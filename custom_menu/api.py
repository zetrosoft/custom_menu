import frappe
import json
import os
import requests
from frappe import _
from custom_menu.utils import parse_smart_address

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Constants for AI models
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_URL = "http://localhost:11434/api/generate"

TRANSACTION_DOCTYPES = [
    "Journal Entry", "Payment Entry", "Purchase Invoice", "Sales Invoice",
    "Purchase Receipt", "Delivery Note", "Purchase Order", "Sales Order",
    "Stock Entry", "Material Request", "Quotation", "Supplier Quotation",
    "Request for Quotation", "Work Order", "Job Card", "Asset",
    "Asset Movement", "Asset Repair", "Payment Request", "Expense Claim",
    "Leave Application", "Attendance", "Salary Slip", "Timesheet",
    "Quality Inspection", "BOM", "Process Loss Entry", "Work Order Item",
    "Pick List", "Packing Slip", "Landed Cost Voucher", "Asset Capitalization",
    "Stock Reconciliation", "Period Closing Voucher", "Bank Clearance",
    "Payment Reconciliation", "POS Invoice", "Loyalty Point Entry"
]

MASTER_DOCTYPES = [
    "Item", "Item Group", "Item Attribute", "Item Variant Attribute", "UOM", "Brand", "Warehouse",
    "Account", "Cost Center", "Mode of Payment", "Payment Term", "Currency", "Tax Category", 
    "Tax Withholding Category", "Party Type", "Bank", "Bank Account", "Fiscal Year", "Tax Rule",
    "Customer", "Customer Group", "Sales Person", "Territory", "Sales Partner", "Lead", 
    "Opportunity", "Campaign", "Address", "Contact",
    "Supplier", "Supplier Group",
    "Employee", "Department", "Designation", "Employment Type", "Branch", "Employee Grade", 
    "Leave Type", "Holiday List", "Shift Type", "Salary Component", "Salary Structure",
    "Project", "Activity Type", "Asset Category",
    "Company", "Terms and Conditions", "Price List", "Item Price", "Pricing Rule"
]

def get_ai_settings():
    settings = frappe.get_single("Custom Brand Settings")
    return {
        "gemini_api_key": settings.get_password("gemini_api_key"),
        "ollama_url": settings.ollama_url or "http://localhost:11434/api/generate",
        "ollama_model": settings.ollama_model or "gemma3:4b"
    }

def call_ai_api(prompt, system_prompt=None):
    """
    Tries Ollama (Gemma 3) first, fallbacks to Gemini 2.0 Flash.
    """
    settings = get_ai_settings()
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    
    # 1. Try Ollama (Gemma 3)
    try:
        response = requests.post(settings["ollama_url"], json={
            "model": settings["ollama_model"],
            "prompt": full_prompt,
            "stream": False
        }, timeout=300) # Increased timeout to 5 minutes
        
        if response.status_code == 200:
            res_json = response.json()
            ollama_res = res_json.get("response")
            return ollama_res
        else:
            frappe.log_error(f"Ollama Error Status {response.status_code}: {response.text}", "AI Smart Importer - Ollama")
    except Exception as e:
        frappe.log_error(f"Ollama Connection Error: {str(e)}", "AI Smart Importer - Ollama")

    # 2. Gemini Fallback (Gemini 2.0 Flash)
    if not settings["gemini_api_key"]:
        # Don't throw, just return None so the caller can retry or log appropriately
        return None
        
    if not genai:
        frappe.log_error("Google Generative AI library is not installed. Fallback skipped.", "AI Smart Importer - Gemini")
        return None

    try:
        genai.configure(api_key=settings["gemini_api_key"])
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        frappe.log_error(f"Gemini Fallback Error: {str(e)}", "AI Smart Importer - Gemini")
        return None

@frappe.whitelist()
def get_doctype_stats(type_filter="transaction"):
    doctypes = TRANSACTION_DOCTYPES if type_filter == "transaction" else MASTER_DOCTYPES
    if type_filter == "all":
        doctypes = TRANSACTION_DOCTYPES + MASTER_DOCTYPES
        
    doctypes = sorted(list(set(doctypes)))
    stats = []
    for doctype in doctypes:
        try:
            if frappe.db.exists("DocType", doctype):
                stats.append({"doctype": doctype, "count": frappe.db.count(doctype)})
        except Exception:
            continue
    return stats

