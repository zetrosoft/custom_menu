import frappe
import json
import os
import requests
import csv
import time
from frappe.model.document import Document
from frappe import _
from custom_menu.api import call_ai_api

class AISmartImporter(Document):
    pass

def get_file_data(file_url, limit=None):
    if not file_url: return [], []
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    header, all_rows = [], []
    try:
        content = file_doc.get_content()
        if file_url.lower().endswith(".csv"):
            from frappe.utils.csvutils import read_csv_content
            rows = read_csv_content(content)
        else:
            from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file
            rows = read_xlsx_file_from_attached_file(fcontent=content)
            
        if rows:
            raw_header = []
            for r in rows:
                if any(c is not None and str(c).strip() != "" for c in r):
                    raw_header = r
                    break
            
            last_idx = 0
            for i, c in enumerate(raw_header):
                if c is not None and str(c).strip() != "":
                    last_idx = i
            
            header = [str(c).strip() if c is not None else f"Column {i}" for i, c in enumerate(raw_header[:last_idx+1])]
            
            data_start = False
            for r in rows:
                if not data_start:
                    if r == raw_header:
                        data_start = True
                    continue
                
                row_values = r[:len(header)]
                if any(c is not None and str(c).strip() != "" for c in row_values):
                    clean_row = [str(c).strip() if c is not None else "" for c in row_values]
                    all_rows.append(clean_row)
                    if limit and len(all_rows) >= limit:
                        break
                        
    except Exception as e:
        frappe.log_error(f"File reading error: {str(e)}", "AI Smart Importer")
        raise e
    return header, all_rows

def extract_json(text):
    if not text: return None
    text = text.strip()
    try: return json.loads(text)
    except:
        import re
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: return None
    return None

@frappe.whitelist()
def start_background_analysis(docname):
    doc = frappe.get_doc("AI Smart Importer", docname)
    
    if doc.target_doctype == "Account":
        frappe.throw(_("Import for 'Account' (COA) must be done manually or via standard Frappe Import for better hierarchy integrity."))
        
    if doc.status == "Analyzing":
        return {"status": "Already Analyzing", "progress": doc.current_progress}
    doc.status = "Analyzing"
    doc.save()
    frappe.db.commit()
    frappe.enqueue(method="custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.run_analysis_job", queue="long", timeout=50000, docname=docname, user=frappe.session.user)
    return {"status": "Job Started"}

@frappe.whitelist()
def stop_analysis(docname):
    doc = frappe.get_doc("AI Smart Importer", docname)
    if doc.status == "Analyzing":
        doc.status = "Draft"
        doc.save()
        frappe.db.commit()
        return {"status": "Stop Signal Sent"}
    return {"status": "Not Running"}

@frappe.whitelist()
def auto_resume_broken_jobs():
    from frappe.utils import now_datetime, add_to_date
    stuck_jobs = frappe.get_all("AI Smart Importer", filters={"status": "Analyzing", "modified": ["<", add_to_date(now_datetime(), minutes=-10)]}, fields=["name", "owner"])
    for job in stuck_jobs:
        frappe.enqueue(method="custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.run_analysis_job", queue="long", timeout=50000, docname=job.name, user=job.owner)
    return len(stuck_jobs)

