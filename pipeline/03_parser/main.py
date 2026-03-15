import argparse
import glob
import hashlib
import json
import logging
import os
import re
from datetime import datetime

import trafilatura
from bs4 import BeautifulSoup
from underthesea import sent_tokenize

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path="config/parser.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_article_id(url, date_ref):
    unique_string = f"{url}|{date_ref}"
    return hashlib.sha1(unique_string.encode('utf-8')).hexdigest()

def flatten_tables(html_content):
    """Fallback to flatten tables into pseudo-sentences."""
    soup = BeautifulSoup(html_content, 'html.parser')
    flattened_text = []
    
    # Process all tables
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            col_texts = [col.get_text(strip=True) for col in cols if col.get_text(strip=True)]
            if col_texts:
                # Create pseudo-sentence: Col 1 | Col 2 | Col 3
                flattened_text.append(" | ".join(col_texts))
        
        # Remove the table from the soup so it's not double-processed
        table.decompose()
    
    # Return flattened table text + remaining text from soup
    remaining_text = soup.get_text(separator='\n', strip=True)
    return "\n".join(flattened_text + [remaining_text])

def extract_text(raw_html):
    """Use Trafilatura first, fallback to BeautifulSoup if empty or mostly tables."""
    extracted = trafilatura.extract(raw_html, include_tables=False)
    has_table = "</table>" in raw_html.lower()
    
    # If trafilatura fails or we know there are tables (which trafilatura often ruins or we excluded), 
    # we use our custom fallback to ensure tables are flattened properly.
    if not extracted or has_table:
        parser_method = "trafilatura+bs4_fallback"
        raw_text = flatten_tables(raw_html)
    else:
        parser_method = "trafilatura"
        raw_text = extracted
        
    return raw_text, parser_method, has_table

def is_candidate(sentence, signals):
    s_lower = sentence.lower()
    
    has_coffee = any(sig in s_lower for sig in signals["coffee"])
    has_price = any(sig in s_lower for sig in signals["price"])
    has_hard_negative = any(sig in s_lower for sig in signals["hard_negative"])
    
    is_valid = has_coffee and has_price
    
    noise_flags = []
    if has_hard_negative and is_valid:
        noise_flags.append("mixed_commodity")
        
    return is_valid, noise_flags

def process_file(input_file, output_file, config):
    logging.info(f"Processing {input_file} -> {output_file}")
    
    processed_ids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line)
                processed_ids.add(record['article_id'])
                
    records_to_write = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            raw_record = json.loads(line)
            # Only process if status not explicitly failed (assuming successful ones have raw_html)
            if 'raw_html' not in raw_record or not raw_record['raw_html']:
                continue
                
            article_id = generate_article_id(raw_record['url'], raw_record.get('date_ref', ''))
            
            if article_id in processed_ids:
                continue
                
            raw_text, parser_method, has_table = extract_text(raw_record['raw_html'])
            
            if not raw_text:
                continue
                
            # Sentence split using underthesea
            try:
                sentences = sent_tokenize(raw_text)
            except Exception as e:
                # Fallback regex splitter
                logging.warning(f"underthesea failed, using regex fallback: {e}")
                sentences = re.split(r'(?<=[.!?]) +', raw_text)
                
            candidate_sentences = []
            
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                is_valid, noise_flags = is_candidate(sentence, config['signals'])
                
                if is_valid:
                    candidate_id = hashlib.sha1(f"{article_id}_{i}".encode('utf-8')).hexdigest()
                    
                    candidate_sentences.append({
                        "candidate_id": candidate_id,
                        "sentence_index": i,
                        "sentence_text": sentence,
                        "context_prev": sentences[i-1].strip() if i > 0 else "",
                        "context_next": sentences[i+1].strip() if i < len(sentences) - 1 else "",
                        "candidate_reason": "coffee_and_price_match",
                        "noise_flags": noise_flags
                    })
            
            article_record = {
                "article_id": article_id,
                "url": raw_record.get('url'),
                "final_url": raw_record.get('url'),
                "domain": raw_record.get('domain'),
                "source_id": raw_record.get('domain'), # Using domain as source_id for now
                "date_ref": raw_record.get('date_ref'),
                "published_at": raw_record.get('published_at', ''),
                "published_at_alignment": "", # Logic to compute alignment could be added here
                "collected_at": raw_record.get('collected_at'),
                "discovery_rank": raw_record.get('discovery_rank', 0),
                "title": raw_record.get('title', ''),
                "raw_text": raw_text,
                "main_html": "", # Can be populated if needed
                "lead": sentences[0] if sentences else "",
                "parser_status": "success",
                "parser_method": parser_method,
                "parser_warnings": [],
                "has_table": has_table,
                "noise_flags": list(set([flag for c in candidate_sentences for flag in c['noise_flags']])),
                "sentence_count": len(sentences),
                "candidate_count": len(candidate_sentences),
                "candidate_sentences": candidate_sentences
            }
            
            records_to_write.append(article_record)
            
    if records_to_write:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'a', encoding='utf-8') as f:
            for record in records_to_write:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        logging.info(f"Appended {len(records_to_write)} new records to {output_file}")
    else:
        logging.info("No new records to process.")

def main():
    parser = argparse.ArgumentParser(description="Parse Raw HTML to Articles and Candidate Sentences.")
    parser.add_argument("--input", default="data/02_raw_articles/*.jsonl", help="Input glob pattern")
    parser.add_argument("--resume", action="store_true", help="Resume from last processed")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files to process")
    
    args = parser.parse_args()
    config = load_config()
    
    input_files = glob.glob(args.input)
    if args.limit:
        input_files = input_files[:args.limit]
        
    for input_file in input_files:
        filename = os.path.basename(input_file)
        output_file = os.path.join(config['output_dir'], filename)
        process_file(input_file, output_file, config)

if __name__ == "__main__":
    main()