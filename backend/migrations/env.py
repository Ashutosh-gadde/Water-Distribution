from alembic import context
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.db import Base
import app.models  # noqa: F401  (register tables)

target_metadata = Base.metadata


def run():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


run()
