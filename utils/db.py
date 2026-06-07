import json
import os
import uuid
import time
from datetime import datetime

# ── Import MongoDB client ──
try:
    from pymongo import MongoClient
    from bson import ObjectId
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False


class MongoDBWrapper:
    def __init__(self, collection_name: str, connection_uri: str):
        self.client = MongoClient(connection_uri)
        # Parse database name from connection_uri if possible, fallback to 'agentfirst'
        try:
            self.db = self.client.get_default_database()
            if self.db is None:
                self.db = self.client["agentfirst"]
        except Exception:
            self.db = self.client["agentfirst"]
        self.collection = self.db[collection_name]

    def _convert_id_in_query(self, query):
        if not query:
            return {}
        q = query.copy()
        if "_id" in q:
            val = q["_id"]
            if isinstance(val, str) and len(val) == 24:
                try:
                    q["_id"] = ObjectId(val)
                except Exception:
                    pass
        return q

    def _serialize_doc(self, doc):
        if not doc:
            return None
        d = doc.copy()
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    def find(self, query):
        q = self._convert_id_in_query(query)
        cursor = self.collection.find(q)
        return [self._serialize_doc(doc) for doc in cursor]

    def find_one(self, query):
        q = self._convert_id_in_query(query)
        doc = self.collection.find_one(q)
        return self._serialize_doc(doc)

    def insert(self, doc):
        d = doc.copy()
        # If _id exists as a string, check if we should keep it or convert to ObjectId
        if "_id" in d:
            val = d["_id"]
            if isinstance(val, str) and len(val) == 24:
                try:
                    d["_id"] = ObjectId(val)
                except Exception:
                    pass
        else:
            # Check if NeDB format string should be used, or let mongo assign ObjectId
            # We assign standard 24-character hex ID string or MongoDB ObjectId
            pass
            
        if "createdAt" not in d:
            d["createdAt"] = {"$$date": int(time.time() * 1000)}
            
        res = self.collection.insert_one(d)
        d["_id"] = str(res.inserted_id)
        return d

    def update(self, query, update_doc):
        q = self._convert_id_in_query(query)
        # Convert update_doc values if they use query patterns
        res = self.collection.update_many(q, update_doc)
        return res.modified_count

    def remove(self, query):
        q = self._convert_id_in_query(query)
        res = self.collection.delete_many(q)
        return res.deleted_count


class NeDB:
    def __init__(self, filepath):
        self.filepath = filepath
        self.use_mongo = False
        
        # Determine connection from environment
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri and HAS_PYMONGO:
            filename = os.path.basename(filepath)
            collection_name = filename.split(".")[0]  # e.g. "users" or "projects"
            try:
                self.mongo = MongoDBWrapper(collection_name, mongo_uri)
                self.use_mongo = True
                print(f"Connected to MongoDB collection: {collection_name}")
                return
            except Exception as e:
                print(f"Failed to connect to MongoDB, falling back to local files: {e}")
                
        # Local NeDB File implementation
        self.data = []
        self.load()

    def load(self):
        if self.use_mongo:
            return
        if not os.path.exists(self.filepath):
            return
        self.data = []
        with open(self.filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # Skip NeDB index creation records
                    if "$$indexCreated" in obj:
                        continue
                    self.data.append(obj)
                except Exception as e:
                    print(f"Error parsing line in NeDB file {self.filepath}:", e)

    def save_all(self):
        if self.use_mongo:
            return
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            for item in self.data:
                f.write(json.dumps(item) + '\n')
            # Add NeDB index record back for compatibility
            f.write(json.dumps({"$$indexCreated": {"fieldName": "userId"}}) + '\n')

    def find(self, query):
        if self.use_mongo:
            return self.mongo.find(query)
            
        results = []
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                results.append(item)
        return results

    def find_one(self, query):
        if self.use_mongo:
            return self.mongo.find_one(query)
            
        results = self.find(query)
        return results[0] if results else None

    def insert(self, doc):
        if self.use_mongo:
            return self.mongo.insert(doc)
            
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4()).replace('-', '')[:16]  # NeDB format
        if "createdAt" not in doc:
            doc["createdAt"] = {"$$date": int(time.time() * 1000)}
        self.data.append(doc)
        self.save_all()
        return doc

    def update(self, query, update_doc):
        if self.use_mongo:
            return self.mongo.update(query, update_doc)
            
        updated_count = 0
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                if "$set" in update_doc:
                    for uk, uv in update_doc["$set"].items():
                        item[uk] = uv
                else:
                    item.update(update_doc)
                updated_count += 1
        if updated_count > 0:
            self.save_all()
        return updated_count

    def remove(self, query):
        if self.use_mongo:
            return self.mongo.remove(query)
            
        new_data = []
        removed = 0
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                removed += 1
            else:
                new_data.append(item)
        if removed > 0:
            self.data = new_data
            self.save_all()
        return removed


# Helper to normalize gmail address (e.g. dots & plus signs)
def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not email:
        return ""
    if "@" in email:
        local, domain = email.split("@", 1)
        if domain in ["gmail.com", "googlemail.com"]:
            if "+" in local:
                local = local.split("+", 1)[0]
            local = local.replace(".", "")
            domain = "gmail.com"
        return f"{local}@{domain}"
    return email


# Format date from NeDB timestamp object
def format_date(timestamp_obj) -> str:
    if isinstance(timestamp_obj, dict) and "$$date" in timestamp_obj:
        ts = timestamp_obj["$$date"] / 1000.0
    elif isinstance(timestamp_obj, (int, float)):
        ts = timestamp_obj / 1000.0
    else:
        return str(timestamp_obj)
    
    dt = datetime.fromtimestamp(ts)
    day = dt.day
    month = dt.strftime("%B")
    year = dt.year
    return f"{day} {month} {year}"
