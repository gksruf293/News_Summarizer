import os
import json
import time
from datetime import datetime
import requests
from openai import OpenAI
from src.fetch_news import fetch_by_category, fetch_everything, get_full_text

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def query_hf_embedding(text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    for _ in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json={"inputs": text}, timeout=15)
            if response.status_code == 200:
                return response.json()
            time.sleep(10)
        except:
            pass
    return None

def generate_multi_summaries(text):
    """영어 학습용 요약 생성 (English ||| Korean)"""
    prompts = {
        "elementary": "Summarize in 2 simple sentences (A1).",
        "middle": "Summarize in 3 clear sentences (B1).",
        "high": "Summarize in professional English (C1)."
    }
    summaries = {}
    
    if not text or len(text.strip()) < 100:
        return {k: {"en": "Text too short.", "ko": "본문이 너무 짧습니다."} for k in prompts}

    for level, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an English teacher. Format: English ||| Korean"},
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
            summaries[level] = {"en": "Summary error.", "ko": "요약 오류"}
    return summaries

def run_pipeline():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Running Pipeline for {today_str}")

    # 1. 카테고리 뉴스 수집
    cat_results = {}
    for cat in CATEGORY_LIST:
        articles = fetch_by_category(category=cat, page_size=5)
        processed = []
        for art in articles:
            full_text = get_full_text(art["url"])
            summaries = generate_multi_summaries(full_text if len(full_text)>200 else art.get("description", ""))
            processed.append({
                "title": art["title"], "url": art["url"], 
                "image": art.get("urlToImage"), "summaries": summaries
            })
        cat_results[cat] = processed

    # 2. 검색용 임베딩 뉴스 수집 (오늘의 이슈 위주)
    print("--- Generating Today's Search Embeddings ---")
    raw_articles = fetch_everything(query="AI OR technology OR economy", page_size=40)
    emb_results = []
    for art in raw_articles:
        text = f"{art['title']}. {art.get('description','')}"
        emb = query_hf_embedding(text)
        if emb and isinstance(emb, list):
            emb_results.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"),
                "embedding": emb, "summaries": generate_multi_summaries(text)
            })
    
    print(f"🔥 Final Embedding Count: {len(emb_results)}")

    # 3. 데이터 저장
    for path in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/category.json", "w", encoding="utf-8") as f:
            json.dump(cat_results, f, ensure_ascii=False, indent=2)
        with open(f"{path}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(emb_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_pipeline()
