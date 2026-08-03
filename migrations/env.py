import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

# Import all models so their metadata is registered
import app.backend.models.clinic  # noqa: F401
import app.backend.models.user  # noqa: F401
import app.backend.models.professional  # noqa: F401
import app.backend.models.patient  # noqa: F401
import app.backend.models.appointment  # noqa: F401
import app.backend.models.medical_record  # noqa: F401
import app.backend.models.phone_list  # noqa: F401
import app.backend.models.check_in  # noqa: F401
import app.backend.models.emotion  # noqa: F401
import app.backend.models.check_in_emotion  # noqa: F401
import app.backend.models.family_member  # noqa: F401
import app.backend.models.body_signal  # noqa: F401
import app.backend.models.check_in_body_signal  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    from app.backend.core.config import settings

    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
