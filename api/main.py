from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.models import Product, PriceHistory, Retailer
from worker.tasks import trigger_ecommerce_scrape, trigger_books_scrape, trigger_full_scrape


app = FastAPI(
    title="Enterprise Scraper API",
    description=(
        "Distributed Price Intelligence API. "
        "Triggers Scrapy/Playwright crawls via Celery and serves time-series price data from PostgreSQL."
    ),
    version="2.0.0"
)


@app.get("/")
def read_root():
    return {"status": "Online", "service": "Enterprise Scraper API", "version": "2.0.0"}


@app.post("/scrape/trigger", tags=["scraping"])
def trigger_scrape():
    """Dispatch an async Celery task to scrape the e-commerce (webscraper.io) spider."""
    task = trigger_ecommerce_scrape.delay()
    return {"message": "E-commerce scraping task queued.", "task_id": str(task.id)}


@app.post("/scrape/trigger/books", tags=["scraping"])
def trigger_books():
    """Dispatch an async Celery task to scrape books.toscrape.com (1,000 books)."""
    task = trigger_books_scrape.delay()
    return {"message": "Books scraping task queued.", "task_id": str(task.id)}


@app.post("/scrape/trigger/all", tags=["scraping"])
def trigger_all():
    """Dispatch an async Celery task to run ALL spiders for maximum data volume."""
    task = trigger_full_scrape.delay()
    return {"message": "Full pipeline scrape queued.", "task_id": str(task.id)}


@app.get("/api/v1/products", tags=["products"])
def get_products(
    skip: int = 0,
    limit: int = 100,
    category: str | None = None,
    db: Session = Depends(get_db)
):
    """
    List all tracked products with enriched metadata.
    Filter by category (e.g. laptops, tablets, phones).
    """
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.id).offset(skip).limit(limit).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "category": p.category,
            "brand": p.brand,
            "description": p.description,
            "image_url": p.image_url,
            "rating": p.rating,
            "review_count": p.review_count,
            "url": p.url,
            "retailer": p.retailer.name if p.retailer else None,
        }
        for p in products
    ]


@app.get("/api/v1/products/{product_id}/prices", tags=["prices"])
def get_product_prices(product_id: int, db: Session = Depends(get_db)):
    """Return full time-series price history for a product, newest first."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    prices = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(desc(PriceHistory.scraped_at))
        .all()
    )

    return {
        "product": {"id": product.id, "name": product.name, "sku": product.sku},
        "price_history": [
            {
                "price": p.price,
                "currency": p.currency,
                "in_stock": p.in_stock,
                "scraped_at": p.scraped_at,
            }
            for p in prices
        ],
    }


@app.get("/api/v1/categories", tags=["products"])
def get_categories(db: Session = Depends(get_db)):
    """Return a summary of product counts per category."""
    from sqlalchemy import func
    results = (
        db.query(Product.category, func.count(Product.id).label("count"))
        .group_by(Product.category)
        .all()
    )
    return [{"category": r.category, "product_count": r.count} for r in results]
