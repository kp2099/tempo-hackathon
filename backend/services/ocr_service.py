"""
OCR Service — Extracts structured data from receipt images using pytesseract.

Extracted fields:
  - ocr_amount: total amount on the receipt
  - ocr_merchant: merchant/store name
  - ocr_date: date on the receipt
  - ocr_items: list of line items
  - ocr_tax: tax amount
  - ocr_currency: detected currency
  - ocr_receipt_number: receipt/invoice number
  - ocr_confidence: overall OCR confidence (0-1)
  - ocr_raw_text: full extracted text

These fields feed into the ML risk pipeline for cross-validation
against employee-submitted data (amount mismatch, merchant mismatch, etc.)
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional

try:
    import pytesseract
    from PIL import Image, ImageFilter, ImageEnhance
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger("TempoExpenseAI.OCRService")

# Common date formats found on receipts
DATE_PATTERNS = [
    r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',          # MM/DD/YYYY, DD-MM-YYYY
    r'\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b',              # YYYY-MM-DD
    r'\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b',              # January 15, 2026
    r'\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b',                # 15 January 2026
]

# Amount patterns — look for total/subtotal/amount due/balance
TOTAL_PATTERNS = [
    r'(?:total|amount\s*due|balance\s*due|grand\s*total|net\s*total)\s*[:\s]*\$?\s*([\d,]+\.?\d{0,2})',
    r'(?:total)\s*\$?\s*([\d,]+\.\d{2})',
    r'\$\s*([\d,]+\.\d{2})\s*$',  # Amount at end of line
]

SUBTOTAL_PATTERNS = [
    r'(?:subtotal|sub\s*total)\s*[:\s]*\$?\s*([\d,]+\.?\d{0,2})',
]

TAX_PATTERNS = [
    r'(?:tax|hst|gst|vat|sales\s*tax)\s*[:\s]*\$?\s*([\d,]+\.?\d{0,2})',
]

TIP_PATTERNS = [
    r'(?:tip|gratuity)\s*[:\s]*\$?\s*([\d,]+\.?\d{0,2})',
]

CURRENCY_SYMBOLS = {
    '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', 'C$': 'CAD', 'A$': 'AUD',
}

RECEIPT_NUMBER_PATTERNS = [
    r'(?:receipt|invoice|order|check|ref|transaction)\s*#?\s*[:\s]*([A-Za-z0-9\-]{4,20})',
    r'#\s*([A-Za-z0-9\-]{4,20})',
]


def _preprocess_image(image_path: str) -> "Image":
    """
    Preprocess the receipt image for better OCR accuracy.
    - Convert to grayscale
    - Enhance contrast
    - Sharpen
    - Resize if too small
    """
    img = Image.open(image_path)

    # Convert to grayscale
    img = img.convert("L")

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # If image is very small, scale up for better OCR
    w, h = img.size
    if w < 600:
        scale = 600 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return img


def _parse_amount(text: str) -> Optional[float]:
    """Extract a dollar amount from text, handling commas."""
    try:
        cleaned = text.replace(",", "").strip()
        return round(float(cleaned), 2)
    except (ValueError, TypeError):
        return None


def _extract_amounts(raw_text: str) -> dict:
    """Extract total, subtotal, tax, and tip from OCR text."""
    text_lower = raw_text.lower()
    result = {
        "total": None,
        "subtotal": None,
        "tax": None,
        "tip": None,
    }

    # Extract total (try multiple patterns)
    for pattern in TOTAL_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            # Take the largest match as the total (usually the final total)
            amounts = [_parse_amount(m) for m in matches]
            amounts = [a for a in amounts if a is not None and a > 0]
            if amounts:
                result["total"] = max(amounts)
                break

    # Extract subtotal
    for pattern in SUBTOTAL_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            result["subtotal"] = _parse_amount(match.group(1))
            break

    # Extract tax
    for pattern in TAX_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            result["tax"] = _parse_amount(match.group(1))
            break

    # Extract tip
    for pattern in TIP_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            result["tip"] = _parse_amount(match.group(1))
            break

    # If no explicit total found, try to find the largest dollar amount
    if result["total"] is None:
        all_amounts = re.findall(r'\$\s*([\d,]+\.\d{2})', raw_text)
        parsed = [_parse_amount(a) for a in all_amounts]
        parsed = [a for a in parsed if a is not None and a > 0]
        if parsed:
            result["total"] = max(parsed)

    return result


def _extract_merchant(raw_text: str) -> Optional[str]:
    """
    Extract merchant name from receipt.
    Usually the first 1-3 lines of a receipt contain the store name.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    if not lines:
        return None

    # The merchant name is typically in the first few non-empty lines
    # Skip lines that look like addresses, phone numbers, dates
    for line in lines[:5]:
        # Skip lines that are just numbers, dates, or too short
        if len(line) < 3:
            continue
        if re.match(r'^[\d\s\-\(\)\+\.]+$', line):  # Just numbers (phone)
            continue
        if re.match(r'^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', line):  # Date
            continue
        if re.match(r'^\d+\s+\w+\s+(st|ave|rd|blvd|dr|ln|ct)', line, re.I):  # Address
            continue

        # Clean up and return as merchant
        merchant = line.strip()
        # Capitalize nicely
        if merchant.isupper() and len(merchant) > 3:
            merchant = merchant.title()
        return merchant[:100]  # Cap length

    return None


