# CTI Crawler

This directory contains the crawler, its YAML configuration, and PDF conversion tools.
The [project README](../README.md) covers installation, collection modes, configuration,
usage, outputs, and contributing.

From the repository root, create the complete environment with:

```bash
conda env create -f cti-crawler/environment.yml
conda activate cti-crawler
cd cti-crawler
python -m crawler list --profile apt
python -m crawler run --profile apt
```

Use `--profile cti` for broad CTI collection. Configure source selections in
`config/profiles/` and per-source limits and concurrency in `config/runtime.yaml`.
