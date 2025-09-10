import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

URL_TO_FILENAME_MAPS_ROOT_PATH = os.path.join(PROJECT_ROOT, "threat_encyclopedia_crawlers/url_to_filename_maps/")

# F-Secure
FSECURE_THREAT_REPORT_BASE_URL = "https://www.f-secure.com"
FSECURE_THREAT_REPORT_URL = os.path.join(FSECURE_THREAT_REPORT_BASE_URL, "v-descs/index.shtml")

FSECURE_THREAT_REPORT_ROOT_DIR = os.path.join(PROJECT_ROOT, "output/threat_encyclopedia_reports")
FSECURE_THREAT_REPORT_DIR = os.path.join(FSECURE_THREAT_REPORT_ROOT_DIR, "fsecure_html")

FSECURE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "fsecure_threats.json")

# Symantec
SYMANTEC_REPORT_BASE_URL = "http://asb-sngweb.symantec.com"
SYMANTEC_THREAT_REPORT_URL = os.path.join(SYMANTEC_REPORT_BASE_URL, "security_response/landing/azlisting.jsp")
SYMANTEC_VULNERABILITIES_REPORT_URL = os.path.join(SYMANTEC_REPORT_BASE_URL, "security_response/landing/vulnerabilities.jsp")

SYMANTEC_REPORT_ROOT_DIR = os.path.join(PROJECT_ROOT, "output/threat_encyclopedia_reports/symantec")
SYMANTEC_THREAT_REPORT_DIR = os.path.join(SYMANTEC_REPORT_ROOT_DIR, "threats_html")
SYMANTEC_VULNERABILITY_REPORT_DIR = os.path.join(SYMANTEC_REPORT_ROOT_DIR, "vulnerabilities_html")

SYMANTEC_VULNERABILITIES_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "symantec_vulnerabilities.json")
SYMANTEC_THREATS_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "symantec_threats.json")


# Trend Micro
TRENDMICRO_THREAT_REPORT_BASE_URL = "https://www.trendmicro.com"
TRENDMICRO_THREAT_REPORT_MALWARE_URL = os.path.join(TRENDMICRO_THREAT_REPORT_BASE_URL, "vinfo/us/threat-encyclopedia/malware") #vinfo/ae/threat-encyclopedia/malware
TRENDMICRO_THREAT_REPORT_SPAM_URL = os.path.join(TRENDMICRO_THREAT_REPORT_BASE_URL, "vinfo/us/threat-encyclopedia/spam")

TRENDMICRO_THREAT_REPORT_ROOT_DIR = os.path.join(PROJECT_ROOT, "output/threat_encyclopedia_reports/trendmicro")
TRENDMICRO_THREAT_REPORT_MALWARE_DIR = os.path.join(TRENDMICRO_THREAT_REPORT_ROOT_DIR, "malware_html")
TRENDMICRO_THREAT_REPORT_SPAM_DIR = os.path.join(TRENDMICRO_THREAT_REPORT_ROOT_DIR, "spam_html")

TRENDMICRO_MALWARE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trendmicro_malware.json")
TRENDMICRO_SPAM_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trendmicro_spam.json")

# Kaspersky
KASPERSKY_THREAT_REPORT_BASE_URL = "https://threats.kaspersky.com/en"
KASPERSKY_THREAT_REPORT_VULNERABILITY_URL = os.path.join(KASPERSKY_THREAT_REPORT_BASE_URL, "vulnerability")
KASPERSKY_THREAT_REPORT_THREAT_URL = os.path.join(KASPERSKY_THREAT_REPORT_BASE_URL, "threat")

KASPERSKY_THREAT_REPORT_ROOT_DIR = os.path.join(PROJECT_ROOT, "output/threat_encyclopedia_reports/kaspersky")
KASPERSKY_THREAT_REPORT_VULNERABILITY_DIR = os.path.join(KASPERSKY_THREAT_REPORT_ROOT_DIR, "vulnerability_html")
KASPERSKY_THREAT_REPORT_THREAT_DIR = os.path.join(KASPERSKY_THREAT_REPORT_ROOT_DIR, "threat_html")

KASPERSKY_VULNERABILITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "kaspersky_vulnerability.json")
KASPERSKY_THREAT_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "kaspersky_threat.json")

# MalwareBytes Labs
MALWAREBYTES_THREAT_REPORT_BASE_URL = "https://www.malwarebytes.com/blog"
MALWAREBYTES_THREAT_REPORT_URL = os.path.join(MALWAREBYTES_THREAT_REPORT_BASE_URL, "all-posts")

MALWAREBYTES_THREAT_REPORT_ROOT_DIR = os.path.join(PROJECT_ROOT, "output/threat_encyclopedia_reports")
MALWAREBYTES_THREAT_REPORT_DIR = os.path.join(MALWAREBYTES_THREAT_REPORT_ROOT_DIR, "malwarebytes_html")

MALWAREBYTES_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "malwarebytes.json")
