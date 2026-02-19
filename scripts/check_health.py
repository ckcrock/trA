import requests
import time
import sys

def check_health(url="http://localhost:8000/api/docs", max_retries=30, delay=2):
    print(f"Checking health at {url}...")
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ System is UP and Running!")
                return True
        except requests.ConnectionError:
            pass
        
        print(f"Waiting for system to start... ({i+1}/{max_retries})")
        time.sleep(delay)
    
    print("❌ System failed to start in time.")
    return False

if __name__ == "__main__":
    if not check_health():
        sys.exit(1)
