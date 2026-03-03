# src/pipeline.py

from src.fetch_news import fetch_by_category
from src.embed_rank import rank_articles_by_interest

def run_pipeline(USER_CATEGORY='technology', TOP_K = 3):
    print(f"Fetching news from category: {USER_CATEGORY}")

    articles = fetch_by_category(
        category=USER_CATEGORY,
        country="us",
        page_size=30
    )

    print(f"Fetched {len(articles)} articles.")

    if not articles:
        print("No articles found.")
        return

    # category 자체를 관심사 텍스트로 사용
    user_interest = f"Latest news about {USER_CATEGORY}"

    top_articles = rank_articles_by_interest(
        articles,
        user_interest=user_interest,
        top_k=TOP_K
    )

    print(f"\nSelected {len(top_articles)} articles for summarization.")

    return top_articles
