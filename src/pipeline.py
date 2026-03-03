import os
import json
import time
from datetime import datetime
import requests
from openai import OpenAI
from fetch_news import fetch_top_headlines, get_full_text

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
HF_TOKEN = os.getenv("HF_TOKEN")

# 핵심 수정: 기존 api-inference 대신 router.huggingface.co/models/ 주소를 사용합니다.
HF_API_URL = "https://router.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"

CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def query_hf_embedding(text):
    """최신 허깅페이스 라우터 API를 사용하여 임베딩을 생성합니다."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": [text[:1000]], 
        "options": {"wait_for_model": True, "use_cache": True}
    }
    
    for i in range(3):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
            res_json = response.json()
            
            if response.status_code == 200:
                if isinstance(res_json, list) and len(res_json) > 0:
                    return res_json[0]
                return res_json
            elif response.status_code == 503:
                print(f"⌛ 모델 로딩 중... {i+1}번째 재시도 (30초 대기)")
                time.sleep(30)
                continue
            else:
                print(f"⚠️ API 응답 오류: {response.status_code} - {res_json}")
        except Exception as e:
            print(f"❌ 네트워크 에러: {e}")
            
        time.sleep(5)
    return None

def generate_multi_summaries(text):
    """GPT를 이용한 3단계 요약 및 번역 생성 (English ||| Korean)"""
    prompts = {"elementary": "2 simple sentences", "middle": "3 clear sentences", "high": "Advanced summary"}
    summaries = {}
    content = text[:3000] if text else "No content available."
    
    for level, p in prompts.items():
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a teacher. Format: English ||| Korean"},
                    {"role": "user", "content": f"{p}\n\nContent: {content}"}
                ],
                temperature=0.3
            )
            res = resp.choices[0].message.content.strip()
            if "|||" in res:
                en, ko = res.split("|||")
                summaries[level] = {"en": en.strip(), "ko": ko.strip()}
            else:
                summaries[level] = {"en": res, "ko": "(번역 준비 중)"}
        except:
            summaries[level] = {"en": "Error.", "ko": "요약 생성 오류"}
    return summaries

def run_pipeline():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 파이프라인 시작 (API 엔드포인트 수정됨): {today_str}")

    # 1. 임베딩 데이터 생성
    print("--- 임베딩 데이터 구축 중 ---")
    base_articles = fetch_top_headlines(category="general", page_size=40)
    embedding_results = []
    
    for art in base_articles:
        combined_text = f"{art['title']}. {art.get('description') or ''}"
        if len(combined_text) < 30: continue
        
        emb = query_hf_embedding(combined_text)
        if emb:
            embedding_results.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"),
                "embedding": emb, "summaries": generate_multi_summaries(combined_text)
            })
            print(f"✅ 임베딩 완료: {art['title'][:30]}...")
    
    print(f"🔥 최종 임베딩 개수: {len(embedding_results)}")

    # 2. 카테고리별 데이터 생성
    category_results = {}
    for cat in CATEGORY_LIST:
        print(f"Processing category: {cat}")
        articles = fetch_top_headlines(category=cat, page_size=5)
        processed = []
        for art in articles:
            full_text = get_full_text(art["url"])
            summaries = generate_multi_summaries(full_text if len(full_text)>200 else art.get("description", ""))
            processed.append({
                "title": art["title"], "url": art["url"], "image": art.get("urlToImage"), "summaries": summaries
            })
        category_results[cat] = processed

    # 3. 데이터 저장
    for p in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(p, exist_ok=True)
        with open(f"{p}/category.json", "w", encoding="utf-8") as f:
            json.dump(category_results, f, ensure_ascii=False, indent=2)
        with open(f"{p}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(embedding_results, f, ensure_ascii=False, indent=2)
    print("✨ 파이프라인 작업 완료!")

if __name__ == "__main__":
    run_pipeline()
