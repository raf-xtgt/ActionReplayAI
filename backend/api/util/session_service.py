from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    JSON,
    ForeignKey,
    BLOB,
    Enum as SQLEnum,
    DateTime,
    URL,
    create_engine,
    or_,
    and_,
    inspect
)
from config.tidb_config import (
    engine, Base, SessionLocal
)
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.orm import relationship
import ollama
from flask import jsonify
from .knowledge_graph import ( DatabaseEntity, DatabaseRelationship, get_query_embedding )
from typing import Optional, Dict, List


def update_session_cache(session_data: dict):
    """Update session cache based on current conversation"""
    conversation_text = " ".join([
        turn["content"] for turn in session_data["conversation"]
    ])
    
    with SessionLocal() as session:
        # Update embedding cache
        embedding = get_query_embedding(conversation_text)
        new_embedding_results = session.query(DatabaseEntity).order_by(
            DatabaseEntity.description_vec.cosine_distance(embedding)
        ).limit(20).all()
        session_data["embedding_cache"] = [obj.entity_id for obj in new_embedding_results]
        
        # Update BM25 cache
        new_bm25_results = session.query(DatabaseEntity).filter(
            or_(
                DatabaseEntity.description.contains(term) for term in conversation_text.split()[:5]
            )
        ).limit(20).all()
        session_data["bm25_cache"] = [obj.entity_id for obj in new_bm25_results]
