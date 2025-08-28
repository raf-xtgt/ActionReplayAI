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
    inspect
)
from datetime import datetime
from sqlalchemy.orm import relationship, Session, sessionmaker, declarative_base, joinedload
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

def get_db_url():
    return URL(
        drivername="mysql+pymysql",
        username=os.getenv("TIDB_USER"),
        password=os.getenv("TIDB_PASSWORD"),
        host=os.getenv('TIDB_HOST').strip(), # Added .strip() here
        port=int(os.getenv("TIDB_PORT")),
        database=os.getenv("TIDB_DB_NAME"),
        query={"ssl_verify_cert": True, "ssl_verify_identity": True},
    )

# Configure DSPy with Ollama
lm_conf = dspy.LM("ollama_chat/llama3.1:latest", api_base="http://localhost:11434", api_key="")
dspy.settings.configure(lm=lm_conf)

# Set up database connection
engine = create_engine(get_db_url(), pool_recycle=300)
Base = declarative_base()
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)  # Create tables if they don't exist


# Define your Pydantic models for structured extraction
class TechniqueOutcome(BaseModel):
    techn_ot_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    desc: str

class Technique(BaseModel):
    tehcn_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    desc: str
    outcome: TechniqueOutcome

class AddressingStrategy(BaseModel):
    strat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    desc: str
    techniques: List[Technique]

class Objection(BaseModel):
    obj_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    desc: str
    priority: int
    addressing_strategies: List[AddressingStrategy]

class ClientProfile(BaseModel):
    name: str
    industry: str
    company_size: str
    desc: str

class ExtractionResult(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_profile: ClientProfile
    objections: List[Objection]
    source_files: List[str]
    llm_metadata: Dict[str, str]


class SalesKnowledge(Base):
    __tablename__ = 'sales_knowledge'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(String(36), nullable=False)
    client_profile = Column(JSON)
    objections = Column(JSON)
    source_files = Column(JSON)
    llm_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)



class ProfileExtractor(dspy.Signature):
    """Analyze the following text from a sales case study. 
    Identify the client Profile, their key Objections, and for each objection, extract the Strategy used to address it, 
    the Techniques used in that strategy, and the final Outcome."""
    sales_content: str = dspy.InputField(desc="Sales case study content")
    extraction_result: ExtractionResult = dspy.OutputField(desc="Structured extraction result")

def process_markdown_files(markdown_dir: str):
    """Process all markdown files in a directory and store results in TiDB"""
    # Set up database connection
    # engine = create_engine(get_db_url(), pool_recycle=300)
    # Base = declarative_base()
    # Base.metadata.create_all(engine)  # Create tables if they don't exist
    Session = sessionmaker(bind=engine)
    session = Session()
    
    processed_count = 0
    
    for filename in os.listdir(markdown_dir):
        if not filename.endswith('.md'):
            continue
            
        file_path = os.path.join(markdown_dir, filename)
        print(f"Begin processing {filename}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Begin LLM extraction")
            extractor = dspy.Predict(ProfileExtractor)

            result = extractor(sales_content=content)
            extraction_result = result.extraction_result
            print("LLM extraction complete")

            sales_knowledge = SalesKnowledge(
                profile_id=extraction_result.profile_id,
                client_profile=extraction_result.client_profile.model_dump(),
                objections=[obj.model_dump() for obj in extraction_result.objections],
                source_files=extraction_result.source_files,
                llm_metadata=extraction_result.llm_metadata
            )
            # print("sales_knowledge", sales_knowledge)
            session.add(sales_knowledge)
            processed_count += 1
            print(f"Processing {filename} done\n")
            session.commit()
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            session.rollback()
    
    try:
        print(f"Successfully processed {processed_count} files")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"Database error: {str(e)}")
    finally:
        session.close()
    
    return processed_count

if __name__ == "__main__":
    markdown_dir = "../markdowns/sales_case_studies"
    count = process_markdown_files(markdown_dir)
    print(f"Processed {count} files")
