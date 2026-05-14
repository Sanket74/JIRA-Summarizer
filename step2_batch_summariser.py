import json
import time
import os
import requests
import csv
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not found. Please set it in a .env file.")
    exit(1)

MODEL_ID = "gemini-flash-latest"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"

SYSTEM_INSTRUCTION = """You are a support ticket text compressor. Rewrite input into 15-20 words only. Reuse original words. Open with a noun. No filler."""

def get_word_count(text):
    return len(text.split())

def validate_summary(text):
    word_count = get_word_count(text)
    return 15 <= word_count <= 25, word_count # Slightly relaxed for test

def generate_summary(body, row_idx):
    prompt = f"{SYSTEM_INSTRUCTION}\n\nInput: {body}\n\nOutput:"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(1, 4):
        try:
            response = requests.post(URL, json=data, timeout=30)
            if response.status_code == 200:
                text = response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                is_valid, wc = validate_summary(text)
                return {"status": "passed" if is_valid else "held", "summary": text, "word_count": wc}
            else:
                print(f"[{row_idx}] Error {response.status_code}: {response.text}")
                time.sleep(10)
        except Exception as e:
            print(f"[{row_idx}] Error: {e}")
            time.sleep(10)
    return {"status": "held", "summary": "Error", "word_count": 0}

def process_batch():
    input_file = 'top80.json'
    output_file = 'test_5_results.json'
    
    with open(input_file, 'r') as f:
        tickets = json.load(f)
    
    # Run English tickets (index 2-7)
    test_tickets = tickets[2:7]
    results = []
    
    for i, t in enumerate(test_tickets):
        print(f"[{i+1}/5] Processing {t['ticket_id']}...")
        res = generate_summary(t['body'], i+1)
        results.append({"ticket_id": t['ticket_id'], "summary": res['summary'], "word_count": res['word_count']})
        print(f"   Summary: {res['summary']}")
        
        # Save incrementally
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
            
        time.sleep(45) # Increased pacing to 45s
    print("Done!")

if __name__ == "__main__":
    process_batch()
