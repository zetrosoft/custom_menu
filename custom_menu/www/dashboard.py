import frappe

def get_context(context):
    context.no_cache = 1
    context.full_width = True
    
    # Redirect Guest to login
    if frappe.session.user == "Guest":
        frappe.redirect("/login")
        return

    user_doc = frappe.get_doc("User", frappe.session.user)
    context.full_name = user_doc.full_name
    
    # Get all modules
    all_modules = frappe.get_all("Module Def", fields=["name"])
    all_module_names = [m.name for m in all_modules]
    
    # Get blocked modules for this user
    blocked_modules = user_doc.get_blocked_modules()
    
    # Administrator's blocked modules also apply to everyone usually
    admin_blocked_modules = frappe.get_doc("User", "Administrator").get_blocked_modules()
    all_blocked = set(blocked_modules + admin_blocked_modules)
    
    # Final allowed modules
    context.allowed_modules = [m for m in all_module_names if m not in all_blocked]
    
    return context
