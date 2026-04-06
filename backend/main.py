import re
import os
import json
import logging
import smtplib
from typing import List, Optional
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:myp@ss123@localhost:5432/ai_agency_db")
engine = create_engine(DATABASE_URL)

import requests

def get_hunter_email(dm_name: str, company_website: str) -> Optional[str]:
    hunter_key = os.getenv("HUNTER_API_KEY")
    if not hunter_key or not company_website:
        return None
        
    try:
        domain = str(company_website)
        if "://" in domain: domain = domain.split("://")[1]
        domain = domain.split("/")[0].replace("www.", "")
        
        # Don't waste hunter credits searching linkedin.com
        if "linkedin.com" in domain:
            return None
            
        parts = dm_name.split()
        f_name = parts[0] if len(parts) > 0 else ""
        l_name = parts[-1] if len(parts) > 1 else ""
        
        url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={f_name}&last_name={l_name}&api_key={hunter_key}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("email")
    except Exception as e:
        logging.error(f"Hunter API Exception: {e}")
    return None

def get_session():
    with Session(engine) as session:
        yield session

THROTTLE_FILE = "backend/data/throttle.json"

def check_and_update_throttle(limit: int = 2) -> tuple[bool, str]:
    if os.getenv("LIVE_MODE", "false").lower() != "true":
        return True, ""
        
    now = datetime.utcnow()
    os.makedirs("backend/data", exist_ok=True)
    
    launches = []
    if os.path.exists(THROTTLE_FILE):
        try:
            with open(THROTTLE_FILE, "r") as f:
                data = json.load(f)
                # Handle both legacy 'last_launch' and new 'launches' format
                if "launches" in data:
                    launches = [datetime.fromisoformat(ts) for ts in data["launches"]]
                elif "last_launch" in data:
                    launches = [datetime.fromisoformat(data["last_launch"])]
        except Exception as e:
            logging.error(f"Error reading throttle file: {e}")
            launches = []

    # Filter for launches in the last hour (3600 seconds)
    recent_launches = [ts for ts in launches if (now - ts).total_seconds() < 3600]
    
    if len(recent_launches) >= limit:
        # Find time until oldest launch in the window expires
        oldest_launch = min(recent_launches)
        diff = (now - oldest_launch).total_seconds()
        mins_left = max(1, int((3600 - diff) / 60))
        return False, f"Rate limit reached (Limit: {limit}/hour). Please wait ~{mins_left} more mins."
                
    # Record this launch
    recent_launches.append(now)
    with open(THROTTLE_FILE, "w") as f:
        json.dump({"launches": [ts.isoformat() for ts in recent_launches]}, f)
    
    return True, ""


# Models are imported from backend.app.db.models

# FastAPI App
app = FastAPI(title="ABM Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage for assets
STORAGE_PATH = "backend/storage"
if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH)
app.mount("/storage", StaticFiles(directory=STORAGE_PATH), name="storage")

def stringify_step(step):
    if isinstance(step, dict):
        # Case-insensitive check for subject and body
        subject = None
        body = None
        other_parts = []
        
        for k, v in step.items():
            k_low = k.lower().strip()
            if "subject" in k_low:
                subject = v
            elif "body" in k_low:
                body = v
            elif v and str(v).strip():
                other_parts.append(f"{k}: {v}")
        
        if subject or body:
            res = ""
            if subject: res += f"Subject: {subject}\n\n"
            if body: res += str(body)
            if other_parts:
                res += "\n\n" + "\n".join(other_parts)
            return res.strip()
            
        return json.dumps(step)
    return str(step) if step else ""

