(() => {
  "use strict";

  const config = window.EVIDRAVA_CONFIG || {apiBase: "http://127.0.0.1:8001"};
  const apiBase = String(config.apiBase || "").replace(/\/$/, "");
  const elements = {
    connection: document.getElementById("connection"),
    statusCards: document.getElementById("status-cards"),
    refreshStatus: document.getElementById("refresh-status"),
    workbookFile: document.getElementById("workbook-file"),
    sessionsCsv: document.getElementById("sessions-csv"),
    selectionManifestJson: document.getElementById("selection-manifest-json"),
    checkWorkbook: document.getElementById("check-workbook"),
    loadTemplates: document.getElementById("load-templates"),
    frameCsv: document.getElementById("frame-csv"),
    protocolJson: document.getElementById("protocol-json"),
    checkFrame: document.getElementById("check-frame"),
    drawSample: document.getElementById("draw-sample"),
    downloadManifest: document.getElementById("download-manifest"),
    resultStatus: document.getElementById("result-status"),
    resultSummary: document.getElementById("result-summary"),
    resultJson: document.getElementById("result-json")
  };
  let lastManifest = null;

  function setConnection(state, text) {
    elements.connection.className = `connection ${state}`;
    elements.connection.textContent = text;
  }

  function renderJson(value, error = false) {
    elements.resultJson.textContent = JSON.stringify(value, null, 2);
    elements.resultJson.className = error ? "result-error" : "";
  }

  function setResult(label, summary, value, error = false) {
    elements.resultStatus.textContent = label;
    elements.resultSummary.textContent = summary;
    renderJson(value, error);
  }

  async function request(path, options = {}) {
    const headers = {...(options.headers || {})};
    if (options.body !== undefined && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers
    });
    let body;
    try { body = await response.json(); } catch { body = {error: {code: "INVALID_RESPONSE", message: "Local service did not return JSON."}}; }
    if (!response.ok) {
      const message = body?.error?.message || `Request failed with ${response.status}`;
      throw Object.assign(new Error(message), {body, status: response.status});
    }
    return body;
  }

  function card(label, value, state = "pending") {
    const node = document.createElement("article");
    node.className = `status-card ${state}`;
    const labelNode = document.createElement("span");
    labelNode.textContent = label;
    const valueNode = document.createElement("strong");
    valueNode.textContent = value;
    node.append(labelNode, valueNode);
    return node;
  }

  async function loadStatus() {
    try {
      const data = await request("/api/v1/project-status", {headers: {}});
      const research = data.research_status || {};
      const screening = data.screening || {};
      const sourcePreparation = data.source_preparation || {};
      const screeningQueue = data.screening_queue || {};
      const screeningState = screening.input_integrity === "VALID"
        ? (screening.status === "READY_FOR_SCOPE_REVIEW" ? "good" : "pending")
        : "error";
      const screeningLabel = `${screening.completed_attempts || 0} / ${screening.expected_records || 30} completed · ${screening.status || "Unknown"}`;
      elements.statusCards.replaceChildren(
        card("Protocol", research.protocol || "Unknown", research.protocol === "FROZEN" ? "good" : "pending"),
        card("Research decision", research.research_decision || "NOT_EVALUATED", "pending"),
        card("Reviewer", research.reviewer_confirmed ? "Confirmed" : "Unconfirmed", research.reviewer_confirmed ? "good" : "pending"),
        card("Source material", `${sourcePreparation.records_acquired || 0} / ${sourcePreparation.expected_records || 30} prepared`, sourcePreparation.status === "COMPLETE" ? "good" : "pending"),
        card("Screening queue", screeningQueue.status === "SOURCE_QUEUE_READY" ? `${screeningQueue.records_ready || 0} ready` : "Not built", screeningQueue.status === "SOURCE_QUEUE_READY" ? "good" : "pending"),
        card("Screening", screeningLabel, screeningState)
      );
      setConnection("ok", "Local stack connected");
    } catch (error) {
      elements.statusCards.replaceChildren(card("Local stack", "Unavailable", "pending"));
      setConnection("error", "Local stack unavailable");
      setResult("Connection error", error.message, error.body || {error: error.message}, true);
    }
  }

  async function loadTemplates() {
    try {
      const data = await request("/api/v1/templates", {headers: {}});
      elements.frameCsv.value = data.candidate_frame_csv || "";
      elements.protocolJson.value = data.frozen_protocol_json || "";
      lastManifest = null;
      elements.downloadManifest.disabled = true;
      setResult("DRAFT templates loaded", "The protocol remains DRAFT and cannot produce a selection manifest.", data);
    } catch (error) {
      setResult("Template error", error.message, error.body || {error: error.message}, true);
    }
  }

  async function validateFrame() {
    try {
      const data = await request("/api/v1/frame/check", {method: "POST", body: JSON.stringify({frame_csv: elements.frameCsv.value})});
      const report = data.report || {};
      setResult(report.status || "Frame checked", "This result is structural only; research remains NOT_EVALUATED.", data, report.status === "INVALID");
    } catch (error) {
      setResult("Frame rejected", error.message, error.body || {error: error.message}, true);
    }
  }

  async function fileAsBase64(file) {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const chunkSize = 0x8000;
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
    }
    return btoa(binary);
  }

  async function validateWorkbook() {
    const file = elements.workbookFile.files && elements.workbookFile.files[0];
    if (!file) {
      setResult("Workbook required", "Choose a v3.3 .xlsx copy before running a preparation check.", {error: {code: "WORKBOOK_REQUIRED", message: "No workbook file was selected."}}, true);
      return;
    }
    if (file.size > 20_000_000) {
      setResult("Workbook too large", "The local pilot checker accepts a workbook of up to 20 MB.", {error: {code: "WORKBOOK_TOO_LARGE", message: "Selected file exceeds 20 MB."}}, true);
      return;
    }
    const originalLabel = elements.checkWorkbook.textContent;
    elements.checkWorkbook.disabled = true;
    elements.checkWorkbook.textContent = "Checking temporary copy…";
    try {
      const workbookBase64 = await fileAsBase64(file);
      const payload = {workbook_base64: workbookBase64};
      if (elements.sessionsCsv.value.trim()) payload.sessions_csv = elements.sessionsCsv.value;
      if (elements.selectionManifestJson.value.trim()) payload.selection_manifest_json = elements.selectionManifestJson.value;
      const data = await request("/api/v1/workbook/check", {method: "POST", body: JSON.stringify(payload)});
      const report = data.report || {};
      const errorCount = (report.diagnostics || []).filter(item => item.severity === "error").length;
      setResult(report.validation_status || "Workbook checked", `${errorCount} structural error(s) reported. Formula results were not recalculated; research remains NOT_EVALUATED.`, data, report.validation_status === "INVALID");
    } catch (error) {
      setResult("Workbook rejected", error.message, error.body || {error: error.message}, true);
    } finally {
      elements.checkWorkbook.disabled = false;
      elements.checkWorkbook.textContent = originalLabel;
    }
  }

  async function drawSample() {
    try {
      const data = await request("/api/v1/sample/draw", {method: "POST", body: JSON.stringify({frame_csv: elements.frameCsv.value, protocol_json: elements.protocolJson.value})});
      lastManifest = data.selection_manifest || null;
      elements.downloadManifest.disabled = !lastManifest;
      const report = data.report || {};
      setResult(report.status || "Selection created", "The manifest is a configuration artifact; research remains NOT_EVALUATED.", data);
    } catch (error) {
      lastManifest = null;
      elements.downloadManifest.disabled = true;
      setResult("Draw rejected", error.message, error.body || {error: error.message}, true);
    }
  }

  function downloadManifest() {
    if (!lastManifest) return;
    const blob = new Blob([JSON.stringify(lastManifest, null, 2) + "\n"], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "selection-manifest.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  elements.refreshStatus.addEventListener("click", loadStatus);
  elements.checkWorkbook.addEventListener("click", validateWorkbook);
  elements.loadTemplates.addEventListener("click", loadTemplates);
  elements.checkFrame.addEventListener("click", validateFrame);
  elements.drawSample.addEventListener("click", drawSample);
  elements.downloadManifest.addEventListener("click", downloadManifest);
  loadStatus();
  loadTemplates();
})();
