"""
Agent: calendar_agent
---------------------
The Scheduler Agent. Interfaces with Google Calendar or Outlook APIs.
For this local execution, it mocks the API using a local JSON database to prevent 
needing full OAuth scopes out of the box, but enforces the exact same logic.
"""

import os
import json
from datetime import datetime, timedelta

DESCRIPTION = (
    "The Scheduler Agent. Use this to check availability, book meetings, or reschedule events. "
    "Dates must be provided in YYYY-MM-DD format, and times in HH:MM format."
)

PARAMETERS = {
    "action": {
        "type": "string",
        "required": True,
        "description": "Must be one of: 'check_availability', 'create_event', 'reschedule_event'.",
    },
    "date": {
        "type": "string",
        "required": False,
        "description": "The date (YYYY-MM-DD) to check availability for.",
    },
    "title": {
        "type": "string",
        "required": False,
        "description": "The title of the meeting (for create_event).",
    },
    "start_time": {
        "type": "string",
        "required": False,
        "description": "Start time (HH:MM).",
    },
    "end_time": {
        "type": "string",
        "required": False,
        "description": "End time (HH:MM).",
    },
    "event_id": {
        "type": "string",
        "required": False,
        "description": "The ID of the event to reschedule.",
    }
}

DB_PATH = os.path.join(os.getcwd(), "archive", "calendar_db.json")

def _load_db():
    if not os.path.exists(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with open(DB_PATH, 'w') as f:
            json.dump({"events": []}, f)
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def _save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def calendar_agent(
    action: str, 
    date: str = "", 
    title: str = "", 
    start_time: str = "", 
    end_time: str = "",
    event_id: str = ""
) -> dict:
    """Interacts with the Calendar."""
    action = action.lower().strip()
    db = _load_db()
    
    if action == "check_availability":
        if not date:
            return {"error": "check_availability requires a 'date' (YYYY-MM-DD)."}
            
        booked_slots = [
            f"{e['start_time']} - {e['end_time']} ({e['title']})"
            for e in db["events"] if e["date"] == date
        ]
        
        if not booked_slots:
            return {"success": True, "message": f"Your calendar is completely open on {date}."}
        
        return {
            "success": True, 
            "message": f"Booked slots on {date}:",
            "booked_slots": booked_slots
        }
        
    elif action == "create_event":
        if not all([date, title, start_time, end_time]):
            return {"error": "create_event requires 'date', 'title', 'start_time', and 'end_time'."}
            
        # SAFETY RAIL: Prevent double booking
        for e in db["events"]:
            if e["date"] == date:
                # Basic overlap logic
                if (start_time >= e["start_time"] and start_time < e["end_time"]) or \
                   (end_time > e["start_time"] and end_time <= e["end_time"]):
                    return {"error": f"Conflict detected! You already have '{e['title']}' scheduled from {e['start_time']} to {e['end_time']}."}
                    
        new_id = f"evt_{int(datetime.now().timestamp())}"
        new_event = {
            "id": new_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "title": title
        }
        
        db["events"].append(new_event)
        _save_db(db)
        
        return {"success": True, "message": f"Successfully booked '{title}' on {date} from {start_time} to {end_time}.", "event_id": new_id}
        
    elif action == "reschedule_event":
        if not event_id or not date or not start_time or not end_time:
            return {"error": "reschedule_event requires 'event_id', 'date', 'start_time', and 'end_time'."}
            
        found = False
        for i, e in enumerate(db["events"]):
            if e["id"] == event_id:
                db["events"][i]["date"] = date
                db["events"][i]["start_time"] = start_time
                db["events"][i]["end_time"] = end_time
                found = True
                break
                
        if not found:
            return {"error": f"Event with ID {event_id} not found."}
            
        _save_db(db)
        return {"success": True, "message": f"Event {event_id} successfully rescheduled to {date} at {start_time}."}
        
    else:
        return {"error": "Invalid action. Use 'check_availability', 'create_event', or 'reschedule_event'."}
