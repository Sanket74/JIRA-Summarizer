import json
import urllib.request
import urllib.error
import time
import os
import ssl
import csv
from datetime import datetime
from dotenv import load_dotenv

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not found. Please set it in a .env file.")
    exit(1)

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={API_KEY}"

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
* Avoid prefixes like "Customer…", "Dear…", "I am…", "We are…"
* Output must **open with a noun** — the specific system, tool, or issue name
* Output should feel like a **trimmed version of the original sentence**

---

### **HARD CONSTRAINT**

* If the output contains **words not present in the input**, regenerate the answer
* If output exceeds **20 words or is below 15 words**, regenerate
* If output opens with a verb or pronoun (I, We, Reaching, Seeking, Formally, Kindly), regenerate

---

### **FEW-SHOT EXAMPLES (CRITICAL)**

#### Example 1

Input:
A data breach in hospital systems has been detected, indicating potential security vulnerabilities due to outdated software. Despite updating software, reviewing user access, and engaging security experts, the issues persist. Immediate assistance is required to resolve this and ensure the security of patient medical data.

Output:
Data breach detected in hospital systems; issues persist despite updates and audits, requiring immediate assistance to secure patient data.

---

#### Example 2

Input:
Dear customer support, I am reaching out for detailed guidance on how to integrate SendGrid into our project management SaaS. We are keen on utilizing SendGrid's email services to enhance our communication capabilities.

Output:
SendGrid integration guidance requested for project management SaaS to utilize email services and improve communication capabilities.

---

#### Example 3

Input:
I am formally requesting to swap the product I recently bought, as it is causing problems that directly affect the operation of the SaaS platform.

