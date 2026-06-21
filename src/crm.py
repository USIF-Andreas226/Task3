import os
import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False


MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB = os.environ.get("MONGO_DB", "kayfa_crm")
MONGO_COLLECTION = os.environ.get("MONGO_COLLECTION", "tickets")


class LeadInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    language: str | None = None
    dialect: str | None = None
    contact_channel: str | None = None
    contact_time: str | None = None


class ProductsOfInterest(BaseModel):
    courses: list[str] = Field(default_factory=list)
    tracks: list[str] = Field(default_factory=list)
    diplomas: list[str] = Field(default_factory=list)
    goal: str | None = None
    current_level: str | None = None
    prerequisites_discussed: str | None = None


class LeadAssessment(BaseModel):
    temperature: str = "cold"
    buying_signals: list[str] = Field(default_factory=list)
    budget_sensitivity: str | None = None
    objections: list[str] = Field(default_factory=list)
    intent: str = "browsing"
    goal: str | None = None


class CRMTicket(BaseModel):
    lead: LeadInfo = Field(default_factory=LeadInfo)
    products: ProductsOfInterest = Field(default_factory=ProductsOfInterest)
    assessment: LeadAssessment = Field(default_factory=LeadAssessment)
    conversation_summary: str = ""
    recommended_action: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    ticket_id: str | None = None


class CRMClient:
    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.collection: Any = None
        self._connected = False
        self._in_memory: list[dict[str, Any]] = []
        if MONGO_AVAILABLE and MONGO_URI:
            try:
                self.client = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                )
                self.client.server_info()
                db = self.client[MONGO_DB]
                self.collection = db[MONGO_COLLECTION]
                self._connected = True
            except (ConnectionFailure, Exception):
                self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def save_ticket(self, ticket: CRMTicket) -> str:
        data = ticket.model_dump()
        data["ticket_id"] = f"LEAD-2026-{len(self._in_memory) + 1:04d}"
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        if self._connected and self.collection is not None:
            try:
                result = self.collection.insert_one(data)
                data["_id"] = str(result.inserted_id)
            except Exception:
                pass
        self._in_memory.append(data)
        return data["ticket_id"]

    def get_all_tickets(self) -> list[dict[str, Any]]:
        tickets: list[dict[str, Any]] = []
        if self._connected and self.collection is not None:
            try:
                for doc in self.collection.find().sort("timestamp", -1):
                    doc["_id"] = str(doc["_id"])
                    tickets.append(doc)
            except Exception:
                pass
        tickets.extend(self._in_memory)
        seen = set()
        unique: list[dict[str, Any]] = []
        for t in tickets:
            tid = t.get("ticket_id", "")
            if tid not in seen:
                seen.add(tid)
                unique.append(t)
        return unique

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        for t in self.get_all_tickets():
            if t.get("ticket_id") == ticket_id:
                return t
        return None

    def close(self) -> None:
        if self.client:
            self.client.close()
