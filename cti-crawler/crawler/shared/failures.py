import json
from collections import Counter
from datetime import datetime, timezone

from .storage import FileStorage


def failure_record(source, url, stage, error, origins=()) -> dict:
    response = getattr(error, "response", None)
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "url": url,
        "stage": stage,
        "error_type": type(error).__name__,
        "reason": str(error),
        "http_status": response.status_code if response is not None else None,
        "final_url": response.url if response is not None else None,
        "content_type": response.headers.get("Content-Type") if response is not None else None,
        "redirects": [
            {"url": item.url, "status": item.status_code, "location": item.headers.get("Location")}
            for item in response.history
        ] if response is not None else [],
        "origins": list(origins),
    }


def _stats(records) -> dict:
    return {
        "failure_events": len(records),
        "unique_failed_urls": len({r["url"] for r in records if r["url"]}),
        "by_source": dict(Counter(r["source"] for r in records)),
        "by_stage": dict(Counter(r["stage"] for r in records)),
        "by_error_type": dict(Counter(r["error_type"] for r in records)),
        "by_http_status": dict(Counter(str(r["http_status"]) if r["http_status"] is not None else "unknown" for r in records)),
    }


def export_failures(state, output_root, filename, profile) -> None:
    records = state.failure_records()
    current = [record for record in records if record["run_id"] == state.run_id]
    payload = {
        "profile": profile,
        "stats": _stats(records),
        "latest_run": {"run_id": state.run_id, **_stats(current)},
        "failures": records,
    }
    FileStorage(output_root).write(
        filename, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
