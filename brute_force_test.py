import urllib.request
import json
import time
import os
from pymongo import MongoClient

DEMO_BANK_BASE = 'http://localhost:3000'
REGISTER_URL = f'{DEMO_BANK_BASE}/api/auth/register'
LOGIN_URL = f'{DEMO_BANK_BASE}/api/auth/login'

def register_user(username, email, password):
    payload = {
        "username": username,
        "email": email,
        "password": password
    }
    req = urllib.request.Request(
        REGISTER_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def login_user(email, password, ip, fingerprint):
    payload = {
        "email": email,
        "password": password,
        "bank_name": "Demo Bank",
        "device_fingerprint": fingerprint
    }
    req = urllib.request.Request(
        LOGIN_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-Forwarded-For': ip
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body
    except Exception as e:
        return None, str(e)

def run_brute_force():
    # Main execution
    unique_id = int(time.time())
    username = f"brute_{unique_id}"
    email = f"{username}@gmail.com"
    password = "BrutePassword123!"

    print(f"Registering user {username}...")
    reg_res = register_user(username, email, password)
    user_id = reg_res['user']['user_id']
    print(f"Registered User ID: {user_id}")

    # Rotate IPs and fingerprints
    attempts = [
        ("192.168.1.10", "device_aaa"),
        ("192.168.1.11", "device_bbb"),
        ("192.168.1.12", "device_ccc"),
        ("192.168.1.13", "device_ddd"),
        ("192.168.1.14", "device_eee"),
        ("192.168.1.15", "device_fff"),
    ]

    print("\nStarting simulated brute force / credential stuffing login attempts...")
    for i, (ip, fp) in enumerate(attempts):
        print(f"\n[Attempt {i+1}] Logging in from IP={ip}, device={fp}...")
        status, body = login_user(email, password, ip, fp)
        print(f"  Response Status: {status}")
        print(f"  Response Body: {body}")
        time.sleep(1.0) # short delay to allow background thread to process

    # Wait for final background evaluations to complete
    print("\nWaiting 4 seconds for background evaluations to write to DB and S3...")
    time.sleep(4.0)

    # Verify DB storage
    client = MongoClient('mongodb://127.0.0.1:27017/')
    db = client['graphshield']

    print("\n" + "="*60)
    print("VERIFYING MONGODB STORAGE")
    print("="*60)
    
    # Find events in MongoDB
    events = list(db.risk_events.find({"user_id": user_id}).sort('timestamp', 1))
    print(f"MongoDB: Found {len(events)} risk events for user in risk_events collection.")
    for idx, ev in enumerate(events):
        print(f"  Event {idx+1}: Decision={ev.get('decision')} | ML Score={ev.get('ml_score'):.3f} | Graph Score={ev.get('graph_score'):.3f} | Final Score={ev.get('final_score'):.3f}")

    # Find alerts in MongoDB
    alerts = list(db.alerts.find({"user_id": user_id}))
    print(f"MongoDB: Found {len(alerts)} alerts generated in alerts collection.")
    for idx, al in enumerate(alerts):
        print(f"  Alert {idx+1}: {al.get('message')} at {al.get('timestamp')}")

    # Check Graph Nodes & Edges in MongoDB fallback storage
    nodes_count = db.graph_nodes.count_documents({})
    edges_count = db.graph_edges.count_documents({})
    print(f"MongoDB Graph Fallback: {nodes_count} nodes, {edges_count} edges total.")

    # Print S3 files created for latest session
    print("\n" + "="*60)
    print("VERIFYING MOCK S3 STORAGE")
    print("="*60)
    latest_event = events[-1] if events else None
    if latest_event and latest_event.get('session_id'):
        sid = latest_event.get('session_id')
        s3_path = f"s3_storage_mock/graphshield-storage-bucket/{sid}"
        if os.path.exists(s3_path):
            print(f"[OK] Mock S3 session folder exists: {s3_path}")
            for root, dirs, files in os.walk(s3_path):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), s3_path)
                    print(f"  - {rel_path} ({os.path.getsize(os.path.join(root, file))} bytes)")
        else:
            print(f"[ERROR] Mock S3 session folder not found: {s3_path}")

if __name__ == '__main__':
    run_brute_force()
