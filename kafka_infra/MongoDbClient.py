import os
import pymongo
from dotenv import load_dotenv


class MongoDbClient:
    def __init__(self, collection_name):
        load_dotenv()
        connection_string = os.environ.get("MONGO_DB_CONNECTION_STRING_DEV")
        self.db_name = 'anomaly_detection_db'
        self.client = pymongo.MongoClient(connection_string)
        self.database = self.client[self.db_name]
        self.collection = self.database[collection_name]

    def insert_record(self, record):
        callback = self.collection.insert_one(record)
        return callback.inserted_id

    def insert_many_records(self, records_list):
        callback = self.collection.insert_many(records_list)
        return callback.inserted_ids

    def aggregate(self, pipline):
        return self.collection.aggregate(pipline)

    def find(self, query):
        return self.collection.find({}, query)