def run_analysis_job(docname, user=None):
    if user: frappe.set_user(user)
    doc = frappe.get_doc("AI Smart Importer", docname)
    try:
        limit = (doc.sample_size or 20) if doc.is_sample else None
        header, all_rows = get_file_data(doc.import_file, limit=limit)
        if not header:
            doc.db_set("status", "Failed")
            doc.db_set("results_log", "Error: Could not detect headers.")
            return
        total = len(all_rows)
        doc.db_set("total_records", total)
        mapping_list = []
        if doc.mapping_json:
            try: mapping_list = json.loads(doc.mapping_json).get("mapping", [])
            except: pass
        if not mapping_list:
            def get_all_fields(dt):
                meta = frappe.get_meta(dt)
                return [{"label": f.label, "fieldname": f.fieldname, "reqd": f.reqd, "fieldtype": f.fieldtype} for f in meta.fields if not f.hidden and f.fieldtype not in ["Section Break", "Column Break", "Button"]]
            mapping_prompt = f"TASK: Map columns to fields. HEADERS: {json.dumps(header)}. SAMPLES: {json.dumps(all_rows[:3])}. FIELDS: {doc.target_doctype}: {json.dumps(get_all_fields(doc.target_doctype))}, Address: {json.dumps(get_all_fields('Address'))}, Contact: {json.dumps(get_all_fields('Contact'))}. Respond ONLY JSON: {{'mapping': [{{'column': '...', 'target_doctype': '...', 'target_fieldname': '...'}}]}}"
            res_mapping = call_ai_api(mapping_prompt)
            mapping_data = extract_json(res_mapping)
            raw_mapping = mapping_data.get("mapping") if isinstance(mapping_data, dict) else (mapping_data if isinstance(mapping_data, list) else [])
            mapping_list = []
            seen_fields = set()
            sorted_raw = sorted(raw_mapping, key=lambda x: 1 if "nama" in x.get("column", "").lower() else 2)
            for m in sorted_raw:
                field_key = f"{m.get('target_doctype')}:{m.get('target_fieldname')}"
                if field_key not in seen_fields:
                    mapping_list.append(m); seen_fields.add(field_key)
            if not mapping_list: raise Exception("AI mapping failed.")
            doc.db_set("mapping_json", json.dumps({"mapping": mapping_list}))
        current_idx = doc.current_progress or 0
        batch_size = 3
        m_obj_init = json.loads(frappe.db.get_value("AI Smart Importer", docname, "mapping_json") or '{"mapping": [], "parsed_data": []}')
        parsed_data_accumulator = m_obj_init.get("parsed_data", [])
        mapped_doctypes = [dt for dt in list(set([m.get("target_doctype") for m in mapping_list])) if frappe.db.exists("DocType", dt)]
        def get_unmapped_mandatory(dt, mappings):
            if not frappe.db.exists("DocType", dt): return []
            mapped_f = [m.get("target_fieldname") for m in mappings if m.get("target_doctype") == dt]
            return [f.fieldname for f in frappe.get_meta(dt).fields if f.reqd and f.fieldname not in mapped_f]
        missing_reqs = {dt: get_unmapped_mandatory(dt, mapping_list) for dt in mapped_doctypes}
        for i in range(current_idx, total, batch_size):
            db_status = frappe.db.get_value("AI Smart Importer", docname, "status")
            if db_status != "Analyzing": return
            end = min(i + batch_size, total)
            batch_rows = all_rows[i:end]
            rows_with_header = [dict(zip(header, r)) for r in batch_rows]
            frappe.publish_realtime("ai_analysis_progress", {"progress": end, "total": total, "msg": f"AI Parsing {end}/{total}..."}, user=user)
            transform_prompt = f"MAPPING: {json.dumps(mapping_list)}\nDATA: {json.dumps(rows_with_header)}\nRULES:\n1. Respond ONLY JSON array of objects with keys: {mapped_doctypes}.\n2. Fill mandatory {json.dumps(missing_reqs)} with smart defaults.\n3. For {doc.target_doctype}, if Name contains PT/CV/UD/Toko, set type to 'Company', else 'Individual'."
            res_batch = call_ai_api(transform_prompt)
            if not res_batch: continue
            parsed = extract_json(res_batch)
            if isinstance(parsed, list):
                parsed_data_accumulator.extend(parsed)
                doc.db_set("mapping_json", json.dumps({"mapping": mapping_list, "parsed_data": parsed_data_accumulator}))
                doc.db_set("current_progress", end)
                frappe.db.commit()
            time.sleep(0.1)
        doc.db_set("status", "Analyzed")
        frappe.db.commit()
        frappe.publish_realtime("ai_analysis_progress", {"progress": total, "total": total, "msg": "Analysis Complete!"}, user=user)
    except Exception as e:
        frappe.db.rollback()
        doc.db_set("status", "Failed")
        frappe.db.commit()
        frappe.log_error(title="AI Importer Job Failed", message=frappe.get_traceback() or str(e))
        frappe.publish_realtime("ai_analysis_progress", {"status": "Failed", "msg": str(e)}, user=user)

@frappe.whitelist()
def get_analysis_status(docname):
    doc = frappe.get_doc("AI Smart Importer", docname)
    return {"status": doc.status, "progress": doc.current_progress, "total": doc.total_records, "mapping_json": doc.mapping_json}

