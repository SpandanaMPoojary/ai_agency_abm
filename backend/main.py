import os
import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import SQLModel, create_engine, select, Relationship, Field, Session
from dotenv import load_dotenv
import uvicorn

# Internal imports
from backend.app.services.enrichment import EnrichmentService
from backend.app.services.automation import AutomationService
from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.abm_agent import ABMAgent
from backend.app.services.google_sheets import GoogleSheetsService
from backend.app.db.models import Account, OutreachSequence, LeadScore

load_dotenv(override=True)

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mypass123@localhost:5432/ai_agency_db")
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

# Models are imported from backend.app.db.models

# FastAPI App
app = FastAPI(title="ABM Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper for stringifying steps
def stringify_step(step):
    if isinstance(step, dict):
        return json.dumps(step)
    return str(step) if step else ""

# API Endpoints
@app.get("/api/leads")
async def get_leads(session: Session = Depends(get_session)):
    stmt = select(Account, OutreachSequence).join(OutreachSequence)
    results = session.exec(stmt).all()
    
    leads = []
    for acc, os in results:
        leads.append({
            "id": str(os.id),
            "account_id": str(acc.id),
            "name": acc.company_name,
            "first_name": acc.first_name,
            "company": acc.company_name,
            "profile_url": acc.website,
            "step_1": os.step_1_linkedin,
            "step_2": os.step_2_email,
            "step_3": os.step_3_followup,
            "status": os.approval_status,
            "lead_score": acc.lead_score,
            "human_notes": acc.human_notes
        })
    return {"leads": leads}

@app.get("/api/leads/scores")
async def get_lead_scores(session: Session = Depends(get_session)):
    """Returns accounts that are not pending, sorted by score descending."""
    stmt = select(Account).where(Account.status != 'pending').order_by(Account.lead_score.desc())
    results = session.exec(stmt).all()
    return {"accounts": results}

@app.post("/api/approve-campaign/{id}")
async def approve_campaign(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    acc_obj = session.get(Account, os_obj.account_id)
    profile_url = acc_obj.website
    first_name = acc_obj.first_name or acc_obj.company_name.split()[0]
    connection_note = os_obj.step_1_linkedin
    
    # Generate Tracking Link (Only for follow-ups now)
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    track_link = f"{backend_url}/t/{acc_obj.id}"
    
    # 3. Fire the Phantom (Simulated or actual)
    automation = AutomationService()
    # Connection note NO LONGER needs tracking link
    result = automation.trigger_linkedin_outreach(profile_url, connection_note, acc_obj.email)
    
    if result.get("status") == "success":
        os_obj.approval_status = "CONNECTION_SENT"
        session.add(os_obj)
        
        # Sync to Google Sheets (Only 3 columns now)
        try:
            sheets_service = GoogleSheetsService()
            sheets_service.append_lead(profile_url, first_name, connection_note)
        except Exception as e:
            logging.error(f"Failed to sync to Google Sheets: {e}")
        
        # 4. Initialize Lead Score Table Entry (0 points)
        new_score = LeadScore(
            account_id=acc_obj.id,
            score=0,
            reason="Initial approval and connection firing",
            timestamp=datetime.utcnow()
        )
        session.add(new_score)
        
        # 5. Update Statuses
        os_obj.approval_status = "CONNECTION_SENT"
        acc_obj.status = "Active"
        session.add(os_obj)
        session.add(acc_obj)
        session.commit()

        return {"status": "success", "result": result}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "Outreach failed"))

@app.get("/t/{lead_id}")
async def track_click(lead_id: int, session: Session = Depends(get_session)):
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        return {"error": "Lead not found"}
    
    acc_obj.lead_score += 20
    acc_obj.status = "CLICKED"
    
    # Track scoring event
    new_score = LeadScore(
        account_id=lead_id,
        score=20,
        reason="Tracking link clicked",
        timestamp=datetime.utcnow()
    )
    session.add(acc_obj)
    session.add(new_score)
    session.commit()
    
    landing_page = os.getenv("AGENCY_LANDING_PAGE", "https://youragency.com")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=landing_page)

