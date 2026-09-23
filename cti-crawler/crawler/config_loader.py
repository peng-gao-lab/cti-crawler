from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .registry import adapter_module
from .shared.report_index import REPORT_CLASSES
from .shared.naming import normalize_report_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_ROOT = PROJECT_ROOT / "config"
FETCHERS = {"http", "browser"}


@dataclass(frozen=True)
class SourceConfig:
    name: str
    adapter: str
    adapter_module: str
    base_url: str
    start_urls: tuple[str, ...]
    discovery: str
    content: str
    source_family: str | None = None
    report_class: str | None = None
    classification_basis: str | None = None
    max_reports: int | None = None
    excluded_urls: dict[str, str] = field(default_factory=dict)
    manifest: str | None = None  # absolute path of a local report list for collection adapters (resolved against the config root)


@dataclass(frozen=True)
class CrawlerConfig:
    profile: str
    data_namespace: str
    runtime: dict[str, Any]
    sources: tuple[SourceConfig, ...]
    classification_file: str | None = None
    failure_file: str | None = None
    enabled_source_families: tuple[str, ...] | None = None
    source_risk_file: str | None = None
    source_risk_notices: dict[str, dict[str, Any]] = field(default_factory=dict)


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML: {path}") from error

    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def _load_catalog(config_root: Path, filenames: list[str]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for filename in filenames:
        source_file = config_root / "sources" / filename
        sources = _read_yaml(source_file).get("sources", {})
        if not isinstance(sources, dict):
            raise ValueError(f"Expected 'sources' to be a mapping in {source_file}")

        duplicates = catalog.keys() & sources.keys()
        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise ValueError(f"Duplicate source names: {names}")
        catalog.update(sources)
    return catalog


def _resolve_source(
    name: str, raw: dict[str, Any], default_max_reports: int | None = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
) -> SourceConfig:
    adapter = raw["adapter"]
    start_urls = raw["start_urls"]
    discovery = raw["discovery"]
    content = raw["content"]

    if not isinstance(start_urls, list) or not start_urls:
        raise ValueError(f"Source '{name}' must define at least one start URL")
    if discovery not in FETCHERS or content not in FETCHERS:
        raise ValueError(f"Source '{name}' uses an unknown fetcher")
    report_class = raw.get("report_class")
    if report_class is not None and report_class not in REPORT_CLASSES:
        raise ValueError(f"Source '{name}' uses an unknown report class")
    max_reports = raw.get("max_reports")
    if max_reports is not None and (type(max_reports) is not int or max_reports < 1):
        raise ValueError(f"Source '{name}' max_reports must be a positive integer")
    if max_reports is None:
        max_reports = default_max_reports
    excluded_urls = raw.get("excluded_urls", {})
    if not isinstance(excluded_urls, dict):
        raise ValueError(f"Source '{name}' excluded_urls must map URLs to review reasons")
    for url, reason in excluded_urls.items():
        if (not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"}
                or not urlsplit(url).hostname or not isinstance(reason, str) or not reason.strip()):
            raise ValueError(f"Source '{name}' exclusions require HTTP(S) URLs and nonempty reasons")
    manifest = raw.get("manifest")
    if manifest is not None:
        if not isinstance(manifest, str) or not manifest.strip():
            raise ValueError(f"Source '{name}' manifest must be a path relative to the config directory")
        manifest_path = config_root / manifest
        if not manifest_path.is_file():
            raise ValueError(f"Source '{name}' manifest not found: {manifest_path}")
        manifest = str(manifest_path)

    return SourceConfig(
        name=name,
        adapter=adapter,
        adapter_module=adapter_module(adapter),
        base_url=raw["base_url"],
        start_urls=tuple(start_urls),
        discovery=discovery,
        content=content,
        source_family=raw.get("source_family"),
        report_class=report_class,
        classification_basis=raw.get("classification_basis"),
        max_reports=max_reports,
        excluded_urls={normalize_report_url(url): reason.strip() for url, reason in excluded_urls.items()},
        manifest=manifest,
    )


def load_config(
    profile_name: str | None = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
) -> CrawlerConfig:
    app = _read_yaml(config_root / "app.yaml")
    runtime = _read_yaml(config_root / "runtime.yaml")
    pdf = runtime.setdefault("pdf", {})
    if not isinstance(pdf, dict):
        raise ValueError("pdf must be a mapping")
    for key, default in {"enabled": False, "archive_resources": False, "cleanup_after_success": True}.items():
        if type(pdf.setdefault(key, default)) is not bool:
            raise ValueError(f"pdf.{key} must be a boolean")
    for key, default in {"workers": 1, "resource_workers": 1, "resource_host_concurrency": 2}.items():
        if type(pdf.setdefault(key, default)) is not int or pdf[key] < 1:
            raise ValueError(f"pdf.{key} must be a positive integer")
    interval = pdf.setdefault("resource_host_interval_seconds", 1.0)
    if type(interval) not in {int, float} or not 0 <= interval < float("inf"):
        raise ValueError("pdf.resource_host_interval_seconds must be finite and non-negative")
    concurrency = runtime.setdefault("concurrency", {})
    if not isinstance(concurrency, dict):
        raise ValueError("concurrency must be a mapping")
    for key, default in {"sites": 1, "downloads": 2, "browser_downloads": 1}.items():
        value = concurrency.setdefault(key, default)
        if type(value) is not int or value < 1:
            raise ValueError(f"concurrency.{key} must be a positive integer")
    default_max_reports = runtime.get("default_max_reports")
    if default_max_reports is not None and (
        type(default_max_reports) is not int or default_max_reports < 1
    ):
        raise ValueError("default_max_reports must be a positive integer or null")
    profile_name = profile_name or app.get("default_profile")
    if not profile_name:
        raise ValueError("No profile selected")

    profile_file = config_root / "profiles" / f"{profile_name}.yaml"
    profile = _read_yaml(profile_file)
    if profile.get("name") != profile_name:
        raise ValueError(f"Profile name does not match {profile_file.name}")

    source_files = profile.get("source_files", [])
    enabled_sources = profile.get("enabled_sources", [])
    if not isinstance(source_files, list) or not isinstance(enabled_sources, list):
        raise ValueError(f"Invalid source selection in {profile_file}")

    catalog = _load_catalog(config_root, source_files)
    missing = [name for name in enabled_sources if name not in catalog]
    if missing:
        raise ValueError(f"Unknown sources: {', '.join(missing)}")

    sources = tuple(
        _resolve_source(name, catalog[name], default_max_reports, config_root) for name in enabled_sources
    )
    enabled_families = None
    if "enabled_source_families" in profile:
        families = profile["enabled_source_families"]
        if not isinstance(families, list) or any(not isinstance(f, str) for f in families):
            raise ValueError("enabled_source_families must be a list of source family names")
        known_families = {raw.get("source_family") for raw in catalog.values()}
        unknown = set(families) - known_families
        if unknown:
            raise ValueError(f"Unknown source families: {', '.join(sorted(unknown))}")
        enabled_families = tuple(families)
        sources = tuple(source for source in sources if source.source_family in enabled_families)
    classification_file = profile.get("classification_file")
    failure_file = profile.get("failure_file")
    if failure_file:
        if not isinstance(failure_file, str) or Path(failure_file).name != failure_file or failure_file in {".", ".."}:
            raise ValueError("failure_file must be a filename within the output namespace")
        if failure_file == classification_file:
            raise ValueError("failure_file and classification_file must be different")
    if classification_file:
        if not isinstance(classification_file, str) or Path(classification_file).name != classification_file:
            raise ValueError("classification_file must be a filename within the output namespace")
        if classification_file in {".", ".."}:
            raise ValueError("classification_file must name a file")
        if any(not source.report_class or not source.source_family or not source.classification_basis for source in sources):
            raise ValueError("Classified sources must define report_class, source_family and classification_basis")
    source_risk_file = profile.get("source_risk_file")
    source_risk_notices = profile.get("source_risk_notices", {})
    if not isinstance(source_risk_notices, dict):
        raise ValueError("source_risk_notices must be a mapping")
    if source_risk_file:
        if (not isinstance(source_risk_file, str) or Path(source_risk_file).name != source_risk_file
                or source_risk_file in {".", "..", classification_file, failure_file}):
            raise ValueError("source_risk_file must be a distinct filename within the output namespace")
    elif source_risk_notices:
        raise ValueError("source_risk_notices requires source_risk_file")
    for name, notice in source_risk_notices.items():
        if (not isinstance(name, str) or not isinstance(notice, dict)
                or not isinstance(notice.get("reason"), str) or not notice["reason"].strip()
                or not isinstance(notice.get("evidence"), list) or not notice["evidence"]
                or any(not isinstance(item, str) or not item.strip() for item in notice["evidence"])):
            raise ValueError("Each source risk notice must have a reason and evidence links")
    return CrawlerConfig(
        profile=profile_name,
        data_namespace=profile.get("data_namespace", profile_name),
        runtime=runtime,
        sources=sources,
        classification_file=classification_file,
        failure_file=failure_file,
        enabled_source_families=enabled_families,
        source_risk_file=source_risk_file,
        source_risk_notices=source_risk_notices,
    )
