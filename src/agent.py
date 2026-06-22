import json
import os
import re
import logging
from typing import Any

from openai import OpenAI

from src.rag import KnowledgeBase, RAGRetriever
from src.crm import CRMClient, CRMTicket, LeadInfo, ProductsOfInterest, LeadAssessment

# Set up logging for debugging
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")

_llm_client: OpenAI | None = None

def _get_llm() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        if not OPENROUTER_API_KEY:
            logger.error("❌ OPENROUTER_API_KEY is not set. See STREAMLIT_CLOUD.md for setup instructions.")
            raise ValueError("OPENROUTER_API_KEY environment variable is required. See STREAMLIT_CLOUD.md")
        if OPENROUTER_API_KEY.startswith("<") or "REDACTED" in OPENROUTER_API_KEY:
            logger.error("❌ OPENROUTER_API_KEY is a placeholder. Set the real key in Streamlit Cloud Secrets.")
            raise ValueError("OPENROUTER_API_KEY is not configured properly")
        _llm_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://kayfa.com",
                "X-Title": "Kayf AI Sales Agent",
            },
        )
        logger.info("✓ LLM client initialized successfully")
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
- لا تخترع معلومات — استخدم فقط البيانات المقدمة في قاعدة المعرفة أدناه
- لا تذكر سعراً أو اسم دورة غير موجود في قاعدة المعرفة
- إذا سألك العميل عن شيء خارج مجال كيف، قل بلطف أنك متخصص في منتجات كيف واعرض المساعدة في مجال آخر
- عند ظهور إشارات شراء قوية، اسأل عن معلومات التواصل (الاسم، رقم واتساب) بلطف
- لا تكن انتهازياً — كن مفيداً وصادقاً أولاً
- استخدم الرموز التعبيرية باعتدال

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
- إذا تم تسجيل العميل كـ "hot lead"، أخبره أنه تم تسجيل بياناته."""


SYSTEM_PROMPT_EN = """You are an AI sales agent for Kayf, a leading Arabic tech education platform. Kayf offers courses, tracks, and diplomas in technology fields like AI, cybersecurity, data science, and web development.

## Personality:
- You are a friendly, persuasive, and professional sales consultant
- You answer only from the knowledge base — never invent prices or courses
- Your goal: understand the visitor's need, recommend the right product, handle objections, and move toward enrollment

