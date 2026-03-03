import requests
import os
import time
from typing import List, Dict
from newspaper import Article

NEWS_API_URL = "https://newsapi.org/v2"

def fetch_everything(query: str, language: str = "en", page_size: int = 50, page: int = 1) -> List[Dict]:
    """
    Developer 플랜 제약을 고려한 뉴스 페칭 함수
    """
    api_key = os.getenv("NEWS_API_KEY")
    
    # 1️⃣ 헤더 설정: 브라우저 차단(CORS)을 피하기 위해 User-Agent를 반드시 설정
    headers = {
        "User-Agent": "MyNewsApp/1.0 (Python-requests)", # 브라우저가 아님을 명시
        "X-Api-Key": api_key
    }
    
    url = f"{NEWS_API_URL}/everything"
    
    # Developer 플랜은 24시간 지연된 데이터만 접근 가능하므로 
    # 너무 최신 데이터를 요청하면 결과가 적을 수 있음
    params = {
        "q": query,
        "language": language,
        "pageSize": page_size,
        "page": page,
        "sortBy": "publishedAt"
    }

    try:
        # API 호출
        response = requests.get(url, params=params, headers=headers)
        
        # 에러 핸들링
        if response.status_code == 403:
            print("CORS/Permission Error: API가 요청을 거부했습니다. 헤더 설정을 확인하세요.")
            return []
        elif response.status_code == 429:
            print("Rate Limit: 하루 100회 요청 제한에 도달했습니다.")
            return []
            
        response.raise_for_status()
        articles_meta = response.json().get("articles", [])
        
    except Exception as e:
        print(f"NewsAPI 요청 중 오류 발생: {e}")
        return []

    # 2️⃣ 본문 추출 (newspaper3k)
    articles = []
    for meta in articles_meta:
        url = meta.get("url")
        title = meta.get("title")
        
        if not url or "[Removed]" in title:
            continue

        try:
            article = Article(url)
            # 타임아웃을 짧게 주어 파이프라인이 멈추는 것을 방지
            article.download(config={'request_timeout': 5})
            article.parse()
            full_text = article.text[:5000]
        except:
            full_text = ""

        articles.append({
            "title": title,
            "url": url,
            "description": meta.get("description", ""),
            "text": full_text
        })
    
    return articles
