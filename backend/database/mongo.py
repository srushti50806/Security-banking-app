import logging
from copy import deepcopy

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_mongo_client = None
_db = None


class InMemoryInsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class InMemoryUpdateResult:
    def __init__(self, matched_count=0, modified_count=0, upserted_id=None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id


class InMemoryCursor:
    def __init__(self, documents):
        self._documents = list(documents)

    def sort(self, key, direction):
        reverse = int(direction) < 0
        self._documents.sort(
            key=lambda item: _sort_value(item.get(key)),
            reverse=reverse,
        )
        return self

    def limit(self, count):
        self._documents = self._documents[: max(int(count), 0)]
        return self

    def __iter__(self):
        return iter(self._documents)


class InMemoryCollection:
    def __init__(self, name):
        self.name = name
        self._documents = []

    def create_index(self, *args, **kwargs):
        return None

    def find_one(self, query=None, projection=None):
        for document in self._documents:
            if _matches_query(document, query or {}):
                return _apply_projection(document, projection)
        return None

    def find(self, query=None, projection=None):
        documents = [
            _apply_projection(document, projection)
            for document in self._documents
            if _matches_query(document, query or {})
        ]
        return InMemoryCursor(documents)

    def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault('_id', ObjectId())
        self._documents.append(stored)
        return InMemoryInsertOneResult(stored['_id'])

    def update_one(self, query, update, upsert=False):
        for index, document in enumerate(self._documents):
            if _matches_query(document, query or {}):
                updated = deepcopy(document)
                _apply_update(updated, update or {})
                self._documents[index] = updated
                return InMemoryUpdateResult(matched_count=1, modified_count=1)

        if not upsert:
            return InMemoryUpdateResult()

        base = {}
        for key, value in (query or {}).items():
            if key.startswith('$') or isinstance(value, dict):
                continue
            base[key] = deepcopy(value)
        _apply_update(base, update or {}, is_insert=True)
        base.setdefault('_id', ObjectId())
        self._documents.append(base)
        return InMemoryUpdateResult(
            matched_count=0,
            modified_count=1,
            upserted_id=base['_id'],
        )

    def count_documents(self, query=None):
        return sum(
            1
            for document in self._documents
            if _matches_query(document, query or {})
        )

    def distinct(self, field, query=None):
        values = []
        seen = set()
        for document in self._documents:
            if not _matches_query(document, query or {}):
                continue
            value = document.get(field)
            marker = repr(value)
            if marker in seen:
                continue
            seen.add(marker)
            values.append(deepcopy(value))
        return values


class InMemoryDatabase:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return self._collections.setdefault(name, InMemoryCollection(name))


def _sort_value(value):
    if value is None:
        return (0, 0)
    if isinstance(value, (int, float)):
        return (1, float(value))
    return (2, str(value))


def _normalize_document(document):
    normalized = deepcopy(document)
    normalized.setdefault('_id', ObjectId())
    return normalized


def _matches_query(document, query):
    if not query:
        return True

    for key, expected in query.items():
        if key == '$or':
            if not any(_matches_query(document, option or {}) for option in expected or []):
                return False
            continue

        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == '$gt':
                    if actual is None or actual <= value:
                        return False
                elif operator == '$in':
                    if actual not in (value or []):
                        return False
                else:
                    return False
        elif actual != expected:
            return False

    return True


def _apply_projection(document, projection):
    if projection is None:
        return deepcopy(document)

    include_fields = {
        key
        for key, value in projection.items()
        if key != '_id' and bool(value)
    }
    exclude_id = projection.get('_id') == 0

    if include_fields:
        projected = {}
        if not exclude_id and '_id' in document:
            projected['_id'] = deepcopy(document['_id'])
        for field in include_fields:
            if field in document:
                projected[field] = deepcopy(document[field])
        return projected

    projected = deepcopy(document)
    if exclude_id:
        projected.pop('_id', None)
    return projected


def _apply_update(document, update, is_insert=False):
    for key, values in update.items():
        if key == '$set':
            for field, value in values.items():
                document[field] = deepcopy(value)
        elif key == '$unset':
            for field in values.keys():
                document.pop(field, None)
        elif key == '$setOnInsert':
            if is_insert:
                for field, value in values.items():
                    document[field] = deepcopy(value)
        else:
            document[key] = deepcopy(values)


def init_mongo(app):
    global _mongo_client, _db

    uri = app.config.get('MONGO_URI', 'mongodb://127.0.0.1:27017/')
    db_name = app.config.get('MONGO_DB_NAME', 'graphshield')

    try:
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        _mongo_client.admin.command('ping')
        _db = _mongo_client[db_name]
        logger.info("Connected to MongoDB at %s", uri)
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        logger.warning(
            "Failed to connect to MongoDB: %s. Falling back to in-memory storage.",
            exc,
        )
        _mongo_client = None
        _db = InMemoryDatabase()

    _ensure_indexes(_db)


def _ensure_indexes(db):
    db.risk_events.create_index('user_id')
    db.risk_events.create_index('bank_id')
    db.risk_events.create_index('bank_name')
    db.risk_events.create_index('timestamp')
    db.risk_events.create_index([('bank_id', 1), ('user_id', 1), ('timestamp', -1)])
    db.login_logs.create_index([('bank_id', 1), ('user_id', 1), ('timestamp', -1)])
    db.trusted_devices.create_index([('user_id', 1), ('device_id', 1)], unique=True)
    db.api_keys.create_index('api_key', unique=True, sparse=True)
    db.api_keys.create_index('api_key_hash', unique=True, sparse=True)
    db.subscription_requests.create_index([('bank_id', 1), ('status', 1), ('created_at', -1)])


def get_db():
    return _db


def close_mongo():
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
