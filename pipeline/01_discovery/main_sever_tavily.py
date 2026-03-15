import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from tavily_client import TavilyClient

def load_config(filepath="config/discovery.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_existing_dates(filepath):
    if not os.path.exists(filepath):
        return set()
    
    dates = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                dates.add(data["date"])
            except:
                pass
    return dates

def main():
    config = load_config()
    client = TavilyClient(config)
    
    output_dir = config["output"]["dir"]
    os.makedirs(output_dir, exist_ok=True)

    start_date = datetime.strptime(config["date_range"]["start"], "%Y-%m-%d")
    end_date = datetime.strptime(config["date_range"]["end"], "%Y-%m-%d")
    
    template = config["query_templates"][0]["template"]
    skip_if_exists = config["resume"]["skip_if_date_exists"]

    print("Bat dau thu thap link...")
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Tao ngay tiep theo de lam end_date
        next_date = current_date + timedelta(days=1)
        next_date_str = next_date.strftime("%Y-%m-%d")
        
        year = current_date.year
        month = current_date.month
        day = current_date.day

        filename = config["output"]["filename_pattern"].format(year=year, month=month)
        filepath = os.path.join(output_dir, filename)

        if skip_if_exists:
            existing_dates = get_existing_dates(filepath)
            if date_str in existing_dates:
                print(f"Bo qua {date_str} (da co du lieu)")
                current_date += timedelta(days=1)
                continue

        query = template.format(day=day, month=month, year=year)
        
        print(f"Dang tim kiem: '{query}' voi khoang thoi gian {date_str} den {next_date_str}")

        # Truyen next_date_str vao end_date
        results = client.search(query, start_date=date_str, end_date=next_date_str)

        day_record = {
            "date": date_str,
            "query": query,
            "results": []
        }

        for rank, res in enumerate(results, start=1):
            domain = res.get("url", "").split("/")[2] if "://" in res.get("url", "") else ""
            day_record["results"].append({
                "rank": rank,
                "url": res.get("url"),
                "domain": domain,
                "title": res.get("title"),
                "scrape_status": "pending"
            })

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(day_record, ensure_ascii=False) + "\n")

        print(f"Da luu {len(day_record['results'])} links vao {filename}")

        current_date += timedelta(days=1)

    print("Hoan tat thu thap link!")

if __name__ == "__main__":
    main()