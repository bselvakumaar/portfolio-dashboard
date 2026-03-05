import requests
import json

URL = "http://127.0.0.1:8080/market/snapshot?top_n=5"
try:
    resp = requests.get(URL, timeout=30)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
