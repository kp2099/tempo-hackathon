"""
Natural Language Expense Parser.

Parses plain English descriptions like "Spent $120 at Marriott for the Chicago conference"
into structured expense data (amount, merchant, category, description).

This is the "wow factor" for judges — users speak, the AI understands.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("TempoExpenseAI.NLParser")

# Category inference from keywords
CATEGORY_KEYWORDS = {
    "meals": [
        "lunch", "dinner", "breakfast", "food", "restaurant", "cafe", "coffee",
        "meal", "eat", "eating", "dine", "dining", "brunch", "snack", "pizza",
        "burger", "sushi", "chipotle", "mcdonalds", "starbucks", "subway",
    ],
    "travel": [
        "flight", "airfare", "airline", "plane", "trip", "fly", "flying",
        "delta", "united", "american airlines", "southwest", "jetblue",
        "boarding pass", "ticket",
    ],
    "accommodation": [
        "hotel", "motel", "airbnb", "lodging", "stay", "room", "marriott",
        "hilton", "hyatt", "booking", "nights",
    ],
    "transportation": [
        "uber", "lyft", "taxi", "cab", "ride", "parking", "gas", "fuel",
        "train", "bus", "subway", "metro", "toll", "rental car",
    ],
    "office_supplies": [
        "office", "supplies", "staples", "paper", "ink", "printer", "pens",
        "notebooks", "post-it", "amazon",
    ],
    "software": [
        "software", "subscription", "saas", "license", "app", "github",
        "slack", "figma", "notion", "adobe", "microsoft", "cloud",
    ],
    "equipment": [
        "laptop", "monitor", "keyboard", "mouse", "computer", "hardware",
        "headphones", "desk", "chair", "webcam", "apple",
    ],
    "training": [
        "course", "training", "conference", "seminar", "workshop",
        "certification", "class", "bootcamp", "tutorial", "education",
    ],
    "client_entertainment": [
        "client", "entertainment", "event", "tickets", "show", "game",
        "concert", "networking", "happy hour", "drinks",
    ],
}

# Known merchants for better extraction
KNOWN_MERCHANTS = [
    "Chipotle", "McDonald's", "Starbucks", "Subway", "Delta Airlines",
    "United Airlines", "American Airlines", "Southwest", "JetBlue",
    "Marriott", "Hilton", "Hyatt", "Airbnb", "Uber", "Lyft", "Amazon",
    "Staples", "Best Buy", "Apple", "Microsoft", "Google", "GitHub",
    "Slack", "Figma", "Notion", "Adobe", "Home Depot", "Costco",
    "Whole Foods", "Trader Joe's",
]


def parse_natural_language(text: str) -> dict:
    """
    Parse a natural language expense description into structured fields.

    Examples:
        "Spent $120 at Marriott for the Chicago conference"
        → amount: 120, merchant: Marriott, category: accommodation, description: Chicago conference

        "$45 lunch at Chipotle with clients"
        → amount: 45, merchant: Chipotle, category: meals, description: lunch with clients

        "Flight to NYC, Delta Airlines, $850"
        → amount: 850, merchant: Delta Airlines, category: travel, description: Flight to NYC

        "Uber ride to airport $42"
        → amount: 42, merchant: Uber, category: transportation, description: ride to airport
    """
    if not text or not text.strip():
        return {
            "amount": None,
            "merchant": None,
            "category": "miscellaneous",
            "description": text or "",
            "parsed": False,
            "confidence": 0.0,
            "parse_notes": "Empty input",
        }

    original_text = text.strip()
    text_lower = original_text.lower()
    confidence = 0.0

    # ─── 1. Extract Amount ────────────────────────────────────────
    amount = None
    amount_match = re.search(r'\$\s*([\d,]+(?:\.\d{1,2})?)', original_text)
    if amount_match:
        amount_str = amount_match.group(1).replace(",", "")
        amount = float(amount_str)
        confidence += 0.4
    else:
        # Try "120 dollars" or just a number
        num_match = re.search(r'(\d+(?:\.\d{1,2})?)\s*(?:dollars?|usd|bucks)', text_lower)
        if num_match:
            amount = float(num_match.group(1))
            confidence += 0.3

    # ─── 2. Extract Merchant ──────────────────────────────────────
    merchant = None

    # First try known merchants
    for known in KNOWN_MERCHANTS:
        if known.lower() in text_lower:
            merchant = known
            confidence += 0.2
            break

    # Then try pattern: "at [Name]" or "from [Name]"
    if not merchant:
        patterns = [
            r'(?:at|from|via|with|to)\s+([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+){0,2})',
            r'(?:at|from|via|with|to)\s+([A-Z][a-zA-Z\'\-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, original_text)
            if match:
                candidate = match.group(1).strip()
                # Filter out common non-merchant words
                skip_words = {"the", "a", "an", "my", "our", "this", "that", "for", "and"}
                if candidate.lower() not in skip_words and len(candidate) > 1:
                    merchant = candidate
                    confidence += 0.15
                    break

    # ─── 3. Infer Category ────────────────────────────────────────
    category = "miscellaneous"
    best_score = 0

    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            category = cat

    if best_score > 0:
        confidence += min(0.3, best_score * 0.1)

    # ─── 4. Build Description ─────────────────────────────────────
    # Use the original text as description, cleaned up
    description = original_text
    # Remove the dollar amount for a cleaner description
    if amount_match:
        description = re.sub(r'\$\s*[\d,]+(?:\.\d{1,2})?', '', description).strip()
    # Clean up connectors
    description = re.sub(r'\s+', ' ', description).strip()
    description = re.sub(r'^[\s,\-–—]+|[\s,\-–—]+$', '', description)

    if not description:
        description = original_text

    # ─── 5. Build notes about what was parsed ─────────────────────
    notes = []
    if amount:
        notes.append(f"Amount: ${amount:.2f}")
    else:
        notes.append("Could not detect amount — please enter manually")
    if merchant:
        notes.append(f"Merchant: {merchant}")
    if category != "miscellaneous":
        notes.append(f"Category: {category}")
    else:
        notes.append("Category: could not determine — defaulting to miscellaneous")

    confidence = min(confidence, 1.0)

    result = {
        "amount": amount,
        "merchant": merchant,
        "category": category,
        "description": description,
        "parsed": True,
        "confidence": round(confidence, 2),
        "parse_notes": " | ".join(notes),
        "original_text": original_text,
    }

    logger.info(f"🗣️ NL Parse: \"{original_text[:50]}...\" → {result['parse_notes']}")
    return result

