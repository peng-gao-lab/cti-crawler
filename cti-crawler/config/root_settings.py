import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

HEADERS = {
    # "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,
    # application/signed-exchange;v=b3;q=0.9", "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/83.0.4103.116 Safari/537.36"
}

TEST_LIMIT = 2

CTI_REPORTS_CRAWLERS_DIR = f"{PROJECT_ROOT}/cti_reports_crawlers/"
CTI_REPORTS_CRAWLERS_MODULE_PATH = "cti_reports_crawlers."

THREAT_ENCYCLOPEDIAS_CRAWLER_DIR = f"{PROJECT_ROOT}/threat_encyclopedia_crawlers/"
THREAT_ENCYCLOPEDIAS_CRAWLERS_MODULE_PATH = "threat_encyclopedia_crawlers."

NUM_THREADS_MAIN_DRIVER_FUNCTION = 5
NUM_THREADS_DOWNLOAD_HTML = 10

DAILY_DIFFS_PATH = "daily_diffs.json"
COMPUTE_DAILY_DIFFS_FILE_PATH = "utils.compute_daily_diffs"

in_docker_container = bool(os.environ.get('IN_DOCKER_CONTAINER', False))

if in_docker_container:
    # Docker container uses Ubuntu
    chromedriver_name = "chromedriver_v138_linux" #"chromedriver_v84_linux"
else:
    # Change this based on local operating system
    # For MAC - use chromedriver_v84_mac
    # For Linux - use chromedriver_v84_linux
    # For Windows - use chromedriver.exe
    chromedriver_name = "chromedriver_v138_linux" #"chromedriver_v84_linux"

CHROME_DRIVER_PATH = os.path.join(PROJECT_ROOT, "config/{}".format(chromedriver_name))
    
LOOP_TIME = -1 #24*3600 means execute every 24 hours, -1 means only execute once

#############################################################
# Comment out crawler files that you don't want to run below
#############################################################

cti_blogs = [
    'csoonline.py',
    'paloalto.py',
    'spiderlabs.py',
    'symantec_threat_intel.py',
    'thehackernews.py',
    'threatpost.py',
    'trustwave.py',
    'unit42_paloalto.py', 

    'attcybersecurity.py',
    'ciscoumbrella.py',
    'cloudflare.py',
    'crowdstrike.py',
    'darknet.py',
    #'fireeye.py', #Become trellix
    'trellix.py',
    'forcepoint.py',
    'hotforsecurity.py',
    'kasperskydaily.py',
    'krebsonsecurity.py',
    'malwarebytes.py',
    'mcafee.py',
    'nakedsecurity.py',
    'nccgroup.py',
    'recordedfuture.py',
    'rsa.py',
    'securelist.py',
    'shneier_on_security.py',
    'sophos.py',
    'trendmicro.py',
    #'trendmicro_security_intelligence.py',
    'webroot.py',
    'welivesecurity.py',
    'zscaler.py'

    
]

threat_encyclopedias = [
    # 'symantec_threat.py',
    # 'symantec_vulnerability.py',
    'fsecure_threat.py',
    'malwarebytes.py',
    'trendmicro_malware.py',
    'trendmicro_spam.py',

    # Crawlers that require Selenium to run
    'kaspersky_threat.py',
    'kaspersky_vulnerability.py'
]
