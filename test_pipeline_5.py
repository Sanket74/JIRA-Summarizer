import json
import os
import time
from step2_batch_summariser import generate_summary, validate_summary

def run_test_5():
    input_file = 'top80.json'
    output_file = 'test_5_results.json'
    
    # Run Step 1
    print("Fetching 80 tickets...")
    os.system("python3 step1_ticket_fetcher.py")
    
    if not os.path.exists(input_file):
        print("Error: top80.json not found.")
        return
        
    with open(input_file, 'r', encoding='utf-8') as f:
        all_tickets = json.load(f)
    
    test_tickets = all_tickets[2:7]
    results = []
    
    print(f"Processing 5 test tickets...")
    for i, ticket in enumerate(test_tickets):
        print(f"[{i+1}/5] Processing Ticket {ticket['ticket_id']}...", flush=True)
        
        # Pacing
        if i > 0:
            time.sleep(35)
            
        result = generate_summary(ticket['body'], i+1)
        results.append({
            "ticket_id": ticket["ticket_id"],
            "original_body": ticket["body"],
            "summary": result["summary"],
            "word_count": result["word_count"],
            "status": result["status"]
        })
        
        print(f"      Result: {result['status']} | Word Count: {result['word_count']}")
        print(f"      Summary: {result['summary']}")
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    
    print(f"\nTest complete! Results saved to {output_file}")

if __name__ == "__main__":
    run_test_5()
