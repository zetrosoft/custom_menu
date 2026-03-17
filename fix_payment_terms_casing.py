import json
import os

base_path = 'apps/custom_menu/exports/'
payment_terms_file = os.path.join(base_path, 'payment_terms_data.json')
customer_file = os.path.join(base_path, 'customer_data.json')
supplier_file = os.path.join(base_path, 'supplier_data.json')

def to_title_case(s):
    if not s:
        return s
    # Khusus untuk "COD", kita biarkan tetap "COD" (All Caps) karena singkatan umum
    if s.upper() == "COD":
        return "COD"
    return s.title()

template_name_map = {}

# 1. Update payment_terms_data.json
if os.path.exists(payment_terms_file):
    print(f"Memproses {payment_terms_file}...")
    with open(payment_terms_file, 'r') as f:
        templates = json.load(f)
    
    for tmpl in templates:
        old_name = tmpl.get('name')
        if old_name:
            new_name = to_title_case(old_name)
            template_name_map[old_name] = new_name
            
            # Update main fields
            tmpl['name'] = new_name
            tmpl['template_name'] = new_name
            
            # Update child table (terms)
            if 'terms' in tmpl:
                for term in tmpl['terms']:
                    term['parent'] = new_name
                    if term.get('payment_term'):
                        term['payment_term'] = to_title_case(term['payment_term'])
    
    # Backup dan simpan
    if not os.path.exists(payment_terms_file + '.bak'):
        os.rename(payment_terms_file, payment_terms_file + '.bak')
    
    with open(payment_terms_file, 'w') as f:
        json.dump(templates, f, indent=1)
    print(f"Payment Terms Template telah diperbarui ke Title Case.")

# 2. Update references in Customer and Supplier
for data_file in [customer_file, supplier_file]:
    if os.path.exists(data_file):
        print(f"Memproses referensi di {data_file}...")
        with open(data_file, 'r') as f:
            records = json.load(f)
        
        updated = 0
        for rec in records:
            old_pt = rec.get('payment_terms')
            if old_pt and old_pt in template_name_map:
                rec['payment_terms'] = template_name_map[old_pt]
                updated += 1
            elif old_pt:
                # Jika tidak ada di map, coba ubah langsung
                rec['payment_terms'] = to_title_case(old_pt)
                updated += 1
        
        with open(data_file, 'w') as f:
            json.dump(records, f, indent=1)
        print(f"Selesai memperbarui {updated} referensi di {os.path.basename(data_file)}.")

print("\nRingkasan Perubahan:")
for old, new in list(template_name_map.items()):
    if old != new:
        print(f"  {old} -> {new}")
