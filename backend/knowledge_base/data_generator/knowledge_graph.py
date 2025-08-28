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
    entity_id = Column(String(36), nullable=False, unique=True)
    name = Column(String(512))
    type = Column(String(50))  # ClientProfile, Objection, Strategy, Technique, Outcome
    description = Column(Text)
    properties = Column(JSON)  # Additional properties as JSON

class DatabaseRelationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True)
    source_entity_id = Column(Integer, ForeignKey("entities.id"))
    target_entity_id = Column(Integer, ForeignKey("entities.id"))
    relationship_type = Column(String(50))
    properties = Column(JSON)  # Additional properties as JSON
    
    source_entity = relationship("DatabaseEntity", foreign_keys=[source_entity_id])
    target_entity = relationship("DatabaseEntity", foreign_keys=[target_entity_id])

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
    
    entity_map = {}  # Map of entity_id to DatabaseEntity id
    relationship_count = 0
    
    for record in sales_records:
        # Create client profile entity
        client_profile = record.client_profile
        client_entity = DatabaseEntity(
            entity_id=record.profile_id,
            name=client_profile.get('name', 'Unknown'),
            type="ClientProfile",
            description=client_profile.get('desc', ''),
            properties=client_profile
        )
        session.add(client_entity)
        session.flush()  # Get the ID
        entity_map[record.profile_id] = client_entity.id
        
        # Process objections
        for objection in record.objections:
            # Create objection entity
            objection_entity = DatabaseEntity(
                entity_id=objection['id'],
                name=f"Objection: {objection['desc'][:50]}...",
                type="Objection",
                description=objection['desc'],
                properties=objection
            )
            session.add(objection_entity)
            session.flush()
            entity_map[objection['id']] = objection_entity.id
            
            # Create relationship: ClientProfile -[HAS_OBJECTION]-> Objection
            rel = DatabaseRelationship(
                source_entity_id=entity_map[record.profile_id],
                target_entity_id=entity_map[objection['id']],
                relationship_type="HAS_OBJECTION",
                properties={"priority": objection['priority']}
            )
            session.add(rel)
            relationship_count += 1
            
            # Process strategies
            for strategy in objection['addressing_strategies']:
                # Create strategy entity
                strategy_entity = DatabaseEntity(
                    entity_id=strategy['id'],
                    name=f"Strategy: {strategy['desc'][:50]}...",
                    type="Strategy",
                    description=strategy['desc'],
                    properties=strategy
                )
                session.add(strategy_entity)
                session.flush()
                entity_map[strategy['id']] = strategy_entity.id
                
                # Create relationship: Objection -[ADDRESSED_BY]-> Strategy
                rel = DatabaseRelationship(
                    source_entity_id=entity_map[objection['id']],
                    target_entity_id=entity_map[strategy['id']],
                    relationship_type="ADDRESSED_BY"
                )
                session.add(rel)
                relationship_count += 1
                
                # Process techniques
                for technique in strategy['techniques']:
                    # Create technique entity
                    technique_entity = DatabaseEntity(
                        entity_id=technique['id'],
                        name=f"Technique: {technique['desc'][:50]}...",
                        type="Technique",
                        description=technique['desc'],
                        properties=technique
                    )
                    session.add(technique_entity)
                    session.flush()
                    entity_map[technique['id']] = technique_entity.id
                    
                    # Create relationship: Strategy -[USES]-> Technique
                    rel = DatabaseRelationship(
                        source_entity_id=entity_map[strategy['id']],
                        target_entity_id=entity_map[technique['id']],
                        relationship_type="USES"
                    )
                    session.add(rel)
                    relationship_count += 1
                    
                    # Process outcome
                    outcome = technique['outcome']
                    outcome_entity = DatabaseEntity(
                        entity_id=outcome['id'],
                        name=f"Outcome: {outcome['desc'][:50]}...",
                        type="Outcome",
                        description=outcome['desc'],
                        properties=outcome
                    )
                    session.add(outcome_entity)
                    session.flush()
                    entity_map[outcome['id']] = outcome_entity.id
                    
                    # Create relationship: Technique -[RESULTS_IN]-> Outcome
                    rel = DatabaseRelationship(
                        source_entity_id=entity_map[technique['id']],
                        target_entity_id=entity_map[outcome['id']],
                        relationship_type="RESULTS_IN"
                    )
                    session.add(rel)
                    relationship_count += 1
    
    try:
        session.commit()
        print(f"Built knowledge graph with {len(entity_map)} entities and {relationship_count} relationships")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    build_knowledge_graph()

#       anon_63.md
#   anon_34.md
#   anon_32.md
#   anon_25.md
#   anon_23.md
#   anon_16.md