import logging
import os
import pickle

import pandas as pd

logger = logging.getLogger(__name__)


class MLEngine:
    def __init__(self):
        self.lgb_model = None
        self.iso_model = None
        self.features_list = None
        self.load_models()

    def _load_pickle(self, path):
        with open(path, 'rb') as handle:
            return pickle.load(handle)

    def _load_from_disk(self, base_dir):
        self.lgb_model = self._load_pickle(os.path.join(base_dir, 'bank_security_model.pkl'))
        self.iso_model = self._load_pickle(os.path.join(base_dir, 'bank_anomaly_model.pkl'))
        self.features_list = self._load_pickle(os.path.join(base_dir, 'model_features.pkl'))

        if not hasattr(self.lgb_model, 'predict_proba'):
            raise TypeError("bank_security_model.pkl does not expose predict_proba")
        if not hasattr(self.iso_model, 'decision_function'):
            raise TypeError("bank_anomaly_model.pkl does not expose decision_function")
        if not isinstance(self.features_list, list):
            raise TypeError("model_features.pkl is not a feature list")

    def load_models(self):
        base_dir = os.path.dirname(__file__)
        try:
            self._load_from_disk(base_dir)
            logger.info("Loaded ML models successfully.")
        except Exception as load_error:
            logger.warning("Failed to load ML models: %s. Attempting regeneration.", load_error)
            try:
                from mock_models.generate_models import generate_models

                generate_models()
                self._load_from_disk(base_dir)
                logger.info("Regenerated and loaded ML models successfully.")
            except Exception as regen_error:
                logger.critical(
                    "Failed to regenerate ML models: %s. Run `python backend/mock_models/generate_models.py`.",
                    regen_error,
                )

    def compute_ml_score(self, feature_dict):
        if not self.lgb_model or not self.iso_model or not self.features_list:
            return 0.0

        vector = []
        for feat in self.features_list:
            vector.append(feature_dict.get(feat, 0))

        df = pd.DataFrame([vector], columns=self.features_list)
        lgbm_prob = self.lgb_model.predict_proba(df)[0][1]

        iso_decision = self.iso_model.decision_function(df)[0]
        anomaly_score = 1.0 if iso_decision < 0 else 0.0

        ml_score = 0.7 * lgbm_prob + 0.3 * anomaly_score
        
        logger.info(f"ML Features Input: {feature_dict}")
        logger.info(f"Raw LGBM prob (y_prob): {lgbm_prob:.4f}, ISO decision: {iso_decision:.4f}, Anomaly Score: {anomaly_score}")

        return min(max(ml_score, 0.0), 1.0)

    def explain_risk_score(self, feature_dict):
        """
        Runs TreeSHAP on the input features using LightGBM natively with pred_contrib=True.
        Returns a dictionary containing percentage attribution for each feature.
        """
        if not self.lgb_model or not self.features_list:
            return {}

        vector = []
        for feat in self.features_list:
            vector.append(feature_dict.get(feat, 0))

        df = pd.DataFrame([vector], columns=self.features_list)
        try:
            contribs = self.lgb_model.predict(df, pred_contrib=True)
            shap_values = contribs[0][:-1]  # exclude the base value (last element)
        except Exception:
            try:
                contribs = self.lgb_model.booster_.predict(df, pred_contrib=True)
                shap_values = contribs[0][:-1]
            except Exception as e:
                logger.error(f"Error computing TreeSHAP: {e}")
                return {}

        # Decompose absolute feature contributions into percentages
        abs_shap = [abs(val) for val in shap_values]
        total_abs = sum(abs_shap)
        
        attributions = {}
        for i, feat in enumerate(self.features_list):
            val = shap_values[i]
            pct = (abs_shap[i] / total_abs) if total_abs > 0 else 0.0
            attributions[feat] = {
                'shap_value': float(val),
                'percentage': round(pct, 4)
            }
        return attributions



ml_engine_instance = None


def init_ml_engine():
    global ml_engine_instance
    ml_engine_instance = MLEngine()


def get_ml_engine():
    return ml_engine_instance
