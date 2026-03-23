import os
import sys
import logging
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, create_engine, select, desc
import uvicorn
from dotenv import load_dotenv

# Ensure the root directory is in the Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.db.models import Account, OutreachSequence
from backend.app.services.automation import AutomationService
from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.abm_agent import ABMAgent
from backend.app.services.google_sheets import GoogleSheetsService
from pydantic import BaseModel

load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI(title="AI Agency ABM Live Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helpers ---

def stringify_step(step_data):
    """Ensure any step (which might be a dict from LLM) is a string."""
    if isinstance(step_data, dict):
        if "subject" in step_data and "body" in step_data:
            return f"Subject: {step_data['subject']}\n\n{step_data['body']}"
        return str(step_data)
    return str(step_data) if step_data is not None else None

# --- API Endpoints ---

@app.get("/api/leads")
async def get_leads(session: Session = Depends(get_session)):
    """Fetch all leads and their sequences."""
    statement = select(OutreachSequence, Account).join(Account).order_by(desc(OutreachSequence.id))
    results = session.exec(statement).all()
    
    leads = []
    for os_obj, acc_obj in results:
        leads.append({
            "id": str(os_obj.id),
            "account_id": str(acc_obj.id),
            "name": acc_obj.company_name, # Using company_name as name for simplicity in current UI
            "company": acc_obj.industry or "Target Company",
            "profile_url": acc_obj.website or "https://www.linkedin.com",
            "message": os_obj.message,
            "step_1": os_obj.step_1_linkedin,
            "step_2": os_obj.step_2_email,
            "step_3": os_obj.step_3_followup,
            "agent_id": "abm_agent_01",
            "status": os_obj.approval_status,
            "lead_score": acc_obj.lead_score,
            "human_notes": acc_obj.human_notes
        })
    return {"leads": leads}

@app.get("/api/leads/scores")
async def get_lead_scores(session: Session = Depends(get_session)):
    """Fetch leads sorted by lead_score descending."""
    statement = select(Account).order_by(desc(Account.lead_score))
    accounts = session.exec(statement).all()
    return {"accounts": accounts}

@app.post("/api/approve-campaign/{id}")
async def approve_campaign(id: int, session: Session = Depends(get_session)):
    """Approves a campaign and triggers outreach."""
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    acc_obj = session.get(Account, os_obj.account_id)
    
    # 1. Prepare tracking link
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    tracking_link = f"{backend_url}/api/track-click/{acc_obj.id}"
    
    # 2. Replace placeholder in message
    msg_to_send = os_obj.step_1_linkedin or os_obj.message
    final_message = msg_to_send.replace("[[TRACKING_LINK]]", tracking_link)
    
    # Wait, we should replace it in ALL steps for consistency in DB if we want, 
    # but for firing we just need the one being sent.
    
    # 3. Trigger Automation
    automation_service = AutomationService()
    profile_url = acc_obj.website or "https://www.linkedin.com/in/test" # Fallback
    
    result = automation_service.trigger_linkedin_outreach(
        profile_url=profile_url,
        message=final_message,
        email=acc_obj.email
    )
    
    # 4. Sync to Google Sheets Firing List
    try:
        sheets_service = GoogleSheetsService()
        sheets_service.append_lead(profile_url, final_message)
    except Exception as e:
        logging.error(f"Failed to sync to Google Sheets: {e}")
        # We don't fail the whole request just because Sheets sync failed, 
        # but the Phantom trigger was already attempted.

    if result["status"] == "success":
        os_obj.approval_status = "SENT"
        acc_obj.status = "Active"
        session.add(os_obj)
        session.add(acc_obj)
        session.commit()
        return {"status": "success", "result": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "Outreach failed"))

@app.get("/api/track-click/{lead_id}")
async def track_click(lead_id: int, session: Session = Depends(get_session)):
    """Tracks a link click, updates score/status, and redirects."""
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update score and status
    acc_obj.lead_score += 20
    acc_obj.status = "ENGAGED"
    session.add(acc_obj)
    session.commit()
    
    # Redirect to agency landing page
    landing_page = os.getenv("AGENCY_LANDING_PAGE", "https://your-agency.com")
    return RedirectResponse(url=landing_page)

class UpdateSequenceRequest(BaseModel):
    step_1: Optional[str] = None
    step_2: Optional[str] = None
    step_3: Optional[str] = None

