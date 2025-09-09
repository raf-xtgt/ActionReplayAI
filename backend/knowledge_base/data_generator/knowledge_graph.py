import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import ollama
import dspy
import os
import json
import uuid
from pymysql import Connection
from pymysql.cursors import DictCursor
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
from datetime import datetime
from sqlalchemy.orm import relationship, Session, sessionmaker, declarative_base, joinedload
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from pyvis.network import Network
import webbrowser
load_dotenv()

# Use the same get_db_url function
def get_db_url():
    return URL(
        drivername="mysql+pymysql",
        username=os.getenv("TIDB_USER"),
        password=os.getenv("TIDB_PASSWORD"),
        host=os.getenv('TIDB_HOST').strip(),
        port=int(os.getenv("TIDB_PORT")),
        database=os.getenv("TIDB_DB_NAME"),
        query={"ssl_verify_cert": True, "ssl_verify_identity": True},
    )

# Set up database connection
engine = create_engine(get_db_url(), pool_recycle=300)
Base = declarative_base()
Base.metadata.create_all(engine)

class DatabaseEntity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(String(4096), nullable=False)
    name = Column(String(4096))
    type = Column(String(4096))  # ClientProfile, Objection, Strategy, Technique, Outcome
    description = Column(Text)
    description_vec = Column(VectorType())
    properties = Column(JSON)  # Additional properties as JSON

class DatabaseRelationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id"))
    target_entity_id = Column(Integer, ForeignKey("entities.id"))
    relationship_type = Column(String(4096))
    properties = Column(JSON)  # Additional properties as JSON
    
    source_entity = relationship("DatabaseEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("DatabaseEntity", foreign_keys=[target_entity_id])


class SalesKnowledge(Base):
    __tablename__ = 'sales_knowledge'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String(4096), nullable=False)
    client_profile = Column(JSON)
    objections = Column(JSON)
    source_files = Column(JSON)
    llm_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)


def get_query_embedding(query: str):
    """
    Generate embedding using Ollama's nomic-embed-text model.
    """
    response = ollama.embeddings(model='nomic-embed-text', prompt=query)
    return response['embedding']

