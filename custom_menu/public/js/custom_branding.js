(function() {
    function apply_custom_branding() {
        if (typeof frappe === 'undefined' || !frappe.call) return;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Custom Brand Settings",
                filters: {},
                fieldname: ["navbar_color", "brand_text", "use_image_as_brand", "brand_image", "app_icon", "hide_help_menu", "hide_setup_menu"]
            },
            callback: function(r) {
                if (r.message) {
                    const settings = r.message;
                    let custom_style = "";

                    if (settings.navbar_color) {
                        custom_style += `
                            .navbar, .header-navbar, .navbar-light { background-color: ${settings.navbar_color} !important; background: ${settings.navbar_color} !important; }
                            .navbar .nav-link, .navbar .navbar-brand, .navbar .app-logo-text { color: #ffffff !important; }
                            .navbar .search-bar input { background-color: rgba(255,255,255,0.2) !important; color: #ffffff !important; }`;
                    }
                    
                    if (parseInt(settings.hide_help_menu)) {
                        custom_style += `
                            .dropdown-help, .vertical-bar { display: none !important; }
                            [data-label="Help"], .help-menu-link { display: none !important; }
                        `;
                    }

                    if (parseInt(settings.hide_setup_menu)) {
                        custom_style += `
                            [data-label="Settings"], a[href="/app/settings"], .dropdown-item[href="/app/settings"] { display: none !important; }
                        `;
                    }

                    if (settings.app_icon) {
                        $('link[rel*="icon"]').attr('href', settings.app_icon);
                        // CSS minimal untuk splash agar tidak merusak yang lain
                        custom_style += `
                            #splash-screen .frappe-logo { 
                                content: url("${settings.app_icon}") !important;
                                max-height: 80px !important;
                                width: auto !important;
                                margin: 0 auto !important;
                            }
                        `;
                    }

                    $('#custom-branding-css').remove();
                    $('<style id="custom-branding-css">').prop("type", "text/css").html(custom_style).appendTo("head");

                    if (settings.use_image_as_brand && settings.brand_image) {
                        $('.navbar-brand img, .app-logo img').attr('src', settings.brand_image).css('max-height', '30px').show();
                        $('.app-logo-text').hide();
                    } else if (settings.brand_text) {
                        $('.navbar-brand, .app-logo-text').text(settings.brand_text).css('color', '#fff').show();
                        $('.app-logo img').hide();
                    }
                }
            }
        });
    }

    $(document).ready(function() {
        setTimeout(apply_custom_branding, 100); 
        
        // Override standard logout behavior
        $(document).on('click', '.dropdown-item:contains("Logout")', function(e) {
            e.preventDefault();
            window.location.href = '/api/method/logout';
        });
    });

    $(document).on('page-change', apply_custom_branding);
})();
