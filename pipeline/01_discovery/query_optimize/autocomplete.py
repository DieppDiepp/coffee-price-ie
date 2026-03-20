# Thực hiện code auto complete để nghiên cứu key word search 

import requests
url = "https://google.serper.dev/autocomplete"

payload = {
  "q": "giá cà phê ",
  "gl": "vn"
}
headers = {
  'X-API-KEY': 'a545d91ae3f40c2458fb7940413488aaeaea3047',
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, json=payload)

print(response.text)