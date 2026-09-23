# <div align="center"> :mag: CTI Crawler<div>
<div align="center">
*A fast, reproducible crawler framework for Cyber Threat Intelligence (CTI) reports & threat encyclopedias.*
</div>

<h4 align="center">

<p>
<a href="#sparkles-features">Features</a> |
<a href="#compass-project-layout">Project Layout</a> |
<a href="#mag_right-collection-modes">Collection Modes</a> |
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

> **TL;DR**: CTI-Crawler is designed to fetch threat intelligence reports and threat encyclopedia entries from major CTI platforms.

---

## :sparkles: Features

- **Broad coverage**: 31 CTI report sources, 6 threat encyclopedia sources, and 26 APT sources (25 enabled by default). See the [CTI source list](https://docs.google.com/spreadsheets/d/1VIWT3QJisB2AAREk_5bKXk5R_BTqI9zV/edit?usp=sharing&ouid=105701644494878688467&rtpof=true&sd=true) and [APT source list](https://docs.google.com/spreadsheets/d/1ZB7VIBvCSS6AM_aNxuWB7f7w8wUBT0d5/edit?usp=sharing&ouid=105701644494878688467&rtpof=true&sd=true).
- **Collection modes**: switch between CTI and APT modes, or select individual sources without editing Python code.
- **Resumable runs**: saved articles are skipped before requesting their contents again.
- **HTML and PDF**: convert saved HTML to PDF
- **Modular adapters**: website parsing is separate from shared fetching, storage, state, and PDF conversion.

**What's changed:** the original per-site scripts have been reorganized into a shared crawler framework. APT mode adds MITRE ATT&CK references, publisher APT sections, research sections, and selected report repositories. The command-line interface, YAML profiles, resume state, and optional PDF conversion replace the original entry points and settings.

---

## :compass: Project Layout

```text
cti-crawler/                     # Repository root
├─ README.md
├─ LICENSE
└─ cti-crawler/                 # Run commands from this directory
   ├─ config/
   │  ├─ app.yaml               # Default mode
   │  ├─ runtime.yaml           # Limits, paths, concurrency, HTTP/browser and PDF settings
   │  ├─ profiles/              # CTI and APT source selections
   │  ├─ sources/               # Source URLs, adapters and collection rules
   │  └─ manifests/             # Frozen lists of repository PDFs
   ├─ crawler/
   │  ├─ sites/                 # Website adapters
   │  ├─ collections/           # Manifest-based repository adapters
   │  ├─ shared/                # Fetching, navigation, saving and resume state
   │  └─ pdf/                   # Resource preparation and offline PDF rendering
   ├─ fonts/                   # Bundled PDF fallback fonts and their licenses
   ├─ environment.yml
   ├─ output/                  # Created at runtime. Not committed
   └─ state/                   # Created at runtime. Not committed
```

The two modes keep CTI and APT outputs and resume state separate. Each source uses a shared download pipeline. Website-specific parsing stays in its adapter.

---

## :mag_right: Collection Modes

| Mode | Scope |
| --- | --- |
| `cti` | 37 report and threat encyclopedia sources for CTI research. |
| `apt` | Three source families selected for APT research, with 25 sources enabled by default. |

APT means **Advanced Persistent Threat**, not just groups whose names start with “APT”.

1. **`mitre_references`**: references cited on MITRE ATT&CK Groups pages. Many groups conduct APT activity.
2. **`vendor_apt`**: publisher APT categories, report series, and reviewed publisher selections.
3. **`activity_reports`**: broader research sections and selected PDFs from CyberMonitor and blackorbird report repositories. They include APT reports, other multistep attacks, and general malware research. The repository sources use bundled, commit-pinned lists rather than crawling the entire repositories.

All three families are enabled in APT mode. Recorded Future's broader activity source remains disabled because its tested entry mixed in general product and CTI material. APT mode does not collect CVE/CWE catalogs.

Although the crawler does not guarantee that every article is an APT report, **`vendor_apt`** offers higher-quality APT coverage and is the recommended selection.

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

The original release keeps the layout shown above. Its JSON filename maps are not directly interchangeable with the current crawler's SQLite resume state.

We also release the APT dataset collected by running CTI-Crawler in APT mode. You can download the dataset here: [Hugging Face dataset](https://huggingface.co/datasets/CZLi/apt-reports).

3,051 reports were collected in the released APT dataset: 1,008 from MITRE ATT&CK references, 1,023 from publisher APT sections, and 1,020 from research sections and report repositories. 2,364 of them were saved as HTML and converted to PDF, and 687 were downloaded as PDF, so every report has a PDF.

Here's the structure of the dataset
```
apt_github_distribution_20260922T211548298793Z.zip
├─ 01_MITRE_references/       # Reports cited on MITRE ATT&CK Groups pages.
│  ├─ html/                   # Saved HTML originals, named by article number (000123.html).
│  │  ├─ 000123.html
│  │  └─ ...
│  └─ pdf/                    # PDFs with the same numbers: converted from the HTML, or downloaded as PDF.
│     ├─ 000123.pdf
│     └─ ...
├─ 02_APT_publishers/         # Publisher APT sections and report series, one folder per source.
│  ├─ securelist_apt/
│  │  ├─ html/
│  │  └─ pdf/
│  └─ ...
├─ 03_activity_reports/       # Research sections and selected report repositories, one folder per source.
│  ├─ welivesecurity_activity/
│  │  ├─ html/
│  │  └─ pdf/
│  ├─ cybermonitor_history/   # Repository sources contain PDFs only.
│  │  └─ pdf/
│  └─ ...
├─ README.md                  # Dataset guide: layout, records, and review notes.
├─ classifications.json       # Article URLs, sources, collection categories, and paths.
├─ filename_map.json          # Article numbers with their source, URL, and paths.
├─ source_risks.json          # Source-level review notices.
├─ pdf_issues.json            # PDFs with missing images or other conversion issues.
└─ collection.log             # Packaging time and article counts per source and category.
```

An article available in both formats shares one number and is counted once. See the dataset's README for the review notes and PDF limitations. The [APT source spreadsheet](https://docs.google.com/spreadsheets/d/1ZB7VIBvCSS6AM_aNxuWB7f7w8wUBT0d5/edit?usp=sharing&ouid=105701644494878688467&rtpof=true&sd=true) lists the collection entries and source families.

---

## :rocket: Quick Start

Install [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) or another Conda distribution first. On Linux:

```bash
git clone https://github.com/peng-gao-lab/cti-crawler.git
cd cti-crawler
conda env create -f cti-crawler/environment.yml
conda activate cti-crawler
cd cti-crawler

# Inspect the APT selection without making website requests.
python -m crawler list --profile apt

# Collect the three APT source families, then convert saved HTML to PDF.
python -m crawler run --profile apt
```

The single `conda env create` command installs the Python dependencies, PDF libraries, and base fonts. The default limit is **300 discovered article URLs per source**, including already saved articles. To collect the CTI sources instead, use `python -m crawler run --profile cti`.

Outputs and resume records are written locally. Repeating the same command skips saved articles. Press Ctrl-C once to request an orderly stop.

---

## :wrench: Installation

**Prerequisites**
- **OS**: Linux is the tested platform. Windows users should use WSL2. The crawler uses POSIX file locks.
- **Conda**: `environment.yml` installs Python 3.11, crawler dependencies, Pango, fonts, and the HTML-to-PDF dependencies in `requirements-pdf.txt`.
- **Browser**: HTTP-only sources need no browser. Some CTI sources use Chrome. [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) resolves the driver and can obtain Chrome for Testing when Chrome is absent. Its first use needs network access. Minimal Linux installations may also need Chrome's system libraries. Installing Google Chrome through the distribution's package manager supplies those dependencies.

To update an existing environment, run this from the repository root:

```bash
conda env update -n cti-crawler -f cti-crawler/environment.yml --prune
```

PDF rendering uses [WeasyPrint](https://doc.courtbouillon.org/weasyprint/latest/first_steps.html), not a browser. Conda supplies its native dependencies, and fallback fonts with their licenses are included in `cti-crawler/fonts/`.

---

## :gear: Configuration

All runtime configuration lives in `cti-crawler/config/`. Paths such as `output` and `state` are resolved relative to the inner `cti-crawler/` directory.

| File or directory | Purpose |
| --- | --- |
| `app.yaml` | Default mode when `--profile` is omitted. Currently `cti`. |
| `runtime.yaml` | Shared paths, report limit, concurrency, retries, timeouts, browser settings, and PDF settings. |
| `profiles/cti.yaml`, `profiles/apt.yaml` | Catalogs to load, enabled source IDs, and separate data namespaces. APT also selects source families and includes review notices. |
| `sources/cti.yaml` | CTI source IDs, entry URLs, adapters, and HTTP/browser choices. |
| `sources/apt/*.yaml` | APT catalogs: MITRE, publisher sections, broader research sections, and repository collections. |
| `manifests/apt/*.json` | Frozen repository PDF lists needed by the two collection adapters. These are supplied with the code. |

### 1) Mode and source selection

Each mode is defined by a profile in `config/profiles/` and selected with `--profile cti` or `--profile apt`. Edit `enabled_sources` in that profile to change its selection. In APT mode, the selected sources must also belong to an enabled family:

```yaml
# config/profiles/apt.yaml
enabled_source_families:
  - mitre_references
  - vendor_apt
  - activity_reports
```

Remove a family to disable it. Use `[]` to disable all three. This changes future runs without deleting existing files. `--source` narrows the enabled selection. It cannot activate a source disabled in the mode.

### 2) Collection limits and paths

```yaml
# config/runtime.yaml
output_root: output
state_root: state
default_max_reports: 300
```

The limit applies separately to each source and counts distinct discovered article URLs, including saved ones. It does not promise 300 new downloads because the sources may not have enough data. MITRE reads group pages to merge reference evidence before selecting report URLs.

Each source entry in `config/sources/` can set `max_reports: 50`, for example, to override the global limit. A source-level `null` inherits the global value. A global `null` removes the limit for sources without an override.

### 3) Concurrency and retries

```yaml
# config/runtime.yaml
concurrency:
  sites: 3
  downloads: 2
  browser_downloads: 1
http:
  timeout_seconds: 20
  retries: 3
```

At most `min(sites, selected website groups) × downloads` HTTP article downloads run together: **6** with these defaults. Sources sharing a base hostname run sequentially within one website group. Browser downloads use `browser_downloads` instead. These are task limits, not requests per second. External MITRE references may target other hosts.

`retries: 3` allows three retries after the initial HTTP attempt. HTTP 429 responses trigger backoff. Browser headless mode and navigation timeouts are in the `browser` section of the same file.

### 4) PDF conversion

```yaml
# config/runtime.yaml
pdf:
  enabled: true
  archive_resources: true
  cleanup_after_success: true
  workers: 8
  resource_workers: 4
  resource_host_concurrency: 2
  resource_host_interval_seconds: 1
```

Conversion starts **after collection**. Image preparation can make network requests. PDF rendering itself is offline. Renderer concurrency is `workers`, independent of crawler concurrency. Image requests are limited by both `resource_workers` and the per-host settings.

Set `enabled: false` and keep `archive_resources: true` to prepare images now and render later. Set both to `false` for collection only. Successful conversion normally removes intermediate copies and later clears unused shared images. Set `cleanup_after_success: false` if you want to retain resources for future offline regeneration.

---

## :arrow_forward: Usage

Run these commands from the inner `cti-crawler/` directory after activating the environment.

### A) Inspect or run selected sources

```bash
python -m crawler list --profile cti
python -m crawler list --profile apt

python -m crawler run --profile cti --source krebsonsecurity
python -m crawler run --profile cti --source cloudflare --source webroot
python -m crawler run --profile apt --source securelist_apt --source talos_apt
```

`--source` accepts the IDs shown by `list` and can be repeated. Omit it to run every enabled source in the mode.

### B) Run one APT source family

For publisher APT sources only, set this in `config/profiles/apt.yaml`, then run `python -m crawler run --profile apt`:

```yaml
enabled_source_families: [vendor_apt]
```

Use `[mitre_references]` or `[activity_reports]` for the other families. Sources must also remain listed under `enabled_sources`.

### C) Convert previously collected HTML

```bash
# Offline conversion from resources prepared during collection.
python -m crawler convert-pdf --profile apt --workers 4

# Allow missing images to be fetched, without downloading article pages again.
python -m crawler convert-pdf --profile apt --fetch-resources --workers 4

# Process only one saved source, even if it is now disabled for crawling.
python -m crawler convert-pdf --profile apt --source securelist_apt

# Prepare resources for later offline conversion.
python -m crawler convert-pdf --profile apt --fetch-resources --archive-only
```

Use `--profile cti` for CTI outputs. Conversion skips PDFs whose files and saved status are still current. Failed conversions retry on the next invocation. Native PDFs are kept as downloaded.

### D) Start a separate collection

Change both `output_root` and `state_root` in `runtime.yaml`, or use a separate `data_namespace` in a profile. Keep the old output and matching state together if you want to resume it later. This avoids mixing independent runs.

---

## :package: Outputs & Idempotency

- **CTI originals**: `output/cti/<source>/`.
- **APT originals**: `output/apt/<source>/`. Third-family reports use `output/apt/activity_reports/<source>/`.
- **Derived PDFs**: alongside their HTML originals. APT uses permanent article numbers such as `000123.html` and `000123.pdf`. CTI uses `<original HTML filename>.pdf`.
- **Resume state**: `state/<namespace>/completed.sqlite3`. Identity is the source ID plus URL. This does not deduplicate the same report across sources or URLs.
- **Run records**: `output/<namespace>/runs/<run_id>/` contains run status, source counts, events, and failures.
- **APT indexes**: `classifications.json` links reports to their sources and collection rules. `failures.json` records collection failures. `source_risks.json` contains source-level review notices.
- **PDF records**: `pdf-run.json`, `pdf-events.jsonl`, and per-article status under `.pdf/` describe conversion results. APT's `pdf_issues.json` summarizes missing PDFs, missing images, and text-layer warnings.

Re-run the same command to resume. Saved files are skipped before article requests. Absent or failed downloads are retried when discovered again. A PDF failure does not cause the original HTML to be downloaded again. Keep the output's `.package/` article registry, `.pdf/` status, and matching `state/` directory when moving a working collection.

Only one collection, conversion, or maintenance operation can hold a collection's lock at a time. Ctrl-C stops scheduling new work and waits for active tasks to finish before recording the final status.

---

## :test_tube: Performance & Tips

- Start with a few sources and a smaller `default_max_reports` when checking a new installation.
- Reduce `sites` or `downloads` if publishers rate-limit requests. Raising concurrency does not improve a blocked source.
- Lower `pdf.workers` on machines with limited memory. Resource preparation and rendering have separate limits.
- Source listings change over time. The CTI adapters preserve the original coverage, but that does not guarantee every historical website is still available.
- Do not run two jobs against the same collection directory. Use separate output and state roots for independent work.

---

## :hammer_and_wrench: Troubleshooting & FAQ

**Q: Chrome cannot start or Selenium cannot obtain a driver?**

A: Install Google Chrome with its system dependencies and allow Selenium Manager's initial download. Check `browser` settings and confirm that Chrome can run headlessly on the host. APT's current HTTP-only sources do not require Chrome.

**Q: Getting 403, 429, or an empty listing?**

A: Review the source's run records. Lower concurrency and retry later for rate limits. A moved or retired entry may require an adapter update. Failed downloads are not marked complete.

**Q: Does this crawl images?**

A: Originals are saved first. When resource archiving is enabled, the PDF stage downloads referenced images into local reading copies. It does not revisit article pages or fetch embedded videos. Animated images use their first frame. Dynamic embeds are represented by omission notices.

**Q: Why can a saved HTML report lack a PDF or an image?**

A: Images may be unavailable, and some pages are dynamic shells rather than static reports. The converter checks text and page bounds and records failures or missing-image placeholders. Inspect PDF records rather than treating download success as proof of complete rendering.

**Q: Can I use the old release's JSON maps to resume?**

A: Not directly. This version uses SQLite state and APT article IDs. The original dataset's mapping files use the earlier format.

**Q: Does every report collected in APT mode meet a strict APT definition?**

A: No. Selection follows source sections, citations, and repository lists. Source-level review is not article-level screening. Broader research sections contain non-APT reports too.

---

## :world_map: Roadmap

- Restore Docker support for the modular crawler.
- Maintain source adapters as publisher websites change and expand APT coverage where useful.

---

## :handshake: Contributing

Issues and PRs are welcome!  
For new crawlers:
- Review an existing adapter under `crawler/sites/` or `crawler/collections/`.
- Keep site-specific selectors and navigation in the adapter. Reuse shared downloading, state, numbering, and PDF conversion.
- Add the source entry under `config/sources/` and enable it in the appropriate profile.
- Add a small offline test for the source's parsing or pagination behavior. Keep downloaded data and development records out of commits.

We plan to restore Docker support in a later update. Contributions toward a reproducible container setup are welcome.

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
