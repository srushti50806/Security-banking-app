import logging
import uuid
import json
from datetime import datetime

from database.mongo import get_db
from engine.ml_engine import get_ml_engine
from engine.feature_engineering import compute_features

logger = logging.getLogger(__name__)


class DecisionEngine:
    def __init__(self):
        pass

    def evaluate_login(
        self,
        user_id,
        device_id,
        ip_address,
        bank_id,
        session_id=None,
        metadata=None,
        insert_event=True,
    ):
        import concurrent.futures
        from database.s3_client import get_s3_client
        from config import Config

        now_dt = datetime.utcnow()
        if not session_id:
            timestamp_prefix = now_dt.strftime("SESSION_%Y%m%d_%H%M%S")
            session_id = f"{timestamp_prefix}_{uuid.uuid4().hex[:6]}"

        db = get_db()

        # Compute features
        if metadata and 'features' in metadata:
            features = metadata['features']
        else:
            features = compute_features(
                user_id=user_id,
                device_id=device_id,
                ip_address=ip_address,
                redis_client=None,
                db=db,
                bank_id=bank_id,
                metadata=metadata,
            )

        ml_engine = get_ml_engine()
        s3 = get_s3_client()

        # Log to S3
        if s3:
            s3.log_orchestrator(f"Starting parallel security evaluation for session {session_id}")
            # Upload raw telemetry
            s3.upload_file(s3.bucket_name, f"{session_id}/raw/telemetry_payload.bin", json.dumps({
                "user_id": user_id,
                "device_id": device_id,
                "ip_address": ip_address,
                "bank_id": bank_id,
                "metadata": metadata
            }).encode('utf-8'))
            s3.upload_file(s3.bucket_name, f"{session_id}/raw/metadata_header.json", {
                "session_id": session_id,
                "timestamp": now_dt.isoformat(),
                "client_ip": ip_address
            })

            # Upload extracted features
            s3.upload_file(s3.bucket_name, f"{session_id}/extracted/normalized_features.csv", [features])
            s3.upload_file(s3.bucket_name, f"{session_id}/extracted/hardware_fingerprint.json", {
                "device_id": device_id,
                "os": metadata.get("os") if metadata else None,
                "platform": metadata.get("platform") if metadata else None,
                "screen_size": metadata.get("screen_size") if metadata else None
            })

        # Parallel inference and graph query execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Task 1: ML Score
            ml_future = executor.submit(lambda: ml_engine.compute_ml_score(features) if ml_engine else 0.2)
            
            # Task 2: Graph Score
            def calc_graph_score():
                g_score = 0.0
                from database.graph_db import get_graph
                graph_db = get_graph()
                if graph_db:
                    # Log activity in graph DB (uses fallback under the hood if Neo4j is down)
                    graph_db.log_activity(user_id, device_id, ip_address, bank_id)
                    
                    device_users = graph_db.detect_device_reuse(device_id)
                    ip_count = graph_db.detect_ip_rotation(device_id)
                    bank_count = graph_db.detect_cross_bank(device_id)
                    
                    if device_users > 2:
                        g_score += 0.4
                    if ip_count > 3:
                        g_score += 0.3
                    if bank_count > 1:
                        g_score += 0.5
                return min(g_score, 1.0)

            graph_future = executor.submit(calc_graph_score)

            ml_score = ml_future.result()
            graph_score = graph_future.result()

        # Upload graph edge visualization structure
        if s3:
            cypher_snippet = f'MERGE (u:User {{user_id: "{user_id}"}}) MERGE (d:Device {{device_id: "{device_id}"}}) MERGE (i:IP {{ip: "{ip_address}"}}) MERGE (b:Bank {{bank_id: "{bank_id}"}}) MERGE (u)-[:USES]->(d) MERGE (d)-[:CONNECTED_TO]->(i) MERGE (u)-[:BELONGS_TO]->(b);'
            s3.upload_file(s3.bucket_name, f"{session_id}/graph/edge_connections.cypher", cypher_snippet)
            npz_mock = {
                "nodes": [user_id, device_id, ip_address, bank_id],
                "edges": [[user_id, device_id], [device_id, ip_address], [user_id, bank_id]]
            }
            s3.upload_file(s3.bucket_name, f"{session_id}/graph/adjacency_matrix.npz", json.dumps(npz_mock).encode('utf-8'))

        # SHAP explainability calculations
        shap_attributions = ml_engine.explain_risk_score(features) if ml_engine else {}
        reasons = []
        if shap_attributions:
            sorted_feats = sorted(shap_attributions.items(), key=lambda item: item[1]['percentage'], reverse=True)
            for feat, data in sorted_feats[:3]:
                if data['percentage'] > 0.1:
                    reasons.append(f"{feat.replace('_', ' ').title()} accounts for {int(data['percentage']*100)}% of the ML risk score.")

        if not reasons:
            reasons = ["Normal feature profile"]

        # Final consolidated decision
        # Verdict = BLOCK if w1*S_lgbm + w2*S_graph >= t else ALLOW
        # w1 = 0.5, w2 = 0.5, threshold = 0.5 (or block threshold config)
        final_score = 0.5 * ml_score + 0.5 * graph_score
        block_threshold = float(Config.RISK_BLOCK_THRESHOLD) if hasattr(Config, 'RISK_BLOCK_THRESHOLD') else 0.5
        
        # Override threshold for standard rule-based triggers
        if final_score > 0.5:
            decision = "BLOCK"
            risk_level = "HIGH"
            client_reason = "Suspicious activity detected (high ML or graph relational risk)"
        else:
            decision = "ALLOW"
            risk_level = "LOW"
            client_reason = "Normal authentication path"

        print("FEATURES:", features)
        print("ML SCORE:", ml_score)
        print("GRAPH SCORE:", graph_score)
        print("FINAL SCORE:", final_score)

        rule_penalty = 0.0
        attack_type = 'NONE'
        if ml_score > 0.7:
            attack_type = 'CREDENTIAL_STUFFING'
        elif graph_score > 0.6:
            attack_type = 'SESSION_HIJACKING'

        # Upload verdict and SHAP matrix to S3
        if s3:
            verdict_payload = {
                'decision': decision,
                'session_id': session_id,
                'ml_score': ml_score,
                'graph_score': graph_score,
                'final_score': final_score,
                'risk_level': risk_level,
                'reasons': reasons,
                'attack_type': attack_type,
                'timestamp': now_dt.isoformat()
            }
            s3.upload_file(s3.bucket_name, f"{session_id}/alerts/evaluation_verdict.json", verdict_payload)
            s3.upload_file(s3.bucket_name, f"{session_id}/alerts/shap_attribution_matrix.json", shap_attributions)
            s3.log_orchestrator(f"Consolidated verdict reached for session {session_id}: {decision} (Score: {final_score:.3f})")

        if db is not None and insert_event:
            event = {
                'user_id': str(user_id),
                'session_id': session_id,
                'device_id': device_id,
                'ip_address': ip_address,
                'bank_id': bank_id,
                'event_source': 'OUTSIDER_LOGIN',
                'ml_score': ml_score,
                'graph_score': graph_score,
                'rule_penalty': rule_penalty,
                'final_score': final_score,
                'risk_score': final_score,
                'risk_level': risk_level,
                'decision': decision,
                'features': features,
                'reasons': reasons,
                'shap_attributions': shap_attributions,
                's3_path': f"s3://{s3.bucket_name}/{session_id}/" if s3 else None,
                'attack_type': attack_type,
                'timestamp': now_dt.timestamp(),
            }
            db.risk_events.insert_one(event)

            log = {
                'user_id': str(user_id),
                'session_id': session_id,
                'bank_id': bank_id,
                'device_id': device_id,
                'ip_address': ip_address,
                'decision': decision,
                'risk_level': risk_level,
                'risk_score': final_score,
                'status': 'success',
                'timestamp': now_dt.timestamp(),
            }
            db.login_logs.insert_one(log)

            db.trusted_devices.update_one(
                {'user_id': str(user_id), 'device_id': device_id},
                {
                    '$setOnInsert': {
                        'user_id': str(user_id),
                        'device_id': device_id,
                        'created_at': now_dt.timestamp(),
                    }
                },
                upsert=True,
            )

        logger.info(
            "%s decision user=%s session=%s score=%.3f",
            decision,
            user_id,
            session_id,
            final_score,
        )

        return {
            'decision': decision,
            'session_id': session_id,
            'ml_score': round(ml_score, 3),
            'graph_score': round(graph_score, 3),
            'rule_penalty': round(rule_penalty, 3),
            'final_score': round(final_score, 3),
            'risk_score': round(final_score, 3),
            'risk_level': risk_level,
            'reason': client_reason,
            'reasons': reasons,
            'shap_attributions': shap_attributions,
            's3_path': f"s3://{s3.bucket_name}/{session_id}/" if s3 else None,
            'attack_type': attack_type,
        }


decision_engine_instance = None


def init_decision_engine():
    global decision_engine_instance
    decision_engine_instance = DecisionEngine()
    logger.info("Initialized Decision Engine")


def get_decision_engine():
    return decision_engine_instance
