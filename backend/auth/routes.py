import json
import hashlib
import logging
import re
import uuid
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import bcrypt
import jwt
from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request

from auth.jwt_handler import (
    blacklist_jti,
    generate_token,
    roles_required,
    token_required,
)
from database.graph_db import get_graph
from database.mongo import get_db
from database.redis_db import get_redis

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)
security_bp = Blueprint('security', __name__)

TRIAL_DAYS = 30
SUBSCRIPTION_PLAN_DAYS = {
    'PLAN_6_MONTHS': 180,
    'PLAN_1_YEAR': 365,
    'PLAN_5_YEARS': 1825,
}
PAYMENT_METHODS = {'BANK_TRANSFER', 'UPI', 'CARD'}


def _normalize_bank_info(data):
    raw_bank_id = (data.get('bank_id') or '').strip().lower()
    raw_bank_name = (data.get('bank_name') or '').strip()

    if not raw_bank_id and not raw_bank_name:
        return None, None

    if raw_bank_id:
        bank_id = re.sub(r'[^a-z0-9_]+', '_', raw_bank_id).strip('_')
    else:
        source = raw_bank_name.lower()
        bank_id = re.sub(r'[^a-z0-9]+', '_', source).strip('_')

    if not bank_id:
        return None, None

    bank_name = raw_bank_name if raw_bank_name else bank_id.replace('_', ' ').title()
    return bank_id, bank_name


def _check_rate_limit(redis_client, key, limit=5, window_seconds=60):
    if not redis_client:
        return False
    attempts = redis_client.incr(key)
    if attempts == 1:
        redis_client.expire(key, window_seconds)
    return attempts > limit


def _extract_api_key():
    header_key = (request.headers.get('X-API-Key') or '').strip()
    if header_key:
        return header_key

    auth_header = (request.headers.get('Authorization') or '').strip()
    if auth_header.lower().startswith('apikey '):
        return auth_header.split(' ', 1)[1].strip()
    if auth_header.lower().startswith('bearer '):
        # Support bearer format for partner integrations using API key auth.
        return auth_header.split(' ', 1)[1].strip()

    return None


def _parse_bank_api_key_map():
    raw = (current_app.config.get('BANK_API_KEYS_JSON') or '{}').strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        logger.warning("Invalid BANK_API_KEYS_JSON config.")
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        str(api_key).strip(): str(bank_id).strip().lower()
        for api_key, bank_id in parsed.items()
        if str(api_key).strip() and str(bank_id).strip()
    }


def _is_subscription_active(api_key_doc):
    status = str(api_key_doc.get('subscription_status') or 'ACTIVE').strip().upper()
    if status not in {'ACTIVE', 'TRIAL'}:
        return False

    expires_at = api_key_doc.get('subscription_expires_at')
    if isinstance(expires_at, datetime):
        return expires_at > datetime.utcnow()
    if isinstance(expires_at, (int, float)):
        return datetime.utcfromtimestamp(float(expires_at)) > datetime.utcnow()
    if isinstance(expires_at, str) and expires_at.strip():
        try:
            parsed = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
            return parsed > datetime.utcnow()
        except Exception:
            return False

    return True


def _is_bank_subscription_active(bank_doc):
    payload = _build_bank_subscription_payload(bank_doc)
    return bool(payload.get('is_active'))


def _resolve_bank_from_api_key(db, provided_api_key):
    if not provided_api_key:
        return None, 'API key is required'

    # Env-based mapping fallback for local validation.
    mapped_bank = _parse_bank_api_key_map().get(provided_api_key)
    if mapped_bank:
        if db is not None:
            bank_doc = db.banks.find_one({'bank_id': mapped_bank})
            if not bank_doc:
                return None, 'Bank not found for API key'
            bank_doc = _ensure_bank_subscription_defaults(db, bank_doc)
            if not _is_bank_subscription_active(bank_doc):
                return None, 'Subscription is inactive or expired'
        return mapped_bank, None

    if db is None:
        return None, 'DB not initialized'

    hashed_key = hashlib.sha256(provided_api_key.encode('utf-8')).hexdigest()
    api_key_doc = db.api_keys.find_one(
        {
            '$or': [
                {'api_key': provided_api_key},
                {'api_key_hash': hashed_key},
            ]
        }
    )
    if not api_key_doc:
        return None, 'Invalid API key'

    if not api_key_doc.get('is_active', True):
        return None, 'API key is inactive'

    if not _is_subscription_active(api_key_doc):
        return None, 'Subscription is inactive or expired'

    bank_id = (api_key_doc.get('bank_id') or '').strip().lower()
    if not bank_id:
        return None, 'API key is not linked to a bank'

    bank_doc = db.banks.find_one({'bank_id': bank_id})
    if bank_doc:
        bank_doc = _ensure_bank_subscription_defaults(db, bank_doc)
        if not _is_bank_subscription_active(bank_doc):
            return None, 'Subscription is inactive or expired'

    return bank_id, None


def _log_user_approval_event(admin_id, user_id, bank_id, action, reason=None):
    payload = {
        'event': 'USER_APPROVAL',
        'admin_id': admin_id,
        'user_id': user_id,
        'bank_id': bank_id,
        'action': action,
    }
    if reason:
        payload['reason'] = reason
    logger.critical(payload)


def _serialize_dt(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(value)).isoformat()
        except Exception:
            return None
    if isinstance(value, str) and value.strip():
        return value
    return None


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(float(value))
        except Exception:
            return None
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
            return parsed
        except Exception:
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is not None:
                    parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
                return parsed
            except Exception:
                return None
    return None


