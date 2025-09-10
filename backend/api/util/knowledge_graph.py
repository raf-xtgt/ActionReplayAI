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

def get_query_embedding(query: str):
    """
    Generate embedding using Ollama's nomic-embed-text model.
    """
    response = ollama.embeddings(model='nomic-embed-text', prompt=query)
    return response['embedding']
