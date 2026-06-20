from datetime import datetime
import ipaddress


def _is_likely_vpn_or_proxy_ip(ip_address):
    if not ip_address:
        return 0
    normalized_ip = str(ip_address).strip()
    if normalized_ip in {'localhost', '::1'}:
        return 0
    try:
        parsed = ipaddress.ip_address(normalized_ip)
        # Treat local/private networks as non-VPN to avoid false positives in dev and LAN.
        if (
            parsed.is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_reserved
            or parsed.is_multicast
        ):
            return 0
        return 1
    except ValueError:
        # If IP format is unknown, default to non-VPN for stability.
        return 0


def _normalize_flag(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if float(value) > 0 else 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in {'1', 'true', 'yes', 'y'} else 0
    return 0


def compute_features(
    user_id,
    device_id,
    ip_address,
    redis_client,
    db,
    bank_id=None,
    metadata=None,
):
    """
    Computes real-time features for the ML model based on historical telemetry.
    """
    _ = redis_client  # reserved for future online feature caching
    metadata = metadata or {}
    now_ts = datetime.utcnow().timestamp()
    metadata_vpn = metadata.get('is_vpn')
    effective_vpn = (
        _normalize_flag(metadata_vpn)
        if metadata_vpn is not None
        else _is_likely_vpn_or_proxy_ip(ip_address)
    )
    features = {
        'failed_attempts': 0,
        'otp_requests': 0,
        'request_interval': 60.0,
        'session_duration': 60.0,
        'ip_change_count': 1,
        'typing_speed': float(metadata.get('typing_speed', 50.0) or 50.0),
        'is_new_device': 0,
        'is_vpn': effective_vpn,
        'login_hour': datetime.utcnow().hour,
    }

    if db is None:
        return features

    trusted = db.trusted_devices.find_one(
        {'user_id': str(user_id), 'device_id': device_id}
    )
    features['is_new_device'] = 0 if trusted else 1

    one_hour_ago = now_ts - 3600
    risk_query = {
        'user_id': str(user_id),
        'decision': 'BLOCK',
        'timestamp': {'$gt': one_hour_ago},
    }
    logs_query = {'user_id': str(user_id)}
    if bank_id:
        risk_query['bank_id'] = bank_id
        logs_query['bank_id'] = bank_id

    features['failed_attempts'] = db.risk_events.count_documents(risk_query)
    features['otp_requests'] = 0

    recent_logs = list(db.login_logs.find(logs_query).sort('timestamp', -1).limit(10))
    if recent_logs:
        latest_ts = recent_logs[0].get('timestamp')
        if latest_ts:
            features['request_interval'] = max(now_ts - float(latest_ts), 0.0)

        ips = {log.get('ip_address') for log in recent_logs if log.get('ip_address')}
        if ips:
            features['ip_change_count'] = len(ips)

    # Session duration and typing speed are placeholders for demo telemetry.
    # In production, these would come from client instrumentation.
    try:
        features['session_duration'] = float(metadata.get('session_duration', 60.0) or 60.0)
    except Exception:
        features['session_duration'] = 60.0
    return features