def build_knowledge_graph():
    """Build knowledge graph from data in sales_knowledge table"""
    # Set up database connections
    engine = create_engine(get_db_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create knowledge graph tables if they don't exist
    Base.metadata.create_all(engine)
    
    # Fetch all sales knowledge records
    sales_records = session.query(SalesKnowledge).all()
    total_sales_count = len(sales_records)
    print("total sales records", total_sales_count)

    entity_map = {}  # Map of entity_id to DatabaseEntity id
    relationship_count = 0
    processed_count = 0

    for record in sales_records:
        # Create client profile entity
        client_profile = record.client_profile
        client_entity = DatabaseEntity(
            entity_id=record.profile_id,
            name=client_profile.get('name', 'Unknown'),
            type="ClientProfile",
            description=client_profile.get('desc', ''),
            description_vec = get_query_embedding(client_profile.get('desc', '')),
            properties=client_profile
        )
        session.add(client_entity)
        session.flush()  # Get the ID
        entity_map[record.profile_id] = client_entity.id
        
        # Process objections
        for objection in record.objections:
            # Create objection entity
            objection_entity = DatabaseEntity(
                entity_id=objection['obj_id'],
                name=f"Objection: {objection['desc'][:50]}...",
                type="Objection",
                description=objection['desc'],
                description_vec = get_query_embedding(objection['desc']),
                properties=objection
            )
            session.add(objection_entity)
            session.flush()
            entity_map[objection['obj_id']] = objection_entity.id
            
            # Create relationship: ClientProfile -[HAS_OBJECTION]-> Objection
            rel = DatabaseRelationship(
                source_entity_id=entity_map[record.profile_id],
                target_entity_id=entity_map[objection['obj_id']],
                relationship_type="HAS_OBJECTION",
                properties={"priority": objection['priority']}
            )
            session.add(rel)
            relationship_count += 1
            
            # Process strategies
            for strategy in objection['addressing_strategies']:
                # Create strategy entity
                strategy_entity = DatabaseEntity(
                    entity_id=strategy['strat_id'],
                    name=f"Strategy: {strategy['desc'][:50]}...",
                    type="Strategy",
                    description=strategy['desc'],
                    description_vec = get_query_embedding(strategy['desc']),
                    properties=strategy
                )
                session.add(strategy_entity)
                session.flush()
                entity_map[strategy['strat_id']] = strategy_entity.id
                
                # Create relationship: Objection -[ADDRESSED_BY]-> Strategy
                rel = DatabaseRelationship(
                    source_entity_id=entity_map[objection['obj_id']],
                    target_entity_id=entity_map[strategy['strat_id']],
                    relationship_type="ADDRESSED_BY"
                )
                session.add(rel)
                relationship_count += 1
                
                # Process techniques
                for technique in strategy['techniques']:
                    # Create technique entity
                    technique_entity = DatabaseEntity(
                        entity_id=technique['tehcn_id'],
                        name=f"Technique: {technique['desc'][:50]}...",
                        type="Technique",
                        description=technique['desc'],
                        description_vec = get_query_embedding(technique['desc']),
                        properties=technique
                    )
                    session.add(technique_entity)
                    session.flush()
                    entity_map[technique['tehcn_id']] = technique_entity.id
                    
                    # Create relationship: Strategy -[USES]-> Technique
                    rel = DatabaseRelationship(
                        source_entity_id=entity_map[strategy['strat_id']],
                        target_entity_id=entity_map[technique['tehcn_id']],
                        relationship_type="USES"
                    )
                    session.add(rel)
                    relationship_count += 1
                    
                    # Process outcome
                    outcome = technique['outcome']
                    outcome_entity = DatabaseEntity(
                        entity_id=outcome['techn_ot_id'],
                        name=f"Outcome: {outcome['desc'][:50]}...",
                        type="Outcome",
                        description=outcome['desc'],
                        description_vec = get_query_embedding(outcome['desc']),
                        properties=outcome
                    )
                    session.add(outcome_entity)
                    session.flush()
                    entity_map[outcome['techn_ot_id']] = outcome_entity.id
                    
                    # Create relationship: Technique -[RESULTS_IN]-> Outcome
                    rel = DatabaseRelationship(
                        source_entity_id=entity_map[technique['tehcn_id']],
                        target_entity_id=entity_map[outcome['techn_ot_id']],
                        relationship_type="RESULTS_IN"
                    )
                    session.add(rel)
                    relationship_count += 1
    
        processed_count += 1
        print(f"Processed records {processed_count}/{total_sales_count}\n")
    try:
        session.commit()
        print(f"Built knowledge graph with {len(entity_map)} entities and {relationship_count} relationships")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error: {str(e)}")
    finally:
        session.close()

def visualize_knowledge_graph():
    """Visualize the knowledge graph using PyVis"""
    engine = create_engine(get_db_url())
    Session = sessionmaker(bind=engine)
    session = Session()

    # Fetch all entities and relationships
    entities = session.query(DatabaseEntity).all()
    relationships = session.query(DatabaseRelationship).all()

    # Create network
    net = Network(notebook=False, height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.force_atlas_2based()

    # Add entities as nodes
    for entity in entities:
        net.add_node(
            entity.id,
            label=entity.name,
            title=f"{entity.type}: {entity.description}",
            color=get_color_for_type(entity.type)
        )

    # Add relationships as edges
    for rel in relationships:
        net.add_edge(
            rel.source_entity_id,
            rel.target_entity_id,
            label=rel.relationship_type,
            title=rel.relationship_type
        )

    # Generate and open HTML
    filename = "knowledge_graph.html"
    net.save_graph(filename)
    webbrowser.open(f"file://{os.path.abspath(filename)}")
    session.close()

def get_color_for_type(entity_type):
    """Assign colors based on entity type"""
    colors = {
        "ClientProfile": "#FF6B6B",
        "Objection": "#4ECDC4",
        "Strategy": "#45B7D1",
        "Technique": "#96CEB4",
        "Outcome": "#FFEAA7"
    }
    return colors.get(entity_type, "#999999")

if __name__ == "__main__":
    build_knowledge_graph()
    # visualize_knowledge_graph()
