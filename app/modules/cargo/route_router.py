"""TEHTEK — Cargo Routes Router.

Manages DB-driven cargo routes and their ordered stops.
All routes require cargo:routes permission (superadmin or explicit grant).
"""
from datetime import datetime
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.cargo.route_models import CargoRoute, CargoRouteStop
from app.modules.finance.extended_models import Location

router = APIRouter(
    prefix="/api/v1",
    tags=["cargo-routes"],
    dependencies=[Depends(get_current_user)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RouteStopIn(BaseModel):
    sequence_order: int
    location_id:    Optional[int] = None
    event_type:     str
    label:          Optional[str] = None
    stop_side:      str = "origin"   # origin | transit | destination
    condition:      Optional[str] = None


class RouteCreate(BaseModel):
    name:           str
    code:           str
    origin_country: str
    dest_country:   str
    transport_mode: str              # sea | air | land | local
    notes:          Optional[str] = None
    stops:          List[RouteStopIn] = []


class RouteUpdate(BaseModel):
    name:           Optional[str] = None
    code:           Optional[str] = None
    origin_country: Optional[str] = None
    dest_country:   Optional[str] = None
    transport_mode: Optional[str] = None
    is_active:      Optional[bool] = None
    notes:          Optional[str] = None


def _stop_out(stop: CargoRouteStop) -> Dict[str, Any]:
    loc = stop.location
    return {
        "id":             stop.id,
        "route_id":       stop.route_id,
        "sequence_order": stop.sequence_order,
        "location_id":    stop.location_id,
        "location": {
            "id":      loc.id,
            "name":    loc.name,
            "city":    loc.city,
            "country": loc.country,
            "type":    loc.type,
        } if loc else None,
        "event_type":     stop.event_type,
        "label":          stop.label,
        "stop_side":      stop.stop_side,
        "condition":      stop.condition,
    }


def _route_out(route: CargoRoute) -> Dict[str, Any]:
    return {
        "id":             route.id,
        "name":           route.name,
        "code":           route.code,
        "origin_country": route.origin_country,
        "dest_country":   route.dest_country,
        "transport_mode": route.transport_mode,
        "is_active":      route.is_active,
        "notes":          route.notes,
        "created_at":     route.created_at.isoformat() if route.created_at else None,
        "stops":          [_stop_out(s) for s in route.stops],
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/cargo/routes")
def list_routes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all active routes for the company."""
    routes = (
        db.query(CargoRoute)
        .filter_by(company_id=current_user.company_id)
        .order_by(CargoRoute.name)
        .all()
    )
    return [_route_out(r) for r in routes]


@router.get("/cargo/routes/{route_id}")
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    route = db.query(CargoRoute).filter_by(
        id=route_id, company_id=current_user.company_id
    ).first()
    if not route:
        raise HTTPException(404, "Route not found")
    return _route_out(route)


@router.post("/cargo/routes", status_code=201)
def create_route(
    body: RouteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:routes")),
):
    """Create a route with its stops."""
    # Validate stops — each location_id must belong to the company (via Location)
    for stop in body.stops:
        if stop.location_id is not None:
            loc = db.query(Location).filter_by(
                id=stop.location_id, company_id=current_user.company_id
            ).first()
            if not loc:
                raise HTTPException(400, f"Location {stop.location_id} not found")

    route = CargoRoute(
        company_id=current_user.company_id,
        name=body.name,
        code=body.code.upper().strip(),
        origin_country=body.origin_country,
        dest_country=body.dest_country,
        transport_mode=body.transport_mode,
        notes=body.notes,
    )
    db.add(route)
    db.flush()  # get route.id

    for s in body.stops:
        db.add(CargoRouteStop(
            route_id=route.id,
            sequence_order=s.sequence_order,
            location_id=s.location_id,
            event_type=s.event_type,
            label=s.label or None,
            stop_side=s.stop_side,
            condition=s.condition or None,
        ))

    db.commit()
    db.refresh(route)
    return _route_out(route)


@router.patch("/cargo/routes/{route_id}")
def update_route(
    route_id: int,
    body: RouteUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:routes")),
):
    route = db.query(CargoRoute).filter_by(
        id=route_id, company_id=current_user.company_id
    ).first()
    if not route:
        raise HTTPException(404, "Route not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "code" and value:
            value = value.upper().strip()
        setattr(route, field, value)

    route.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(route)
    return _route_out(route)


@router.put("/cargo/routes/{route_id}/stops")
def replace_stops(
    route_id: int,
    stops: List[RouteStopIn],
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:routes")),
):
    """Full replacement of all stops for a route."""
    route = db.query(CargoRoute).filter_by(
        id=route_id, company_id=current_user.company_id
    ).first()
    if not route:
        raise HTTPException(404, "Route not found")

    # Validate locations
    for s in stops:
        if s.location_id is not None:
            loc = db.query(Location).filter_by(
                id=s.location_id, company_id=current_user.company_id
            ).first()
            if not loc:
                raise HTTPException(400, f"Location {s.location_id} not found")

    # Delete existing stops (cascade=all handles this but explicit is clearer)
    for existing in route.stops:
        db.delete(existing)
    db.flush()

    for s in stops:
        db.add(CargoRouteStop(
            route_id=route.id,
            sequence_order=s.sequence_order,
            location_id=s.location_id,
            event_type=s.event_type,
            label=s.label or None,
            stop_side=s.stop_side,
            condition=s.condition or None,
        ))

    route.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(route)
    return _route_out(route)


@router.delete("/cargo/routes/{route_id}", status_code=204)
def delete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("cargo:routes")),
):
    route = db.query(CargoRoute).filter_by(
        id=route_id, company_id=current_user.company_id
    ).first()
    if not route:
        raise HTTPException(404, "Route not found")

    # Deactivate instead of hard-delete (shipments may reference it)
    route.is_active = False
    route.updated_at = datetime.utcnow()
    db.commit()