@frappe.whitelist()
def get_import_preview(docname):
    import random
    doc = frappe.get_doc("AI Smart Importer", docname)
    if not doc.mapping_json: return []
    try:
        data = json.loads(doc.mapping_json)
        parsed_data = data.get("parsed_data", [])
        if not parsed_data: return []
        sample_size = min(len(parsed_data), 5)
        return random.sample(parsed_data, sample_size)
    except: return []

@frappe.whitelist()
def execute_import(docname):
    doc = frappe.get_doc("AI Smart Importer", docname)
    if not doc.mapping_json: frappe.throw(_("Analyze first."))
    doc.status = "Processing"
    doc.save()
    frappe.db.commit()
    frappe.enqueue(method="custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.run_import_job", queue="long", timeout=50000, docname=docname, user=frappe.session.user)
    return True

def run_import_job(docname, user=None):
    if user: frappe.set_user(user)
    doc = frappe.get_doc("AI Smart Importer", docname)
    data_store = json.loads(doc.mapping_json)
    parsed_records = data_store.get("parsed_data", [])
    target_doctype = doc.target_doctype
    meta = frappe.get_meta(target_doctype)
    link_fields = {df.fieldname: df.options for df in meta.fields if df.fieldtype == "Link"}
    if doc.import_criteria == "Replace All":
        frappe.db.sql(f"DELETE FROM `tab{target_doctype}`")
        frappe.db.commit()
    import_stats = {"parent": 0, "address": 0, "contact": 0, "errors": []}
    total_parsed = len(parsed_records)
    for idx, payload in enumerate(parsed_records, start=1):
        if idx % 10 == 0:
            frappe.publish_realtime("ai_import_progress", {"progress": idx, "total": total_parsed, "msg": f"Importing {idx}/{total_parsed}"}, user=user)
        try:
            # Helper to get value from dict with multiple naming conventions
            def get_val(data, fieldname):
                if not isinstance(data, dict): return None
                # Try exact match
                if fieldname in data: return data[fieldname]
                # Try normalized search
                fn_norm = fieldname.lower().replace("_", "").replace(" ", "")
                for k in data.keys():
                    if k.lower().replace("_", "").replace(" ", "") == fn_norm:
                        return data[k]
                return None

            # 1. Get Parent Data (Supplier/Customer/Account)
            p_data_raw = payload.get(target_doctype, {})
            # Flatten if it's a list (AI sometimes returns a list even for one record)
            if isinstance(p_data_raw, list): p_data_raw = p_data_raw[0] if p_data_raw else {}
            
            # If AI returned a single string instead of object
            if isinstance(p_data_raw, str):
                name_f = meta.title_field or "name"
                if target_doctype == "Account": name_f = "account_name"
                p_data = {name_f: p_data_raw}
            else:
                p_data = p_data_raw.copy()

            if not p_data:
                for k in payload.keys():
                    if k.lower() == target_doctype.lower():
                        res = payload[k]
                        p_data = res[0] if isinstance(res, list) else res
                        break
            
            if not p_data: continue
            
            # Resolve name_val using normalized search
            name_val = get_val(p_data, "account_name") or get_val(p_data, "supplier_name") or get_val(p_data, "customer_name") or get_val(p_data, "name")
            if not name_val or str(name_val).startswith("Import "): continue
            
            # Re-map keys to match Frappe fieldnames exactly
            clean_p_data = {"doctype": target_doctype}
            for f in meta.fields:
                val = get_val(p_data, f.fieldname)
                if val is not None: clean_p_data[f.fieldname] = val
            
            # Special logic for Account (COA)
            if target_doctype == "Account":
                if not get_val(clean_p_data, "account_name"): clean_p_data["account_name"] = name_val
                if not get_val(clean_p_data, "parent_account"): clean_p_data["parent_account"] = ""
                if not get_val(clean_p_data, "company"): 
                    clean_p_data["company"] = frappe.db.get_single_value("Global Defaults", "default_company") or "PT. SIUMANG TEMAN SUKSES"
                # Fix is_group to integer
                is_g = get_val(p_data, "is_group")
                try: clean_p_data["is_group"] = 1 if float(str(is_g)) >= 1 else 0
                except: clean_p_data["is_group"] = 0
            
            # Ensure link fields exist
            for fieldname, value in clean_p_data.items():
                if fieldname in link_fields and value and fieldname != "parent_account": 
                    try: ensure_master_data_exists(link_fields[fieldname], value)
                    except: clean_p_data[fieldname] = None
            
            p_doc = frappe.get_doc(clean_p_data).insert(ignore_permissions=True)
            frappe.db.commit()
            import_stats["parent"] += 1
            
            # Address Recovery
            a_data = payload.get("Address", {})
            if isinstance(a_data, list): a_data = a_data[0] if a_data else {}
            if not a_data or (isinstance(a_data, dict) and not any(a_data.values())):
                rec_addr = {f: p_data.get(f) for f in ["address_line1", "city", "state", "country", "pincode"] if p_data.get(f)}
                if rec_addr: a_data = rec_addr
            if a_data and isinstance(a_data, dict) and (a_data.get("address_line1") or a_data.get("city")):
                if not a_data.get("city"): a_data["city"] = "Indonesia"
                if not a_data.get("address_line1"): a_data["address_line1"] = "Alamat tidak terdeteksi"
                if not a_data.get("address_title"): a_data["address_title"] = name_val
                if not a_data.get("country"): a_data["country"] = "Indonesia"
                a_data.update({"doctype": "Address", "links": [{"link_doctype": target_doctype, "link_name": p_doc.name}]})
                try:
                    frappe.get_doc(a_data).insert(ignore_permissions=True)
                    frappe.db.commit(); import_stats["address"] += 1
                except: frappe.db.rollback()
            
            # Contact Recovery
            c_data = payload.get("Contact", {})
            if isinstance(c_data, list): c_data = c_data[0] if c_data else {}
            if not c_data or (isinstance(c_data, dict) and not any(c_data.values())):
                rec_con = {f: p_data.get(f) for f in ["first_name", "mobile_no", "phone", "email_id"] if p_data.get(f)}
                if rec_con: c_data = rec_con
            if c_data and isinstance(c_data, dict) and (c_data.get("first_name") or c_data.get("mobile_no") or c_data.get("email_id")):
                if not c_data.get("first_name"): c_data["first_name"] = name_val
                c_data.update({"doctype": "Contact", "links": [{"link_doctype": target_doctype, "link_name": p_doc.name}]})
                try:
                    frappe.get_doc(c_data).insert(ignore_permissions=True)
                    frappe.db.commit(); import_stats["contact"] += 1
                except: frappe.db.rollback()
        except Exception as e:
            frappe.db.rollback()
            if len(import_stats["errors"]) < 1000: import_stats["errors"].append(f"Row {idx}: {str(e)}")
    doc.results_log = json.dumps(import_stats, indent=2)
    doc.status = "Completed"
    doc.save()
    frappe.db.commit()
    frappe.publish_realtime("ai_import_progress", {"progress": total_parsed, "total": total_parsed, "msg": "Import Completed!"}, user=user)

