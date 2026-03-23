from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    icp_score: Optional[int] = None
    lead_score: int = Field(default=0)
    status: str = Field(default="pending")
    human_notes: Optional[str] = None
    
    outreach_sequences: list["OutreachSequence"] = Relationship(back_populates="account")

class OutreachSequence(SQLModel, table=True):
    __tablename__ = "outreach_sequences"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    channel: str
    message: Optional[str] = None # Legacy/Primary message
    step_1_linkedin: Optional[str] = None
    step_2_email: Optional[str] = None
    step_3_followup: Optional[str] = None
    cta: str
    approval_status: str = Field(default="draft")
    
    account: Optional[Account] = Relationship(back_populates="outreach_sequences")
