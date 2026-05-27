"""
TEHTEK Public Shop — Payment endpoints (no auth required).

Supported methods:
  fapshi  — Fapshi hosted page (card, Orange Money, MTN MoMo)
  paypal  — PayPal JS SDK capture
  cod     — Cash on Delivery (verified ERP customers only)

Endpoints:
  POST /api/v1/shop/checkout                — create order + initiate payment
  GET  /api/v1/shop/orders/{ref}            — poll order status (public)
  POST /api/v1/shop/payment/fapshi/webhook  — Fapshi payment notification
  POST /api/v1/shop/payment/paypal/capture  — PayPal order capture
  GET  /api/v1/shop/cod-eligible            — check COD eligibility by phone
"""
import json
import logging
import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.companies.controller import next_sequence
from app.core.enums import SequenceType
from app.modules.customers.models import Customer
from app.modules.stock.shop_order_models import ShopOrder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/shop", tags=["shop-payment"])

# ── Config ────────────────────────────────────────────────────────────────────

FAPSHI_API_USER      = os.getenv("FAPSHI_API_USER", "")
FAPSHI_API_KEY       = os.getenv("FAPSHI_API_KEY", "")
FAPSHI_BASE_URL      = os.getenv("FAPSHI_BASE_URL", "https://live.fapshi.com")
FAPSHI_WEBHOOK_SECRET = os.getenv("FAPSHI_WEBHOOK_SECRET", "")

PAYPAL_CLIENT_ID  = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET     = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL   = os.getenv("PAYPAL_BASE_URL", "https://api-m.paypal.com")

SHOP_BASE_URL     = os.getenv("SHOP_BASE_URL", "https://tehtek.com")
API_BASE_URL      = os.getenv("API_BASE_URL",  "https://api2.tehtek.com/api/v1")

# 1 USD ≈ 620 XAF  (update periodically)
XAF_TO_USD        = float(os.getenv("XAF_TO_USD_RATE", "620"))


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutItem(BaseModel):
    id:         int
    sku:        str
    name:       str
    qty:        int
    unit_price: float


class CheckoutRequest(BaseModel):
    customer_name:    str
    customer_phone:   str
    customer_email:   Optional[str] = None
    customer_city:    Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_notes:   Optional[str] = None
    items:            List[CheckoutItem]
    payment_method:   str   # fapshi | paypal | cod


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fapshi_headers() -> dict:
    return {"apiuser": FAPSHI_API_USER, "apikey": FAPSHI_API_KEY}


async def _fapshi_initiate(
    order_ref: str,
    amount: int,
    description: str,
    email: str | None = None,
) -> dict:
    """Call Fapshi /initiate-pay and return {transId, payLink}.

    Fapshi API fields (camelCase per docs): amount, message, email,
    redirectUrl, externalId, userId.
    Note: name and phone pre-fill are NOT supported by Fapshi.
    Webhook URL is configured once in the Fapshi dashboard, not per request.
    """
    payload = {
        "amount":      amount,
        "message":     description,
        "redirectUrl": f"{SHOP_BASE_URL}/order/{order_ref}",
        "externalId":  order_ref,   # for reconciliation in Fapshi dashboard
    }
    if email:
        payload["email"] = email

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{FAPSHI_BASE_URL}/initiate-pay",
            json=payload,
            headers=_fapshi_headers(),
        )
    if r.status_code != 200:
        raise HTTPException(502, f"Fapshi error: {r.text}")
    data = r.json()
    if data.get("statusCode") not in (200, None) and data.get("status") not in (200, None):
        raise HTTPException(502, f"Fapshi rejected: {data}")
    return data.get("data", data)


async def _paypal_access_token() -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{PAYPAL_BASE_URL}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        )
    if r.status_code != 200:
        raise HTTPException(502, "PayPal auth failed")
    return r.json()["access_token"]


async def _paypal_capture(paypal_order_id: str) -> dict:
    token = await _paypal_access_token()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{PAYPAL_BASE_URL}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if r.status_code not in (200, 201):
        raise HTTPException(502, f"PayPal capture failed: {r.text}")
    return r.json()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/checkout", status_code=201)
