import os
from datetime import datetime
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)

TWILIO_SID   = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM  = os.environ["TWILIO_FROM"]
SALES_NUMBERS = [
    os.environ["SALES_NUMBER_1"],
]

class WhatsAppReporter:
    def __init__(self, crm):
        self.crm = crm
        try:
            self.client = Client(TWILIO_SID, TWILIO_TOKEN)
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
        self.scheduler = BackgroundScheduler()

    def _build_report(self) -> str:
        tickets = self.crm.get_all_tickets()
        today = datetime.now().date()

        hot, warm, cold = [], [], []
        new_today = 0

        for t in tickets:
            temp = t.get("assessment", {}).get("temperature", "cold")
            created = t.get("timestamp", "") # Assuming timestamp is stored as "YYYY-MM-DD HH:MM"

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
        for number in SALES_NUMBERS:
            try:
                self.client.messages.create(
                    from_=TWILIO_FROM,
                    to=number,
                    body=message
                )
            except Exception as e:
                logger.error(f"Failed to send WhatsApp report to {number}: {e}")
        print(f"✅ WhatsApp report sent at {datetime.now()}")

    def send_lead_alert(self, ticket_data: dict):
        """Send an instant alert to sales when a new qualified lead is captured."""
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
            return # Don't alert for cold leads

        message = f"""🚨 *عميل جديد ({urgency})* {emoji}
━━━━━━━━━━━━━━━
👤 الاسم: {name}
📞 رقم: {phone}
🎯 الاهتمام: {interest}
🔥 الحرارة: {temp.upper()}
━━━━━━━━━━━━━━━
_يرجى التواصل معه في أقرب وقت_"""

        for number in SALES_NUMBERS:
            try:
                self.client.messages.create(
                    from_=TWILIO_FROM,
                    to=number,
                    body=message
                )
            except Exception as e:
                logger.error(f"Failed to send WhatsApp alert to {number}: {e}")

    def start(self):
        self.scheduler.add_job(
            self.send_report,
            trigger="cron",
            hour=8,
            minute=0
        )
        self.scheduler.start()
        print("📱 WhatsApp scheduler started")