@frappe.whitelist()
def clear_selected_doctypes(doctypes):
    if isinstance(doctypes, str):
        doctypes = json.loads(doctypes)
    
    frappe.only_for("System Manager")
    allowed_doctypes = TRANSACTION_DOCTYPES + MASTER_DOCTYPES
    results = {}
    
    for doctype in doctypes:
        if doctype not in allowed_doctypes or not frappe.db.exists("DocType", doctype):
            continue

        try:
            count = 0
            errors = []
            
            if doctype == "Account":
                from frappe.utils.nestedset import rebuild_tree
                try:
                    rebuild_tree("Account", "parent_account")
                except:
                    pass
                
                # Ulangi penghapusan beberapa kali untuk memastikan child terhapus duluan
                for _ in range(5):
                    # Ambil yang bukan root dan urutkan dari yang paling dalam (lft desc)
                    doc_names = frappe.db.get_all(doctype, order_by="lft desc", pluck="name")
                    if not doc_names: break
                    
                    total_docs = len(doc_names)
                    for i, name in enumerate(doc_names):
                        try:
                            # Lindungi Root Nodes Utama Siumang
                            if name in ["Application of Funds - SIUMANG", "Sources of Funds - SIUMANG", "Equity - SIUMANG", "Income - SIUMANG", "Expense - SIUMANG"]:
                                continue
                                
                            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True, delete_permanently=True)
                            count += 1
                            
                            # Kirim progres penghapusan setiap 10 records
                            if i % 10 == 0 or i == total_docs - 1:
                                frappe.publish_realtime("clear_record_progress", {
                                    "current": i + 1,
                                    "total": total_docs,
                                    "doctype": doctype
                                }, user=frappe.session.user)
                                
                        except:
                            continue
                    frappe.db.commit()
            else:
                doc_names = frappe.db.get_all(doctype, pluck="name")
                total_docs = len(doc_names)
                for i, name in enumerate(doc_names):
                    try:
                        # Force update docstatus to 2 (Cancelled) in DB and commit
                        frappe.db.sql(f"UPDATE `tab{doctype}` SET docstatus = 2 WHERE name = %s", name)
                        frappe.db.commit()
                        
                        try:
                            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True, delete_permanently=True)
                        except Exception:
                            # Hard delete via SQL as last resort
                            frappe.db.sql(f"DELETE FROM `tab{doctype}` WHERE name = %s", name)
                            table_meta = frappe.get_meta(doctype)
                            for child in table_meta.get_table_fields():
                                frappe.db.sql(f"DELETE FROM `tab{child.options}` WHERE parent = %s", name)
                            frappe.db.commit()
                                
                        count += 1
                        
                        # Kirim progres penghapusan setiap 10 records
                        if i % 10 == 0 or i == total_docs - 1:
                            frappe.publish_realtime("clear_record_progress", {
                                "current": i + 1,
                                "total": total_docs,
                                "doctype": doctype
                            }, user=frappe.session.user)
                            
                    except Exception as e:
                        errors.append(f"{name}: {str(e)}")
            
            results[doctype] = {"count": count, "errors": errors}
        except Exception as e:
            results[doctype] = {"count": 0, "errors": [str(e)]}
    
    frappe.db.commit()
    return results

@frappe.whitelist()
def analyze_with_gemini(doctype, file_url):
    """
    Whitelist name kept for compatibility. Now uses Ollama first.
    """
    frappe.only_for("System Manager")
    from frappe.utils.file_manager import get_file_path
    import openpyxl

    file_path = get_file_path(file_url.split('/')[-1])
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active
    rows = list(sheet.rows)
    header = [str(cell.value) for cell in rows[0] if cell.value]
    sample_data = [[str(cell.value) if cell.value is not None else "" for cell in row] for row in rows[1:4]]

    def get_meta_fields(dt):
        meta = frappe.get_meta(dt)
        return [{"label": f.label, "fieldname": f.fieldname, "fieldtype": f.fieldtype} 
                for f in meta.fields if not f.hidden and f.fieldtype not in ["Section Break", "Column Break", "Button"]]

    prompt = f"""
    You are a data analyst for Frappe/ERPNext. Your task is to map file columns to DocTypes.
    Target: {doctype}, Address, Contact.
    Header: {json.dumps(header)}
    Sample Data: {json.dumps(sample_data)}
    
    Fields for {doctype}: {json.dumps(get_meta_fields(doctype))}
    Fields for Address: {json.dumps(get_meta_fields("Address"))}
    Fields for Contact: {json.dumps(get_meta_fields("Contact"))}
    
    Return ONLY a JSON mapping like:
    {{
      "mapping": [
        {{"column": "Nama", "target_doctype": "{doctype}", "target_fieldname": "customer_name"}},
        {{"column": "Alamat", "target_doctype": "Address", "target_fieldname": "address_line1"}}
      ]
    }}
    """
    
    res_text = call_ai_api(prompt)
    try:
        # Clean markdown if present
        res_text = res_text.replace('```json', '').replace('```', '').strip()
        return json.loads(res_text)
    except Exception as e:
        frappe.throw(_("AI Analysis failed to parse JSON: {0}").format(str(e)))

