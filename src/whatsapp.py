import os
from datetime import datetime
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

class WhatsAppReporter:
    def __init__(self, crm):
        self.crm = crm

        sid   = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.from_  = os.environ.get("TWILIO_FROM")
        self.numbers = [n for n in [
            os.environ.get("SALES_NUMBER_1"),
            os.environ.get("SALES_NUMBER_2"),
        ] if n]

        if not all([sid, token, self.from_, self.numbers]):
            missing = [k for k, v in [
                ("TWILIO_ACCOUNT_SID", sid),
                ("TWILIO_AUTH_TOKEN", token),
                ("TWILIO_FROM", self.from_),
                ("SALES_NUMBER_1", os.environ.get("SALES_NUMBER_1")),
            ] if not v]
            logger.warning(f"Twilio credentials missing — WhatsApp disabled. Missing: {missing}")
            self.client = None
            self._init_error = f"Missing env vars: {missing}"
            return

        try:
            self.client = Client(sid, token)
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
            self._init_error = str(e)

    def _build_report(self) -> str:
        tickets = self.crm.get_all_tickets()
        today = datetime.now().date()

        hot, warm, cold = [], [], []
        new_today = 0

        for t in tickets:
            temp = t.get("assessment", {}).get("temperature", "cold")
            created = t.get("timestamp", "")

            if created and created[:10] == str(today):
                new_today += 1

            if temp == "hot":
                hot.append(t)
            elif temp == "warm":
                warm.append(t)
            else:
                cold.append(t)

        from collections import Counter
        all_courses = []
        for t in tickets:
            prods = t.get("products", {})
            all_courses += prods.get("courses", [])
            all_courses += prods.get("diplomas", [])
            all_courses += prods.get("tracks", [])
        top = Counter(all_courses).most_common(1)
        top_course = top[0][0] if top else "غير محدد"

        day_ar = ["الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","السبت","الأحد"]
        day_name = day_ar[datetime.now().weekday()]

        report = f"""📊 *تقرير كيف | {day_name} {today}*
━━━━━━━━━━━━━━━
🔴 Hot Leads: {len(hot)} (يحتاجون تواصل فوري)
🟡 Warm Leads: {len(warm)} (follow-up اليوم)
🔵 Cold Leads: {len(cold)}
━━━━━━━━━━━━━━━
🆕 محادثات اليوم: {new_today}
🏆 الأكثر طلباً: {top_course}
━━━━━━━━━━━━━━━"""

        if hot:
            report += "\n\n🔴 *Hot Leads تحتاج تواصل:*"
            for t in hot[:3]:
                lead = t.get("lead", {})
                name  = lead.get("name", "غير معروف")
                phone = lead.get("phone", "—")
                prods = t.get("products", {})
                interest = (prods.get("diplomas") or prods.get("tracks") or prods.get("courses") or ["غير محدد"])[0]
                report += f"\n👤 {name} | {phone}\n🎯 {interest}"

        report += "\n\n_Kayfa AI Sales Agent_"
        return report

    def send_report(self):
        if not self.client:
            return
        message = self._build_report()
        for number in self.numbers:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=number,
                    body=message
                )
            except Exception as e:
                logger.error(f"Failed to send WhatsApp report to {number}: {e}")
        logger.info(f"WhatsApp report sent at {datetime.now()}")

    def send_lead_alert(self, ticket_data: dict):
        if not self.client:
            return

        lead = ticket_data.get("lead", {})
        assessment = ticket_data.get("assessment", {})
        prods = ticket_data.get("products", {})

        name = lead.get("name", "غير معروف")
        phone = lead.get("phone", "—")
        temp = assessment.get("temperature", "cold")
        interest = (prods.get("diplomas") or prods.get("tracks") or prods.get("courses") or ["غير محدد"])[0]

        if temp == "hot":
            emoji = "🔴"
            urgency = "فوري"
        elif temp == "warm":
            emoji = "🟡"
            urgency = "عادي"
        else:
            return

        message = f"""🚨 *عميل جديد ({urgency})* {emoji}
━━━━━━━━━━━━━━━
👤 الاسم: {name}
📞 رقم: {phone}
🎯 الاهتمام: {interest}
🔥 الحرارة: {temp.upper()}
━━━━━━━━━━━━━━━
_يرجى التواصل معه في أقرب وقت_"""

        for number in self.numbers:
            try:
                self.client.messages.create(
                    from_=self.from_,
                    to=number,
                    body=message
                )
            except Exception as e:
                logger.error(f"Failed to send WhatsApp alert to {number}: {e}")
