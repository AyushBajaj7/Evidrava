"""Human-readable navigation report for the screened-source queue."""
from html import escape


def render_screening_queue(result):
    def e(value):
        return escape(str(value))

    def local_link(uri, label):
        return f'<a href="{e(uri)}">{e(label)}</a>'

    cards = []
    for record in result["records"]:
        links = record["links"]
        material = " · ".join([
            local_link(links["source_pdf"], "Original PDF"),
            local_link(links["page_text"], "Page text"),
            local_link(links["page_inventory"], "Page inventory"),
        ] + ([local_link(links["captured_listing_page"], "Captured listing page")] if links["captured_listing_page"] else []))
        external = f'<a href="{e(record["official_listing_url"])}">Official listing</a>'
        rejection = (f'<p class="note">{record["rejected_candidate_count"]} unrelated candidate link(s) were retained as rejections in the packet manifest.</p>'
                     if record["rejected_candidate_count"] else "")
        cards.append(f'''<section><p class="eyebrow">{e(record["screening_id"])} · {e(record["listing_date_stratum"])} · {e(record["extraction_status"])}</p>
<h2>{e(record["title"])}</h2><p>{external} · packet: {e(record["source_packet"])}</p><p>{material}</p>{rejection}<p><strong>Human action:</strong> {e(record["human_action_required"])}</p></section>''')
    source = result["source_preparation"]
    checklist = "".join(f"<li>{e(item)}</li>" for item in result["human_work_checklist"])
    limitations = "".join(f"<li>{e(item)}</li>" for item in result["limitations"])
    packet_rows = "".join(f"<tr><td>{e(item['packet'])}</td><td>{e(item['packet_status'])}</td><td>{item['acquired_records']}</td><td>{item['verified_files']}</td></tr>" for item in result["source_packet_checks"])
    statuses = ", ".join(f"{e(name)}: {count}" for name, count in source["extraction_statuses"].items())
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidrava human screening queue</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#173044;background:#f4f7f9;max-width:1100px;margin:2rem auto;padding:0 1rem}}h1,h2{{line-height:1.25}}section{{padding:1.25rem;background:white;border:1px solid #d7e2e8;border-radius:8px;margin:1rem 0}}.banner{{padding:1.2rem;border-left:5px solid #b57212;background:#fff2d6}}.eyebrow,.note{{font-size:.9rem;color:#4b6271}}a{{color:#075e85;overflow-wrap:anywhere}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:.6rem;text-align:left;border-bottom:1px solid #d7e2e8;vertical-align:top}}.scroll{{overflow:auto}}</style></head><body><main>
<h1>Evidrava human screening queue</h1><div class="banner"><strong>SOURCE MATERIAL READY — HUMAN SCREENING PENDING</strong><br>All links below lead to saved source material. This report has not selected a sample, made an eligibility decision, measured time, verified publication dates or credited independent audit.</div>
<p><strong>{source['acquired_records']} / {source['expected_records']}</strong> fixed workload records have preserved source material. Native extraction status: {statuses}.</p>
<p>Use this queue to navigate. Record real human work only in <code>working/screening_30.csv</code>; do not edit the navigation export. When complete, run <code>python -m evidrava screening-report --csv working/screening_30.csv --out &lt;new-directory&gt;</code>.</p>
<h2>Human workflow</h2><ol>{checklist}</ol>
<h2>Packet integrity checked</h2><div class="scroll"><table><thead><tr><th>Packet</th><th>Acquisition status</th><th>Acquired records</th><th>Files hash-checked</th></tr></thead><tbody>{packet_rows}</tbody></table></div>
<h2>Records</h2>{''.join(cards)}
<h2>Limits</h2><ul>{limitations}</ul><p>The research decision remains <strong>NOT EVALUATED</strong>.</p>
<p><a href="screening-queue.json">Structured queue</a> · <a href="screening-queue.csv">Navigation CSV</a> · <a href="manifest.json">Output hashes</a></p>
</main></body></html>'''
