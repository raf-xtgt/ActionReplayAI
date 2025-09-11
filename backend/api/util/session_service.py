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
from model.context_model import (SessionModel, ClientAgentContextModel)
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.orm import relationship
import ollama
from flask import jsonify
from .knowledge_graph import ( DatabaseEntity, DatabaseRelationship, DatabaseSession, get_query_embedding )
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

def create_new_session(session_model: SessionModel):
    print("create new session")
    with SessionLocal() as session:
        session_entity = DatabaseSession(
            guid=session_model.session_id,
            client_agent_context=session_model.client_agent_context.dict(),
            round_count = session_model.round_count
        )
        session.add(session_entity)
        session.commit()

def get_session_by_id(session_id: str):
    print("get session by id")
    with SessionLocal() as session:
        session_entity = session.query(DatabaseSession).filter(
            DatabaseSession.guid == session_id
        ).first()

        if not session_entity:
            return None

        # Convert client_agent_context JSON -> ClientAgentContextModel
        client_context = ClientAgentContextModel(**session_entity.client_agent_context)

        # Build SessionModel
        return SessionModel(
            session_id=session_entity.guid,
            client_agent_context=client_context,
            round_count=session_entity.round_count
        )

def update_session_by_id(session_id: str, updatedSession: SessionModel):
    print(f"update session by id: {session_id}")
    with SessionLocal() as session:
        # Find the session by ID
        session_entity = session.query(DatabaseSession).filter(
            DatabaseSession.guid == session_id
        ).first()

        if not session_entity:
            print(f"Session with id {session_id} not found")
            return False


        session_entity.client_agent_context = updatedSession.client_agent_context.dict()
        session_entity.round_count = updatedSession.round_count
        
        session.commit()
        print(f"Session {session_id} updated successfully")
        return True