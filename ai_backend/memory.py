"""
memory.py — RAG Memory System for Antigravity Clone
=====================================================
Stores every conversation in MongoDB with vector embeddings.
On each new session, retrieves the most relevant past conversations
and injects them into the LLM context.

MongoDB document structure (same as Mongoose schema in Express):
{
  user_message:   "what is startup india fund?",
  agent_response: "The Startup India Seed Fund...",
  combined_text:  "User: what is... Agent: The Startup...",
  embedding:      [0.12, -0.34, ...],   # 384-dim vector
  timestamp:      ISODate("2026-05-17T...")
}
"""

import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

# ── Config ──────────────────────────────────────────────────────────
MONGO_URL  = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
DB_NAME    = "antigravity_memory"
COLL_NAME  = "conversations"
MODEL_NAME = "all-MiniLM-L6-v2"   # lightweight ~90MB, runs locally
TOP_K      = 3                     # how many past conversations to retrieve
MIN_SIM    = 0.3                   # minimum similarity score to include

# ── Lazy globals ────────────────────────────────────────────────────
_client     = None
_collection = None
_model      = None


# ════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ════════════════════════════════════════════════════════════════════

def _get_collection():
    """Connect to MongoDB (same as mongoose.connect in Express)."""
    global _client, _collection
    if _collection is None:
        _client     = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        _collection = _client[DB_NAME][COLL_NAME]
        # Create index on timestamp for faster queries
        _collection.create_index("timestamp")
    return _collection


def _get_model():
    """Load embedding model (only on first call — downloads ~90MB once)."""
    global _model
    if _model is None:
        print("🧠 Loading embedding model (first time downloads ~90MB)...")
        _model = SentenceTransformer(MODEL_NAME)
        print("✅ Embedding model ready")
    return _model


def _embed(text: str) -> list:
    """Convert text to a 384-dimensional vector (the 'embedding')."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def _cosine_similarity(vec_a: list, vec_b: list) -> float:
    """
    Compute similarity between two vectors (0.0 = unrelated, 1.0 = identical).
    Same math as MongoDB Atlas Vector Search uses internally.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


# ════════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════════

def save_conversation(user_message: str, agent_response: str) -> bool:
    """
    Save a conversation to MongoDB with its embedding.
    Like: await Conversation.create({...}) in Express/Mongoose.

    Returns True if saved, False if MongoDB unavailable.
    """
    try:
        coll = _get_collection()

        # Combine both messages into one text for embedding
        combined = f"User: {user_message}\nAgent: {agent_response}"
        embedding = _embed(combined)

        # Insert document (same fields as a Mongoose schema)
        coll.insert_one({
            "user_message":   user_message,
            "agent_response": agent_response,
            "combined_text":  combined,
            "embedding":      embedding,
            "timestamp":      datetime.now(timezone.utc)
        })
        return True

    except Exception as e:
        print(f"⚠️  Memory save failed (MongoDB unavailable?): {e}")
        return False


def retrieve_relevant(query: str, top_k: int = TOP_K) -> list:
    """
    Find the most relevant past conversations for a given query.
    Like: Conversation.find({}).sort({score: -1}).limit(3) in Express.

    Returns list of dicts: [{user_message, agent_response, similarity}]
    """
    try:
        coll = _get_collection()

        # Check if any conversations exist
        if coll.count_documents({}) == 0:
            return []

        # Embed the query
        query_embedding = _embed(query)

        # Fetch recent 100 docs (for large histories, use Atlas Vector Search)
        docs = list(coll.find(
            {},
            {"user_message": 1, "agent_response": 1, "embedding": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(100))

        # Compute cosine similarity for each doc
        scored = []
        for doc in docs:
            sim = _cosine_similarity(query_embedding, doc["embedding"])
            scored.append((sim, doc))

        # Sort by similarity (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top_k results above minimum threshold
        results = []
        for sim, doc in scored[:top_k]:
            if sim >= MIN_SIM:
                results.append({
                    "user_message":   doc["user_message"],
                    "agent_response": doc["agent_response"],
                    "similarity":     round(sim, 3)
                })

        return results

    except Exception as e:
        print(f"⚠️  Memory retrieval failed (MongoDB unavailable?): {e}")
        return []


def build_memory_context(query: str) -> str:
    """
    Build a context string from relevant past conversations.
    This gets injected into the LLM's system prompt.
    """
    relevant = retrieve_relevant(query)
    if not relevant:
        return ""

    parts = ["\n📚 RELEVANT PAST CONVERSATIONS (from memory):"]
    for i, conv in enumerate(relevant, 1):
        parts.append(f"\n--- Memory {i} (relevance: {conv['similarity']}) ---")
        parts.append(f"User previously asked: {conv['user_message']}")
        parts.append(f"Agent replied: {conv['agent_response'][:400]}")

    parts.append("\n(Use the above context if relevant to the current question)\n")
    return "\n".join(parts)


def get_stats() -> dict:
    """Return memory stats — like db.conversations.countDocuments() in Express."""
    try:
        coll = _get_collection()
        total = coll.count_documents({})
        oldest = coll.find_one({}, sort=[("timestamp", 1)])
        return {
            "total_conversations": total,
            "oldest": oldest["timestamp"].strftime("%Y-%m-%d") if oldest else None,
            "db": DB_NAME,
            "collection": COLL_NAME
        }
    except Exception as e:
        return {"error": str(e)}
