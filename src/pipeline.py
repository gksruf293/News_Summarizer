import os
import json
import time
from datetime import datetime
import requests
from openai import OpenAI
from src.fetch_news import fetch_top_headlines

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")
# 최신 라우터 주소
HF_API_URL = "https://router.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def query_hf_embedding(text):
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    # 입력을 리스트가 아닌 단일 텍스트로 전달
    payload = {"inputs": text[:1000], "options": {"wait_for_model": True, "use_cache": True}}
    
    for i in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res = response.json()
                return res[0] if isinstance(res, list) else res
            elif response.status_code == 503:
                time.sleep(20)
                continue
            else:
                print(f"⚠️ API 오류 {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"❌ 임베딩 시도 중 에러: {e}")
        time.sleep(2)
    return None

def generate_multi_summaries(text):
    """요약 생성 (시간 단축을 위해 3000자 제한)"""
    if not text or len(text) < 50:
        return {k: {"en": "No content", "ko": "내용 없음"} for k in ["elementary", "middle", "high"]}
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Format: English ||| Korean. Only 2-3 sentences."},
                {"role": "user", "content": f"Summarize: {text[:2000]}"}
            ],
            temperature=0.3
        )
        res = resp.choices[0].message.content.strip()
        if "|||" in res:
            en, ko = res.split("|||")
            return {"elementary": {"en": en.strip(), "ko": ko.strip()}, "middle": {"en": en.strip(), "ko": ko.strip()}, "high": {"en": en.strip(), "ko": ko.strip()}}
    except:
        pass
    return {"elementary": {"en": "Summary Error", "ko": "요약 오류"}}

def run_pipeline():
    start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 파이프라인 시작: {today_str}")

    # 1. 시맨틱 검색용 풀 (시간 단축을 위해 20개로 축소)
    print("--- 임베딩 생성 (20개 목표) ---")
    base_articles = fetch_top_headlines(category="general", page_size=20)
    embedding_results = []
    
    for art in base_articles:
        txt = f"{art['title']}. {art.get('description') or ''}"
        emb = query_hf_embedding(txt)
        if emb:
            embedding_results.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"),
                "embedding": emb, "summaries": generate_multi_summaries(txt)
            })
            print(f"✅") # 성공 시 점만 찍어 로그 단축
    
    # 2. 카테고리별 데이터 (본문 크롤링 생력하여 시간 단축)
    print("--- 카테고리 데이터 생성 ---")
    category_results = {}
    for cat in CATEGORY_LIST:
        articles = fetch_top_headlines(category=cat, page_size=5)
        processed = []
        for art in articles:
            # get_full_text(art["url"]) 대신 description 사용
            summaries = generate_multi_summaries(art.get('description', art['title']))
            processed.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"), "summaries": summaries
            })
        category_results[cat] = processed

    # 3. 저장
    for p in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(p, exist_ok=True)
        with open(f"{p}/category.json", "w", encoding="utf-8") as f:
            json.dump(category_results, f, ensure_ascii=False)
        with open(f"{p}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(embedding_results, f, ensure_ascii=False)
            
    print(f"🔥 완료! 시간: {int(time.time() - start_time)}초 | 개수: {len(embedding_results)}")

if __name__ == "__main__":
    run_pipeline()
