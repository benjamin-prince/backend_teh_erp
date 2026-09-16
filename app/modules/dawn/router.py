"""TEHTEK — Dawn Block API, consumed by the Android app.

Every route is scoped to the authenticated user: no permission flag, because
this is personal data rather than company data — owning the account is the
authorisation.
"""
import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.dawn.models import (
    DawnCandidate, DawnDay, DawnMeal, DawnPlanItem, DawnProfile,
    DawnResearch, DawnSet, DawnWeight,
)

router = APIRouter(prefix="/api/v1/dawn", tags=["dawn-block"])

STAGES = ["Scanning", "Sourcing", "Costed", "Sampled", "Ordered"]


# ── Morning blocks ───────────────────────────────────────────────────────────

class DayIn(BaseModel):
    day:       str = Field(min_length=10, max_length=10)   # YYYY-MM-DD
    blocks:    list[str] = Field(default_factory=list, max_length=40)
    wake_time: str | None = Field(default=None, max_length=5)    # HH:MM
    drink:     str | None = Field(default=None, max_length=20)   # water|tea|coffee|none
    read_note: str | None = Field(default=None, max_length=2000)


def _day_out(r: DawnDay) -> dict:
    return {"day": r.day, "blocks": json.loads(r.blocks or "[]"),
            "wake_time": r.wake_time, "drink": r.drink, "read_note": r.read_note}


@router.get("/days")
def list_days(since: str | None = Query(default=None),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DawnDay).filter(DawnDay.user_id == user.id)
    if since:
        q = q.filter(DawnDay.day >= since)
    rows = q.order_by(DawnDay.day.desc()).limit(120).all()
    return {"items": [_day_out(r) for r in rows]}


