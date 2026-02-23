import os
import subprocess
import sys
from worker.celery_app import app

os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'scraper.settings')


def _run_spider(spider_name: str) -> subprocess.CompletedProcess:
    """Run a single Scrapy spider by name via the CLI subprocess pattern."""
    return subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", spider_name],
        cwd="/app",
        env={**os.environ, "SCRAPY_SETTINGS_MODULE": "scraper.settings"},
        capture_output=True,
        text=True,
    )


@app.task(bind=True)
def trigger_ecommerce_scrape(self):
    """
    Celery task: runs the e-commerce (webscraper.io) spider.
    Target: ~147 products across laptops, tablets, phones.
    """
    result = _run_spider("ecommerce")
    if result.returncode != 0:
        raise RuntimeError(f"ecommerce spider failed:\n{result.stderr[-2000:]}")
    return "ecommerce scrape completed successfully"


@app.task(bind=True)
def trigger_books_scrape(self):
    """
    Celery task: runs the books (books.toscrape.com) spider.
    Target: 1,000 books across 50 genres.
    """
    result = _run_spider("books")
    if result.returncode != 0:
        raise RuntimeError(f"books spider failed:\n{result.stderr[-2000:]}")
    return "books scrape completed successfully"


@app.task(bind=True)
def trigger_full_scrape(self):
    """
    Celery task: runs ALL spiders sequentially for maximum data volume.
    Total target: 1,147+ unique products, growing price_history on every run.
    """
    results = {}

    for spider_name in ["ecommerce", "books"]:
        result = _run_spider(spider_name)
        status = "success" if result.returncode == 0 else "failed"
        results[spider_name] = status
        if result.returncode != 0:
            # Log but continue — don't abort sibling spider
            print(f"[WARNING] {spider_name} spider failed: {result.stderr[-500:]}")

    return {"message": "Full scrape pipeline completed", "results": results}
