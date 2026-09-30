"""TEHTEK — Dawn Block API, consumed by the Android app.

Every route is scoped to the authenticated user: no permission flag, because
this is personal data rather than company data — owning the account is the
authorisation.
"""
import json
import re
from datetime import date, datetime, timedelta

from contextvars import ContextVar

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.dawn.models import (
    DawnAccount, DawnBalance, DawnCandidate, DawnDay, DawnDayPlan, DawnLog,
    DawnMeal, DawnPlanItem, DawnProfile, DawnResearch, DawnSet, DawnTask,
    DawnTracker, DawnWeight,
)

router = APIRouter(prefix="/api/v1/dawn", tags=["dawn-block"])

# Benjamin's day runs 03:30–21:00 in New York; the server runs in UTC. Between
# 20:00 and midnight local the two calendars disagree, which is exactly when he
# sits down to plan tomorrow. So the client sends its own date and the server
# trusts it for anything day-shaped; UTC is only the fallback.
_LOCAL_DAY: ContextVar[str | None] = ContextVar("dawn_local_day", default=None)


async def use_local_day(x_local_date: str | None = Header(default=None)) -> None:
    """Router-wide dependency: pin this request to the caller's calendar day.

    Async on purpose. A sync dependency is run in a threadpool, and a ContextVar
    set inside that worker never reaches the endpoint — the copy only travels
    parent to child. Setting it in the request's own coroutine does reach the
    endpoint, threadpool or not.
    """
    if x_local_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x_local_date):
        _LOCAL_DAY.set(x_local_date)
    else:
        _LOCAL_DAY.set(None)


router.dependencies.append(Depends(use_local_day))

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
    weight:    float | None = Field(default=None, gt=0, le=2000)
    reps:      int | None = Field(default=None, ge=1, le=500)
    minutes:   int | None = Field(default=None, ge=1, le=600)


@router.get("/sets")
def list_sets(lift_id: str | None = Query(default=None), limit: int = Query(default=400, le=2000),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DawnSet).filter(DawnSet.user_id == user.id)
    if lift_id:
        q = q.filter(DawnSet.lift_id == lift_id)
    rows = q.order_by(DawnSet.id.desc()).limit(limit).all()
    return {"items": [{
        "id": r.id, "lift_id": r.lift_id, "lift_name": r.lift_name,
        "day": r.day,
        "weight": float(r.weight) if r.weight is not None else None,
        "reps": r.reps, "minutes": r.minutes,
        "created_at": r.created_at.isoformat(),
    } for r in reversed(rows)]}


