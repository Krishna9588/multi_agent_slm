"""
Agent: data_exporter_agent
----------------------------
Takes structured JSON data (such as extracted entities) and saves it
to a CSV file in the archive/outputs folder.

Primary function: data_exporter_agent(data_json, filename_prefix)
"""

import sys
import os
import json
import csv
from datetime import datetime

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Exports structured JSON array data to a CSV file. "
    "Use this when the user asks to save, write, or export data to a CSV/Excel file. "
    "Returns the absolute path to the saved file."
)

PARAMETERS = {
    "data_json": {
        "type":        "string",
        "required":    True,
        "description": "A JSON-formatted string representing a list of objects (e.g. [{\"name\": \"John\", \"role\": \"CEO\"}]).",
    },
    "filename_prefix": {
        "type":        "string",
        "required":    False,
        "description": "A short descriptive prefix for the filename (e.g. 'founding_members'). Default is 'export'.",
    }
}

# ── Primary function ───────────────────────────────────────────────────────────

def data_exporter_agent(data_json: str, filename_prefix: str = "export") -> dict:
    """
    Parse a JSON string of objects and write them to a CSV file.
    
    Args:
        data_json: A JSON string of a list of dictionaries.
        filename_prefix: Prefix for the output CSV file.
        
    Returns:
        dict: Status message and file path.
    """
    try:
        data = json.loads(data_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format provided. Must be a valid JSON array of objects."}

    if not isinstance(data, list):
        # If it's a single dictionary, wrap it in a list
        if isinstance(data, dict):
            # Check if it's a dictionary of lists (like the NER agent output)
            # If so, flatten it into a list of dicts with a 'category' column
            flattened = []
            for category, items in data.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item['category'] = category
                            flattened.append(item)
                        elif isinstance(item, str):
                            flattened.append({'category': category, 'value': item})
            
            if flattened:
                data = flattened
            else:
                data = [data]
        else:
            return {"error": "Data must be a JSON array of objects or a categorized dictionary."}

    if not data:
        return {"error": "The provided JSON array is empty. Nothing to export."}

    # Ensure output directory exists
    out_dir = os.path.join(os.getcwd(), "archive", "outputs")
    os.makedirs(out_dir, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(c if c.isalnum() else "_" for c in filename_prefix)
    filename = f"{safe_prefix}_{timestamp}.csv"
    filepath = os.path.join(out_dir, filename)

    # Extract all possible headers (keys) from all objects
    headers = set()
    for row in data:
        if isinstance(row, dict):
            headers.update(row.keys())
    
    header_list = sorted(list(headers))

    if not header_list:
        return {"error": "Could not determine CSV headers from the provided data."}

    # Write to CSV
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header_list)
            writer.writeheader()
            for row in data:
                if isinstance(row, dict):
                    writer.writerow(row)
                else:
                    # Fallback for primitive items in list
                    writer.writerow({header_list[0]: str(row)})
                    
        return {
            "status": "success",
            "message": f"Successfully exported {len(data)} rows.",
            "file_path": filepath
        }
    except Exception as e:
        return {"error": f"Failed to write CSV file: {str(e)}"}
