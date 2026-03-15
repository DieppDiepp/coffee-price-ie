import os
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from serper_client import SerperClient

def load_config(filepath="config/discovery.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_existing_runs(filepath):
    """
    Kiem tra cac (ngay + query_id) da duoc quet de tranh quet lai hoac bo sot
    khi co nhieu query trong cung mot ngay.
    """
    if not os.path.exists(filepath):
        return set()
    
    runs = set()
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                run_key = f"{data['date']}_{data.get('query_id', 'unknown')}"
                runs.add(run_key)
            except:
                pass
    return runs

def parse_serper_date(raw_date):
    if not raw_date:
        return ""
        
    raw_date = raw_date.lower().strip()
    today = datetime.now()
    
    match_days = re.search(r'(\d+)\s*(ngay truoc|ngày trước|days ago)', raw_date)
    if match_days:
        days = int(match_days.group(1))
        return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        
    if any(kw in raw_date for kw in ["gio", "giờ", "phut", "phút", "hours", "mins"]):
        return today.strftime("%Y-%m-%d")
        
    match_vn_date = re.search(r'(\d+)\s*thg\s*(\d+)[,\s]*(\d{4})', raw_date)
    if match_vn_date:
        d, m, y = match_vn_date.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
        
    try:
        dt = datetime.strptime(raw_date, "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
        
    return raw_date

def main():
    config = load_config()
    client = SerperClient(config)
    
    output_dir = config["output"]["dir"]
    os.makedirs(output_dir, exist_ok=True)

    start_date = datetime.strptime(config["date_range"]["start"], "%Y-%m-%d")
    end_date = datetime.strptime(config["date_range"]["end"], "%Y-%m-%d")
    
    templates = config.get("query_templates", [])
    skip_if_exists = config["resume"]["skip_if_date_exists"]

    print("Bat dau thu thap link bang Google Search (Serper) voi nhieu mau query...")
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        next_date = current_date + timedelta(days=1)
        next_date_str = next_date.strftime("%Y-%m-%d")
        
        year = current_date.year
        month = current_date.month
        day = current_date.day

        filename = config["output"]["filename_pattern"].format(year=year, month=month)
        filepath = os.path.join(output_dir, filename)

        # Chay qua tung template cho cung mot ngay
        for template_info in templates:
            query_id = template_info.get("id", "unknown")
            target = template_info.get("target", "unknown")
            template = template_info["template"]
            
            run_key = f"{date_str}_{query_id}"
            
            if skip_if_exists:
                existing_runs = get_existing_runs(filepath)
                if run_key in existing_runs:
                    print(f"Bo qua {run_key} (da co du lieu)")
                    continue

            query = template.format(day=day, month=month, year=year)
            
            print(f"Dang tim kiem: '{query}' ({date_str} den {next_date_str})")

            results = client.search(query, start_date=date_str, end_date=next_date_str)

            # Bo sung cac truong phan loai vao day_record
            day_record = {
                "date": date_str,
                "query_id": query_id,
                "target": target,
                "query": query,
                "results": []
            }

            for rank, res in enumerate(results, start=1):
                link = res.get("link", "")
                domain = link.split("/")[2] if "://" in link else ""
                
                raw_date = res.get("date", "")
                parsed_date = parse_serper_date(raw_date)
                
                day_record["results"].append({
                    "rank": rank,
                    "url": link,
                    "domain": domain,
                    "title": res.get("title", ""),
                    "snippet": res.get("snippet", ""),
                    "raw_date": raw_date,
                    "published_date": parsed_date,
                    "scrape_status": "pending"
                })

            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(day_record, ensure_ascii=False) + "\n")

            print(f"Da luu {len(day_record['results'])} links vao {filename}")

        # Sang ngay tiep theo sau khi da chay het cac template cua ngay hien tai
        current_date += timedelta(days=1)

    print("Hoan tat thu thap link bang Serper!")

if __name__ == "__main__":
    main()