@router.post("/sets", status_code=201)
def add_set(body: SetIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    has_lift = body.weight is not None and body.reps is not None
    if not has_lift and body.minutes is None:
        raise HTTPException(400, "Donnez un poids et des répétitions, ou une durée.")
    row = DawnSet(user_id=user.id, lift_id=body.lift_id, lift_name=body.lift_name,
                  day=body.day, weight=body.weight, reps=body.reps, minutes=body.minutes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "lift_id": row.lift_id, "day": row.day,
            "weight": float(row.weight) if row.weight is not None else None,
            "reps": row.reps, "minutes": row.minutes}


@router.get("/sets/last")
def last_per_lift(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The most recent set for every lift — what the app shows as 'beat this'."""
    rows = (db.query(DawnSet).filter(DawnSet.user_id == user.id)
              .order_by(DawnSet.id.desc()).limit(2000).all())
    best: dict[str, dict] = {}
    for r in rows:
        if r.lift_id not in best:
            best[r.lift_id] = {
                "day": r.day, "reps": r.reps, "minutes": r.minutes,
                "weight": float(r.weight) if r.weight is not None else None,
            }
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

    Calories land on the plan's 3,000–3,200 band at 90 kg and follow bodyweight
    from there, so the figures stay the ones the 30-day plan was written around.
    """
    bw = float(p.bodyweight_kg or 90)
    return {
        "protein_g": int(p.protein_target_g or round(bw * 2.0)),
        "kcal": int(p.kcal_target or round(bw * 32 + 220)),
        "protein_range": [170, 190],
        "kcal_range": [3000, 3200],
    }


class ProfileIn(BaseModel):
    bodyweight_kg:    float | None = Field(default=None, gt=20, le=400)
    goal_kg:          float | None = Field(default=None, gt=20, le=400)
    protein_target_g: int | None = Field(default=None, ge=0, le=600)
    kcal_target:      int | None = Field(default=None, ge=0, le=10000)
    day_start:        str | None = Field(default=None, max_length=5)
    day_end:          str | None = Field(default=None, max_length=5)
    slot_minutes:     int | None = Field(default=None, ge=5, le=120)


def _hhmm(v: str) -> str:
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", v.strip()):
        raise HTTPException(400, f"Time must be HH:MM, got {v!r}")
    return v.strip()


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
            "targets": _targets(p),
            "day_start": p.day_start or "03:30", "day_end": p.day_end or "21:00",
            "slot_minutes": int(p.slot_minutes or 30)}


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
    if body.day_start:    p.day_start = _hhmm(body.day_start)
    if body.day_end:      p.day_end = _hhmm(body.day_end)
    if body.slot_minutes: p.slot_minutes = body.slot_minutes
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

# ── The eating plan ──────────────────────────────────────────────────────────
# Slots follow the 30-day plan, but at the times the morning block actually
# runs: the plan assumed a 3:00–4:30 session, whereas training here is
# 4:45–5:50, so the pre-workout meal sits at 4:10 and the big breakfast at 6:15.

SLOT_ORDER = ["pre", "post", "snack_am", "lunch", "snack_pm", "dinner", "prebed"]
SLOT_LABELS = {
    "pre":      ("Pre-workout",    "4:10"),
    "post":     ("Post-workout breakfast", "6:15"),
    "snack_am": ("Morning snack",  "9:00"),
    "lunch":    ("Lunch",          "12:30"),
    "snack_pm": ("Afternoon snack", "16:00"),
    "dinner":   ("Dinner",         "19:00"),
    "prebed":   ("Pre-bed protein", "21:00"),
}

# Week 1 of the plan, which is the template the later weeks vary on.
# Keyed by weekday: the plan's Day 1 is Monday, and it lines up with training.
MEAL_PLAN = {
    1: {"pre": "Banana + 2 slices whole-grain toast + 1 tbsp peanut butter",
        "post": "4 eggs, oatmeal with whole milk, blueberries, Greek yogurt",
        "snack_am": "Apple + Greek yogurt + walnuts",
        "lunch": "Grilled chicken breast, rice, broccoli, avocado",
        "snack_pm": "Tuna on whole-grain bread + orange",
        "dinner": "Salmon, sweet potato, spinach",
        "prebed": "Cottage cheese + berries"},
    2: {"pre": "Banana + oatmeal with a little milk",
        "post": "4 eggs, whole-grain toast, avocado, Greek yogurt + berries",
        "snack_am": "Banana + almonds + milk",
        "lunch": "Chicken thighs, rice, black beans, vegetables",
        "snack_pm": "Turkey whole-grain sandwich + apple",
        "dinner": "Lean ground beef, baked potato, broccoli",
        "prebed": "Greek yogurt + 1 tbsp peanut butter"},
    3: {"post": "3 eggs, oatmeal, banana, Greek yogurt",
        "snack_am": "Apple + almonds",
        "lunch": "Chicken, brown rice, vegetables, avocado",
        "snack_pm": "Cottage cheese + berries",
        "dinner": "Salmon, sweet potato, salad",
        "prebed": "Greek yogurt"},
    4: {"pre": "Banana + whole-grain toast + peanut butter",
        "post": "4 eggs, oats + whole milk + banana, Greek yogurt",
        "snack_am": "Cottage cheese + pineapple",
        "lunch": "Turkey, rice, black beans, vegetables",
        "snack_pm": "Tuna sandwich + fruit",
        "dinner": "Chicken breast, potatoes, broccoli + olive oil",
        "prebed": "Greek yogurt + walnuts"},
    5: {"pre": "Banana + toast + peanut butter",
        "post": "4 eggs, large oatmeal + milk + berries, Greek yogurt",
        "snack_am": "Banana + almonds",
        "lunch": "Lean beef, rice, beans, vegetables",
        "snack_pm": "Turkey sandwich + fruit",
        "dinner": "Salmon, rice, spinach, avocado",
        "prebed": "Cottage cheese"},
    6: {"post": "Eggs, avocado toast, fruit, Greek yogurt",
        "snack_am": "Oats + milk + banana",
        "lunch": "Chicken, rice, broccoli",
        "snack_pm": "Apple + natural peanut butter",
        "dinner": "Lean beef, sweet potato, mixed vegetables",
        "prebed": "Greek yogurt"},
    0: {"post": "3 eggs, oatmeal, berries",
        "snack_am": "Greek yogurt + walnuts",
        "lunch": "Salmon, rice, vegetables",
        "snack_pm": "Cottage cheese + fruit",
        "dinner": "Chicken, potatoes, salad + avocado",
        "prebed": "Milk or Greek yogurt"},
}

SHOPPING = {
    "Protein": ["Eggs", "Chicken breast", "Chicken thighs", "90–93% lean ground beef",
                "Lean turkey", "Salmon", "Tuna in water", "Plain whole-milk Greek yogurt",
                "Cottage cheese", "Whole milk", "Black beans"],
    "Carbohydrates": ["Rolled oats", "Jasmine or brown rice", "Sweet potatoes",
                      "White/red potatoes", "100% whole-grain bread", "Quinoa"],
    "Fruit": ["Bananas", "Apples", "Oranges", "Berries", "Avocados"],
    "Vegetables": ["Broccoli", "Spinach", "Mixed frozen vegetables", "Green beans",
                   "Bell peppers", "Salad greens"],
    "Fats": ["Natural peanut butter", "Extra-virgin olive oil", "Almonds", "Walnuts"],
}

PROGRESS_RULES = [
    "Weigh in the same conditions and compare 7-day averages, never single days.",
    "0.25–0.5 kg a week is the pace. Faster is mostly fat.",
    "If the average has not moved for two weeks, add 150–250 kcal a day — rice, oats, milk, avocado or olive oil.",
    "If the waist is growing faster than the lifts, cut the portions back a little.",
    "Protein stays between 170 and 190 g a day.",
    "Sleep is where the muscle is actually built.",
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
    if body.slot not in SLOT_ORDER:
        raise HTTPException(400, f"Slot invalide. Attendu : {', '.join(SLOT_ORDER)}")
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
    today = _today()
    meals = (db.query(DawnMeal)
               .filter(DawnMeal.user_id == user.id, DawnMeal.day == today).all())
    weights = (db.query(DawnWeight).filter(DawnWeight.user_id == user.id)
                 .order_by(DawnWeight.day.desc()).limit(30).all())
    return {
        "user": {"id": user.id, "name": getattr(user, "first_name", None) or user.email},
        "profile": _profile_out(prof),
        "plan": _plan_out(plan),
        "meal_plan_today": MEAL_PLAN.get(int(datetime.utcnow().strftime("%w")), {}),
        "slot_order": SLOT_ORDER,
        "slot_labels": {k: {"label": v[0], "time": v[1]} for k, v in SLOT_LABELS.items()},
        "meals_today": [{"id": m.id, "slot": m.slot, "text": m.text,
                         "kcal": m.kcal, "protein_g": m.protein_g} for m in meals],
        "weights": [{"day": w.day, "kg": float(w.kg)} for w in weights],
        "days": [_day_out(d) for d in days],
        "last_sets": last_per_lift(db, user)["items"],
        "candidates": [_cand(c) for c in cands],
        "stages": STAGES,
    }


@router.get("/eating-plan")
def eating_plan(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The 30-day plan as reference: today's meals, the list, and the rules."""
    dow = int(datetime.utcnow().strftime("%w"))
    return {
        "today": MEAL_PLAN.get(dow, {}),
        "slot_order": SLOT_ORDER,
        "slot_labels": {k: {"label": v[0], "time": v[1]} for k, v in SLOT_LABELS.items()},
        "shopping": SHOPPING,
        "rules": PROGRESS_RULES,
        "targets": _targets(_get_profile(db, user)),
    }


# ── Tasks ────────────────────────────────────────────────────────────────────

KINDS = ("buy", "call", "do", "ads", "admin", "health")
REPEATS = ("none", "daily", "weekly")


class TaskIn(BaseModel):
    title:    str = Field(min_length=1, max_length=300)
    kind:     str = Field(default="do", max_length=20)
    due_date: str | None = Field(default=None, max_length=10)
    slot:     str | None = Field(default=None, max_length=5)   # HH:MM block
    slots:    int = Field(default=1, ge=1, le=48)
    repeat:   str = Field(default="none", max_length=10)
    priority: int = Field(default=1, ge=0, le=2)
    notes:    str | None = None


class TaskPatch(BaseModel):
    title:    str | None = Field(default=None, max_length=300)
    kind:     str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=10)
    slot:     str | None = Field(default=None, max_length=5)
    slots:    int | None = Field(default=None, ge=1, le=48)
    repeat:   str | None = Field(default=None, max_length=10)
    priority: int | None = Field(default=None, ge=0, le=2)
    notes:    str | None = None
    done:     bool | None = None


class TaskBulkIn(BaseModel):
    """A pasted list: one task per line, sharing a kind and a deadline."""
    titles:   list[str] = Field(min_length=1, max_length=200)
    kind:     str = Field(default="do", max_length=20)
    due_date: str | None = Field(default=None, max_length=10)
    repeat:   str = Field(default="none", max_length=10)
    priority: int = Field(default=1, ge=0, le=2)
    notes:    str | None = None


def _task_out(t: DawnTask) -> dict:
    today = _today()
    # A repeating task is "done" only for the day it was last ticked.
    done = (t.last_done == today) if t.repeat != "none" else (t.done_at is not None)
    return {
        "id": t.id, "title": t.title, "kind": t.kind, "due_date": t.due_date,
        "repeat": t.repeat, "priority": t.priority, "notes": t.notes,
        "done": done,
        "overdue": bool(t.due_date and t.due_date < today and not done),
        "unplanned": bool(t.unplanned),
        "slot": t.slot, "slots": int(t.slots or 1),
    }


@router.get("/tasks")
def list_tasks(include_done: bool = Query(default=False),
               kind: str | None = Query(default=None),
               day: str | None = Query(default=None),
               since: str | None = Query(default=None),
               until: str | None = Query(default=None),
               overdue: bool = Query(default=False),
               undated: bool = Query(default=False),
               q: str | None = Query(default=None),
               limit: int = Query(default=500, ge=1, le=1000),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The whole list, filtered. Every filter is optional and they combine.

    `kind` takes one or several ("do,call"). `day` pins a single date, while
    `since`/`until` bound a range; `overdue` and `undated` are shorthands for
    the two questions the phone asks most often.
    """
    today = _today()
    rows = db.query(DawnTask).filter(DawnTask.user_id == user.id)
    if not include_done:
        # Repeating tasks always stay on the list; one-offs drop off once done.
        rows = rows.filter((DawnTask.done_at.is_(None)) | (DawnTask.repeat != "none"))

    if kind:
        kinds = [k.strip() for k in kind.split(",") if k.strip()]
        unknown = [k for k in kinds if k not in KINDS]
        if unknown:
            raise HTTPException(400, f"Unknown kind: {', '.join(unknown)}")
        if kinds:
            rows = rows.filter(DawnTask.kind.in_(kinds))

    # Undated and dated are exclusive: asking for both would return nothing, so
    # `undated` wins and the range filters are skipped.
    if undated:
        rows = rows.filter(DawnTask.due_date.is_(None))
    elif day:
        rows = rows.filter(DawnTask.due_date == day)
    else:
        if since:
            rows = rows.filter(DawnTask.due_date >= since)
        if until:
            rows = rows.filter(DawnTask.due_date <= until)
        if overdue:
            rows = rows.filter(DawnTask.due_date.isnot(None), DawnTask.due_date < today)

    if q:
        like = f"%{q.strip()}%"
        rows = rows.filter(or_(DawnTask.title.ilike(like), DawnTask.notes.ilike(like)))

    rows = rows.order_by(DawnTask.priority.asc(),
                         DawnTask.due_date.asc().nullslast(),
                         DawnTask.id.desc()).limit(limit).all()
    items = [_task_out(t) for t in rows]
    # For a repeating task "done" is per-day and computed in _task_out, so an
    # overdue filter can only be honoured once the rows are serialised.
    if overdue:
        items = [i for i in items if i["overdue"]]
    return {"items": items, "kinds": list(KINDS), "count": len(items)}


@router.post("/tasks", status_code=201)
def add_task(body: TaskIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if body.kind not in KINDS:
        raise HTTPException(400, f"Kind must be one of: {', '.join(KINDS)}")
    if body.repeat not in REPEATS:
        raise HTTPException(400, f"Repeat must be one of: {', '.join(REPEATS)}")
    due = body.due_date or None
    t = DawnTask(user_id=user.id, title=body.title.strip(), kind=body.kind,
                 due_date=due, repeat=body.repeat,
                 slot=_hhmm(body.slot) if body.slot else None, slots=body.slots,
                 priority=body.priority, notes=body.notes,
                 unplanned=1 if _is_improvised(db, user, due) else 0)
    db.add(t); db.commit(); db.refresh(t)
    return _task_out(t)


@router.post("/tasks/bulk", status_code=201)
def add_tasks_bulk(body: TaskBulkIn,
                   db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Create many at once — a brain-dump arrives as one request, not twenty.

    Blank lines are dropped rather than rejected, because the list is pasted and
    trailing newlines are normal.
    """
    if body.kind not in KINDS:
        raise HTTPException(400, f"Kind must be one of: {', '.join(KINDS)}")
    if body.repeat not in REPEATS:
        raise HTTPException(400, f"Repeat must be one of: {', '.join(REPEATS)}")

    titles = [t.strip()[:300] for t in body.titles if t and t.strip()]
    if not titles:
        raise HTTPException(400, "Nothing to add")

    due = body.due_date or None
    unplanned = 1 if _is_improvised(db, user, due) else 0
    made = [DawnTask(user_id=user.id, title=title, kind=body.kind, due_date=due,
                     repeat=body.repeat, priority=body.priority, notes=body.notes,
                     unplanned=unplanned)
            for title in titles]
    db.add_all(made); db.commit()
    for t in made:
        db.refresh(t)
    return {"items": [_task_out(t) for t in made], "count": len(made)}


def _own_task(db: Session, user, tid: int) -> DawnTask:
    t = db.query(DawnTask).filter(DawnTask.id == tid, DawnTask.user_id == user.id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@router.patch("/tasks/{tid}")
def patch_task(tid: int, body: TaskPatch,
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = _own_task(db, user, tid)
    if body.title:              t.title = body.title.strip()
    if body.kind:               t.kind = body.kind
    if body.repeat:             t.repeat = body.repeat
    if body.priority is not None: t.priority = body.priority
    if body.notes is not None:  t.notes = body.notes
    if body.due_date is not None: t.due_date = body.due_date or None
    if body.slot is not None:     t.slot = _hhmm(body.slot) if body.slot else None
    if body.slots is not None:    t.slots = body.slots
    if body.done is not None:
        today = _today()
        if t.repeat != "none":
            # Repeating: tick for today, untick clears today only.
            t.last_done = today if body.done else None
        else:
            t.done_at = datetime.utcnow() if body.done else None
    db.commit(); db.refresh(t)
    return _task_out(t)


@router.delete("/tasks/{tid}", status_code=204)
def delete_task(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.delete(_own_task(db, user, tid)); db.commit()


# ── Plan the day before ──────────────────────────────────────────────────────
#
# The rule Benjamin set for himself: the day is built the evening before, and
# nothing new gets invented once it starts. The API does not block same-day
# additions — it marks them unplanned and counts them, so the habit shows up as
# a number instead of a feeling.

def _today() -> str:
    return _LOCAL_DAY.get() or date.today().isoformat()


def _tomorrow() -> str:
    return (date.fromisoformat(_today()) + timedelta(days=1)).isoformat()


def _plan_row(db: Session, user, day: str, create: bool = False) -> DawnDayPlan | None:
    p = (db.query(DawnDayPlan)
           .filter(DawnDayPlan.user_id == user.id, DawnDayPlan.day == day).first())
    if p is None and create:
        p = DawnDayPlan(user_id=user.id, day=day)
        db.add(p); db.commit(); db.refresh(p)
    return p


def _is_improvised(db: Session, user, due: str | None) -> bool:
    """True when a task is being added to a day that is already under way and locked."""
    if not due or due != _today():
        return False
    p = _plan_row(db, user, due)
    return bool(p and p.locked_at)


def _done_on(t: DawnTask, day: str) -> bool:
    return (t.last_done == day) if t.repeat != "none" else (t.done_at is not None)


def _day_tasks(db: Session, user, day: str) -> list[DawnTask]:
    rows = (db.query(DawnTask)
              .filter(DawnTask.user_id == user.id,
                      (DawnTask.due_date == day) | (DawnTask.repeat != "none"))
              .order_by(DawnTask.priority.asc(), DawnTask.id.asc()).all())
    # An overdue one-off still belongs on today's list, or it disappears.
    if day == _today():
        late = (db.query(DawnTask)
                  .filter(DawnTask.user_id == user.id, DawnTask.repeat == "none",
                          DawnTask.done_at.is_(None), DawnTask.due_date.isnot(None),
                          DawnTask.due_date < day)
                  .order_by(DawnTask.due_date.asc()).all())
        seen = {t.id for t in rows}
        rows += [t for t in late if t.id not in seen]
    return rows


class DayPlanIn(BaseModel):
    day:       str = Field(min_length=10, max_length=10)
    intention: str | None = Field(default=None, max_length=2000)
    review:    str | None = Field(default=None, max_length=4000)
    locked:    bool | None = None


def _slot_list(start: str, end: str, minutes: int) -> list[str]:
    """Every block of the day: 03:30 → 21:00 by 30 gives 35 blocks, 03:30…20:30.

    The end time is when the day is over, not the start of one more block, so
    the last slot is the one that *finishes* at `end`.
    """
    def mins(v: str) -> int:
        h, m = v.split(":")
        return int(h) * 60 + int(m)
    a, b, out = mins(start), mins(end), []
    while a + minutes <= b:
        out.append(f"{a // 60:02d}:{a % 60:02d}")
        a += minutes
    return out


# The fixed points of Benjamin's day. Everything else is his to fill in the
# evening — the app anchors the routine, it does not invent the working hours.
DAY_ANCHORS: list[tuple[str, int, str, str]] = [
    ("03:30", 1, "Wake — water, no phone",        "health"),
    ("04:00", 2, "Product research",              "work"),
    ("05:00", 1, "Pre-workout food",              "health"),
    ("05:30", 3, "Gym — Planet Fitness",          "health"),
    ("07:00", 1, "Post-workout breakfast",        "health"),
    ("09:00", 1, "Snack",                         "health"),
    ("12:30", 1, "Lunch",                         "health"),
    ("16:00", 1, "Snack",                         "health"),
    ("19:00", 1, "Dinner",                        "health"),
    ("20:30", 1, "Plan tomorrow — lock the day",  "admin"),
]


def _grid(db: Session, user, day: str, tasks: list[dict]) -> dict:
    p = _get_profile(db, user)
    slots = _slot_list(p.day_start or "03:30", p.day_end or "21:00",
                       int(p.slot_minutes or 30))
    placed: dict[str, list[dict]] = {s: [] for s in slots}
    unscheduled = []
    for t in tasks:
        if t["slot"] in placed:
            placed[t["slot"]].append(t)
        else:
            unscheduled.append(t)
    rows = [{"slot": s, "tasks": placed[s]} for s in slots]
    return {
        "slots": slots, "rows": rows, "unscheduled": unscheduled,
        "slot_minutes": int(p.slot_minutes or 30),
        "day_start": p.day_start or "03:30", "day_end": p.day_end or "21:00",
        "free_slots": len([s for s in slots if not placed[s]]),
        "filled_slots": len([s for s in slots if placed[s]]),
    }


def _dayplan_out(db: Session, user, day: str) -> dict:
    p = _plan_row(db, user, day)
    tasks = [_task_out(t) for t in _day_tasks(db, user, day)]
    return {
        "day": day,
        "grid": _grid(db, user, day, tasks),
        "is_today": day == _today(),
        "is_tomorrow": day == _tomorrow(),
        "locked": bool(p and p.locked_at),
        "locked_at": p.locked_at.isoformat() if (p and p.locked_at) else None,
        "intention": p.intention if p else None,
        "review": p.review if p else None,
        "tasks": tasks,
        "scheduled_count": len([t for t in tasks if t["slot"]]),
        "planned_count": len([t for t in tasks if not t["unplanned"]]),
        "unplanned_count": len([t for t in tasks if t["unplanned"]]),
        "done_count": len([t for t in tasks if t["done"]]),
    }


@router.get("/day-plan")
def get_day_plan(day: str | None = Query(default=None),
                 db: Session = Depends(get_db), user=Depends(get_current_user)):
    """The plan for one day. Defaults to tomorrow, because that is the one you edit."""
    return _dayplan_out(db, user, day or _tomorrow())


@router.put("/day-plan")
def put_day_plan(body: DayPlanIn, db: Session = Depends(get_db),
                 user=Depends(get_current_user)):
    p = _plan_row(db, user, body.day, create=True)
    if body.intention is not None: p.intention = body.intention.strip() or None
    if body.review is not None:    p.review = body.review.strip() or None
    if body.locked is not None:
        p.locked_at = datetime.utcnow() if body.locked else None
    db.commit()
    return _dayplan_out(db, user, body.day)


def _discipline(db: Session, user, days: int = 14) -> dict:
    """How well the plan-the-night-before habit is holding, day by day."""
    out, planned_ahead, improvised = [], 0, 0
    base = date.fromisoformat(_today())
    for i in range(days):
        d = (base - timedelta(days=i)).isoformat()
        p = _plan_row(db, user, d)
        tasks = _day_tasks(db, user, d)
        n_un = len([t for t in tasks if t.unplanned])
        # Planned ahead means the plan was locked before that day began.
        ahead = bool(p and p.locked_at and p.locked_at.date().isoformat() < d)
        if ahead: planned_ahead += 1
        improvised += n_un
        out.append({"day": d, "planned_ahead": ahead, "locked": bool(p and p.locked_at),
                    "tasks": len(tasks), "unplanned": n_un,
                    "done": len([t for t in tasks if _done_on(t, d)])})
    return {"days": out, "planned_ahead": planned_ahead, "window": days,
            "unplanned_total": improvised}


@router.get("/day-plan/discipline")
def discipline(days: int = Query(default=14, ge=1, le=90),
               db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _discipline(db, user, days)


# ── Trackers: anything worth counting once a day ─────────────────────────────
#
# One table instead of one feature per habit. Money in and money saved are the
# two seeded with targets, because a daily minimum is the whole point of them;
# the rest are whatever Benjamin decides to count, private ones included.

SHAPES = ("amount", "count", "minutes", "yesno", "scale", "note")
GROUPS = ("money", "body", "work", "life")
DIRECTIONS = ("floor", "ceiling")

SEED_TRACKERS = [
    # name,               shape,     unit,  target, direction, group,   private
    ("Money in",          "amount",  "USD",   50,   "floor",   "money", 0),
    ("Saved",             "amount",  "USD",   20,   "floor",   "money", 0),
    ("Spent",             "amount",  "USD",   30,   "ceiling", "money", 0),
    ("Water",             "amount",  "L",      3,   "floor",   "body",  0),
    ("Protein shake",     "count",   None,     2,   "floor",   "body",  0),
    ("Vitamins",          "yesno",   None,     1,   "floor",   "body",  0),
    ("Ads posted",        "count",   None,     5,   "floor",   "work",  0),
    ("Product research",  "minutes", "min",   60,   "floor",   "work",  0),
    ("Sleep",             "minutes", "min",  420,   "floor",   "body",  0),
    ("Mood",              "scale",   None,   None,  "floor",   "life",  0),
]


def _seed_trackers(db: Session, user) -> None:
    n = db.query(DawnTracker).filter(DawnTracker.user_id == user.id).count()
    if n:
        return
    for i, (name, shape, unit, target, direction, group, private) in enumerate(SEED_TRACKERS):
        db.add(DawnTracker(user_id=user.id, name=name, shape=shape, unit=unit,
                           target=target, direction=direction, group=group,
                           private=private, position=i))
    db.commit()


class TrackerIn(BaseModel):
    name:      str = Field(min_length=1, max_length=80)
    shape:     str = Field(default="count", max_length=10)
    unit:      str | None = Field(default=None, max_length=20)
    target:    float | None = Field(default=None, ge=0)
    direction: str = Field(default="floor", max_length=8)
    group:     str = Field(default="life", max_length=20)
    private:   bool = False


class TrackerPatch(BaseModel):
    name:      str | None = Field(default=None, max_length=80)
    unit:      str | None = Field(default=None, max_length=20)
    target:    float | None = Field(default=None, ge=0)
    direction: str | None = Field(default=None, max_length=8)
    group:     str | None = Field(default=None, max_length=20)
    private:   bool | None = None
    archived:  bool | None = None


def _num(v) -> float | None:
    return None if v is None else float(v)


def _hit(shape: str, direction: str, value, target) -> bool | None:
    """Did this day meet the tracker's daily minimum (or stay under its ceiling)?"""
    if target is None or value is None:
        return None
    return value <= target if direction == "ceiling" else value >= target


def _tracker_out(t: DawnTracker, logs: dict[int, DawnLog], day: str,
                 streak: int = 0, week: float | None = None) -> dict:
    log = logs.get(t.id)
    value = _num(log.value) if log else None
    return {
        "id": t.id, "name": t.name, "shape": t.shape, "unit": t.unit,
        "target": _num(t.target), "direction": t.direction, "group": t.group,
        "private": bool(t.private), "archived": bool(t.archived),
        "day": day, "value": value, "planned": _num(log.planned) if log else None,
        "note": log.note if log else None,
        "hit": _hit(t.shape, t.direction, value, _num(t.target)),
        "streak": streak, "week_total": week,
    }


def _logs_for(db: Session, user, day: str) -> dict[int, DawnLog]:
    rows = db.query(DawnLog).filter(DawnLog.user_id == user.id, DawnLog.day == day).all()
    return {r.tracker_id: r for r in rows}


def _streaks(db: Session, user, trackers: list[DawnTracker],
             day: str, back: int = 60) -> tuple[dict[int, int], dict[int, float]]:
    """Consecutive days a target was met, counting back from `day`, plus 7-day totals."""
    days = [(date.fromisoformat(day) - timedelta(days=i)).isoformat() for i in range(back)]
    rows = (db.query(DawnLog)
              .filter(DawnLog.user_id == user.id, DawnLog.day.in_(days)).all())
    by: dict[int, dict[str, float | None]] = {}
    for r in rows:
        by.setdefault(r.tracker_id, {})[r.day] = _num(r.value)

    streak, week = {}, {}
    for t in trackers:
        vals = by.get(t.id, {})
        week[t.id] = round(sum(v for d, v in vals.items()
                               if v is not None and d in days[:7]), 2)
        target = _num(t.target)
        if target is None:
            streak[t.id] = 0
            continue
        n = 0
        for d in days:
            if _hit(t.shape, t.direction, vals.get(d), target):
                n += 1
            else:
                # Today not yet logged should not break a streak that is still alive.
                if d == day and vals.get(d) is None:
                    continue
                break
        streak[t.id] = n
    return streak, week


def _trackers_payload(db: Session, user, day: str | None = None,
                      include_archived: bool = False) -> dict:
    _seed_trackers(db, user)
    d = day or _today()
    q = db.query(DawnTracker).filter(DawnTracker.user_id == user.id)
    if not include_archived:
        q = q.filter(DawnTracker.archived == 0)
    rows = q.order_by(DawnTracker.position.asc(), DawnTracker.id.asc()).all()
    logs = _logs_for(db, user, d)
    streak, week = _streaks(db, user, rows, d)
    items = [_tracker_out(t, logs, d, streak.get(t.id, 0), week.get(t.id)) for t in rows]
    money = [i for i in items if i["group"] == "money"]
    return {
        "day": d, "items": items,
        "shapes": list(SHAPES), "groups": list(GROUPS),
        "money_today": {m["name"]: m["value"] for m in money},
        "missed": [i["name"] for i in items
                   if i["target"] is not None and i["hit"] is not True and not i["private"]],
    }


@router.get("/trackers")
def list_trackers(day: str | None = Query(default=None),
                  include_archived: bool = Query(default=False),
                  db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _trackers_payload(db, user, day, include_archived)


@router.post("/trackers", status_code=201)
def add_tracker(body: TrackerIn, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    if body.shape not in SHAPES:
        raise HTTPException(400, f"Shape must be one of: {', '.join(SHAPES)}")
    if body.direction not in DIRECTIONS:
        raise HTTPException(400, f"Direction must be one of: {', '.join(DIRECTIONS)}")
    last = (db.query(DawnTracker).filter(DawnTracker.user_id == user.id)
              .order_by(DawnTracker.position.desc()).first())
    t = DawnTracker(user_id=user.id, name=body.name.strip(), shape=body.shape,
                    unit=(body.unit or None), target=body.target,
                    direction=body.direction,
                    group=body.group if body.group in GROUPS else "life",
                    private=1 if body.private else 0,
                    position=(last.position + 1) if last else 0)
    db.add(t); db.commit(); db.refresh(t)
    return _tracker_out(t, {}, _today())


def _own_tracker(db: Session, user, tid: int) -> DawnTracker:
    t = (db.query(DawnTracker)
           .filter(DawnTracker.id == tid, DawnTracker.user_id == user.id).first())
    if not t:
        raise HTTPException(404, "Tracker not found")
    return t


@router.patch("/trackers/{tid}")
def patch_tracker(tid: int, body: TrackerPatch, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    t = _own_tracker(db, user, tid)
    if body.name:      t.name = body.name.strip()
    if body.unit is not None: t.unit = body.unit or None
    if body.target is not None: t.target = body.target or None
    if body.direction in DIRECTIONS: t.direction = body.direction
    if body.group in GROUPS: t.group = body.group
    if body.private is not None:  t.private = 1 if body.private else 0
    if body.archived is not None: t.archived = 1 if body.archived else 0
    db.commit(); db.refresh(t)
    d = _today()
    return _tracker_out(t, _logs_for(db, user, d), d)


@router.delete("/trackers/{tid}", status_code=204)
def delete_tracker(tid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = _own_tracker(db, user, tid)
    db.query(DawnLog).filter(DawnLog.user_id == user.id,
                             DawnLog.tracker_id == t.id).delete()
    db.delete(t); db.commit()


class LogIn(BaseModel):
    tracker_id: int
    day:     str | None = Field(default=None, max_length=10)
    value:   float | None = Field(default=None, ge=0)
    planned: float | None = Field(default=None, ge=0)
    note:    str | None = Field(default=None, max_length=2000)
    # Without this, sending only `planned` would wipe the logged value.
    set_value: bool = True


@router.put("/logs")
def upsert_log(body: LogIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = _own_tracker(db, user, body.tracker_id)
    d = body.day or _today()
    row = (db.query(DawnLog)
             .filter(DawnLog.user_id == user.id, DawnLog.tracker_id == t.id,
                     DawnLog.day == d).first())
    if row is None:
        row = DawnLog(user_id=user.id, tracker_id=t.id, day=d)
        db.add(row)
    if body.set_value:
        row.value = body.value
    if body.planned is not None:
        row.planned = body.planned or None
    if body.note is not None:
        row.note = body.note.strip() or None
    db.commit()
    streak, week = _streaks(db, user, [t], d)
    return _tracker_out(t, {t.id: row}, d, streak.get(t.id, 0), week.get(t.id))


@router.get("/logs")
def list_logs(tracker_id: int | None = Query(default=None),
              days: int = Query(default=30, ge=1, le=365),
              db: Session = Depends(get_db), user=Depends(get_current_user)):
    since = (date.fromisoformat(_today()) - timedelta(days=days)).isoformat()
    q = db.query(DawnLog).filter(DawnLog.user_id == user.id, DawnLog.day >= since)
    if tracker_id:
        q = q.filter(DawnLog.tracker_id == tracker_id)
    rows = q.order_by(DawnLog.day.desc()).all()
    return {"items": [{"id": r.id, "tracker_id": r.tracker_id, "day": r.day,
                       "value": _num(r.value), "note": r.note} for r in rows]}


@router.get("/money")
def money(days: int = Query(default=30, ge=1, le=365),
          db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Income and savings against their daily minimums — the two that must never be zero."""
    _seed_trackers(db, user)
    rows = (db.query(DawnTracker)
              .filter(DawnTracker.user_id == user.id, DawnTracker.group == "money",
                      DawnTracker.archived == 0)
              .order_by(DawnTracker.position.asc()).all())
    if not rows:
        return {"items": [], "days": []}
    since = (date.fromisoformat(_today()) - timedelta(days=days - 1)).isoformat()
    logs = (db.query(DawnLog)
              .filter(DawnLog.user_id == user.id, DawnLog.day >= since,
                      DawnLog.tracker_id.in_([t.id for t in rows])).all())
    by: dict[int, dict[str, float | None]] = {}
    for r in logs:
        by.setdefault(r.tracker_id, {})[r.day] = _num(r.value)

    d = _today()
    streak, week = _streaks(db, user, rows, d)
    items = []
    for t in rows:
        vals = by.get(t.id, {})
        got = [v for v in vals.values() if v is not None]
        target = _num(t.target)
        items.append({
            "id": t.id, "name": t.name, "unit": t.unit, "target": target,
            "today": vals.get(d), "hit_today": _hit(t.shape, t.direction, vals.get(d), target),
            "streak": streak.get(t.id, 0),
            "total": round(sum(got), 2), "days_logged": len(got),
            "days_hit": len([v for v in got if _hit(t.shape, t.direction, v, target)]),
            "expected": round(target * days, 2) if target else None,
            "week_total": week.get(t.id),
        })
    base_day = date.fromisoformat(_today())
    days_list = [(base_day - timedelta(days=i)).isoformat() for i in range(days)]
    return {"window": days, "items": items,
            "days": [{"day": x, **{str(t.id): by.get(t.id, {}).get(x) for t in rows}}
                     for x in days_list]}


class BuildDayIn(BaseModel):
    day:   str | None = Field(default=None, max_length=10)
    reset: bool = False   # clear existing anchors first


@router.post("/day-plan/build")
def build_day(body: BuildDayIn, db: Session = Depends(get_db),
              user=Depends(get_current_user)):
    """Lay the standing routine onto a day, so only the free blocks need thought.

    Idempotent: an anchor already sitting in its slot is left alone, so this can
    be run again after the day has been partly filled in.
    """
    day = body.day or _tomorrow()
    existing = {(t.slot, t.title): t for t in _day_tasks(db, user, day) if t.slot}
    if body.reset:
        for (slot, title), t in list(existing.items()):
            if any(title == a[2] for a in DAY_ANCHORS) and not _done_on(t, day):
                db.delete(t)
        db.commit()
        existing = {}
    added = 0
    for slot, span, title, kind in DAY_ANCHORS:
        if (slot, title) in existing:
            continue
        db.add(DawnTask(user_id=user.id, title=title, kind=kind, due_date=day,
                        slot=slot, slots=span, repeat="none", priority=1))
        added += 1
    db.commit()
    out = _dayplan_out(db, user, day)
    out["added"] = added
    return out


def _money_payload(db: Session, user, day: str | None = None) -> dict:
    """Planned vs actual earning, spending and saving for one day.

    `net` is what actually stayed: money in minus money out. It is the number
    that decides whether the day paid for itself.
    """
    _seed_trackers(db, user)
    d = day or _today()
    rows = (db.query(DawnTracker)
              .filter(DawnTracker.user_id == user.id, DawnTracker.group == "money",
                      DawnTracker.archived == 0)
              .order_by(DawnTracker.position.asc()).all())
    logs = _logs_for(db, user, d)
    streak, week = _streaks(db, user, rows, d)
    items = [_tracker_out(t, logs, d, streak.get(t.id, 0), week.get(t.id)) for t in rows]

    def pick(name: str, key: str):
        for i in items:
            if i["name"].lower() == name:
                return i[key]
        return None

    earned, spent = pick("money in", "value"), pick("spent", "value")
    p_earn, p_spend = pick("money in", "planned"), pick("spent", "planned")
    return {
        "day": d, "items": items,
        "net": None if earned is None and spent is None
               else round((earned or 0) - (spent or 0), 2),
        "net_planned": None if p_earn is None and p_spend is None
                       else round((p_earn or 0) - (p_spend or 0), 2),
        "saved": pick("saved", "value"),
        "saved_target": pick("saved", "target"),
        "minimums_met": all(i["hit"] is True for i in items if i["target"] is not None),
    }


@router.get("/money/plan")
def money_plan(day: str | None = Query(default=None), db: Session = Depends(get_db),
               user=Depends(get_current_user)):
    return _money_payload(db, user, day)


class MoneyPlanIn(BaseModel):
    day:     str | None = Field(default=None, max_length=10)
    earn:    float | None = Field(default=None, ge=0)
    spend:   float | None = Field(default=None, ge=0)
    save:    float | None = Field(default=None, ge=0)


@router.put("/money/plan")
def put_money_plan(body: MoneyPlanIn, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    """Set tomorrow's money plan in one call: what comes in, goes out, and stays."""
    _seed_trackers(db, user)
    d = body.day or _tomorrow()
    wanted = {"money in": body.earn, "spent": body.spend, "saved": body.save}
    rows = (db.query(DawnTracker)
              .filter(DawnTracker.user_id == user.id, DawnTracker.group == "money",
                      DawnTracker.archived == 0).all())
    for t in rows:
        amount = wanted.get(t.name.lower())
        if amount is None:
            continue
        row = (db.query(DawnLog)
                 .filter(DawnLog.user_id == user.id, DawnLog.tracker_id == t.id,
                         DawnLog.day == d).first())
        if row is None:
            row = DawnLog(user_id=user.id, tracker_id=t.id, day=d)
            db.add(row)
        row.planned = amount or None
    db.commit()
    return _money_payload(db, user, d)


@router.get("/today")
def today(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """One call for the whole day: the timetable, the trackers, the money, the gaps."""
    _seed_trackers(db, user)
    d = _today()
    plan = _dayplan_out(db, user, d)
    tomorrow = _dayplan_out(db, user, _tomorrow())
    trackers = _trackers_payload(db, user, d)
    return {
        "day": d,
        "plan": plan,
        "money": _money_payload(db, user, d),
        "trackers": trackers["items"],
        "missed": trackers["missed"],
        "tomorrow": {"day": tomorrow["day"], "locked": tomorrow["locked"],
                     "tasks": len(tomorrow["tasks"]),
                     "free_slots": tomorrow["grid"]["free_slots"],
                     "intention": tomorrow["intention"]},
        "accounts": _accounts_payload(db, user)["items"],
        # The nudge: the evening block exists so tomorrow is never improvised.
        "needs_planning": not tomorrow["locked"],
    }


# ── The three accounts ───────────────────────────────────────────────────────
#
# Benjamin's stated goals, in his own terms: a billion XAF in the Cameroon
# business account, a million USD at United Bank, a hundred thousand personal in
# Canada. He said "how, I don't know" — so these routes answer exactly that:
# given a target, a balance and a deadline, what has to land per day and per
# month. A goal without a rate is a wish; with a rate it is a number to beat.

SEED_ACCOUNTS = [
    # name,                       bank,           country,    ccy,  target,        kind
    ("Business account Cameroon", None,           "Cameroon", "XAF", 1_000_000_000, "business"),
    ("Business account USA",      "United Bank",  "USA",      "USD",     1_000_000, "business"),
    ("Personal account Canada",   None,           "Canada",   "CAD",       100_000, "personal"),
]


def _seed_accounts(db: Session, user) -> None:
    if db.query(DawnAccount).filter(DawnAccount.user_id == user.id).count():
        return
    for i, (name, bank, country, ccy, target, kind) in enumerate(SEED_ACCOUNTS):
        db.add(DawnAccount(user_id=user.id, name=name, bank=bank, country=country,
                           currency=ccy, target=target, balance=0, kind=kind,
                           position=i))
    db.commit()


def _money(v) -> float:
    return float(v or 0)


def _account_out(a: DawnAccount) -> dict:
    target, balance = _money(a.target), _money(a.balance)
    remaining = max(target - balance, 0)
    days_left = None
    if a.deadline:
        days_left = (date.fromisoformat(a.deadline) - date.fromisoformat(_today())).days
    per_day = per_month = None
    if days_left and days_left > 0:
        per_day = round(remaining / days_left, 2)
        per_month = round(remaining / (days_left / 30.44), 2)
    return {
        "id": a.id, "name": a.name, "bank": a.bank, "country": a.country,
        "currency": a.currency, "kind": a.kind,
        "target": target, "balance": balance, "remaining": remaining,
        "progress": round(balance / target * 100, 2) if target else 0.0,
        "deadline": a.deadline, "days_left": days_left,
        "per_day": per_day, "per_month": per_month,
        # Without a deadline there is no rate, and the goal stays a wish.
        "needs_deadline": a.deadline is None,
        "archived": bool(a.archived),
    }


class AccountIn(BaseModel):
    name:     str = Field(min_length=1, max_length=120)
    bank:     str | None = Field(default=None, max_length=120)
    country:  str | None = Field(default=None, max_length=60)
    currency: str = Field(default="USD", max_length=6)
    target:   float = Field(gt=0)
    balance:  float = Field(default=0, ge=0)
    deadline: str | None = Field(default=None, max_length=10)
    kind:     str = Field(default="business", max_length=12)


class AccountPatch(BaseModel):
    name:     str | None = Field(default=None, max_length=120)
    bank:     str | None = Field(default=None, max_length=120)
    country:  str | None = Field(default=None, max_length=60)
    currency: str | None = Field(default=None, max_length=6)
    target:   float | None = Field(default=None, gt=0)
    balance:  float | None = Field(default=None, ge=0)
    deadline: str | None = Field(default=None, max_length=10)
    archived: bool | None = None


def _accounts_payload(db: Session, user) -> dict:
    _seed_accounts(db, user)
    rows = (db.query(DawnAccount)
              .filter(DawnAccount.user_id == user.id, DawnAccount.archived == 0)
              .order_by(DawnAccount.position.asc(), DawnAccount.id.asc()).all())
    items = [_account_out(a) for a in rows]
    return {"items": items,
            "needs_deadline": [i["name"] for i in items if i["needs_deadline"]]}


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _accounts_payload(db, user)


@router.post("/accounts", status_code=201)
def add_account(body: AccountIn, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    last = (db.query(DawnAccount).filter(DawnAccount.user_id == user.id)
              .order_by(DawnAccount.position.desc()).first())
    a = DawnAccount(user_id=user.id, name=body.name.strip(), bank=body.bank,
                    country=body.country, currency=body.currency.upper(),
                    target=body.target, balance=body.balance,
                    deadline=body.deadline or None, kind=body.kind,
                    position=(last.position + 1) if last else 0)
    db.add(a); db.commit(); db.refresh(a)
    return _account_out(a)


def _own_account(db: Session, user, aid: int) -> DawnAccount:
    a = (db.query(DawnAccount)
           .filter(DawnAccount.id == aid, DawnAccount.user_id == user.id).first())
    if not a:
        raise HTTPException(404, "Account not found")
    return a


@router.patch("/accounts/{aid}")
def patch_account(aid: int, body: AccountPatch, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    a = _own_account(db, user, aid)
    if body.name:     a.name = body.name.strip()
    if body.bank is not None:    a.bank = body.bank or None
    if body.country is not None: a.country = body.country or None
    if body.currency: a.currency = body.currency.upper()
    if body.target is not None:  a.target = body.target
    if body.deadline is not None: a.deadline = body.deadline or None
    if body.archived is not None: a.archived = 1 if body.archived else 0
    if body.balance is not None:
        a.balance = body.balance
        # Every balance change is also a dated reading, so the curve is real.
        d = _today()
        row = (db.query(DawnBalance)
                 .filter(DawnBalance.user_id == user.id, DawnBalance.account_id == a.id,
                         DawnBalance.day == d).first())
        if row is None:
            row = DawnBalance(user_id=user.id, account_id=a.id, day=d, amount=body.balance)
            db.add(row)
        else:
            row.amount = body.balance
    db.commit(); db.refresh(a)
    return _account_out(a)


@router.delete("/accounts/{aid}", status_code=204)
def delete_account(aid: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    a = _own_account(db, user, aid)
    db.query(DawnBalance).filter(DawnBalance.user_id == user.id,
                                 DawnBalance.account_id == a.id).delete()
    db.delete(a); db.commit()


@router.get("/accounts/{aid}/history")
def account_history(aid: int, days: int = Query(default=180, ge=7, le=3650),
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    a = _own_account(db, user, aid)
    since = (date.fromisoformat(_today()) - timedelta(days=days)).isoformat()
    rows = (db.query(DawnBalance)
              .filter(DawnBalance.user_id == user.id, DawnBalance.account_id == a.id,
                      DawnBalance.day >= since)
              .order_by(DawnBalance.day.asc()).all())
    pts = [{"day": r.day, "amount": _money(r.amount)} for r in rows]
    # Growth per day measured over the readings themselves, not assumed.
    rate = None
    if len(pts) >= 2:
        span = (date.fromisoformat(pts[-1]["day"]) - date.fromisoformat(pts[0]["day"])).days
        if span > 0:
            rate = round((pts[-1]["amount"] - pts[0]["amount"]) / span, 2)
    eta = None
    if rate and rate > 0:
        left = max(_money(a.target) - _money(a.balance), 0)
        eta = (date.fromisoformat(_today()) + timedelta(days=int(left / rate))).isoformat()
    return {"account": _account_out(a), "points": pts,
            "observed_per_day": rate, "projected_arrival": eta}
