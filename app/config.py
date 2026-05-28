import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EXPORTS_DIR = ROOT / "exports"
LOGS_DIR = ROOT / "logs"
CONFIG_DIR = ROOT / "config"
SEARCHES_FILE = CONFIG_DIR / "searches.yaml"

for d in (DATA_DIR, EXPORTS_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SCORES_FILE = DATA_DIR / "scores.xlsx"
REVIEWS_FILE = DATA_DIR / "reviews.xlsx"
JOBS_FILE = DATA_DIR / "jobs.xlsx"
NEWS_FILE = DATA_DIR / "news.xlsx"

HTTP_TIMEOUT = 10.0
HTTP_RETRIES = 1
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# APIs externas — chaves opcionais via env
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", "").strip()

# Coletores padrão (default analyze). Frágeis movidos para "experimental".
DEFAULT_COLLECTORS = ["cnpj", "site", "pagespeed", "noticias"]
EXPERIMENTAL_COLLECTORS = ["google_maps", "reclame_aqui", "linkedin", "vagas"]
