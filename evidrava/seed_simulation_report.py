"""Render local seed sensitivity simulation report."""
from html import escape
import json


def render_seed_simulation(result):
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
    
    probs = "".join(f"<tr><td><code>{e(g)}</code></td><td>{prob:.2%}</td></tr>"
                    for g, prob in result.get("empirical_group_selection_probabilities", {}).items())
    
    sizes = "".join(f"<tr><td>Group size {e(s)}</td><td>{e(c)} times</td></tr>"
                    for s, c in result.get("selected_group_size_counts", {}).items())
    
    limits = "".join(f"<li>{e(item)}</li>" for item in result.get("limitations", []))

    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidrava Seed Sensitivity Simulation</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1050px;margin:3rem auto;padding:0 1rem;color:#172b3a;background:#f8fafb}}h1,h2{{line-height:1.2}}.status{{padding:1rem;border-left:5px solid #0d6580;background:#e7f3f7}}table{{width:100%;border-collapse:collapse;background:white;margin:1rem 0}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #dae2e8;vertical-align:top;overflow-wrap:anywhere}}code{{font-size:.85em}}.scroll{{overflow:auto}}small{{color:#485d6b}}</style>
<main><h1>Evidrava Seed Sensitivity Simulation</h1><div class="status"><strong>{e(result['status'])}</strong><br>Research decision: <strong>NOT EVALUATED</strong>. This report simulates selection probability across candidate seeds; it does not replace pre-registration or research evaluation.</div>
<p>Frame: {e(result.get('frame_name', '—'))}<br><small>SHA-256: {e(result.get('frame_sha256', '—'))}</small></p><h2>Summary</h2><table>{summary}</table><h2>Selected Group Sizes Across Seeds</h2><table><thead><tr><th>Size</th><th>Selection Frequency</th></tr></thead><tbody>{sizes or '<tr><td colspan="2">None</td></tr>'}</tbody></table><h2>Empirical Group Selection Probabilities</h2><div class="scroll"><table><thead><tr><th>Group ID</th><th>Selection Probability</th></tr></thead><tbody>{probs or '<tr><td colspan="2">None</td></tr>'}</tbody></table></div><h2>Boundaries</h2><ul>{limits}</ul></main></html>"""
