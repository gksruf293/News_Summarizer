from src.scheduler import should_run_today
from src.pipeline import run_pipeline


if __name__ == "__main__":
    if not should_run_today():
        print("Pipeline skipped today.")
    else:
        run_pipeline()
