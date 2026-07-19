"""
TEHCARGO WhatsApp Assistant — Models

WhatsAppConversation : one row per WhatsApp number talking to the bot
WhatsAppMessage      : full transcript (user / assistant / tool turns),
                       content stored as JSON-serialized Claude content blocks
WhatsAppLead         : structured lead captured by the assistant, later
                       convertible to a Customer + PickupRequest
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id           = Column(Integer, primary_key=True)
    wa_id        = Column(String(30), unique=True, nullable=False)  # E.164 phone from Meta
    profile_name = Column(String(200), nullable=True)
    customer_id  = Column(Integer, ForeignKey("customers.id"), nullable=True)

    # active   — bot replies automatically
    # handoff  — bot paused, a human (Benjamin) answers from WhatsApp directly
    # closed   — conversation archived
    status       = Column(String(20), nullable=False, default="active")
    language     = Column(String(5), nullable=True)  # "fr" / "en", detected by the bot

    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id              = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("whatsapp_conversations.id"), nullable=False)

    role          = Column(String(20), nullable=False)  # user | assistant
    content       = Column(Text, nullable=False)        # JSON list of Claude content blocks
    wa_message_id = Column(String(100), nullable=True)  # Meta message id (dedup)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WhatsAppLead(Base):
    __tablename__ = "whatsapp_leads"

    id              = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("whatsapp_conversations.id"), nullable=False)
    customer_id     = Column(Integer, ForeignKey("customers.id"), nullable=True)

    name                 = Column(String(200), nullable=True)
    phone                = Column(String(30), nullable=False)
    email                = Column(String(255), nullable=True)
    pickup_address       = Column(Text, nullable=True)
    destination          = Column(Text, nullable=True)
    cargo_type           = Column(String(100), nullable=True)   # boxes, barrels, vehicle, ...
    weight_or_dimensions = Column(String(200), nullable=True)
    preferred_pickup_date = Column(String(50), nullable=True)   # free text from customer
    pickup_readiness     = Column(String(200), nullable=True)   # ready now / ready on <date>, as stated
    notes                = Column(Text, nullable=True)

    # new | contacted | converted | rejected
    status     = Column(String(20), nullable=False, default="new")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
