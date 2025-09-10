from flask import Blueprint, jsonify
import json
from config.tidb_config import (SessionLocal)
from util.db_service import ( get_client_objections, get_client_profile )
from util.knowledge_graph import ( DatabaseEntity )


client_profile_bp = Blueprint('client_profile_bp', __name__)


@client_profile_bp.route('/get-all', methods=['GET'])
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

@client_profile_bp.route('/get-by-id/<client_profile_id>', methods=['GET'])
def retrieve_client_profile(client_profile_id):
    """Get specific client profile by ID"""
    return jsonify(get_client_profile(client_profile_id))


@client_profile_bp.route('/objections/<client_profile_id>', methods=['GET'])
def retrieve_client_profile_objections(client_profile_id):
    """Get client profile objections by ID"""
    return jsonify(get_client_objections(client_profile_id)) 
