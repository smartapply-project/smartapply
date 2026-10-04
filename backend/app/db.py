from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    raw = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/smartapply.db")
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw.startswith("mysql://"):
        return raw.replace("mysql://", "mysql+asyncmy://", 1)
    return raw


def _build_engine(url: str):
    connect_args = {"connect_timeout": 8} if url.startswith("mysql") else {"timeout": 8} if url.startswith("sqlite") else {"timeout": 8}
    return create_async_engine(url, echo=False, pool_pre_ping=True, connect_args=connect_args)


DATABASE_URL = _database_url()
if DATABASE_URL.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)

engine = _build_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def _create_tables() -> None:
    from .models import Application, DocumentRecord, AnalysisIssue, CheckRecord  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def init_db() -> None:
    global DATABASE_URL, engine, SessionLocal
    try:
        await asyncio.wait_for(_create_tables(), timeout=10)
    except Exception:
        if DATABASE_URL.startswith("sqlite"):
            raise
        DATABASE_URL = "sqlite+aiosqlite:///./data/smartapply.db"
        Path("data").mkdir(exist_ok=True)
        engine = _build_engine(DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        await _create_tables()