def inject_tracking_link(content: str, account_id: int, backend_url: str, force_append: bool = False) -> str:
    """Replaces placeholders or hallucinations with a tracking link, or appends one if missing."""
    if not content: return ""
    
    tracking_link = f"{backend_url}/t/{account_id}"
    # This covers {{tracking_link}}, [[TRACKING_LINK]], {tracking_link}, or hallucinated links.
    url_pattern = r"(https?://[^\s{}|<>\[\]]+|\[\[TRACKING_LINK\]\]|{{tracking_link}}|{tracking_link})"
    
    # 1. Try to replace specific common placeholders or ANY url found
    new_content = re.sub(url_pattern, tracking_link, content)
    
    # 2. Safety Fallback: If no replacement was made and force_append is True
    if force_append and new_content == content:
        new_content = f"{content}\n\nResource: {tracking_link}"
        
    return new_content

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
    
    # THROTTLE CHECK
    is_allowed, reason = check_and_update_throttle()
    if not is_allowed:
        raise HTTPException(status_code=429, detail=reason)
        
    # Generate Tracking Link (Only for follow-ups now)
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    track_link = f"{backend_url}/t/{acc_obj.id}"
    
    # 1. Sync to Google Sheets FIRST
    try:
        sheets_service = GoogleSheetsService()
        sheets_service.append_lead(profile_url, first_name, connection_note)
    except Exception as e:
        logging.error(f"Failed to sync to Google Sheets: {e}")
        
    # Wait to ensure Sheets DB has registered it before Phantom fetches
    import time
    time.sleep(1.5)
    
    # 3. Fire the Phantom
    automation = AutomationService()
    result = automation.trigger_linkedin_outreach(profile_url, connection_note, acc_obj.email)
    
    if result.get("status") == "success":
        os_obj.approval_status = "CONNECTION_SENT"
        session.add(os_obj)
        
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

