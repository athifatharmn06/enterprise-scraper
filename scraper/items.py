import re
import scrapy
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional


class ProductValidator(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    sku: str = Field(min_length=1)
    price: Optional[float] = None
    currency: str = "USD"
    in_stock: bool
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    retailer_name: str
    retailer_domain: str

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v is not None and not (0.0 <= v <= 5.0):
            raise ValueError("Rating must be between 0 and 5")
        return v


class ProductItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()
    sku = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    in_stock = scrapy.Field()
    category = scrapy.Field()
    description = scrapy.Field()
    image_url = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()
    retailer_name = scrapy.Field()
    retailer_domain = scrapy.Field()
