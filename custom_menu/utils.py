import frappe

def redirect_post_login(login_manager):
    # Redirect user to /dashboard after successful login
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/dashboard"
