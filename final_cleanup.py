import json
import os

target_dir = 'frappe-bench/apps/custom_menu/exports/'
customer_file = os.path.join(target_dir, 'customer_data.json')

def is_numeric(s):
    if not s: return False
    try:
        float(s)
        return any(c.isdigit() for c in s) and not any(c.isalpha() for c in s)
    except:
        return False

if os.path.exists(customer_file):
    print(f"Pembersihan file: {customer_file}")
    with open(customer_file, 'r') as f:
        data = json.load(f)
    
    clean_data = [d for d in data if not is_numeric(d.get('customer_name'))]
    removed = len(data) - len(clean_data)
    
    print(f"Data dihapus: {removed}")
    
    with open(customer_file, 'w') as f:
        json.dump(clean_data, f, indent=1)
    print("Selesai.")
