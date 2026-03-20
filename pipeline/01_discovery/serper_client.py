import os
import time
import requests
import threading
from datetime import datetime

class SerperClient:
    def __init__(self, config):
        raw_keys = {
            key: value for key, value in os.environ.items() 
            if key.startswith("SERPER_KEY_") and value.strip()
        }
        self.api_keys = [raw_keys[k] for k in sorted(raw_keys.keys())]
        
        if not self.api_keys:
            raise ValueError("Khong tim thay API Key nao bat dau bang SERPER_KEY_ trong .env!")

        print(f"🔑 Đã tìm thấy {len(self.api_keys)} API keys.")

        self.settings = config.get("serper", {})
        self.rate_limit = config["rate_limit"]
        
        self.current_key_idx = 0
        self.call_count = 0
        
        # Thêm ổ khóa để an toàn khi chạy song song nhiều luồng
        self.lock = threading.Lock()

    def mask_key(self, key):
        if len(key) > 8:
            return f"{key[:4]}...{key[-4:]}"
        return "***"

    def _rotate_key(self, reason):
        old_idx = self.current_key_idx
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        self.call_count = 0
        print(f"🔄 {reason}. Đã chuyển từ Key {old_idx + 1} sang Key {self.current_key_idx + 1}.")

    def get_current_key(self):
        # Mở khóa: Chỉ 1 luồng được vào đây kiểm tra và lấy key tại 1 thời điểm
        with self.lock:
            limit = self.rate_limit.get("rotate_keys_every_n_calls", 100)
            if self.call_count >= limit:
                self._rotate_key(f"Đã đạt giới hạn {limit} lượt gọi")
            
            current_api = self.api_keys[self.current_key_idx]
            
            if self.call_count == 0:
                print(f"👉 Dùng API Key số {self.current_key_idx + 1} ({self.mask_key(current_api)})")
                
            self.call_count += 1
            return current_api

    def search(self, query, start_date=None, end_date=None):
        api_key = self.get_current_key()
        
        time.sleep(self.rate_limit.get("delay_between_calls_sec", 1))

        url = "https://google.serper.dev/search"
        
        exclude_domains = self.settings.get("exclude_domains", [])
        for domain in exclude_domains:
            query += f" -site:{domain}"

        payload = {
            "q": query,
            "gl": "vn",
            "hl": "vi",
            "num": self.settings.get("max_results", 15)
        }

        if start_date and end_date:
            try:
                s_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                e_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                payload["tbs"] = f"cdr:1,cd_min:{s_date},cd_max:{e_date}"
            except Exception as e:
                print(f"Lỗi ngày tháng: {e}")

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json().get("organic", [])
            
        elif response.status_code in [403, 429]:
            print(f"⚠️ API Key số {self.current_key_idx + 1} báo lỗi {response.status_code}.")
            with self.lock:
                self._rotate_key("Ép buộc xoay key do lỗi 403/429")
            return []
            
        else:
            print(f"❌ Lỗi API: {response.status_code} - {response.text}")
            return []