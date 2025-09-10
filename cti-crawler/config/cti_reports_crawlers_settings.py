import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

THREAT_REPORT_ROOT_PATH = os.path.join(PROJECT_ROOT, "output/cti_reports/")
URL_TO_FILENAME_MAPS_ROOT_PATH = os.path.join(PROJECT_ROOT, "cti_reports_crawlers/url_to_filename_maps/")

# Threat report urls and report directories
SECURELIST_BASE_URL = "https://securelist.com"
SECURELIST_THREAT_REPORT_BASE_URL = os.path.join(SECURELIST_BASE_URL, "all")
SECURELIST_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "securelist_html")
SECURELIST_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "securelist.json")

ATTCYBERSECURITY_BASE_URL = "https://levelblue.com" #"https://cybersecurity.att.com"
ATTCYBERSECURITY_THREAT_REPORT_BASE_URL = os.path.join(ATTCYBERSECURITY_BASE_URL, "blogs/labs-research")
ATTCYBERSECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "attcybersecurity_html")
ATTCYBERSECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "attcybersecurity.json")

CSOONLINE_BASE_URL = "https://www.csoonline.com"
CSOONLINE_SECURITY_THREAT_REPORT_BASE_URL = os.path.join(CSOONLINE_BASE_URL, "security") #category/security
CSOONLINE_VULERNABILITIES_THREAT_REPORT_BASE_URL = os.path.join(CSOONLINE_BASE_URL, "vulnerabilities")
CSOONLINE_CYBERWARFARE_THREAT_REPORT_BASE_URL = os.path.join(CSOONLINE_BASE_URL, "cyberwarfare")
CSOONLINE_CYBERCRIME_THREAT_REPORT_BASE_URL = os.path.join(CSOONLINE_BASE_URL, "cybercrime") #cyber-crime
CSOONLINE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "csoonline_html")
CSOONLINE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "csoonline.json")

TRENDMICRO_BASE_URL = "https://www.trendmicro.com/en_us/research.html" #"https://blog.trendmicro.com"
TRENDMICRO_THREAT_REPORT_BASE_URL = TRENDMICRO_BASE_URL
TRENDMICRO_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "trendmicro_html")
TRENDMICRO_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trendmicro.json")

TRENDMICROSECURITYINTELLIGENCE_BASE_URL = "https://blog.trendmicro.com"
TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_BASE_URL = os.path.join(TRENDMICRO_BASE_URL,
                                                                     "trendlabs-security-intelligence")
TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "trendmicrosecurityintelligence_html")
TRENDMICROSECURITYINTELLIGENCE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trendmicrosecurityintelligence.json")

CLOUDFLARE_BASE_URL = "https://blog.cloudflare.com"
CLOUDFLARE_THREAT_REPORT_BASE_URL = CLOUDFLARE_BASE_URL
CLOUDFLARE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "cloudflare_html")
CLOUDFLARE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "cloudflare.json")

CROWDSTRIKE_BASE_URL = "https://www.crowdstrike.com"
CROWDSTRIKE_THREAT_REPORT_BASE_URL = os.path.join(CROWDSTRIKE_BASE_URL, "en-us/blog") #blog/recent-articles
CROWDSTRIKE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "crowdstrike_html")
CROWDSTRIKE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "crowdstrike.json")

DARKNET_BASE_URL = "https://www.darknet.org.uk"
DARKNET_THREAT_REPORT_BASE_URL = DARKNET_BASE_URL
DARKNET_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "darknet_html")
DARKNET_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "darknet.json")

# FIREEYE_BASE_URL = "ttps://www.fireeye.com" 
# FIREEYE_THREAT_REPORT_BASE_URL = os.path.join(FIREEYE_BASE_URL, "blog/threat-research")
# FIREEYE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "fireeye_html")
# FIREEYE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "fireeye.json")

Trellix_BASE_URL = "https://www.trellix.com"
Trellix_THREAT_REPORT_BASE_URL = os.path.join(Trellix_BASE_URL, "blogs/research/") #content/mainsite/en-us/blogs/research.blogs-topic-listing.json
Trellix_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "trellix_html")
Trellix_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trellix.json")