async def create_checkout(body: CheckoutRequest, db: Session = Depends(get_db)):
    """
    Create a shop order and, depending on payment_method:
      - fapshi : returns {order_ref, pay_link}  — frontend redirects to pay_link
      - paypal : returns {order_ref}             — frontend uses PayPal JS SDK
      - cod    : returns {order_ref}             — if customer is eligible
    """
    method = body.payment_method.lower()
    if method not in ("fapshi", "paypal", "cod"):
        raise HTTPException(400, "payment_method must be fapshi | paypal | cod")

    # ── COD eligibility ──────────────────────────────────────────────────
    cod_customer_id = None
    if method == "cod":
        customer = (
            db.query(Customer)
            .filter(
                Customer.phone == body.customer_phone,
                Customer.kyc_status == "verified",
                Customer.status == "active",
                Customer.deleted_at.is_(None),
            )
            .first()
        )
        if not customer:
            raise HTTPException(
                403,
                "Le paiement à la livraison n'est disponible que pour les clients "
                "vérifiés par notre équipe. Contactez-nous via WhatsApp pour vous faire certifier."
            )
        cod_customer_id = customer.id

    # ── Build order ──────────────────────────────────────────────────────
    subtotal = sum(i.qty * i.unit_price for i in body.items)
    if subtotal <= 0:
        raise HTTPException(400, "Le panier est vide ou le total est invalide")

    items_snapshot = [
        {
            "id":         i.id,
            "sku":        i.sku,
            "name":       i.name,
            "qty":        i.qty,
            "unit_price": i.unit_price,
            "line_total": round(i.qty * i.unit_price, 2),
        }
        for i in body.items
    ]

    order_ref = next_sequence(db, SequenceType.shop_order_number)

    order = ShopOrder(
        order_ref        = order_ref,
        customer_name    = body.customer_name,
        customer_phone   = body.customer_phone,
        customer_email   = body.customer_email,
        customer_city    = body.customer_city,
        delivery_address = body.delivery_address,
        delivery_notes   = body.delivery_notes,
        items_json       = json.dumps(items_snapshot, ensure_ascii=False),
        subtotal         = round(subtotal, 2),
        payment_method   = method,
        payment_status   = "pending",
        status           = "pending",
        cod_customer_id  = cod_customer_id,
    )
    db.add(order)
    db.flush()   # get id without committing yet

    response: dict = {"order_ref": order_ref}

    # ── Fapshi: initiate hosted payment ──────────────────────────────────
    if method == "fapshi":
        if not FAPSHI_API_USER or not FAPSHI_API_KEY:
            db.rollback()
            raise HTTPException(503, "Fapshi n'est pas encore configuré sur ce serveur.")
        try:
            fapshi_data = await _fapshi_initiate(
                order_ref   = order_ref,
                amount      = int(round(subtotal)),
                description = f"Commande TEHTEK {order_ref}",
                email       = body.customer_email,
            )
            order.payment_ref = fapshi_data.get("transId") or fapshi_data.get("transaction_id")
            response["pay_link"] = fapshi_data.get("payLink") or fapshi_data.get("link")
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            logger.exception("Fapshi initiate error: %s", exc)
            raise HTTPException(502, "Erreur de communication avec la plateforme de paiement.")

    # ── PayPal: just create the order record — capture happens separately ─
    elif method == "paypal":
        if not PAYPAL_CLIENT_ID:
            db.rollback()
            raise HTTPException(503, "PayPal n'est pas encore configuré sur ce serveur.")
        usd_amount = round(subtotal / XAF_TO_USD, 2)
        response["usd_amount"] = usd_amount

    # ── COD: immediately confirm ──────────────────────────────────────────
    elif method == "cod":
        order.payment_status = "cod_pending"
        order.status         = "confirmed"

    db.commit()
    return response


@router.get("/orders/{order_ref}")
def get_order_status(order_ref: str, db: Session = Depends(get_db)):
    """Poll order status — used by confirmation page."""
    order = db.query(ShopOrder).filter_by(order_ref=order_ref).first()
    if not order:
        raise HTTPException(404, "Commande introuvable")
    return {
        "order_ref":      order.order_ref,
        "status":         order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "subtotal":       float(order.subtotal),
        "customer_name":  order.customer_name,
        "customer_city":  order.customer_city,
        "items":          json.loads(order.items_json),
        "created_at":     order.created_at.isoformat(),
    }


