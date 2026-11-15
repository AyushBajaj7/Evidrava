"""Offline provisional-note checks; fixture PDF bytes are not authored evidence."""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from urllib.parse import unquote

from evidrava.brief import build_brief
from evidrava.__main__ import main


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = self.root / "packet"
        self.packet.mkdir()
        self.out = self.root / "brief"
        self.notes_path = self.root / "notes.json"
        self.manifest = {"kind": "source-acquisition", "records": [], "files": {}}
        records = []
        for number in (1, 2):
            sid = f"RECON-{number:02}"
            relative = f"records/{sid}"
            folder = self.packet / relative
            folder.mkdir(parents=True)
            # Deliberately opaque transport bytes: these tests never parse a PDF.
            (folder / "source.pdf").write_bytes(f"%PDF-fixture-{number}\nopaque test bytes".encode())
            pages = {"status": "OK", "page_count": 2, "pages": [
                {"page": 1, "text": f"First source anchor for record {number}.\nOnly page one contains this phrase."},
                {"page": 2, "text": "Second page contains different evidence."},
            ]}
            write_json(folder / "pages.json", pages)
            for filename in ("source.pdf", "pages.json"):
                self.manifest["files"][f"{relative}/{filename}"] = digest(folder / filename)
            self.manifest["records"].append({
                "screening_id": sid, "title": f"Fictional source {number}", "status": "ACQUIRED",
                "pdf_capture": {"path": f"{relative}/source.pdf", "sha256": digest(folder / "source.pdf")},
                "extraction": {"path": f"{relative}/pages.json", "status": "OK", "page_count": 2},
            })
            records.append({"screening_id": sid, "suggested_disposition": "uncertain",
                "rationale": "Provisional fixture requiring a person's decision.",
                "observations": [{"summary": "A machine-assisted fixture summary.", "page": 1,
                    "paragraph": "Fixture paragraph 1", "anchor": f"First source anchor for record {number}."}],
                "open_questions": ["Does the original source support the proposed interpretation?"]})
        self.notes = {"kind": "provisional-screening-notes", "schema_version": 1,
            "prepared_on": "2026-11-14", "prepared_by": "AI-assisted fixture",
            "source_packet_manifest_sha256": "", "scope_basis": "Unfrozen fixture scope.", "records": records}
        self.save_manifest()

    def save_manifest(self):
        write_json(self.packet / "manifest.json", self.manifest)
        self.notes["source_packet_manifest_sha256"] = digest(self.packet / "manifest.json")

    def change_pages(self, change):
        relative = "records/RECON-01/pages.json"
        path = self.packet / relative
        pages = json.loads(path.read_text(encoding="utf-8"))
        change(pages)
        write_json(path, pages)
        self.manifest["files"][relative] = digest(path)
        self.save_manifest()

    def build(self, out=None):
        write_json(self.notes_path, self.notes)
        return build_brief(self.packet, self.notes_path, out or self.out)

    def test_valid_brief_is_provisional_and_preserves_inputs(self):
        before = {str(path): path.read_bytes() for path in self.packet.rglob("*") if path.is_file()}
        notes_before = deepcopy(self.notes)
        result = self.build()
        self.assertEqual(result["status"], "PROVISIONAL")
        self.assertEqual(result["citation_checks"], "PASSED")
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")
        for key in ("human_screening_completed", "independent_audit_completed", "publication_dates_verified"):
            self.assertIs(result[key], False)
        self.assertTrue(all(r["status"] == "PENDING_HUMAN_REVIEW" for r in result["records"]))
        self.assertEqual(self.notes, notes_before)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.packet.rglob("*") if path.is_file()})
        manifest = json.loads((self.out / "manifest.json").read_text())
        for name, value in manifest["files"].items():
            self.assertEqual(digest(self.out / name), value)
        html = (self.out / "report.html").read_text(encoding="utf-8")
        for target in re.findall(r'href="([^"]+)"', html):
            self.assertTrue((self.out / unquote(target.split("#")[0])).exists(), target)

    def test_notes_bound_to_exact_packet_manifest(self):
        self.notes["source_packet_manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.out.exists())

    def test_changed_source_bytes_rejected_without_output(self):
        (self.packet / "records/RECON-01/source.pdf").write_bytes(b"changed source")
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.out.exists())

    def test_changed_text_bytes_rejected_without_rehash(self):
        path = self.packet / "records/RECON-01/pages.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.build()

    def test_page_out_of_bounds_or_anchor_on_wrong_page_rejected(self):
        for page in (0, 3, 2):
            with self.subTest(page=page):
                self.notes["records"][0]["observations"][0]["page"] = page
                with self.assertRaises(ValueError):
                    self.build()

    def test_invented_anchor_rejected(self):
        self.notes["records"][0]["observations"][0]["anchor"] = "This statement never appears in the source."
        with self.assertRaises(ValueError):
            self.build()

    def test_anchor_whitespace_normalization_is_supported(self):
        self.notes["records"][0]["observations"][0]["anchor"] = "First\n source\t anchor for  record 1."
        self.assertEqual(self.build()["citation_checks"], "PASSED")

    def test_noncontiguous_extracted_page_inventory_rejected(self):
        self.change_pages(lambda pages: pages["pages"][1].update(page=3))
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_extracted_page_rejected_even_with_valid_hashes(self):
        self.change_pages(lambda pages: pages["pages"].pop())
        with self.assertRaises(ValueError):
            self.build()

    def test_record_page_count_must_match_extraction(self):
        self.manifest["records"][0]["extraction"]["page_count"] = 3
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()

    def test_duplicate_missing_and_extra_note_ids_rejected(self):
        original = deepcopy(self.notes["records"])
        variants = [original[:1], original + [deepcopy(original[0])], deepcopy(original), deepcopy(original)]
        variants[2][1]["screening_id"] = "RECON-01"
        variants[3][1]["screening_id"] = "RECON-03"
        for records in variants:
            with self.subTest(ids=[r["screening_id"] for r in records]):
                self.notes["records"] = records
                with self.assertRaises(ValueError):
                    self.build()

    def test_human_review_audit_and_timing_fields_are_not_accepted(self):
        original = deepcopy(self.notes)
        for field, value in (("human_screening_decision", "include"), ("screening_active_minutes", 2),
                             ("independent_audit_completed", True), ("human_reviewer_id", "Synthetic Reviewer")):
            with self.subTest(field=field):
                self.notes = deepcopy(original)
                self.notes["records"][0][field] = value
                with self.assertRaises(ValueError):
                    self.build()
        self.notes = deepcopy(original)
        self.notes["human_screening_completed"] = True
        with self.assertRaises(ValueError):
            self.build()

    def test_path_escape_is_rejected_even_when_hash_matches(self):
        outside = self.root / "outside.txt"
        outside.write_bytes(b"not part of the packet")
        self.manifest["files"]["../outside.txt"] = digest(outside)
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(outside.read_bytes(), b"not part of the packet")

    def test_booleans_are_not_page_numbers(self):
        self.notes["records"][0]["observations"][0]["page"] = True
        with self.assertRaises(ValueError):
            self.build()
        self.notes["records"][0]["observations"][0]["page"] = 1
        self.change_pages(lambda pages: pages["pages"][0].update(page=True))
        with self.assertRaises(ValueError):
            self.build()

    def test_html_escapes_source_title_notes_and_anchors(self):
        injection = '<script>alert("fixture")</script> & unsafe markup'
        self.manifest["records"][0]["title"] = injection
        self.change_pages(lambda pages: pages["pages"][0].update(text=injection))
        note = self.notes["records"][0]
        note["rationale"] = injection
        note["observations"][0].update(summary=injection, paragraph=injection, anchor=injection)
        note["open_questions"] = [injection]
        self.build()
        html = (self.out / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp; unsafe markup", html)
        self.assertIn("PROVISIONAL", html)

    def test_existing_brief_is_preserved(self):
        self.build()
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_output_cannot_modify_preserved_packet(self):
        for target in (self.packet, self.packet / "new-brief"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.build(target)
        self.assertFalse((self.packet / "new-brief").exists())

    def test_duplicate_json_keys_rejected(self):
        write_json(self.notes_path, self.notes)
        raw = self.notes_path.read_text(encoding="utf-8")
        raw = raw.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1)
        self.notes_path.write_text(raw, encoding="utf-8")
        with self.assertRaises(ValueError):
            build_brief(self.packet, self.notes_path, self.out)

    def test_include_suggestion_cannot_promote_human_or_audit_status(self):
        self.notes["records"][0]["suggested_disposition"] = "include_candidate"
        result = self.build()
        self.assertEqual(result["records"][0]["status"], "PENDING_HUMAN_REVIEW")
        self.assertIs(result["human_screening_completed"], False)
        self.assertIs(result["independent_audit_completed"], False)
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")

    def test_cli_valid_brief_and_overwrite_refusal(self):
        write_json(self.notes_path, self.notes)
        argv = ["review-brief", "--packet", str(self.packet), "--notes", str(self.notes_path), "--out", str(self.out)]
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(argv), 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["status"], "PROVISIONAL")
        self.assertIs(result["human_screening_completed"], False)
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(main(argv), 4)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_cli_invalid_notes_fail_without_output(self):
        self.notes["records"][0]["observations"][0]["anchor"] = "A wholly invented statement."
        write_json(self.notes_path, self.notes)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(main(["review-brief", "--packet", str(self.packet), "--notes", str(self.notes_path), "--out", str(self.out)]), 4)
        self.assertFalse(self.out.exists())

    def test_received_provisional_notes_bind_to_saved_packet(self):
        root = Path(__file__).resolve().parents[1]
        # Windows may put TemporaryDirectory on C: while the project is on D:.
        # Keep the copied, byte-identical packet and its relative output on one volume.
        received_packet = self.root / "received-packet"
        shutil.copytree(root / "pilot/sources/recon-first-three", received_packet)
        result = build_brief(received_packet, root / "pilot/screening/provisional-first-three-2026-11-14.json", self.out)
        self.assertEqual(len(result["records"]), 3)
        self.assertEqual(sum(len(r["observations"]) for r in result["records"]), 15)
        self.assertEqual(result["citation_checks"], "PASSED")
        self.assertIs(result["human_screening_completed"], False)


if __name__ == "__main__":
    unittest.main()
