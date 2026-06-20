import csv
import dateutil.parser
from pymongo import MongoClient
from collections import defaultdict
from datetime import datetime

def main():
    # 1. FETCH DATA
    print("Connecting to MongoDB...")
    # Add a timeout so it doesn't hang forever if MongoDB is down
    client = MongoClient('mongodb://127.0.0.1:27017/', serverSelectionTimeoutMS=5000)
    db = client['graphshield']
    collection = db['risk_events']
    
    try:
        # Test connection
        client.admin.command('ping')
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    print("Fetching risk events...")
    # Sort by timestamp ascending
    events_cursor = collection.find().sort('timestamp', 1)
    events = list(events_cursor)
    print(f"Found {len(events)} events.")

    # 2. FEATURE EXTRACTION (State setup)
    user_state = defaultdict(lambda: {
        'failed_attempts': 0,
        'seen_ips': set(),
        'seen_devices': set(),
        'last_timestamp': None
    })
    
    device_state = defaultdict(lambda: {
        'seen_users': set(),
        'seen_ips': set()
    })

    # Thresholds
    RAPID_THRESHOLD_SECONDS = 60
    
    # Bonus summary stats
    total_attacks = 0
    total_blocked = 0
    scenarios_counts = defaultdict(int)

    results = []

    for event in events:
        user_id = str(event.get('user_id', ''))
        bank_name = str(event.get('bank_name', ''))
        device_id = str(event.get('device_id', ''))
        ip_address = str(event.get('ip_address', ''))
        timestamp_raw = event.get('timestamp')
        
        ml_score = event.get('ml_score', 0)
        graph_score = event.get('graph_score', 0)
        risk_score = event.get('risk_score', 0)
        decision = event.get('decision', 'ALLOW')
        
        # Parse timestamp safely
        if isinstance(timestamp_raw, str):
            try:
                dt = dateutil.parser.isoparse(timestamp_raw)
            except Exception:
                dt = datetime.min
        elif isinstance(timestamp_raw, datetime):
            dt = timestamp_raw
        else:
            dt = datetime.min

        # Ensure strings are not empty for tracking device connections
        if not user_id or not device_id:
            continue
            
        # Update device tracking
        device_state[device_id]['seen_users'].add(user_id)
        device_state[device_id]['seen_ips'].add(ip_address)
        
        ustate = user_state[user_id]
        
        # Feature Extraction
        is_new_device_bool = device_id not in ustate['seen_devices']
        ustate['seen_devices'].add(device_id)
        
        ustate['seen_ips'].add(ip_address)
        ip_change_count = len(ustate['seen_ips'])
        
        request_interval = None
        if ustate['last_timestamp']:
            request_interval = (dt - ustate['last_timestamp']).total_seconds()
            
        ustate['last_timestamp'] = dt
        
        # 3. PATTERN DETECTION
        failed_attempts = ustate['failed_attempts']
        behavior_change_detected = 'NO'
        
        if failed_attempts > 2 or (request_interval is not None and request_interval < RAPID_THRESHOLD_SECONDS):
            behavior_change_detected = 'YES'
            
        graph_pattern_detected = 'NO'
        multiple_users_per_device = len(device_state[device_id]['seen_users']) > 1
        multiple_ips_per_device = len(device_state[device_id]['seen_ips']) > 1
        
        if multiple_users_per_device or multiple_ips_per_device:
            graph_pattern_detected = 'YES'
            
        # 4. SCENARIO CLASSIFICATION
        scenario = 'NORMAL'
        reasons = []
        
        if multiple_users_per_device:
            scenario = 'DEVICE_REUSE'
            reasons.append("Device used across multiple users")
        elif multiple_ips_per_device:
            scenario = 'IP_ROTATION'
            reasons.append("Multiple IPs detected for same device")
        elif request_interval is not None and request_interval < RAPID_THRESHOLD_SECONDS:
            scenario = 'RAPID_ATTEMPT'
            reasons.append("High frequency login attempts observed")
        elif failed_attempts > 2:
            scenario = 'RAPID_ATTEMPT'
            reasons.append("Multiple failed attempts detected")
            
        if scenario == 'NORMAL' and is_new_device_bool:
            reasons.append("New device detected but within normal thresholds")
            
        if not reasons:
            reasons.append("Normal behavior")
            
        reason_text = " | ".join(reasons)
        
        # Update failed attempts state for future iterations
        if decision == 'BLOCK':
            ustate['failed_attempts'] += 1
            total_blocked += 1
            
        # Track statistics
        if scenario != 'NORMAL':
            total_attacks += 1
            
        scenarios_counts[scenario] += 1
        
        # Row Construction
        row = {
            'user_id': user_id,
            'bank_name': bank_name,
            'device_id': device_id,
            'ip_address': ip_address,
            'timestamp': str(timestamp_raw),
            'ml_score': ml_score,
            'graph_score': graph_score,
            'risk_score': risk_score,
            'decision': decision,
            
            'failed_attempts': failed_attempts,
            'ip_change_count': ip_change_count,
            'request_interval': round(request_interval, 2) if request_interval is not None else '',
            'is_new_device': 'YES' if is_new_device_bool else 'NO',
            
            'behavior_change_detected': behavior_change_detected,
            'graph_pattern_detected': graph_pattern_detected,
            
            'scenario': scenario,
            'reason': reason_text
        }
        results.append(row)

    # 6. EXPORT CSV
    if results:
        csv_file = 'qualitative_analysis.csv'
        fieldnames = list(results[0].keys())
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSuccessfully generated {csv_file}")
    else:
        print("No results to export.")
        
    # ⚡ BONUS SUMMARY
    print("\n" + "="*40)
    print("📊 QUALITATIVE ANALYSIS SUMMARY")
    print("="*40)
    print(f"Total Login Events Analyzed: {len(events)}")
    print(f"Total Attacks Detected:      {total_attacks}")
    block_rate = (total_blocked / len(events) * 100) if events else 0
    print(f"Percent Blocked:             {block_rate:.1f}%")
    
    if scenarios_counts:
        # Exclude NORMAL from the most common pattern search if we only want attacks
        attack_counts = {k: v for k, v in scenarios_counts.items() if k != 'NORMAL'}
        if attack_counts:
            most_common = max(attack_counts.items(), key=lambda x: x[1])
            print(f"Most Common Attack Pattern:  {most_common[0]} ({most_common[1]} occurences)")
        else:
            print("Most Common Attack Pattern:  NONE")
    print("="*40)

if __name__ == '__main__':
    main()
