import urllib.request
import json
import time

BASE_URL = 'http://127.0.0.1:5000'
CHECK_LOGIN_URL = f'{BASE_URL}/api/security/check-login'
API_KEY = 'demo_admin_api_key'

# Configure headers
HEADERS = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
}

def send_login(user_id, device_id, ip_address, bank_name="Global GM Bank", typing_speed=50.0, session_duration=60.0):
    payload = {
        "bank_name": bank_name,
        "user_id": user_id,
        "device_id": device_id,
        "ip_address": ip_address,
        "typing_speed": typing_speed,
        "session_duration": session_duration
    }
    
    req = urllib.request.Request(
        CHECK_LOGIN_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode('utf-8')
            return json.loads(resp_body)
    except Exception as e:
        print(f"Error sending payload to {CHECK_LOGIN_URL}: {e}")
        return None

def run_simulation():
    print("\n" + "="*60)
    print("STARTING GRAPHSHIELD USER-SPECIFIC THREAT SIMULATOR")
    print("Target User: user@gmbank.com")
    print("Bank Name:   Global GM Bank")
    print("="*60 + "\n")

    # Send 4 login attempts with rotating IPs to trigger graph-based IP rotation block
    ips = [
        "185.228.180.1",
        "185.228.180.2",
        "185.228.180.3",
        "185.228.180.4"
    ]

    for i, ip in enumerate(ips):
        print(f"[{i+1}/4] Simulating outsider login attempt from IP {ip}...")
        # Anomalous characteristics (slow typing speed and short session duration)
        res = send_login(
            user_id="user@gmbank.com",
            device_id="compromised_browser_agent",
            ip_address=ip,
            typing_speed=32.0,
            session_duration=25.0
        )
        if res:
            print(f"      Response: decision={res.get('decision')} | session_id={res.get('session_id')}")
        time.sleep(1.5) # Wait for background threads to complete database insertions

    print("\n" + "="*60)
    print("Simulation finished! Check the dashboards in Chrome.")
    print("="*60 + "\n")

if __name__ == '__main__':
    run_simulation()
