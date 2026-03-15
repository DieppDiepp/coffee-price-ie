import argparse
import glob
import hashlib
import json
import logging
import os
import re
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path="config/ie.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_mention_id(candidate_id, model_id, prompt_version, index):
    unique_string = f"{candidate_id}|{model_id}|{prompt_version}|{index}"
    return hashlib.sha1(unique_string.encode('utf-8')).hexdigest()

def normalize_location(loc):
    if not loc:
        return "Unknown"
    loc = loc.lower()
    if "đắk lắk" in loc or "dak lak" in loc: return "Dak Lak"
    if "đắk nông" in loc or "dak nong" in loc: return "Dak Nong"
    if "gia lai" in loc: return "Gia Lai"
    if "lâm đồng" in loc or "lam dong" in loc: return "Lam Dong"
    if "tây nguyên" in loc or "tay nguyen" in loc: return "Tay Nguyen"
    return "Unknown"

def baseline_rule_extractor(sentence):
    """A baseline regex extractor for numeric fields to sanity check."""
    # This is a very simplistic baseline
    prices = re.findall(r'(\d{2,3}(?:[.,]\d{3})*|\d{2,3})\s*(đ/kg|đồng/kg)', sentence.lower())
    mentions = []
    if prices:
        try:
            val = float(prices[0][0].replace(',', '.').replace('.', ''))
            mentions.append({
                "commodity": "cà phê Robusta",
                "price_low": val,
                "price_high": val,
                "currency": "VND",
                "unit": "kg",
                "price_direction": "stable",
                "price_change": 0,
                "location": "Tay Nguyen",
                "price_type": "spot",
                "evidence_span": prices[0][0] + " " + prices[0][1]
            })
        except:
            pass
    return mentions

def build_prompt(config, candidate, article):
    user_prompt = f"""
Thông tin bài báo:
- Domain: {article.get('domain')}
- Ngày xuất bản: {article.get('published_at')}
- Ngày tham chiếu: {article.get('date_ref')}

Câu cần trích xuất:
"{candidate['sentence_text']}"

Ngữ cảnh trước: "{candidate['context_prev']}"
Ngữ cảnh sau: "{candidate['context_next']}"

Chỉ trả về cấu trúc JSON Array: {json.dumps(config['extraction_schema'])}
"""
    return [
        {"role": "system", "content": config['system_prompt']},
        {"role": "user", "content": user_prompt}
    ]

class HFExtractor:
    def __init__(self, model_id, config):
        self.model_id = model_id
        self.config = config
        
        logging.info(f"Loading HF Model: {model_id}...")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto",
                quantization_config=quantization_config,
                torch_dtype=torch.float16,
            )
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
            )
            self.is_mock = False
        except ImportError as e:
            logging.warning(f"Could not load transformers/bitsandbytes. Running in Mock/Baseline mode. Error: {e}")
            self.is_mock = True

    def extract(self, candidate, article):
        if self.is_mock:
            return baseline_rule_extractor(candidate['sentence_text'])
            
        messages = build_prompt(self.config, candidate, article)
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        outputs = self.pipe(
            prompt,
            max_new_tokens=512,
            do_sample=False,
            temperature=0.0,
        )
        
        generated_text = outputs[0]["generated_text"][len(prompt):].strip()
        
        # Parse JSON
        try:
            # Strip markdown block if present
            if generated_text.startswith("```json"):
                generated_text = generated_text[7:]
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]
                
            mentions = json.loads(generated_text)
            if not isinstance(mentions, list):
                mentions = [mentions]
            return mentions
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON from {self.model_id}: {generated_text}")
            return []

