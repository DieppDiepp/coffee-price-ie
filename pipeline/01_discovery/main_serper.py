import os
import json
import re
import hashlib
from datetime import datetime, timedelta
import snowflake.connector
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

from serper_client import SerperClient

def load_config(filepath="config/discovery.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_snowflake_connection():
    """Tạo kết nối đến kho dữ liệu Snowflake"""
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )

def get_existing_runs_from_snowflake(conn):
    """
    Hỏi Snowflake xem những ngày nào và câu tìm kiếm nào đã được quét rồi.
    Trả về danh sách dạng: '2026-03-11_robusta_local'
    """
    runs = set()
    try:
        cursor = conn.cursor()
        # Lấy ngày và ID câu tìm kiếm đã lưu thành công
        cursor.execute("SELECT TO_VARCHAR(date_ref, 'YYYY-MM-DD'), query_id FROM discovery_links GROUP BY date_ref, query_id")
        for row in cursor:
            if row[0] and row[1]:
                runs.add(f"{row[0]}_{row[1]}")
    except Exception as e:
        print(f"Lỗi khi lấy lịch sử từ Snowflake: {e}")
    finally:
        cursor.close()
    return runs

def parse_serper_date(raw_date):
    """Chuyển ngày của Google thành chuẩn YYYY-MM-DD, nếu không có thì trả về None"""
    if not raw_date:
        return None
        
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
        
    return None

def save_to_snowflake(conn, target, query_id, search_query, date_ref, results):
    """Lưu danh sách link vào bảng discovery_links, cho phép 1 link đi kèm nhiều query_id"""
    if not results:
        return 0
        
    cursor = conn.cursor()
    success_count = 0
    
    # Lệnh MERGE cập nhật điều kiện khớp: Cùng url_hash VÀ cùng query_id
    sql = """
    MERGE INTO discovery_links target_table
    USING (SELECT %s AS url_hash, %s AS target, %s AS query_id, %s AS search_query, 
                  %s AS date_ref, %s AS domain, %s AS url, %s AS title, 
                  %s AS snippet, %s AS published_date) source
    ON target_table.url_hash = source.url_hash AND target_table.query_id = source.query_id
    WHEN NOT MATCHED THEN 
        INSERT (url_hash, target, query_id, search_query, date_ref, domain, url, title, snippet, published_date)
        VALUES (source.url_hash, source.target, source.query_id, source.search_query, source.date_ref, 
                source.domain, source.url, source.title, source.snippet, source.published_date)
    """
    
    for res in results:
        link = res.get("link", "")
        if not link:
            continue
            
        url_hash = hashlib.sha256(link.encode('utf-8')).hexdigest()
        domain = link.split("/")[2] if "://" in link else ""
        
        raw_date = res.get("date", "")
        published_date = parse_serper_date(raw_date)
        title = res.get("title", "")
        snippet = res.get("snippet", "")
        
        try:
            cursor.execute(sql, (
                url_hash, target, query_id, search_query, date_ref, 
                domain, link, title, snippet, published_date
            ))
            success_count += 1
        except Exception as e:
            print(f"Lỗi khi lưu link {link}: {e}")
            
    conn.commit()
    cursor.close()
    return success_count

def fetch_single_query(client, template_info, date_str, next_date_str, day, month, year):
    """Hàm phụ để chạy luồng riêng cho 1 query"""
    query_id = template_info.get("id", "unknown")
    target = template_info.get("target", "unknown")
    template = template_info["template"]
    
    query = template.format(day=day, month=month, year=year)
    print(f"Đang tìm: '{query}' ({date_str})")
    
    results = client.search(query, start_date=date_str, end_date=next_date_str)
    
    # Trả về nguyên cục dữ liệu để hàm main xử lý lưu DB
    return {
        "target": target,
        "query_id": query_id,
        "query": query,
        "results": results
    }

def main():
    config = load_config()
    client = SerperClient(config)
    
    print("Đang kết nối đến Snowflake...")
    conn = get_snowflake_connection()
    print("Kết nối thành công!")

    start_date = datetime.strptime(config["date_range"]["start"], "%Y-%m-%d")
    end_date = datetime.strptime(config["date_range"]["end"], "%Y-%m-%d")
    
    templates = config.get("query_templates", [])
    skip_if_exists = config["resume"]["skip_if_date_exists"]

    existing_runs = set()
    if skip_if_exists:
        existing_runs = get_existing_runs_from_snowflake(conn)
        print(f"Đã tìm thấy {len(existing_runs)} lượt quét cũ.")

    print("Bắt đầu chạy đa luồng thu thập link...")
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        next_date = current_date + timedelta(days=1)
        next_date_str = next_date.strftime("%Y-%m-%d")
        
        # Mở một "hồ bơi" chứa tối đa 4 công nhân (workers) chạy song song
        with ThreadPoolExecutor(max_workers=len(templates)) as executor:
            futures = []
            
            for template_info in templates:
                query_id = template_info.get("id", "unknown")
                run_key = f"{date_str}_{query_id}"
                
                if skip_if_exists and run_key in existing_runs:
                    print(f"⏩ Bỏ qua {run_key} (đã có dữ liệu)")
                    continue

                # Giao việc cho công nhân chạy ngầm
                future = executor.submit(
                    fetch_single_query, 
                    client, template_info, date_str, next_date_str, 
                    current_date.day, current_date.month, current_date.year
                )
                futures.append(future)

            # Gom kết quả từ các công nhân khi họ làm xong
            for future in as_completed(futures):
                data = future.result()
                
                # Ghi vào DB tuần tự để chống kẹt
                saved_count = save_to_snowflake(
                    conn, data["target"], data["query_id"], 
                    data["query"], date_str, data["results"]
                )
                print(f"Đã lưu {saved_count} links cho {data['query_id']} ({date_str}).")

        current_date += timedelta(days=1)

    conn.close()
    print("Hoàn tất thu thập link!")

if __name__ == "__main__":
    main()