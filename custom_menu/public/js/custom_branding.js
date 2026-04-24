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

                    // Perbaikan Navbar untuk Frappe v15
                    if (settings.navbar_color) {
                        custom_style += `
                            .navbar, .header-navbar, .navbar-light { 
                                background-color: ${settings.navbar_color} !important; 
                                background: ${settings.navbar_color} !important; 
                                border-bottom: 1px solid rgba(0,0,0,0.05) !important;
                            }
                            .navbar .nav-link, .navbar .navbar-brand, .navbar .app-logo-text { color: #ffffff !important; }
                            .navbar .search-bar input { background-color: rgba(255,255,255,0.15) !important; color: #ffffff !important; border: none !important; }
                            .navbar .search-bar .search-icon { color: #ffffff !important; opacity: 0.8; }
                        `;
                    }
                    
                    // Mencegah Overlap di Frappe v15 Sidebar & Content
                    custom_style += `
                        .standard-sidebar { z-index: 10 !important; }
                        .page-container { transition: margin-left 0.2s ease !important; }
                        
                        /* Fix overlap issue for Title */
                        @media (min-width: 992px) {
                            .body-sidebar .page-head { 
                                margin-left: var(--sidebar-width, 240px);
                                width: calc(100% - var(--sidebar-width, 240px));
                            }
                        }
                    `;

                    if (parseInt(settings.hide_help_menu)) {
                        custom_style += `
                            .dropdown-help, .vertical-bar, [data-label="Help"], .help-menu-link { display: none !important; }
                        `;
                    }

                    if (parseInt(settings.hide_setup_menu)) {
                        custom_style += `
                            [data-label="Settings"], a[href="/app/settings"], .dropdown-item[href="/app/settings"] { display: none !important; }
                        `;
                    }

                    if (settings.app_icon) {
                        $('link[rel*="icon"]').attr('href', settings.app_icon);
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

                    // Logo & Brand Text handling
                    if (settings.use_image_as_brand && settings.brand_image) {
                        $('.navbar-brand img, .app-logo img').attr('src', settings.brand_image)
                            .css({
                                'max-height': '28px',
                                'width': 'auto',
                                'display': 'inline-block'
                            });
                        $('.app-logo-text').hide();
                    } else if (settings.brand_text) {
                        $('.navbar-brand, .app-logo-text').text(settings.brand_text)
                            .css({
                                'color': '#fff',
                                'font-weight': 'bold',
                                'font-size': '16px'
                            }).show();
                        $('.app-logo img').hide();
                    }
                }
            }
        });
    }

    $(document).ready(function() {
        // Delay sedikit agar Frappe init selesai
        setTimeout(apply_custom_branding, 300); 
        
        // Logout override
        $(document).on('click', '.dropdown-item:contains("Logout")', function(e) {
            e.preventDefault();
            window.location.href = '/api/method/logout';
        });
    });

    // Re-apply on page change for Single Page App (SPA) feel
    $(document).on('page-change', function() {
        setTimeout(apply_custom_branding, 100);
    });
})();
