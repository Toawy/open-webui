"""User-managed client scripts: stored JavaScript that runs in the user's browser.

Security model: a client script runs ONLY in its author's own browser, with the
same privileges the user already has (they could run the same JS via DevTools or
a userscript manager). It is therefore user-managed (NOT admin-gated) and strictly
scoped to its owner. The server stores and serves scripts but never executes them.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.internal.db import get_async_session
from open_webui.models.client_scripts import (
    ClientScriptForm,
    ClientScriptModel,
    ClientScripts,
)
from open_webui.utils.auth import get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


async def _get_owned_script_or_error(id: str, user, db: AsyncSession) -> ClientScriptModel:
    """Fetch a script and ensure the requesting user owns it (admins may override)."""
    script = await ClientScripts.get_client_script_by_id(id, db=db)
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client script not found')
    if script.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Access prohibited')
    return script


############################
# List
############################


@router.get('/', response_model=list[ClientScriptModel])
async def get_client_scripts(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """All of the current user's client scripts (for the management UI)."""
    return await ClientScripts.get_client_scripts_by_user_id(user.id, db=db)


@router.get('/active', response_model=list[ClientScriptModel])
async def get_active_client_scripts(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    """The current user's enabled scripts (fetched by the frontend loader)."""
    return await ClientScripts.get_client_scripts_by_user_id(user.id, active_only=True, db=db)


############################
# Create
############################


@router.post('/create', response_model=ClientScriptModel | None)
async def create_new_client_script(
    form_data: ClientScriptForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    script = await ClientScripts.insert_new_client_script(user.id, form_data, db=db)
    if not script:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='Error creating client script'
        )
    return script


############################
# Get / Toggle / Update / Delete (owner-scoped)
############################


@router.get('/id/{id}', response_model=ClientScriptModel | None)
async def get_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    return await _get_owned_script_or_error(id, user, db)


@router.post('/id/{id}/toggle', response_model=ClientScriptModel | None)
async def toggle_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    script = await _get_owned_script_or_error(id, user, db)
    return await ClientScripts.update_client_script_by_id(
        id, {'is_active': not script.is_active}, db=db
    )


@router.post('/id/{id}/update', response_model=ClientScriptModel | None)
async def update_client_script_by_id(
    id: str,
    form_data: ClientScriptForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await _get_owned_script_or_error(id, user, db)
    return await ClientScripts.update_client_script_by_id(
        id,
        {
            'name': form_data.name,
            'content': form_data.content,
            'meta': form_data.meta.model_dump(),
        },
        db=db,
    )


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_client_script_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await _get_owned_script_or_error(id, user, db)
    return await ClientScripts.delete_client_script_by_id(id, db=db)
