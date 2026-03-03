import os
import json
import time
from src.fetch_news import fetch_by_category, fetch_everything
from src.embed_rank import get_embedding

CATEGORY_LIST = [
    "business", "entertainment", "general",
    "health", "science", "sports", "technology"
]

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_pipeline():
    # 1️⃣ Category 뉴스 (기존 로직 유지)
    category_data = {}
    for cat in CATEGORY_LIST:
        print(f"Fetching category: {cat}")
        try:
            articles = fetch_by_category(category=cat, page_size=10)
            category_data[cat] = [
                {"title": a["title"], "description": a["description"], "url": a["url"]} 
                for a in articles if a.get("title") and "[Removed]" not in a["title"]
            ]
        except Exception as e:
            print(f"Failed to fetch category {cat}: {e}")
            category_data[cat] = []

    save_json("docs/data/category.json", category_data)
    print("--- Saved category news! ---\n")

    # 2️⃣ Interest 뉴스 (everything 50개 + embedding)
    query = "Artificial Intelligence and technology innovation"
    print(f"Fetching everything for interest: {query}")
    
    # fetch_everything에서 에러가 날 경우를 대비해 빈 리스트 반환 처리 확인
    raw_articles = fetch_everything(query=query, page_size=50)

    embedding_data = []
    seen_urls = set() # 중복 기사 방지용

    for i, art in enumerate(raw_articles):
        # 중복 제거 및 유효성 검사
        if art["url"] in seen_urls or not art["title"] or "[Removed]" in art["title"]:
            continue
        
        # 임베딩할 텍스트 결정 (본문 우선, 없으면 설명글)
        content_to_embed = art["text"] if art["text"].strip() else art["description"]
        
        # 텍스트가 아예 없는 경우 임베딩 건너뜀
        if not content_to_embed or len(content_to_embed.strip()) < 10:
            continue

        print(f"[{i+1}/{len(raw_articles)}] Embedding: {art['title'][:30]}...")
        
        try:
            emb = get_embedding(content_to_embed)
            embedding_data.append({
                "title": art["title"],
                "description": art["description"],
                "url": art["url"],
                "embedding": emb
            })
            seen_urls.add(art["url"])
            
            # API Rate Limit 방지를 위한 아주 짧은 휴식 (사용하는 임베딩 API에 따라 조절)
            # time.sleep(0.05) 
            
        except Exception as e:
            print(f"Failed to get embedding for {art['url']}: {e}")
            continue

    save_json("docs/data/embedding.json", embedding_data)
    print(f"\n--- Saved {len(embedding_data)} interest embeddings! ---")

if __name__ == "__main__":
    run_pipeline()
