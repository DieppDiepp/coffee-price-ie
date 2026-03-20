import argparse
import hashlib
import json
import logging
import os
import re
from datetime import datetime

import trafilatura
from bs4 import BeautifulSoup

from snowflake_utils import get_snowflake_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text(raw_html):
    """Sử dụng Trafilatura để lấy chữ sạch, và dùng BeautifulSoup để trải phẳng (flatten) bảng."""
    # 1. Lấy text sạch (bỏ qua table để tránh bị lỗi format)
    extracted_text = trafilatura.extract(raw_html, include_tables=False) or ""
    
    # 2. Nếu có bảng, dùng BS4 để trải phẳng riêng các bảng đó
    has_table = "</table>" in raw_html.lower()
    if has_table:
        soup = BeautifulSoup(raw_html, 'html.parser')
        flattened_tables = []
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                col_texts = [re.sub(r'\s+', ' ', col.get_text(strip=True)) for col in cols if col.get_text(strip=True)]
                if col_texts:
                    flattened_tables.append(" | ".join(col_texts))
        
        if flattened_tables:
            # Gắn dữ liệu bảng vào cuối bài viết
            extracted_text = extracted_text + "\n\n" + "\n".join(flattened_tables)
            
    # 3. Fallback cuối cùng nếu trafilatura thất bại hoàn toàn
    if not extracted_text.strip():
        soup = BeautifulSoup(raw_html, 'html.parser')
        # Xóa các thẻ rác
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        extracted_text = soup.get_text(separator='\n', strip=True)
        
    return extracted_text

def extract_metadata(raw_html):
    """Extract metadata like real_title, real_published_at, and author."""
    metadata = {
        "real_title": None,
        "real_published_at": None,
        "author": None
    }
    
    if not raw_html:
        return metadata
        
    # Try Trafilatura extract_metadata first
    extracted_meta = trafilatura.extract_metadata(raw_html)
    if extracted_meta:
        metadata["real_title"] = extracted_meta.title
        metadata["real_published_at"] = extracted_meta.date
        metadata["author"] = extracted_meta.author
        
    # Fallback to BeautifulSoup if any is missing
    if not all(metadata.values()):
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        if not metadata["real_title"]:
            if soup.title and soup.title.string:
                metadata["real_title"] = soup.title.string.strip()
            else:
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    metadata["real_title"] = og_title.get("content", "").strip()
                    
        if not metadata["real_published_at"]:
            time_tag = soup.find("time")
            if time_tag and time_tag.get("datetime"):
                metadata["real_published_at"] = time_tag.get("datetime").strip()
            else:
                meta_time = soup.find("meta", property="article:published_time")
                if meta_time:
                    metadata["real_published_at"] = meta_time.get("content", "").strip()
                    
        if not metadata["author"]:
            meta_author = soup.find("meta", attrs={"name": "author"})
            if meta_author:
                metadata["author"] = meta_author.get("content", "").strip()
                
    # Format length limits
    if metadata["real_title"]:
        metadata["real_title"] = metadata["real_title"][:1000]
    if metadata["author"]:
        metadata["author"] = metadata["author"][:200]
        
    return metadata

def process_records_from_db(conn, limit=None):
    cursor = conn.cursor()
    
    # Select from scraped_html that are not in parsed_articles
    query = """
    SELECT s.url_hash, s.html_content 
    FROM scraped_html s 
    LEFT JOIN parsed_articles p ON s.url_hash = p.url_hash 
    WHERE p.url_hash IS NULL
    """
    
    if limit:
        query += f" LIMIT {limit}"
        
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        logging.info("No new records to process.")
        return

    logging.info(f"Found {len(rows)} new records to parse.")
    
    parsed_count = 0
    for row in rows:
        url_hash = row[0]
        html_content = row[1]
        
        if not html_content:
            continue
            
        try:
            cleaned_text = extract_text(html_content)
            if not cleaned_text or not cleaned_text.strip():
                # Bỏ qua nếu không parse được chữ gì
                continue
                
            metadata = extract_metadata(html_content)
            
            # Insert into parsed_articles
            cursor.execute("""
                INSERT INTO parsed_articles (url_hash, real_title, real_published_at, author, cleaned_text)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                url_hash, 
                metadata["real_title"], 
                metadata["real_published_at"] if metadata["real_published_at"] else None, 
                metadata["author"], 
                cleaned_text
            ))
            
            parsed_count += 1
            if parsed_count % 100 == 0:
                conn.commit()
                logging.info(f"Processed {parsed_count} records...")
                
        except Exception as e:
            logging.error(f"Error parsing {url_hash}: {e}")
            conn.rollback()

    conn.commit()
    logging.info(f"Successfully processed {parsed_count} records.")

def main():
    parser = argparse.ArgumentParser(description="Parse Raw HTML to Articles into Snowflake.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records to process")
    
    args = parser.parse_args()
    
    logging.info("Connecting to Snowflake...")
    try:
        conn = get_snowflake_connection()
        process_records_from_db(conn, limit=args.limit)
    except Exception as e:
        logging.error(f"Database connection or execution error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    main()