Output:
Product swap requested for recently bought item causing problems that directly affect SaaS platform operation.
"""

def get_word_count(text):
    clean_text = text.replace('-', ' ').replace('—', ' ')
    words = [w for w in clean_text.split() if w.strip()]
    return len(words)

def validate_summary(text):
    word_count = get_word_count(text)
    first_word = text.split()[0].lower() if text else ""
    forbidden_starts = ['i', 'we', 'reaching', 'seeking', 'formally', 'kindly', 'dear', 'customer', 'requesting', 'guidance']
    
    if 15 <= word_count <= 20 and first_word not in forbidden_starts:
        return True, word_count
    return False, word_count

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
    
    total_prompt_tokens = 0
    total_candidates_tokens = 0
    
    # Max 3 retries as per spec (1 initial + 3 retries = 4 attempts total)
    max_attempts = 4 
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
                print(f"[{row_idx}] API call successful", flush=True)
                result = json.loads(response.read().decode())
                
                # Extract token usage
                if 'usageMetadata' in result:
                    total_prompt_tokens += result['usageMetadata'].get('promptTokenCount', 0)
                    total_candidates_tokens += result['usageMetadata'].get('candidatesTokenCount', 0)
                
                if 'content' not in result.get('candidates', [{}])[0]:
                    print(f"[{row_idx}] Empty content returned from API, retrying...", flush=True)
                    time.sleep(15)
                    continue
                    
                text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                text = text.replace('**', '').replace('"', '').replace('Output:', '').strip()
                
                is_valid, word_count = validate_summary(text)
                first_word = text.split()[0].lower() if text else ""
                
                if is_valid:
                    return {
                        "status": "passed",
                        "summary": text,
                        "word_count": word_count,
                        "prompt_tokens": total_prompt_tokens,
                        "candidates_tokens": total_candidates_tokens
                    }
                else:
                    if attempt < max_attempts:
                        print(f"[{row_idx}] Attempt {attempt}: Constraint violated ({word_count} words, start: '{first_word}'). Retrying...", flush=True)
                        data["generationConfig"]["temperature"] = min(0.9, data["generationConfig"]["temperature"] + 0.15)
                        # Append stricter instruction if failing
                        if attempt == 2:
                            prompt += "\n\nCRITICAL: You failed the constraints. Ensure your output is exactly 15 to 20 words, and starts with a noun!"
                            data["contents"][0]["parts"][0]["text"] = prompt
                        time.sleep(15) # Strict pacing
                    else:
                        print(f"[{row_idx}] Failed after {max_attempts} attempts. Moving to held queue.", flush=True)
                        return {
                            "status": "held",
                            "summary": text,
                            "word_count": word_count,
                            "prompt_tokens": total_prompt_tokens,
                            "candidates_tokens": total_candidates_tokens,
                            "reason": f"Constraint violated ({word_count} words, start: '{first_word}')"
                        }
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"[{row_idx}] Rate limited ({e.code}). Backing off for 60 seconds...", flush=True)
                time.sleep(60)
            else:
                print(f"[{row_idx}] HTTP Error {e.code}: {e.read().decode()}", flush=True)
                time.sleep(15)
        except Exception as e:
            print(f"[{row_idx}] Error: {e}. Retrying in 15 seconds...", flush=True)
            time.sleep(15)
            
    # Fallback if loops exit without returning
    return {
        "status": "held",
        "summary": "Error: Max retries exceeded without valid output.",
        "word_count": 0,
        "prompt_tokens": total_prompt_tokens,
        "candidates_tokens": total_candidates_tokens,
        "reason": "Max retries exceeded"
    }

def process_batch():
    input_file = 'top80.json'
    output_file = 'primary_summaries.json'
    cost_file = 'daily_cost_log.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Run step1_ticket_fetcher.py first.")
        return
        
    with open(input_file, 'r', encoding='utf-8') as f:
        tickets = json.load(f)
        
    passed_queue = []
    held_queue = []
    
    total_prompt_tokens_batch = 0
    total_candidates_tokens_batch = 0
    
    # Check if we already have partial progress to resume
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                passed_queue = data.get("passed", [])
                held_queue = data.get("held", [])
                print(f"Resuming: Found {len(passed_queue)} passed, {len(held_queue)} held.")
            except:
                pass
                
    processed_ids = {t["ticket_id"] for t in passed_queue + held_queue}
    
    for i, ticket in enumerate(tickets):
        if ticket["ticket_id"] in processed_ids:
            print(f"Skipping row {i+1}/{len(tickets)} (already processed)", flush=True)
            continue
            
        print(f"Processing row {i+1}/{len(tickets)}...", flush=True)
        time.sleep(35) # Very conservative pacing: <2 requests per minute to avoid 429
        
        result = generate_summary(ticket['body'], i+1)
        
        total_prompt_tokens_batch += result.get("prompt_tokens", 0)
        total_candidates_tokens_batch += result.get("candidates_tokens", 0)
        
        summary_record = {
            "ticket_id": ticket["ticket_id"],
            "summary": result["summary"],
            "word_count": result["word_count"]
        }
        
        if result["status"] == "passed":
            passed_queue.append(summary_record)
        else:
            summary_record["reason"] = result.get("reason", "Unknown")
            held_queue.append(summary_record)
            
        # Save incrementally
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"passed": passed_queue, "held": held_queue}, f, indent=4)
            
    # Log costs
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Gemini Flash pricing: roughly $0.075 / 1M prompt tokens, $0.30 / 1M candidate tokens
    estimated_cost = (total_prompt_tokens_batch / 1000000 * 0.075) + (total_candidates_tokens_batch / 1000000 * 0.30)
    
    file_exists = os.path.isfile(cost_file)
    with open(cost_file, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['run_date', 'tickets_processed', 'passed', 'held', 'prompt_tokens', 'candidates_tokens', 'estimated_cost_usd'])
        writer.writerow([run_date, len(tickets), len(passed_queue), len(held_queue), total_prompt_tokens_batch, total_candidates_tokens_batch, f"${estimated_cost:.5f}"])
        
    print(f"\nBatch processing complete!")
    print(f"Passed: {len(passed_queue)}, Held: {len(held_queue)}")
    print(f"Estimated Cost: ${estimated_cost:.5f}")

if __name__ == "__main__":
    process_batch()
