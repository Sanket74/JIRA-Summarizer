import csv
import json
import urllib.request
import urllib.error
import time
import os
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "AIzaSyAoJEnlcaHHwjaTFSUS5rOEBmK0m9compI"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

SYSTEM_PROMPT = """You are a support ticket text compressor.

Your task is to **rewrite the input into a shorter version**, not summarize it.

---

### **RULES (STRICT)**

* Output must be **15–20 words only**
* **Reuse original words and phrasing** as much as possible
* Only **remove unnecessary words** (compression task)
* **Do not rephrase or generalize**
* **Do not introduce new information**
* **Do not infer causes unless explicitly stated**
* Keep meaning **exactly the same as input**
* Avoid prefixes like “Customer…”
* Output should feel like a **trimmed version of the original sentence**

---

### **HARD CONSTRAINT**

* If the output contains **words not present in the input**, regenerate the answer
* If output exceeds **20 words or is below 15 words**, regenerate

---

### **FEW-SHOT EXAMPLES (CRITICAL)**

#### Example 1

Input:
A data breach in hospital systems has been detected, indicating potential security vulnerabilities due to outdated software. Despite updating software, reviewing user access, and engaging security experts, the issues persist. Immediate assistance is required to resolve this and ensure the security of patient medical data.

Output:
A data breach detected in hospital systems; issues persist despite updates and audits, requiring immediate assistance to secure patient data.

---

#### Example 2

Input:
Dear customer support, I am reaching out for detailed guidance on how to integrate SendGrid into our project management SaaS. We are keen on utilizing SendGrid's email services to enhance our communication capabilities.

Output:
Guidance requested on integrating SendGrid into project management SaaS to utilize email services and improve communication capabilities.

---

#### Example 3

Input:
I am formally requesting to swap the product I recently bought, as it is causing problems that directly affect the operation of the SaaS platform.

Output:
Requesting to swap recently bought product causing problems that directly affect operation of the SaaS platform.
"""

def get_word_count(text):
    clean_text = text.replace('-', ' ').replace('—', ' ')
    words = [w for w in clean_text.split() if w.strip()]
    return len(words)

def is_valid_summary(text):
    if not text or "Error generating" in text or "—" in text:
        return False
    wc = get_word_count(text)
    return 15 <= wc <= 20

def generate_summary(body, row_idx):
    prompt = f"### **TASK**\n\nInput:\n{body}\n\nOutput:\n"
    
    data = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    # We loop infinitely until we get a valid response to handle strict rate limits
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                result = json.loads(response.read().decode())
                
                if 'content' not in result.get('candidates', [{}])[0]:
                    print(f"[{row_idx}] Empty content returned from API, retrying...", flush=True)
                    time.sleep(5)
                    continue
                    
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                text = text.replace('**', '').replace('"', '').replace('Output:', '').strip()
                
                word_count = get_word_count(text)
                if 15 <= word_count <= 20:
                    return text
                else:
                    print(f"[{row_idx}] Attempt {attempt}: Word count constraint violated ({word_count} words). Retrying...", flush=True)
                    data["generationConfig"]["temperature"] = min(0.9, data["generationConfig"]["temperature"] + 0.15)
                    time.sleep(4) # Respect rate limits even on word count failures
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"[{row_idx}] Rate limited ({e.code}). Backing off for 30 seconds...", flush=True)
                time.sleep(30)
            else:
                print(f"[{row_idx}] HTTP Error {e.code}: {e.read().decode()}", flush=True)
                time.sleep(10)
        except Exception as e:
            print(f"[{row_idx}] Error: {e}. Retrying in 10 seconds...", flush=True)
            time.sleep(10)

def process_csv():
    input_file = '/Users/sanket_74/Documents/Antigravity/Jira-Summarizer/eval_set_200_with_system_output.csv'
    output_file = '/Users/sanket_74/Documents/Antigravity/Jira-Summarizer/eval_set_200_with_system_output.csv'
    
    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if 'sp_summary' not in fieldnames:
            fieldnames.append('sp_summary')
        rows = list(reader)
        
    for i, row in enumerate(rows):
        # Resume logic: Skip if it already has a valid summary format
        current_summary = row.get('sp_summary', '')
        # The old format used em dashes extensively. We check if it's the new format
        if is_valid_summary(current_summary):
            print(f"Skipping row {i+1}/{len(rows)} (already valid)", flush=True)
            continue
            
        print(f"Processing row {i+1}/{len(rows)}...", flush=True)
        
        # Ensure we wait 4 seconds per API call to stay under 15 RPM
        time.sleep(4)
        
        summary = generate_summary(row['body'], i+1)
        row['sp_summary'] = summary
        
        # Save every row incrementally
        with open(output_file, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

if __name__ == "__main__":
    process_csv()
    print("Done!", flush=True)