## Strict rules:
- Never make up information — use only the knowledge base provided below
- Never mention a price or course not in the knowledge base
- If asked about something outside Kayf, politely say you specialize in Kayf products and offer to help with another topic
- When strong buying signals appear, gently ask for contact info (name, WhatsApp)
- Don't be pushy — be genuinely helpful first
- Use emojis sparingly

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
- If captured as hot lead, tell them their info has been saved"""


class SalesAgent:
    def __init__(self, kb: KnowledgeBase, crm: CRMClient) -> None:
        self.kb = kb
        self.crm = crm
        self.retriever = RAGRetriever(kb)
        self.conversation_history: list[dict[str, str]] = []
        self.current_lead: CRMTicket | None = None
        self.collected_info: dict[str, str] = {}
        self.lead_captured_this_session: bool = False

    def detect_language(self, text: str) -> str:
        arabic_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text))
        return "ar" if arabic_chars > len(text) * 0.3 else "en"

    def detect_dialect(self, text: str) -> str:
        egyptian = re.findall(r"\b(إيه|مين|كدة|ده|دي|دول|كده|عليها|بقي|خلاص|أهو|كام|دلوقت)\b", text)
        saudi = re.findall(r"\b(وش|وشو|كيفك|ليش|ابغى|تبغى|عندي|هذا|هاذي|الحين|قاعد|دايم)\b", text)
        syrian = re.findall(r"\b(شو|مشان|هلق|كرمال|عنجد|منيح|إزا|لأنو|كيفك)\b", text)
        if len(egyptian) >= len(saudi) and len(egyptian) >= len(syrian) and len(egyptian) > 0:
            return "egyptian"
        elif len(saudi) >= len(syrian) and len(saudi) > 0:
            return "saudi"
        elif len(syrian) > 0:
            return "syrian"
        return "standard"

    def detect_intent(self, text: str) -> str:
        text_lower = text.lower()
        scores: dict[str, int] = {intent: 0 for intent in INTENT_PATTERNS}
        for intent, patterns in INTENT_PATTERNS.items():
            for p in patterns:
                if re.search(p, text_lower):
                    scores[intent] += 2
        for pattern in BUYING_SIGNAL_PATTERNS:
            if re.search(pattern, text_lower):
                scores["ready_to_enroll"] += 1
        for pattern_obj, _ in OBJECTION_PATTERNS:
            if re.search(pattern_obj, text_lower):
                scores["hesitant"] += 1
        max_score = max(scores.values()) if scores else 0
        if max_score > 0:
            return max(scores, key=scores.get)
        return "browsing"

    def detect_buying_signals(self, text: str) -> list[str]:
        signals: list[str] = []
        text_lower = text.lower()
        for pattern, signal_text in [
            (    r"(how (do|can) i (enroll|register|sign up|join)|I want to (enroll|register|sign up|join|buy|purchase)|سجلني|سجّلني|كيف أسجل|كيفية التسجيل|(?:^|\s)(سجل|اسجل|اشترك)(?=\s|$|[\W_]))", "طلب تسجيل"),
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
                signals.append(signal_text)
        return signals

    def detect_objections(self, text: str) -> list[str]:
        objections: list[str] = []
        text_lower = text.lower()
        for pattern, obj_type in OBJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                objections.append(obj_type)
        return objections

    def get_temperature(self, text: str) -> str:
        signals = self.detect_buying_signals(text)
        objections = self.detect_objections(text)
        intent = self.detect_intent(text)
        prices_mentioned = bool(re.search(r"(price|cost|سعر|تكلفة|كم|بكم|budget|ميزانية)", text.lower()))
        hot_signals = {"طلب تسجيل", "جاهز للتسجيل", "طلب تواصل"}
        has_hot_signal = any(s in hot_signals for s in signals)
        if intent == "ready_to_enroll" and has_hot_signal:
            return "hot"
        if intent == "ready_to_enroll":
            return "hot"
        if len(signals) >= 2:
            return "hot"
        if signals:
            return "warm"
        if intent == "comparing":
            return "warm"
        if intent == "price_sensitive" and not objections:
            return "warm"
        if prices_mentioned and intent not in ("browsing",):
            return "warm"
        if objections and not intent == "browsing":
            return "warm"
        return "cold"

    def extract_lead_info(self, text: str) -> dict[str, str]:
        info: dict[str, str] = {}
        name_patterns = [
            r"(?:اسمي|الاسم|my name is|My name is)\s*[:\s]+([\u0600-\u06FF\w]+(?:\s+[\u0600-\u06FF\w]+){1,2})",
            r"(?:my name is|My name is)\s*[:\s]+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,2})",
            r"^([\u0600-\u06FF\w]+(?:\s+[\u06FF\w]+){0,2})\s+\d",
        ]
        _non_name_words = {
            "معنديش", "ماعنديش", "ما عندي", "ليس لدي", "لا", "باحب", "بحب", "أحب",
            "عايز", "عاوز", "بدي", "أريد", "اريد", "أنا", "انا", "اسمي", "في",
            "من", "الى", "إلى", "على", "عن", "كان", "هذا", "هذه", "ذلك", "تلك",
            "نعم", "أهلا", "اهلا", "مرحبا", "hello", "hi", "yes", "no",
            "شكرا", "شكراً", "عفوا", "عفواً", "ممكن", "هل", "كم", "ما", "لماذا",
            "أستفسر", "استفسر", "سؤال", "عندي", "ودي", "أبغى", "ابغى", "تبغى",
        }
        for p in name_patterns:
            m = re.search(p, text)
            if m:
                raw = m.group(1).strip()
                cleaned = re.sub(r"[،,].*$", "", raw).strip()
                cleaned = re.sub(r"\s+\d+\s*.*$", "", cleaned).strip()
                cleaned = re.sub(r"\s+(و|من|في|على|مع|وب|from|in)\s+\w+.*$", "", cleaned).strip()
                if cleaned and len(cleaned) > 1 and len(cleaned) < 30 and cleaned not in _non_name_words:
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
                if 7 <= len(digits) <= 15:
                    info["phone"] = phone
                    break

        if "phone" not in info:
            phone_match = re.search(r"(?<!\w)(\+?\d[\d\s\-\(\)]{7,14})(?!\w)", text)
            if phone_match:
                digits = re.sub(r"\D", "", phone_match.group(1))
                if 7 <= len(digits) <= 15:
                    info["phone"] = phone_match.group(1).strip()

        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            info["email"] = email_match.group(0)

        known_locations = ["مصر", "السعودية", "الأردن", "سوريا", "الإمارات", "ليبيا",
                           "تونس", "الجزائر", "المغرب", "فلسطين", "العراق", "السودان",
                           "اليمن", "عمان", "البحرين", "الكويت", "قطر", "لبنان"]
        for loc in known_locations:
            if loc in text:
                info["city"] = loc
                break

        self.collected_info.update(info)
        return info

    def generate_response(self, user_input: str) -> str:
        lang = self.detect_language(user_input)
        dialect = self.detect_dialect(user_input)
        intent = self.detect_intent(user_input)
        buying_signals = self.detect_buying_signals(user_input)
        objections = self.detect_objections(user_input)
        temperature = self.get_temperature(user_input)
        lead_info = self.extract_lead_info(user_input)

        self.conversation_history.append({"role": "user", "content": user_input})

        context = self.retriever.retrieve_context(user_input)

        if self.current_lead is None:
            if temperature in ("hot", "warm") or lead_info.get("name") or lead_info.get("phone") or buying_signals:
                self.current_lead = CRMTicket()
                self.current_lead.lead.language = "Arabic" if lang == "ar" else "English"
                self.current_lead.lead.dialect = dialect

        if self.current_lead:
            for signal in buying_signals:
                if signal not in self.current_lead.assessment.buying_signals:
                    self.current_lead.assessment.buying_signals.append(signal)
            for obj in objections:
                if obj not in self.current_lead.assessment.objections:
                    self.current_lead.assessment.objections.append(obj)
            self.current_lead.assessment.temperature = max(
                [self.current_lead.assessment.temperature, temperature],
                key=lambda t: {"cold": 0, "warm": 1, "hot": 2}[t]
            )
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
            user_input, lang, dialect, intent, temperature,
            buying_signals, objections, context
        )

        self.conversation_history.append({"role": "assistant", "content": response})

        should_capture = False
        if self.current_lead and not self.lead_captured_this_session:
            nm = self.current_lead.lead.name
            ph = self.current_lead.lead.phone
            temp = self.current_lead.assessment.temperature
            if nm:
                nm_lower = nm.lower().strip()
                _bad_names = {"معنديش", "ماعنديش", "ما عندي", "ليس لدي", "لا", "باحب", "بحب", "أحب",
                              "عايز", "عاوز", "بدي", "أريد", "اريد", "أنا", "انا", "اسمي",
                              "نعم", "أهلا", "اهلا", "مرحبا", "hello", "hi"}
                if nm_lower in _bad_names or any(b in nm_lower for b in ["عنديش", "ماعند", "عايز", "بدي"]):
                    nm = None
                    self.current_lead.lead.name = None
            has_name_phone = bool(nm and ph and len(nm) > 1 and len(re.sub(r"\D", "", ph or "")) >= 7)
            has_contact = bool(lead_info.get("phone") or lead_info.get("name"))
            if has_name_phone:
                should_capture = True
            elif temp == "hot" and (nm or ph or has_contact):
                should_capture = True

        if should_capture:
            summary = self._generate_summary(lang)
            self.current_lead.conversation_summary = summary
            if lang == "ar":
                self.current_lead.recommended_action = "التواصل مع العميل عبر واتساب خلال 24 ساعة لتأكيد التسجيل"
            else:
                self.current_lead.recommended_action = "Contact the client via WhatsApp within 24 hours to confirm enrollment"
            self.crm.save_ticket(self.current_lead)
            self.lead_captured_this_session = True
            self.current_lead = None
            if lang == "ar":
                response += "\n\n📋 **تم تسجيل بياناتك!** أحد مندوبي المبيعات سيتواصل معك قريباً."
            else:
                response += "\n\n📋 **Your information has been saved!** A sales rep will contact you soon."

        return response

    def _track_products(self, text: str) -> None:
        if not self.current_lead:
            return
        texts = [text.lower()]
        for m in self.conversation_history:
            if m["role"] == "user":
                texts.append(m["content"].lower())
        for t in texts:
            self._scan_text_for_products(t)

    def _scan_text_for_products(self, t: str) -> None:
        t_norm = t.replace("-", " ").replace("_", " ")

        rkeywords = ["full stack", "web dev", "data science", "data analytics",
                     "cyber", "soc", "pentest", "pen test", "ai", "devops", "python",
                     "security", "hack", "network", "linux", "programming",
                     "mobile", "flutter", "swift", "kotlin", "react", "node",
                     "django", "javascript", "typescript", "docker", "aws"]

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
                if rwords & twords:
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
        context: str
    ) -> str:
        is_first = len(self.conversation_history) <= 1
        is_generic = len(user_input.strip()) < 10 or (intent == "browsing" and not re.search(r"(cybersecurity|security|soc|data\s*science|ai|artificial intelligence|web|programming|python|machine learning|deep learning|cloud|devops|mobile|hacking|pentest|network|linux|course|courses|دورات|كورسات|مسارات|diploma|دبلوم|دبلومة|available|متاحة|offer|تقدم|عندك|شو عند)", user_input.lower()))
        if is_first and is_generic and not buying_signals and not objections:
            return self._fallback_greeting("en" if lang == "en" else dialect)

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

        try:
            llm = _get_llm()
            resp = llm.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            return resp.choices[0].message.content.strip()
        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            return self._fallback_response(lang, dialect, intent, temperature, objections)
        except Exception as e:
            logger.error(f"❌ LLM API error: {type(e).__name__}: {str(e)}")
            return self._fallback_response(lang, dialect, intent, temperature, objections)

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
