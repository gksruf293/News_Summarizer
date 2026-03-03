import requests
import os

API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2"

def fetch_top_headlines(category="general", country="us", page_size=50):
    """/top-headlines 엔드포인트를 사용하여 주요 뉴스를 수집합니다."""
    url = f"{BASE_URL}/top-headlines"
    params = {
        "country": country,
        "category": category,
        "pageSize": page_size,
        "apiKey": API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()
        if data.get("status") == "ok":
            return data.get("articles", [])
        else:
            print(f"⚠️ News API Error: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ News API Fetch Error: {e}")
        return []

def get_full_text(url):
    """뉴스 본문을 추출합니다."""
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except:
        return ""
