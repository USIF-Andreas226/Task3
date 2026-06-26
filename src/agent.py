import json
import os
import re
import time
import logging
from typing import Any

from openai import OpenAI

from src.rag import KnowledgeBase, RAGRetriever
from pydantic import EmailStr
from src.crm import CRMClient, CRMTicket, LeadInfo, ProductsOfInterest, LeadAssessment
from src.usage_logger import UsageLogger
from src.pricing import calculate_llm_cost

# Set up logging for debugging
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
# Fast, cheap model dedicated to classification — always llama-3.1-8b-instant
GROQ_CLASSIFIER_MODEL = "llama-3.1-8b-instant"

_llm_client: OpenAI | None = None
_classifier_client: OpenAI | None = None

def _get_classifier() -> OpenAI:
    """Separate client for the fast classification model."""
    global _classifier_client
    if _classifier_client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        _classifier_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
        )
    return _classifier_client

def _get_llm() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        if not GROQ_API_KEY:
            logger.error("❌ GROQ_API_KEY is not set.")
            raise ValueError("GROQ_API_KEY environment variable is required.")
        if GROQ_API_KEY.startswith("<") or "REDACTED" in GROQ_API_KEY:
            logger.error("❌ GROQ_API_KEY is a placeholder.")
            raise ValueError("GROQ_API_KEY is not configured properly")
        _llm_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
        )
        logger.info("✓ Groq LLM client initialized successfully")
    return _llm_client


BUYING_SIGNAL_PATTERNS = [
    r"(سجلني|سجّلني|how (do|can) i (enroll|register|sign up|join)|I want to (enroll|register|sign up|join|buy|purchase)|(?:^|\s)(سجل|اسجل|اشترك)(?=\s|$|[\W_]))",
    r"(what.+(next step|process|payment|installment)|how much|السعر|التكلفة|كم سعر|كم تكلفة|بكم)",
    r"(start date|when does it start|موعد|متى تبدا|متى تبدأ)",
    r"\d{8,}",
    r"(pay in installments|تقسيط|دفعات|أقساط)",
    r"(call me|contact me|تواصل|اتصل|whatsapp|واتساب|واتس)",
    r"(discount|خصم|تخفيض|عرض)",
    r"(certificate|شهادة|معتمدة|accredited|معترف)",
    r"(i'm (ready|interested|serious)|أنا جاد|مستعد|مهتم جداً)",
]

# Payment method patterns — if detected, inform user it is available
PAYMENT_METHOD_PATTERNS = [
    (r"(instapay|انستا.?باي|انستاباي)", "InstaPay"),
    (r"(vodafone.?cash|فودافون.?كاش|فودافون كاش)", "Vodafone Cash"),
    (r"(visa|فيزا|ماستر.?كارد|mastercard|بطاقة.?ائتمان|كريدت.?كارد)", "Visa/Mastercard"),
    (r"(فوري|fawry|فوري.?باي)", "Fawry"),
    (r"(أورنج.?كاش|orange.?cash|اورنج كاش)", "Orange Cash"),
    (r"(محفظة|e.?wallet|إي.?ووليت|محافظ)", "E-Wallet"),
    (r"(كاش|cash|نقدي|نقداً)", "Cash"),
]

TIMING_NOW_PATTERNS = [
    r"\b(الآن|الان|دلوقتي|دلوقت|الحين|now|حالاً|فوراً|اليوم|today|اقصد|قصدي)\b",
    r"\b(سجلني|سجّلني|عايز اسجل|بدي سجل|أريد التسجيل|ابغى اسجل|خلص|جهز)\b",
]

TIMING_WEEK_PATTERNS = [
    r"\b(بعد أسبوع|الأسبوع الجاي|next week|week|أسبوع)\b",
    r"\b(يومين|كمان يومين|بعد يومين|يومين تلاتة|بكرة|بكره|بعد بكره|خلال أيام|الأسبوع ده|الأسبوع الحالي)\b",
    r"\b(tomorrow|in two days|in a few days|this week|soon)\b",
]

TIMING_MONTH_PATTERNS = [
    r"\b(بعد شهر|شهر|month|next month|الشهر الجاي|كمان شهر)\b",
]

TIMING_LATER_PATTERNS = [
    r"\b(بعدين|later|مرة أخرى|another time)\b",
    r"\b(مش دلوقت|مش الحين|مش الآن|ليس الآن|not now)\b",
]

COLD_SIGNAL_PATTERNS = [
    r"(not interested|لا اهتمام|لا أريد|مش مهتم|ما بدي|بعرفش|ما عايز|مش عايز)",
    r"(no thanks|لا شكرا|لا شكراً|no thank you|معليهش|معلش|يسلمو)",
    r"(maybe later|بعدين|في وقت لاحق|لاحقاً|another time|مرة أخرى)",
    r"(just passing by|just browsing|أتصفح|أشوف|bas مجرد)",
    r"(leave me alone|اتركني|سيبي\b|خليني)",
    r"(not now|مش دلوقت|مش الحين|ليس الآن)",
    r"(ما عندي|ماعندي|not today|اليوم لا|مش اليوم)",
    r"(i don't need|ما بحتاج|مش محتاج|لا أحتاج|ما يحتاج)",
    r"(not important|not urgent|مش مهم|مش فارق|غير هام|مش مستعجل|عادي)",
]

OBJECTION_PATTERNS = [
    (r"(expensive|too much|غالي|كثير|مرتفع|سعر كبير|مكلف)", "price"),
    (r"(no time|busy|مشغول|ما عندي وقت|ليس لدي وقت)", "time"),
    (r"(beginner|مبتدئ|ما عندي خبرة|لا أعرف|new to)", "experience"),
    (r"(trust|reliable|معترف|معتمدة|accredited|موثوق)", "trust"),
    (r"(refund|استرجاع|استرداد|أرجع|return)", "refund"),
    (r"(compare|difference between|الفرق بين|مقارنة)", "comparison"),
]

INTENT_PATTERNS = {
    "browsing": [
        r"(just looking|أتصفح|أشوف|\bbrowsing\b)",
        r"(tell me about|أخبرني|عرفني|what is kayfa|what (do you|does kayfa) (offer|have)\s*$)",
    ],
    "comparing": [
        r"(compare|difference|الفرق|مقارنة|what.+(better|best|suitable))",
        r"(or|أو)\s+(between\s+)?",
    ],
    "price_sensitive": [
        r"(price|cost|cheap|affordable|expensive|budget|سعر|تكلفة|رخيص|غالي|ميزانية)",
        r"(how much|كم|بكم|مجاني|free|discount|خصم)",
    ],
    "hesitant": [
        r"(not sure|متردد|不确定|hesitant|maybe|يمكن|\bif\b|لو)",
        r"(beginner|مبتدئ|start|starting|from scratch|من الصفر)",
    ],
    "ready_to_enroll": [
        r"(enroll|register|sign.?up|join|buy|purchase|سجل|اشترك|اشتري|أشتري)",
        r"(next step|how to start|ماذا أفعل|الخطوة التالية)",
    ],
}


