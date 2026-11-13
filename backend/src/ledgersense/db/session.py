from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from ledgersense.core.config import settings

# Parameterized SQLite engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    """Create all SQLModel tables and install the audit_events append-only SQLite trigger."""
    SQLModel.metadata.create_all(engine)

    # SQLite trigger enforcing append-only invariant on audit_events
    if engine.url.drivername.startswith("sqlite"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TRIGGER IF NOT EXISTS trigger_abort_audit_events_update
                    BEFORE UPDATE ON audit_events
                    BEGIN
                        SELECT RAISE(ABORT, 'audit_events is append-only: UPDATE forbidden');
                    END;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TRIGGER IF NOT EXISTS trigger_abort_audit_events_delete
                    BEFORE DELETE ON audit_events
                    BEGIN
                        SELECT RAISE(ABORT, 'audit_events is append-only: DELETE forbidden');
                    END;
                    """
                )
            )


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    with Session(engine) as session:
        yield session
