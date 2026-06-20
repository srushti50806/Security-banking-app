import logging
import os
import pickle

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


def _atomic_pickle_dump(obj, destination_path):
    tmp_path = f"{destination_path}.tmp"
    with open(tmp_path, 'wb') as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, destination_path)


def generate_models():
    features = [
        'failed_attempts',
        'otp_requests',
        'request_interval',
        'session_duration',
        'ip_change_count',
        'typing_speed',
        'is_new_device',
        'is_vpn',
        'login_hour',
    ]

    np.random.seed(42)
    n_samples = 1000

    x = pd.DataFrame(np.random.rand(n_samples, len(features)), columns=features)
    y = np.random.randint(2, size=n_samples)

    lgb_model = lgb.LGBMClassifier(n_estimators=10, random_state=42)
    lgb_model.fit(x, y)

    iso_model = IsolationForest(n_estimators=10, random_state=42)
    iso_model.fit(x)

    base_dir = os.path.dirname(os.path.dirname(__file__))
    engine_dir = os.path.join(base_dir, 'engine')
    os.makedirs(engine_dir, exist_ok=True)

    _atomic_pickle_dump(lgb_model, os.path.join(engine_dir, 'bank_security_model.pkl'))
    _atomic_pickle_dump(iso_model, os.path.join(engine_dir, 'bank_anomaly_model.pkl'))
    _atomic_pickle_dump(features, os.path.join(engine_dir, 'model_features.pkl'))

    logger.info("Successfully generated synthetic ML models and feature list.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    generate_models()
