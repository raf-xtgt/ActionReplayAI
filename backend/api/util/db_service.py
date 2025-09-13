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
from model.context_model import (CoachAgentRiskAnalysis, CoachAgentSolution, CoachAgentSolutionAnalysis, CoachAgentProblemAnalysis)
from typing import List


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
        # print("client objections", objection_descriptions)
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

def get_client_with_detailed_objections(client_profile_id):
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
        # print("client objections", objection_descriptions)
        initial_context = " ".join(objection_descriptions)
        
        # Embedding search
        embedding = get_query_embedding(initial_context)
        embedding_results = session.query(DatabaseEntity).filter(
            DatabaseEntity.type == 'Objection'
        ).order_by(
            DatabaseEntity.description_vec.cosine_distance(embedding)
        ).limit(20).all()
        em_objs = [obj.description for obj in embedding_results]
        
        # BM25 search (simplified)
        bm25_results = session.query(DatabaseEntity).filter(
            and_(
                DatabaseEntity.type == 'Objection',
                or_(
                    DatabaseEntity.description.contains(term) for term in initial_context.split()[:5]
                )
            )
        ).limit(20).all()
        bm25_objs = [obj.description for obj in bm25_results]
        related_objs = list(set(em_objs + bm25_objs))
               
        return {
            "client_objections": objection_descriptions,
            "related_objections": related_objs
        }

def get_solutions_to_objections(analysis: CoachAgentProblemAnalysis):
    with SessionLocal() as session:
        # Extract risk descriptions
        risk_analysis = analysis.risk
        risk_descriptions = [risk.description for risk in risk_analysis.risks]
        risk_query_text = " ".join(risk_descriptions)
        risk_strategies = get_strategies(risk_query_text)

        behavioral_analysis = analysis.behavioral
        behavioral_descriptions = [b.interpretation for b in behavioral_analysis.behavioral_cues]
        bhv_query_text = " ".join(behavioral_descriptions)
        bhv_strategies = get_strategies(bhv_query_text)
        
        risk_solutions = get_solutions(risk_strategies)
        bhv_solutions = get_solutions(bhv_strategies)
        solutions = list(set(risk_solutions + bhv_solutions))
        return solutions

def get_strategies(query_text):
    with SessionLocal() as session:
        # Embedding search
        embedding = get_query_embedding(query_text)
        embedding_results = session.query(DatabaseEntity).filter(
            DatabaseEntity.type == 'Strategy'
        ).order_by(
            DatabaseEntity.description_vec.cosine_distance(embedding)
        ).limit(10).all()
            
        # BM25 search
        bm25_results = session.query(DatabaseEntity).filter(
            and_(
                DatabaseEntity.type == 'Strategy',
                or_(
                    DatabaseEntity.description.contains(term) for term in query_text.split()
                )
            )
        ).limit(10).all()
            
        # Combine and deduplicate strategies
        unique_strategies = {s.id: s for s in embedding_results}
        unique_strategies.update({s.id: s for s in bm25_results})
        return unique_strategies

def get_solutions(unique_strategies):
    solution_analysis = CoachAgentSolutionAnalysis()
    with SessionLocal() as session:
        for strategy in unique_strategies.values():
            # Find techniques for the strategy
            techniques = session.query(DatabaseEntity).join(
                DatabaseRelationship,
                DatabaseRelationship.target_entity_id == DatabaseEntity.id
            ).filter(
                DatabaseRelationship.source_entity_id == strategy.id,
                DatabaseRelationship.relationship_type == "USES"
            ).all()
                
            for technique in techniques:
                # Find outcomes for the technique
                outcomes = session.query(DatabaseEntity).join(
                    DatabaseRelationship,
                    DatabaseRelationship.target_entity_id == DatabaseEntity.id
                ).filter(
                    DatabaseRelationship.source_entity_id == technique.id,
                    DatabaseRelationship.relationship_type == "RESULTS_IN"
                ).all()
                    
                for outcome in outcomes:
                    sol  = CoachAgentSolution(
                        strategy=strategy.description, 
                        technique=technique.description,
                        outcome=outcome.description)
                    solution_analysis.analysis.append(sol)
      
        return solution_analysis