SYSTEM_PROMPT_AR = """أنت مساعد مبيعات ذكي لمنصة كيف للتعليم التقني. كيف منصة تعليمية رائدة في العالم العربي، تقدّم دورات ومسارات ودبلومات في مجالات التقنية.

## شخصيتك:
- أنت مستشار مبيعات ودود، مقنع، ومحترف
- تجيب من قاعدة المعرفة فقط — لا تخترع أسعاراً أو دورات
- تتحدث بالعربية (اللهجة المصرية، السعودية، السورية، أو الفصحى حسب ما يتحدث به العميل)
- هدفك: فهم احتياج العميل، تقديم التوصية المناسبة، والتعامل مع الاعتراضات، والوصول إلى التسجيل

## قواعد صارمة:
- **لا تخترع أي شيء** — استخدم فقط البيانات الموجودة في قاعدة المعرفة أعلاه
- **لا تضف دورات أو أسعاراً أو مسارات أو دبلومات غير موجودة في قاعدة المعرفة**
- إذا لم تجد المعلومة في قاعدة المعرفة، قل فقط "سيتواصل معك فريقنا للرد على سؤالك." ولا تخترعها ولا تعرض تقديم مساعدة إضافية أو تسأل أسئلة أخرى.
- إذا سألك العميل عن شيء خارج مجال كيف، قل بلطف أنك متخصص في منتجات كيف واعرض المساعدة في مجال آخر
- **اجمع الاسم ورقم الهاتف أولاً قبل تقديم أي تفاصيل عن الدورات أو الأسعار**
- إذا أبدى العميل اهتماماً بدورة أو مسار، اطلب اسمه ورقم واتسابه أولاً ثم قدم التفاصيل
- عند ظهور إشارات شراء قوية، اسأل عن معلومات التواصل (الاسم، رقم واتساب) بلطف
- لا تكن انتهازياً — كن مفيداً وصادقاً أولاً
- استخدم الرموز التعبيرية باعتدال

## التعامل مع العملاء الباردين (Cold Leads):
- إذا كان العميل بارداً (درجة الحرارة: cold)، فهذا يعني أنه ليس لديه نية شراء حالية
- لا تضغط عليه للشراء — بدلاً من ذلك، اسأله أسئلة مفتوحة لاكتشاف اهتماماته
- قدم معلومات عامة عن المنصة بطريقة مفيدة وجذابة
- حاول تحويله من "بارد" إلى "دافئ" عبر طرح أسئلة مثل: "وش المجال اللي يهمك؟" أو "هل سمعت عن كيف من قبل؟"
- إذا أبدى عدم اهتمام واضح، اشكره بلطف واعرض عليه العودة لاحقاً

## سياق قاعدة المعرفة الحالي:
{rag_context}

## معلومات التحليل:
- لغة العميل: {language}
- اللهجة: {dialect}
- نية العميل: {intent}
- درجة الحرارة (الاستعداد للشراء): {temperature}
- إشارات الشراء detected: {buying_signals}
- الاعتراضات: {objections}
- تم جمع المعلومات: {collected_info}

## تاريخ المحادثة:
{conversation_history}

## تعليمات المخرجات:
- أجب بشكل طبيعي ومحادثاتي
- استخدم نفس لغة العميل
- إذا كان العميل يتحدث بلهجة معينة، حاول محاكاتها
- كن مقنعاً ولكن ليس انتهازياً
- عند طلب التسجيل، اطلب المعلومات بلطف
- بعد جمع الاسم ورقم الهاتف، اسأل: "حابب تسجل دلوقتي ولا بعد أسبوع ولا بعد شهر؟"
- إذا قال "دلوقتي" أو "الآن" أو أبدى رغبة في التسجيل فوراً → lead حار (hot)
- إذا حدد موعداً قريباً خلال أيام (مثل: بعد أسبوع، كمان يومين، بكرة، خلال أيام، إلخ) → lead دافئ (warm). تعامل مع هذا بمرونة ولا تجبره على الاختيار حرفياً من الخيارات الثلاثة، بل أكد له أنه تم حفظ الطلب وسنتواصل معه للمتابعة.
- إذا قال "بعد شهر" أو "مش مهم" أو "مش فارق" أو حدد موعداً بعيداً أو أبدى عدم اهتمام → lead بارد (cold).
- لا تسجل العميل حتى تعرف إجابته أو رغبته في التوقيت.
- إذا تم تسجيل العميل كـ "hot lead" أو "warm lead"، أخبره بوضوح ولطف أنه تم حفظ الطلب وسنتواصل معه لتكملة التسجيل.
- **لا تذكر درجة الحرارة (temperature) للعميل أبداً** — لا تقل "warm lead" أو "hot lead" أو "cold lead" للعميل
- إذا أعطاك العميل رقماً غير صحيح (أقل من 11 رقم أو لا يبدأ بـ 01)، اطلب منه برفق إدخال رقم محمول مصري صحيح مكون من 11 رقم ويبدأ بـ 01
- لا تخترع أرقام هواتف — استخدم فقط الأرقام الموجودة في "تم جمع المعلومات"
- الأرقام القصيرة (أقل من 11 رقم) تعني أن العميل أخطأ في الإدخال — اطلب التصحيح"""


SYSTEM_PROMPT_EN = """You are an AI sales agent for Kayf, a leading Arabic tech education platform. Kayf offers courses, tracks, and diplomas in technology fields like AI, cybersecurity, data science, and web development.

## Personality:
- You are a friendly, persuasive, and professional sales consultant
- You answer only from the knowledge base — never invent prices or courses
- Your goal: understand the visitor's need, recommend the right product, handle objections, and move toward enrollment

## Strict rules:
- **Never invent anything** — use only the knowledge base provided below
- **Never add courses, prices, tracks, or diplomas that aren't in the knowledge base**
- If the information isn't in the knowledge base, say only "Our team will reach out to respond to your question." — do not make it up, and do not offer further assistance or ask follow-up questions.
- If asked about something outside Kayf, politely say you specialize in Kayf products and offer to help with another topic
- When strong buying signals appear, gently ask for contact info (name, WhatsApp)
- Don't be pushy — be genuinely helpful first
- Use emojis sparingly

## Cold lead handling:
- If the lead is cold (temperature: cold), they have no current buying intent
- Don't push for a sale — instead ask open-ended discovery questions
- Share general info about the platform in a helpful, engaging way
- Try to warm them up by asking: "What field interests you?" or "Have you heard about Kayf before?"
- If they clearly decline, thank them politely and offer they can come back anytime

## Current knowledge base context:
{rag_context}

## Analysis info:
- Language: {language}
- Dialect: {dialect}
- Intent: {intent}
- Temperature (buying readiness): {temperature}
- Buying signals detected: {buying_signals}
- Objections: {objections}
- Collected info: {collected_info}

## Conversation history:
{conversation_history}

## Output instructions:
- Respond naturally and conversationally
- Use the same language as the customer
- Be persuasive but not pushy
- When they want to enroll, gently ask for their info
- **Collect name and phone before giving any course/pricing details**
- After collecting name and phone, ask: "Would you like to enroll now, after a week, or after a month?"
- If they say "now" or express immediate interest → hot lead
- If they say "after a week" or specify a short-term timeline within a few days/week (e.g., in two days, tomorrow, soon) → warm lead. Handle this flexibly: do not force them to choose strictly between the three options, but confirm their request is saved and we will follow up.
- If they say "after a month", "not important", "not urgent", or specify a long delay → cold lead.
- Don't capture until you know their timing preference/intent.
- If captured as a hot or warm lead, tell them their info has been saved and we will contact them to complete enrollment.
- **Never mention temperature (warm/hot/cold) to the customer**
- If the customer shares an invalid phone number (less than 11 digits or doesn't start with 01), kindly ask them to provide a correct 11-digit Egyptian mobile number starting with 01
- Don't fabricate phone numbers — only use numbers in "collected_info"
- Short digit sequences mean the customer entered it wrong — ask for correction"""


