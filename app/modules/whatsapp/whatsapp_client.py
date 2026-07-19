"""
TEHCARGO WhatsApp Assistant — Meta Cloud API client

Outbound side only: send text messages, mark incoming messages as read.
Config via env (same pattern as shop_payment_router):
  WHATSAPP_ACCESS_TOKEN     — permanent token from Meta Business (System User)
  WHATSAPP_PHONE_NUMBER_ID  — the Cloud API phone number id
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

WHATSAPP_ACCESS_TOKEN    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_BASE_URL           = os.getenv("WHATSAPP_GRAPH_BASE_URL", "https://graph.facebook.com/v21.0")

# WhatsApp hard limit is 4096 chars per text message
MAX_TEXT_LEN = 4000


def _messages_url() -> str:
    return f"{GRAPH_BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def send_text(to_wa_id: str, text: str) -> None:
    """Send a plain text message, splitting if it exceeds the WhatsApp limit."""
    chunks = [text[i:i + MAX_TEXT_LEN] for i in range(0, len(text), MAX_TEXT_LEN)] or [""]
    with httpx.Client(timeout=30) as client:
        for chunk in chunks:
            resp = client.post(
                _messages_url(),
                headers=_headers(),
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to_wa_id,
                    "type": "text",
                    "text": {"preview_url": False, "body": chunk},
                },
            )
            if resp.status_code >= 400:
                logger.error("WhatsApp send failed (%s): %s", resp.status_code, resp.text)
                resp.raise_for_status()


def mark_read(wa_message_id: str) -> None:
    """Mark an incoming message as read (blue ticks). Best-effort."""
    try:
        with httpx.Client(timeout=15) as client:
            client.post(
                _messages_url(),
                headers=_headers(),
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": wa_message_id,
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("mark_read failed for %s: %s", wa_message_id, exc)
