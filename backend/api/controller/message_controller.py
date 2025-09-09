from flask import Blueprint, jsonify, request, Response
import json
from config.tidb_config import (
    engine, Base, SessionLocal, session_cache
)
from model.data_model import (
    ClientProfileResponse,
    ConversationRound,
    CoachAnalysis
)
from model.context_model import (
    coach_agent
)
from agent import (ClientAgent)
from util.knowledge_graph import ( DatabaseEntity, DatabaseRelationship, get_query_embedding )
from util.db_service import ( get_client_objections, get_client_profile )
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
import uuid

msg_bp = Blueprint('msg_bp', __name__)

@msg_bp.route('/send', methods=['POST'])
def send_msg():
    print("send message endpoint")


@msg_bp.route('/client_profiles', methods=['GET'])
def get_client_profiles():
    """Get all available client profiles"""
    with SessionLocal() as session:
        profiles = session.query(DatabaseEntity).filter(
            DatabaseEntity.type == "ClientProfile"
        ).all()
        
        return jsonify([{
            "id": profile.entity_id,
            "name": profile.name,
            "description": profile.description
        } for profile in profiles])

@msg_bp.route('/client_profile/<client_profile_id>', methods=['GET'])
def retrieve_client_profile(client_profile_id):
    """Get specific client profile by ID"""
    return jsonify(get_client_profile(client_profile_id))


@msg_bp.route('/client_profile/objections/<client_profile_id>', methods=['GET'])
def retrieve_client_profile_objections(client_profile_id):
    """Get client profile objections by ID"""
    return jsonify(get_client_objections(client_profile_id)) 

@msg_bp.route('/start_session', methods=['POST'])
def start_session():
    """Start a new session with selected client profile"""
    data = request.json
    client_profile_id = data['client_profile_id']
    
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
        
        # BM25 search (simplified)
        bm25_results = session.query(DatabaseEntity).filter(
            or_(
                DatabaseEntity.description.contains(term) for term in initial_context.split()[:5]
            )
        ).limit(20).all()
        
        # Create session cache
        session_id = str(uuid.uuid4())
        session_cache[session_id] = {
            "client_profile": client_profile_id,
            "objections": [obj.entity_id for obj in objections],
            "embedding_cache": [obj.entity_id for obj in embedding_results],
            "bm25_cache": [obj.entity_id for obj in bm25_results],
            "conversation": [],
            "round_count": 0
        }
        print(json.dumps(session_cache, indent=2, default=str))

        # Get first objection
        first_objection = objections[0] if objections else None
        
        return jsonify({
            "session_id": session_id,
            "first_objection": first_objection.description if first_objection else "No objections found"
        })



@msg_bp.route('/start_session_v2', methods=['POST'])
def start_session_v2():
    """Start a new session with selected client profile"""
    data = request.json
    client_profile_id = data['client_profile_id']
    
    # Initialize the agent
    client_agent = ClientAgent()

    # First turn - no user response yet
    client_message = client_agent(client_profile_id)
    print("client_message", client_message)
    # Second turn - pass user response
    # user_response = "Our solution automates the contact discovery process, reducing time spent by 80%"
    # client_message = client_agent.forward("nexumora-time-consuming-process", user_response)
        
    return jsonify({
        "client_agent_response": client_message
    })
