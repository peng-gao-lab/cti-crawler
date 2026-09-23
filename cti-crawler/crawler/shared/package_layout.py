"""Archive layout and the short README shared by exports and packaging."""
from pathlib import Path, PurePosixPath


FAMILY_FOLDERS = {
    "mitre_references": "01_MITRE_references",
    "vendor_apt": "02_APT_publishers",
    "activity_reports": "03_activity_reports",
}


def archive_document_path(source, family, filename):
    if family not in FAMILY_FOLDERS:
        raise ValueError(f"Unknown source family for {source}: {family}")
    if not source or source in {".", ".."} or "/" in source or "\\" in source:
        raise ValueError(f"Invalid source name: {source}")
    name = PurePosixPath(filename)
    if name.name != filename or "\\" in filename:
        raise ValueError(f"Expected a document filename: {filename}")
    kind = "html" if name.suffix.lower() in {".html", ".htm"} else "pdf"
    folder = PurePosixPath(FAMILY_FOLDERS[family])
    if family != "mitre_references":
        folder /= source
    return (folder / kind / filename).as_posix()


TEMPLATES = Path(__file__).resolve().parent / "templates"
AUDIENCES = {
    "delivery": "collection_readme.md",          # wording of the delivered ZIP; edit the file, not this module
    "public": "collection_readme_public.md",     # GitHub/Hugging Face distribution copy
}


def collection_readme(counts, risk_sources, *, reports=(), missing_pdfs=(), audience="delivery"):
    """Render the README shipped with an export or a ZIP from the Markdown template for the audience.

    Templates use plain str.format placeholders; the few sentences that depend on the counts are
    composed here so the template files stay prose that anyone can edit."""
    if audience not in AUDIENCES:
        raise ValueError(f"Unknown README audience: {audience}")
    families = {r["source"]: r.get("source_family") for r in reports}
    vendor_missing = sum(families.get(r["source"]) == "vendor_apt" for r in missing_pdfs)
    if not counts['missing_pdfs']:
        conversion_note = "All HTML reports have corresponding PDFs."
    elif vendor_missing == counts['missing_pdfs']:
        conversion_note = f"Conversion or text/layout validation failed for {vendor_missing} reports in `02_APT_publishers`, so no PDFs were saved for them. Their HTML originals are included."
    else:
        conversion_note = f"Conversion or text/layout validation failed for {counts['missing_pdfs']} HTML reports, so no PDFs were saved for them. Their HTML originals are included."
    activity_count = sum(r.get("source_family") == "activity_reports" for r in reports)
    activity_note = (f"This folder contains {activity_count} reports."
                     if activity_count else "This folder is empty.")
    names = ", ".join(f"`{name}`" for name in sorted(risk_sources))
    risks = (f"`source_risks.json` explains the concerns about {names}, with review results and examples. "
             "The results describe our review samples; the proportion of non-APT reports in this collection has not been measured."
             if names else "No sources in this package are marked in `source_risks.json`.")
    outdated_note = (f" Another {counts['pdfs_needing_reconversion']} PDFs need their conversion status checked."
                     if counts['pdfs_needing_reconversion'] else "")
    text_layer_count = counts.get('pdfs_with_text_layer_issues', 0)
    text_layer_note = (f" {text_layer_count} PDFs display their text correctly but lose a few combining marks of a "
                       "complex script (for example Myanmar medials in a decoy file name) when the text is copied or "
                       "searched. `pdf_issues.json` lists the affected characters and text, and the HTML originals keep them."
                       if text_layer_count else "")
    pdf_issue_note = (f"{counts['pdfs_with_missing_images']} of them are missing one or more images that could not be "
                      "retrieved (placeholders mark the spots)." + text_layer_note + outdated_note)
    context = {**counts, "pdfs_total": counts['native_pdfs'] + counts['derived_pdfs'],
               "conversion_note": conversion_note, "activity_note": activity_note, "risks": risks,
               "outdated_note": outdated_note, "text_layer_note": text_layer_note, "pdf_issue_note": pdf_issue_note}
    template = (TEMPLATES / AUDIENCES[audience]).read_text(encoding="utf-8")
    return template.format_map(context)
