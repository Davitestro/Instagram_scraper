# Instagram Scraper

A lightweight Instagram scraping utility for collecting posts, media and comments from search results or specific profiles.

Features
- Search-based scraping (keywords)
- Media and comments export
- CSV and JSON exporters (see `output/`)

Requirements

- Python 3.10+
- See `requirements.txt` for exact dependencies

Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Basic usage

- Run the main scraper:

```bash
python main.py
```

- Run the search scraper (example):

```bash
python search_scraper.py --keywords keywords.txt
```

Output

Scraped CSV and JSON files are written to the `output/` folder (see `output/csv/` and `output/json/`).

Contributing

Feel free to open issues or submit PRs. Update `keywords.txt` to add search terms.

License

This project is licensed under the MIT License — see the `LICENSE` file.
