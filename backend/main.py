import os
import sys

# Ensure the root directory is in the Python path regardless of how the script is executed
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from urllib.parse import urlparse
from backend.app.services.automation import AutomationService
from backend.app.agents.research_agent import ResearchAgent
from backend.app.agents.abm_agent import ABMAgent
from pydantic import BaseModel
import uvicorn
# Try to load dotenv here locally for FastAPI entry
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="AI Agency ABM Webhooks")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    try:
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            parsed = urlparse(database_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'postgres'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
        return conn
    except Exception as e:
        print(f"Database error: {e}")
        return None

@app.post("/webhooks/hunter")
async def hunter_webhook(request: Request):
    """Webhook for Hunter.io email opens/clicks."""
    payload = await request.json()
    # Typical Hunter webhook logic here:
    email = payload.get("email")
    event = payload.get("event") # e.g. 'open' or 'click'
    
    if event in ["open", "click"] and email:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # simplistic proxy mapping: increase lead_score for accounts matching some parameter
                    cursor.execute("UPDATE accounts SET lead_score = lead_score + 10 WHERE website LIKE %s", (f"%{email.split('@')[-1]}%",))
                conn.commit()
            except Exception as e:
                print(e)
            finally:
                conn.close()
    return {"status": "received"}

@app.post("/webhooks/phantombuster")
async def pb_webhook(request: Request):
    """Webhook for Phantombuster success/replies."""
    payload = await request.json()
    # Logic to map the phantom output back to the account and increment score
    profile_url = payload.get("profileUrl")
    
    if profile_url:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    # if the account table had a linkedinUrl we'd filter on that. 
                    # Assuming we add it or map via another table:
                    cursor.execute("UPDATE accounts SET lead_score = lead_score + 25")
                conn.commit()
            finally:
                conn.close()
    return {"status": "received"}

@app.post("/api/fire_automation")
async def fire_automation(payload: dict):
    """Triggered by the Next.js 'Approve' button."""
    agent_id = payload.get("agent_id")
    profile_url = payload.get("profile_url")
    message = payload.get("message")
    
    if not all([agent_id, profile_url, message]):
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    automation_service = AutomationService()
    try:
        result = automation_service.trigger_linkedin_outreach(agent_id, profile_url, message)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ResearchRequest(BaseModel):
    icp_description: str
    limit: int = 5
    platform: str = "linkedin"

@app.post("/api/research")
async def run_research(request: ResearchRequest):
    research_agent = ResearchAgent()
    abm_agent = ABMAgent()
    
    # Run research loop
    leads = research_agent.execute_full_research(
        request.icp_description, 
        limit=request.limit, 
        platform=request.platform
    )
    
    results = []
    for i, lead in enumerate(leads):
        try:
            account_data = f"{lead['account']} - {lead['decision_maker']}"
            value_prop = "Our AI Agency specializes in B2B growth and automations."
            
            sequence = abm_agent.generate_outreach_sequence(
                account_data, request.icp_description, value_prop
            )
            
            message = sequence[0]["message"] if isinstance(sequence, list) and len(sequence) > 0 else "Failed to generate message."
            
            # Save to DB
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO accounts (company_name, website, status) VALUES (%s, %s, %s) RETURNING id",
                            (lead['account'], lead['website'], "pending")
                        )
                        account_id = cursor.fetchone()[0]
                        cursor.execute(
                            "INSERT INTO outreach_sequences (account_id, channel, message, cta, approval_status) VALUES (%s, %s, %s, %s, %s)",
                            (account_id, request.platform, message, "Review", "draft")
                        )
                    conn.commit()
                except Exception as e:
                    print(f"DB Error: {e}")
                finally:
                    conn.close()
            
            results.append({
                "id": f"lead_{i}",
                "name": lead['decision_maker'],
                "company": lead['account'],
                "profile_url": lead['dm_linkedin'],
                "message": message,
                "agent_id": "abm_agent_01"
            })
        except Exception as e:
            print(f"Error processing lead {lead['account']}: {e}")
            
    return {"leads": results}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
