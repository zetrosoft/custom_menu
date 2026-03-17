import frappe
import json
import os

def export_to_json(doctype, filename):
    print(f"Exporting {doctype}...")
    
    # Ambil semua field
    data = frappe.get_all(doctype, fields="*")
    
    if not data:
        print(f"No data found for {doctype}")
        return

    # Path di dalam container
    output_path = f"/home/frappe/frappe-bench/apps/custom_menu/exports/{filename}"
    
    # Pastikan folder ada
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)
    
    print(f"Successfully exported {len(data)} records to {output_path}")
