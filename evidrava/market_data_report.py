"""Render local market-data validation report."""
from html import escape
import json


def render_market_data(result):
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
    diagnostics = "".join(f"<tr><td>{e(item.get('row') or '—')}</td><td><code>{e(item['code'])}</code></td><td>{e(item['field'])}</td><td>{e(item['severity'])}</td><td>{e(item['message'])}</td></tr>"
                          for item in result["diagnostics"])
    limits = "".join(f"<li>{e(item)}</li>" for item in result["limitations"])
    isin_list = ", ".join(result.get("unique_isins", [])) or "None"

    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidrava Market Data Check</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1050px;margin:3rem auto;padding:0 1rem;color:#172b3a;background:#f8fafb}}h1,h2{{line-height:1.2}}.status{{padding:1rem;border-left:5px solid #0d6580;background:#e7f3f7}}table{{width:100%;border-collapse:collapse;background:white;margin:1rem 0}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #dae2e8;vertical-align:top;overflow-wrap:anywhere}}code{{font-size:.85em}}.scroll{{overflow:auto}}small{{color:#485d6b}}</style>
<main><h1>Evidrava Market Data Check</h1><div class="status"><strong>{e(result['status'])}</strong><br>Research decision: <strong>NOT EVALUATED</strong>. This report verifies daily bar schema and consistency; it does not establish detector validity or hindsight proof.</div>
<p>File: {e(result['file_name'])}<br><small>SHA-256: {e(result['file_sha256'])}</small></p><h2>Summary</h2><table>{summary}</table><h2>ISINs ({len(result.get('unique_isins', []))})</h2><p><code>{e(isin_list)}</code></p><h2>Diagnostics</h2><div class="scroll"><table><thead><tr><th>Row</th><th>Code</th><th>Field</th><th>Severity</th><th>Finding</th></tr></thead><tbody>{diagnostics or '<tr><td colspan="5">No market data diagnostics. All bars consistent.</td></tr>'}</tbody></table></div><h2>Boundaries</h2><ul>{limits}</ul></main></html>"""
