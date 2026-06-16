"""Client Script (a.k.a. "Scripts") models, forms, and database operations.

Scripts are user-authored JavaScript that runs in the owner's own browser
(client-side only). They are managed in the Workspace like Tools — same
access-grant sharing model (resource_type 'client_script'), same meta/manifest
shape — but the server only stores and serves them; it never executes them.

Mirrors models/tools.py for access control, plus an `is_active`/`is_global`
runtime tier specific to client scripts (which scripts actually run, and whether
an admin pushes one to every user).
"""

from __future__ import annotations

import logging
import time

from open_webui.internal.db import Base, JSONField, get_async_db_context
from open_webui.models.access_grants import AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import UserResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, Index, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class ClientScript(Base):  # database table mapping
    __tablename__ = 'client_script'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)  # owner user id
    name = Column(Text, nullable=False)  # human-readable label
    content = Column(Text, nullable=True)  # JavaScript executed in the owner's browser
    meta = Column(JSONField, nullable=True)  # { description, manifest }
    is_active = Column(Boolean, default=False)  # whether it runs for the owner
    is_global = Column(Boolean, default=False)  # admin-pushed: runs for every user
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
    access_grants: list[AccessGrantModel] = Field(default_factory=list)
    updated_at: int
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms / responses
####################


class ClientScriptResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ClientScriptMeta
    is_active: bool
    is_global: bool
    access_grants: list[AccessGrantModel] = Field(default_factory=list)
    updated_at: int
    created_at: int

    model_config = ConfigDict(from_attributes=True)


class ClientScriptUserResponse(ClientScriptResponse):
    user: UserResponse | None = None
    model_config = ConfigDict(extra='allow')


class ClientScriptAccessResponse(ClientScriptUserResponse):
    write_access: bool | None = False


class ClientScriptForm(BaseModel):
    id: str
    name: str
    content: str
    meta: ClientScriptMeta = ClientScriptMeta()
    access_grants: list[dict | None] | None = None


RESOURCE_TYPE = 'client_script'


class ClientScriptsTable:
    async def _get_access_grants(
        self, script_id: str, db: AsyncSession | None = None
    ) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource(RESOURCE_TYPE, script_id, db=db)

    async def _to_model(
        self,
        script: ClientScript,
        access_grants: list[AccessGrantModel] | None = None,
        db: AsyncSession | None = None,
    ) -> ClientScriptModel:
        data = ClientScriptModel.model_validate(script).model_dump(exclude={'access_grants'})
        data['access_grants'] = (
            access_grants
            if access_grants is not None
            else await self._get_access_grants(data['id'], db=db)
        )
        return ClientScriptModel.model_validate(data)

    async def insert_new_client_script(
        self,
        user_id: str,
        form_data: ClientScriptForm,
        db: AsyncSession | None = None,
    ) -> ClientScriptModel | None:
        try:
            async with get_async_db_context(db) as db:
                result = ClientScript(
                    **{
                        **form_data.model_dump(exclude={'access_grants'}),
                        'user_id': user_id,
                        'is_active': True,  # new scripts run by default; owner can toggle off
                        'is_global': False,
                        'updated_at': int(time.time()),
                        'created_at': int(time.time()),
                    }
                )
                db.add(result)
                await db.commit()
                await db.refresh(result)
                await AccessGrants.set_access_grants(
                    RESOURCE_TYPE, result.id, form_data.access_grants, db=db
                )
                return await self._to_model(result, db=db)
        except Exception as e:
            log.exception(f'Error creating a new client script: {e}')
            return None

    async def get_client_scripts(self, db: AsyncSession | None = None) -> list[ClientScriptModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(ClientScript).order_by(ClientScript.updated_at.desc()))
            scripts = result.scalars().all()
            return [await self._to_model(s, db=db) for s in scripts]

    async def get_client_scripts_by_user_id(
        self, user_id: str, permission: str = 'write', db: AsyncSession | None = None
    ) -> list[ClientScriptModel]:
        """Scripts the user owns or has the given access permission to."""
        scripts = await self.get_client_scripts(db=db)
        user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
        user_group_ids = {group.id for group in user_groups}

        result = []
        for script in scripts:
            if script.user_id == user_id:
                result.append(script)
            elif await AccessGrants.has_access(
                user_id=user_id,
                resource_type=RESOURCE_TYPE,
                resource_id=script.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            ):
                result.append(script)
        return result

    async def get_active_client_scripts_by_user_id(
        self, user_id: str, db: AsyncSession | None = None
    ) -> list[ClientScriptModel]:
        """The owner's enabled scripts (the loader runs these)."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClientScript)
                .filter_by(user_id=user_id, is_active=True)
                .order_by(ClientScript.updated_at.desc())
            )
            return [await self._to_model(s, db=db) for s in result.scalars().all()]

    async def get_active_global_client_scripts(
        self, db: AsyncSession | None = None
    ) -> list[ClientScriptModel]:
        """Enabled global scripts — the loader runs these for every user."""
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClientScript)
                .filter_by(is_active=True, is_global=True)
                .order_by(ClientScript.updated_at.desc())
            )
            return [await self._to_model(s, db=db) for s in result.scalars().all()]

    async def get_global_client_scripts(
        self, db: AsyncSession | None = None
    ) -> list[ClientScriptModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(ClientScript).filter_by(is_global=True).order_by(ClientScript.updated_at.desc())
            )
            return [await self._to_model(s, db=db) for s in result.scalars().all()]

    async def get_client_script_by_id(
        self, id: str, db: AsyncSession | None = None
    ) -> ClientScriptModel | None:
        try:
            async with get_async_db_context(db) as db:
                script = await db.get(ClientScript, id)
                return await self._to_model(script, db=db) if script else None
        except Exception:
            return None

    async def update_client_script_by_id(
        self, id: str, updated: dict, db: AsyncSession | None = None
    ) -> ClientScriptModel | None:
        try:
            async with get_async_db_context(db) as db:
                access_grants = updated.pop('access_grants', None)
                await db.execute(
                    update(ClientScript).filter_by(id=id).values(**updated, updated_at=int(time.time()))
                )
                await db.commit()
                if access_grants is not None:
                    await AccessGrants.set_access_grants(RESOURCE_TYPE, id, access_grants, db=db)
                script = await db.get(ClientScript, id)
                await db.refresh(script)
                return await self._to_model(script, db=db)
        except Exception as e:
            log.exception(f'Error updating client script {id}: {e}')
            return None

    async def delete_client_script_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await AccessGrants.revoke_all_access(RESOURCE_TYPE, id, db=db)
                await db.execute(delete(ClientScript).filter_by(id=id))
                await db.commit()
                return True
        except Exception:
            return False


ClientScripts = ClientScriptsTable()  # singleton
