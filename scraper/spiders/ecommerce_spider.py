import scrapy
from scraper.items import ProductItem


# All product categories available on the test site
CATEGORIES = [
    ("computers/laptops", "laptops"),
    ("computers/tablets", "tablets"),
    ("phones/touch", "touch-phones"),
    ("phones", "phones"),
]

BASE_URL = "https://webscraper.io/test-sites/e-commerce/allinone"


class EcommerceSpider(scrapy.Spider):
    """
    Enterprise-grade Scrapy spider with Playwright rendering.

    Scrapes ALL product categories across ALL paginated pages from
    the webscraper.io e-commerce test site, extracting:
      - name, SKU, URL, category
      - price, currency, in-stock status
      - description, image URL
      - star rating and review count
      - retailer metadata
    """
    name = "ecommerce"
    allowed_domains = ["webscraper.io"]

    def start_requests(self):
        for path, category in CATEGORIES:
            yield scrapy.Request(
                url=f"{BASE_URL}/{path}",
                callback=self.parse,
                errback=self.errback,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "category": category,
                }
            )

    async def parse(self, response):
        """Parse a product listing page and follow pagination."""
        page = response.meta.get("playwright_page")
        category = response.meta.get("category", "unknown")

        if page:
            try:
                await page.wait_for_selector(".thumbnail", timeout=12000)
            except Exception:
                self.logger.warning(f"Timeout waiting for products on {response.url}")
            finally:
                await page.close()

        products = response.css(".thumbnail")
        self.logger.info(
            f"[{category.upper()}] {response.url} — {len(products)} products found"
        )

        for product in products:
            item = self._extract_product(product, response, category)
            if item:
                yield item

        # Follow pagination
        next_page = response.css("a[rel='next']::attr(href)").get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse,
                errback=self.errback,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "category": category,
                }
            )

    def _extract_product(self, product, response, category: str):
        """
        Extract all fields from a single product card.
        Returns a populated ProductItem or None if critical fields are missing.
        """
        # --- Required fields ---
        name = (
            product.css("a.title::attr(title)").get()
            or product.css("a.title::text").get()
            or ""
        ).strip()

        link = product.css("a.title::attr(href)").get()

        if not name or not link:
            self.logger.debug("Skipping product card — missing name or link")
            return None

        url = response.urljoin(link)
        sku = url.rstrip("/").split("/")[-1]

        # --- Price extraction (multiple fallback selectors) ---
        raw_price = (
            product.css("h4.pull-right.price::text").get()
            or product.css(".price::text").get()
            or product.css("h4.price::text").get()
            or ""
        ).strip()

        price = None
        if raw_price:
            try:
                price = float(raw_price.replace("$", "").replace(",", "").strip())
            except ValueError:
                self.logger.debug(f"Could not parse price: {raw_price!r}")

        # --- Description ---
        description = (
            product.css("p.description::text").get()
            or product.css(".description::text").get()
            or ""
        ).strip() or None

        # --- Image URL ---
        image_url = product.css("img.img-responsive::attr(src)").get()
        if image_url:
            image_url = response.urljoin(image_url)

        # --- Star Rating (count filled stars) ---
        rating_stars = product.css("span.ws-icon.ws-icon-star")
        rating = float(len(rating_stars)) if rating_stars else None

        # --- Review count ---
        review_text = (
            product.css("div.ratings p::text").get()
            or product.css(".ratings::text").get()
            or ""
        ).strip()
        review_count = None
        if review_text:
            try:
                review_count = int("".join(filter(str.isdigit, review_text)))
            except ValueError:
                pass

        item = ProductItem()
        item["name"] = name
        item["url"] = url
        item["sku"] = sku
        item["price"] = price
        item["currency"] = "USD"
        item["in_stock"] = True
        item["category"] = category
        item["description"] = description
        item["image_url"] = image_url
        item["rating"] = rating
        item["review_count"] = review_count
        item["retailer_name"] = "WebScraper Test Site"
        item["retailer_domain"] = "webscraper.io"
        return item

    async def errback(self, failure):
        """Clean up Playwright page and log request failures."""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(
            f"[ERRBACK] Request to {failure.request.url} failed: {failure.value}"
        )
