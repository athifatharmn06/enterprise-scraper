import logging
import sys
import os
from scrapy.exceptions import DropItem

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import SessionLocal
from core.models import Retailer, Product, PriceHistory
from scraper.items import ProductValidator
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """
    Stage 1: Validate incoming items against the Pydantic schema.
    Drops malformed items with full error logging for observability.
    """

    def process_item(self, item, spider):
        try:
            ProductValidator(**dict(item))
            return item
        except ValidationError as e:
            errors = e.errors()
            spider.logger.warning(
                f"[VALIDATION FAIL] SKU={item.get('sku')} URL={item.get('url')} "
                f"Errors={errors}"
            )
            raise DropItem(f"Validation failed: {errors}")


class PostgresPipeline:
    """
    Stage 2: Upsert enriched product data and append time-series price history
    into PostgreSQL using SQLAlchemy.

    Strategy:
      - Retailer: get or create
      - Product: get or create by (retailer_id, sku); update mutable fields
      - PriceHistory: always insert a new snapshot (idempotent append)
    """

    def open_spider(self, spider):
        self.db = SessionLocal()
        spider.logger.info("[PostgresPipeline] Database session opened.")

    def close_spider(self, spider):
        self.db.close()
        spider.logger.info("[PostgresPipeline] Database session closed.")

    def process_item(self, item, spider):
        try:
            # --- 1. Get or create Retailer ---
            retailer = (
                self.db.query(Retailer)
                .filter_by(domain=item["retailer_domain"])
                .first()
            )
            if not retailer:
                retailer = Retailer(
                    name=item["retailer_name"],
                    domain=item["retailer_domain"]
                )
                self.db.add(retailer)
                self.db.flush()  # Get the ID without full commit

            # --- 2. Upsert Product ---
            product = (
                self.db.query(Product)
                .filter_by(retailer_id=retailer.id, sku=item["sku"])
                .first()
            )

            if not product:
                product = Product(
                    retailer_id=retailer.id,
                    name=item["name"],
                    url=str(item["url"]),
                    sku=item["sku"],
                    category=item.get("category"),
                    description=item.get("description"),
                    image_url=item.get("image_url"),
                    rating=item.get("rating"),
                    review_count=item.get("review_count"),
                )
                self.db.add(product)
                self.db.flush()
            else:
                # Update mutable enriched fields on re-scrape
                product.name = item["name"]
                product.url = str(item["url"])
                product.category = item.get("category") or product.category
                product.description = item.get("description") or product.description
                product.image_url = item.get("image_url") or product.image_url
                product.rating = item.get("rating") if item.get("rating") is not None else product.rating
                product.review_count = item.get("review_count") if item.get("review_count") is not None else product.review_count

            # --- 3. Append PriceHistory snapshot ---
            history = PriceHistory(
                product_id=product.id,
                price=item.get("price"),
                currency=item.get("currency", "USD"),
                in_stock=item.get("in_stock", True),
            )
            self.db.add(history)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            spider.logger.error(
                f"[DB ERROR] Failed to save SKU={item.get('sku')}: {e}"
            )
            raise DropItem(f"Database error: {e}")

        return item
