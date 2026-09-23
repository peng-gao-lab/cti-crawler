"""Per-invocation diagnostics; collection identity remains the configured paths."""
import json
import logging
import threading
from dataclasses import asdict, replace
from datetime import datetime, timezone

from .storage import FileStorage


COUNTS = ("discovered", "downloaded", "skipped", "excluded", "failed")


class RunRecord:
    def __init__(self, config, sources, output_root, state_root, run_id, stop_event):
        self.storage = FileStorage(output_root / "runs" / run_id.replace(":", "-"))
        self.stop_event = stop_event
        self.lock = threading.Lock()
        self.data = {
            "run_id": run_id, "started_at": run_id, "finished_at": None,
            "status": "running", "exit_code": None,
            "output_directory": str(output_root.resolve()),
            "state_directory": str(state_root.resolve()),
            "config": asdict(replace(config, sources=tuple(sources))),
            "sources": {s.name: {"status": "pending", **dict.fromkeys(COUNTS, 0)} for s in sources},
            "excluded_reports": [],
        }
        self.logger = logging.getLogger("crawler")
        self.level = getattr(logging, config.runtime.get("logging", {}).get("level", "INFO").upper(), logging.INFO)

    def __enter__(self):
        self._write()
        self.handler = logging.FileHandler(self.storage.path("run.log"), encoding="utf-8")
        self.handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        self.previous_level = self.logger.level
        self.logger.setLevel(self.level)
        self.logger.addHandler(self.handler)
        self.logger.info("Run %s started; output=%s; state=%s", self.data["run_id"],
                         self.data["output_directory"], self.data["state_directory"])
        return self

    def add(self, source, counter, count=1):
        with self.lock:
            self.data["sources"][source][counter] += count

    def source_started(self, source):
        with self.lock:
            self.data["sources"][source]["status"] = "running"

    def excluded(self, source, report, reason):
        with self.lock:
            self.data["sources"][source.name]["excluded"] += 1
            self.data["excluded_reports"].append({
                "source": source.name, "url": report.url, "reason": reason,
                "origins": report.metadata(source)["origins"],
            })

    def source_finished(self, source):
        with self.lock:
            stats = self.data["sources"][source]
            stats["status"] = ("interrupted" if self.stop_event.is_set()
                               else "failed" if stats["failed"] else "completed")

    def _write(self):
        self.data["stats"] = {
            key: sum(stats[key] for stats in self.data["sources"].values()) for key in COUNTS
        }
        self.storage.write("run.json", (json.dumps(self.data, ensure_ascii=False, indent=2) + "\n").encode())

    def __exit__(self, exc_type, error, traceback):
        # The crawler has already joined every worker before leaving this context.
        failed = (error is not None or any(s["failed"] for s in self.data["sources"].values())
                  or bool(self.data.get("pdf", {}).get("exit_code")))
        status = "failed" if error is not None else "interrupted" if self.stop_event.is_set() else "failed" if failed else "completed"
        self.data.update(status=status, finished_at=datetime.now(timezone.utc).isoformat(),
                         exit_code=130 if status == "interrupted" else 1 if failed else 0)
        if error is not None:
            self.data["error"] = {"type": exc_type.__name__, "reason": str(error)}
            self.logger.error("Run failed", exc_info=(exc_type, error, traceback))
        for stats in self.data["sources"].values():
            if stats["status"] == "running":
                stats["status"] = status
        try:
            self._write()
            self.logger.info("Run %s finished: %s; %s", self.data["run_id"], status, self.data["stats"])
        finally:
            self.logger.removeHandler(self.handler)
            self.handler.close()
            self.logger.setLevel(self.previous_level)
