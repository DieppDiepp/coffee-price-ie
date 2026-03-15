import argparse
import glob
import json
import logging
import os
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def serialize_mention(m):
    """Chuyển đổi record JSON thành một câu văn bản mượt mà để PhoBERT có thể hiểu."""
    if not m:
        return "Không có thông tin giá."
    return f"Cà phê {m.get('commodity', '')} tại {m.get('location', '')} có giá từ {m.get('price_low', '')} đến {m.get('price_high', '')} {m.get('currency', '')}/{m.get('unit', '')}"

def main():
    parser = argparse.ArgumentParser(description="Tính toán Disagreement/Similarity bằng PhoBERT.")
    parser.add_argument("--input", default="data/04_price_mentions/*.jsonl", help="Input glob pattern")
    parser.add_argument("--output", default="data/05_disagreement/ie_benchmark.jsonl", help="Output file")
    
    args = parser.parse_args()
    
    # Đọc tất cả các mentions đã trích xuất
    candidates = defaultdict(dict)
    input_files = glob.glob(args.input)
    
    for fpath in input_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    cid = record['candidate_id']
                    mid = record['model_id']
                    candidates[cid][mid] = record
                except Exception as e:
                    pass

    logging.info(f"Đã tải {len(candidates)} ứng viên (candidates) để phân tích bất đồng.")

    try:
        import numpy as np
        import torch
        from transformers import AutoModel, AutoTokenizer
        from underthesea import word_tokenize
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Đang tải mô hình PhoBERT lên thiết bị: {device}...")
        
        tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")
        model = AutoModel.from_pretrained("vinai/phobert-base-v2").to(device)
        
        def get_embedding(text):
            # Khuyến nghị của PhoBERT: Word segmentation trước khi đưa vào mô hình
            seg_text = word_tokenize(text, format="text")
            inputs = tokenizer(seg_text, return_tensors="pt", truncation=True, max_length=256).to(device)
            with torch.no_grad():
                outputs = model(**inputs)
            # Lấy trung bình (mean pooling) của last_hidden_state làm vector đại diện cho câu
            return outputs.last_hidden_state.mean(dim=1).cpu().numpy()[0]

        def cosine_sim(v1, v2):
            num = np.dot(v1, v2)
            den = np.linalg.norm(v1) * np.linalg.norm(v2)
            return float(num/den) if den > 0 else 0.0

    except ImportError as e:
        logging.error(f"Thiếu thư viện transformers/underthesea. Vui lòng cài đặt. Lỗi: {e}")
        return

    results = []
    # So sánh Qwen với Llama (nếu có) hoặc với Baseline (mặc định luôn có)
    for cid, models in candidates.items():
        if 'qwen' in models:
            target_model = 'llama' if 'llama' in models else 'baseline'
            
            if target_model in models:
                q_text = serialize_mention(models['qwen'])
                t_text = serialize_mention(models[target_model])
                
                v_q = get_embedding(q_text)
                v_t = get_embedding(t_text)
                sim = cosine_sim(v_q, v_t)
                
                results.append({
                    "candidate_id": cid,
                    "article_id": models['qwen'].get('article_id'),
                    "primary_model": "qwen",
                    "target_model": target_model,
                    "qwen_mention": models['qwen'],
                    "target_mention": models[target_model],
                    "phobert_similarity": sim,
                    "disagreement_flag": sim < 0.92 # Chỉnh ngưỡng xuống một chút cho baseline
                })

    if results:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
                
        logging.info(f"Đã lưu {len(results)} bản ghi Disagreement vào {args.output}")
        logging.info(f"Độ tương đồng trung bình: {np.mean([r['phobert_similarity'] for r in results]):.4f}")
    else:
        logging.info("Không có dữ liệu hợp lệ (cần cả Qwen và Llama) để so sánh.")

if __name__ == "__main__":
    main()