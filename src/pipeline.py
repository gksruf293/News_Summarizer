import os
import json
import time
from datetime import datetime
from huggingface_hub import InferenceClient
from openai import OpenAI
from fetch_news import fetch_top_headlines

# API 설정
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN"))

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
CATEGORY_LIST = ["business", "entertainment", "general", "health", "science", "sports", "technology"]

def get_embedding(text):
    """문장 임베딩 생성"""
    try:
        embedding = hf_client.feature_extraction(text[:1000], model=MODEL_ID)
        return embedding.tolist() if hasattr(embedding, "tolist") else embedding
    except Exception as e:
        print(f"⚠️ HF API 에러: {e}")
        return None

def generate_multi_summaries(title, description):
    """레벨별(3, 5, 7줄) 확실한 차이를 둔 요약 생성"""
    source_text = description if description and len(description) > 50 else title
    
    if not source_text or len(source_text) < 10:
        msg = {"en": title, "ko": "내용 요약이 제공되지 않는 기사입니다."}
        return {k: msg for k in ["elementary", "middle", "high"]}

    try:
        resp = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are a professional English teacher. 
                Create three distinct levels of summaries:
                
                1. Level 1 (Elementary): Exactly 3 short sentences. Use basic vocabulary (CEFR A1).
                2. Level 2 (Middle): Exactly 5 sentences. Use intermediate vocabulary and compound sentences (CEFR B1-B2).
                3. Level 3 (High): Exactly 7 sentences. Use advanced academic vocabulary, complex structures, and idioms (CEFR C1).
                
                Output format for each level:
                Level X: [English sentences] ||| [Korean translation]"""},
                {"role": "user", "content": source_text[:1200]}
            ],
            temperature=0.4
        )
        
        content = resp.choices[0].message.content.strip()
        lines = [line for line in content.split('\n') if "|||" in line]
        
        levels = ["elementary", "middle", "high"]
        summaries = {}
        
        for i, line in enumerate(lines[:3]):
            clean_line = line.split(":", 1)[-1] if ":" in line else line
            en, ko = clean_line.split("|||")
            # 문장 간 줄바꿈이 필요한 경우 브라우저 표시를 위해 처리
            summaries[levels[i]] = {
                "en": en.strip().replace(". ", ".<br>"), 
                "ko": ko.strip().replace(". ", ".<br>")
            }
            
        return summaries
    except Exception as e:
        print(f"⚠️ 요약 생성 에러: {e}")
        fallback = {"en": title, "ko": "요약 생성 중 오류가 발생했습니다."}
        return {k: fallback for k in ["elementary", "middle", "high"]}

def run_pipeline():
    start_time = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 파이프라인 시작: {today_str}")

    all_collected_articles = []
    category_results = {}

    # 1. 카테고리별 20개씩 수집 (총 140개 중 중복제외 100개 목표)
    for cat in CATEGORY_LIST:
        print(f"--- {cat} 카테고리 수집 중 ---")
        articles = fetch_top_headlines(category=cat, page_size=20)
        processed = []
        
        for art in articles:
            summaries = generate_multi_summaries(art['title'], art.get('description'))
            entry = {
                "title": art["title"],
                "url": art["url"],
                "image": art.get("urlToImage"),
                "summaries": summaries,
                "description": art.get('description', '')
            }
            processed.append(entry)
            all_collected_articles.append(entry)
            print("✅", end="", flush=True)
        
        category_results[cat] = processed
        print(f"\n{cat} 완료 ({len(processed)}개)")

    # 2. 시맨틱 검색용 임베딩 생성 (중복 제거 후 100개)
    print("\n--- 임베딩 생성 시작 (Top 100) ---")
    unique_articles = {a['url']: a for a in all_collected_articles}.values()
    target_articles = list(unique_articles)[:100]
    embedding_results = []

    for art in target_articles:
        search_text = f"{art['title']}. {art['description']}"
        emb = get_embedding(search_text)
        if emb:
            art['embedding'] = emb
            embedding_results.append(art)
            print("💎", end="", flush=True)

    # 3. 저장 (날짜별 폴더 및 최신 폴더)
    for p in [f"docs/data/{today_str}", "docs/data/latest"]:
        os.makedirs(p, exist_ok=True)
        with open(f"{p}/category.json", "w", encoding="utf-8") as f:
            json.dump(category_results, f, ensure_ascii=False)
        with open(f"{p}/embedding.json", "w", encoding="utf-8") as f:
            json.dump(embedding_results, f, ensure_ascii=False)
            
    print(f"\n✨ 완료! 소요시간: {int(time.time() - start_time)}초 | 데이터: {len(embedding_results)}개")

if __name__ == "__main__":
    run_pipeline()
