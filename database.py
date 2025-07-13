from sqlalchemy import create_engine, Column, Integer, String, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Path to SQLite database
DATABASE_URL = "sqlite:///./historical_docs.db"

# Set up SQLAlchemy
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Define document table
class HistoricalDocument(Base):
    __tablename__ = 'historical_documents'

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String)
    year = Column(Integer)
    text = Column(Text)
    effective_date = Column(String)
    title = Column(String)

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# FTS5 virtual table setup and population
def populate_fts(session):
    session.execute(text("DROP TABLE IF EXISTS historical_documents_fts"))

    session.execute(text("""
        CREATE VIRTUAL TABLE historical_documents_fts USING fts5(
            doc_type, year UNINDEXED, text, effective_date,
            content='historical_documents', content_rowid='id'
        )
    """))

    session.execute(text("""
        INSERT INTO historical_documents_fts(rowid, doc_type, year, text, effective_date)
        SELECT id, doc_type, year, text, effective_date FROM historical_documents
    """))

    session.commit()
