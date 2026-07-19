"""
TEHCARGO WhatsApp Assistant — Routers

Public (ACC-008 whitelist — Meta Cloud API calls these):
  GET  /api/v1/whatsapp/webhook   — Meta verification handshake (hub.challenge)
  POST /api/v1/whatsapp/webhook   — incoming messages (HMAC-verified, processed in background)

Staff (JWT, ACC-007 router-level auth):
  GET   /api/v1/whatsapp/conversations
  GET   /api/v1/whatsapp/conversations/{id}/messages
  POST  /api/v1/whatsapp/conversations/{id}/status
  GET   /api/v1/whatsapp/leads
  PATCH /api/v1/whatsapp/leads/{id}
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import func, or_

from app.core.database import SessionLocal, get_db
from app.core.dependencies import get_current_user
from app.modules.customers.models import Customer
from app.modules.whatsapp import whatsapp_client
from app.modules.whatsapp.assistant import run_assistant
from app.modules.whatsapp.models import (
    WhatsAppConversation,
    WhatsAppLead,
    WhatsAppMessage,
)

logger = logging.getLogger(__name__)

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET   = os.getenv("WHATSAPP_APP_SECRET", "")

webhook_router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp-webhook"])
admin_router = APIRouter(
    prefix="/api/v1/whatsapp",
    tags=["whatsapp-admin"],
    dependencies=[Depends(get_current_user)],  # ACC-007: auth at router level
)

# ── Public webhook ────────────────────────────────────────────────────────────


@webhook_router.get("/webhook")
def verify_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    """Meta subscription handshake."""
    if mode == "subscribe" and WHATSAPP_VERIFY_TOKEN and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


def _verify_signature(raw_body: bytes, signature_header: str) -> bool:
    if not WHATSAPP_APP_SECRET:
        logger.warning("WHATSAPP_APP_SECRET not set — skipping signature verification")
        return True
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len("sha256="):])


def _process_incoming(payload: dict) -> None:
    """Background task: runs the assistant and replies. Own DB session."""
    db = SessionLocal()
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                contacts = {c["wa_id"]: c for c in value.get("contacts", [])}
                for msg in value.get("messages", []):
                    _handle_message(db, msg, contacts.get(msg.get("from"), {}))
    except Exception:
        logger.exception("WhatsApp webhook processing failed")
        db.rollback()
    finally:
        db.close()


def _find_customer(db: Session, wa_id: str) -> Customer | None:
    """Match a WhatsApp number to an existing ERP customer.

    wa_id is digits-only E.164 (e.g. '13017785042'); customer phone/whatsapp
    fields come in mixed formats, so compare on the last 9 digits after
    stripping non-digits on the SQL side.
    """
    tail = "".join(ch for ch in wa_id if ch.isdigit())[-9:]
    if len(tail) < 8:
        return None
    norm_whatsapp = func.regexp_replace(func.coalesce(Customer.whatsapp, ""), r"\D", "", "g")
    norm_phone = func.regexp_replace(func.coalesce(Customer.phone, ""), r"\D", "", "g")
    return (
        db.query(Customer)
        .filter(or_(norm_whatsapp.like(f"%{tail}"), norm_phone.like(f"%{tail}")))
        .first()
    )


def _handle_message(db: Session, msg: dict, contact: dict) -> None:
    wa_id = msg.get("from")
    wa_message_id = msg.get("id")
    if not wa_id or not wa_message_id:
        return

    # Dedup — Meta retries deliveries
    if db.query(WhatsAppMessage.id).filter(WhatsAppMessage.wa_message_id == wa_message_id).first():
        return

    if msg.get("type") == "text":
        text = msg["text"]["body"]
    else:
        # Phase 1: text only. Voice/images come in phase 3.
        text = None

    conv = db.query(WhatsAppConversation).filter(WhatsAppConversation.wa_id == wa_id).first()
    if conv is None:
        customer = _find_customer(db, wa_id)
        conv = WhatsAppConversation(
            wa_id=wa_id,
            profile_name=contact.get("profile", {}).get("name"),
            customer_id=customer.id if customer else None,
        )
        db.add(conv)
        db.flush()

    whatsapp_client.mark_read(wa_message_id)

    if conv.status == "handoff":
        # Human is handling this chat — store the message, don't auto-reply
        db.add(WhatsAppMessage(
            conversation_id=conv.id,
            role="user",
            content=json.dumps([{"type": "text", "text": text or f"[{msg.get('type')} message]"}],
                               ensure_ascii=False),
            wa_message_id=wa_message_id,
        ))
        db.commit()
        return

    if text is None:
        db.commit()  # keep the conversation row even though we can't process the message
        unsupported = (
            "Merci pour votre message ! Pour l'instant je ne peux lire que les messages texte. "
            "Pouvez-vous écrire votre demande ?\n\n"
            "Thank you for your message! I can only read text messages for now. "
            "Could you type your request?"
        )
        whatsapp_client.send_text(wa_id, unsupported)
        return

    reply = run_assistant(db, conv, text, wa_message_id)
    if reply:
        whatsapp_client.send_text(wa_id, reply)


@webhook_router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(raw_body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(raw_body)
    # Respond 200 immediately (Meta retries slow webhooks); Claude runs in background
    background_tasks.add_task(_process_incoming, payload)
    return {"status": "received"}


# ── Staff endpoints ───────────────────────────────────────────────────────────


class ConversationStatusUpdate(BaseModel):
    status: str  # active | handoff | closed


class StaffReply(BaseModel):
    text: str


class LeadUpdate(BaseModel):
    status: str | None = None       # new | contacted | converted | rejected
    customer_id: int | None = None
    notes: str | None = None


@admin_router.get("/conversations")
def list_conversations(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(WhatsAppConversation)
    if status:
        q = q.filter(WhatsAppConversation.status == status)
    rows = q.order_by(WhatsAppConversation.last_message_at.desc()).limit(200).all()
    return [
        {
            "id": c.id,
            "wa_id": c.wa_id,
            "profile_name": c.profile_name,
            "status": c.status,
            "language": c.language,
            "customer_id": c.customer_id,
            "last_message_at": c.last_message_at,
        }
        for c in rows
    ]


@admin_router.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.conversation_id == conversation_id)
        .order_by(WhatsAppMessage.id)
        .all()
    )
    out = []
    for m in rows:
        try:
            blocks = json.loads(m.content)
            text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        except (json.JSONDecodeError, AttributeError):
            text = m.content
        out.append({"id": m.id, "role": m.role, "text": text, "created_at": m.created_at})
    return out


@admin_router.post("/conversations/{conversation_id}/reply")
def staff_reply(
    conversation_id: int,
    body: StaffReply,
    db: Session = Depends(get_db),
):
    """Send a message to the customer as a human (staff).

    Puts the conversation in handoff so the bot stays silent until staff
    sets it back to active. Stored with role='staff' — replayed to Claude
    as an assistant turn so the bot keeps full context if reactivated.
    """
    conv = db.get(WhatsAppConversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    whatsapp_client.send_text(conv.wa_id, text)
    db.add(WhatsAppMessage(
        conversation_id=conv.id,
        role="staff",
        content=json.dumps([{"type": "text", "text": text}], ensure_ascii=False),
    ))
    conv.status = "handoff"
    conv.last_message_at = datetime.utcnow()
    db.commit()
    return {"conversation_id": conv.id, "status": conv.status, "sent": True}


@admin_router.post("/conversations/{conversation_id}/status")
def update_conversation_status(
    conversation_id: int,
    body: ConversationStatusUpdate,
    db: Session = Depends(get_db),
):
    if body.status not in ("active", "handoff", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    conv = db.get(WhatsAppConversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.status = body.status
    db.commit()
    return {"id": conv.id, "status": conv.status}


@admin_router.get("/leads")
def list_leads(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(WhatsAppLead)
    if status:
        q = q.filter(WhatsAppLead.status == status)
    rows = q.order_by(WhatsAppLead.created_at.desc()).limit(200).all()
    return [
        {
            "id": l.id,
            "conversation_id": l.conversation_id,
            "customer_id": l.customer_id,
            "name": l.name,
            "phone": l.phone,
            "email": l.email,
            "pickup_address": l.pickup_address,
            "destination": l.destination,
            "cargo_type": l.cargo_type,
            "weight_or_dimensions": l.weight_or_dimensions,
            "preferred_pickup_date": l.preferred_pickup_date,
            "pickup_readiness": l.pickup_readiness,
            "shipping_mode": l.shipping_mode,
            "recipient_name": l.recipient_name,
            "recipient_phone": l.recipient_phone,
            "notes": l.notes,
            "status": l.status,
            "created_at": l.created_at,
        }
        for l in rows
    ]


@admin_router.patch("/leads/{lead_id}")
def update_lead(lead_id: int, body: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(WhatsAppLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if body.status is not None:
        if body.status not in ("new", "contacted", "converted", "rejected"):
            raise HTTPException(status_code=400, detail="Invalid status")
        lead.status = body.status
    if body.customer_id is not None:
        lead.customer_id = body.customer_id
    if body.notes is not None:
        lead.notes = body.notes
    db.commit()
    return {"id": lead.id, "status": lead.status, "customer_id": lead.customer_id}
