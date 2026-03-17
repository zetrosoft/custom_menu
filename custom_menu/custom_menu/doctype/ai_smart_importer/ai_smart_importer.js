frappe.ui.form.on('AI Smart Importer', {
	onload: function(frm) {
		// Listener for Analysis Progress (Background Job)
		frappe.realtime.on('ai_analysis_progress', (data) => {
			if (data.progress && data.total) {
				let percent = (data.progress / data.total) * 100;
				frappe.show_progress(__('AI Analyzing Data'), percent, 100, data.msg);
				
				frm.doc.current_progress = data.progress;
				frm.doc.total_records = data.total;
			} else if (data.msg) {
				// Update message even if no progress numbers (e.g., status messages)
				if ($('.frappe-progress-dialog').is(':visible')) {
					$('.frappe-progress-dialog .progress-message').text(__(data.msg));
				}
			}
			
			if (data.status === 'Stopped' || data.status === 'Failed' || (data.progress && data.progress === data.total)) {
				setTimeout(() => {
					frappe.hide_progress();
					frm.reload_doc();
				}, 1500);
			}
		});

		// Listener for Import Progress
		frappe.realtime.on('ai_import_progress', (data) => {
			if (data.progress && data.total) {
				let percent = (data.progress / data.total) * 100;
				frappe.show_progress(__('Smart Importing'), percent, 100, data.msg);
			}
			if (data.progress === data.total) {
				setTimeout(() => {
					frappe.hide_progress();
					frm.reload_doc();
				}, 1000);
			}
		});
	},

	refresh: function(frm) {
		if (frm.doc.mapping_json) {
			frm.trigger('render_mapping_preview');
			frm.trigger('render_data_preview');
		}
		
		// Resume / Analyze Button logic
		if (frm.doc.status !== 'Analyzing' && frm.doc.status !== 'Analyzed' && frm.doc.status !== 'Completed') {
			let label = (frm.doc.current_progress > 0) ? __('Resume AI Analysis') : __('Analyze with AI');
			let icon = (frm.doc.current_progress > 0) ? 'fa fa-play' : 'fa fa-magic';
			
			frm.add_custom_button(label, () => frm.trigger('analyze_btn'), icon).addClass('btn-primary');
		}

		// Monitor Button
		if (frm.doc.status === 'Analyzing') {
			frm.add_custom_button(__('Stop Analysis'), () => {
				frappe.confirm(__('Stop AI Analysis? You can resume later from row {0}.', [frm.doc.current_progress]), () => {
					frappe.call({
						method: 'custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.stop_analysis',
						args: { docname: frm.doc.name },
						callback: function() {
							frappe.show_alert({message: __('Stop signal sent to server'), indicator: 'orange'});
							frm.reload_doc();
						}
					});
				});
			}, 'fa fa-stop').addClass('btn-danger');

			frm.add_custom_button(__('Monitor Progress'), () => {
				// Ambil status terbaru dari server
				frappe.call({
					method: 'custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.get_analysis_status',
					args: { docname: frm.doc.name },
					callback: function(r) {
						if (!r.message) {
							frappe.msgprint(__('No response from server status API.'));
							return;
						}
						
						let progress = parseInt(r.message.progress) || 0;
						let total = parseInt(r.message.total) || 0;
						let percent = total > 0 ? (progress / total) * 100 : 0;
						
						// Jika progress dialog sudah ada, perbarui pesannya
						if ($('.frappe-progress-dialog').is(':visible')) {
							$('.frappe-progress-dialog .progress-bar').css('width', percent + '%');
							$('.frappe-progress-dialog .progress-message').text(__('Row {0} of {1} Success', [progress, total]));
						} else {
							frappe.show_progress(__('AI Analyzing Data'), percent, 100, __('Row {0} of {1} Success', [progress, total]));
						}
						
						frappe.show_alert({message: __('Current Progress: {0}/{1}', [progress, total]), indicator: 'info'});
					}
				});
			}, 'fa fa-search');
		}

		if (frm.doc.status === 'Analyzed') {
			frm.add_custom_button(__('Execute Smart Import'), () => frm.trigger('execute_btn'), 'fa fa-upload').addClass('btn-primary');
		}
	},

	analyze_btn: function(frm) {
		if (!frm.doc.import_file || !frm.doc.target_doctype) {
			frappe.msgprint(__('Please select Target DocType and Attach a File first.'));
			return;
		}

		frappe.confirm(__('Start AI Analysis? This will run in the background and might take a while for large files.'), () => {
			frappe.show_progress(__('AI Analyzing Data'), 0, 100, __('Initializing background job...'));
			
			frappe.call({
				method: 'custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.start_background_analysis',
				args: { docname: frm.doc.name },
				callback: function(r) {
					if (r.message && r.message.status === 'Job Started') {
						frappe.show_alert({message: __('Background Analysis Started'), indicator: 'blue'});
					}
				}
			});
		});
	},

	execute_btn: function(frm) {
		frappe.confirm(__('Are you sure you want to execute this import?'), () => {
			frappe.call({
				method: 'custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.execute_import',
				args: { docname: frm.doc.name },
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({message: __('Import started in background'), indicator: 'green'});
					}
				}
			});
		});
	},

	render_mapping_preview: function(frm) {
		try {
			let data = JSON.parse(frm.doc.mapping_json);
			let mapping = data.mapping;
			if (!mapping) return;
			
			let html = `
				<div class="mapping-preview-container" style="margin-bottom: 20px;">
					<table class="table table-bordered table-condensed small bg-light">
						<thead>
							<tr><th>File Column</th><th>Target DocType</th><th>Field Name</th></tr>
						</thead>
						<tbody>
							${mapping.map(m => `
								<tr><td>${m.column}</td><td><span class="label label-info">${m.target_doctype}</span></td><td><code>${m.target_fieldname}</code></td></tr>
							`).join('')}
						</tbody>
					</table>
				</div>
			`;
			frm.set_df_property('mapping_preview', 'options', html);
		} catch(e) {}
	},

	render_data_preview: function(frm) {
		frappe.call({
			method: 'custom_menu.custom_menu.doctype.ai_smart_importer.ai_smart_importer.get_import_preview',
			args: { docname: frm.doc.name },
			callback: function(r) {
				if (!r.message || !r.message.length) return;
				let data = r.message;
				let target_dt = frm.doc.target_doctype;
				
				let html = `<div class="data-preview-container" style="margin-top: 20px; border-top: 1px solid #d1d8dd; pt-3">
					<div class="row" style="margin-bottom: 10px;">
						<div class="col-sm-8">
							<h6><i class="fa fa-eye"></i> ${__('Random Sample Preview (Verify Consistency)')}</h6>
						</div>
						<div class="col-sm-4 text-right">
							<button class="btn btn-xs btn-default btn-refresh-preview" onclick="cur_frm.trigger('render_data_preview')">
								<i class="fa fa-refresh"></i> ${__('Get Other Samples')}
							</button>
						</div>
					</div>
					<div class="table-responsive">
						<table class="table table-bordered table-condensed small" style="font-size: 10px; table-layout: fixed;">
							<thead class="bg-light">
								<tr>
									<th style="width: 34%">${target_dt}</th>
									<th style="width: 33%">Address</th>
									<th style="width: 33%">Contact</th>
								</tr>
							</thead>
							<tbody>
								${data.map(row => `
									<tr>
										<td class="text-muted"><pre style="background:none; border:none; padding:0; margin:0; white-space: pre-wrap;">${row[target_dt] ? JSON.stringify(row[target_dt], null, 2) : '{}'}</pre></td>
										<td class="text-muted"><pre style="background:none; border:none; padding:0; margin:0; white-space: pre-wrap;">${row['Address'] ? JSON.stringify(row['Address'], null, 2) : '{}'}</pre></td>
										<td class="text-muted"><pre style="background:none; border:none; padding:0; margin:0; white-space: pre-wrap;">${row['Contact'] ? JSON.stringify(row['Contact'], null, 2) : '{}'}</pre></td>
									</tr>
								`).join('')}
							</tbody>
						</table>
					</div>
					<p class="text-muted small"><i class="fa fa-info-circle"></i> ${__('Above are 5 random rows from the analysis results. If satisfied, click Execute Smart Import.')}</p>
				</div>`;
				
				// Clear previous preview if exists
				if ($('.data-preview-container').length) {
					$('.data-preview-container').remove();
				}
				
				let mapping_html = frm.fields_dict.mapping_preview.wrapper.innerHTML;
				frm.set_df_property('mapping_preview', 'options', mapping_html + html);
			}
		});
	}
});
