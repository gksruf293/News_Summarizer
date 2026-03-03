import requests
import os
import time
from typing import List, Dict
from newspaper import Article

NEWS_API_URL = "https://newsapi.org/v2"

def fetch_everything(query: str, language: str = "en", page_size: int = 50, page: int = 1) -> List[Dict]:
    """
    Fetch article metadata from NewsAPI, then use newspaper3k to get full text.
    """
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        print("Error: NEWS_API_KEY not found in environment variables.")
        return []

    url = f"{NEWS_API_URL}/everything"
    
    # 1️⃣ NewsAPI 요청 시 헤더 추가 (매우 중요)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Api-Key": api_key
    }
    
    params = {
        "q": query,
        "language": language,
        "pageSize": page_size,
        "page": page,
    }

    try:
        # params에 apiKey를 넣는 대신 headers를 사용하는 것이 더 안전합니다.
        response = requests.get(url, params=params, headers=headers)
        
        # 상세 에러 체크
        if response.status_code == 429:
            print("Error: Rate limit exceeded. (무료 플랜은 요청 횟수 제한이 엄격합니다)")
            return []
        elif response.status_code == 400:
            print(f"Error: Bad Request. Check your parameters: {response.json().get('message')}")
            return []
        
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error occurred: {e}")
        return []

    articles_meta = response.json().get("articles", [])
    print(f"Successfully fetched {len(articles_meta)} article metadata.")

    # 2️⃣ newspaper3k로 URL에서 full text 가져오기
    articles = []
    for i, meta in enumerate(articles_meta):
        title = meta.get("title")
        url = meta.get("url")
        description = meta.get("description", "")

        if not url or not title or "[Removed]" in title:
            continue

        try:
            article = Article(url)
            # 뉴스사 서버 부하 및 차단 방지를 위한 타임아웃 설정
            article.download(config={'request_timeout': 10}) 
            article.parse()
            
            full_text = article.text[:5000].strip()
            
            # 본문이 너무 짧으면 description으로 대체하거나 건너뜀
            if len(full_text) < 100:
                full_text = description
                
        except Exception as e:
            print(f"[{i+1}] Failed to fetch full text for {url}: {e}")
            full_text = description # 실패 시 요약본이라도 유지

        articles.append({
            "title": title,
            "url": url,
            "description": description,
            "text": full_text
        })
        
        # 50개를 가져올 때 뉴스 사이트 차단을 피하기 위해 아주 짧은 휴식 (옵션)
        # time.sleep(0.1)

    return articles
