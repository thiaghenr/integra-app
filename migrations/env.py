import asyncio
import getpass
from datetime import UTC, datetime
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

import app.backend.models.appointment  # noqa: F401
import app.backend.models.body_signal  # noqa: F401
import app.backend.models.check_in  # noqa: F401
import app.backend.models.check_in_body_signal  # noqa: F401
import app.backend.models.check_in_emotion  # noqa: F401

# Import all models so their metadata is registered
import app.backend.models.clinic  # noqa: F401
import app.backend.models.emotion  # noqa: F401
import app.backend.models.emotion_diary_entry  # noqa: F401
import app.backend.models.family_member  # noqa: F401
import app.backend.models.goal  # noqa: F401
import app.backend.models.material  # noqa: F401
import app.backend.models.medical_record  # noqa: F401
import app.backend.models.mission  # noqa: F401
import app.backend.models.patient  # noqa: F401
import app.backend.models.phone_list  # noqa: F401
import app.backend.models.professional  # noqa: F401
import app.backend.models.user  # noqa: F401
from app.backend.core.logging_config import database_logger, setup_logging

config = context.config
if config.config_file_name is not None:
    # fileConfig() defaults to disable_existing_loggers=True, which would
    # silently disable app.database (it's not in alembic.ini's [loggers]) if
    # this ran after setup_logging() — so setup_logging() must come after.
    fileConfig(config.config_file_name)

# So `alembic upgrade/downgrade` run standalone (as it is in entrypoint.sh,
# before the app process starts) still gets file+stdout handlers — the app's
# own setup_logging() call in app.main.api() never runs in that process.
setup_logging()

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


def _migration_direction() -> str:
    # Best-effort: only populated when run via the `alembic` CLI (upgrade.py
    # / downgrade.py set config.cmd_opts.cmd to (command_function, ...)),
    # which is how entrypoint.sh and every documented command in CLAUDE.md
    # invoke it. Falls back to "unknown" for programmatic context.configure()
    # calls that don't go through the CLI.
    cmd_opts = getattr(config, "cmd_opts", None)
    cmd = getattr(cmd_opts, "cmd", None)
    if cmd and cmd[0] is not None:
        return cmd[0].__name__
    return "unknown"


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    migration_context = context.get_context()
    revision_before = migration_context.get_current_revision()
    direction = _migration_direction()
    os_user = getpass.getuser()

    with context.begin_transaction():
        context.run_migrations()

    revision_after = migration_context.get_current_revision()

    # This is the one thing that would tell us whether a migration — as
    # opposed to a manual `docker compose down -v` or similar — caused a
    # future incident like the Aug 8 dev-DB wipe. LIMITATION: only covers
    # migrations run through this app's own alembic invocation; a DROP
    # DATABASE or docker volume removal run outside it leaves no trace here
    # — see CLAUDE.md's Observability section.
    database_logger.warning(
        "Alembic migration run",
        extra={
            "revision_before": revision_before,
            "revision_after": revision_after,
            "direction": direction,
            "timestamp": datetime.now(UTC).isoformat(),
            "os_user": os_user,
        },
    )


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
