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
    """
    listings = load_listings()

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    if size is not None:
        listings = [l for l in listings if size.lower() in l["size"].lower()]

    keywords = description.lower().split()

    def score(listing):
        text = (listing["title"] + " " + listing["description"]).lower()
        return sum(1 for word in keywords if word in text)

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in scored]


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
    """
    client = _get_groq_client()
    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"A user just found this thrifted item:\n"
            f"Title: {new_item['title']}\n"
            f"Category: {new_item['category']}\n"
            f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
            f"Colors: {', '.join(new_item.get('colors', []))}\n"
            f"Condition: {new_item['condition']}\n\n"
            f"They don't have any wardrobe items on file. Give them general styling advice: "
            f"what types of pieces pair well with this item, what vibe it suits, and how to wear it. "
            f"Keep it casual and helpful, 2-3 sentences."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {item['name']} ({item['category']}, colors: {', '.join(item.get('colors', []))})"
            for item in items
        )
        prompt = (
            f"A user just found this thrifted item:\n"
            f"Title: {new_item['title']}\n"
            f"Category: {new_item['category']}\n"
            f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
            f"Colors: {', '.join(new_item.get('colors', []))}\n"
            f"Condition: {new_item['condition']}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_lines}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item and specific pieces "
            f"from their wardrobe. Name the wardrobe items directly. Keep it casual and specific, "
            f"2-4 sentences."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Outfit suggestion unavailable. Try pairing this with your current wardrobe."


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
    """
    if not outfit or not outfit.strip():
        return "Cannot generate fit card: no outfit suggestion provided."

    client = _get_groq_client()

    prompt = (
        f"Write a 2-4 sentence Instagram/TikTok caption for this thrifted outfit. "
        f"Make it sound like a real person wrote it, not a product listing. "
        f"Mention the item name, price, and platform naturally — each only once.\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']}\n"
        f"Platform: {new_item['platform']}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Outfit: {outfit}\n\n"
        f"Caption (casual, specific, no hashtags):"
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Fit card generation failed. Please try again."
