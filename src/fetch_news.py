import os
import requests
from typing import List, Dict

NEWS_API_URL = "https://newsapi.org/v2"

# NewsAPI에서 공식 지원하는 category만 허용
ALLOWED_CATEGORIES = {
    "business",
    "entertainment",
    "general",
    "health",
    "science",
    "sports",
    "technology"
}


def _get_api_key() -> str:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        raise ValueError("NEWS_API_KEY not found in environment variables.")
    return api_key


def fetch_by_category(
    category: str,
    country: str = "us",
    page_size: int = 30
) -> List[Dict]:
    """
    Fetch articles only from allowed NewsAPI categories.
    """

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Invalid category: {category}. Must be one of {ALLOWED_CATEGORIES}"
        )

    url = f"{NEWS_API_URL}/top-headlines"

    params = {
        "apiKey": _get_api_key(),
        "country": country,
        "category": category,
        "pageSize": page_size
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    articles = response.json().get("articles", [])
    return _clean_articles(articles)


def _clean_articles(raw_articles: List[Dict]) -> List[Dict]:
    """
    - Remove articles without title or url
    - Deduplicate by URL
    - Create unified 'text' field for retrieval
    """

    seen_urls = set()
    cleaned = []

    for article in raw_articles:
        title = article.get("title")
        description = article.get("description")
        url = article.get("url")

        if not title or not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        combined_text = f"{title}. {description or ''}"

        cleaned.append({
            "title": title,
            "description": description,
            "url": url,
            "source": article.get("source", {}).get("name"),
            "publishedAt": article.get("publishedAt"),
            "text": combined_text
        })

    return cleaned
