"""Adapter registry: source ID -> module. Each module defines a class `Adapter`.

Adapter contract (duck-typed; the core probes the optional hooks with getattr):
  Adapter(source, fetchers, stop_event)          required constructor
  discover() -> iterable[Report]                required; yields report URLs with origins
  fetch_content(url) -> FetchedDocument          optional; replaces the default HTTP download of an article
  pdf_content_selectors(url) -> tuple[str, ...]  optional; CSS selectors of the sections printed to PDF
  request_headers() -> dict                      optional; extra HTTP headers for this site's image requests
"""
import importlib


ADAPTER_MODULES = {
    "attcybersecurity": "crawler.sites.attcybersecurity",
    "blackorbird_reports": "crawler.collections.blackorbird_reports",
    "bitdefender_apt": "crawler.sites.bitdefender_apt",
    "ciscoumbrella": "crawler.sites.ciscoumbrella",
    "ciscoumbrella_activity": "crawler.sites.ciscoumbrella_activity",
    "cloudflare": "crawler.sites.cloudflare",
    "crowdstrike": "crawler.sites.crowdstrike",
    "csoonline": "crawler.sites.csoonline",
    "cybermonitor_history": "crawler.collections.cybermonitor_history",
    "darknet": "crawler.sites.darknet",
    "eset_apt_reports": "crawler.sites.eset_apt_reports",
    "forcepoint": "crawler.sites.forcepoint",
    "groupib_apt": "crawler.sites.groupib_apt",
    "fsecure_encyclopedia": "crawler.sites.fsecure_encyclopedia",
    "hotforsecurity": "crawler.sites.hotforsecurity",
    "kasperskydaily": "crawler.sites.kasperskydaily",
    "kaspersky_encyclopedia": "crawler.sites.kaspersky_encyclopedia",
    "krebsonsecurity": "crawler.sites.krebsonsecurity",
    "malwarebytes_encyclopedia": "crawler.sites.malwarebytes_encyclopedia",
    "malwarebytes_reports": "crawler.sites.malwarebytes_reports",
    "mcafee": "crawler.sites.mcafee",
    "mitre_attack": "crawler.sites.mitre_attack",
    "nccgroup": "crawler.sites.nccgroup",
    "paloalto": "crawler.sites.paloalto",
    "recordedfuture": "crawler.sites.recordedfuture",
    "rsa": "crawler.sites.rsa",
    "schneier_on_security": "crawler.sites.schneier_on_security",
    "securelist": "crawler.sites.securelist",
    "certua_apt": "crawler.sites.certua_apt",
    "seqrite_activity": "crawler.sites.seqrite_activity",
    "sekoia_apt": "crawler.sites.sekoia_apt",
    "microsoft_apt": "crawler.sites.microsoft_apt",
    "asec_apt": "crawler.sites.asec_apt",
    "sentinellabs_apt": "crawler.sites.sentinellabs_apt",
    "sophos": "crawler.sites.sophos",
    "talos_apt": "crawler.sites.talos_apt",
    "sophos_pacific_rim": "crawler.sites.sophos_pacific_rim",
    "symantec_encyclopedia": "crawler.sites.symantec_encyclopedia",
    "symantec_threat_intelligence": "crawler.sites.symantec_threat_intelligence",
    "thehackernews": "crawler.sites.thehackernews",
    "threatpost": "crawler.sites.threatpost",
    "trellix": "crawler.sites.trellix",
    "trendmicro": "crawler.sites.trendmicro",
    "trendmicro_apt": "crawler.sites.trendmicro_apt",
    "trendmicro_encyclopedia": "crawler.sites.trendmicro_encyclopedia",
    "trendmicro_security_intelligence": "crawler.sites.trendmicro_security_intelligence",
    "trustwave": "crawler.sites.trustwave",
    "unit42": "crawler.sites.unit42",
    "unit42_apt": "crawler.sites.unit42_apt",
    "webroot": "crawler.sites.webroot",
    "volexity_apt": "crawler.sites.volexity_apt",
    "welivesecurity": "crawler.sites.welivesecurity",
    "zscaler": "crawler.sites.zscaler",
}


def adapter_module(name: str) -> str:
    try:
        return ADAPTER_MODULES[name]
    except KeyError as error:
        raise ValueError(f"Unknown adapter: {name}") from error


def load_adapter(name: str):
    module_name = adapter_module(name)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            raise ValueError(f"Adapter is not implemented yet: {name}") from error
        raise

    try:
        return module.Adapter
    except AttributeError as error:
        raise ValueError(f"Adapter module has no Adapter class: {module_name}") from error
