"""Client Script models, forms, and database operations.

Client Scripts are user-authored JavaScript snippets that run in the *owner's own
browser* (client-side only). They are managed per-user, like a built-in userscript
manager. The server only stores and serves them — it never executes them.

Mirrors the structure of models/functions.py, but scoped to a single owner.
"""

from __future__ import annotations

import logging
import time
import uuid

# local imports
from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Index, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class ClientScript(Base):  # database table mapping
    __tablename__ = 'client_script'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)  # owner user id
    name = Column(Text, nullable=False)  # human-readable label
    content = Column(Text, nullable=True)  # JavaScript source executed in the owner's browser
    meta = Column(JSONField, nullable=True)  # description / manifest
    is_active = Column(Boolean, default=False)  # whether it runs for the owner
    is_global = Column(Boolean, default=False)  # reserved: admin-pushed to all users (unused in v1)
    updated_at = Column(BigInteger)  # epoch seconds
    created_at = Column(BigInteger)  # epoch seconds

    __table_args__ = (Index('client_script_user_id_idx', 'user_id'),)


class ClientScriptMeta(BaseModel):
    description: str | None = None
    manifest: dict | None = {}
    model_config = ConfigDict(extra='allow')


class ClientScriptModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    meta: ClientScriptMeta
    is_active: bool = False
    is_global: bool = False
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ClientScriptResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ClientScriptMeta
    is_active: bool
    is_global: bool
    updated_at: int
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientScriptForm(BaseModel):
    name: str
    content: str
    meta: ClientScriptMeta = ClientScriptMeta()


class ClientScriptsTable:
    async def insert_new_client_script(
        self,
        user_id: str,
        form_data: ClientScriptForm,
        db: AsyncSession | None = None,
    ) -> ClientScriptModel | None:
        script = ClientScriptModel(
            **{
                **form_data.model_dump(),
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'is_active': True,  # newly created scripts run by default; owner can toggle off
                'is_global': False,
                'updated_at': int(time.time()),
                'created_at': int(time.time()),
            }
        )

        try:
            async with get_async_db_context(db) as db:
                result = ClientScript(**script.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                return ClientScriptModel.model_validate(result) if result else None
        except Exception as e:
            log.exception(f'Error creating a new client script: {e}')
            return None

    async def get_client_scripts_by_user_id(
        self, user_id: str, active_only: bool = False, db: AsyncSession | None = None
    ) -> list[ClientScriptModel]:
        async with get_async_db_context(db) as db:
            stmt = select(ClientScript).filter_by(user_id=user_id)
            if active_only:
                stmt = stmt.filter_by(is_active=True)
            stmt = stmt.order_by(ClientScript.updated_at.desc())
            result = await db.execute(stmt)
            return [ClientScriptModel.model_validate(s) for s in result.scalars().all()]

    async def get_client_script_by_id(self, id: str, db: AsyncSession | None = None) -> ClientScriptModel | None:
        try:
            async with get_async_db_context(db) as db:
                script = await db.get(ClientScript, id)
                return ClientScriptModel.model_validate(script) if script else None
        except Exception:
            return None

    async def update_client_script_by_id(
        self, id: str, updated: dict, db: AsyncSession | None = None
    ) -> ClientScriptModel | None:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(
                    update(ClientScript)
                    .filter_by(id=id)
                    .values(
                        **updated,
                        updated_at=int(time.time()),
                    )
                )
                await db.commit()
                script = await db.get(ClientScript, id)
                return ClientScriptModel.model_validate(script) if script else None
            except Exception as e:
                log.exception(f'Error updating client script {id}: {e}')
                return None

    async def delete_client_script_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as db:
            try:
                await db.execute(delete(ClientScript).filter_by(id=id))
                await db.commit()
                return True
            except Exception:
                return False


ClientScripts = ClientScriptsTable()  # singleton client-scripts engine
