from pymongo import MongoClient
from pprint import pprint

client = MongoClient('mongodb://127.0.0.1:27017/')
db = client['graphshield']
doc = db.risk_events.find_one()
pprint(doc)