def ensure_master_data_exists(doctype, value):
    if not value or not doctype: return
    if frappe.db.exists(doctype, value): return
    try:
        new_doc = frappe.new_doc(doctype)
        if doctype in ["Customer Group", "Supplier Group", "Territory"]:
            if doctype == "Customer Group": p_f, n_f, r_d = "parent_customer_group", "customer_group_name", _("All Customer Groups")
            elif doctype == "Supplier Group": p_f, n_f, r_d = "parent_supplier_group", "supplier_group_name", _("All Supplier Groups")
            else: p_f, n_f, r_d = "parent_territory", "territory_name", _("All Territories")
            root_node = frappe.db.get_value(doctype, {"is_group": 1, p_f: ("in", ["", None])}, "name")
            if not root_node:
                if not frappe.db.exists(doctype, r_d):
                    root_doc = frappe.new_doc(doctype)
                    root_doc.set(n_f, r_d); root_doc.is_group = 1
                    root_doc.insert(ignore_permissions=True); frappe.db.commit()
                root_node = r_d
            new_doc.set(n_f, value); new_doc.set(p_f, root_node); new_doc.is_group = 0
        elif doctype == "Payment Terms Template":
            new_doc.template_name = value
            new_doc.append("terms", {"invoice_portion": 100, "credit_days": 0, "due_date_based_on": "Day(s) after invoice date"})
        else:
            meta = frappe.get_meta(doctype)
            t_f = meta.title_field or "name"
            if t_f != "name": new_doc.set(t_f, value)
            else: new_doc.name = value
            if doctype == "Account": return
        new_doc.insert(ignore_permissions=True); frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(title="Auto-create master data failed", message=f"Doctype: {doctype}, Value: {value}, Error: {str(e)}")
        raise e
