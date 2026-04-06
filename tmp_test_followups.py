import os
import json
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.agents.abm_agent import ABMAgent

# Mock environment
os.environ["BACKEND_URL"] = "http://127.0.0.1:8000"

def test_followup_generation():
    agent = ABMAgent()
    account_data = "John Doe - CTO at AI Corp"
    icp = "CTOs at AI startups"
    value_prop = "Automating backend infrastructure"
    connection_note = "Loved your piece on serverless!"
    
    # Test generation
    followups = agent.generate_followups(account_data, icp, value_prop, connection_note)
    print("Generated Followups:")
    print(json.dumps(followups, indent=2))
    
    # Test injection logic (simulating main.py)
    lead_id = 123
    tracking_link = f"http://127.0.0.1:8000/t/{lead_id}"
    
    success = True
    for key in ["step_2_linkedin_dm", "step_3_email"]:
        if key in followups:
            text = str(followups[key])
            injected = text.replace("{{tracking_link}}", tracking_link)
            injected = injected.replace("[[TRACKING_LINK]]", tracking_link)
            injected = injected.replace("{tracking_link}", tracking_link)
            
            print(f"\nInjected {key}:")
            print(injected)
            
            if tracking_link in injected:
                print(f"SUCCESS: Link found in {key}")
            else:
                print(f"WARNING: Link NOT found in {key}")
                success = False
    
    return success

if __name__ == "__main__":
    test_followup_generation()
