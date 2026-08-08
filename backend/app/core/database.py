from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_db() -> None:
    """Inject company seed SQL on every server start."""
    with open("app/sql/seed_companies.sql", encoding="utf-8") as seed_file:
        sql = seed_file.read()
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