@router.put("/days")
def upsert_day(body: DayIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Idempotent: the app sends the full tick list for that day."""
    row = (db.query(DawnDay)
             .filter(DawnDay.user_id == user.id, DawnDay.day == body.day).first())
    if row is None:
        row = DawnDay(user_id=user.id, day=body.day)
        db.add(row)
    row.blocks = json.dumps(sorted(set(body.blocks)))
    # None means "not sent", so a partial update never wipes the other fields.
    if body.wake_time is not None: row.wake_time = body.wake_time or None
    if body.drink is not None:     row.drink = body.drink or None
    if body.read_note is not None: row.read_note = body.read_note or None
    db.commit()
    return _day_out(row)


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


# ── Profile and intake targets ───────────────────────────────────────────────

def _targets(p: DawnProfile) -> dict:
    """
    Protein at 2.0 g per kg — the upper half of the 1.6–2.2 range that the
    evidence supports for gaining, because under-eating protein is the common
    failure and the excess is harmless.

    Calories at maintenance plus a 400 kcal surplus: roughly 0.4 kg a week,
    the middle of the 0.25–0.5 target. Maintenance uses 33 kcal/kg, which fits
    a lifter training four mornings a week.
    """
    bw = float(p.bodyweight_kg or 90)
    return {
        "protein_g": int(p.protein_target_g or round(bw * 2.0)),
        "kcal": int(p.kcal_target or round(bw * 33 + 400)),
    }


class ProfileIn(BaseModel):
    bodyweight_kg:    float | None = Field(default=None, gt=20, le=400)
    goal_kg:          float | None = Field(default=None, gt=20, le=400)
    protein_target_g: int | None = Field(default=None, ge=0, le=600)
    kcal_target:      int | None = Field(default=None, ge=0, le=10000)


def _get_profile(db: Session, user) -> DawnProfile:
    p = db.query(DawnProfile).filter(DawnProfile.user_id == user.id).first()
    if p is None:
        p = DawnProfile(user_id=user.id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def _profile_out(p: DawnProfile) -> dict:
    return {"bodyweight_kg": float(p.bodyweight_kg), "goal_kg": float(p.goal_kg),
            "targets": _targets(p)}


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _profile_out(_get_profile(db, user))


@router.put("/profile")
def put_profile(body: ProfileIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    p = _get_profile(db, user)
    if body.bodyweight_kg is not None:    p.bodyweight_kg = body.bodyweight_kg
    if body.goal_kg is not None:          p.goal_kg = body.goal_kg
    if body.protein_target_g is not None: p.protein_target_g = body.protein_target_g or None
    if body.kcal_target is not None:      p.kcal_target = body.kcal_target or None
    db.commit()
    db.refresh(p)
    return _profile_out(p)


# ── Training plan, editable ──────────────────────────────────────────────────

DEFAULT_PLAN: dict[int, list[tuple[str, str, str]]] = {
    1: [("bench", "Smith / Barbell Bench Press", "4 × 6–8"),
        ("incline-db", "Incline Dumbbell Press", "4 × 8–10"),
        ("machine-press", "Machine Chest Press", "3 × 10–12"),
        ("cable-fly", "High-to-Low Cable Fly", "3 × 12–15"),
        ("rope-pushdown", "Rope Pushdown", "3 × 10–12"),
        ("cable-ext", "Single-Arm Cable Extension", "3 × 12–15")],
    2: [("pulldown", "Wide-Grip Lat Pulldown", "4 × 8–10"),
        ("cable-row", "Seated Cable Row", "4 × 8–10"),
        ("db-row", "One-Arm Dumbbell Row", "3 × 10 / side"),
        ("straight-arm", "Straight-Arm Pulldown", "3 × 12–15"),
        ("incline-curl", "Incline Dumbbell Curl", "3 × 8–10"),
        ("hammer", "Hammer Curl", "3 × 10–12"),
        ("preacher", "Preacher Curl", "2 × 12–15")],
    3: [("bike-easy", "Easy bicycle", "20–30 min")],
    4: [("incline-smith", "Incline Smith Press", "4 × 6–8"),
        ("flat-db", "Flat Dumbbell Press", "3 × 8–10"),
        ("pec-deck", "Pec Deck", "3 × 12–15"),
        ("db-shoulder", "Dumbbell Shoulder Press", "3 × 8–10"),
        ("cable-lateral", "Cable Lateral Raise", "4 × 12–15"),
        ("ez-curl", "EZ-Bar / Cable Curl", "3 × 10–12"),
        ("overhead-rope", "Overhead Rope Triceps Extension", "3 × 10–12")],
    5: [("hack-squat", "Hack Squat / Smith Squat", "4 × 6–10"),
        ("rdl", "Romanian Deadlift", "3 × 8–10"),
        ("leg-press", "Leg Press", "3 × 10–12"),
        ("leg-curl", "Lying / Seated Leg Curl", "3 × 10–12"),
        ("hip-thrust", "Hip Thrust", "4 × 8–12"),
        ("calf", "Calf Raise", "4 × 12–15"),
        ("cable-hammer", "Cable Hammer Curl", "3 × 12"),
        ("dip", "Assisted Dip / Triceps Press", "3 × 10–12")],
    6: [("bike-sat", "Easy bicycle", "20–30 min"),
        ("stretch", "Stretching", "10 min")],
    0: [],
}

SESSION_NAMES = {
    0: "Full rest", 1: "Chest A + Triceps", 2: "Back + Biceps", 3: "Recovery",
    4: "Chest B + Shoulders + Arms", 5: "Legs + Glutes + Arms", 6: "Active recovery",
}


def _seed_plan(db: Session, user) -> None:
    """First read installs the programme; after that the user's edits stand."""
    if db.query(DawnPlanItem).filter(DawnPlanItem.user_id == user.id).first():
        return
    for dow, items in DEFAULT_PLAN.items():
        for i, (lid, name, scheme) in enumerate(items):
            db.add(DawnPlanItem(user_id=user.id, dow=dow, position=i,
                                lift_id=lid, name=name, scheme=scheme))
    db.commit()


def _plan_out(rows: list[DawnPlanItem]) -> dict:
    by_day: dict[str, list[dict]] = {str(d): [] for d in range(7)}
    for r in sorted(rows, key=lambda x: (x.dow, x.position, x.id)):
        by_day[str(r.dow)].append({"id": r.id, "lift_id": r.lift_id,
                                   "name": r.name, "scheme": r.scheme})
    return {"days": by_day, "names": {str(k): v for k, v in SESSION_NAMES.items()}}


class PlanItemIn(BaseModel):
    dow:     int = Field(ge=0, le=6)
    name:    str = Field(min_length=1, max_length=120)
    scheme:  str | None = Field(default=None, max_length=40)
    lift_id: str | None = Field(default=None, max_length=40)


class PlanItemPatch(BaseModel):
    name:     str | None = Field(default=None, max_length=120)
    scheme:   str | None = Field(default=None, max_length=40)
    position: int | None = Field(default=None, ge=0, le=99)


@router.get("/plan")
def get_plan(db: Session = Depends(get_db), user=Depends(get_current_user)):
    _seed_plan(db, user)
    rows = db.query(DawnPlanItem).filter(DawnPlanItem.user_id == user.id).all()
    return _plan_out(rows)


@router.post("/plan", status_code=201)
def add_plan_item(body: PlanItemIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    last = (db.query(DawnPlanItem)
              .filter(DawnPlanItem.user_id == user.id, DawnPlanItem.dow == body.dow)
              .order_by(DawnPlanItem.position.desc()).first())
    lid = body.lift_id or re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")[:40]
    row = DawnPlanItem(user_id=user.id, dow=body.dow,
                       position=(last.position + 1) if last else 0,
                       lift_id=lid or "custom", name=body.name.strip(), scheme=body.scheme)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "lift_id": row.lift_id, "name": row.name, "scheme": row.scheme}


def _own_item(db: Session, user, iid: int) -> DawnPlanItem:
    row = (db.query(DawnPlanItem)
             .filter(DawnPlanItem.id == iid, DawnPlanItem.user_id == user.id).first())
    if not row:
        raise HTTPException(404, "Exercice introuvable")
    return row


@router.patch("/plan/{iid}")
def patch_plan_item(iid: int, body: PlanItemPatch,
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = _own_item(db, user, iid)
    if body.name:                  row.name = body.name.strip()
    if body.scheme is not None:    row.scheme = body.scheme
    if body.position is not None:  row.position = body.position
    db.commit()
    db.refresh(row)
    return {"id": row.id, "lift_id": row.lift_id, "name": row.name, "scheme": row.scheme}


@router.delete("/plan/{iid}", status_code=204)
def delete_plan_item(iid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.delete(_own_item(db, user, iid))
    db.commit()


@router.post("/plan/reset")
def reset_plan(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Back to the programme as written, discarding edits."""
    db.query(DawnPlanItem).filter(DawnPlanItem.user_id == user.id).delete()
    db.commit()
    _seed_plan(db, user)
    rows = db.query(DawnPlanItem).filter(DawnPlanItem.user_id == user.id).all()
    return _plan_out(rows)


# ── Meals ────────────────────────────────────────────────────────────────────

SLOTS = ("fuel", "breakfast", "lunch", "dinner", "snack")

# What to eat at 4:10am: fast protein plus fast carbs, low fat and low fibre so
# it is out of the stomach before the first set. Around 250 kcal is enough —
# more sits heavy under a bench press.
FUEL_IDEAS = [
    {"text": "Whey shake + banana",              "kcal": 250, "protein_g": 27},
    {"text": "Greek yogurt + honey + oats",      "kcal": 280, "protein_g": 22},
    {"text": "3 egg whites + white toast",       "kcal": 230, "protein_g": 20},
    {"text": "Rice cakes + whey in water",       "kcal": 220, "protein_g": 25},
    {"text": "Skimmed milk + dates",             "kcal": 240, "protein_g": 18},
]


class MealIn(BaseModel):
    day:       str = Field(min_length=10, max_length=10)
    slot:      str = Field(max_length=20)
    text:      str = Field(min_length=1, max_length=500)
    kcal:      int | None = Field(default=None, ge=0, le=10000)
    protein_g: int | None = Field(default=None, ge=0, le=600)


@router.get("/meals")
def list_meals(day: str | None = Query(default=None),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DawnMeal).filter(DawnMeal.user_id == user.id)
    if day:
        q = q.filter(DawnMeal.day == day)
    rows = q.order_by(DawnMeal.id.desc()).limit(200).all()
    total_k = sum(r.kcal or 0 for r in rows if not day or r.day == day)
    total_p = sum(r.protein_g or 0 for r in rows if not day or r.day == day)
    return {
        "items": [{"id": r.id, "day": r.day, "slot": r.slot, "text": r.text,
                   "kcal": r.kcal, "protein_g": r.protein_g} for r in rows],
        "totals": {"kcal": total_k, "protein_g": total_p},
    }


@router.post("/meals", status_code=201)
def add_meal(body: MealIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if body.slot not in SLOTS:
        raise HTTPException(400, f"Slot invalide. Attendu : {', '.join(SLOTS)}")
    row = DawnMeal(user_id=user.id, day=body.day, slot=body.slot,
                   text=body.text.strip(), kcal=body.kcal, protein_g=body.protein_g)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "day": row.day, "slot": row.slot, "text": row.text,
            "kcal": row.kcal, "protein_g": row.protein_g}


@router.delete("/meals/{mid}", status_code=204)
def delete_meal(mid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(DawnMeal).filter(DawnMeal.id == mid, DawnMeal.user_id == user.id).first()
    if not row:
        raise HTTPException(404, "Repas introuvable")
    db.delete(row)
    db.commit()


# ── Bodyweight ───────────────────────────────────────────────────────────────

class WeightIn(BaseModel):
    day: str = Field(min_length=10, max_length=10)
    kg:  float = Field(gt=20, le=400)


@router.get("/weights")
def list_weights(limit: int = Query(default=120, le=730),
                 db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (db.query(DawnWeight).filter(DawnWeight.user_id == user.id)
              .order_by(DawnWeight.day.desc()).limit(limit).all())
    return {"items": [{"day": r.day, "kg": float(r.kg)} for r in rows]}


@router.put("/weights")
def upsert_weight(body: WeightIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One reading a day: stepping on the scale twice should not skew a trend."""
    row = (db.query(DawnWeight)
             .filter(DawnWeight.user_id == user.id, DawnWeight.day == body.day).first())
    if row is None:
        row = DawnWeight(user_id=user.id, day=body.day)
        db.add(row)
    row.kg = body.kg
    db.commit()
    # Bodyweight drives the intake targets, so keep the profile in step.
    p = _get_profile(db, user)
    p.bodyweight_kg = body.kg
    db.commit()
    return {"day": row.day, "kg": float(row.kg)}


# ── One call the app makes on launch ─────────────────────────────────────────

@router.get("/bootstrap")
def bootstrap(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Everything the app needs at 3am, in a single round trip."""
    days = (db.query(DawnDay).filter(DawnDay.user_id == user.id)
              .order_by(DawnDay.day.desc()).limit(14).all())
    cands = (db.query(DawnCandidate)
               .filter(DawnCandidate.user_id == user.id, DawnCandidate.killed_at.is_(None))
               .order_by(DawnCandidate.id.desc()).all())
    _seed_plan(db, user)
    plan = db.query(DawnPlanItem).filter(DawnPlanItem.user_id == user.id).all()
    prof = _get_profile(db, user)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    meals = (db.query(DawnMeal)
               .filter(DawnMeal.user_id == user.id, DawnMeal.day == today).all())
    weights = (db.query(DawnWeight).filter(DawnWeight.user_id == user.id)
                 .order_by(DawnWeight.day.desc()).limit(30).all())
    return {
        "user": {"id": user.id, "name": getattr(user, "first_name", None) or user.email},
        "profile": _profile_out(prof),
        "plan": _plan_out(plan),
        "fuel_ideas": FUEL_IDEAS,
        "meals_today": [{"id": m.id, "slot": m.slot, "text": m.text,
                         "kcal": m.kcal, "protein_g": m.protein_g} for m in meals],
        "weights": [{"day": w.day, "kg": float(w.kg)} for w in weights],
        "days": [_day_out(d) for d in days],
        "last_sets": last_per_lift(db, user)["items"],
        "candidates": [_cand(c) for c in cands],
        "stages": STAGES,
    }