FORCEPOINT_BASE_URL = "https://www.forcepoint.com"
FORCEPOINT_THREAT_REPORT_BASE_URL = os.path.join(FORCEPOINT_BASE_URL, "blog")
FORCEPOINT_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "forcepoint_html")
FORCEPOINT_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "forcepoint.json")

HOTFORSECURITY_BASE_URL = "https://www.bitdefender.com" #"https://hotforsecurity.bitdefender.com"
HOTFORSECURITY_THREAT_REPORT_BASE_URL = os.path.join(HOTFORSECURITY_BASE_URL, "en-us/blog/hotforsecurity/tag/industry-news") #HOTFORSECURITY_BASE_URL
HOTFORSECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "hotforsecurity_html")
HOTFORSECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "hotforsecurity.json")

KASPERSKYDAILY_BASE_URL = "https://www.kaspersky.com"
KASPERSKYDAILY_THREAT_REPORT_BASE_URL = os.path.join(KASPERSKYDAILY_BASE_URL, "blog/all-posts")
KASPERSKYDAILY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "kasperskydaily_html")
KASPERSKYDAILY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "kasperskydaily.json")

KREBSONSECURITY_BASE_URL = "https://krebsonsecurity.com"
KREBSONSECURITY_THREAT_REPORT_BASE_URL = KREBSONSECURITY_BASE_URL
KREBSONSECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "krebsonsecurity_html")
KREBSONSECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "krebsonsecurity.json")

MALWAREBYTES_BASE_URL = "https://www.malwarebytes.com/blog" #"https://blog.malwarebytes.com"
MALWAREBYTES_THREAT_REPORT_BASE_URL = MALWAREBYTES_BASE_URL
MALWAREBYTES_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "malwarebytes_html")
MALWAREBYTES_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "malwarebytes.json")

MCAFEE_BASE_URL = "https://www.mcafee.com"
MCAFEE_THREAT_REPORT_BASE_URL = os.path.join(MCAFEE_BASE_URL, "blogs") 
MCAFEE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "mcafee_html")
MCAFEE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "mcafee.json")

NAKEDSECURITY_BASE_URL = "https://news.sophos.com/en-us" #"https://nakedsecurity.sophos.com"
NAKEDSECURITY_THREAT_REPORT_BASE_URL = os.path.join(NAKEDSECURITY_BASE_URL, "category/serious-security/") #NAKEDSECURITY_BASE_URL
NAKEDSECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "nakedsecurity_html")
NAKEDSECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "nakedsecurity.json")

NCCGROUP_BASE_URL = "https://www.nccgroup.com" #"https://research.nccgroup.com"
NCCGROUP_THREAT_REPORT_BASE_URL = os.path.join(NCCGROUP_BASE_URL, "research-blog") #archive/page
NCCGROUP_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "nccgroup_html")
NCCGROUP_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "nccgroup.json")

CISCOUMBRELLA_BASE_URL = "https://umbrella.cisco.com"
CISCOUMBRELLA_THREAT_REPORT_BASE_URL = os.path.join(CISCOUMBRELLA_BASE_URL, "blog")
CISCOUMBRELLA_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "ciscoumbrella_html")
CISCOUMBRELLA_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "ciscoumbrella.json")

RECORDEDFUTURE_BASE_URL = "https://www.recordedfuture.com"
RECORDEDFUTURE_THREAT_REPORT_BASE_URL = os.path.join(RECORDEDFUTURE_BASE_URL, "query-index.json") #blog
RECORDEDFUTURE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "recordedfuture_html")
RECORDEDFUTURE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "recordedfuture.json")

RSA_BASE_URL = "https://www.rsa.com"
RSA_THREAT_REPORT_BASE_URL = os.path.join(RSA_BASE_URL, "resources/blog/") #en-us/blog
RSA_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "rsa_html")
RSA_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "rsa.json")