@app.post("/api/generate-followups/{lead_id}")
async def generate_followups(lead_id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, lead_id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    acc_obj = session.get(Account, os_obj.account_id)
    abm_agent = ABMAgent()
    
    account_data = f"{acc_obj.company_name} - {acc_obj.human_notes or 'B2B Lead'}"
    icp = acc_obj.industry or "B2B AI Automation"
    value_prop = "Our AI Agency specializes in B2B growth and automations."
    
    followups = abm_agent.generate_followups(account_data, icp, value_prop)
    
    # Inject tracking links
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    tracking_link = f"{backend_url}/t/{lead_id}"
    
    if "step_2_linkedin_dm" in followups:
        os_obj.step_2_email = stringify_step(followups["step_2_linkedin_dm"]).replace("[[TRACKING_LINK]]", tracking_link) # mapping step_2
    if "step_3_email" in followups:
        os_obj.step_3_followup = stringify_step(followups["step_3_email"]).replace("[[TRACKING_LINK]]", tracking_link) # mapping step_3
        
    session.add(os_obj)
    session.commit()
    return {"status": "success", "followups": followups}
@app.patch("/api/sequences/{id}")
async def update_sequence(id: int, request: dict, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    if "step_1" in request: os_obj.step_1_linkedin = request["step_1"]
    if "step_2" in request: os_obj.step_2_email = request["step_2"]
    if "step_3" in request: os_obj.step_3_followup = request["step_3"]
    
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
        
        dm_name = lead.get('decision_maker', 'Target')
        f_name = dm_name.split()[0] if dm_name and len(dm_name.split()) > 0 else "Target"
        
        new_acc = Account(
            company_name=lead.get('account', 'Target Account'),
            first_name=f_name,
            website=lead.get('dm_linkedin') or lead.get('website') or request.url,
            industry=request.icp_context[:50],
            status="pending",
            lead_score=0
        )
        session.add(new_acc)
        session.flush()
        
        new_os = OutreachSequence(
            account_id=new_acc.id,
            channel="manual",
            step_1_linkedin=stringify_step(sequence.get("step_1_connection_note")),
            message=stringify_step(sequence.get("step_1_connection_note")),
            cta="Connect",
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
                "step_1": sequence.get("step_1_connection_note"),
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
            
            new_acc = Account(
                company_name=lead['account'],
                first_name=lead['decision_maker'].split()[0],
                website=lead['dm_linkedin'] or lead['website'],
                industry=request.icp_description[:50],
                status="pending",
                lead_score=0
            )
            session.add(new_acc)
            session.flush()
            
            new_os = OutreachSequence(
                account_id=new_acc.id,
                channel="linkedin",
                step_1_linkedin=stringify_step(sequence.get("step_1_connection_note")),
                message=stringify_step(sequence.get("step_1_connection_note")),
                cta="Connect",
                approval_status="draft"
            )
            session.add(new_os)
            session.commit()
            
            results.append({
                "id": str(new_os.id),
                "account_id": str(new_acc.id),
                "name": lead['decision_maker'],
                "company": lead['account'],
                "profile_url": lead['dm_linkedin'] or lead['website'],
                "step_1": sequence.get("step_1_connection_note"),
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
    lead_id = payload.get("lead_id")
    activity = payload.get("activity")
    
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if activity == "LINK_CLICKED" or activity == "SIMULATED_ENGAGEMENT":
        acc_obj.lead_score += 20
        acc_obj.status = "CONNECTED"
        
        # Also update sequence if exists
        stmt = select(OutreachSequence).where(OutreachSequence.account_id == acc_obj.id)
        os_obj = session.exec(stmt).first()
        if os_obj:
            os_obj.approval_status = "ACCEPTED"
            session.add(os_obj)

        new_score = LeadScore(
            account_id=acc_obj.id,
            score=20,
            reason=f"Scoring Event: {activity}",
            timestamp=datetime.utcnow()
        )
        session.add(new_score)
    session.add(acc_obj)
    session.commit()
    return {"status": "success"}

@app.post("/api/reject-campaign/{id}")
async def reject_campaign(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    os_obj.approval_status = "REJECTED"
    
    # Also update the Account status
    acc_obj = session.get(Account, os_obj.account_id)
    if acc_obj:
        acc_obj.status = "REJECTED"
        session.add(acc_obj)
        
    session.add(os_obj)
    session.commit()
    return {"status": "success"}

@app.post("/api/check-acceptance/{id}")
async def check_acceptance(id: int, session: Session = Depends(get_session)):
    # The 'id' from frontend is Account ID
    stmt = select(OutreachSequence).where(OutreachSequence.account_id == id)
    os_obj = session.exec(stmt).first()
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found for this account")
    
    acc_obj = os_obj.account
    
    # Perform Automated Check
    automation = AutomationService()
    profile_url = acc_obj.website
    
    check_result = automation.check_linkedin_acceptance(profile_url)
    
    if check_result.get("status") == "success" and check_result.get("accepted"):
        os_obj.approval_status = "ACCEPTED"
        acc_obj.lead_score += 20
        acc_obj.status = "CONNECTED"
        
        # Track scoring event
        new_score = LeadScore(
            account_id=acc_obj.id,
            score=20,
            reason="LinkedIn Connection Accepted (Automated Check)",
            timestamp=datetime.utcnow()
        )
        session.add(acc_obj)
        session.add(os_obj)
        session.add(new_score)
        session.commit()
        return {"status": "success", "message": "Connection verified and score increased!"}
    elif check_result.get("status") == "error":
        raise HTTPException(status_code=500, detail=check_result.get("message"))
    else:
        # Return 200 for pending so the frontend shows the custom alert
        return {"status": "pending", "message": "Connection not yet accepted. Try again later!"}

@app.delete("/api/clear-leads")
async def clear_leads(session: Session = Depends(get_session)):
    session.query(OutreachSequence).delete()
    session.query(Account).delete()
    session.commit()
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
