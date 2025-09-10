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
from config.tidb_config import (SessionLocal)
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.orm import relationship
import ollama
from flask import jsonify
from .knowledge_graph import ( DatabaseEntity, DatabaseRelationship, get_query_embedding )


def get_client_profile(client_profile_id):
    with SessionLocal() as session:
        # Query for the client profile with the given entity_id
        profile = session.query(DatabaseEntity).filter(
            DatabaseEntity.entity_id == client_profile_id,
            DatabaseEntity.type == "ClientProfile"
        ).first()
        
        if not profile:
            return jsonify({"error": "Client profile not found"}), 404
        
        return {
            "id": profile.entity_id,
            "name": profile.name,
            "description": profile.description,
            "properties": profile.properties  # Include additional properties if needed
        }

def get_client_objections(client_profile_id):
    with SessionLocal() as session:
        # Get objections for this client profile
        client_profile = session.query(DatabaseEntity).filter(
            DatabaseEntity.entity_id == client_profile_id,
            DatabaseEntity.type == "ClientProfile"
        ).first()
        
        if not client_profile:
            return jsonify({"error": "Client profile not found"}), 404
        
        # Get related objections
        objections = session.query(DatabaseEntity).join(
            DatabaseRelationship,
            DatabaseRelationship.target_entity_id == DatabaseEntity.id
        ).filter(
            DatabaseRelationship.source_entity_id == client_profile.id,
            DatabaseRelationship.relationship_type == "HAS_OBJECTION"
        ).all()
        
        # Perform initial searches
        objection_descriptions = [obj.description for obj in objections]
        initial_context = " ".join(objection_descriptions)
        
        # Embedding search
        embedding = get_query_embedding(initial_context)
        embedding_results = session.query(DatabaseEntity).order_by(
            DatabaseEntity.description_vec.cosine_distance(embedding)
        ).limit(20).all()
        em_objs = [obj.description for obj in embedding_results]
        
        # BM25 search (simplified)
        bm25_results = session.query(DatabaseEntity).filter(
            or_(
                DatabaseEntity.description.contains(term) for term in initial_context.split()[:5]
            )
        ).limit(20).all()
        bm25_objs = [obj.description for obj in bm25_results]
        related_objs = list(set(em_objs + bm25_objs))
               
        return {
            "client_objections": objection_descriptions,
            "related_objections": related_objs
        }

