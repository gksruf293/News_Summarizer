import os
import json
import time
from datetime import datetime
import requests
from openai import OpenAI
from src.fetch_news import fetch_by_category, fetch_everything, get_full_text

# 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def query_hf_embedding(text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    for _ in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json={"inputs": text}, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                time.sleep(15)
                continue
        except:
            pass
    return None

def generate_multi_summaries(text):
    """영어 학습용: 영문 요약 ||| 한글 번역 생성"""
    prompts = {
        "elementary": "Summarize in 2 very simple sentences for a beginner. (A1 level)",
        "middle": "Summarize in 3 clear sentences with intermediate vocabulary. (B1 level)",
        "high": "Summarize in a logical, professional manner for advanced learners. (C1 level)"
    }
    summaries = {}
    
    if not text or len(text.strip()) < 100:
        return {k: {"en": "Content too short to summarize.", "ko": "요약하기에 본문이 너무 짧습니다."} for k in prompts}

    for level, prompt in prompts.items():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an English teacher. Summarize in English and provide Korean translation. Format: English text ||| Korean translation"},
                    {"role": "user", "content": f"{prompt}\n\nContent: {text[:3500]}"}
                ],
                temperature=0.3
            )
            res_text = response.choices[0].message.content.strip()
            if "|||" in res_text:
                en, ko = res_text.split("|||")
                summaries[level] = {"en": en.strip(), "ko": ko.strip()}
            else:
                summaries[level] = {"en": res_text, "ko": "(번역 준비 중)"}
        except Exception as e:
            summaries[level] = {"en": "Error occurred during summary.", "ko": "요약 중 오류 발생"}
    return summaries

def run_pipeline():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Running Pipeline for Date: {today_str}")

    # 1️⃣ 카테고리별 뉴스 수집
    final_category_data = {}
    for cat in CATEGORY_LIST:
        print(f"--- Processing Category: {cat} ---")
        articles = fetch_by_category(category=cat, page_size=5)
        processed = []
        for art in articles:
            full_text = get_full_text(art["url"])
            target_text = full_text if len(full_text) > 200 else art.get("description", "")
            
            print(f"Summarizing: {art['title'][:30]}...")
            summaries = generate_multi_summaries(target_text)
            
            processed.append({
                "title": art["title"],
                "url": art["url"],
                "image": art.get("image"),
                "source": art.get("source"),
                "summaries": summaries
            })
        final_category_data[cat] = processed

    # 2️⃣ 검색용 임베딩 생성 (범용 쿼리로 0개 방지)
    print("\n--- Generating Search Embeddings ---")
    interest_news = fetch_everything(query="world news", page_size=20)
    embedding_data = []
    for art in interest_news:
        text_to_embed = f"{art['title']}. {art.get('description', '')}"
        emb = query_hf_embedding(text_to_embed)
        if emb and isinstance(emb, list):
            embedding_data.append({
                "title": art["title"],
                "url": art["url"],
                "description": art.get("description"),
                "image": art.get("image"),
                "embedding": emb,
                "summaries": generate_multi_summaries(art.get("description", art["title"]))
            })
    
    print(f"✅ Generated {len(embedding_data)} embeddings")

    # 3️⃣ 저장
    for path_dir in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(path_dir, exist_ok=True)
        with open(f"{path_dir}/category.json", "w", encoding="utf-8") as f:
            json.dump(final_category_data, f, ensure_ascii=False, indent=2)
        with open(f"{path_dir}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(embedding_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Data saved successfully in docs/data/{today_str}")

if __name__ == "__main__":
    run_pipeline()
