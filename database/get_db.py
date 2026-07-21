from .db_shared import DatabaseInterface, DB_NO_CONFIG_ERROR

INSTANCE: DatabaseInterface | None = None

async def get_db() -> DatabaseInterface | None:
    global INSTANCE
    if INSTANCE: return INSTANCE

    try:
        from . import db_sqlite3
        INSTANCE = db_sqlite3.Sqlite3DB()
        await INSTANCE.startup()
        return INSTANCE
    except DB_NO_CONFIG_ERROR: pass
