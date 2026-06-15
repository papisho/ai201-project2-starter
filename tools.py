"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query = (description or "").strip().lower()
    if not query:
        return []

    query_terms = [term for term in re.findall(r"[a-z0-9]+", query) if term]
    normalized_size = size.strip().lower() if isinstance(size, str) and size.strip() else None

    scored_listings: list[tuple[int, int, dict]] = []
    for index, listing in enumerate(listings):
        if max_price is not None and listing.get("price") is not None:
            if float(listing["price"]) > float(max_price):
                continue

        listing_size = str(listing.get("size", "")).lower()
        if normalized_size and normalized_size not in listing_size:
            continue

        searchable_parts = [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", []) or []),
            " ".join(listing.get("colors", []) or []),
            listing.get("brand") or "",
            listing.get("platform", ""),
            listing.get("condition", ""),
            listing.get("size", ""),
        ]
        searchable_text = " ".join(str(part) for part in searchable_parts).lower()

        score = sum(1 for term in query_terms if term in searchable_text)
        if score > 0:
            scored_listings.append((score, index, listing))

    scored_listings.sort(key=lambda item: (-item[0], item[1]))
    return [listing for _, _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()
    items = (wardrobe or {}).get("items", []) or []

    item_name = new_item.get("title") or new_item.get("name") or "the new item"
    item_category = new_item.get("category") or "item"
    item_styles = ", ".join(new_item.get("style_tags", []) or []) or "neutral"
    item_colors = ", ".join(new_item.get("colors", []) or []) or "unspecified colors"
    item_price = new_item.get("price", "unknown")
    item_platform = new_item.get("platform", "unknown platform")

    if not items:
        prompt = (
            "You are a practical, budget-conscious fashion stylist with a casual, playful tone. "
            "The user has no wardrobe items available, so give general styling advice instead of referencing specific closet pieces. "
            "Suggest 1-2 easy outfit directions for the item below, focusing on what types of basics, shoes, and accessories would pair well. "
            "Keep it concise, useful, and readable.\n\n"
            f"Item details:\n"
            f"- Name: {item_name}\n"
            f"- Category: {item_category}\n"
            f"- Style tags: {item_styles}\n"
            f"- Colors: {item_colors}\n"
            f"- Price: {item_price}\n"
            f"- Platform: {item_platform}\n"
        )
    else:
        wardrobe_lines = []
        for index, wardrobe_item in enumerate(items, start=1):
            wardrobe_lines.append(
                f"{index}. {wardrobe_item.get('name', 'Unnamed item')} | "
                f"category={wardrobe_item.get('category', 'unknown')} | "
                f"colors={', '.join(wardrobe_item.get('colors', []) or []) or 'unknown'} | "
                f"style={', '.join(wardrobe_item.get('style_tags', []) or []) or 'unknown'} | "
                f"size={wardrobe_item.get('size', 'unknown')}"
            )

        prompt = (
            "You are a practical, budget-conscious fashion stylist with a casual, playful tone. "
            "Suggest 1-2 complete outfits using the thrifted item and the user's actual wardrobe pieces. "
            "Prefer simple, realistic pairings and mention specific wardrobe item names. "
            "Do not invent items that are not listed. Keep the response concise and easy to scan.\n\n"
            f"Thrifted item:\n"
            f"- Name: {item_name}\n"
            f"- Category: {item_category}\n"
            f"- Style tags: {item_styles}\n"
            f"- Colors: {item_colors}\n"
            f"- Price: {item_price}\n"
            f"- Platform: {item_platform}\n\n"
            "User wardrobe:\n"
            + "\n".join(wardrobe_lines)
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.8,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful fashion styling assistant. "
                    "Return only the outfit advice with no preamble or meta commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not isinstance(outfit, str) or not outfit.strip():
        return "Cannot create a fit card because the outfit suggestion is missing or empty."

    client = _get_groq_client()

    item_name = new_item.get("title") or new_item.get("name") or "the item"
    item_price = new_item.get("price", "unknown")
    item_platform = new_item.get("platform", "unknown platform")
    item_styles = ", ".join(new_item.get("style_tags", []) or []) or "neutral"
    item_colors = ", ".join(new_item.get("colors", []) or []) or "unspecified colors"
    item_category = new_item.get("category") or "item"

    prompt = (
        "Write a casual, playful OOTD caption for social media. "
        "Make it feel authentic and specific, not like a product description. "
        "Use 2-4 sentences. Mention the item name, price, and platform naturally exactly once each. "
        "Keep the vibe budget-conscious and stylish.\n\n"
        f"Item details:\n"
        f"- Name: {item_name}\n"
        f"- Category: {item_category}\n"
        f"- Style tags: {item_styles}\n"
        f"- Colors: {item_colors}\n"
        f"- Price: {item_price}\n"
        f"- Platform: {item_platform}\n\n"
        f"Outfit suggestion:\n{outfit.strip()}\n"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=1.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a fashion creator writing punchy social captions. "
                    "Return only the caption text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()
