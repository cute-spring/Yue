import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.settings import AppSettings

settings = AppSettings()

# Default SQLite database path
DATA_DIR = os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))
DB_FILE = os.path.join(DATA_DIR, "yue.db")

# Ensure DATA_DIR exists
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_DATABASE_URL = f"sqlite:///{DB_FILE}"
DATABASE_URL = settings.database_url or DEFAULT_DATABASE_URL

# Check if SQLite is being used
is_sqlite = DATABASE_URL.startswith("sqlite")

# SQLite needs special arguments to support concurrency
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # echo=True  # Can enable for debugging SQL
)

# Use WAL mode for SQLite to improve concurrency
if is_sqlite:
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
