import os
import time
import requests

class TavilyClient:
    def __init__(self, config):
        self.api_keys = [
            value for key, value in os.environ.items() 
            if key.startswith("TAVILY_KEY_") and value.strip()
        ]
        
        if not self.api_keys:
            raise ValueError("Khong tim thay API Key nao trong .env!")

        self.tavily_settings = config["tavily"]
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

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": self.tavily_settings["search_depth"],
            "max_results": self.tavily_settings["max_results"],
            "exclude_domains": self.tavily_settings["exclude_domains"]
        }
        
        # Them bo loc ngay thang neu co
        if start_date:
            payload["include_images"] = False # Giam tai du lieu thua
            # API cua Tavily co the nhan tham so time filter tuy thuoc vao tai khoan
            # Minh truyen thang vao payload theo cau truc ban de xuat
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date

        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            print(f"Loi goi API: {response.status_code} - {response.text}")
            return []