from pydantic import BaseModel

class SupportTicketAdminResolve(BaseModel):
    reply_message: str
    close_ticket: bool
