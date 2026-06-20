"""
Diagnostic script to check if required databases are running
"""
import sys
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import redis
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_mongodb():
    """Check MongoDB connection"""
    try:
        client = MongoClient('mongodb://127.0.0.1:27017/', serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        logger.info("✓ MongoDB is running at 127.0.0.1:27017")
        client.close()
        return True
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        logger.error(f"✗ MongoDB not available: {e}")
        logger.info("  Start MongoDB with: mongod")
        return False

def check_redis():
    """Check Redis connection"""
    try:
        r = redis.Redis(host='127.0.0.1', port=6379, db=0, socket_connect_timeout=2)
        r.ping()
        logger.info("✓ Redis is running at 127.0.0.1:6379")
        return True
    except Exception as e:
        logger.error(f"✗ Redis not available: {e}")
        logger.info("  Start Redis with: redis-server")
        return False

def check_neo4j():
    """Check Neo4j connection"""
    try:
        driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
        driver.verify_connectivity()
        logger.info("✓ Neo4j is running at bolt://localhost:7687")
        driver.close()
        return True
    except Exception as e:
        logger.error(f"✗ Neo4j not available: {e}")
        logger.info("  Neo4j may not be installed or URI/credentials are incorrect")
        return False

if __name__ == '__main__':
    print("\n" + "="*60)
    print("DATABASE CONNECTIVITY CHECK")
    print("="*60 + "\n")
    
    results = {
        'MongoDB': check_mongodb(),
        'Redis': check_redis(),
        'Neo4j': check_neo4j(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for service, available in results.items():
        status = "Available" if available else "Not Available"
        symbol = "✓" if available else "✗"
        print(f"{symbol} {service}: {status}")
    print("="*60 + "\n")
    
    all_ok = all(results.values())
    if not all_ok:
        print("WARNING: Some services are not available.")
        print("The application will start, but some features will be degraded.\n")
    
    sys.exit(0 if all_ok else 1)
