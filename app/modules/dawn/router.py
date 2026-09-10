"""TEHTEK — Dawn Block API, consumed by the Android app.

Every route is scoped to the authenticated user: no permission flag, because
this is personal data rather than company data — owning the account is the
authorisation.
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.dawn.models import DawnCandidate, DawnDay, DawnResearch, DawnSet

router = APIRouter(prefix="/api/v1/dawn", tags=["dawn-block"])

STAGES = ["Scanning", "Sourcing", "Costed", "Sampled", "Ordered"]


# ── Morning blocks ───────────────────────────────────────────────────────────

class DayIn(BaseModel):
    day:    str = Field(min_length=10, max_length=10)   # YYYY-MM-DD
    blocks: list[str] = Field(default_factory=list, max_length=40)


@router.get("/days")
def list_days(since: str | None = Query(default=None),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DawnDay).filter(DawnDay.user_id == user.id)
    if since:
        q = q.filter(DawnDay.day >= since)
    rows = q.order_by(DawnDay.day.desc()).limit(120).all()
    return {"items": [{"day": r.day, "blocks": json.loads(r.blocks or "[]")} for r in rows]}


@router.put("/days")
def upsert_day(body: DayIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Idempotent: the app sends the full tick list for that day."""
    row = (db.query(DawnDay)
             .filter(DawnDay.user_id == user.id, DawnDay.day == body.day).first())
    if row is None:
        row = DawnDay(user_id=user.id, day=body.day)
        db.add(row)
    row.blocks = json.dumps(sorted(set(body.blocks)))
    db.commit()
    return {"day": row.day, "blocks": json.loads(row.blocks)}


# ── Training sets ────────────────────────────────────────────────────────────

class SetIn(BaseModel):
    lift_id:   str = Field(min_length=1, max_length=40)
    lift_name: str | None = Field(default=None, max_length=120)
    day:       str = Field(min_length=10, max_length=10)
    weight:    float = Field(gt=0, le=2000)
    reps:      int = Field(ge=1, le=500)


@router.get("/sets")
def list_sets(lift_id: str | None = Query(default=None), limit: int = Query(default=400, le=2000),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DawnSet).filter(DawnSet.user_id == user.id)
    if lift_id:
        q = q.filter(DawnSet.lift_id == lift_id)
    rows = q.order_by(DawnSet.id.desc()).limit(limit).all()
    return {"items": [{
        "id": r.id, "lift_id": r.lift_id, "lift_name": r.lift_name,
        "day": r.day, "weight": float(r.weight), "reps": r.reps,
        "created_at": r.created_at.isoformat(),
    } for r in reversed(rows)]}


@router.post("/sets", status_code=201)
def add_set(body: SetIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = DawnSet(user_id=user.id, lift_id=body.lift_id, lift_name=body.lift_name,
                  day=body.day, weight=body.weight, reps=body.reps)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "lift_id": row.lift_id, "day": row.day,
            "weight": float(row.weight), "reps": row.reps}


@router.get("/sets/last")
def last_per_lift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The most recent set for every lift — what the app shows as 'beat this'."""
    rows = (db.query(DawnSet).filter(DawnSet.user_id == user.id)
              .order_by(DawnSet.id.desc()).limit(2000).all())
    best: dict[str, dict] = {}
    for r in rows:
        if r.lift_id not in best:
            best[r.lift_id] = {"day": r.day, "weight": float(r.weight), "reps": r.reps}
    return {"items": best}


# ── Product research board ───────────────────────────────────────────────────

class CandidateIn(BaseModel):
    name:     str = Field(min_length=1, max_length=200)
    category: str = Field(default="Other", max_length=60)
    notes:    str | None = None


class CandidatePatch(BaseModel):
    stage: int | None = Field(default=None, ge=0, le=len(STAGES) - 1)
    notes: str | None = None
    name:  str | None = Field(default=None, max_length=200)


def _cand(r: DawnCandidate) -> dict:
    return {"id": r.id, "name": r.name, "category": r.category, "stage": r.stage,
            "stage_label": STAGES[r.stage] if 0 <= r.stage < len(STAGES) else "?",
            "notes": r.notes, "created_at": r.created_at.isoformat()}


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(DawnCandidate)
              .filter(DawnCandidate.user_id == user.id, DawnCandidate.killed_at.is_(None))
              .order_by(DawnCandidate.id.desc()).all())
    return {"items": [_cand(r) for r in rows], "stages": STAGES}


@router.post("/candidates", status_code=201)
def add_candidate(body: CandidateIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = DawnCandidate(user_id=user.id, name=body.name.strip(),
                        category=body.category, notes=body.notes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _cand(row)


def _own(db: Session, user, cid: int) -> DawnCandidate:
    row = (db.query(DawnCandidate)
             .filter(DawnCandidate.id == cid, DawnCandidate.user_id == user.id).first())
    if not row:
        raise HTTPException(404, "Candidat introuvable")
    return row


@router.patch("/candidates/{cid}")
def patch_candidate(cid: int, body: CandidatePatch,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = _own(db, user, cid)
    if body.stage is not None: row.stage = body.stage
    if body.notes is not None: row.notes = body.notes
    if body.name:              row.name = body.name.strip()
    db.commit()
    db.refresh(row)
    return _cand(row)


@router.delete("/candidates/{cid}", status_code=204)
def kill_candidate(cid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Soft delete: a killed idea is a result worth keeping."""
    row = _own(db, user, cid)
    row.killed_at = datetime.utcnow()
    db.commit()


# ── Research sessions ────────────────────────────────────────────────────────

class ResearchIn(BaseModel):
    day:          str = Field(min_length=10, max_length=10)
    focus:        str | None = Field(default=None, max_length=60)
    candidate_id: int | None = None
    minutes:      int | None = Field(default=None, ge=0, le=600)
    findings:     str | None = None


@router.get("/research")
def list_research(limit: int = Query(default=60, le=365),
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(DawnResearch).filter(DawnResearch.user_id == user.id)
              .order_by(DawnResearch.id.desc()).limit(limit).all())
    return {"items": [{
        "id": r.id, "day": r.day, "focus": r.focus, "candidate_id": r.candidate_id,
        "minutes": r.minutes, "findings": r.findings,
        "created_at": r.created_at.isoformat(),
    } for r in rows]}


@router.post("/research", status_code=201)
def add_research(body: ResearchIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if body.candidate_id is not None:
        _own(db, user, body.candidate_id)     # never log against someone else's idea
    row = DawnResearch(user_id=user.id, day=body.day, focus=body.focus,
                       candidate_id=body.candidate_id, minutes=body.minutes,
                       findings=body.findings)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "day": row.day, "focus": row.focus}


# ── One call the app makes on launch ─────────────────────────────────────────

@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Everything the app needs at 3am, in a single round trip."""
    days = (db.query(DawnDay).filter(DawnDay.user_id == user.id)
              .order_by(DawnDay.day.desc()).limit(14).all())
    cands = (db.query(DawnCandidate)
               .filter(DawnCandidate.user_id == user.id, DawnCandidate.killed_at.is_(None))
               .order_by(DawnCandidate.id.desc()).all())
    return {
        "user": {"id": user.id, "name": getattr(user, "first_name", None) or user.email},
        "days": [{"day": d.day, "blocks": json.loads(d.blocks or "[]")} for d in days],
        "last_sets": last_per_lift(db, user)["items"],
        "candidates": [_cand(c) for c in cands],
        "stages": STAGES,
    }
