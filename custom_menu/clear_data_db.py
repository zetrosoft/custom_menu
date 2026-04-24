import frappe

def run():
    doctypes = ["Address", "Contact", "Dynamic Link", "Contact Phone", "Contact Email"]
    for dt in doctypes:
        try:
            print(f"Mengosongkan {dt}...")
            frappe.db.delete(dt)
        except Exception as e:
            print(f"Gagal menghapus {dt}: {e}")
    
    frappe.db.commit()
    print("Database sudah bersih dari Address dan Contact.")

if __name__ == "__main__":
    frappe.connect(site="siumang")
    run()
