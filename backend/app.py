import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from database.graph_db import init_neo4j
from database.mongo import init_mongo
from database.redis_db import init_redis
from engine.decision_engine import init_decision_engine
from engine.ml_engine import init_ml_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)

app = Flask(__name__)
app.config.from_object(Config)

# Configure CORS properly to allow frontend requests (supports dynamic Flutter ports)
cors_config = {
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "max_age": 3600,
}
CORS(app, resources={r"/api/*": cors_config})

init_mongo(app)
init_redis(app)
init_neo4j(app)

init_ml_engine()
init_decision_engine()


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'success', 'message': 'GraphShield API is running'})


def is_allowed_origin(origin):
    """Check if origin is allowed (localhost or 127.0.0.1 on any port)"""
    if not origin:
        return False
    return origin.startswith('http://localhost:') or origin.startswith('http://127.0.0.1:')


# Global error handler to ensure CORS headers are always present
@app.after_request
def after_request(response):
    # Ensure CORS headers are present on all responses
    origin = request.headers.get('Origin')
    if is_allowed_origin(origin):
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Methods', ', '.join(cors_config['methods']))
        response.headers.add('Access-Control-Allow-Headers', ', '.join(cors_config['allow_headers']))
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_preflight(path):
    """Handle CORS preflight requests"""
    origin = request.headers.get('Origin')
    if is_allowed_origin(origin):
        return '', 204
    return '', 403


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'message': str(e)}), 404


@app.errorhandler(500)
def internal_error(e):
    logger = logging.getLogger(__name__)
    logger.error(f"Internal server error: {e}")
    return jsonify({'error': 'Internal server error', 'message': 'Please try again later'}), 500


from auth.routes import auth_bp, security_bp

app.register_blueprint(auth_bp, url_prefix='/api/v1')
app.register_blueprint(security_bp, url_prefix='/api')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
