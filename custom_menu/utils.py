import frappe
import csv
import re

def parse_smart_address(raw_address):
    """
    Sangat sederhana: Mencoba memisahkan jalan, kota, provinsi dari string alamat.
    """
    if not raw_address:
        return {}
    
    parts = [p.strip() for p in raw_address.split(',')]
    res = {
        "address_line1": parts[0],
        "address_type": "Billing"
    }
    
    if len(parts) > 1:
        res["city"] = parts[1]
    if len(parts) > 2:
        res["state"] = parts[2]
        
    return res

def format_phone_number(phone):
    if not phone: return ""
    phone = str(phone).strip().replace(".0", "")
    if phone.startswith("8"): phone = "0" + phone
    return phone

def import_coa_csv():
    # ... (fungsi eksisting tetap ada jika masih digunakan)
    pass
