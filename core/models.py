from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Index, BigInteger, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Retailer(Base):
    """Stores information about the store being scraped."""
    __tablename__ = "retailers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="retailer", cascade="all, delete")


class Product(Base):
    """Stores enriched product information."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    retailer_id = Column(Integer, ForeignKey("retailers.id"), nullable=False)
    name = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    sku = Column(String(100), index=True)
    brand = Column(String(100))
    category = Column(String(100), index=True)            # NEW: e.g. "laptops", "tablets"
    description = Column(Text, nullable=True)             # NEW: product description
    image_url = Column(String(1000), nullable=True)       # NEW: product image URL
    rating = Column(Float, nullable=True)                  # NEW: star rating 0.0–5.0
    review_count = Column(Integer, nullable=True)          # NEW: number of reviews
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    retailer = relationship("Retailer", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete")

    __table_args__ = (
        Index('idx_product_retailer_sku', 'retailer_id', 'sku', unique=True),
    )


class PriceHistory(Base):
    """Time-series price tracking data per product."""
    __tablename__ = "price_history"

    id = Column(BigInteger, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")
    in_stock = Column(Boolean, default=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    product = relationship("Product", back_populates="price_history")

    __table_args__ = (
        Index('idx_product_id_scraped_at', 'product_id', 'scraped_at'),
    )
