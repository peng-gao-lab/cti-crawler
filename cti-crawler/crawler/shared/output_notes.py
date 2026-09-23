"""Reader-facing inventory of saved documents and their current PDF issues."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ..pdf.cleanup import current_pdf
from .document_paths import derived_pdf_path
from .report_index import saved_reports
from .storage import FileStorage
from .package_layout import collection_readme


def collect_pdf_issues(output_root, reports):
    """Inspect current files using either the crawl index or a packaging manifest."""
    output_root = Path(output_root)
    counts = Counter(articles=0, html_originals=0, native_pdfs=0, derived_pdfs=0,
                     missing_pdfs=0, pdfs_needing_reconversion=0, pdfs_with_missing_images=0,
                     pdfs_with_text_layer_issues=0)
    missing, outdated, warnings, text_layer = [], [], [], []
    for report in sorted(reports, key=lambda r: (r["source"], r["url"])):
        original = output_root / report["file"]
        if not original.is_file():
            continue
        counts["articles"] += 1
        if original.suffix.lower() == ".pdf":
            counts["native_pdfs"] += 1
            continue
        if original.suffix.lower() not in {".html", ".htm"}:
            continue
        counts["html_originals"] += 1
        status_file = output_root / ".pdf" / report["file"] / "status.json"
        status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.is_file() else {}
        pdf = derived_pdf_path(original)
        item = {"source": report["source"], "url": report["url"], "html": report["file"],
                "pdf": pdf.relative_to(output_root).as_posix()}
        if not pdf.is_file():
            missing.append({**item, "conversion_status": status.get("conversion_status", "not_attempted"),
                            "last_error": status.get("error")})
            counts["missing_pdfs"] += 1
            continue
        counts["derived_pdfs"] += 1
        if not current_pdf(status, output_root):
            outdated.append({**item, "reason": "PDF has no matching successful conversion record for the current original."})
            counts["pdfs_needing_reconversion"] += 1
        missing_images = status.get("missing_images", []) + status.get("checks", {}).get("missing_images", [])
        if missing_images:
            warnings.append({**item, "missing_image_count": len(missing_images),
                             "missing_images": missing_images})
            counts["pdfs_with_missing_images"] += 1
        issues = status.get("checks", {}).get("text_layer_issues", [])
        if issues:
            text_layer.append({**item, "text_layer_issues": issues})
            counts["pdfs_with_text_layer_issues"] += 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "All saved sources, including sources disabled in the latest run. Articles are counted by source + URL.",
        "notes": "Reports without PDFs retain their HTML originals. Each error records the last conversion attempt. Unavailable images are replaced with placeholders and listed below. PDFs with text-layer issues display their text but lose the listed characters when copied or searched; the HTML original keeps them.",
        "counts": dict(counts), "missing_pdfs": missing,
        "pdfs_needing_reconversion": outdated, "pdfs_with_missing_images": warnings,
        "pdfs_with_text_layer_issues": text_layer,
    }
    return payload


def export_output_notes(output_root, state_root, *, classification_file="classifications.json",
                        failure_file="failures.json", source_risk_file="source_risks.json"):
    output_root = Path(output_root)
    reports = list(saved_reports(state_root, output_root))
    payload = collect_pdf_issues(output_root, reports)
    storage = FileStorage(output_root)
    storage.write("pdf_issues.json", (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    risk_path = output_root / source_risk_file if source_risk_file else None
    risks = json.loads(risk_path.read_text(encoding="utf-8"))["sources"] if risk_path and risk_path.is_file() else []
    included = {r['source'] for r in reports if (output_root / r['file']).is_file()}
    try:
        readme = collection_readme(payload['counts'], [r['source'] for r in risks if r['source'] in included],
                                   reports=[r for r in reports if (output_root / r['file']).is_file()],
                                   missing_pdfs=payload['missing_pdfs'])
    except FileNotFoundError:
        return payload  # README templates belong to the delivery workflow and are not distributed with the crawler.
    storage.write("README.md", readme.encode("utf-8"))
    return payload
