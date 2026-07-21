"""
Dream Tracker ("North Star") — API. Single-owner personal tool (auth required,
same convention as the personal module — no per-user scoping).
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.dreams.models import Dream, DreamState, DreamStep

router = APIRouter(
    prefix="/api/v1/dreams",
    tags=["Dreams"],
    dependencies=[Depends(get_current_user)],  # ACC-007: auth at router level
)


def _state(db: Session) -> DreamState:
    st = db.get(DreamState, 1)
    if st is None:
        st = DreamState(id=1, abcde=[
            {"g": "A", "t": "", "done": False},
            {"g": "B", "t": "", "done": False},
            {"g": "C", "t": "", "done": False},
        ])
        db.add(st)
        db.commit()
        db.refresh(st)
    return st


def _state_dict(st: DreamState) -> dict:
    return {
        "mdp": st.mdp or "", "mdp_date": st.mdp_date.isoformat() if st.mdp_date else "",
        "frog": st.frog or "", "frog_date": st.frog_date.isoformat() if st.frog_date else "",
        "abcde": st.abcde or [], "streak": st.streak,
        "last_commit": st.last_commit.isoformat() if st.last_commit else "",
        "last_rewrite": st.last_rewrite.isoformat() if st.last_rewrite else "",
    }


def _dream_dict(d: Dream) -> dict:
    return {
        "id": d.id, "title": d.title, "life_area": d.life_area,
        "is_major_purpose": d.is_major_purpose,
        "target_date": d.target_date.isoformat() if d.target_date else "",
        "progress": d.progress, "status": d.status,
        "why": d.why or "", "obstacles": d.obstacles or "",
        "skills": d.skills or "", "people": d.people or "", "position": d.position,
        "steps": [{"id": s.id, "text": s.text, "done": s.done, "position": s.position} for s in d.steps],
    }


def _recalc(d: Dream) -> None:
    if d.steps:
        done = sum(1 for s in d.steps if s.done)
        d.progress = round(done / len(d.steps) * 100)


# ── State ─────────────────────────────────────────────────────────────────────

class StatePatch(BaseModel):
    mdp: str | None = None
    mdp_date: str | None = None
    frog: str | None = None
    frog_date: str | None = None
    abcde: list | None = None


@router.get("/state")
def get_state(db: Session = Depends(get_db)):
    return _state_dict(_state(db))


@router.patch("/state")
def patch_state(body: StatePatch, db: Session = Depends(get_db)):
    st = _state(db)
    if body.mdp is not None:
        st.mdp = body.mdp
    if body.mdp_date is not None:
        st.mdp_date = date.fromisoformat(body.mdp_date) if body.mdp_date else None
    if body.frog is not None:
        st.frog = body.frog
        st.frog_date = date.today()
    if body.frog_date is not None:
        st.frog_date = date.fromisoformat(body.frog_date) if body.frog_date else None
    if body.abcde is not None:
        st.abcde = body.abcde
    db.commit()
    return _state_dict(st)


@router.post("/rewrite")
def rewrite(db: Session = Depends(get_db)):
    st = _state(db)
    st.last_rewrite = date.today()
    db.commit()
    return _state_dict(st)


@router.post("/commit")
def commit_action(db: Session = Depends(get_db)):
    """Log that an action toward the major goal was taken today; update the streak."""
    st = _state(db)
    today = date.today()
    if st.last_commit == today:
        return _state_dict(st)
    st.streak = st.streak + 1 if st.last_commit == today - timedelta(days=1) else 1
    st.last_commit = today
    db.commit()
    return _state_dict(st)


# ── Dreams ────────────────────────────────────────────────────────────────────

class DreamPatch(BaseModel):
    title: str | None = None
    life_area: str | None = None
    target_date: str | None = None
    progress: int | None = None
    status: str | None = None
    why: str | None = None
    obstacles: str | None = None
    skills: str | None = None
    people: str | None = None
    is_major_purpose: bool | None = None


@router.get("")
def list_dreams(db: Session = Depends(get_db)):
    rows = db.query(Dream).order_by(Dream.position, Dream.id).all()
    return [_dream_dict(d) for d in rows]


@router.post("", status_code=201)
def create_dream(db: Session = Depends(get_db)):
    maxpos = db.query(Dream).count()
    d = Dream(title="", life_area="business", position=maxpos)
    db.add(d)
    db.commit()
    db.refresh(d)
    return _dream_dict(d)


@router.patch("/{dream_id}")
def update_dream(dream_id: int, body: DreamPatch, db: Session = Depends(get_db)):
    d = db.get(Dream, dream_id)
    if d is None:
        raise HTTPException(404, "Dream not found")
    data = body.model_dump(exclude_unset=True)
    if "is_major_purpose" in data and data["is_major_purpose"]:
        db.query(Dream).update({Dream.is_major_purpose: False})
        d.is_major_purpose = True
        data.pop("is_major_purpose")
    if "target_date" in data:
        d.target_date = date.fromisoformat(data.pop("target_date")) if data["target_date"] else None
    if "progress" in data and data["progress"] is not None:
        data["progress"] = max(0, min(100, data["progress"]))
    for k, v in data.items():
        setattr(d, k, v)
    db.commit()
    return _dream_dict(d)


@router.delete("/{dream_id}", status_code=204)
def delete_dream(dream_id: int, db: Session = Depends(get_db)):
    d = db.get(Dream, dream_id)
    if d:
        db.delete(d)
        db.commit()


# ── Steps ─────────────────────────────────────────────────────────────────────

class StepPatch(BaseModel):
    text: str | None = None
    done: bool | None = None


@router.post("/{dream_id}/steps", status_code=201)
def add_step(dream_id: int, db: Session = Depends(get_db)):
    d = db.get(Dream, dream_id)
    if d is None:
        raise HTTPException(404, "Dream not found")
    step = DreamStep(dream_id=dream_id, text="", position=len(d.steps))
    db.add(step)
    db.commit()
    db.refresh(d)
    return _dream_dict(d)


@router.patch("/steps/{step_id}")
def update_step(step_id: int, body: StepPatch, db: Session = Depends(get_db)):
    s = db.get(DreamStep, step_id)
    if s is None:
        raise HTTPException(404, "Step not found")
    if body.text is not None:
        s.text = body.text
    if body.done is not None:
        s.done = body.done
    _recalc(s.dream)
    db.commit()
    return _dream_dict(s.dream)


@router.delete("/steps/{step_id}")
def delete_step(step_id: int, db: Session = Depends(get_db)):
    s = db.get(DreamStep, step_id)
    if s is None:
        return {"ok": True}
    d = s.dream
    db.delete(s)
    db.flush()
    _recalc(d)
    db.commit()
    return _dream_dict(d)