def _serialize_event_doc(document):
    serialized = {}
    for key, value in document.items():
        if key == '_id':
            serialized[key] = str(value)
        elif key == 'timestamp':
            dt_value = _parse_dt(value)
            serialized[key] = (
                dt_value.timestamp()
                if isinstance(dt_value, datetime)
                else value
            )
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            serialized[key] = str(value)
        else:
            serialized[key] = value
    return serialized


def _build_bank_subscription_payload(bank_doc):
    now = datetime.utcnow()
    trial_end = _parse_dt(bank_doc.get('trial_end_at')) or now
    subscription_end = _parse_dt(bank_doc.get('subscription_expires_at'))
    raw_status = str(bank_doc.get('subscription_status') or 'TRIAL').strip().upper()
    is_active = False
    requires_subscription = False

    if raw_status == 'ACTIVE':
        is_active = subscription_end is not None and subscription_end > now
        if not is_active:
            raw_status = 'EXPIRED'
            requires_subscription = True
    elif raw_status == 'TRIAL':
        is_active = trial_end > now
        requires_subscription = not is_active
        if not is_active:
            raw_status = 'TRIAL_EXPIRED'
    elif raw_status == 'PENDING_APPROVAL':
        requires_subscription = True
    else:
        requires_subscription = True

    return {
        'bank_id': (bank_doc.get('bank_id') or '').strip().lower(),
        'bank_name': bank_doc.get('bank_name'),
        'status': raw_status,
        'plan_code': bank_doc.get('subscription_plan') or 'TRIAL_1_MONTH',
        'trial_start_at': _serialize_dt(bank_doc.get('trial_start_at')),
        'trial_end_at': _serialize_dt(bank_doc.get('trial_end_at')),
        'subscription_started_at': _serialize_dt(bank_doc.get('subscription_started_at')),
        'subscription_expires_at': _serialize_dt(bank_doc.get('subscription_expires_at')),
        'pending_plan_code': bank_doc.get('pending_plan_code'),
        'pending_payment_method': bank_doc.get('pending_payment_method'),
        'pending_transaction_no': bank_doc.get('pending_transaction_no'),
        'requires_subscription': requires_subscription,
        'is_active': is_active,
    }


def _ensure_bank_subscription_defaults(db, bank_doc):
    now = datetime.utcnow()
    updates = {}

    if not bank_doc.get('trial_start_at'):
        updates['trial_start_at'] = bank_doc.get('created_at') or now
    if not bank_doc.get('trial_end_at'):
        start_dt = _parse_dt(updates.get('trial_start_at') or bank_doc.get('trial_start_at')) or now
        updates['trial_end_at'] = start_dt + timedelta(days=TRIAL_DAYS)
    if not bank_doc.get('subscription_status'):
        updates['subscription_status'] = 'TRIAL'
    if not bank_doc.get('subscription_plan'):
        updates['subscription_plan'] = 'TRIAL_1_MONTH'
    if not bank_doc.get('subscription_expires_at'):
        updates['subscription_expires_at'] = updates.get('trial_end_at') or bank_doc.get('trial_end_at')
    if not bank_doc.get('subscription_payment_status'):
        updates['subscription_payment_status'] = 'FREE_TRIAL'

    if updates:
        db.banks.update_one({'_id': bank_doc['_id']}, {'$set': updates})
        bank_doc = db.banks.find_one({'_id': bank_doc['_id']}) or {**bank_doc, **updates}

    return bank_doc


def run_async_evaluation(user_id, device_id, ip_address, bank_id, bank_name, session_id, metadata):
    try:
        from database.mongo import get_db
        from engine.decision_engine import get_decision_engine
        
        db = get_db()
        engine = get_decision_engine()
        if db is None or engine is None:
            return
            
        # Feature engineering: fetch past logs
        past_logs = list(db.risk_events.find({
            "user_id": user_id,
            "bank_name": bank_name
        }).sort('timestamp', -1).limit(10))

        # Build features
        failed_attempts = sum(1 for log in past_logs if log.get('decision') == 'BLOCK')
        ip_change_count = len(set(log.get('ip_address') for log in past_logs if log.get('ip_address')))
        request_interval = 60.0
        if len(past_logs) > 1:
            timestamps = [log.get('timestamp') for log in past_logs if log.get('timestamp')]
            if timestamps:
                import datetime as dt_module
                ts_floats = []
                for ts in timestamps:
                    if isinstance(ts, dt_module.datetime):
                        ts_floats.append(ts.timestamp())
                    else:
                        ts_floats.append(float(ts))
                ts_floats.sort(reverse=True)
                request_interval = (ts_floats[0] - ts_floats[-1]) / len(ts_floats)
        
        login_hour = datetime.utcnow().hour
        is_new_device = 1 if not any(log.get('device_id') == device_id for log in past_logs) else 0

        features = {
            'failed_attempts': failed_attempts,
            'ip_change_count': ip_change_count,
            'request_interval': request_interval,
            'login_hour': login_hour,
            'is_new_device': is_new_device,
            'is_vpn': 0,
            'typing_speed': float(metadata.get('typing_speed', 50.0) or 50.0) if metadata else 50.0,
            'session_duration': float(metadata.get('session_duration', 60.0) or 60.0) if metadata else 60.0,
            'otp_requests': 0
        }

        # Use decision engine for scoring and decision
        result = engine.evaluate_login(
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
            bank_id=bank_id,
            session_id=session_id,
            metadata={'features': features},
            insert_event=True,
        )

        # Alert system
        if result['decision'] == "BLOCK":
            alert = {
                "bank_name": bank_name,
                "user_id": user_id,
                "message": "Suspicious login detected",
                "timestamp": datetime.utcnow()
            }
            db.alerts.insert_one(alert)

    except Exception as e:
        print("[ASYNC EVALUATION ERROR]:", e)
        import traceback
        traceback.print_exc()


