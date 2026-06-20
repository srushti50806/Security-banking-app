import logging
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import current_app, jsonify, request

logger = logging.getLogger(__name__)


def generate_token(user_id, role='USER', session_id=None, token_type='ACCESS', expires_minutes=60):
    now = datetime.utcnow()
    payload = {
        'jti': str(uuid.uuid4()),
        'exp': now + timedelta(minutes=expires_minutes),
        'iat': now,
        'user_id': str(user_id),
        'sub': str(user_id),
        'role': role,
        'token_type': token_type,
    }
    if session_id:
        payload['session_id'] = session_id
    return jwt.encode(payload, current_app.config.get('SECRET_KEY'), algorithm='HS256')


def blacklist_jti(jti, ttl_seconds):
    from database.redis_db import get_redis

    redis_client = get_redis()
    if redis_client and jti:
        # Use jti-based revocation, not full-token blacklist.
        redis_client.setex(f"bl_jti:{jti}", max(int(ttl_seconds), 1), "1")


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            from database.redis_db import get_redis

            decoded = jwt.decode(
                token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256'],
            )

            redis_client = get_redis()
            if redis_client and redis_client.get(f"bl_jti:{decoded.get('jti')}"):
                return jsonify({'error': 'Token revoked'}), 401

            # Attach decoded claims to request context for downstream handlers.
            request.user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception as exc:
            logger.warning("Invalid token: %s", exc)
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated


def roles_required(*roles):
    allowed = set(roles)

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = getattr(request, 'user', None)
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401
            if user.get('role') not in allowed:
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)

        return wrapped

    return decorator