SHNEIERONSECURITY_BASE_URL = "https://www.schneier.com"
SHNEIERONSECURITY_THREAT_REPORT_BASE_URL = SHNEIERONSECURITY_BASE_URL
SHNEIERONSECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "shneieronsecurity_html")
SHNEIERONSECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "shneieronsecurity.json")

SOPHOS_BASE_URL = "https://news.sophos.com"
SOPHOS_THREAT_REPORT_BASE_URL = os.path.join(SOPHOS_BASE_URL, "en-us")
SOPHOS_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "sophos_html")
SOPHOS_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "sophos.json")

SYMANTECTHREATINTELLIGENCE_BASE_URL = "https://www.security.com" #"https://symantec-enterprise-blogs.security.com/blogs/threat-intelligence/"
SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_BASE_URL = os.path.join(SYMANTECTHREATINTELLIGENCE_BASE_URL,"threat-intelligence")
SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "symantecthreatintelligence_html")
SYMANTECTHREATINTELLIGENCE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "symantecthreatintelligence.json")

THREATPOST_BASE_URL = "https://threatpost.com/"
THREATPOST_THREAT_REPORT_BASE_URL = THREATPOST_BASE_URL
THREATPOST_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "threatpost_html")
THREATPOST_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "threatpost.json")

WEBROOT_BASE_URL = "https://www.webroot.com"
WEBROOT_THREAT_REPORT_BASE_URL = os.path.join(WEBROOT_BASE_URL, "blog")
WEBROOT_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "webroot_html")
WEBROOT_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "webroot.json")

WELIVESECURITY_BASE_URL = "https://www.welivesecurity.com"
WELIVESECURITY_THREAT_REPORT_BASE_URL = os.path.join(WELIVESECURITY_BASE_URL,"en")
WELIVESECURITY_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "welivesecurity_html")
WELIVESECURITY_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "welivesecurity.json")

ZSCALER_BASE_URL = "https://www.zscaler.com/blogs"
ZSCALER_THREAT_REPORT_BASE_URL = ZSCALER_BASE_URL + "?type=security-research" #os.path.join(ZSCALER_BASE_URL, "blogs", "security-research")
ZSCALER_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "zscaler_html")
ZSCALER_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "zscaler.json")

PALOALTO_BASE_URL = "https://www.paloaltonetworks.com/blog/"
PALOALTO_THREAT_REPORT_BASE_URL = PALOALTO_BASE_URL
PALOALTO_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "paloalto_html")
PALOALTO_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "paloalto.json")

UNIT42_PALOALTO_BASE_URL = "https://unit42.paloaltonetworks.com/" #"https://unit42.paloaltonetworks.com/"
UNIT42_PALOALTO_THREAT_REPORT_BASE_URL = os.path.join(UNIT42_PALOALTO_BASE_URL, "unit-42-all-articles/")
UNIT42_PALOALTO_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "unit42_paloalto_html")
UNIT42_PALOALTO_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "unit42_paloalto.json")

TRUSTWAVE_BASE_URL = "https://www.trustwave.com"
TRUSTWAVE_THREAT_REPORT_BASE_URL = os.path.join(TRUSTWAVE_BASE_URL, "en-us/resources/blogs/trustwave-blog")
TRUSTWAVE_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "trustwave_html")
TRUSTWAVE_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "trustwave.json")

SPIDERLABS_BASE_URL = "https://www.trustwave.com"
SPIDERLABS_THREAT_REPORT_BASE_URL = os.path.join(SPIDERLABS_BASE_URL, "en-us/resources/blogs/spiderlabs-blog")
SPIDERLABS_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "spiderlabs_html")
SPIDERLABS_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "spiderlabs.json")

THEHACKERNEWS_BASE_URL = "https://thehackernews.com"
THEHACKERNEWS_THREAT_REPORT_BASE_URL = THEHACKERNEWS_BASE_URL
THEHACKERNEWS_THREAT_REPORT_DIR = os.path.join(THREAT_REPORT_ROOT_PATH, "thehackernews_html")
THEHACKERNEWS_URL_TO_FILENAME_MAP_PATH = os.path.join(URL_TO_FILENAME_MAPS_ROOT_PATH, "thehackernews.json")
