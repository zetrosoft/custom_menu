frappe.ready(function() {
    // Redirect user from desk home (workspaces) to our custom dashboard
    const current_page = frappe.get_route_str();
    const is_desk_home = current_page === "" || current_page === "workspaces";
    const is_under_app_path = window.location.pathname.startsWith('/app');

    // Only redirect if it's the main workspace home and the user is logged in
    if (is_under_app_path && is_desk_home && frappe.session.user !== "Guest") {
        window.location.href = "/";
    }
});
