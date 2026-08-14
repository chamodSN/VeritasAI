from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_current_user
from services.courtlistener import courtlistener_client
from services.docket_monitor import list_user_alerts, save_user_alert, remove_user_alert

router = APIRouter()


class AlertCreate(BaseModel):
    query: str
    name: str
    rate: str = "dly"


@router.post("/alerts")
async def create_alert(payload: AlertCreate, user: dict = Depends(get_current_user)):
    async with courtlistener_client as cl:
        resource_uri = await cl.create_alert(payload.query, payload.name, payload.rate)

    if not resource_uri:
        raise HTTPException(
            status_code=502, detail="Failed to create alert on CourtListener")

    await save_user_alert(user["user_id"], payload.name, payload.query, payload.rate, resource_uri)
    return {"status": "created", "resource_uri": resource_uri}


@router.get("/alerts")
async def get_alerts(user: dict = Depends(get_current_user)):
    async with courtlistener_client as cl:
        remote_alerts = await cl.get_alerts()
    local_alerts = await list_user_alerts(user["user_id"])
    return {"alerts": [a.__dict__ for a in remote_alerts], "tracked": local_alerts}


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, user: dict = Depends(get_current_user)):
    async with courtlistener_client as cl:
        ok = await cl.delete_alert(alert_id)
    if ok:
        await remove_user_alert(user["user_id"], alert_id)
    return {"status": "deleted" if ok else "failed"}