@security_bp.route('/security/check-login', methods=['POST'])
def security_check_login():
    try:
        print("==== GRAPHSHIELD API HIT ====")
        print("Headers:", dict(request.headers))
        print("Payload:", request.json)

        db = get_db()
        if db is None:
            return jsonify({'error': 'DB not initialized'}), 500

        api_key = request.headers.get("x-api-key") or request.headers.get("X-Api-Key")
        print("API KEY RECEIVED:", api_key)
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401

        data = request.get_json() or {}
        bank_name = data.get("bank_name")
        if not bank_name:
            return jsonify({'error': 'bank_name is required'}), 400
        bank_id = re.sub(r'[^a-z0-9]+', '_', bank_name.strip().lower()).strip('_')

        # Query MongoDB for bank using exact bank_name match
        bank = db.subscribed_banks.find_one({"bank_name": bank_name, "api_key": api_key})
        print("BANK FOUND:", bank)
        if bank is None:
            # Auto-register bank
            new_bank = {
                "bank_name": bank_name,
                "api_key": api_key,
                "status": "ACTIVE"
            }
            db.subscribed_banks.insert_one(new_bank)
            bank = new_bank
            print("AUTO-REGISTERED BANK:", bank)

        user_id = str(data.get('user_id') or '').strip()
        device_id = str(data.get('device_id') or 'unknown_device').strip()
        ip_address = str(data.get('ip_address') or request.remote_addr or 'unknown').strip()
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        # Generate unique session identifier derived from timestamp
        now_dt = datetime.utcnow()
        timestamp_prefix = now_dt.strftime("SESSION_%Y%m%d_%H%M%S")
        session_id = f"{timestamp_prefix}_{uuid.uuid4().hex[:6]}"

        # Persist raw telemetry to simulated S3
        from database.s3_client import get_s3_client
        s3 = get_s3_client()
        if s3:
            s3.log_orchestrator(f"Ingested raw telemetry from client. Session assigned: {session_id}")
            s3.upload_file(s3.bucket_name, f"{session_id}/raw/telemetry_payload.bin", json.dumps(data).encode('utf-8'))
            s3.upload_file(s3.bucket_name, f"{session_id}/raw/metadata_header.json", {
                "session_id": session_id,
                "timestamp": now_dt.isoformat(),
                "client_ip": ip_address
            })

        # Launch background worker process/thread
        import threading
        t = threading.Thread(
            target=run_async_evaluation,
            args=(user_id, device_id, ip_address, bank_id, bank_name, session_id, data)
        )
        t.daemon = True
        t.start()

        # Immediately return authentication confirmation (zero latency impact)
        return jsonify({
            'decision': 'ALLOW',
            'session_id': session_id,
            'status': 'submitted',
            'message': 'Telemetry registered and background worker triggered'
        }), 200

    except Exception as e:
        print("🔥 ERROR:", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@auth_bp.route('/banks', methods=['GET'])
def list_banks():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    banks = list(
        db.banks.find({}, {'_id': 0, 'bank_id': 1, 'bank_name': 1}).sort('bank_name', 1)
    )
    return jsonify(banks), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    ip_address = request.remote_addr or 'unknown'
    redis_client = get_redis()
    if _check_rate_limit(redis_client, f"rate_limit_register:{ip_address}", limit=5, window_seconds=60):
        return jsonify({'error': 'Too many registration attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    role = (data.get('role') or 'USER').upper()
    bank_id, bank_name = _normalize_bank_info(data)

    if role not in {'USER', 'BANK', 'ADMIN'}:
        return jsonify({'error': 'Unsupported role'}), 400

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if role == 'BANK' and (not bank_id or not bank_name):
        return jsonify({'error': 'bank_name is required for bank registration'}), 400
    if role in {'USER', 'ADMIN'} and not bank_id:
        return jsonify({'error': 'bank_id is required for this registration'}), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    if db.users.find_one({'email': email, 'role': role}):
        return jsonify({'error': 'User already exists'}), 409

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    now = datetime.utcnow()

    user_bank_id = None
    user_bank_name = None
    if role == 'BANK':
        bank_doc = db.banks.find_one({'bank_id': bank_id})
        if bank_doc is None:
            trial_start = now
            trial_end = now + timedelta(days=TRIAL_DAYS)
            db.banks.insert_one(
                {
                    'bank_id': bank_id,
                    'bank_name': bank_name,
                    'admin_email': email,
                    'admin_password': password_hash,
                    'created_at': now,
                    'trial_start_at': trial_start,
                    'trial_end_at': trial_end,
                    'subscription_status': 'TRIAL',
                    'subscription_plan': 'TRIAL_1_MONTH',
                    'subscription_started_at': trial_start,
                    'subscription_expires_at': trial_end,
                    'subscription_payment_status': 'FREE_TRIAL',
                }
            )
        else:
            updates = {'bank_name': bank_name}
            if not bank_doc.get('admin_email'):
                updates['admin_email'] = email
                updates['admin_password'] = password_hash
            db.banks.update_one({'bank_id': bank_id}, {'$set': updates})
            bank_doc = db.banks.find_one({'bank_id': bank_id})
            if bank_doc:
                _ensure_bank_subscription_defaults(db, bank_doc)
        user_bank_id = bank_id
        user_bank_name = bank_name
    elif role == 'USER':
        bank_doc = db.banks.find_one({'bank_id': bank_id})
        if bank_doc is None:
            return jsonify({'error': 'Selected bank does not exist'}), 404
        user_bank_id = bank_id
        user_bank_name = bank_doc.get('bank_name') or bank_id.replace('_', ' ').title()
    elif role == 'ADMIN':
        bank_doc = db.banks.find_one({'bank_id': bank_id})
        if bank_doc is None:
            return jsonify({'error': 'Selected bank does not exist'}), 404
        user_bank_id = bank_id
        user_bank_name = bank_doc.get('bank_name') or bank_id.replace('_', ' ').title()

    approval_status = 'PENDING' if role == 'USER' else 'APPROVED'
    user_id = db.users.insert_one(
        {
            'email': email,
            # legacy compatibility
            'username': email,
            'password': password_hash,
            'role': role,
            'bank_id': user_bank_id,
            'bank_name': user_bank_name,
            'approval_status': approval_status,
            'approved_by': None,
            'approved_at': None,
            'rejection_reason': None,
            'created_at': now,
        }
    ).inserted_id

    logger.info("Registered %s account %s", role, email)
    message = (
        'Registration successful. Awaiting bank approval.'
        if role == 'USER'
        else 'User created successfully'
    )
    return (
        jsonify(
            {
                'message': message,
                'user_id': str(user_id),
                'bank_id': user_bank_id,
                'bank_name': user_bank_name,
                'email': email,
                'role': role,
                'approval_status': approval_status,
            }
        ),
        201,
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    ip_address = request.remote_addr or 'unknown'
    redis_client = get_redis()
    if _check_rate_limit(redis_client, f"rate_limit_login:{ip_address}", limit=5, window_seconds=60):
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or data.get('username') or '').strip().lower()
    password = data.get('password')
    requested_role = (data.get('role') or 'USER').upper()
    device_id = data.get('device_id', 'unknown_device')
    requested_bank_id = (data.get('bank_id') or '').strip().lower()

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    if requested_role == 'BANK':
        return jsonify({'error': 'Use /bank-login for bank authentication'}), 400

    user = db.users.find_one({'email': email, 'role': requested_role})
    if user is None:
        user = db.users.find_one({'username': email, 'role': requested_role})

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    expected_bank_id = user.get('bank_id')
    if requested_role == 'USER':
        approval_status = (user.get('approval_status') or 'PENDING').upper()
        if approval_status != 'APPROVED':
            if approval_status == 'REJECTED':
                rejection_reason = (user.get('rejection_reason') or '').strip()
                rejection_message = (
                    f"Account rejected by bank: {rejection_reason}"
                    if rejection_reason
                    else 'Account rejected by bank'
                )
                return (
                    jsonify(
                        {
                            'error': rejection_message,
                            'approval_status': approval_status,
                            'reason': rejection_reason or None,
                        }
                    ),
                    403,
                )
            return jsonify({'error': 'Account pending bank approval', 'approval_status': approval_status}), 403
        if not expected_bank_id:
            return jsonify({'error': 'User account is not linked to a bank'}), 400
        if requested_bank_id and requested_bank_id != expected_bank_id:
            return jsonify({'error': 'Bank mismatch for this user'}), 403
        bank_id = expected_bank_id
    else:
        if requested_role == 'ADMIN' and not expected_bank_id:
            return jsonify({'error': 'Admin account is not linked to a bank'}), 403
        bank_id = expected_bank_id or requested_bank_id or 'admin'

    session_id = str(uuid.uuid4())

    from engine.decision_engine import get_decision_engine

    engine = get_decision_engine()
    result = engine.evaluate_login(
        str(user['_id']),
        device_id,
        ip_address,
        bank_id,
        session_id=session_id,
        insert_event=False,
    )

    if redis_client:
        session_key = f"session:{user['_id']}:{session_id}"
        session_payload = {
            'user_id': str(user['_id']),
            'bank_id': bank_id,
            'status': 'AUTHENTICATED',
            'security_decision': result['decision'],
            'created_at': datetime.utcnow().isoformat(),
        }
        redis_client.setex(session_key, 3600, json.dumps(session_payload))

    if result['decision'] == 'BLOCK':
        logger.warning(
            "Dashboard login marked high-risk user=%s bank=%s ip=%s score=%.3f",
            user['_id'],
            bank_id,
            ip_address,
            float(result.get('risk_score', 0.0)),
        )

    token = generate_token(
        str(user['_id']),
        role=user.get('role', 'USER'),
        session_id=session_id,
        token_type='ACCESS',
        expires_minutes=60,
    )
    return (
        jsonify(
            {
                'token': token,
                'user_id': str(user['_id']),
                'role': user.get('role', 'USER'),
                'bank_id': bank_id,
                'email': email,
                'username': user.get('username', email),
                'risk': result,
                'session_id': session_id,
            }
        ),
        200,
    )


@auth_bp.route('/bank-login', methods=['POST'])
def bank_login():
    ip_address = request.remote_addr or 'unknown'
    redis_client = get_redis()
    if _check_rate_limit(redis_client, f"rate_limit_bank_login:{ip_address}", limit=5, window_seconds=60):
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    bank_id = (data.get('bank_id') or '').strip().lower()

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    bank = db.banks.find_one({'bank_id': bank_id}) if bank_id else db.banks.find_one({'admin_email': email})
    if not bank:
        return jsonify({'error': 'Bank account not found'}), 404
    bank = _ensure_bank_subscription_defaults(db, bank)

    admin_email = bank.get('admin_email')
    admin_password = bank.get('admin_password')
    if not admin_email or not admin_password:
        return jsonify({'error': 'Bank admin account not initialized for this bank'}), 403

    if admin_email != email or not bcrypt.checkpw(password.encode('utf-8'), admin_password.encode('utf-8')):
        return jsonify({'error': 'Invalid bank credentials'}), 401

    session_id = str(uuid.uuid4())
    token = generate_token(
        bank.get('bank_id'),
        role='BANK',
        session_id=session_id,
        token_type='ACCESS',
        expires_minutes=60,
    )

    if redis_client:
        redis_client.setex(
            f"session:{bank.get('bank_id')}:{session_id}",
            3600,
            json.dumps(
                {
                    'bank_id': bank.get('bank_id'),
                    'status': 'AUTHENTICATED',
                    'created_at': datetime.utcnow().isoformat(),
                }
            ),
        )

    return (
        jsonify(
            {
                'token': token,
                'role': 'BANK',
                'bank_id': bank.get('bank_id'),
                'bank_name': bank.get('bank_name', bank.get('bank_id')),
                'email': admin_email,
                'session_id': session_id,
                'subscription': _build_bank_subscription_payload(bank),
            }
        ),
        200,
    )


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    claims = request.user
    jti = claims.get('jti')
    exp = claims.get('exp', 0)
    ttl_seconds = exp - int(datetime.utcnow().timestamp())
    blacklist_jti(jti, ttl_seconds)

    session_id = claims.get('session_id')
    user_id = claims.get('user_id')
    redis_client = get_redis()
    if redis_client and session_id and user_id:
        redis_client.delete(f"session:{user_id}:{session_id}")

    logger.info("Logged out user_id=%s role=%s", user_id, claims.get('role'))
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/admin-only', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_only():
    return jsonify({'message': 'admin ok'}), 200


def _resolve_bank_for_subscription(db, claims):
    role = (claims.get('role') or '').strip().upper()
    if role == 'BANK':
        bank_id = (claims.get('user_id') or '').strip().lower()
        if not bank_id:
            return None, (jsonify({'error': 'Bank context missing in token'}), 403)
        bank = db.banks.find_one({'bank_id': bank_id})
        if not bank:
            return None, (jsonify({'error': 'Bank not found'}), 404)
        return _ensure_bank_subscription_defaults(db, bank), None

    if role == 'ADMIN':
        requested_bank = (request.args.get('bank_id') or '').strip().lower()
        if requested_bank:
            bank = db.banks.find_one({'bank_id': requested_bank})
            if not bank:
                return None, (jsonify({'error': 'Bank not found'}), 404)
            return _ensure_bank_subscription_defaults(db, bank), None
        # Fallback to linked bank for admin.
        bank_id, scope_error = _resolve_admin_bank_scope(db, claims)
        if scope_error:
            return None, scope_error
        bank = db.banks.find_one({'bank_id': bank_id})
        if not bank:
            return None, (jsonify({'error': 'Bank not found'}), 404)
        return _ensure_bank_subscription_defaults(db, bank), None

    return None, (jsonify({'error': 'Forbidden'}), 403)


@auth_bp.route('/subscription/status', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def subscription_status():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    bank, error = _resolve_bank_for_subscription(db, request.user)
    if error:
        return error
    return jsonify(_build_bank_subscription_payload(bank)), 200


@auth_bp.route('/subscription/request', methods=['POST'])
@token_required
@roles_required('BANK')
def subscription_request():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    claims = request.user
    bank_id = (claims.get('user_id') or '').strip().lower()
    if not bank_id:
        return jsonify({'error': 'Bank context missing in token'}), 403

    bank = db.banks.find_one({'bank_id': bank_id})
    if not bank:
        return jsonify({'error': 'Bank not found'}), 404
    bank = _ensure_bank_subscription_defaults(db, bank)

    data = request.get_json() or {}
    plan_code = (data.get('plan_code') or '').strip().upper()
    payment_method = (data.get('payment_method') or '').strip().upper()
    transaction_no = (data.get('transaction_no') or '').strip()

    if plan_code not in SUBSCRIPTION_PLAN_DAYS:
        return jsonify({'error': 'Invalid plan selected'}), 400
    if payment_method not in PAYMENT_METHODS:
        return jsonify({'error': 'Invalid payment method'}), 400
    if len(transaction_no) < 4:
        return jsonify({'error': 'Transaction number is required'}), 400

    now = datetime.utcnow()
    existing_pending = db.subscription_requests.find_one(
        {'bank_id': bank_id, 'status': 'PENDING'}
    )
    if existing_pending:
        return jsonify({'error': 'A subscription request is already pending approval'}), 409

    request_doc = {
        'bank_id': bank_id,
        'bank_name': bank.get('bank_name') or bank_id,
        'plan_code': plan_code,
        'plan_days': SUBSCRIPTION_PLAN_DAYS[plan_code],
        'payment_method': payment_method,
        'transaction_no': transaction_no,
        'status': 'PENDING',
        'created_at': now,
        'updated_at': now,
        'approved_by': None,
        'approved_at': None,
        'rejection_reason': None,
    }
    inserted = db.subscription_requests.insert_one(request_doc)
    db.banks.update_one(
        {'_id': bank['_id']},
        {
            '$set': {
                'subscription_status': 'PENDING_APPROVAL',
                'pending_plan_code': plan_code,
                'pending_payment_method': payment_method,
                'pending_transaction_no': transaction_no,
                'pending_subscription_request_id': str(inserted.inserted_id),
                'pending_subscription_requested_at': now,
            }
        },
    )

    return jsonify({'message': 'Subscription request submitted for admin approval'}), 201


@auth_bp.route('/admin/subscription-requests', methods=['GET'])
@token_required
@roles_required('ADMIN')
def admin_subscription_requests():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    status_filter = (request.args.get('status') or 'PENDING').strip().upper()
    query = {}
    if status_filter != 'ALL':
        query['status'] = status_filter

    items = list(
        db.subscription_requests.find(
            query,
            {
                'bank_id': 1,
                'bank_name': 1,
                'plan_code': 1,
                'plan_days': 1,
                'payment_method': 1,
                'transaction_no': 1,
                'status': 1,
                'created_at': 1,
                'updated_at': 1,
                'approved_by': 1,
                'approved_at': 1,
                'rejection_reason': 1,
            },
        ).sort('created_at', -1)
    )

    serialized = []
    for item in items:
        serialized.append(
            {
                'request_id': str(item.get('_id')),
                'bank_id': item.get('bank_id'),
                'bank_name': item.get('bank_name') or item.get('bank_id'),
                'plan_code': item.get('plan_code'),
                'plan_days': item.get('plan_days'),
                'payment_method': item.get('payment_method'),
                'transaction_no': item.get('transaction_no'),
                'status': item.get('status'),
                'created_at': _serialize_dt(item.get('created_at')),
                'updated_at': _serialize_dt(item.get('updated_at')),
                'approved_by': item.get('approved_by'),
                'approved_at': _serialize_dt(item.get('approved_at')),
                'rejection_reason': item.get('rejection_reason'),
            }
        )

    return jsonify(serialized), 200


@auth_bp.route('/admin/subscription-requests/<request_id>/decision', methods=['POST'])
@token_required
@roles_required('ADMIN')
def admin_subscription_decision(request_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    try:
        req_object_id = ObjectId(request_id)
    except Exception:
        return jsonify({'error': 'Invalid request_id'}), 400

    subscription_request_doc = db.subscription_requests.find_one({'_id': req_object_id})
    if not subscription_request_doc:
        return jsonify({'error': 'Subscription request not found'}), 404
    if (subscription_request_doc.get('status') or '').upper() != 'PENDING':
        return jsonify({'error': 'Subscription request already finalized'}), 409

    bank_id = (subscription_request_doc.get('bank_id') or '').strip().lower()
    bank = db.banks.find_one({'bank_id': bank_id})
    if not bank:
        return jsonify({'error': 'Bank not found'}), 404

    data = request.get_json() or {}
    action = (data.get('action') or 'APPROVE').strip().upper()
    reason = (data.get('reason') or '').strip()
    now = datetime.utcnow()

    if action not in {'APPROVE', 'REJECT'}:
        return jsonify({'error': 'Invalid action'}), 400
    if action == 'REJECT' and not reason:
        return jsonify({'error': 'reason is required for rejection'}), 400

    if action == 'APPROVE':
        plan_code = (subscription_request_doc.get('plan_code') or '').strip().upper()
        plan_days = int(subscription_request_doc.get('plan_days') or SUBSCRIPTION_PLAN_DAYS.get(plan_code, 0))
        if plan_code not in SUBSCRIPTION_PLAN_DAYS or plan_days <= 0:
            return jsonify({'error': 'Invalid plan configuration in request'}), 400

        start_at = now
        end_at = now + timedelta(days=plan_days)
        db.subscription_requests.update_one(
            {'_id': req_object_id},
            {
                '$set': {
                    'status': 'APPROVED',
                    'updated_at': now,
                    'approved_by': str(request.user.get('user_id') or ''),
                    'approved_at': now,
                }
            },
        )
        db.banks.update_one(
            {'_id': bank['_id']},
            {
                '$set': {
                    'subscription_status': 'ACTIVE',
                    'subscription_plan': plan_code,
                    'subscription_started_at': start_at,
                    'subscription_expires_at': end_at,
                    'subscription_payment_status': 'PAID',
                    'last_transaction_no': subscription_request_doc.get('transaction_no'),
                    'last_payment_method': subscription_request_doc.get('payment_method'),
                    'last_subscription_approved_by': str(request.user.get('user_id') or ''),
                    'last_subscription_approved_at': now,
                },
                '$unset': {
                    'pending_plan_code': '',
                    'pending_payment_method': '',
                    'pending_transaction_no': '',
                    'pending_subscription_request_id': '',
                    'pending_subscription_requested_at': '',
                },
            },
        )
        return jsonify({'message': 'Subscription approved successfully'}), 200

    current_payload = _build_bank_subscription_payload(_ensure_bank_subscription_defaults(db, bank))
    fallback_status = 'TRIAL' if current_payload.get('is_active') else 'TRIAL_EXPIRED'
    db.subscription_requests.update_one(
        {'_id': req_object_id},
        {
            '$set': {
                'status': 'REJECTED',
                'updated_at': now,
                'approved_by': str(request.user.get('user_id') or ''),
                'approved_at': now,
                'rejection_reason': reason,
            }
        },
    )
    db.banks.update_one(
        {'_id': bank['_id']},
        {
            '$set': {
                'subscription_status': fallback_status,
                'last_subscription_rejection_reason': reason,
                'last_subscription_rejected_at': now,
            },
            '$unset': {
                'pending_plan_code': '',
                'pending_payment_method': '',
                'pending_transaction_no': '',
                'pending_subscription_request_id': '',
                'pending_subscription_requested_at': '',
            },
        },
    )
    return jsonify({'message': 'Subscription request rejected'}), 200


@auth_bp.route('/user/dashboard', methods=['GET'])
@token_required
@roles_required('USER')
def user_dashboard():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    claims = request.user
    user_id = str(claims.get('user_id') or '').strip()
    if not user_id:
        return jsonify({'error': 'Invalid user context'}), 401

    user = None
    try:
        user = db.users.find_one({'_id': ObjectId(user_id), 'role': 'USER'})
    except Exception:
        user = None
    if not user:
        return jsonify({'error': 'User account not found'}), 404

    bank_id = (user.get('bank_id') or '').strip().lower()
    if not bank_id:
        return jsonify({'error': 'User account is not linked to a bank'}), 403

    query = {
        '$or': [
            {'user_id': user_id},
            {'user_id': user.get('email')},
            {'user_id': user.get('username')},
        ],
        'bank_id': bank_id,
        'event_source': 'OUTSIDER_LOGIN',
        'decision': 'BLOCK',
    }
    events = list(db.risk_events.find(query).sort('timestamp', -1).limit(50))
    events = [_serialize_event_doc(event) for event in events]

    device_counts = {}
    ip_counts = {}
    for event in events:
        device_id = str(event.get('device_id') or 'unknown')
        ip_address = str(event.get('ip_address') or 'unknown')
        device_counts[device_id] = device_counts.get(device_id, 0) + 1
        ip_counts[ip_address] = ip_counts.get(ip_address, 0) + 1

    devices = [
        {'device_id': device_id, 'attempts': attempts}
        for device_id, attempts in sorted(
            device_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    ip_history = [
        {'ip_address': ip_address, 'attempts': attempts}
        for ip_address, attempts in sorted(
            ip_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return jsonify(
        {
            'user_id': user_id,
            'bank_id': bank_id,
            'events': events,
            'devices': devices,
            'ip_history': ip_history,
        }
    ), 200


@auth_bp.route('/admin/dashboard', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_dashboard():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    claims = request.user
    bank_id, scope_error = _resolve_admin_bank_scope(db, claims)
    if scope_error:
        return scope_error
    bank_doc = db.banks.find_one({'bank_id': bank_id})
    subscription = None
    if bank_doc:
        bank_doc = _ensure_bank_subscription_defaults(db, bank_doc)
        subscription = _build_bank_subscription_payload(bank_doc)

    query = {
        'bank_id': bank_id,
        'event_source': 'OUTSIDER_LOGIN',
        'decision': 'BLOCK',
    }
    recent_events = list(db.risk_events.find(query).sort('timestamp', -1).limit(300))
    recent_events = [_serialize_event_doc(event) for event in recent_events]

    total_events = db.risk_events.count_documents(query)
    blocks = db.risk_events.count_documents(query)
    allows = 0

    counts_by_day = {}
    for event in recent_events:
        event_dt = _parse_dt(event.get('timestamp'))
        if event_dt is None:
            continue
        day_key = event_dt.strftime('%Y-%m-%d')
        counts_by_day[day_key] = counts_by_day.get(day_key, 0) + 1

    device_users = {}
    user_ips = {}
    for event in recent_events:
        user_id = str(event.get('user_id') or 'unknown')
        device_id = str(event.get('device_id') or 'unknown')
        ip_address = str(event.get('ip_address') or 'unknown')

        device_users.setdefault(device_id, set()).add(user_id)
        user_ips.setdefault(user_id, set()).add(ip_address)

    suspicious_patterns = {
        'device_reuse': [
            {'device_id': device_id, 'unique_users': len(users)}
            for device_id, users in device_users.items()
            if len(users) > 1
        ],
        'ip_rotation': [
            {'user_id': user_id, 'unique_ips': len(ips)}
            for user_id, ips in user_ips.items()
            if len(ips) > 2
        ],
    }

    stats = {
        'bank_id': bank_id,
        'subscription': subscription,
        'total_events': db.risk_events.count_documents(query),
        'blocks': blocks,
        'allows': allows,
        'attempts_vs_days': [
            {'day': day, 'attempts': counts_by_day[day]}
            for day in sorted(counts_by_day.keys())
        ],
        'suspicious_patterns': suspicious_patterns,
        'latest': recent_events,
    }
    return jsonify(stats), 200


@auth_bp.route('/admin/graph-insights', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_graph_insights():
    graph = get_graph()
    if not graph:
        return jsonify({'error': 'Graph not initialized'}), 500
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    bank_id, scope_error = _resolve_admin_bank_scope(db, request.user)
    if scope_error:
        return scope_error

    return jsonify(graph.get_graph_insights(bank_id=bank_id)), 200


@auth_bp.route('/admin/graph-data', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_graph_data():
    graph = get_graph()
    if not graph:
        return jsonify({'error': 'Graph not initialized'}), 500
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    bank_id, scope_error = _resolve_admin_bank_scope(db, request.user)
    if scope_error:
        return scope_error

    return jsonify(graph.get_graph_data(bank_id=bank_id)), 200


@auth_bp.route('/admin/pending-users', methods=['GET'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_pending_users():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    claims = request.user
    bank_id, scope_error = _resolve_admin_bank_scope(db, claims)
    if scope_error:
        return scope_error

    query = {'role': 'USER', 'approval_status': 'PENDING'}
    query['bank_id'] = bank_id

    users = list(
        db.users.find(
            query,
            {
                '_id': 1,
                'email': 1,
                'username': 1,
                'bank_id': 1,
                'bank_name': 1,
                'approval_status': 1,
                'created_at': 1,
            },
        ).sort('created_at', 1)
    )

    bank_ids = sorted(
        {
            (user.get('bank_id') or '').strip().lower()
            for user in users
            if (user.get('bank_id') or '').strip()
        }
    )
    banks_by_id = {}
    if bank_ids:
        bank_docs = db.banks.find({'bank_id': {'$in': bank_ids}}, {'bank_id': 1, 'bank_name': 1})
        banks_by_id = {
            (bank.get('bank_id') or '').strip().lower(): bank.get('bank_name')
            for bank in bank_docs
        }

    serialized = []
    for user in users:
        created_at = user.get('created_at')
        user_bank_id = user.get('bank_id')
        serialized.append(
            {
                'user_id': str(user.get('_id')),
                'email': user.get('email'),
                'username': user.get('username'),
                'bank_id': user_bank_id,
                'bank_name': user.get('bank_name')
                or banks_by_id.get((user_bank_id or '').strip().lower())
                or user_bank_id,
                'approval_status': user.get('approval_status', 'PENDING'),
                'created_at': created_at.isoformat() if isinstance(created_at, datetime) else created_at,
            }
        )
    return jsonify(serialized), 200


def _resolve_admin_bank_scope(db, claims):
    role = (claims.get('role') or '').strip().upper()
    if role == 'BANK':
        bank_id = (claims.get('user_id') or '').strip().lower()
        if not bank_id:
            return None, (jsonify({'error': 'Bank context missing in token'}), 403)
        return bank_id, None

    if role != 'ADMIN':
        return None, (jsonify({'error': 'Forbidden'}), 403)

    admin_id = (claims.get('user_id') or '').strip()
    try:
        admin_object_id = ObjectId(admin_id)
    except Exception:
        return None, (jsonify({'error': 'Invalid admin identity'}), 401)

    admin_user = db.users.find_one({'_id': admin_object_id, 'role': 'ADMIN'})
    if not admin_user:
        return None, (jsonify({'error': 'Admin account not found'}), 403)

    bank_id = (admin_user.get('bank_id') or '').strip().lower()
    if not bank_id:
        return None, (jsonify({'error': 'Admin account is not linked to a bank'}), 403)

    return bank_id, None


def _resolve_user_for_approval(db, user_id, claims):
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return None, (jsonify({'error': 'Invalid user_id'}), 400)

    user = db.users.find_one({'_id': object_id, 'role': 'USER'})
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)

    admin_bank_id, scope_error = _resolve_admin_bank_scope(db, claims)
    if scope_error:
        return None, scope_error
    if (user.get('bank_id') or '').strip().lower() != admin_bank_id:
        return None, (jsonify({'error': 'Cannot manage users from another bank'}), 403)

    if (user.get('approval_status') or 'PENDING').upper() != 'PENDING':
        return None, (jsonify({'error': 'User approval already finalized'}), 409)

    return user, None


@auth_bp.route('/admin/approve-user', methods=['POST'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_approve_user():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    data = request.get_json() or {}
    user_id = (data.get('user_id') or '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    claims = request.user
    user, error = _resolve_user_for_approval(db, user_id, claims)
    if error:
        return error

    now = datetime.utcnow()
    db.users.update_one(
        {'_id': user['_id']},
        {
            '$set': {
                'approval_status': 'APPROVED',
                'approved_by': str(claims.get('user_id')),
                'approved_at': now,
                'rejection_reason': None,
            }
        },
    )
    _log_user_approval_event(
        admin_id=str(claims.get('user_id')),
        user_id=str(user['_id']),
        bank_id=user.get('bank_id'),
        action='APPROVED',
    )
    return (
        jsonify(
            {
                'message': 'User approved successfully',
                'user_id': str(user['_id']),
                'approval_status': 'APPROVED',
                'approved_by': str(claims.get('user_id')),
                'approved_at': now.isoformat(),
            }
        ),
        200,
    )


@auth_bp.route('/admin/reject-user', methods=['POST'])
@token_required
@roles_required('BANK', 'ADMIN')
def admin_reject_user():
    db = get_db()
    if db is None:
        return jsonify({'error': 'DB not initialized'}), 500

    data = request.get_json() or {}
    user_id = (data.get('user_id') or '').strip()
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    reason = (data.get('reason') or '').strip()
    if not reason:
        return jsonify({'error': 'reason is required'}), 400

    claims = request.user
    user, error = _resolve_user_for_approval(db, user_id, claims)
    if error:
        return error

    now = datetime.utcnow()
    db.users.update_one(
        {'_id': user['_id']},
        {
            '$set': {
                'approval_status': 'REJECTED',
                'approved_by': str(claims.get('user_id')),
                'approved_at': now,
                'rejection_reason': reason,
            }
        },
    )
    _log_user_approval_event(
        admin_id=str(claims.get('user_id')),
        user_id=str(user['_id']),
        bank_id=user.get('bank_id'),
        action='REJECTED',
        reason=reason,
    )
    return (
        jsonify(
            {
                'message': 'User rejected successfully',
                'user_id': str(user['_id']),
                'approval_status': 'REJECTED',
                'reason': reason,
            }
        ),
        200,
    )

# Security monitoring endpoints
@security_bp.route('/active-session', methods=['GET'])
def active_session():
    """Get active session information"""
    try:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            try:
                claims = jwt.decode(token, current_app.config.get('SECRET_KEY'), algorithms=['HS256'])
                return jsonify({
                    'active': True,
                    'user_id': claims.get('user_id'),
                    'session_id': claims.get('session_id'),
                    'role': claims.get('role'),
                }), 200
            except Exception:
                pass
        return jsonify({'active': False}), 200
    except Exception as e:
        logger.error(f"Error getting active session: {e}")
        return jsonify({'active': False}), 200


@security_bp.route('/blocked-sites', methods=['GET'])
def blocked_sites():
    """Get list of blocked sites from security policies"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'blocked_sites': []}), 200
        
        # Return empty list or fetch from security policies collection
        blocked = []
        security_policies = db.security_policies.find_one({'type': 'blocked_sites'})
        if security_policies:
            blocked = security_policies.get('sites', [])
        
        return jsonify({'blocked_sites': blocked}), 200
    except Exception as e:
        logger.error(f"Error getting blocked sites: {e}")
        return jsonify({'blocked_sites': []}), 200
