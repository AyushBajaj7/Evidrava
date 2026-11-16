"""Render local candidate-frame validation and draw reports."""
from html import escape
import json


def render_frame(result):
    def e(value):
        return escape(str(value))

    def display(value):
        if value is None:
            return "unavailable"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    summary = "".join(f"<tr><th>{e(key.replace('_', ' '))}</th><td>{e(display(value))}</td></tr>"
                      for key, value in result["summary"].items())
    diagnostics = "".join(f"<tr><td>{e(item.get('row') or '—')}</td><td><code>{e(item['code'])}</code></td><td>{e(item['field'])}</td><td>{e(item.get('matter_id') or '—')}</td><td>{e(item['message'])}</td></tr>"
                          for item in result["diagnostics"])
    limits = "".join(f"<li>{e(item)}</li>" for item in result["limitations"])
    selected = ""
    if "selected_matter_ids" in result:
        selected = f"<h2>Selection</h2><p>Related-matter groups: <code>{e(', '.join(result['selected_group_ids']))}</code></p><p>Selected matters: <code>{e(', '.join(result['selected_matter_ids']))}</code></p>"
    diagnostics_rows = diagnostics or '<tr><td colspan="5">No frame diagnostics.</td></tr>'
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidrava candidate frame</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1050px;margin:3rem auto;padding:0 1rem;color:#172b3a;background:#f8fafb}}h1,h2{{line-height:1.2}}.status{{padding:1rem;border-left:5px solid #0d6580;background:#e7f3f7}}table{{width:100%;border-collapse:collapse;background:white;margin:1rem 0}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #dae2e8;vertical-align:top;overflow-wrap:anywhere}}code{{font-size:.85em}}.scroll{{overflow:auto}}small{{color:#485d6b}}</style>
<main><h1>Evidrava candidate frame</h1><div class="status"><strong>{e(result['status'])}</strong><br>Research decision: <strong>NOT EVALUATED</strong>. This report does not verify eligibility evidence, audit, market coverage or a model.</div>
<p>Frame: {e(result['frame_name'])}<br><small>SHA-256: {e(result['frame_sha256'])}</small></p><h2>Counts</h2><table>{summary}</table>{selected}<h2>Diagnostics</h2><div class="scroll"><table><thead><tr><th>Row</th><th>Code</th><th>Field</th><th>Matter</th><th>Finding</th></tr></thead><tbody>{diagnostics_rows}</tbody></table></div><h2>Boundaries</h2><ul>{limits}</ul></main></html>"""
