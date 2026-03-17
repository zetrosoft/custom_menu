import frappe
import json
import os

def run_import_single(doctype):
    # Map DocType ke filename
    mapping = {
        "Account": "account_data.json",
        "Customer Group": "customer_group_data.json",
        "Supplier Group": "supplier_group_data.json",
        "Payment Terms Template": "payment_terms_data.json",
        "Customer": "customer_data.json",
        "Supplier": "supplier_data.json",
        "Address": "address_data.json",
        "Contact": "contact_data.json"
    }
    
    filename = mapping.get(doctype)
    if not filename:
        return {"success": 0, "skipped": 0, "errors": [f"No mapping found for {doctype}"]}
        
    base_path = "/home/frappe/frappe-bench/apps/custom_menu/exports"
    file_path = os.path.join(base_path, filename)
    
    if not os.path.exists(file_path):
        return {"success": 0, "skipped": 0, "errors": [f"File {filename} not found"]}
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    success = 0
    skipped = 0
    errors = []
    
    if doctype == "Account":
        # Sort berdasarkan 'lft' agar parent diimpor lebih dulu (Nested Set)
        data = sorted(data, key=lambda x: x.get('lft', 0))

    # Gunakan multiple passes untuk Account agar parent-child terpenuhi
    passes = 3 if doctype == "Account" else 1
    
    total_records = len(data)
    
    for p in range(passes):
        current_errors = []
        for i, doc_data in enumerate(data):
            doc_name = doc_data.get("name") or doc_data.get(frappe.get_meta(doctype).get_title_field())

            # Pengecekan dasar berdasarkan Primary Key (name)
            if frappe.db.exists(doctype, doc_name):
                if p == 0: skipped += 1
                continue

            # Pengecekan ekstra untuk Customer/Supplier berdasarkan nama agar tidak jadi "Nama - 1"
            if doctype == "Customer" and doc_data.get("customer_name"):
                if frappe.db.exists("Customer", {"customer_name": doc_data.get("customer_name")}):
                    if p == 0: skipped += 1
                    continue

            if doctype == "Supplier" and doc_data.get("supplier_name"):
                if frappe.db.exists("Supplier", {"supplier_name": doc_data.get("supplier_name")}):
                    if p == 0: skipped += 1
                    continue

            try:

                # Pastikan kunci doctype ada di dalam dict sebelum get_doc
                if isinstance(doc_data, dict):
                    doc_data["doctype"] = doctype
                    
                new_doc = frappe.get_doc(doc_data)
                
                # Tambahkan flags untuk mematikan validasi
                new_doc.flags.ignore_mandatory = True
                new_doc.flags.ignore_validate = True
                new_doc.flags.ignore_permissions = True
                new_doc.flags.ignore_links = True
                
                new_doc.insert(ignore_permissions=True)
                success += 1
                
                # Kirim progres setiap 5 records agar UI responsif (hanya di pass pertama atau jika sukses)
                if i % 5 == 0 or i == total_records - 1:
                    frappe.publish_realtime("migration_record_progress", {
                        "current": i + 1,
                        "total": total_records,
                        "doctype": doctype
                    }, user=frappe.session.user)
                    
            except Exception as e:
                # Jika ini pass terakhir, baru masukkan ke error list permanen
                if p == passes - 1:
                    errors.append(f"{doc_name}: {str(e)}")
                else:
                    current_errors.append(f"{doc_name}: {str(e)}")
        
        frappe.db.commit()
        if not current_errors: break # Selesai jika tidak ada error lagi di pass ini
        
    if doctype == "Account" and success > 0:
        from frappe.utils.nestedset import rebuild_tree
        print("Rebuilding Account tree...")
        rebuild_tree("Account", "parent_account")
        frappe.db.commit()
        
    return {"success": success, "skipped": skipped, "errors": errors}

def run_import(selected_doctypes=None):
    # Urutan impor sangat penting karena dependensi
    doctypes_to_import = [
        ("account_data.json", "Account"),
        ("customer_group_data.json", "Customer Group"),
        ("supplier_group_data.json", "Supplier Group"),
        ("payment_terms_data.json", "Payment Terms Template"),
        ("customer_data.json", "Customer"),
        ("supplier_data.json", "Supplier"),
        ("address_data.json", "Address"),
        ("contact_data.json", "Contact")
    ]
    
    base_path = "/home/frappe/frappe-bench/apps/custom_menu/exports"
    
    for filename, doctype in doctypes_to_import:
        # Jika user memilih data tertentu, filter di sini
        if selected_doctypes and doctype not in selected_doctypes:
            continue
            
        file_path = os.path.join(base_path, filename)
        if not os.path.exists(file_path):
            print(f"File {filename} not found, skipping...")
            continue
            
        print(f"\n--- Importing {doctype} from {filename} ---")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        count = 0
        success = 0
        skipped = 0
        errors = []
        
        # Untuk Account, kita perlu sorting agar parent diimpor duluan
        if doctype == "Account":
            # Sort berdasarkan level/depth (asumsi: path length atau parent_account)
            # Cara sederhana: ulangi beberapa kali sampai semua terimpor atau gunakan rekursi
            # Untuk sekarang kita coba import biasa, jika parent belum ada akan error di percobaan pertama
            # Kita bisa memproses is_group=1 dulu
            data = sorted(data, key=lambda x: x.get('is_group', 0), reverse=True)

        for doc_data in data:
            count += 1
            doc_name = doc_data.get("name") or doc_data.get(frappe.get_meta(doctype).get_title_field())
            
            if frappe.db.exists(doctype, doc_name):
                skipped += 1
                continue
            
            try:
                # Bersihkan data dari field sistem yang tidak perlu jika ada
                # Namun karena ini dari get_all("*"), biasanya aman untuk insert kembali
                new_doc = frappe.get_doc(doc_data)
                new_doc.doctype = doctype
                new_doc.insert(ignore_permissions=True)
                success += 1
            except Exception as e:
                errors.append(f"{doc_name}: {str(e)}")
        
        frappe.db.commit()
        print(f"Finished {doctype}: {success} imported, {skipped} skipped, {len(errors)} errors.")
        if errors:
            for err in errors[:5]: # Tampilkan 5 error pertama
                print(f"  Error: {err}")
            if len(errors) > 5:
                print(f"  ... and {len(errors)-5} more errors.")

if __name__ == "__main__":
    run_import()
