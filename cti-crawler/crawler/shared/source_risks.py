"""Source-level review guidance, separate from article classifications and failures."""
import json

from .storage import FileStorage


def export_source_risks(config, sources, output_root, run_id):
    selected = {source.name for source in sources}
    # Export the whole configured register, including sources not selected this run.
    # A partial/resume run must not hide guidance needed for earlier collected files.
    payload = {
        "profile": config.profile,
        "run_id": run_id,
        "scope": "Source review guidance; not article judgments or measured contamination rates.",
        "sources": [
            {**notice, "source": name, "selected_this_run": name in selected}
            for name, notice in sorted(config.source_risk_notices.items())
        ],
    }
    FileStorage(output_root).write(
        config.source_risk_file,
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
