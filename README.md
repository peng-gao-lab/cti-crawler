# <div align="center"> :mag: CTI Crawler<div>
<div align="center">
*A fast, reproducible crawler framework for Cyber Threat Intelligence (CTI) reports & threat encyclopedias.*
</div>

<h4 align="center">

<p>
<a href="#sparkles-features">Features</a> |
<a href="#compass-project-layout">Project Layout</a> |
<a href="#open_file_folder-released-dataset">Released Dataset</a> |
<a href="#rocket-quick-start">Quick Start</a> |
<a href="#wrench-installation">Installation</a> |
<a href="#gear-configuration">Configuration</a> |
<a href="#arrow_forward-usage">Usage</a> |
<a href="#package-outputs--idempotency">Outputs & Idempotency</a> |
<a href="#test_tube-performance--tips">Performance & Tips</a> |
<a href="#hammer_and_wrench-troubleshooting--faq">Troubleshooting & FAQ</a> |
<a href="#world_map-roadmap">Roadmap</a> |
<a href="#handshake-contributing">Contributing</a> |
<a href="#book-citation">Citation</a> |
<a href="#page_facing_up-license">License</a> |
<a href="#pray-acknowledgements">Acknowledgements</a> |
</p>

</h4>

> **TL;DR**: CTI-Crawler is designed to fetch threat intelligence reports and threat encyclopedia entries (HTML only) from major CTI platforms. It currently includes **31 report crawlers** and **6 encyclopedia crawlers**, works best on **Linux or Docker**.

---

