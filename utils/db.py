import json
import os
import uuid
import time
from datetime import datetime

class NeDB:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = []
        self.load()

    def load(self):
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
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            for item in self.data:
                f.write(json.dumps(item) + '\n')
            # Add NeDB index record back for complete compatibility
            f.write(json.dumps({"$$indexCreated": {"fieldName": "userId"}}) + '\n')

    def find(self, query):
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
        results = self.find(query)
        return results[0] if results else None

    def insert(self, doc):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4()).replace('-', '')[:16]  # NeDB format
        if "createdAt" not in doc:
            doc["createdAt"] = {"$$date": int(time.time() * 1000)}
        self.data.append(doc)
        self.save_all()
        return doc

    def update(self, query, update_doc):
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
