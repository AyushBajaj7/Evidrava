"""Helper to verify and safely route encrypted PDF sources (e.g. RECON-08).

Documents legitimate manual acquisition, checks PDF structure and keyword
relevance, and extracts native page text into a verified resolution packet.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from pypdf import PdfReader


EXPECTED_KEYWORDS = {
    "RECON-08": ["Ruchiraj", "Shree Yaax", "14502", "January", "2011"]
}


def check_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise ValueError(f"File not found: {pdf_path}")
    blob = pdf_path.read_bytes()
    digest = sha256(blob).hexdigest()

    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        return {
            "status": "ENCRYPTED",
            "file_name": pdf_path.name,
            "sha256": digest,
            "page_count": len(reader.pages),
            "text_extractable": False,
        }

    pages_text = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception as exc:
            txt = ""
        pages_text.append({"page": idx, "text": txt})

    full_text = "\n".join(p["text"] for p in pages_text)
    return {
        "status": "OK",
        "file_name": pdf_path.name,
        "sha256": digest,
        "page_count": len(pages_text),
        "text_extractable": bool(full_text.strip()),
        "pages": pages_text,
        "full_text": full_text
    }


def main():
    parser = argparse.ArgumentParser(description="Verify and resolve encrypted PDF sources")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to PDF to inspect or resolve")
    parser.add_argument("--screening-id", default="RECON-08", help="Screening ID to check keywords for")
    parser.add_argument("--out", type=Path, help="Optional output directory for extracted pages.json and text.txt")
    args = parser.parse_args()

    try:
        info = check_pdf(args.pdf)
    except Exception as exc:
        print(f"Error checking PDF: {exc}", file=sys.stderr)
        return 1

    print(f"PDF: {info['file_name']}")
    print(f"Status: {info['status']}")
    print(f"SHA-256: {info['sha256']}")
    print(f"Pages: {info['page_count']}")
    print(f"Text Extractable: {info['text_extractable']}")

    keywords = EXPECTED_KEYWORDS.get(args.screening_id, [])
    if info["status"] == "OK" and keywords:
        matched = [k for k in keywords if k.lower() in info["full_text"].lower()]
        print(f"Keyword Matches for {args.screening_id}: {len(matched)} / {len(keywords)} ({', '.join(matched)})")

    if args.out and info["status"] == "OK":
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "pages.json").write_text(json.dumps({"status": "OK", "page_count": info["page_count"], "pages": info["pages"]}, indent=2), encoding="utf-8")
        (args.out / "text.txt").write_text(info["full_text"], encoding="utf-8")
        receipt = {
            "screening_id": args.screening_id,
            "resolved_pdf_sha256": info["sha256"],
            "page_count": info["page_count"],
            "resolution_method": "manual_verified_route",
            "research_decision": "NOT_EVALUATED"
        }
        (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote resolution packet to: {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
