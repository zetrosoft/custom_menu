import frappe
from frappe.model.document import Document

class CustomBrandSettings(Document):
    def on_update(self):
        # Update Navbar Settings logo
        if self.app_icon or self.brand_image:
            target_image = self.app_icon or self.brand_image
            
            # Update Navbar Settings
            navbar_settings = frappe.get_doc("Navbar Settings")
            navbar_settings.app_logo = target_image
            navbar_settings.save(ignore_permissions=True)
            
            # Update Website Settings (untuk logo website dan favicon)
            website_settings = frappe.get_doc("Website Settings")
            website_settings.app_logo = target_image
            website_settings.favicon = target_image
            website_settings.brand_html = f'<img src="{target_image}" style="max-height: 30px;">'
            website_settings.save(ignore_permissions=True)
            
            frappe.clear_cache()
