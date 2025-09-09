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

from util.knowledge_graph import ( DatabaseEntity, DatabaseRelationship, get_query_embedding )


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
