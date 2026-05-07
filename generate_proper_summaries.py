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


API_KEY = "AIzaSyAoJEnlcaHHwjaTFSUS5rOEBmK0m9compI" # From Linkedin-PM-Engine/.env
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

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

def generate_summary(subject, body, priority):
    prompt = f"Ticket Subject: {subject}\nTicket Priority: {priority}\nTicket Body:\n{body}\n\nWrite the summary:"
    
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
    
    req = urllib.request.Request(URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    retries = 5
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                result = json.loads(response.read().decode())
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                # Clean up markdown if any
                text = text.replace('**', '').replace('"', '').strip()
                return text
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"Rate limited (429). Retrying in {10 * (attempt + 1)} seconds...")
                time.sleep(10 * (attempt + 1))
            else:
                print(f"HTTP Error {e.code}: {e.read().decode()}")
                time.sleep(5)
        except Exception as e:
            print(f"Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            
    return "Error generating summary due to API limits."

def process_csv():
    input_file = 'eval_set_200_completed.csv'
    output_file = 'eval_set_200_proper.csv'
    
    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        
    for i, row in enumerate(rows):
        if i % 10 == 0:
            print(f"Processing row {i+1}/200...")
        
        # Don't regenerate if we already have it from a previous interrupted run
        # if row.get('human_summary_2') and row['human_summary_2'] != "Error generating summary due to API limits." and 'hallucinated' not in row['human_summary_2']:
        #    pass
        
        summary = generate_summary(row['subject'], row['body'], row['priority_level'])
        word_count = len(summary.split())
        
        row['human_summary_2'] = summary
        row['word_count_2'] = word_count
        row['labeller_2'] = 'SM-2'
        
        time.sleep(3) # Base delay to avoid 429s proactively
        
        # Save every row incrementally in case of crash
        with open(output_file, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

if __name__ == "__main__":
    process_csv()
    print("Done!")
