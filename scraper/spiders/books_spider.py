import re
import scrapy
from scraper.items import ProductItem

# Word-to-number map for CSS star rating class names
STAR_RATING = {
    "One": 1.0, "Two": 2.0, "Three": 3.0, "Four": 4.0, "Five": 5.0
}


class BooksSpider(scrapy.Spider):
    """
    High-volume spider targeting books.toscrape.com.

    A site purpose-built for scraping practice with 1,000 books
    across 50 genres. Uses standard HTTP (no Playwright needed)
    for maximum throughput. Extracts:
      - title, price, currency, in_stock status
      - star rating, category / genre
      - cover image URL
      - per-genre breadcrumb category
    """
    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com/catalogue/page-1.html"]

    custom_settings = {
        # No Playwright needed — this site is static HTML
        "DOWNLOAD_HANDLERS": {},
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "CONCURRENT_REQUESTS": 16,
        "DOWNLOAD_DELAY": 0.25,
    }

    def parse(self, response):
        """Parse a paginated book listing page."""
        books = response.css("article.product_pod")
        self.logger.info(
            f"[BOOKS] {response.url} — {len(books)} books found"
        )

        for book in books:
            item = self._extract_book(book, response)
            if item:
                yield item

        # Follow pagination (50 pages × 20 books = 1,000 total)
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def _extract_book(self, book, response):
        """Extract all available fields from a book card."""
        # Title
        name = book.css("h3 a::attr(title)").get()
        if not name:
            return None

        # Relative URL to book detail page
        link = book.css("h3 a::attr(href)").get()
        if not link:
            return None

        url = response.urljoin(link)
        sku = url.rstrip("/").split("/")[-2]  # slug is second-to-last segment

        # Price — "£12.34" → 12.34 USD equivalent for demo
        raw_price = book.css(".price_color::text").get("").strip()
        price = None
        if raw_price:
            try:
                price = float(re.sub(r"[^\d.]", "", raw_price))
            except ValueError:
                pass

        # Star rating via CSS class name
        rating_class = book.css("p.star-rating::attr(class)").get("")
        rating_word = rating_class.replace("star-rating", "").strip()
        rating = STAR_RATING.get(rating_word)

        # In-stock status
        availability_text = book.css(".availability::text").getall()
        in_stock = "in stock" in " ".join(availability_text).lower()

        # Cover image
        image_url = book.css("img.thumbnail::attr(src)").get()
        if image_url:
            image_url = response.urljoin(image_url)

        # Category from breadcrumb (e.g. "Mystery", "Science Fiction")
        breadcrumb = response.css("ul.breadcrumb li a::text").getall()
        category = breadcrumb[-1].strip().lower() if len(breadcrumb) >= 2 else "books"

        item = ProductItem()
        item["name"] = name.strip()
        item["url"] = url
        item["sku"] = sku
        item["price"] = price
        item["currency"] = "GBP"
        item["in_stock"] = in_stock
        item["category"] = category
        item["description"] = None   # Not on listing page; would need detail request
        item["image_url"] = image_url
        item["rating"] = rating
        item["review_count"] = None
        item["retailer_name"] = "Books to Scrape"
        item["retailer_domain"] = "books.toscrape.com"
        return item
