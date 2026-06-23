import os
import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator, EmailStr
from dotenv import load_dotenv
from typing import Literal, Annotated

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
    name: Annotated[str, Field(min_length=2, max_length=60)] | None = Field(
        default=None,
        description="الاسم الكامل للعميل كما أدخله في المحادثة"
    )
    phone: Annotated[str, Field(min_length=11, max_length=11, pattern=r"^01\d{9}$")] | None = Field(
        default=None,
        description="رقم المحمول المصري: 01 متبوعاً بـ 9 أرقام"
    )
    email: EmailStr | None = Field(
        default=None,
        description="البريد الإلكتروني إن وُجد"
    )
    city: str | None = Field(
        default=None,
        description="الدولة أو المدينة المستخرجة من المحادثة"
    )
    language: Literal["Arabic", "English"] | None = Field(
        default=None,
        description="لغة المحادثة: Arabic أو English"
    )
    dialect: Literal["egyptian", "saudi", "syrian", "standard"] | None = Field(
        default=None,
        description="اللهجة المكتشفة"
    )
    contact_channel: Literal["whatsapp", "email", "call"] | None = Field(
        default=None,
        description="القناة المفضلة للتواصل"
    )
    contact_time: str | None = Field(
        default=None,
        description="الوقت المفضل للتواصل إن ذُكر"
    )


class ProductsOfInterest(BaseModel):
    courses: Annotated[list[str], Field(max_length=20)] = Field(
        default_factory=list,
        description="أسماء الدورات الفردية"
    )
    tracks: Annotated[list[str], Field(max_length=10)] = Field(
        default_factory=list,
        description="أسماء المسارات التعليمية"
    )
    diplomas: Annotated[list[str], Field(max_length=5)] = Field(
        default_factory=list,
        description="أسماء الدبلومات المباشرة"
    )
    goal: Annotated[str, Field(max_length=200)] | None = Field(
        default=None,
        description="الهدف التعليمي للعميل"
    )
    current_level: Literal["beginner", "intermediate", "advanced"] | None = Field(
        default=None,
        description="المستوى الحالي للعميل"
    )
    prerequisites_discussed: Annotated[str, Field(max_length=500)] | None = Field(
        default=None,
        description="ملاحظات حول المتطلبات المسبقة"
    )


class LeadAssessment(BaseModel):
    temperature: Literal["cold", "warm", "hot"] = Field(
        default="cold",
        description="مستوى جاهزية العميل للشراء"
    )
    buying_signals: Annotated[list[str], Field(max_length=20)] = Field(
        default_factory=list,
        description="إشارات الشراء المكتشفة"
    )
    budget_sensitivity: Literal["sensitive", "neutral", "not_sensitive"] | None = Field(
        default=None,
        description="مدى حساسية العميل للسعر"
    )
    objections: Annotated[
        list[Literal["price", "time", "experience", "trust", "refund", "comparison"]],
        Field(max_length=10)
    ] = Field(
        default_factory=list,
        description="الاعتراضات المكتشفة"
    )
    intent: Literal["browsing", "comparing", "price_sensitive", "hesitant", "ready_to_enroll"] = Field(
        default="browsing",
        description="نية العميل"
    )
    goal: Annotated[str, Field(max_length=200)] | None = Field(
        default=None,
        description="الهدف المستخرج من المحادثة"
    )


class CRMTicket(BaseModel):
    lead: LeadInfo = Field(
        default_factory=LeadInfo,
        description="بيانات العميل الشخصية"
    )
    products: ProductsOfInterest = Field(
        default_factory=ProductsOfInterest,
        description="المنتجات التي أبدى اهتمامًا بها"
    )
    assessment: LeadAssessment = Field(
        default_factory=LeadAssessment,
        description="تقييم العميل"
    )
    conversation_summary: Annotated[str, Field(max_length=2000)] = Field(
        default="",
        description="ملخص تلقائي للمحادثة"
    )
    recommended_action: Annotated[str, Field(max_length=500)] = Field(
        default="",
        description="الإجراء الموصى به لفريق المبيعات"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"),
        description="وقت إنشاء التذكرة"
    )
    ticket_id: Annotated[
        str, Field(pattern=r"^LEAD-\d{4}-\d{4}$")
    ] | None = Field(
        default=None,
        description="المعرف الفريد للتذكرة بصيغة LEAD-2026-XXXX"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d %H:%M")  # يرمي ValueError لو الـ format غلط
        return v

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
        counter = len(self._in_memory)
        if self._connected and self.collection is not None:
            try:
                counter = self.collection.count_documents({})
            except Exception:
                pass
        data["ticket_id"] = f"LEAD-2026-{counter + 1:04d}"
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