@app.post("/api/mark-manually-sent/{id}")
async def mark_manually_sent(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    acc_obj = session.get(Account, os_obj.account_id)
    
    # 1. Sync to Google Sheets
    try:
        sheets_service = GoogleSheetsService()
        sheets_service.update_status(acc_obj.website, "SENT_MANUAL")
    except Exception as e:
        logging.error(f"Failed to sync manual status to Sheets: {e}")
        
    # 2. Update Statuses
    os_obj.approval_status = "SENT_MANUAL"
    acc_obj.status = "Active"
    session.add(os_obj)
    session.add(acc_obj)
    
    # 3. Log Score Entry (0 pts for starting outreach)
    new_score = LeadScore(
        account_id=acc_obj.id,
        score=0,
        reason="Initial manual outreach started",
        timestamp=datetime.utcnow()
    )
    session.add(new_score)
    session.commit()
    
    return {"status": "success"}

@app.get("/t/{lead_id}")
async def track_click(lead_id: int, session: Session = Depends(get_session)):
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        return RedirectResponse(url=os.getenv("AGENCY_LANDING_PAGE", "https://youragency.com"))
    
    reason = "Follow-up Link Clicked"
    # Deduplicate: only award +20 for the first click
    stmt_score = select(LeadScore).where(LeadScore.account_id == acc_obj.id, LeadScore.reason == reason)
    if not session.exec(stmt_score).first():
        acc_obj.lead_score += 20
        acc_obj.status = "CLICKED"
        
        # Also update the outreach sequence status for UI consistency
        stmt_os = select(OutreachSequence).where(OutreachSequence.account_id == acc_obj.id)
        os_obj = session.exec(stmt_os).first()
        if os_obj:
            os_obj.approval_status = "CLICKED"
            session.add(os_obj)
        
        # Sync to Sheets
        try:
            sheets_service = GoogleSheetsService()
            sheets_service.update_status(acc_obj.website, "CLICKED")
        except Exception as e:
            logging.error(f"Failed to sync status to Sheets: {e}")

        new_score = LeadScore(
            account_id=lead_id,
            score=20,
            reason=reason,
            timestamp=datetime.utcnow()
        )
        session.add(new_score)
    
    session.add(acc_obj)
    session.commit()
    
    landing_page = os.getenv("AGENCY_LANDING_PAGE", "https://youragency.com")
    return RedirectResponse(url=landing_page)

class UpdateStatusRequest(BaseModel):
    status: str

@app.post("/api/leads/{id}/status")
async def update_lead_status(id: int, request: UpdateStatusRequest, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
        
    acc_obj = os_obj.account
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Account not found")
        
    old_status = os_obj.approval_status
    new_status = request.status
    
    os_obj.approval_status = new_status
    acc_obj.status = new_status
    
    # Sync to Sheets
    try:
        sheets_service = GoogleSheetsService()
        sheets_service.update_status(acc_obj.website, new_status)
    except Exception as e:
        logging.error(f"Failed to sync status to Sheets: {e}")
    
    # Logic for lead scoring update when status becomes 'CONNECTED'
    if new_status == "CONNECTED" and old_status != "CONNECTED":
        reason = "Manual Status Update: Connected"
        stmt_score = select(LeadScore).where(LeadScore.account_id == acc_obj.id, LeadScore.reason == reason)
        if not session.exec(stmt_score).first():
            acc_obj.lead_score += 20
            new_score = LeadScore(
                account_id=acc_obj.id,
                score=20,
                reason=reason,
                timestamp=datetime.utcnow()
            )
            session.add(new_score)
            
    session.add(os_obj)
    session.add(acc_obj)
    session.commit()
    return {"status": "success", "new_score": acc_obj.lead_score}

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
    
    # Passing step_1_linkedin as the context for the follow-up
    followups = abm_agent.generate_followups(account_data, icp, value_prop, connection_note=os_obj.step_1_linkedin)

    
    # Inject tracking links
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    
    if "step_2_linkedin_dm" in followups:
        raw_text = stringify_step(followups["step_2_linkedin_dm"])
        os_obj.step_2_email = inject_tracking_link(raw_text, acc_obj.id, backend_url, force_append=True)
        followups["step_2_linkedin_dm"] = os_obj.step_2_email
    if "step_3_email" in followups:
        raw_text = stringify_step(followups["step_3_email"])
        os_obj.step_3_followup = inject_tracking_link(raw_text, acc_obj.id, backend_url, force_append=True)
        followups["step_3_email"] = os_obj.step_3_followup
        
    session.add(os_obj)
    session.commit()
    return {"status": "success", "followups": followups}

@app.patch("/api/sequences/{id}")
async def update_sequence(id: int, request: dict, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

    if "step_1" in request: 
        # Phase 1 is officially link-free as per latest requirements
        os_obj.step_1_linkedin = request["step_1"]
    if "step_2" in request: 
        os_obj.step_2_email = inject_tracking_link(request["step_2"], os_obj.account_id, backend_url, force_append=False)
    if "step_3" in request: 
        os_obj.step_3_followup = inject_tracking_link(request["step_3"], os_obj.account_id, backend_url, force_append=False)
    
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

@app.post("/api/fire-linkedin-dm/{id}")

async def fire_linkedin_dm(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj: raise HTTPException(status_code=404, detail="Sequence not found")
    if not os_obj.step_2_email: raise HTTPException(status_code=400, detail="LinkedIn DM message not generated yet")
        
    acc_obj = os_obj.account
    if not acc_obj: raise HTTPException(status_code=404, detail="Account not found")

    profile_url = acc_obj.website
    
    # THROTTLE CHECK
    is_allowed, reason = check_and_update_throttle()
    if not is_allowed:
        raise HTTPException(status_code=429, detail=reason)

    # 1. Append to Sheets first
    sheets_service = GoogleSheetsService()
    sheets_service.append_linkedin_dm(profile_url, os_obj.step_2_email)
    
    import time
    time.sleep(1.5)
    
    # 2. Trigger Phantombuster
    automation = AutomationService()
    result = automation.trigger_message_sender(profile_url, os_obj.step_2_email)
    
    if result.get("status") != "success":
        logging.error(f"Failed to fire LinkedIn DM Phantom: {result}")
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to trigger Phantom"))
        
    return {"status": "success", "message": "LinkedIn DM Fired Successfully!"}

@app.post("/api/fire-cold-email/{id}")
async def fire_cold_email(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj: raise HTTPException(status_code=404, detail="Sequence not found")
    if not os_obj.step_3_followup: raise HTTPException(status_code=400, detail="Cold Email message not generated yet")
        
    acc_obj = os_obj.account
    if not acc_obj: raise HTTPException(status_code=404, detail="Account not found")

    profile_url = acc_obj.website
    
    # 1. Append to Sheets specifically marked as Email
    sheets_service = GoogleSheetsService()
    sheets_service.append_cold_email(profile_url, os_obj.step_3_followup)
    
    # 2. Extract AI Subject and Body
    raw_text = os_obj.step_3_followup
    subject = f"Quick question regarding {acc_obj.company_name}"
    body = raw_text
    
    for line in raw_text.split('\n'):
        if line.lower().startswith('subject:'):
            subject = line[8:].strip()
            # Remove the 'Subject' line from the body gracefully
            body_parts = raw_text.split(line)
            body = "".join(body_parts).strip()
            break
            
    # 3. Handle actual SMTP sending
    target_email = acc_obj.email
    if not target_email:
        return {"status": "success", "message": "Email logged to Google Sheet (No recipient email found to send to)."}
        
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_pass:
        raise HTTPException(status_code=500, detail="SMTP credentials not found in backend .env")
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = target_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        logging.info(f"Cold Email sent via SMTP to {target_email}")
        return {"status": "success", "message": f"Cold Email successfully dispatched to {target_email}!"}
    except Exception as e:
        logging.error(f"SMTP Flow Failed: {e}")
        raise HTTPException(status_code=500, detail=f"SMTP Error: {str(e)}")

@app.delete("/api/leads/clear")
async def clear_all_leads(session: Session = Depends(get_session)):
    try:
        # Clear Database
        for ls in session.exec(select(LeadScore)).all(): session.delete(ls)
        for os_obj in session.exec(select(OutreachSequence)).all(): session.delete(os_obj)
        for acc in session.exec(select(Account)).all(): session.delete(acc)
        session.commit()
        
        # Clear Google Sheets
        try:
            sheets_service = GoogleSheetsService()
            sheets_service.clear_all_data()
        except Exception as e:
            logging.error(f"Failed to clear Google Sheets: {e}")
            
        return {"status": "success", "message": "Database and Google Sheets cleared"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/leads/{id}")
async def delete_lead(id: int, session: Session = Depends(get_session)):
    acc = session.get(Account, id)
    if not acc:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    try:
        for ls in session.exec(select(LeadScore).where(LeadScore.account_id == id)).all(): session.delete(ls)
        for os_obj in session.exec(select(OutreachSequence).where(OutreachSequence.account_id == id)).all(): session.delete(os_obj)
        session.delete(acc)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
        company_name = lead.get('account', 'Target Account')
        target_website = lead.get('dm_linkedin') or lead.get('website') or request.url
        
        # Guard against duplicates (by URL or Name+Company)
        stmt_dup = select(Account).where(
            (Account.website == target_website) | 
            ((Account.first_name == f_name) & (Account.company_name == company_name))
        )
        if session.exec(stmt_dup).first():
            raise HTTPException(status_code=400, detail="This lead has already been targeted and exists in the pipeline.")
        
        # Handle Hunter mapping
        company_website = lead.get('website') or request.url
        discovered_email = get_hunter_email(dm_name, company_website)
        
        new_acc = Account(
            company_name=company_name,
            first_name=f_name,
            website=target_website,
            industry=request.icp_context[:50],
            status="pending",
            lead_score=0,
            email=discovered_email
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
            
            target_website = lead['dm_linkedin'] or lead['website']
            f_name_extracted = lead['decision_maker'].split()[0]
            company_extracted = lead['account']
            
            stmt_dup = select(Account).where(
                (Account.website == target_website) | 
                ((Account.first_name == f_name_extracted) & (Account.company_name == company_extracted))
            )
            if session.exec(stmt_dup).first():
                continue  # Skip duplicate lead
            
            sequence = abm_agent.generate_outreach_sequence(
                account_data, request.icp_description, value_prop
            )
            
            # Discover Email natively
            company_website = lead.get('website')
            dm_name = lead.get('decision_maker', 'Target')
            discovered_email = get_hunter_email(dm_name, company_website)
            
            new_acc = Account(
                company_name=company_extracted,
                first_name=f_name_extracted,
                website=target_website,
                industry=request.icp_description[:50],
                status="pending",
                lead_score=0,
                email=discovered_email
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
    # payload['lead_id'] is the OutreachSequence.id from frontend
    seq_id = payload.get("lead_id")
    activity = payload.get("activity")
    
    os_obj = session.get(OutreachSequence, seq_id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    acc_obj = os_obj.account
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Account not found for this sequence")
    
    if activity == "LINK_CLICKED":
        reason = f"Scoring Event: {activity}"
        
        # Check for duplicates
        stmt_score = select(LeadScore).where(LeadScore.account_id == acc_obj.id, LeadScore.reason == reason)
        if not session.exec(stmt_score).first():
            acc_obj.lead_score += 20
            acc_obj.status = "CLICKED"
            
            # Also update sequence if exists
            os_obj.approval_status = "CLICKED"

            new_score = LeadScore(
                account_id=acc_obj.id,
                score=20,
                reason=reason,
                timestamp=datetime.utcnow()
            )
            session.add(new_score)
            
    session.add(acc_obj)
    session.add(os_obj)
    session.commit()
    return {"status": "success"}

@app.post("/api/mark-replied/{id}")
async def mark_replied(id: int, session: Session = Depends(get_session)):
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        raise HTTPException(status_code=404, detail="Sequence not found")
        
    acc_obj = os_obj.account
    reason = "Prospect Replied Back"
    
    stmt_score = select(LeadScore).where(LeadScore.account_id == acc_obj.id, LeadScore.reason == reason)
    if not session.exec(stmt_score).first():
        # Update score by +5 for reply as requested (previously was +20)
        acc_obj.lead_score += 5
        acc_obj.status = "REPLIED"
        os_obj.approval_status = "REPLIED"
        
        # Sync to Sheets
        try:
            sheets_service = GoogleSheetsService()
            sheets_service.update_status(acc_obj.website, "REPLIED")
        except Exception as e:
            logging.error(f"Failed to sync status to Sheets: {e}")
        
        new_score = LeadScore(
            account_id=acc_obj.id,
            score=5,
            reason=reason,
            timestamp=datetime.utcnow()
        )
        session.add(new_score)
        session.add(acc_obj)
        session.add(os_obj)
        session.commit()
    
    return {"status": "success"}

# Multi-Asset Tracking Engine
@app.get("/track/{asset_type}/{lead_id}")
async def multi_asset_track(
    asset_type: str, 
    lead_id: int, 
    target: Optional[str] = None, 
    name: Optional[str] = None,
    session: Session = Depends(get_session)
):
    acc_obj = session.get(Account, lead_id)
    if not acc_obj:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Increase lead_score by +10
    acc_obj.lead_score += 10
    
    event_type = "Click" if asset_type == "link" else "Open"
    reason = f"Asset {event_type}: {asset_type}"
    if name: reason += f" ({name})"
    elif target: reason += f" ({target})"

    new_score = LeadScore(
        account_id=lead_id,
        score=10,
        reason=reason,
        timestamp=datetime.utcnow()
    )
    session.add(acc_obj)
    session.add(new_score)
    session.commit()

    if asset_type == "link":
        if not target:
            target = os.getenv("AGENCY_LANDING_PAGE", "https://youragency.com")
        return RedirectResponse(url=target)
    
    elif asset_type == "file":
        if not name:
            raise HTTPException(status_code=400, detail="File name required")
        file_path = os.path.join(STORAGE_PATH, name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path)
    
    return {"status": "success", "message": "Tracked"}

@app.post("/api/upload-asset")
async def upload_asset(file: UploadFile = File(...)):
    if not os.path.exists(STORAGE_PATH):
        os.makedirs(STORAGE_PATH)
    
    file_path = os.path.join(STORAGE_PATH, file.filename)
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
    
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    # Return the file name so frontend can construct the tracking link: 
    # {backend_url}/track/file/{{lead_id}}?name={file.filename}
    return {"status": "success", "filename": file.filename, "url": f"{backend_url}/storage/{file.filename}"}

# Tracking logic moved to Line 240

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
        
        # Sync to Sheets
        try:
            sheets_service = GoogleSheetsService()
            sheets_service.update_status(acc_obj.website, "REJECTED")
        except Exception as e:
            logging.error(f"Failed to sync status to Sheets: {e}")
            
    session.add(os_obj)
    session.commit()
    return {"status": "success"}

@app.post("/api/check-acceptance/{id}")
async def check_acceptance(id: int, session: Session = Depends(get_session)):
    # The 'id' from frontend is OutreachSequence.id
    print(f"Checking acceptance for Sequence ID: {id}")
    os_obj = session.get(OutreachSequence, id)
    if not os_obj:
        # Fallback: check if it was an account ID (just in case)
        stmt = select(OutreachSequence).where(OutreachSequence.account_id == id)
        os_obj = session.exec(stmt).first()
        if not os_obj:
            raise HTTPException(status_code=404, detail=f"Sequence not found for ID {id}")
    
    acc_obj = os_obj.account
    
    # Perform Automated Check
    automation = AutomationService()
    profile_url = acc_obj.website
    
    check_result = automation.check_linkedin_acceptance(profile_url)
    
    if check_result.get("status") == "success" and check_result.get("accepted"):
        os_obj.approval_status = "ACCEPTED"
        
        reason = "LinkedIn Connection Accepted (Automated Check)"
        stmt_score = select(LeadScore).where(LeadScore.account_id == acc_obj.id, LeadScore.reason == reason)
        if not session.exec(stmt_score).first():
            acc_obj.lead_score += 50
            acc_obj.status = "CONNECTED"
            
            # Track scoring event
            new_score = LeadScore(
                account_id=acc_obj.id,
                score=50,
                reason=reason,
                timestamp=datetime.utcnow()
            )
            session.add(new_score)
            
        session.add(acc_obj)
        session.add(os_obj)
        session.commit()
        return {"status": "success", "message": "Connection verified and score updated!"}
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
