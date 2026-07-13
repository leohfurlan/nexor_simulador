"""Camada de banco (SQLAlchemy async), espelhando app/database.py do Nexor Fiscal.

Mantém os mesmos nomes (`engine`, `async_session_maker`, `Base`,
`get_async_session`) para que, na integração, os models e routers do módulo
apontem para o `Base`/sessão do host trocando apenas o import.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.sql_echo, future=True)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
