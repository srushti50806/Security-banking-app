import urllib.request
import json
import time

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
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode('utf-8')
            return response.status, json.loads(resp_body)
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        return e.code, json.loads(resp_body)
    except Exception as e:
        return None, str(e)

def login_user(email, password):
    payload = {
        "email": email,
        "password": password,
        "bank_name": "Demo Bank",
        "device_fingerprint": "mock_browser_fingerprint_xyz_123"
    }
    
    req = urllib.request.Request(
        LOGIN_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode('utf-8')
            return response.status, json.loads(resp_body)
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode('utf-8')
        return e.code, json.loads(resp_body)
    except Exception as e:
        return None, str(e)

def run_tests():
    print("\n" + "="*60)
    print("RUNNING DEMO BANK REGISTRATION & LOGIN INTEGRATION TEST")
    print("="*60 + "\n")

    # Generate a unique email for registration to avoid conflicts
    unique_id = int(time.time())
    username = f"testuser_{unique_id}"
    email = f"testuser_{unique_id}@gmail.com"
    password = "SuperPassword123"

    print(f"Step 1: Registering user '{username}' with email '{email}'...")
    status, body = register_user(username, email, password)
    print(f"  Response Status: {status}")
    print(f"  Response Body: {body}")
    
    if status != 201:
        print("\n[ERROR] Registration failed!")
        return

    print("\nStep 2: Logging in user...")
    status, body = login_user(email, password)
    print(f"  Response Status: {status}")
    print(f"  Response Body: {body}")

    if status == 200 and body.get('decision') == 'ALLOW':
        print("\n" + "="*60)
        print("SUCCESS: Demo Bank Registration & Login successfully verified!")
        print("Decision returned from GraphShield is ALLOW as expected for first login.")
        print("="*60 + "\n")
    else:
        print("\n[ERROR] Login verification failed!")

if __name__ == '__main__':
    run_tests()