def process_file(input_file, output_file, config, extractor, model_name):
    logging.info(f"Processing {input_file} -> {output_file} with {model_name}")
    
    processed_candidates = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line)
                if record['model_id'] == model_name:
                    processed_candidates.add(record['candidate_id'])
                
    records_to_write = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            article = json.loads(line)
            
            for candidate in article.get('candidate_sentences', []):
                if candidate['candidate_id'] in processed_candidates:
                    continue
                    
                # 1. Chạy LLM Extraction
                raw_mentions = extractor.extract(candidate, article)
                
                # 2. Chạy Baseline Extraction (luôn chạy để có mốc so sánh ở Bước 05)
                baseline_mentions = baseline_rule_extractor(candidate['sentence_text'])
                
                # Gộp cả hai loại vào danh sách xử lý
                all_to_process = [ (raw_mentions, model_name, "llm") ]
                if model_name == 'qwen': # Chỉ cần thêm baseline 1 lần khi chạy model chính
                    all_to_process.append( (baseline_mentions, "baseline", "rule") )

                for mentions_list, m_id, m_method in all_to_process:
                    for idx, rm in enumerate(mentions_list):
                        # Validate and normalize
                        commodity = rm.get('commodity', '').lower()
                        if 'cà phê' not in commodity and 'robusta' not in commodity:
                            continue 
                            
                        price_low = rm.get('price_low')
                        price_high = rm.get('price_high')
                        if price_high is None and price_low is not None:
                            price_high = price_low
                            
                        mention_record = {
                            "mention_id": generate_mention_id(candidate['candidate_id'], m_id, config['prompt_version'], idx),
                            "article_id": article['article_id'],
                            "candidate_id": candidate['candidate_id'],
                            "commodity": rm.get('commodity', 'cà phê'),
                            "price_low": price_low,
                            "price_high": price_high,
                            "currency": rm.get('currency', 'VND'),
                            "unit": rm.get('unit', 'kg'),
                            "normalized_unit": "VND/kg" if rm.get('currency') == 'VND' and rm.get('unit') == 'kg' else None,
                            "price_direction": rm.get('price_direction', 'unknown'),
                            "price_change": rm.get('price_change', 0),
                            "location": normalize_location(rm.get('location', '')),
                            "date_ref": article.get('date_ref'),
                            "price_type": rm.get('price_type', 'spot'),
                            "evidence_span": rm.get('evidence_span', ''),
                            "evidence_sentence": candidate['sentence_text'],
                            "source_id": article.get('source_id'),
                            "doc_url": article.get('url'),
                            "published_at": article.get('published_at'),
                            "collected_at": article.get('collected_at'),
                            "extraction_method": m_method,
                            "model_id": m_id,
                            "prompt_version": config['prompt_version'],
                            "validation_status": "valid"
                        }
                        records_to_write.append(mention_record)
                    
                processed_candidates.add(candidate['candidate_id'])
            
            # Flush periodically
            if len(records_to_write) >= 100:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'a', encoding='utf-8') as out_f:
                    for record in records_to_write:
                        out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                records_to_write = []

    # Final flush
    if records_to_write:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'a', encoding='utf-8') as out_f:
            for record in records_to_write:
                out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
        logging.info(f"Appended records to {output_file}")
    else:
        logging.info("No new candidates to process.")

def main():
    parser = argparse.ArgumentParser(description="Extract Price Mentions using LLMs.")
    parser.add_argument("--input", default="data/03_articles/*.jsonl", help="Input glob pattern")
    parser.add_argument("--resume", action="store_true", help="Resume from last processed")
    parser.add_argument("--model", choices=['qwen', 'llama'], default='qwen', help="Model to use")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of files to process")
    
    args = parser.parse_args()
    config = load_config()
    
    model_id = config['models'][args.model]
    extractor = HFExtractor(model_id, config)
    
    input_files = glob.glob(args.input)
    if args.limit:
        input_files = input_files[:args.limit]
        
    for input_file in input_files:
        filename = os.path.basename(input_file)
        output_file = os.path.join(config['output_dir'], filename)
        process_file(input_file, output_file, config, extractor, args.model)

if __name__ == "__main__":
    main()