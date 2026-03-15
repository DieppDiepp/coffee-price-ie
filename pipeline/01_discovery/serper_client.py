import os
import time
import requests
from datetime import datetime

class SerperClient:
    def __init__(self, config):
        self.api_keys = [
            value for key, value in os.environ.items() 
            if key.startswith("SERPER_KEY_") and value.strip()
        ]
        
        if not self.api_keys:
            raise ValueError("Khong tim thay API Key nao bat dau bang SERPER_KEY_ trong .env!")

        self.settings = config.get("serper", {})
        self.rate_limit = config["rate_limit"]
        
        self.current_key_idx = 0
        self.call_count = 0

    def get_current_key(self):
        if self.call_count >= self.rate_limit["rotate_keys_every_n_calls"]:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            self.call_count = 0
            print(f"Da chuyen sang API Key so {self.current_key_idx + 1}")
        
        return self.api_keys[self.current_key_idx]

    def search(self, query, start_date=None, end_date=None):
        api_key = self.get_current_key()
        self.call_count += 1
        
        time.sleep(self.rate_limit["delay_between_calls_sec"])

        url = "https://google.serper.dev/search"
        
        # Google dung cu phap -site: de loai tru cac trang khong mong muon
        exclude_domains = self.settings.get("exclude_domains", [])
        for domain in exclude_domains:
            query += f" -site:{domain}"

        payload = {
            "q": query,
            "gl": "vn",
            "hl": "vi",
            "num": self.settings.get("max_results", 15)
        }

        # Google dung tham so tbs de loc ngay thang, dinh dang MM/DD/YYYY
        if start_date and end_date:
            try:
                s_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                e_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")
                payload["tbs"] = f"cdr:1,cd_min:{s_date},cd_max:{e_date}"
            except Exception as e:
                print(f"Loi dinh dang ngay thang cho Serper: {e}")

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            # Serper tra ve ket qua tim kiem trong mang "organic"
            return data.get("organic", [])
        else:
            print(f"Loi goi API Serper: {response.status_code} - {response.text}")
            return []