class SalesAgent:
    def __init__(self, kb: KnowledgeBase, crm: CRMClient) -> None:
        self.kb = kb
        self.crm = crm
        self.retriever = RAGRetriever(kb)
        self.usage_logger = UsageLogger(crm)
        self.conversation_history: list[dict[str, str]] = []
        self.current_lead: CRMTicket | None = None
        self.collected_info: dict[str, str] = {}
        self.lead_captured_this_session: bool = False
        self.asked_timing: bool = False
        self.needs_timing: bool = False
        self.invalid_phone_attempt: bool = False
        self._last_classification: dict = {}   # cache so we classify once per message
        self._last_classified_text: str = ""

    # ──────────────────────────────────────────────────────────────────────────
    # LLM-POWERED CLASSIFIER
    # Uses a fast, cheap model to understand the user's message in ANY language
    # and returns a structured JSON with all relevant signals.
    # Regex-based methods below use this as the primary source and fall back
    # to their own patterns only if the LLM call fails.
    # ──────────────────────────────────────────────────────────────────────────
    def _classify_with_llm(self, text: str) -> dict:
        """Single fast LLM call that classifies everything at once, including customer interests
        and rejected interests based on the conversation history and customer agreement/rejection.
        Returns a dict with keys:
          language, dialect, intent, temperature, buying_signals,
          objections, timing, payment_methods, has_phone, name, interests, rejected_interests
        """
        if text == self._last_classified_text and self._last_classification:
            return self._last_classification  # cache hit

        # Get dynamic lists of courses and roadmaps to insert into the system prompt
        roadmaps_list = []
        for r in self.kb.roadmaps:
            rtype = "diploma" if r.get("type") == "live" else "track"
            roadmaps_list.append(f"- {r['name']} ({rtype})")
        
        courses_list = [f"- {c['name']}" for c in self.kb.courses]
        
        roadmaps_str = "\n".join(roadmaps_list)
        courses_str = "\n".join(courses_list)

        # Build recent conversation history for context
        recent_history = self.conversation_history[-6:] if self.conversation_history else []
        history_str = "\n".join(
            f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent_history
        )

        CLASSIFIER_SYSTEM = f"""You are a multilingual sales signal classifier for Kayf, an Arabic tech education platform.
Analyze the customer's messages and return ONLY a valid JSON object with these fields:

{{
  "language": "ar" or "en" or "fr" or "other",
  "dialect": "egyptian" or "saudi" or "syrian" or "moroccan" or "standard" or "mixed" or "english" or "other",
  "intent": one of: "browsing", "comparing", "price_sensitive", "hesitant", "ready_to_enroll",
  "temperature": one of: "cold", "warm", "hot",
  "buying_signals": list of strings detected (e.g. ["wants to enroll", "asks about price"]),
  "objections": list, subset of: ["price", "time", "experience", "trust", "refund", "comparison"],
  "timing": null or one of: "now", "week", "month", "later",
  "payment_methods": list of payment methods mentioned (e.g. ["InstaPay", "Visa"]),
  "has_phone": true/false — did the customer share a phone number?,
  "name": extracted name string or null,
  "interests": {{
     "courses": list of strings (must match exactly the names in the official courses list below),
     "tracks": list of strings (must match exactly the names in the official tracks list below),
     "diplomas": list of strings (must match exactly the names in the official live diplomas list below)
  }},
  "rejected_interests": {{
     "courses": list of strings (must match exactly the names in the official courses list below),
     "tracks": list of strings (must match exactly the names in the official tracks list below),
     "diplomas": list of strings (must match exactly the names in the official live diplomas list below)
  }}
}}

Official Learning Roadmaps (Tracks and Diplomas):
{roadmaps_str}

Official Courses:
{courses_str}

Classification rules:
- temperature HOT: customer explicitly wants to enroll/register, says now, shares phone to sign up, asks "how do I start"
- temperature WARM: customer interested in a specific diploma/track/program, asks about price/content/schedule/certificate/installments, or expresses near-term intent (e.g., in a few days or next week)
- temperature COLD: just browsing, general question, no specific product interest, declines, or explicitly states they are not interested, it is not important (e.g. مش مهم / مش فارق / مش مهتم / عادي), or delays past a month
- timing "now": says now/today/immediately/الآن/دلوقتي/الحين/فوراً
- timing "week": says next week/بعد أسبوع/الأسبوع الجاي, or any short-term timing within a week (e.g., tomorrow/بكرة, in two days/كمان يومين, in a few days/كمان كام يوم, this week/خلال أيام, soon, or confirming/verifying in a few days/يومين وأأكد/بكرة هقولك/بكرة هأكد/يومين وهاكد)
- timing "month": says next month/بعد شهر/الشهر الجاي, or a month later
- timing "later": says later/بعدين/مرة أخرى/not now/in the future (with no short-term timeline specified), or says it's not important/not urgent
- name: Extracted full name of the customer if they just shared it or introduced themselves. Look at the latest user message and the history. If the customer corrects their name, extract the corrected one. If not mentioned or not clear, return null.
- interests: Extract the products of interest that the customer has shown interest in or agreed to in this turn or recent history.
  * Only include courses/tracks/diplomas that the customer actually agreed to, is interested in, or is actively asking about.
  * Pay attention to the customer's agreement (e.g., if the assistant offered Python or General Programming, and the customer replied "خليها اساسيات البرمجة", then "Introduction to Python Programming" is the agreed interest because that is the official general programming fundamentals course).
  * The interest names in the output lists must match EXACTLY the names from the official lists above.
- rejected_interests: Extract the products that the customer explicitly rejects, declines, says they don't want, or changes their mind about (e.g. "I don't want Web development anymore" or "I want AI instead of Web" -> reject Web, interest AI) in this turn or recent history.
- Return ONLY the JSON, no explanation."""

        user_content = f"Recent conversation history:\n{history_str}\n\nLatest Customer Message: {text}"

        try:
            client = _get_classifier()
            try:
                resp = client.chat.completions.create(
                    model=GROQ_CLASSIFIER_MODEL,
                    messages=[
                        {"role": "system", "content": CLASSIFIER_SYSTEM},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.0,
                    max_tokens=450,
                    response_format={"type": "json_object"},
                )
            except Exception as api_err:
                err_msg = str(api_err).lower()
                is_invalid_model = any(k in err_msg for k in ["decommissioned", "not found", "model", "unknown", "invalid", "does not exist", "400", "404"])
                if is_invalid_model and GROQ_CLASSIFIER_MODEL != "llama-3.3-70b-versatile":
                    logger.warning(f"⚠️ Classifier model {GROQ_CLASSIFIER_MODEL} failed/decommissioned, retrying with llama-3.3-70b-versatile...")
                    resp = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": CLASSIFIER_SYSTEM},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=0.0,
                        max_tokens=450,
                        response_format={"type": "json_object"},
                    )
                else:
                    raise api_err

            raw = resp.choices[0].message.content.strip()
            result = json.loads(raw)
            # Normalise
            result.setdefault("language", "ar")
            result.setdefault("dialect", "standard")
            result.setdefault("intent", "browsing")
            result.setdefault("temperature", "cold")
            result.setdefault("buying_signals", [])
            result.setdefault("objections", [])
            result.setdefault("timing", None)
            result.setdefault("payment_methods", [])
            result.setdefault("has_phone", False)
            result.setdefault("name", None)
            result.setdefault("interests", {"courses": [], "tracks": [], "diplomas": []})
            result.setdefault("rejected_interests", {"courses": [], "tracks": [], "diplomas": []})
            self._last_classification = result
            self._last_classified_text = text
            return result
        except Exception as e:
            logger.warning(f"Classifier LLM failed, falling back to regex: {e}")
            # Return empty dict — callers will fall back to regex
            return {}

    # ──────────────────────────────────────────────────────────────────────────
    # SIGNAL DETECTION — LLM-primary, regex fallback
    # ──────────────────────────────────────────────────────────────────────────

    def detect_language(self, text: str) -> str:
        """Primary: LLM classifier. Fallback: Arabic character ratio."""
        clf = self._classify_with_llm(text)
        if clf:
            lang = clf.get("language", "")
            return "ar" if lang == "ar" else ("en" if lang == "en" else "en")
        # Regex fallback
        arabic_chars = len(re.findall(
            r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text
        ))
        return "ar" if arabic_chars > len(text) * 0.3 else "en"

    def detect_dialect(self, text: str) -> str:
        """Primary: LLM classifier. Fallback: keyword matching."""
        clf = self._classify_with_llm(text)
        if clf:
            return clf.get("dialect", "standard") or "standard"
        # Regex fallback
        egyptian = re.findall(r"\b(إيه|مين|كدة|ده|دي|دول|كده|بقي|خلاص|أهو|كام|دلوقت)\b", text)
        saudi    = re.findall(r"\b(وش|ليش|ابغى|تبغى|الحين|قاعد|هذا|هاذي)\b", text)
        syrian   = re.findall(r"\b(شو|مشان|هلق|كرمال|عنجد|منيح|لأنو)\b", text)
        if len(egyptian) >= len(saudi) and len(egyptian) >= len(syrian) and len(egyptian) > 0:
            return "egyptian"
        elif len(saudi) >= len(syrian) and len(saudi) > 0:
            return "saudi"
        elif len(syrian) > 0:
            return "syrian"
        return "standard"

    def detect_intent(self, text: str) -> str:
        """LLM primary merged with regex — takes the most specific intent."""
        valid_intents = {"browsing", "comparing", "price_sensitive", "hesitant", "ready_to_enroll"}
        _rank = {"browsing": 0, "hesitant": 1, "comparing": 2, "price_sensitive": 2, "ready_to_enroll": 3}
        clf = self._classify_with_llm(text)
        llm_intent = clf.get("intent", "browsing") if clf else "browsing"
        llm_intent = llm_intent if llm_intent in valid_intents else "browsing"
        # Regex scoring
        text_lower = text.lower()
        scores: dict[str, int] = {intent: 0 for intent in INTENT_PATTERNS}
        for intent, patterns in INTENT_PATTERNS.items():
            for p in patterns:
                if re.search(p, text_lower):
                    scores[intent] += 2
        for pattern in BUYING_SIGNAL_PATTERNS:
            if re.search(pattern, text_lower):
                scores["ready_to_enroll"] += 1
        max_score = max(scores.values()) if scores else 0
        regex_intent = max(scores, key=scores.get) if max_score > 0 else "browsing"
        # Return the more specific of the two
        return llm_intent if _rank.get(llm_intent, 0) >= _rank.get(regex_intent, 0) else regex_intent

    def detect_buying_signals(self, text: str) -> list[str]:
        """Merges LLM + regex buying signals."""
        clf = self._classify_with_llm(text)
        llm_signals = [str(s) for s in clf.get("buying_signals", [])] if clf else []
        # Always also run regex (catch what LLM may miss)
        regex_signals: list[str] = []
        text_lower = text.lower()
        for pattern, signal_text in [
            (r"(how (do|can) i (enroll|register|sign up|join)|i want to (enroll|register|join|buy|purchase)|سجلني|سجّلني|كيف أسجل|(?:^|\s)(سجل|اسجل|اشترك)(?=\s|$|[\W_]))", "طلب تسجيل"),
            (r"(how much|price|cost|سعر|تكلفة|كم|بكم)", "سؤال عن السعر"),
            (r"(installment|تقسيط|دفعات|أقساط)", "اهتمام بالتقسيط"),
            (r"(next batch|next cohort|موعد|تاريخ البدء|start date)", "سؤال عن موعد البدء"),
            (r"(discount|خصم|تخفيض)", "اهتمام بالخصم"),
            (r"(certificate|شهادة|accredited|معتمدة)", "اهتمام بالشهادة"),
            (r"(call me|contact me|تواصل|whatsapp|اتصل)", "طلب تواصل"),
            (r"(i'm ready|أنا جاد|مستعد|أريد التسجيل)", "جاهز للتسجيل"),
            (r"\d{8,}", "توفير رقم الهاتف"),
        ]:
            if re.search(pattern, text_lower):
                regex_signals.append(signal_text)
        # Union: LLM + regex, deduplicated
        seen = set()
        combined = []
        for s in llm_signals + regex_signals:
            if s not in seen:
                seen.add(s)
                combined.append(s)
        return combined

    def detect_objections(self, text: str) -> list[str]:
        """Primary: LLM classifier. Fallback: pattern list."""
        valid_objections = {"price", "time", "experience", "trust", "refund", "comparison"}
        clf = self._classify_with_llm(text)
        if clf and clf.get("objections") is not None:
            return [o for o in clf.get("objections", []) if o in valid_objections]
        # Regex fallback
        objections: list[str] = []
        text_lower = text.lower()
        for pattern, obj_type in OBJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                objections.append(obj_type)
        return objections

    def detect_cold_signals(self, text: str) -> list[str]:
        """Used internally. Returns cold signals via regex (LLM temperature covers this)."""
        signals: list[str] = []
        text_lower = text.lower()
        for pattern, signal_text in [
            (r"(not interested|لا اهتمام|لا أريد|مش مهتم|ما بدي)", "عدم اهتمام"),
            (r"(no thanks|لا شكرا|لا شكراً|no thank you)", "رفض"),
            (r"(maybe later|بعدين|لاحقاً|another time|مرة أخرى)", "تسويف"),
            (r"(just browsing|just looking|أتصفح|أشوف)", "تصفح"),
            (r"(leave me alone|اتركني|خليني|سيبي)", "انزعاج"),
            (r"(not now|مش دلوقت|مش الحين|ليس الآن)", "ليس الآن"),
            (r"(i don't need|ما بحتاج|مش محتاج|لا أحتاج)", "لا حاجة"),
        ]:
            if re.search(pattern, text_lower):
                signals.append(signal_text)
        return signals

    def detect_timing(self, text: str) -> str | None:
        """Primary: LLM classifier. Fallback: pattern list."""
        clf = self._classify_with_llm(text)
        if clf and "timing" in clf:
            t = clf.get("timing")
            return t if t in ("now", "week", "month", "later") else None
        # Regex fallback
        text_lower = text.lower()
        if any(re.search(p, text_lower) for p in TIMING_NOW_PATTERNS):
            return "now"
        if any(re.search(p, text_lower) for p in TIMING_WEEK_PATTERNS):
            return "week"
        if any(re.search(p, text_lower) for p in TIMING_MONTH_PATTERNS):
            return "month"
        if any(re.search(p, text_lower) for p in TIMING_LATER_PATTERNS):
            return "later"
        return None

    def validate_email(self, email: str) -> bool:
        try:
            EmailStr._validate(email)
            return True
        except Exception:
            return False

    def detect_payment_methods(self, text: str) -> list[str]:
        """Merges LLM + regex payment method detection."""
        clf = self._classify_with_llm(text)
        llm_methods = [str(m) for m in clf.get("payment_methods", [])] if clf else []
        # Always also run regex (LLM sometimes misses abbreviated mentions)
        regex_methods = []
        text_lower = text.lower()
        for pattern, label in PAYMENT_METHOD_PATTERNS:
            if re.search(pattern, text_lower):
                regex_methods.append(label)
        # Union deduplicated
        seen = set()
        combined = []
        for m in llm_methods + regex_methods:
            key = m.lower()
            if key not in seen:
                seen.add(key)
                combined.append(m)
        return combined

    def get_temperature(self, text: str) -> str:
        """Merges LLM + regex temperature — takes the max (hottest) between both."""
        _rank = {"cold": 0, "warm": 1, "hot": 2}
        # LLM classification
        clf = self._classify_with_llm(text)
        llm_temp = clf.get("temperature", "cold") if clf else "cold"
        llm_temp = llm_temp if llm_temp in _rank else "cold"
        # Regex classification (always run as safety net)
        text_lower = text.lower()
        signals = self.detect_buying_signals(text)
        objections = self.detect_objections(text)
        intent = self.detect_intent(text)
        hot_enroll = bool(re.search(
            r"(سجلني|سجّلني|اسجل(ني)?|أريد التسجيل|عايز اسجل|بدي سجل|ابغى اسجل"
            r"|enroll me|sign me up|i want to (enroll|register|join|buy)"
            r"|how (do|can) i (enroll|register|sign up|join)"
            r"|الخطوة التالية|next step|كيف أسجل|how to start)",
            text_lower
        ))
        has_phone = bool(re.search(r"(?<!\w)(\+?01\d{9})(?!\w)", text))
        hot_signals_set = {"طلب تسجيل", "جاهز للتسجيل", "طلب تواصل"}
        if hot_enroll or has_phone or any(s in hot_signals_set for s in signals):
            regex_temp = "hot"
        elif bool(re.search(
            r"(دبلوم|دبلومة|diploma|مسار|track|برنامج|program|full.?stack|data.?sci"
            r"|cyber|web.?dev|flutter|devops|cloud|mobile|ai|تطبيقات"
            r"|سعر|price|cost|تكلفة|بكم|كم|discount|خصم|محتوى|content|مدة"
            r"|duration|شهادة|certificate|تقسيط|installment|مقارنة|compare"
            r"|instapay|انستاباي|vodafone|فودافون|فيزا|visa|فوري|fawry|ادفع|بيها|طريقة الدفع|payment)",
            text_lower
        )) or signals or intent in ("comparing", "price_sensitive"):
            regex_temp = "warm"
        else:
            regex_temp = "cold"
        # Return the hottest of the two
        return max(llm_temp, regex_temp, key=lambda t: _rank[t])

    def extract_lead_info(self, text: str) -> dict[str, str]:
        info: dict[str, str] = {}
        _non_name_words = {
            "معنديش", "ماعنديش", "ما عندي", "ليس لدي", "لا", "باحب", "بحب", "أحب",
            "عايز", "عاوز", "بدي", "أريد", "اريد", "أنا", "انا", "اسمي", "في",
            "من", "الى", "إلى", "على", "عن", "كان", "هذا", "هذه", "ذلك", "تلك",
            "نعم", "أهلا", "اهلا", "مرحبا", "hello", "hi", "yes", "no",
            "شكرا", "شكراً", "عفوا", "عفواً", "ممكن", "هل", "كم", "ما", "لماذا",
            "أستفسر", "استفسر", "سؤال", "عندي", "ودي", "أبغى", "ابغى", "تبغى",
        }

        # 1. Try LLM classifier first for name extraction
        clf = self._classify_with_llm(text)
        if clf and clf.get("name"):
            raw = clf["name"].strip()
            cleaned = re.sub(r"[،,].*$", "", raw).strip()
            cleaned = re.sub(r"\s+\d+\s*.*$", "", cleaned).strip()
            cleaned = re.sub(r"\s+(و|من|في|على|مع|وب|from|in)\s+\w+.*$", "", cleaned).strip()
            if cleaned and len(cleaned) > 1 and len(cleaned) < 30 and cleaned.lower() not in _non_name_words:
                info["name"] = cleaned

        # 2. Fallback to name regex patterns
        if "name" not in info:
            name_patterns = [
                r"(?:اسمي|الاسم|my name is|My name is)\s*[:\s]+([\u0600-\u06FF\w]+(?:\s+[\u0600-\u06FF\w]+){1,2})",
                r"(?:my name is|My name is)\s*[:\s]+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,2})",
                r"^([\u0600-\u06FF\w]+(?:\s+[\u0600-\u06FF\w]+){0,2})\s+\d",
            ]
            for p in name_patterns:
                m = re.search(p, text)
                if m:
                    raw = m.group(1).strip()
                    cleaned = re.sub(r"[،,].*$", "", raw).strip()
                    cleaned = re.sub(r"\s+\d+\s*.*$", "", cleaned).strip()
                    cleaned = re.sub(r"\s+(و|من|في|على|مع|وب|from|in)\s+\w+.*$", "", cleaned).strip()
                    if cleaned and len(cleaned) > 1 and len(cleaned) < 30 and cleaned.lower() not in _non_name_words:
                        info["name"] = cleaned
                        break

        phone_patterns = [
            r"(?:رقم[يي]?|phone|whatsapp|واتس|موبايل|تلفون|جوال|tel)\s*[:\s]*((?:\+?\d{1,3})?[\d\s\-\(\)]{7,15})",
        ]
        for p in phone_patterns:
            m = re.search(p, text)
            if m:
                phone = m.group(1).strip()
                digits = re.sub(r"\D", "", phone)
                if len(digits) == 11 and digits.startswith("01"):
                    info["phone"] = digits
                    break

        if "phone" not in info:
            phone_match = re.search(r"(?<!\w)(\+?\d[\d\s\-\(\)]{7,14})(?!\w)", text)
            if phone_match:
                digits = re.sub(r"\D", "", phone_match.group(1))
                if len(digits) == 11 and digits.startswith("01"):
                    info["phone"] = digits

        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match and self.validate_email(email_match.group(0)):
            info["email"] = email_match.group(0)

        # Detect invalid phone attempts (digits that look like a phone but aren't valid)
        phone_attempt = re.search(r"(?<!\w)01\d{2,8}(?!\w)", text)
        self.invalid_phone_attempt = bool(phone_attempt) and "phone" not in info

        known_locations = ["مصر", "السعودية", "الأردن", "سوريا", "الإمارات", "ليبيا",
                           "تونس", "الجزائر", "المغرب", "فلسطين", "العراق", "السودان",
                           "اليمن", "عمان", "البحرين", "الكويت", "قطر", "لبنان"]
        for loc in known_locations:
            if loc in text:
                info["city"] = loc
                break

        self.collected_info.update(info)
        return info

    def sanitize_input(self, text: str) -> str:
        def _replace(m: re.Match) -> str:
            digits = re.sub(r"\D", "", m.group(0))
            if len(digits) == 11 and digits.startswith("01"):
                return m.group(0)
            return ""
        return re.sub(r"(?<!\w)\+?\d[\d\s\-\(\)]{3,13}(?!\w)", _replace, text).strip()

    def generate_response(self, user_input: str, user_id: str = "guest", conversation_id: str = "default") -> str:
        lang = self.detect_language(user_input)
        dialect = self.detect_dialect(user_input)
        intent = self.detect_intent(user_input)
        buying_signals = self.detect_buying_signals(user_input)
        objections = self.detect_objections(user_input)
        timing = self.detect_timing(user_input)
        temperature = self.get_temperature(user_input)
        payment_methods = self.detect_payment_methods(user_input)
        self.invalid_phone_attempt = False
        lead_info = self.extract_lead_info(user_input)

        # Timing-based temperature override
        # now=hot, week=warm, month=cold, later=cold
        _rank = {"cold": 0, "warm": 1, "hot": 2}
        if timing == "now":
            temperature = max([temperature, "hot"], key=lambda t: _rank[t])
            self.needs_timing = False
            self.asked_timing = True
        elif timing == "week":
            temperature = max([temperature, "warm"], key=lambda t: _rank[t])
            self.needs_timing = False
            self.asked_timing = True
        elif timing == "month":
            temperature = "cold"
            self.needs_timing = False
            self.asked_timing = True
        elif timing == "later":
            temperature = "cold"
            self.asked_timing = True
            self.needs_timing = False

        # Strip invalid phone numbers from LLM-facing text
        clean_input = self.sanitize_input(user_input)
        self.conversation_history.append({"role": "user", "content": clean_input})

        # Save user message to database
        user_message_id = self.crm.save_message(user_id, conversation_id, "user", clean_input)

        # RAG Context Retrieval with intent parameter
        context, tool_calls = self.retriever.retrieve_context(clean_input, intent=intent)

        # Inject payment method availability info into context
        if payment_methods:
            methods_str = "، ".join(payment_methods) if lang == "ar" else ", ".join(payment_methods)
            if lang == "ar":
                context += (
                    f"\n\n**معلومة الدفع:** كيف تدعم طرق الدفع التالية: {methods_str}. "
                    "أخبر العميل أن هذه الطريقة متاحة وشجّعه على الاستفسار عن خطوات الدفع."
                )
            else:
                context += (
                    f"\n\n**Payment Info:** Kayf supports the following payment methods: {methods_str}. "
                    "Inform the customer this method is available and encourage them to ask about payment steps."
                )

        # If user tried an invalid phone, tell the LLM to ask for correction
        if self.invalid_phone_attempt:
            note_ar = "\n\n**ملاحظة:** العميل أدخل رقماً غير صحيح. اطلب منه رقم محمول مصري صحيح مكون من 11 رقم ويبدأ بـ 01."
            note_en = "\n\n**Note:** The customer entered an invalid phone number. Ask them for a correct 11-digit Egyptian mobile number starting with 01."
            context += note_ar if lang == "ar" else note_en

        # Create lead ticket if not yet created and there's enough signal
        if self.current_lead is None:
            existing_ticket = None
            for t in self.crm.get_all_tickets():
                if t.get("conversation_id") == conversation_id or (user_id != "guest" and t.get("user_id") == user_id):
                    existing_ticket = t
                    break
            if existing_ticket:
                self.current_lead = CRMTicket.model_validate(existing_ticket)
            elif temperature in ("hot", "warm") or lead_info.get("name") or lead_info.get("phone") or buying_signals:
                self.current_lead = CRMTicket()
                self.current_lead.user_id = user_id
                self.current_lead.conversation_id = conversation_id
                self.current_lead.lead.language = "Arabic" if lang == "ar" else "English"
                self.current_lead.lead.dialect = dialect

        if self.current_lead:
            self.current_lead.user_id = user_id
            self.current_lead.conversation_id = conversation_id
            for signal in buying_signals:
                if signal not in self.current_lead.assessment.buying_signals:
                    self.current_lead.assessment.buying_signals.append(signal)
            for obj in objections:
                if obj not in self.current_lead.assessment.objections:
                    self.current_lead.assessment.objections.append(obj)
            if timing == "now":
                self.current_lead.assessment.temperature = "hot"
            elif timing == "week":
                self.current_lead.assessment.temperature = "warm"
            elif timing in ("month", "later"):
                self.current_lead.assessment.temperature = "cold"
            else:
                self.current_lead.assessment.temperature = temperature
            if intent != "browsing":
                self.current_lead.assessment.intent = intent
            if self.current_lead.products.goal:
                self.current_lead.assessment.goal = self.current_lead.products.goal
            if lead_info.get("name"):
                self.current_lead.lead.name = lead_info["name"]
            if lead_info.get("phone"):
                self.current_lead.lead.phone = lead_info["phone"]
            if lead_info.get("email"):
                self.current_lead.lead.email = lead_info["email"]
            if lead_info.get("city"):
                self.current_lead.lead.city = lead_info["city"]
            self.current_lead.lead.dialect = dialect
            self._track_products(user_input)

        response = self._llm_response(
            clean_input, lang, dialect, intent, temperature,
            buying_signals, objections, context, user_id, conversation_id,
            user_message_id, tool_calls
        )

        # If LLM just asked the timing question, wait for answer before capturing
        if not self.asked_timing and self.current_lead and self.current_lead.lead.name and self.current_lead.lead.phone:
            timing_asked = re.search(
                r"(حابب تسجل|تسجل دلوقتي|ولا بعد أسبوع|Would you like to enroll|now or after)",
                response, re.IGNORECASE
            )
            if timing_asked:
                self.needs_timing = True

        # Check if we should update/save the ticket
        if self.current_lead:
            nm = self.current_lead.lead.name
            ph = self.current_lead.lead.phone
            em = self.current_lead.lead.email
            temp = self.current_lead.assessment.temperature
            # Clean up bad names
            if nm:
                nm_lower = nm.lower().strip()
                _bad_names = {"معنديش", "ماعنديش", "ما عندي", "ليس لدي", "لا", "باحب", "بحب", "أحب",
                              "عايز", "عاوز", "بدي", "أريد", "اريد", "أنا", "انا", "اسمي",
                              "نعم", "أهلا", "اهلا", "مرحبا", "hello", "hi"}
                if nm_lower in _bad_names or any(b in nm_lower for b in ["عنديش", "ماعند", "عايز", "بدي"]):
                    nm = None
                    self.current_lead.lead.name = None
            # Validate phone — must be 11 digits starting with 01
            phone_valid = bool(ph and len(re.sub(r"\D", "", ph)) == 11 and ph.startswith("01"))
            # Validate email if present
            email_valid = not em or self.validate_email(em)
            if not email_valid:
                self.current_lead.lead.email = None
                em = None

            has_name_phone = bool(nm and phone_valid and len(nm) > 1)

            # Determine if this is a qualified lead that should be in CRM
            is_qualified = False
            if temp == "hot" and phone_valid:
                is_qualified = True
            elif temp == "warm" and has_name_phone:
                is_qualified = True
            elif has_name_phone:
                is_qualified = True

            # If it is qualified, or if it already has a ticket_id (previously saved), save/update it!
            if is_qualified or self.current_lead.ticket_id:
                summary = self._generate_summary(lang)
                self.current_lead.conversation_summary = summary
                temp_now = self.current_lead.assessment.temperature
                if lang == "ar":
                    if temp_now == "hot":
                        self.current_lead.recommended_action = "التواصل مع العميل فوراً عبر واتساب لإتمام التسجيل"
                    elif temp_now == "warm":
                        self.current_lead.recommended_action = "التواصل مع العميل خلال 24-48 ساعة لمتابعة الاهتمام"
                    else:
                        self.current_lead.recommended_action = "إضافة العميل لقائمة المتابعة الشهرية"
                else:
                    if temp_now == "hot":
                        self.current_lead.recommended_action = "Contact immediately via WhatsApp to complete enrollment"
                    elif temp_now == "warm":
                        self.current_lead.recommended_action = "Follow up within 24-48 hours to nurture interest"
                    else:
                        self.current_lead.recommended_action = "Add to monthly follow-up list"
                self.crm.save_ticket(self.current_lead)
                
                # Check if we should append the user-facing "Your information has been saved" confirmation
                # We only show it once when both name & phone are collected, timing is satisfied,
                # and we haven't displayed it in this conversation session yet.
                if has_name_phone and not self.lead_captured_this_session and not self.needs_timing:
                    self.lead_captured_this_session = True
                    if lang == "ar":
                        response += "\n\n📋 **تم تسجيل بياناتك!** أحد مندوبي المبيعات سيتواصل معك قريباً."
                    else:
                        response += "\n\n📋 **Your information has been saved!** A sales rep will contact you soon."

        self.conversation_history.append({"role": "assistant", "content": response})
        self.crm.save_message(user_id, conversation_id, "assistant", response)

        return response

    def _track_products(self, text: str) -> None:
        if not self.current_lead:
            return
        
        clf = self._classify_with_llm(text)
        if clf and ("interests" in clf or "rejected_interests" in clf):
            # 1. Handle rejected/negated interests first
            rejected = clf.get("rejected_interests", {"courses": [], "tracks": [], "diplomas": []})
            if rejected:
                for c in rejected.get("courses", []):
                    if c in self.current_lead.products.courses:
                        self.current_lead.products.courses.remove(c)
                for t in rejected.get("tracks", []):
                    if t in self.current_lead.products.tracks:
                        self.current_lead.products.tracks.remove(t)
                for d in rejected.get("diplomas", []):
                    if d in self.current_lead.products.diplomas:
                        self.current_lead.products.diplomas.remove(d)

            # 2. Handle positive interests
            interests = clf.get("interests", {"courses": [], "tracks": [], "diplomas": []})
            courses = interests.get("courses", [])
            tracks = interests.get("tracks", [])
            diplomas = interests.get("diplomas", [])
            
            # Add new interests if they are not already in the list
            for c in courses:
                if c not in self.current_lead.products.courses:
                    self.current_lead.products.courses.append(c)
            for t in tracks:
                if t not in self.current_lead.products.tracks:
                    self.current_lead.products.tracks.append(t)
            for d in diplomas:
                if d not in self.current_lead.products.diplomas:
                    self.current_lead.products.diplomas.append(d)

            # Update goal based on tracks/diplomas
            for t_name in self.current_lead.products.tracks + self.current_lead.products.diplomas:
                t_name_lower = t_name.lower()
                if "web" in t_name_lower:
                    self.current_lead.products.goal = "تعلم تطوير الويب"
                elif "data" in t_name_lower:
                    self.current_lead.products.goal = "تعلم علوم البيانات"
                elif "ai" in t_name_lower:
                    self.current_lead.products.goal = "تعلم الذكاء الاصطناعي"
                elif "cyber" in t_name_lower or "soc" in t_name_lower or "pentesting" in t_name_lower or "penetration" in t_name_lower:
                    self.current_lead.products.goal = "تعلم الأمن السيبراني"
            return

        # 1. Fallback to regex-based tracking (Handle negative preferences / changing mind)
        text_lower = text.lower()
        clean_text = text_lower
        
        # Arabic negations
        ar_neg_matches = list(re.finditer(r"\b(مش عايز|مش حابب|لا أريد|ما بدي|ما ابغى|بطلت|منيش عايز|مو عاجبني)\s+([\u0600-\u06FF\w\s\-]+?)(?=\s+(و|وعايز|لكن|بس|بل|and|but)\b|$)", text_lower))
        if not ar_neg_matches and re.search(r"\b(مش عايز|مش حابب|لا أريد|ما بدي|ما ابغى|بطلت)\b", text_lower):
            # Fallback simple negation match if no coordinator
            ar_neg_matches = list(re.finditer(r"\b(مش عايز|مش حابب|لا أريد|ما بدي|ما ابغى|بطلت)\s+([\u0600-\u06FF\w\s\-]+)$", text_lower))
            
        for m in ar_neg_matches:
            negated_target = m.group(2)
            clean_text = clean_text.replace(m.group(0), "")
            if re.search(r"(ويب|web|javascript|js|front|فرونت)", negated_target):
                self.current_lead.products.courses = [c for c in self.current_lead.products.courses if "web" not in c.lower() and "js" not in c.lower() and "react" not in c.lower() and "html" not in c.lower()]
                self.current_lead.products.tracks = [t for t in self.current_lead.products.tracks if "web" not in t.lower() and "javascript" not in t.lower() and "full-stack" not in t.lower()]
                self.current_lead.products.diplomas = [d for d in self.current_lead.products.diplomas if "web" not in d.lower() and "javascript" not in d.lower()]
                if self.current_lead.products.goal == "تعلم تطوير الويب":
                    self.current_lead.products.goal = None
            if re.search(r"(ai|ذكاء|artificial|intelligence|deep|machine|الذكاء)", negated_target):
                self.current_lead.products.courses = [c for c in self.current_lead.products.courses if "ai" not in c.lower() and "tensorflow" not in c.lower() and "deep" not in c.lower() and "nlp" not in c.lower() and "vision" not in c.lower()]
                self.current_lead.products.tracks = [t for t in self.current_lead.products.tracks if "ai" not in t.lower() and "deep learning" not in t.lower()]
                self.current_lead.products.diplomas = [d for d in self.current_lead.products.diplomas if "ai" not in d.lower()]
                if self.current_lead.products.goal == "تعلم الذكاء الاصطناعي":
                    self.current_lead.products.goal = None

        # English negations
        en_neg_matches = list(re.finditer(r"\b(dont want|don't want|no longer want|not interested in|change my mind about)\s+([a-zA-Z\s\-]+?)(?=\s+(and|but|or)\b|$)", text_lower))
        if not en_neg_matches and re.search(r"\b(dont want|don't want|no longer want|not interested in)\b", text_lower):
            en_neg_matches = list(re.finditer(r"\b(dont want|don't want|no longer want|not interested in)\s+([a-zA-Z\s\-]+)$", text_lower))
            
        for m in en_neg_matches:
            negated_target = m.group(2)
            clean_text = clean_text.replace(m.group(0), "")
            if re.search(r"(web|javascript|js|front)", negated_target):
                self.current_lead.products.courses = [c for c in self.current_lead.products.courses if "web" not in c.lower() and "js" not in c.lower() and "react" not in c.lower() and "html" not in c.lower()]
                self.current_lead.products.tracks = [t for t in self.current_lead.products.tracks if "web" not in t.lower() and "javascript" not in t.lower() and "full-stack" not in t.lower()]
                self.current_lead.products.diplomas = [d for d in self.current_lead.products.diplomas if "web" not in d.lower() and "javascript" not in d.lower()]
            if re.search(r"(ai|artificial|deep|machine)", negated_target):
                self.current_lead.products.courses = [c for c in self.current_lead.products.courses if "ai" not in c.lower() and "tensorflow" not in c.lower() and "deep" not in c.lower() and "nlp" not in c.lower() and "vision" not in c.lower()]
                self.current_lead.products.tracks = [t for t in self.current_lead.products.tracks if "ai" not in t.lower() and "deep learning" not in t.lower()]
                self.current_lead.products.diplomas = [d for d in self.current_lead.products.diplomas if "ai" not in d.lower()]

        # 2. Fallback scan text for positive interests
        self._scan_text_for_products(clean_text)

    def _scan_text_for_products(self, t: str) -> None:
        # Map generic "Programming Fundamentals" terms to the introductory course "Introduction to Python Programming"
        if re.search(r"\b(اساسيات البرمجة|أساسيات البرمجة|البرمجة العامة|البرمجة للمبتدئين|programming fundamentals|programming basics|intro to programming)\b", t.lower()):
            if "Introduction to Python Programming" not in self.current_lead.products.courses:
                self.current_lead.products.courses.append("Introduction to Python Programming")

        t_norm = t.replace("-", " ").replace("_", " ").replace("\u2011", " ").replace("\u2013", " ").replace("\u2014", " ")

        # Normalize Arabic technology words to English to match roadmap/course names
        t_norm = re.sub(r"(الويب|ويب)", "web", t_norm)
        t_norm = re.sub(r"(ذكاء|اصطناعي|الذكاء|ذكاء اصطناعي|ذكاء إصطناعي)", "ai", t_norm)
        t_norm = re.sub(r"(أمن سيبراني|امن سيبراني|سيبراني|الأمن|الامن|حماية|أمن|امن)", "cyber security", t_norm)
        t_norm = re.sub(r"(بيانات|البيانات)", "data", t_norm)
        t_norm = re.sub(r"(برمجة|البرمجة)", "programming", t_norm)
        t_norm = re.sub(r"(شبكات|الشبكات)", "network", t_norm)
        t_norm = re.sub(r"(اختراق|الهكر)", "hack", t_norm)

        rkeywords = ["full stack", "web dev", "web", "data science", "data analytics", "data",
                     "cyber", "soc", "pentest", "pen test", "ai", "devops", "python",
                     "security", "hack", "network", "linux", "programming",
                     "mobile", "flutter", "swift", "kotlin", "react", "node",
                     "django", "javascript", "typescript", "docker", "aws"]

        generic_words = {"diploma", "track", "live", "self", "paced", "development", "analysis", "testing",
                         "advanced", "and", "or", "for", "with", "deploma", "دبلوم", "دبلومة", "مسار", "كورس", "دورة"}

        for r in self.kb.roadmaps:
            rname_norm = r["name"].lower().replace("-", " ")
            matched = False
            for keyword in rkeywords:
                if keyword in t_norm and keyword in rname_norm:
                    matched = True
                    break
            if not matched:
                rwords = set(rname_norm.split())
                twords = set(t_norm.split())
                # Exclude generic words from overlap comparison
                specific_rwords = rwords - generic_words
                specific_twords = twords - generic_words
                if specific_rwords & specific_twords:
                    matched = True
            if matched:
                if r.get("type") == "live" and r["name"] not in self.current_lead.products.diplomas:
                    self.current_lead.products.diplomas.append(r["name"])
                elif r["name"] not in self.current_lead.products.tracks:
                    self.current_lead.products.tracks.append(r["name"])



        for c in self.kb.courses:
            cname_norm = c["name"].lower().replace("-", " ")
            cname_parts = cname_norm.split()
            cwords = set(cname_parts)
            twords = set(t_norm.split())
            matched = False
            overlap = cwords & twords
            if len(overlap) >= 2:
                matched = True
            if not matched and len(cname_parts) >= 3:
                for i in range(len(cname_parts) - 1):
                    bigram = " ".join(cname_parts[i:i+2])
                    if bigram in t_norm:
                        matched = True
                        break
            if matched and c["name"] not in self.current_lead.products.courses:
                self.current_lead.products.courses.append(c["name"])

        goal_keywords = [
            (r"(web.?dev|full.?stack|تطوير.?ويب)", "تعلم تطوير الويب"),
            (r"(data.?sci|علم.?بيانات|تحليل.?بيانات)", "تعلم علوم البيانات"),
            (r"(python|numpy|pandas|matplotlib)", "تعلم علوم البيانات"),
            (r"(ai|ذكاء.?اصطناعي|machine.?learn|deep.?learn)", "تعلم الذكاء الاصطناعي"),
            (r"(cyber|أمن.?سيبراني|soc|اختراق|hack|security|secu)", "تعلم الأمن السيبراني"),
            (r"(mobile|تطبيقات.?جوال|flutter|swift|kotlin)", "تعلم تطوير التطبيقات"),
            (r"(devops|cloud|docker|kubernetes|aws|سحابي)", "تعلم DevOps والسحابة"),
        ]
        for pattern, goal in goal_keywords:
            if re.search(pattern, t) and not self.current_lead.products.goal:
                self.current_lead.products.goal = goal
                break

    def _llm_response(
        self, user_input: str, lang: str, dialect: str, intent: str,
        temperature: str, buying_signals: list[str], objections: list[str],
        context: str, user_id: str, conversation_id: str, user_message_id: str,
        tool_calls: list[dict]
    ) -> str:
        is_first = len(self.conversation_history) <= 1
        is_generic = len(user_input.strip()) < 10 or (intent == "browsing" and not re.search(r"(cybersecurity|security|soc|data\s*science|ai|artificial intelligence|web|programming|python|machine learning|deep learning|cloud|devops|mobile|hacking|pentest|network|linux|course|courses|دورات|كورسات|مسارات|diploma|دبلوم|دبلومة|available|متاحة|offer|تقدم|عندك|شو عند)", user_input.lower()))
        if is_first and is_generic and not buying_signals and not objections:
            # Even for fallback greeting, we should log a zero-cost trace so the admin can trace the entry point!
            fallback_greeting = self._fallback_greeting("en" if lang == "en" else dialect)
            self.usage_logger.log(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_message_id,
                model=GROQ_MODEL,
                provider="System (Greeting)",
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                llm_cost_usd=0.0,
                embedding_cost_usd=0.0,
                total_cost_usd=0.0,
                tool_calls=tool_calls,
                think_step="Greeting Fallback - generic query detected",
                final_response=fallback_greeting,
                latency_ms=0
            )
            return fallback_greeting

        prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN

        history_str = "\n".join(
            f"{'العميل' if lang == 'ar' else 'Customer'}: {m['content']}"
            if m["role"] == "user"
            else f"{'المساعد' if lang == 'ar' else 'Assistant'}: {m['content']}"
            for m in self.conversation_history[:-1]
        ) or "لا يوجد" if lang == "ar" else "None"

        filled = prompt.format(
            rag_context=context or ("لا يوجد سياق إضافي" if lang == "ar" else "No additional context"),
            language="العربية" if lang == "ar" else "English",
            dialect=dialect,
            intent=intent,
            temperature=temperature,
            buying_signals=", ".join(buying_signals) or ("لا توجد" if lang == "ar" else "None detected"),
            objections=", ".join(objections) or ("لا توجد" if lang == "ar" else "None"),
            collected_info=json.dumps(self.collected_info, ensure_ascii=False),
            conversation_history=history_str,
        )

        messages = [
            {"role": "system", "content": filled},
            {"role": "user", "content": user_input},
        ]

        start_time = time.time()
        attempt_model = GROQ_MODEL
        try:
            llm = _get_llm()
            try:
                resp = llm.chat.completions.create(
                    model=attempt_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=600,
                )
            except Exception as api_err:
                err_msg = str(api_err).lower()
                is_invalid_model = any(k in err_msg for k in ["decommissioned", "not found", "model", "unknown", "invalid", "does not exist", "400", "404"])
                if is_invalid_model and attempt_model != "llama-3.3-70b-versatile":
                    logger.warning(f"⚠️ Model {attempt_model} failed/decommissioned on Groq, retrying with llama-3.3-70b-versatile...")
                    attempt_model = "llama-3.3-70b-versatile"
                    resp = llm.chat.completions.create(
                        model=attempt_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=600,
                    )
                else:
                    raise api_err

            response_content = resp.choices[0].message.content.strip()
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token usage
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(resp, "usage") and resp.usage:
                prompt_tokens = getattr(resp.usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(resp.usage, "completion_tokens", 0) or 0

            # Calculate cost
            llm_cost = calculate_llm_cost(attempt_model, prompt_tokens, completion_tokens)

            # Build think step summary
            think_step = (
                f"🧠 Intent: {intent}\n"
                f"Signals: {buying_signals}\n"
                f"Dialect: {dialect}\n"
                f"Objections: {objections}\n"
                f"Temperature: {temperature}"
            )
            if attempt_model != GROQ_MODEL:
                think_step += f"\nNote: Fell back from {GROQ_MODEL} to {attempt_model}"

            # Log to usage tracker
            self.usage_logger.log(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_message_id,
                model=attempt_model,
                provider="Groq",
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                embedding_tokens=0,
                llm_cost_usd=llm_cost,
                embedding_cost_usd=0.0,
                total_cost_usd=llm_cost,
                tool_calls=tool_calls,
                think_step=think_step,
                final_response=response_content,
                latency_ms=latency_ms
            )

            return response_content

        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            fallback_resp = self._fallback_response(lang, dialect, intent, temperature, objections)
            latency_ms = int((time.time() - start_time) * 1000)
            self.usage_logger.log(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_message_id,
                model=GROQ_MODEL,
                provider="Groq (Fallback)",
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                llm_cost_usd=0.0,
                embedding_cost_usd=0.0,
                total_cost_usd=0.0,
                tool_calls=tool_calls,
                think_step=f"Config Error: {str(e)}",
                final_response=fallback_resp,
                latency_ms=latency_ms
            )
            return fallback_resp

        except Exception as e:
            logger.error(f"❌ LLM API error: {type(e).__name__}: {str(e)}")
            fallback_resp = self._fallback_response(lang, dialect, intent, temperature, objections)
            latency_ms = int((time.time() - start_time) * 1000)
            self.usage_logger.log(
                user_id=user_id,
                conversation_id=conversation_id,
                message_id=user_message_id,
                model=GROQ_MODEL,
                provider="Groq (Fallback)",
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                llm_cost_usd=0.0,
                embedding_cost_usd=0.0,
                total_cost_usd=0.0,
                tool_calls=tool_calls,
                think_step=f"API Error: {type(e).__name__} - {str(e)}",
                final_response=fallback_resp,
                latency_ms=latency_ms
            )
            return fallback_resp

    def _fallback_response(
        self, lang: str, dialect: str, intent: str,
        temperature: str, objections: list[str]
    ) -> str:
        # Check if running on Streamlit Cloud (STREAMLIT env var is set)
        on_cloud = "STREAMLIT" in os.environ
        
        if lang == "en":
            if temperature == "hot":
                msg = ("You seem really interested! 🎯 I'd love to help you get started. "
                        "Could you share your name and the best WhatsApp number to reach you?")
            else:
                msg = ("Thanks for your interest in Kayf! "
                        "Could you tell me more about what you're looking to learn? "
                        "I can recommend the right course, track, or diploma for you.")
            
            if on_cloud:
                msg += "\n\n⚠️ *Note: If you're seeing this message instead of detailed recommendations, "
                msg += "the API key may not be configured. Please check the [Streamlit Cloud setup guide](STREAMLIT_CLOUD.md).*"
            
            return msg
        
        if temperature == "hot":
            msg = ("يبدو أنك جاد في التعلم! 🎯 أقدر أساعدك في التقديم. "
                   "ممكن تعطيني اسمك ورقم واتساب عشان أرسل لك التفاصيل؟")
        else:
            msg = ("شكراً لاهتمامك في كيف! 😊 "
                   "أقدر أساعدك في إيجاد الدورة أو المسار المناسب. "
                   "وشو المجال اللي ببالك؟")
        
        if on_cloud:
            msg += "\n\n⚠️ *ملاحظة: إذا كنت تشاهد هذه الرسالة بدل التوصيات المفصلة، "
            msg += "قد لا يكون مفتاح API مكوناً. يرجى التحقق من [دليل إعداد Streamlit Cloud](STREAMLIT_CLOUD.md).*"
        
        return msg

    def _fallback_greeting(self, dialect: str) -> str:
        if dialect == "en":
            return (
                "Welcome to Kayf! 👋 I'm your learning advisor.\n\n"
                "I can help you find the perfect course, track, or diploma. Whether you're into "
                "AI, cybersecurity, data science, web development, or something else — just let me know.\n\n"
                "💬 **Quick question:** What field are you interested in? Or if you're not sure yet, "
                "tell me a bit about what you'd like to learn or achieve, and I'll recommend the best options for you!"
            )
        if dialect == "saudi":
            return (
                "مرحباً بك في كيف! 👋 أنا مستشارك التعليمي.\n\n"
                "ودك تتعلّم شي جديد؟ أقدر أساعدك تلقى الدورة أو المسار أو الدبلومة المناسبة لك. "
                "سواء كان في الذكاء الاصطناعي، الأمن السيبراني، علوم البيانات، تطوير الويب — أو أي مجال ثاني.\n\n"
                "💬 **سؤال سريع:** وش المجال اللي تبغاه؟ أو إذا مو متأكد، قلي شوي عن اللي تبغى تتعلمه أو تحققه "
                "وأعطيك أفضل الاقتراحات!"
            )
        elif dialect == "egyptian":
            return (
                "أهلاً بيك في كيف! 👋 أنا مستشارك التعليمي.\n\n"
                "عايز تتعلم حاجة جديدة؟ أقدر أساعدك تلاقي الكورس أو المسار أو الدبلومة اللي تناسبك. "
                "سواء في الذكاء الاصطناعي، الأمن السيبراني، علوم البيانات، تطوير الويب — أو أي مجال تاني.\n\n"
                "💬 **سؤال سريع:** إيه المجال اللي في بالك؟ أو لو مش متأكد، قولي شوية عن اللي عايز تتعلمه "
                "أو تحققه وأديك أفضل الاقتراحات!"
            )
        elif dialect == "syrian":
            return (
                "مرحباً بك في كيف! 👋 أنا مستشارك التعليمي.\n\n"
                "بدك تتعلم شي جديد؟ فيني أساعدك تلاقي الدورة أو المسار أو الدبلومة المناسبة. "
                "سواء كان في الذكاء الاصطناعي، الأمن السيبراني، علوم البيانات، تطوير الويب — أو أي مجال تاني.\n\n"
                "💬 **سؤال سريع:** شو المجال اللي ببالك؟ أو إذا مو متأكد، قلي شوي عن اللي بدك تتعلمه "
                "أو تحققه وأعطيك أفضل الاقتراحات!"
            )
        return (
            "مرحباً بك في كيف! 👋 أنا مستشارك التعليمي.\n\n"
            "أستطيع مساعدتك في العثور على الدورة أو المسار أو الدبلومة المناسبة. "
            "سواء في الذكاء الاصطناعي، الأمن السيبراني، علوم البيانات، تطوير الويب — أو أي مجال آخر.\n\n"
            "💬 **سؤال سريع:** ما هو المجال الذي يهمك؟ أو إذا لم تكن متأكداً، أخبرني قليلاً عن "
            "ما ترغب في تعلمه أو تحقيقه وسأقدم لك أفضل الاقتراحات!"
        )

    def _generate_summary(self, lang: str) -> str:
        if not self.current_lead:
            return ""
        products = self.current_lead.products
        assessment = self.current_lead.assessment
        lead = self.current_lead.lead
        if lang == "ar":
            parts = [
                f"محادثة مع عميل يبحث في مجال المنتجات: {'، '.join(products.courses + [f'دبلومة {d}' for d in products.diplomas] + products.tracks) or 'غير محدد'}."
            ]
            if assessment.buying_signals:
                parts.append(f"إشارات شراء: {'، '.join(assessment.buying_signals)}.")
            if assessment.objections:
                parts.append(f"اعتراضات: {'، '.join(assessment.objections)}.")
            parts.append(f"تقييم العميل: {assessment.temperature}.")
            if lead.name:
                parts.append(f"الاسم: {lead.name}.")
            if lead.phone:
                parts.append(f"رقم التواصل: {lead.phone}.")
            return " ".join(parts)
        summary = f"Conversation with a prospect interested in: {', '.join(products.courses + products.tracks + [f'Diploma: {d}' for d in products.diplomas]) or 'Not specified'}."
        if assessment.buying_signals:
            summary += f" Signals: {', '.join(assessment.buying_signals)}."
        if assessment.objections:
            summary += f" Objections: {', '.join(assessment.objections)}."
        summary += f" Temperature: {assessment.temperature}."
        return summary
