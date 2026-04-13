from pydantic import BaseModel
from typing import Optional, List


class HealthResponse(BaseModel):
    status: str


class InvoicePayload(BaseModel):
    user_email: str
    vendor_name: Optional[str]
    amount: Optional[float]
    invoice_number: Optional[str]
