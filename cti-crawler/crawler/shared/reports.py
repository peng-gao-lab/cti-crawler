"""Article records shared by discovery, persistence and exports."""
from dataclasses import dataclass, field


@dataclass
class Report:
    url: str
    origins: list[dict] = field(default_factory=list)

    def metadata(self, source) -> dict:
        defaults = {
            "source": source.name,
            "source_family": source.source_family,
            "classification_basis": source.classification_basis,
        }
        if source.source_family == "activity_reports":
            defaults["review_status"] = "unreviewed"
        return {
            "adapter": source.adapter,
            "class": source.report_class,
            "origins": [{**defaults, **origin} for origin in (self.origins or [{}])],
        }


def merge_report(reports: dict[str, Report], incoming: Report) -> None:
    if incoming.url not in reports:
        reports[incoming.url] = Report(incoming.url, list(incoming.origins))
    else:
        origins = reports[incoming.url].origins
        for origin in incoming.origins:
            if origin not in origins:
                origins.append(origin)


def merge_metadata(previous: dict, incoming: dict) -> dict:
    merged = {**previous, **incoming}
    origins = list(previous.get("origins", []))
    for origin in incoming.get("origins", []):
        if origin not in origins:
            origins.append(origin)
    merged["origins"] = origins
    if "explicit_apt" in {previous.get("class"), incoming.get("class")}:
        merged["class"] = "explicit_apt"
    return merged

