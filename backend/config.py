import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-graphshield-key')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://127.0.0.1:27017/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'graphshield')
    REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Neo4j
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
    RISK_BLOCK_THRESHOLD = float(os.environ.get('RISK_BLOCK_THRESHOLD', 0.85))
    BANK_API_KEYS_JSON = os.environ.get('BANK_API_KEYS_JSON', '{}')
