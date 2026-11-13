"""Render a standalone local HTML preparation report."""
from html import escape


def render_html(result):
    def e(value):
        return escape(str(value))

    metrics = "".join(f"<tr><th>{e(k.replace('_', ' '))}</th><td>{e('unavailable' if v is None else v)}</td></tr>" for k, v in result["metrics"].items())
    findings = "".join(f"<tr><td>{e(d['severity'])}</td><td><code>{e(d['code'])}</code></td><td>{e(d['sheet'])}!{e(d['cell'])}</td><td>{e(d['message'])}</td></tr>" for d in result["diagnostics"])
    readiness = "".join(f"<li>{e(text)}</li>" for text in result["readiness"])
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidrava pilot preparation report</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:3rem auto;padding:0 1rem;color:#172b3a;background:#f8fafb}}h1,h2{{line-height:1.2}}.status{{padding:1rem;border-left:5px solid #0d6580;background:#e7f3f7}}table{{width:100%;border-collapse:collapse;background:white;margin:1rem 0}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #dae2e8;vertical-align:top;overflow-wrap:anywhere}}code{{font-size:.85em}}.scroll{{overflow-x:auto}}small{{color:#485d6b}}</style>
<main><h1>Evidrava pilot preparation</h1>
<div class="status"><strong>Protocol: {e(result['protocol_status'])} · Input validation: {e(result['validation_status'])}</strong><br>
Research decision: <strong>NOT EVALUATED</strong>. This report does not certify audit completion, historical source truth, market coverage, or detector performance.</div>
<p>Workbook: {e(result['source_name'])}<br><small>SHA-256: {e(result['workbook_sha256'])}</small></p>
<h2>Preparation counts</h2><p>Counts use registered inputs and are provisional when an inventory is unfinished or errors exist. An audit flag records an assertion that a human review occurred; identity and source contents still require verification.</p>
<table>{metrics}</table><h2>What remains</h2><ul>{readiness}</ul>
<h2>Diagnostics</h2><div class="scroll"><table><thead><tr><th>Level</th><th>Code</th><th>Location</th><th>Finding</th></tr></thead><tbody>{findings or '<tr><td colspan="4">No input diagnostics.</td></tr>'}</tbody></table></div>
<p><small>Checker {e(result['checker_version'])}. Formula fingerprints were checked against v3.3; formulas were not recalculated. The supplied 114-scenario LibreOffice suite was not executed by this command.</small></p></main></html>"""
