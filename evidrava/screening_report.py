"""Standalone human-readable screening workload report."""
from html import escape


def render_screening(result):
    def e(value):
        return escape(str(value))

    def display(value):
        return "unavailable" if value is None else (f"{value:.2f}" if isinstance(value, float) else str(value))

    s = result["summary"]
    timings = s["complete_active_minutes"]
    stratum_rows = "".join(f"<tr><th>{e(name)}</th><td>{v['completed_screening_attempts']} / {v['expected_records']}</td><td>{v['complete_timing_observations']}</td><td>{e(display(v['complete_active_minutes']['median']))}</td><td>{v['unresolved_records']}</td></tr>" for name, v in result["strata"].items())
    record_rows = "".join(f"<tr><td>{e(r['screening_id'])}</td><td><a href=\"{e(r['url'])}\">{e(r['title'])}</a></td><td>{e(r['decision'] or 'pending')}</td><td>{'complete' if r['disposition_complete'] else 'pending'}</td><td>{e(display(r['active_total_minutes']))}</td><td>{'yes' if r['unresolved'] else 'no'}</td><td>{e(', '.join(r['missing_fields']))}</td></tr>" for r in result["records"])
    issues = "".join(f"<li><strong>{e(d['code'])}</strong> — {e(d['screening_id'])} / {e(d['field'])}: {e(d['message'])}</li>" for d in result["diagnostics"])
    limits = "".join(f"<li>{e(v)}</li>" for v in result["limitations"])
    estimate = result["planning_scenario"]
    forecast = "No candidate-listing workload scenario requested."
    if estimate["requested_candidate_listings"] is not None:
        if estimate["illustrative_initial_screening_hours"] is None:
            forecast = e(estimate["withheld_reason"])
        else:
            forecast = f"For {estimate['requested_candidate_listings']} candidate listings: {estimate['illustrative_initial_screening_hours']:.2f} illustrative initial-screening hours at the observed mean pace."
    assumptions = "".join(f"<li>{e(v)}</li>" for v in estimate["assumptions"])
    waits = s["observed_minutes"]["access_wait_minutes"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidrava screening progress</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:2.5rem auto;padding:0 1rem;color:#172b3a;background:#f8fafb}}h1,h2{{line-height:1.2}}.status{{padding:1rem;background:#e7f3f7;border-left:5px solid #0d6580}}.cards{{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0}}.card{{background:white;padding:1rem;flex:1;min-width:150px;border:1px solid #dae2e8}}.card b{{display:block;font-size:1.7rem}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:.6rem;text-align:left;border-bottom:1px solid #dae2e8;vertical-align:top;overflow-wrap:anywhere}}.scroll{{overflow:auto}}small{{color:#485d6b}}a{{color:#075e85}}</style></head><body><main>
<h1>Evidrava screening progress</h1><div class="status"><strong>{e(result['status'])}</strong><br>This is the fixed reconnaissance exercise. The research protocol remains DRAFT; this report does not select the research sample or certify independent review.</div>
<div class="cards"><div class="card">Screening attempts completed<b>{s['completed_screening_attempts']} / {s['expected_records']}</b></div><div class="card">Complete timing observations<b>{s['complete_timing_observations']}</b></div><div class="card">Pending records<b>{s['pending_records']}</b></div><div class="card">Unresolved records<b>{s['unresolved_records']}</b></div></div>
<p>Continue in the working CSV. Record the actual screening person, decision and evidence. Enter screening, grouping and predecessor minutes separately; use an explicit zero only when no time was spent on that component. An uncertain decision can document a completed attempt while its follow-up remains open.</p>
<h2>Observed effort</h2><ul><li>Logged active minutes, including partial observations: <strong>{e(display(s['logged_active_minutes']))}</strong>.</li><li>Complete timing cohort: {timings['observations']} records; mean {e(display(timings['mean']))}, median {e(display(timings['median']))}, range {e(display(timings['min']))}–{e(display(timings['max']))} active minutes per listing.</li><li>Access waiting: {e(display(waits['total']))} minutes across {waits['observations']} observations; excluded from active-time statistics.</li></ul>
<h2>By listing-date interval</h2><div class="scroll"><table><thead><tr><th>Interval</th><th>Completed / expected</th><th>Timed observations</th><th>Median active minutes</th><th>Unresolved</th></tr></thead><tbody>{stratum_rows}</tbody></table></div>
<h2>Planning scenario</h2><p>{forecast}</p><ul>{assumptions}</ul>
<h2>Records to work through</h2><div class="scroll"><table><thead><tr><th>ID</th><th>Source</th><th>Decision</th><th>Attempt</th><th>Active minutes</th><th>Follow-up</th><th>Missing review fields</th></tr></thead><tbody>{record_rows}</tbody></table></div>
<h2>Diagnostics</h2><ul>{issues or '<li>No input errors; unfinished fields remain pending.</li>'}</ul>
<h2>Interpretation</h2><ul>{limits}</ul><p><small>Input SHA-256: {e(result['input_sha256'])}. Original CSV and nine retained captures verified offline. Report version {e(result['checker_version'])}; research decision NOT EVALUATED.</small></p>
</main></body></html>"""
