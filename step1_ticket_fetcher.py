import csv
import json
import os

def fetch_top_80(input_csv):
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found.")
        return []

    tickets = []
    with open(input_csv, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Create a mock ticket ID if none exists
            ticket_id = row.get('ticket_id') or f"TCK-{i+1:05d}"
            
            # Since there is no actual timestamp column in the CSV, 
            # we use the row index to simulate chronological appending.
            # Larger row index = more recent.
            timestamp_proxy = i 
            
            tickets.append({
                "ticket_id": ticket_id,
                "subject": row.get("subject", ""),
                "body": row.get("body", ""),
                "priority": row.get("priority", "medium"),
                "queue": row.get("queue", ""),
                "tags": [row[f"tag_{j}"] for j in range(1, 9) if row.get(f"tag_{j}")],
                "timestamp_proxy": timestamp_proxy
            })

    # Sort by timestamp_proxy DESC (latest first)
    tickets.sort(key=lambda x: x['timestamp_proxy'], reverse=True)
    
    # Pick the top 80
    top_80 = tickets[:80]
    return top_80

if __name__ == "__main__":
    csv_file = "dataset-tickets-multi-lang-4-20k.csv"
    print(f"Fetching top 80 tickets from {csv_file}...")
    
    top_80 = fetch_top_80(csv_file)
    
    output_file = "top80.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(top_80, f, indent=4)
        
    print(f"Successfully saved {len(top_80)} tickets to {output_file}.")
