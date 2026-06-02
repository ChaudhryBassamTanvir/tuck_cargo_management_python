from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context
import sys, os
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import Base
from app.models.cargo import Cargo, Truck, CargoEvent  # noqa

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ── Build URL safely using urllib to encode special chars ─────────────────────
from urllib.parse import quote_plus

DB_PASSWORD = os.getenv("DB_PASSWORD", "cargo_pass")
DB_USER     = "cargo_user"
DB_HOST     = "localhost"
DB_PORT     = "5432"
DB_NAME     = "cargo_db"

SYNC_URL = f"postgresql+psycopg2://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def run_migrations_offline():
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(SYNC_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()