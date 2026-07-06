"""
Agent: data_exporter_agent
----------------------------
Takes structured JSON data and saves it to a file in the archive/outputs folder.
Supports CSV, JSON, and MD formats.

Primary function: data_exporter_agent(data_json, filename_prefix, format)
"""

import os
import json
import csv
from datetime import datetime

# ── Agent metadata ─────────────────────────────────────────────────────────────

DESCRIPTION = (
    "Exports structured JSON data to a file (CSV, JSON, or MD). "
    "Use this when the user asks to save, write, or export data. "
    "Returns the absolute path to the saved file."
)

PARAMETERS = {
    "data_json": {
        "type":        "string",
        "required":    False,
        "description": "A JSON-formatted string representing the data. (Not required if source_file is provided).",
    },
    "source_file": {
        "type":        "string",
        "required":    False,
        "description": "Absolute filepath to a JSON file containing the data to export. Use this when the system tells you the data was saved to a memory file.",
    },
    "filename_prefix": {
        "type":        "string",
        "required":    False,
        "description": "A short descriptive prefix for the filename (e.g. 'founding_members'). Default is 'export'.",
    },
    "format": {
        "type":        "string",
        "required":    False,
        "description": "The file format to export to. Can be 'csv', 'json', or 'md'. You can also pass multiple separated by commas (e.g. 'csv,md'). Default is 'csv'.",
    }
}

# ── Primary function ───────────────────────────────────────────────────────────

def data_exporter_agent(data_json: str = "", source_file: str = "", filename_prefix: str = "export", format: str = "csv", **kwargs) -> dict:
    """
    Parse a JSON string or read from a source file, and write to a structured file.
    """
    if source_file:
        if not os.path.exists(source_file):
            return {"error": f"source_file not found: {source_file}"}
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load JSON from source_file: {e}"}
    elif data_json:
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON string format provided: {e}"}
    else:
        return {"error": "You must provide either 'data_json' or 'source_file'."}

    format = format.lower().strip()
    if format not in ["csv", "json", "md"]:
        format = "csv"

    # Ensure output directory exists
    output_dir = os.path.join(os.getcwd(), "archive", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(c if c.isalnum() else "_" for c in filename_prefix)
    filename = f"{safe_prefix}_{timestamp}.{format}"
    filepath = os.path.join(output_dir, filename)

    try:
        if format == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return {
                "status": "success",
                "message": "Successfully exported JSON file.",
                "file_path": filepath
            }
            
        elif format == "md":
            with open(filepath, "w", encoding="utf-8") as f:
                if isinstance(data, dict):
                    for k, v in data.items():
                        f.write(f"### {str(k).replace('_', ' ').title()}\\n")
                        if isinstance(v, list):
                            for item in v:
                                f.write(f"- {item}\\n")
                            f.write("\\n")
                        else:
                            f.write(f"{v}\\n\\n")
                elif isinstance(data, list):
                    for item in data:
                        f.write(f"- {item}\\n")
                else:
                    f.write(str(data))
            return {
                "status": "success",
                "message": "Successfully exported Markdown file.",
                "file_path": filepath
            }
            
        elif format == "csv":
            # CSV logic (expects a list of dicts)
            if not isinstance(data, list):
                if isinstance(data, dict):
                    data = [data]
                else:
                    return {"error": "For CSV export, data must be a JSON array of objects or a dictionary."}
            
            if len(data) == 0:
                return {"error": "Data list is empty."}
                
            first_item = data[0]
            if not isinstance(first_item, dict):
                 return {"error": "For CSV export, data must be a JSON array of objects."}

            headers = list(first_item.keys())

            with open(filepath, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in data:
                    clean_row = {}
                    for k, v in row.items():
                        if isinstance(v, (list, dict)):
                            clean_row[k] = json.dumps(v)
                        else:
                            clean_row[k] = v
                    writer.writerow(clean_row)

            return {
                "status": "success",
                "message": f"Successfully exported {len(data)} rows to CSV.",
                "file_path": filepath
            }

    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}
