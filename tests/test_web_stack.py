"""Ephemeral end-to-end checks for frontend -> middleware -> backend."""
from __future__ import annotations

import base64
from io import BytesIO
from http.server import ThreadingHTTPServer
from hashlib import sha256
import json
from pathlib import Path
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from backend.app import create_server as create_backend
from evidrava import __version__
from frontend.serve import create_server as create_frontend
from middleware.proxy import create_server as create_middleware


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx"


class LocalServer:
    def __init__(self, server: ThreadingHTTPServer):
        self.server = server
        host, port = server.server_address[:2]
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


def fetch(url, method="GET", payload=None, origin=None):
    headers = {}
    if origin:
        headers["Origin"] = origin
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


class WebStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = LocalServer(create_backend("127.0.0.1", 0)).start()
        frontend_server = create_frontend("127.0.0.1", 0, api_base="http://127.0.0.1:1")
        cls.frontend = LocalServer(frontend_server)
        cls.middleware = LocalServer(create_middleware("127.0.0.1", 0, backend_url=cls.backend.base_url,
                                                        frontend_origin=cls.frontend.base_url)).start()
        frontend_server.api_base = cls.middleware.base_url
        cls.frontend.start()
        cls.frame_csv = (ROOT / "fixtures/frame/candidate-frame-synthetic.csv").read_text(encoding="utf-8")
        cls.protocol_json = (ROOT / "fixtures/frame/frozen-protocol-synthetic.json").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.frontend.close()
        cls.middleware.close()
        cls.backend.close()

    def test_frontend_serves_static_console_and_dynamic_local_config(self):
        status, headers, body = fetch(self.frontend.base_url + "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Evidrava", body)
        self.assertIn(b"workbook-file", body)
        self.assertIn(b"upload.css", body)
        self.assertIn("Content-Security-Policy", headers)
        status, _, config = fetch(self.frontend.base_url + "/config.js")
        self.assertEqual(status, 200)
        self.assertIn(self.middleware.base_url.encode("utf-8"), config)

    def test_status_and_frame_check_flow_through_middleware(self):
        status, headers, body = fetch(self.middleware.base_url + "/api/v1/project-status", origin=self.frontend.base_url)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), self.frontend.base_url)
        project = json.loads(body)
        release_record = json.loads((ROOT / "pilot/development/evidrava-live-screening-status-increment-2026-11-16.json").read_text(encoding="utf-8"))
        expected_increment = release_record["software_version"] if release_record["status"] == "COMPLETE" else "not-yet-verified"
        self.assertEqual(project["software_version"], __version__)
        self.assertEqual(project["last_verified_increment"], expected_increment)
        self.assertTrue(project["capabilities"]["workbook_check"])
        self.assertEqual(project["research_status"]["research_decision"], "NOT_EVALUATED")
        self.assertEqual(project["source_preparation"]["status"], "COMPLETE")
        self.assertEqual(project["source_preparation"]["records_acquired"], 30)
        self.assertFalse(project["source_preparation"]["human_screening_completed"])
        self.assertEqual(project["screening"]["status"], "IN_PROGRESS")
        self.assertEqual(project["screening"]["input_integrity"], "VALID")
        self.assertEqual(project["screening"]["unresolved_records"], 0)
        self.assertEqual(project["screening_queue"]["status"], "SOURCE_QUEUE_READY")
        self.assertEqual(project["screening_queue"]["records_ready"], 30)
        self.assertFalse(project["screening_queue"]["human_screening_completed"])
        self.assertTrue(project["capabilities"]["screening_source_queue"])
        status, _, body = fetch(self.middleware.base_url + "/api/v1/frame/check", method="POST",
                                payload={"frame_csv": self.frame_csv}, origin=self.frontend.base_url)
        self.assertEqual(status, 200)
        report = json.loads(body)["report"]
        self.assertEqual(report["status"], "READY_TO_FREEZE")
        self.assertEqual(report["research_decision"], "NOT_EVALUATED")

    def test_workbook_copy_is_checked_through_the_api_without_mutating_source(self):
        before = sha256(WORKBOOK.read_bytes()).hexdigest()
        payload = {"workbook_base64": base64.b64encode(WORKBOOK.read_bytes()).decode("ascii")}
        status, _, body = fetch(self.middleware.base_url + "/api/v1/workbook/check", method="POST", payload=payload, origin=self.frontend.base_url)
        self.assertEqual(status, 200)
        report = json.loads(body)["report"]
        self.assertEqual(report["validation_only"], True)
        self.assertEqual(report["research_decision"], "NOT_EVALUATED")
        self.assertEqual(report["source_name"], "browser-uploaded-workbook.xlsx")
        self.assertEqual(report["temporary_upload_only"], True)
        self.assertEqual(before, sha256(WORKBOOK.read_bytes()).hexdigest())

    def test_invalid_workbook_encoding_is_rejected_without_server_error(self):
        status, _, body = fetch(self.middleware.base_url + "/api/v1/workbook/check", method="POST",
                                payload={"workbook_base64": "not valid base64!"}, origin=self.frontend.base_url)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "WORKBOOK_INVALID")

    def test_malformed_workbook_xml_is_rejected_without_server_error(self):
        malformed = BytesIO()
        with ZipFile(malformed, "w") as archive:
            archive.writestr("[Content_Types].xml", "<broken")
        payload = {"workbook_base64": base64.b64encode(malformed.getvalue()).decode("ascii")}
        status, _, body = fetch(self.middleware.base_url + "/api/v1/workbook/check", method="POST",
                                payload=payload, origin=self.frontend.base_url)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "WORKBOOK_INVALID")

    def test_invalid_optional_workbook_manifest_is_rejected(self):
        payload = {
            "workbook_base64": base64.b64encode(WORKBOOK.read_bytes()).decode("ascii"),
            "sessions_csv": "date\n2026-01-02\n",
            "selection_manifest_json": '{"selected_matter_ids":"not-a-list"}'
        }
        status, _, body = fetch(self.middleware.base_url + "/api/v1/workbook/check", method="POST", payload=payload, origin=self.frontend.base_url)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "WORKBOOK_INVALID")

    def test_frozen_draw_succeeds_and_draft_or_bad_origin_are_rejected(self):
        status, _, body = fetch(self.middleware.base_url + "/api/v1/sample/draw", method="POST",
                                payload={"frame_csv": self.frame_csv, "protocol_json": self.protocol_json}, origin=self.frontend.base_url)
        self.assertEqual(status, 200)
        selection = json.loads(body)["selection_manifest"]
        self.assertEqual(len(selection["selected_matter_ids"]), 4)
        draft = json.loads(self.protocol_json)
        draft["state"] = "DRAFT"
        status, _, body = fetch(self.middleware.base_url + "/api/v1/sample/draw", method="POST",
                                payload={"frame_csv": self.frame_csv, "protocol_json": json.dumps(draft)}, origin=self.frontend.base_url)
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(body)["error"]["code"], "DRAW_REJECTED")
        status, _, body = fetch(self.middleware.base_url + "/api/v1/project-status", origin="http://untrusted.example")
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"]["code"], "ORIGIN_NOT_ALLOWED")

    def test_middleware_rejects_unknown_routes_and_permits_safe_preflight(self):
        status, _, body = fetch(self.middleware.base_url + "/api/v1/not-a-route", origin=self.frontend.base_url)
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"]["code"], "ROUTE_NOT_ALLOWED")
        request = Request(self.middleware.base_url + "/api/v1/frame/check", headers={
            "Origin": self.frontend.base_url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }, method="OPTIONS")
        with urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], self.frontend.base_url)

    def test_components_reject_nonlocal_bindings_or_connections(self):
        with self.assertRaises(ValueError):
            create_backend("0.0.0.0", 0)
        with self.assertRaises(ValueError):
            create_frontend("127.0.0.1", 0, api_base="https://example.test")
        with self.assertRaises(ValueError):
            create_middleware("127.0.0.1", 0, backend_url="http://example.test:8002",
                              frontend_origin=self.frontend.base_url)


if __name__ == "__main__":
    unittest.main()