@router.post("/payment/fapshi/webhook")
async def fapshi_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Fapshi calls this URL after payment.
    Fapshi sends JSON: {event, data: {transId, status, amount, ...}}.
    Authenticated via x-wh-secret header, then verified via GET /payment-status/{transId}.
    """
    # ── Verify webhook secret ─────────────────────────────────────────────
    if FAPSHI_WEBHOOK_SECRET:
        incoming = request.headers.get("x-wh-secret", "")
        if incoming != FAPSHI_WEBHOOK_SECRET:
            logger.warning("Fapshi webhook: invalid secret — rejected")
            return {"ok": True}  # always 200 to avoid Fapshi retries

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Fapshi webhook body varies by version — handle both formats
    trans_id = (
        (payload.get("data") or {}).get("transId")
        or payload.get("transId")
        or payload.get("transaction_id")
    )
    if not trans_id:
        logger.warning("Fapshi webhook: missing transId — %s", payload)
        return {"ok": True}  # always 200 to avoid retries

    # Verify with Fapshi API
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{FAPSHI_BASE_URL}/payment-status/{trans_id}",
                headers=_fapshi_headers(),
            )
        status_data = r.json().get("data", r.json())
        fapshi_status = str(status_data.get("status", "")).upper()
        paid_amount   = status_data.get("amount")
    except Exception as exc:
        logger.exception("Fapshi verify error: %s", exc)
        return {"ok": True}

    order = db.query(ShopOrder).filter_by(payment_ref=trans_id).first()
    if not order:
        logger.warning("Fapshi webhook: no order found for transId=%s", trans_id)
        return {"ok": True}

    if fapshi_status == "SUCCESSFUL":
        order.payment_status = "paid"
        order.status         = "confirmed"
        order.payment_amount = paid_amount
        order.updated_at     = datetime.utcnow()
        db.commit()
        logger.info("Order %s paid via Fapshi", order.order_ref)
    elif fapshi_status in ("FAILED", "EXPIRED"):
        order.payment_status = fapshi_status.lower()
        order.updated_at     = datetime.utcnow()
        db.commit()

    return {"ok": True}


@router.post("/payment/paypal/capture")
async def paypal_capture(
    paypal_order_id: str = Query(...),
    order_ref:       str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Frontend calls this after PayPal onApprove.
    We capture the PayPal order and mark our ShopOrder as paid.
    """
    order = db.query(ShopOrder).filter_by(order_ref=order_ref).first()
    if not order:
        raise HTTPException(404, "Commande introuvable")
    if order.payment_status == "paid":
        return {"ok": True, "order_ref": order_ref}

    capture = await _paypal_capture(paypal_order_id)
    pp_status = capture.get("status", "")
    if pp_status == "COMPLETED":
        order.payment_status = "paid"
        order.status         = "confirmed"
        order.payment_ref    = paypal_order_id
        order.payment_amount = float(
            (capture.get("purchase_units") or [{}])[0]
            .get("payments", {})
            .get("captures", [{}])[0]
            .get("amount", {})
            .get("value", 0)
        )
        order.updated_at = datetime.utcnow()
        db.commit()
    else:
        raise HTTPException(402, f"PayPal capture not completed: {pp_status}")

    return {"ok": True, "order_ref": order_ref}


@router.get("/cod-eligible")
def check_cod_eligible(phone: str = Query(...), db: Session = Depends(get_db)):
    """
    Check if a phone number belongs to a verified ERP customer.
    Returns {eligible: bool, name: str|null}.
    Never leaks sensitive data.
    """
    customer = (
        db.query(Customer)
        .filter(
            Customer.phone == phone,
            Customer.kyc_status == "verified",
            Customer.status == "active",
            Customer.deleted_at.is_(None),
        )
        .first()
    )
    if customer:
        return {"eligible": True, "name": customer.first_name}
    return {"eligible": False, "name": None}