@app.patch("/api/sequences/{id}")
async def update_sequence(id: int, request: UpdateSequenceRequest, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if request.step_1 is not None:
        os_obj.step_1_linkedin = request.step_1
        os_obj.message = request.step_1 # Sync legacy message
    if request.step_2 is not None:
        os_obj.step_2_email = request.step_2
    if request.step_3 is not None:
        os_obj.step_3_followup = request.step_3
        
    session.add(os_obj)
    session.commit()
    return {"status": "success"}

class UpdateNotesRequest(BaseModel):
    notes: str

@app.patch("/api/leads/{id}/notes")
async def update_notes(id: int, request: UpdateNotesRequest, session: Session = Depends(get_session)):
    acc_obj = session.get(Account, id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    acc_obj.human_notes = request.notes
    session.add(acc_obj)
    session.commit()
    return {"status": "success"}

class UpdateUrlRequest(BaseModel):
    url: str

@app.patch("/api/leads/{id}/url")
async def update_url(id: int, request: UpdateUrlRequest, session: Session = Depends(get_session)):
    acc_obj = session.get(Account, id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    acc_obj.website = request.url
    session.add(acc_obj)
    session.commit()
    return {"status": "success"}

class ResearchRequest(BaseModel):
    icp_description: str
    limit: int = 5
    platform: str = "linkedin"

class TargetSpecificRequest(BaseModel):
    url: str
    icp_context: str = "B2B AI Automation"

@app.post("/api/target-specific")
async def target_specific(request: TargetSpecificRequest, session: Session = Depends(get_session)):
    research_agent = ResearchAgent()
    abm_agent = ABMAgent()
    
    lead = research_agent.research_single_url(request.url, request.icp_context)
    
    try:
        account_data = f"{lead['account']} - {lead['decision_maker']}"
        value_prop = "Our AI Agency specializes in B2B growth and automations."
        
        sequence = abm_agent.generate_outreach_sequence(
            account_data, request.icp_context, value_prop
        )
        
        new_acc = Account(
            company_name=lead['account'],
            website=lead['website'],
            industry=request.icp_context[:50],
            status="pending"
        )
        session.add(new_acc)
        session.flush()
        
        new_os = OutreachSequence(
            account_id=new_acc.id,
            channel="manual",
            step_1_linkedin=stringify_step(sequence.get("step_1_linkedin")),
            step_2_email=stringify_step(sequence.get("step_2_email")),
            step_3_followup=stringify_step(sequence.get("step_3_followup")),
            message=stringify_step(sequence.get("step_1_linkedin")),
            cta="Click Link",
            approval_status="draft"
        )
        session.add(new_os)
        session.commit()
        
        return {
            "status": "success",
            "lead": {
                "id": str(new_os.id),
                "account_id": str(new_acc.id),
                "name": lead['decision_maker'],
                "company": lead['account'],
                "profile_url": lead['website'],
                "step_1": sequence.get("step_1_linkedin"),
                "step_2": sequence.get("step_2_email"),
                "step_3": sequence.get("step_3_followup"),
                "agent_id": "abm_agent_01",
                "status": "draft",
                "lead_score": 0
            }
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/research")
async def run_research(request: ResearchRequest, session: Session = Depends(get_session)):
    research_agent = ResearchAgent()
    abm_agent = ABMAgent()
    
    leads = research_agent.execute_full_research(
        request.icp_description, 
        limit=request.limit, 
        platform=request.platform
    )
    
    results = []
    for lead in leads:
        try:
            account_data = f"{lead['account']} - {lead['decision_maker']}"
            value_prop = "Our AI Agency specializes in B2B growth and automations."
            
            sequence = abm_agent.generate_outreach_sequence(
                account_data, request.icp_description, value_prop
            )
            
            # Save using SQLModel
            new_acc = Account(
                company_name=lead['account'],
                website=lead['dm_linkedin'] or lead['website'],
                industry=request.icp_description[:50],
                status="pending"
            )
            session.add(new_acc)
            session.flush() # Get ID
            
            new_os = OutreachSequence(
                account_id=new_acc.id,
                channel=request.platform,
                step_1_linkedin=stringify_step(sequence.get("step_1_linkedin")),
                step_2_email=stringify_step(sequence.get("step_2_email")),
                step_3_followup=stringify_step(sequence.get("step_3_followup")),
                message=stringify_step(sequence.get("step_1_linkedin")), # Fallback for legacy
                cta="Click Link",
                approval_status="draft"
            )
            session.add(new_os)
            session.commit()
            
            results.append({
                "id": str(new_os.id),
                "name": lead['decision_maker'],
                "company": lead['account'],
                "profile_url": lead['dm_linkedin'],
                "step_1": sequence.get("step_1_linkedin"),
                "step_2": sequence.get("step_2_email"),
                "step_3": sequence.get("step_3_followup"),
                "agent_id": "abm_agent_01",
                "status": "draft",
                "lead_score": 0
            })
        except Exception as e:
            print(f"Error processing {lead['account']}: {e}")
            session.rollback()
            
    return {"leads": results}

@app.post("/api/webhooks/activity")
async def activity_webhook(payload: dict, session: Session = Depends(get_session)):
    """Manual activity simulation (Compatibility with old UI)"""
    lead_id = payload.get("lead_id")
    activity = payload.get("activity")
    
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if activity == "LINK_CLICKED":
        acc_obj.lead_score += 20
        acc_obj.status = "ENGAGED"
    elif activity == "MESSAGE_SENT":
        acc_obj.status = "Active"
        
    session.add(acc_obj)
    session.commit()
    return {"status": "success"}

@app.delete("/api/clear-leads")
async def clear_leads(session: Session = Depends(get_session)):
    session.query(OutreachSequence).delete()
    session.query(Account).delete()
    session.commit()
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
