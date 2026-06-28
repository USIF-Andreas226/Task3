from src.whatsapp import WhatsAppReporter
from src.crm import CRMTicket, CRMClient

# Mock a CRMTicket to simulate a new lead
mock_ticket = CRMTicket()
mock_ticket.lead.name = "Ahmed Test"
mock_ticket.lead.phone = "01001234567"
mock_ticket.assessment.temperature = "hot"
mock_ticket.products.courses = ["AI Fundamentals"]

# Initialize a dummy CRM client (we don't need it to actually connect to DB for the alert)
crm = CRMClient()
reporter = WhatsAppReporter(crm)

print("Sending lead alert...")
reporter.send_lead_alert(mock_ticket.model_dump())
print("Lead alert process completed.")
