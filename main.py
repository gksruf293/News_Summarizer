# main.py

import json
from datetime import datetime
from src.scheduler import should_run_today
from src.pipeline import run_pipeline

# NewsAPI 공식 category만 허용
USER_CATEGORY = "technology"  # 여기만 바꾸면 됨
TOP_K = 3

if __name__ == "__main__":
    if not should_run_today():
        print("Pipeline skipped today.")
    else:
        top_articles = run_pipeline()

        output = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "articles": top_articles
        }
    
        with open("data/todays_news.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    print("todays_news.json generated.")
