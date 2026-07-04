from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.settings import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_async_session():
    async with async_session_maker() as session:
        yield session


async def commit_tolerating_race(session: AsyncSession) -> bool:
    """Commit pending inserts, tolerating a concurrent duplicate.

    Several exe-facing GET endpoints auto-create a row (UserConfig,
    AccountSettings, ...) keyed by a unique column on first read. Two
    near-simultaneous first requests (e.g. the bot client polling two
    endpoints at startup) can both see "no row" and both try to insert,
    so the loser's commit raises IntegrityError. Returns True on success;
    on a race, rolls back and returns False so the caller re-selects the
    row the winner inserted instead of surfacing a 500.
    """
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False