@frappe.whitelist()
def process_smart_import(doctype, file_url, mapping):
    frappe.only_for("System Manager")
    if isinstance(mapping, str): mapping = json.loads(mapping)

    from frappe.utils.file_manager import get_file_path
    import openpyxl
    
    file_path = get_file_path(file_url.split('/')[-1])
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active
    rows = list(sheet.rows)
    header = [cell.value for cell in rows[0]]
    
    stats = {"parent": 0, "address": 0, "contact": 0, "errors": []}
    
    for idx, row in enumerate(rows[1:], start=2):
        row_data = dict(zip(header, [cell.value for cell in row]))
        
        # Gunakan savepoint agar kegagalan satu baris tidak membatalkan seluruh transaksi
        savepoint_name = f"row_{idx}"
        frappe.db.savepoint(savepoint_name)
        
        try:
            parent_doc = {"doctype": doctype}
            address_doc = {"doctype": "Address"}
            contact_doc = {"doctype": "Contact"}
            
            for m in mapping.get("mapping", []):
                val = row_data.get(m["column"])
                if val is None: continue
                
                if m["target_doctype"] == doctype:
                    parent_doc[m["target_fieldname"]] = val
                elif m["target_doctype"] == "Address":
                    if m["target_fieldname"] == "address_line1":
                        address_doc.update(parse_smart_address(str(val)))
                    elif m["target_fieldname"] == "phone":
                        from custom_menu.utils import format_phone_number
                        address_doc["phone"] = format_phone_number(val)
                    else:
                        address_doc[m["target_fieldname"]] = val
                elif m["target_doctype"] == "Contact":
                    if m["target_fieldname"] == "phone" or m["target_fieldname"] == "mobile_no":
                        from custom_menu.utils import format_phone_number
                        contact_doc[m["target_fieldname"]] = format_phone_number(val)
                    else:
                        contact_doc[m["target_fieldname"]] = val
            
            # Save parent
            p = frappe.get_doc(parent_doc).insert(ignore_permissions=True)
            stats["parent"] += 1
            
            # Save address
            if address_doc.get("address_line1"):
                if not address_doc.get("address_type"):
                    address_doc["address_type"] = "Billing"
                address_doc["links"] = [{"link_doctype": doctype, "link_name": p.name}]
                frappe.get_doc(address_doc).insert(ignore_permissions=True)
                stats["address"] += 1
                
            # Save contact
            if len(contact_doc) > 1:
                contact_doc["links"] = [{"link_doctype": doctype, "link_name": p.name}]
                frappe.get_doc(contact_doc).insert(ignore_permissions=True)
                stats["contact"] += 1
                
        except Exception as e:
            stats["errors"].append(f"Row {idx}: {str(e)}")
            frappe.db.rollback(save_point=savepoint_name)
            
    frappe.db.commit()
    return stats

@frappe.whitelist()
def get_migration_file_list():
    """List JSON files in exports and their corresponding DocTypes with record counts."""
    base_path = "/home/frappe/frappe-bench/apps/custom_menu/exports"
    mapping = [
        ("account_data.json", "Account", "Daftar Akun (Chart of Accounts)"),
        ("customer_group_data.json", "Customer Group", "Pengelompokan Pelanggan"),
        ("supplier_group_data.json", "Supplier Group", "Pengelompokan Pemasok"),
        ("payment_terms_data.json", "Payment Terms Template", "Template Syarat Pembayaran"),
        ("customer_data.json", "Customer", "Data Master Pelanggan"),
        ("supplier_data.json", "Supplier", "Data Master Pemasok"),
        ("address_data.json", "Address", "Alamat Lengkap"),
        ("contact_data.json", "Contact", "Informasi Kontak Person")
    ]
    
    available = []
    for filename, doctype, description in mapping:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else 0
            except:
                count = 0
                
            file_size = os.path.getsize(file_path)
            available.append({
                "doctype": doctype,
                "filename": filename,
                "description": description,
                "count": count,
                "size": f"{round(file_size / 1024, 2)} KB"
            })
    return available

@frappe.whitelist()
def import_single_doctype(doctype):
    """Import a single doctype from JSON and return stats."""
    frappe.only_for("System Manager")
    from custom_menu.import_data import run_import_single
    return run_import_single(doctype)

@frappe.whitelist()
def start_master_data_migration(selected_doctypes=None):
    frappe.only_for("System Manager")
    
    if isinstance(selected_doctypes, str):
        selected_doctypes = json.loads(selected_doctypes)
        
    from custom_menu.import_data import run_import
    # Gunakan background job agar tidak timeout jika data banyak
    frappe.enqueue(run_import, queue='long', timeout=3600, selected_doctypes=selected_doctypes)
    return _("Migration for {0} started in background. Please check the logs/console for progress.").format(", ".join(selected_doctypes) if selected_doctypes else "all")

@frappe.whitelist()
def get_preview_data(doctype):
    if not frappe.db.exists("DocType", doctype): return []
    meta = frappe.get_meta(doctype)
    fields = ["name", "creation", (meta.title_field or "name")]
    return frappe.get_all(doctype, fields=list(set(fields)), limit=20, order_by="creation desc")