def _extract_date(raw_text: str) -> Optional[str]:
    """Extract date from receipt text."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, raw_text)
        if match:
            date_str = match.group(1)
            # Try to parse into a standard format
            for fmt in [
                "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y",
                "%m-%d-%Y", "%m-%d-%y", "%d-%m-%Y",
                "%Y-%m-%d", "%Y/%m/%d",
                "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y",
                "%d %B %Y", "%d %b %Y",
                "%m.%d.%Y", "%d.%m.%Y",
            ]:
                try:
                    parsed = datetime.strptime(date_str.strip(), fmt)
                    return parsed.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # Return raw string if no format matches
            return date_str
    return None


def _extract_currency(raw_text: str) -> str:
    """Detect currency from receipt text."""
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in raw_text:
            return code
    return "USD"  # Default


def _extract_receipt_number(raw_text: str) -> Optional[str]:
    """Extract receipt/invoice number."""
    text_lower = raw_text.lower()
    for pattern in RECEIPT_NUMBER_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1).strip().upper()
    return None


def _extract_line_items(raw_text: str) -> list:
    """
    Extract line items from receipt.
    Look for patterns like: "Item Name    $XX.XX" or "Item Name  XX.XX"
    """
    items = []
    lines = raw_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match: text followed by a price
        match = re.match(r'^(.+?)\s{2,}\$?\s*([\d,]+\.\d{2})\s*$', line)
        if match:
            item_name = match.group(1).strip()
            item_amount = _parse_amount(match.group(2))

            # Filter out totals/subtotals/tax lines
            if item_amount and not re.search(
                r'(total|subtotal|tax|tip|gratuity|change|balance|visa|mastercard|cash)',
                item_name, re.I
            ):
                items.append({
                    "name": item_name[:100],
                    "amount": item_amount,
                })

    return items[:20]  # Cap at 20 items


def extract_receipt_data(image_path: str) -> dict:
    """
    Main entry point: extract structured data from a receipt image.

    Parameters
    ----------
    image_path : str
        Absolute path to the receipt image file.

    Returns
    -------
    dict with keys:
        ocr_amount, ocr_merchant, ocr_date, ocr_items, ocr_tax,
        ocr_currency, ocr_receipt_number, ocr_confidence, ocr_raw_text,
        ocr_tip, ocr_subtotal, ocr_item_count, ocr_success
    """
    if not OCR_AVAILABLE:
        logger.warning("⚠️ pytesseract/Pillow not installed — OCR disabled")
        return _empty_result("OCR libraries not available")

    if not os.path.exists(image_path):
        logger.warning(f"⚠️ Receipt file not found: {image_path}")
        return _empty_result("File not found")

    try:
        # Preprocess image
        img = _preprocess_image(image_path)

        # Run OCR with detailed output for confidence scores
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        # Calculate average confidence (excluding -1 which means no text detected)
        confidences = [int(c) for c in ocr_data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / max(len(confidences), 1) / 100.0

        # Get full text
        raw_text = pytesseract.image_to_string(img)

        if not raw_text.strip():
            logger.info("📄 OCR produced no text from receipt")
            return _empty_result("No text detected in image")

        # Extract structured fields
        amounts = _extract_amounts(raw_text)
        merchant = _extract_merchant(raw_text)
        receipt_date = _extract_date(raw_text)
        currency = _extract_currency(raw_text)
        receipt_number = _extract_receipt_number(raw_text)
        line_items = _extract_line_items(raw_text)

        result = {
            "ocr_success": True,
            "ocr_amount": amounts["total"],
            "ocr_subtotal": amounts["subtotal"],
            "ocr_tax": amounts["tax"],
            "ocr_tip": amounts["tip"],
            "ocr_merchant": merchant,
            "ocr_date": receipt_date,
            "ocr_currency": currency,
            "ocr_receipt_number": receipt_number,
            "ocr_items": line_items,
            "ocr_item_count": len(line_items),
            "ocr_confidence": round(avg_confidence, 3),
            "ocr_raw_text": raw_text[:2000],  # Cap at 2KB
        }

        logger.info(
            f"🔍 OCR extracted: amount=${amounts['total']}, "
            f"merchant={merchant}, date={receipt_date}, "
            f"items={len(line_items)}, confidence={avg_confidence:.1%}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ OCR failed: {e}")
        return _empty_result(f"OCR processing error: {str(e)}")


def _empty_result(reason: str = "") -> dict:
    """Return an empty OCR result dict."""
    return {
        "ocr_success": False,
        "ocr_amount": None,
        "ocr_subtotal": None,
        "ocr_tax": None,
        "ocr_tip": None,
        "ocr_merchant": None,
        "ocr_date": None,
        "ocr_currency": None,
        "ocr_receipt_number": None,
        "ocr_items": [],
        "ocr_item_count": 0,
        "ocr_confidence": 0.0,
        "ocr_raw_text": "",
        "ocr_error": reason,
    }


def compute_ocr_features(ocr_data: dict, submitted_data: dict) -> dict:
    """
    Compute fraud-detection features by cross-referencing OCR data
    with employee-submitted data.

    These features feed into the risk scorer and policy engine.

    Parameters
    ----------
    ocr_data : dict from extract_receipt_data()
    submitted_data : dict with keys: amount, merchant, category

    Returns
    -------
    dict of computed features
    """
    features = {
        "ocr_success": ocr_data.get("ocr_success", False),
        "ocr_confidence": ocr_data.get("ocr_confidence", 0.0),
        "ocr_amount": ocr_data.get("ocr_amount"),
        "ocr_merchant": ocr_data.get("ocr_merchant"),
        "ocr_date": ocr_data.get("ocr_date"),
        "amount_mismatch": 0.0,
        "amount_mismatch_flag": False,
        "merchant_mismatch": False,
        "date_gap_days": 0,
        "date_mismatch_flag": False,
        "has_tax": ocr_data.get("ocr_tax") is not None,
        "has_itemization": (ocr_data.get("ocr_item_count", 0) > 0),
        "receipt_quality": ocr_data.get("ocr_confidence", 0.0),
    }

    if not ocr_data.get("ocr_success"):
        return features

    # ─── Amount mismatch ───
    ocr_amount = ocr_data.get("ocr_amount")
    submitted_amount = submitted_data.get("amount", 0)

    if ocr_amount is not None and submitted_amount > 0:
        mismatch_ratio = abs(ocr_amount - submitted_amount) / max(submitted_amount, 0.01)
        features["amount_mismatch"] = round(mismatch_ratio, 4)
        # Flag if more than 15% difference
        features["amount_mismatch_flag"] = mismatch_ratio > 0.15

    # ─── Merchant mismatch ───
    ocr_merchant = (ocr_data.get("ocr_merchant") or "").lower().strip()
    submitted_merchant = (submitted_data.get("merchant") or "").lower().strip()

    if ocr_merchant and submitted_merchant:
        # Simple fuzzy match — check if one contains the other
        if ocr_merchant and submitted_merchant:
            merchant_match = (
                ocr_merchant in submitted_merchant
                or submitted_merchant in ocr_merchant
                or _word_overlap(ocr_merchant, submitted_merchant) >= 0.5
            )
            features["merchant_mismatch"] = not merchant_match

    # ─── Date gap ───
    ocr_date = ocr_data.get("ocr_date")
    if ocr_date:
        try:
            receipt_dt = datetime.strptime(ocr_date, "%Y-%m-%d")
            now = datetime.utcnow()
            gap = abs((now - receipt_dt).days)
            features["date_gap_days"] = gap
            # Flag if receipt is more than 30 days old
            features["date_mismatch_flag"] = gap > 30
        except (ValueError, TypeError):
            pass

    return features


def _word_overlap(text_a: str, text_b: str) -> float:
    """Compute word overlap ratio between two strings."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))
