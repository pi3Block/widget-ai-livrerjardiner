"""
Tests pour les modèles du module PDF.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from src.pdf.models import (
    PDFRequestBase,
    PDFRequest,
    PDFRequestCreate,
    PDFRequestRead,
    PDFRequestUpdate,
    PDFQuoteUserBase,
    PDFQuoteItemVariantBase,
    PDFQuoteItemBase,
    PDFQuoteDataBase,
    PDFQuoteData,
    PDFQuoteDataCreate,
    PDFQuoteDataRead
)

@pytest.mark.asyncio
async def test_pdf_request_base():
    """Test la création d'un PDFRequestBase."""
    data = {
        "template_name": "test_template",
        "data": {"key": "value"},
        "options": {"option1": "value1"}
    }
    request = PDFRequestBase(**data)
    assert request.template_name == "test_template"
    assert request.data == {"key": "value"}
    assert request.options == {"option1": "value1"}

@pytest.mark.asyncio
async def test_pdf_request_create():
    """Test la création d'un PDFRequestCreate."""
    data = {
        "template_name": "test_template",
        "data": {"key": "value"},
        "options": {"option1": "value1"}
    }
    request = PDFRequestCreate(**data)
    assert request.template_name == "test_template"
    assert request.data == {"key": "value"}
    assert request.options == {"option1": "value1"}

@pytest.mark.asyncio
async def test_pdf_request_read():
    """Test la création d'un PDFRequestRead."""
    data = {
        "template_name": "test_template",
        "data": {"key": "value"},
        "options": {"option1": "value1"},
        "id": 1,
        "user_id": 1,
        "created_at": datetime.utcnow(),
        "status": "pending",
        "file_path": "/path/to/file.pdf",
        "processing_time": 1.5
    }
    request = PDFRequestRead(**data)
    assert request.id == 1
    assert request.user_id == 1
    assert request.status == "pending"
    assert request.file_path == "/path/to/file.pdf"
    assert request.processing_time == 1.5

@pytest.mark.asyncio
async def test_pdf_request_update():
    """Test la création d'un PDFRequestUpdate."""
    data = {
        "template_name": "new_template",
        "status": "completed",
        "file_path": "/new/path/to/file.pdf"
    }
    request = PDFRequestUpdate(**data)
    assert request.template_name == "new_template"
    assert request.status == "completed"
    assert request.file_path == "/new/path/to/file.pdf"
    assert request.data is None
    assert request.options is None

@pytest.mark.asyncio
async def test_pdf_quote_user_base():
    """Test la création d'un PDFQuoteUserBase."""
    data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    user = PDFQuoteUserBase(**data)
    assert user.name == "Test User"
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_pdf_quote_item_variant_base():
    """Test la création d'un PDFQuoteItemVariantBase."""
    data = {
        "name": "Test Variant"
    }
    variant = PDFQuoteItemVariantBase(**data)
    assert variant.name == "Test Variant"

@pytest.mark.asyncio
async def test_pdf_quote_item_base():
    """Test la création d'un PDFQuoteItemBase."""
    data = {
        "variant_sku": "TEST-SKU-123",
        "quantity": 2,
        "price_at_quote": Decimal("19.99")
    }
    item = PDFQuoteItemBase(**data)
    assert item.variant_sku == "TEST-SKU-123"
    assert item.quantity == 2
    assert item.price_at_quote == Decimal("19.99")

@pytest.mark.asyncio
async def test_pdf_quote_data_base():
    """Test la création d'un PDFQuoteDataBase."""
    data = {
        "id": "QUOTE-123",
        "created_at": datetime.utcnow(),
        "total_amount": Decimal("39.98")
    }
    quote = PDFQuoteDataBase(**data)
    assert quote.id == "QUOTE-123"
    assert quote.total_amount == Decimal("39.98")

@pytest.mark.asyncio
async def test_pdf_quote_data_create():
    """Test la création d'un PDFQuoteDataCreate."""
    data = {
        "id": "QUOTE-123",
        "created_at": datetime.utcnow(),
        "total_amount": Decimal("39.98"),
        "user": {
            "name": "Test User",
            "email": "test@example.com"
        },
        "items": [
            {
                "variant_sku": "TEST-SKU-123",
                "quantity": 2,
                "price_at_quote": Decimal("19.99")
            }
        ]
    }
    quote = PDFQuoteDataCreate(**data)
    assert quote.id == "QUOTE-123"
    assert quote.total_amount == Decimal("39.98")
    assert quote.user.name == "Test User"
    assert len(quote.items) == 1
    assert quote.items[0].variant_sku == "TEST-SKU-123" 