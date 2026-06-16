"""Scripts (client_script): user-managed JavaScript that runs in the user's browser.

Same access-control/sharing model as Tools (access grants, resource_type
'client_script'), plus an is_active/is_global runtime tier. The server stores and
serves scripts but never executes them.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.client_scripts import (
    ClientScriptAccessResponse,
    ClientScriptForm,
    ClientScriptModel,
    ClientScripts,
)
from open_webui.models.groups import Groups
from open_webui.models.users import UserResponse, Users
from open_webui.utils.auth import get_admin_user, get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

RESOURCE_TYPE = 'client_script'


def _has_write_from_grants(script, user, user_group_ids: set[str]) -> bool:
    return (
        user.role == 'admin'
        or script.user_id == user.id
        or any(
            g.permission == 'write'
            and (
                (g.principal_type == 'user' and (g.principal_id == user.id or g.principal_id == '*'))
                or (g.principal_type == 'group' and g.principal_id in user_group_ids)
            )
            for g in script.access_grants
        )
    )


async def _require_write(id: str, user, db: AsyncSession) -> ClientScriptModel:
    script = await ClientScripts.get_client_script_by_id(id, db=db)
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Script not found')
    if (
        script.user_id != user.id
        and user.role != 'admin'
        and not await AccessGrants.has_access(
            user_id=user.id, resource_type=RESOURCE_TYPE, resource_id=id, permission='write', db=db
        )
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Access prohibited')
    return script


############################
# List / runtime fetch
############################


@router.get('/list', response_model=list[ClientScriptAccessResponse])
async def get_client_script_list(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """Scripts the user can see (own + shared), with user info and write_access — the Workspace list."""
    if user.role == 'admin':
        scripts = await ClientScripts.get_client_scripts(db=db)
    else:
        scripts = await ClientScripts.get_client_scripts_by_user_id(user.id, 'read', db=db)

    user_group_ids = {g.id for g in await Groups.get_groups_by_member_id(user.id, db=db)}
    user_ids = list({s.user_id for s in scripts})
    users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
    users_dict = {u.id: u for u in users}

    result = []
    for s in scripts:
        u = users_dict.get(s.user_id)
        result.append(
            ClientScriptAccessResponse(
                **s.model_dump(),
                user=(
                    UserResponse(id=u.id, name=u.name, role=u.role, email=u.email) if u else None
                ),
                write_access=_has_write_from_grants(s, user, user_group_ids),
            )
        )
    return result


@router.get('/active', response_model=list[ClientScriptModel])
async def get_active_client_scripts(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """The current user's enabled scripts (fetched by the loader)."""
    return await ClientScripts.get_active_client_scripts_by_user_id(user.id, db=db)


@router.get('/global/active', response_model=list[ClientScriptModel])
async def get_active_global_client_scripts(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """Enabled global scripts — the loader runs these for every user."""
    return await ClientScripts.get_active_global_client_scripts(db=db)


@router.get('/global', response_model=list[ClientScriptModel])
async def get_global_client_scripts(
    user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    return await ClientScripts.get_global_client_scripts(db=db)


@router.get('/export', response_model=list[ClientScriptModel])
async def export_client_scripts(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """Export the user's own scripts (admins export all)."""
    if user.role == 'admin':
        return await ClientScripts.get_client_scripts(db=db)
    return await ClientScripts.get_client_scripts_by_user_id(user.id, 'read', db=db)


############################
# Create
############################


@router.post('/create', response_model=ClientScriptModel | None)
async def create_new_client_script(
    form_data: ClientScriptForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not form_data.id.isidentifier():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only alphanumeric characters and underscores are allowed in the id',
        )
    form_data.id = form_data.id.lower()

    if await ClientScripts.get_client_script_by_id(form_data.id, db=db) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='ID is already in use')

    script = await ClientScripts.insert_new_client_script(user.id, form_data, db=db)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating script'
        )
    return script


############################
# Get / Update / Toggle / Access / Delete
############################


@router.get('/id/{id}', response_model=ClientScriptAccessResponse | None)
async def get_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    script = await ClientScripts.get_client_script_by_id(id, db=db)
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Script not found')

    can_read = (
        user.role == 'admin'
        or script.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id, resource_type=RESOURCE_TYPE, resource_id=id, permission='read', db=db
        )
    )
    if not can_read:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Access prohibited')

    write_access = (
        user.role == 'admin'
        or script.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id, resource_type=RESOURCE_TYPE, resource_id=id, permission='write', db=db
        )
    )
    return ClientScriptAccessResponse(**script.model_dump(), write_access=write_access)


@router.post('/id/{id}/update', response_model=ClientScriptModel | None)
async def update_client_script_by_id(
    id: str,
    form_data: ClientScriptForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _require_write(id, user, db)
    return await ClientScripts.update_client_script_by_id(
        id,
        {
            'name': form_data.name,
            'content': form_data.content,
            'meta': form_data.meta.model_dump(),
            'access_grants': form_data.access_grants,
        },
        db=db,
    )


@router.post('/id/{id}/toggle', response_model=ClientScriptModel | None)
async def toggle_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    script = await _require_write(id, user, db)
    return await ClientScripts.update_client_script_by_id(
        id, {'is_active': not script.is_active}, db=db
    )


@router.post('/id/{id}/toggle/global', response_model=ClientScriptModel | None)
async def toggle_client_script_global_by_id(
    id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    """Admin-only: mark a script global (runs for all users) or revoke it."""
    script = await ClientScripts.get_client_script_by_id(id, db=db)
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Script not found')
    return await ClientScripts.update_client_script_by_id(
        id, {'is_global': not script.is_global}, db=db
    )


@router.post('/id/{id}/access/update', response_model=ClientScriptModel | None)
async def update_client_script_access_by_id(
    id: str,
    form_data: dict,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _require_write(id, user, db)
    await AccessGrants.set_access_grants(
        RESOURCE_TYPE, id, form_data.get('access_grants', []), db=db
    )
    return await ClientScripts.get_client_script_by_id(id, db=db)


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await _require_write(id, user, db)
    return await ClientScripts.delete_client_script_by_id(id, db=db)