## :sparkles: Features
- **Broad coverage**: 31 CTI report crawlers and 6 threat encyclopedia crawlers. You can check the website list here: [list of security websites](https://docs.google.com/spreadsheets/d/1VIWT3QJisB2AAREk_5bKXk5R_BTqI9zV/edit?usp=sharing&ouid=105701644494878688467&rtpof=true&sd=true).
- **Reproducible runs**: URL-to-file maps ensure already-downloaded HTML is skipped, enabling safe re-runs.  
- **Two modes**: run a single crawler for testing, or run a curated subset / all crawlers at once.  
- **Docker-friendly**: simple `docker compose up -d` to get going on servers.  
- **Config-first**: central settings for crawler folders, concurrency, loop mode, browser paths, and crawler selection.  
- **Proxy support**: optional integration with `proxy_pool` for rate-limit-friendly crawling.

---

## :compass: Project Layout

```
cti-crawler/
├─ config/
│  ├─ root_settings.py                       # Global knobs: paths, threads, loop, browser, selected crawlers.
│  ├─ cti_reports_crawlers_settings/         # Per-site settings for CTI reports.
│  └─ threat_encyclopedia_crawlers_settings/ # Per-site settings for threat encyclopedias.
├─ cti_reports_crawlers/
│  ├─ url_to_filename_maps                   # Record the webpage that was already crawled.
│  └─ ...                                    # Individual report crawlers.
├─ threat_encyclopedia_crawlers/
│  ├─ url_to_filename_maps                   # Record the webpage that was already crawled.
│  └─ ...                                    # Individual encyclopedia crawlers.
├─ output/
│  ├─ cti_reports/                           # HTML outputs for report crawlers.
│  └─ threat_encyclopedia_reports/           # HTML outputs for encyclopedia crawlers.
├─ utils/
│  ├─base_crawler.py
│  ├─scraper.py
│  ├─multithreaded_task_scheduler.py
│  └─...
└─ main.py
```

Each crawler directory contains a `url_to_filename_maps/` folder that records downloaded pages and prevents duplicates during re-runs.

---

## :open_file_folder: Released Dataset

We also release the dataset collected by running CTI-Crawler. You can download the dataset here: [Google Drive link](https://drive.google.com/drive/folders/1ANNYgUyfznJ0cGOE-AQTVUU2o-7p5dlT?usp=drive_link).

129,393 reports were collected in the released dataset.

Here's the structure of the dataset
```
cti-crawler_dataset_20250905-full/
├─ cti_reports/
│  ├─ cti_reports_platform_html/ # This folder contains all the blogs crawled from a CTI report platform.
│  │  ├─ blog_name.html
│  │  └─ ...
│  └─ ...
├─ threat_encyclopedia_reports/
│  ├─ threat_encyclopedia_reports_platform_html/ # This folder contains all the blogs crawled from a CTI threat encyclopedia reports platform.
│  │  ├─ blog_name.html
│  │  └─ ...
│  ├─ threat_encyclopedia_reports_platform/ # Some platforms contains more than one type of reports. In the absence of the _html suffix, it will contain folders named after different categories.
│  │  ├─ type_html/
│  │  │  ├─blog_name.html
│  │  │  └─ ...
│  │  └─ ...
│  └─ ...                                 
├─ report_url_to_filename_maps/ # This folder contains JSON files that store the mapping information of the CTI reports platforms.
│  ├─ cti_reports_platform.json  
│  └─ ...             
└─ threat_url_to_filename_maps/ # This folder contains JSON files that store the mapping information of the threat encyclopedia reports platforms.
   ├─ threat_encyclopedia_reports_platform.json  
   └─ ...    
```

If you want to continue crawling based on this dataset and avoid retrieving duplicate articles, you need to replace the **report\_url\_to\_filename\_maps** and **threat\_url\_to\_filename\_maps** folders with **cti\_reports\_crawlers** and **threat\_encyclopedia\_crawlers** in the crawler, respectively.

---

## :rocket: Quick Start

> The fastest way is **Docker**. Ensure **Docker** and **Docker Compose** are installed.

```bash
git clone https://github.com/peng-gao-lab/cti-dataset.git
cd cti-crawler
```

Start the stack:

```bash
docker-compose build && docker-compose up -d # If the current host is Linux system

# or

docker-compose build ; docker-compose up -d # If the current host is Windows system
```

- `-d` runs containers in the background. Remove it if you want to see live logs.  
- Follow logs at any time:

```bash
docker logs --follow crawlers_crawler_1
```

> A host volume is mounted, so downloaded files inside the container are available on your machine.

---

## :wrench: Installation

Prefer running with Docker. If you need a **local** install (Python 3.8+):

```bash
git clone https://github.com/peng-gao-lab/cti-dataset.git
cd cti-crawler

pip3 install -r requirements.txt
```

**Prerequisites**
- **Python**: 3.8+  
- **OS**: Linux (recommended), Windows, macOS  
- **Browser**: Google Chrome (or Chrome for Testing) + **matching** Chromedriver  
- **Docker**/**Docker Compose** (if using containers)

---

## :gear: Configuration

> You may want to tweak configs before running.

### 1) Browser
Some crawlers require a real browser session.

- Set `CHROME_DRIVER_PATH` in `config/root_settings.py` appropriately for your OS and Chrome version.
- Download a *matching* Chrome/Chromedriver pair (e.g., from Chrome for Testing).
- If you place the browser under `config/`, adjust `chromedriver_name` (or similarly named field) in `config/root_settings.py`.

### 2) Global knobs (`config/root_settings.py`)
This file controls:
- **crawler folder paths**
- **concurrency** (threads for searching & downloading)
- **browser path**
- **loop mode** (run once vs. run in a loop)
- **which crawler scripts to execute**

> Tip: You can comment out entries to run a smaller subset.

### 3) Per-site settings
- `config/cti_reports_crawlers_settings/`  
  Contains all links used by CTI report crawlers and the map path.
- `config/threat_encyclopedia_crawlers_settings/`  
  Similar for threat encyclopedia crawlers.

---

## :arrow_forward: Usage

You can (a) run **one** crawler for testing, or (b) run **many** at once via `root_settings`.

### A) Run a single crawler
```bash
# Example (adjust the file name)
python cti_reports_crawlers/<crawler_name>.py
# or
python threat_encyclopedia_crawlers/<crawler_name>.py
```

- A corresponding folder under `output/cti_reports/` or `output/threat_encyclopedia_reports/` will be created.

**Proxy**  
For testing single crawlers, `with_proxy` is typically `False`.  
If supported by a crawler, you can enable a proxy via the `BaseCrawler` setting (integrates with `proxy_pool`).  
Note: some crawlers always require the browser instead of a simple HTTP client.

### B) Run multiple or all crawlers

**Locally**
```bash
python main.py
```
- `main.py` runs once by default.  
- To run continuously, set `LOOP_TIME` in `config/root_settings.py`.

**Docker**
```bash
docker-compose build && docker-compose up -d #If the current host is Linux system

#or

docker-compose build ; docker-compose up -d #If the current host is Windows system
```

---

## :package: Outputs & Idempotency

- Downloaded HTML files are stored under:
  - `output/cti_reports/`
  - `output/threat_encyclopedia_reports/`
- Each crawler keeps a `url_to_filename_maps/` record to avoid re-downloading the same page.
- **Re-crawling**: simply re-run the crawler; existing HTML files are skipped.  
  To force re-crawl, remove the corresponding mapping entries or delete the target output files.

---

## :test_tube: Performance & Tips

- Increase/decrease the **search/download thread counts** in `root_settings.py` based on your network/CPU.  
- For rate-limited sites, enable **proxies** and/or reduce concurrency. Or you may want to modify the code. 
- Headless browser runs are often more stable on servers (ensure correct Chrome/Chromedriver pairing).

---

## :hammer_and_wrench: Troubleshooting & FAQ

**Q: Chromedriver version error (session not created / cannot find Chrome)?**  
A: Ensure Chrome and Chromedriver **versions match**. Update `CHROME_DRIVER_PATH` and related fields in configs.

**Q: Docker command not found / permission issues?**  
A: Install Docker/Compose; add your user to the `docker` group (Linux); re-login. On macOS/Windows, ensure Docker Desktop is running.

**Q: Getting 403/429 (rate-limited)?**  
A: Enable `with_proxy` (if supported), throttle concurrency, or use loop mode to pace requests.

**Q: Where are my files?**  
A: Check `output/` (host-mounted when using Docker). Logs: `docker logs --follow crawlers_crawler_1`.

**Q: Does this crawl images?**  
A: **No** - only HTML is downloaded. Besides, it does not process HTML format. It just downloads the HTML file.

---

## :handshake: Contributing

Issues and PRs are welcome!  
For new crawlers:
- Review existing ones under `cti_reports_crawlers/` or `threat_encyclopedia_crawlers/`.
- Keep outputs consistent and ensure `url_to_filename_maps/` entries are properly maintained.
- Add site-specific configs under the corresponding `config/..._settings/`.

---

## :book: Citation

If you make use of our code or dataset in your research, we would appreciate it if you cite the following papers:

```bibtex
@inproceedings{cheng2025ctinexus,
  title={CTINexus: Automatic Cyber Threat Intelligence Knowledge Graph Construction Using Large Language Models},
  author={Cheng, Yutong and Bajaber, Osama and Tsegai, Saimon Amanuel and Song, Dawn and Gao, Peng},
  booktitle={Proceedings of the IEEE 10th European Symposium on Security and Privacy},
  pages={923--938},
  year={2025},
  series = {EuroS\&P '25}
}
```

```bibtex
@inproceedings{gao2024threatkg,
  title={ThreatKG: An AI-Powered System for Automated Open-Source Cyber Threat Intelligence Gathering and Management},
  author = {Gao, Peng and Liu, Xiaoyuan and Choi, Edward and Ma, Sibo and Yang, Xinyu and Song, Dawn},
  booktitle={Proceedings of the 1st ACM Workshop on Large AI Systems and Models with Privacy and Safety Analysis},
  pages={1--12},
  numpages = {12},
  year = {2024},
  series = {LAMPS '24}
}
```

---
## :page_facing_up: License

The CTI-Crawler is released under the MIT License. By using the crawler, you agree to the terms and conditions of the license.

---

## :pray: Acknowledgements

- CTI report sources: see the maintained list of security websites (Google Sheet).