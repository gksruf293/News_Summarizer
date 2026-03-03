import os
import json
import time
from datetime import datetime
import requests
from openai import OpenAI
from src.fetch_news import fetch_top_headlines, get_full_text

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def query_hf_embedding(text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    for i in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json={"inputs": text}, timeout=20)
            if response.status_code == 200:
                res = response.json()
                if isinstance(res, list): return res
            elif response.status_code == 503:
                time.sleep(20) # 모델 로딩 대기
                continue
        except:
            pass
        time.sleep(5)
    return None

def generate_multi_summaries(text):
    """English ||| Korean 형식의 3단계 요약 생성"""
    prompts = {
        "elementary": "2 simple sentences (A1).",
        "middle": "3 clear sentences (B1).",
        "high": "Professional summary (C1)."
    }
    summaries = {}
    if not text or len(text.strip()) < 100:
        return {k: {"en": "Content too short.", "ko": "본문이 너무 짧습니다."} for k in prompts}

    for level, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an English teacher. Format: English text ||| Korean translation"},
                    {"role": "user", "content": f"{prompt}\n\nContent: {text[:3000]}"}
                ],
                temperature=0.3
            )
            res_text = response.choices[0].message.content.strip()
            if "|||" in res_text:
                en, ko = res_text.split("|||")
                summaries[level] = {"en": en.strip(), "ko": ko.strip()}
            else:
                summaries[level] = {"en": res_text, "ko": "(번역 준비 중)"}
        except:
            summaries[level] = {"en": "Error.", "ko": "오류"}
    return summaries

def run_pipeline():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Pipeline Start: {today_str}")

    # 1. 시맨틱 검색용 데이터 풀 확보 (Top Headlines 100개)
    print("--- Fetching 100 Headlines for Semantic Search ---")
    top_100_articles = fetch_top_headlines(page_size=100)
    embedding_results = []
    
    for art in top_100_articles:
        combined_text = f"{art['title']}. {art.get('description', '')}"
        if len(combined_text) < 30: continue
        
        # 검색용 임베딩 생성
        emb = query_hf_embedding(combined_text)
        if emb:
            embedding_results.append({
                "title": art["title"],
                "url": art["url"],
                "image": art.get("urlToImage"),
                "embedding": emb,
                "summaries": generate_multi_summaries(combined_text)
            })
            if len(embedding_results) >= 50: break # API 제한 및 속도를 위해 50개로 최적화
    
    print(f"✅ Successfully embedded {len(embedding_results)} articles.")

    # 2. 카테고리별 뉴스 (화면 탭 표시용)
    category_results = {}
    for cat in CATEGORY_LIST:
        print(f"Processing category: {cat}")
        cat_articles = fetch_top_headlines(category=cat, page_size=5)
        processed = []
        for art in cat_articles:
            full_text = get_full_text(art["url"])
            summaries = generate_multi_summaries(full_text if len(full_text) > 200 else art.get("description", ""))
            processed.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"), "summaries": summaries
            })
        category_results[cat] = processed

    # 3. 데이터 저장
    for path in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/category.json", "w", encoding="utf-8") as f:
            json.dump(category_results, f, ensure_ascii=False, indent=2)
        with open(f"{path}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(embedding_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_pipeline()
