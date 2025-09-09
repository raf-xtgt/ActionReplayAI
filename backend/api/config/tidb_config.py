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
from dotenv import load_dotenv
from sqlalchemy.orm import relationship, Session, sessionmaker, declarative_base, joinedload
import os

load_dotenv()

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
SessionLocal = sessionmaker(bind=engine)
session_cache = {}
