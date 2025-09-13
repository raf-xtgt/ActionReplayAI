from flask import Blueprint, jsonify, request, Response
import json
from config.tidb_config import (
    engine, Base, SessionLocal
)
from model.data_model import (
    ClientProfileResponse,
    ConversationRound,
    CoachAnalysis
)
from util.session_service import ( update_session_cache, create_new_session, get_session_by_id, update_session_by_id )
from util.db_service import (get_client_profile, get_client_objections, get_client_with_detailed_objections)
from model.context_model import ( 
    ClientAgentContextModel, SessionModel, CoachAgentBehavioralCueAnalysis, 
    CoachAgentRiskAnalysis, CoachAgentProblemAnalysis, CoachAgentSolutionAnalysis
)
from agent import (ClientAgent, CoachAgent)
from util.knowledge_graph import ( DatabaseEntity, DatabaseRelationship, get_query_embedding )
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

session_bp = Blueprint('session_bp', __name__)
# session_cache = {}

@session_bp.route('/start_session', methods=['POST'])
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



@session_bp.route('/session-init', methods=['POST'])
def start_session_v2():
    """Start a new session with selected client profile"""
    data = request.json
    client_profile_id = data['client_profile_id']
    client_agent_context = construct_client_agent_context(client_profile_id, [])

    # Initialize the agent
    client_agent = ClientAgent()

    # First turn - no user response yet
    client_agent_context = client_agent.forward(client_agent_context)
   
    # Create session cache
    session_id = str(uuid.uuid4())
    session = SessionModel(
        session_id=session_id, 
        client_agent_context=client_agent_context,
        round_count=0
    )
    create_new_session(session)
    print("Session created successfully")
    lates_client_response_idx = len(client_agent_context.conversation_history) - 1
    return jsonify({
        "session_id": session_id,
        "client_agent_response": client_agent_context.conversation_history[lates_client_response_idx]
    })

def construct_client_agent_context(client_profile_id, conversation_history):
    client_profile = get_client_profile(client_profile_id)
    print("Client Profile", json.dumps(client_profile, indent=2, default=str) )
    objections = get_client_with_detailed_objections(client_profile_id)
    print("Client Objections", json.dumps(objections, indent=2, default=str) )

        
    # Get the next objection to raise (cycle through them)
    current_objection_idx = len(conversation_history) // 2  # Each round has client + user messages
    if current_objection_idx >= len(objections["client_objections"]):
        current_objection_idx = len(objections["client_objections"]) - 1  # Stay on last objection
        
    current_objection = objections["client_objections"][current_objection_idx] if objections["client_objections"] else "No specific objection"
        
    context_model = ClientAgentContextModel(
        profile_desc=client_profile["description"], 
        current_objection=current_objection,
        all_objections=objections["client_objections"],
        related_objections=objections["related_objections"],
        conversation_history=conversation_history
    )
    return context_model

@session_bp.route('/conversation', methods=['POST'])
def handle_conversation():
    """Handle conversation round"""
    data = request.json
    session_id = data['session_id']
    user_response = data['user_response']
    
    if session_id not in session_cache:
        return jsonify({"error": "Session not found"}), 404
    
    session_data = session_cache[session_id]
    
    # Add to conversation history
    session_data["conversation"].append({
        "role": "user",
        "content": user_response
    })
    
    # Get coach analysis
    analysis = get_coach_analysis(session_data)
    
    # Get next objection or continue conversation
    next_objection = get_next_objection(session_data)
    
    # Update session cache every 3 rounds
    session_data["round_count"] += 1
    if session_data["round_count"] % 3 == 0:
        update_session_cache(session_data)
    
    return jsonify({
        "next_objection": next_objection,
        "coach_analysis": analysis.dict()
    })

@session_bp.route('/user-msg', methods=['POST'])
def handle_msg():
    """Handle conversation round"""
    data = request.json
    session_id = data['session_id']
    user_response = data['user_response']
    
    if not session_id:
        return jsonify({"error": "Session not found"}), 404
    
    session_data = get_session_by_id(session_id)
    print("retrieved session data:::", json.dumps(session_data, indent=2, default=str) )

    client_agent_context = session_data.client_agent_context
    client_agent_context.conversation_history.append({"role": "salesman", "content": user_response})
    client_agent = ClientAgent()
    # Trigger client agent
    client_agent_context = client_agent.forward(client_agent_context)
    print("client_agent_context after:::", json.dumps(client_agent_context, indent=2, default=str) )
    session_data.client_agent_context = client_agent_context
    session_data.round_count += 1
    update_session_by_id(session_id, session_data)
    # round 
    lates_client_response_idx = len(client_agent_context.conversation_history) - 1

    # Trigger coach agent
    coach_agent = CoachAgent()
    user_response_classification = coach_agent.classify_response(client_agent_context)
    solution_analysis = CoachAgentSolutionAnalysis(analysis=[])

    if user_response_classification == 'substantive':
        print("Classification", user_response_classification)
        cues = coach_agent.extract_behavioral_queue(client_agent_context) 
        behavioral_data = json.loads(cues)
        coach_agent_behavioral_analysis = CoachAgentBehavioralCueAnalysis(**behavioral_data)
        print("cues", coach_agent_behavioral_analysis)
        risks = coach_agent.extract_risks(client_agent_context) 
        risks_data = json.loads(risks)
        coach_agent_risk_analysis = CoachAgentRiskAnalysis(**risks_data)
        print("risks", coach_agent_risk_analysis)
        coach_agent_problem_analysis = CoachAgentProblemAnalysis(
            behavioral=coach_agent_behavioral_analysis,
            risk=coach_agent_risk_analysis)
        coach_solution = coach_agent.get_solution_techniques(coach_agent_problem_analysis, solution_analysis)
        print("coach_solution", coach_solution)

    return jsonify({
        "session_id": session_id,
        "client_agent_response": client_agent_context.conversation_history[lates_client_response_idx],
        "client_response_classification": user_response_classification,
        "behavioral":cues,
        "risks":risks
    })