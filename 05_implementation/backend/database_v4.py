from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_v4 import Base

# New Sage v4 database
DATABASE_URL = "sqlite:///./sage_v4.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables in the new database."""
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
