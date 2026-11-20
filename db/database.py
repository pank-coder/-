from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import config
from db.models import Base

engine = None
Session = None


async def init_db():
    global engine, Session
    engine = create_async_engine(config.db_url())
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)


def session():
    return Session()
