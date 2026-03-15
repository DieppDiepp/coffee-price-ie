import os
import json
import requests
import re
from collections import Counter
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_KEY_1")
HEADERS = {
    "X-API-KEY": SERPER_API_KEY,
    "Content-Type": "application/json"
}

def get_autocomplete_suggestions(seed_queries):
    suggestions = set()
    url = "https://google.serper.dev/autocomplete"
    
    for q in seed_queries:
        payload = {"q": q, "gl": "vn"}
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("suggestions", []):
                suggestions.add(item.get("value"))
    return list(suggestions)

def sample_search_results(queries, days=3):
    texts = []
    url = "https://google.serper.dev/search"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    tbs = f"cdr:1,cd_min:{start_date.strftime('%m/%d/%Y')},cd_max:{end_date.strftime('%m/%d/%Y')}"

    for q in queries:
        payload = {
            "q": q,
            "gl": "vn",
            "hl": "vi",
            "tbs": tbs,
            "num": 10
        }
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code == 200:
            organic = response.json().get("organic", [])
            for res in organic:
                texts.append(res.get("title", ""))
                texts.append(res.get("snippet", ""))
    return texts

def extract_ngrams(texts, n=3):
    ngrams_list = []
    for text in texts:
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            if not any(char.isdigit() for char in ngram):
                ngrams_list.append(ngram)
                
    return Counter(ngrams_list)

def main():
    print("Bat dau EDA cho Query...")
    
    seeds = ["giá cà phê ", "giá cà phê robusta ", "giá cà phê arabica "]
    print(f"Hat giong ban dau: {seeds}")
    
    print("Dang lay goi y Autocomplete...")
    expanded_queries = get_autocomplete_suggestions(seeds)
    print(f"Gom duoc {len(expanded_queries)} goi y thuc te.")
    
    print(f"Dang cao sample bao chi tu cac goi y...")
    # Lay het danh sach (ban co the doi expanded_queries[:5] neu muon gioi han test)
    sample_texts = sample_search_results(expanded_queries, days=3) 
    print(f"Thu duoc {len(sample_texts)} doan van ban title va snippet.")
    
    trigrams = extract_ngrams(sample_texts, n=3)
    quadgrams = extract_ngrams(sample_texts, n=4)
    
    # Dinh vi thu muc hien tai cua file code de luu output
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_txt_path = os.path.join(current_dir, "query_report.txt")
    report_json_path = os.path.join(current_dir, "query_report.json")
    
    # Tao noi dung report cho file text
    report_content = "KET QUA PHAN TICH TAN SUAT TU KHOA (EDA QUERY)\n"
    report_content += "="*50 + "\n\n"
    
    report_content += "1. Top cum 3 tu (Tri-grams) xuat hien nhieu nhat tren tieu de/snippet:\n"
    for ngram, count in trigrams.most_common(15):
        report_content += f"   - '{ngram}': {count} lan\n"
        
    report_content += "\n2. Top cum 4 tu (4-grams) xuat hien nhieu nhat tren tieu de/snippet:\n"
    for ngram, count in quadgrams.most_common(15):
        report_content += f"   - '{ngram}': {count} lan\n"
        
    report_content += "\n3. Danh sach goi y tu Google Autocomplete:\n"
    for q in expanded_queries:
        report_content += f"   - {q}\n"

    # Luu file txt
    with open(report_txt_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    # Luu file json
    json_data = {
        "trigrams": dict(trigrams.most_common(15)),
        "quadgrams": dict(quadgrams.most_common(15)),
        "autocomplete_suggestions": expanded_queries
    }
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    print("\nHoan tat! Da luu ket qua vao thu muc hien tai:")
    print(f"- {report_txt_path}")
    print(f"- {report_json_path}")

if __name__ == "__main__":
    main()