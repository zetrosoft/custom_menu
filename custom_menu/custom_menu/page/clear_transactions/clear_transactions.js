frappe.pages['clear-transactions'].on_page_load = function(wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Data Management Tool'),
		single_column: true
	});

	let page = wrapper.page;
	page.current_tab = 'transaction';

	page.main.html(`
		<div class="p-4" id="clear-transactions-container">
			<div class="mb-4 btn-group" role="group">
				<button type="button" class="btn btn-default active-tab-btn tab-nav-btn" data-target="transaction-pane">
					<i class="fa fa-exchange"></i> ${__('Transactions')}
				</button>
				<button type="button" class="btn btn-default tab-nav-btn" data-target="master-pane">
					<i class="fa fa-database"></i> ${__('Master Data')}
				</button>
				<button type="button" class="btn btn-default tab-nav-btn" data-target="migration-pane">
					<i class="fa fa-download"></i> ${__('JSON Migration')}
				</button>
			</div>

			<div class="alert alert-warning mb-4" id="tool-warning">
				<h4 class="alert-heading"><i class="fa fa-warning"></i> Warning</h4>
				<p>This tool will permanently delete or modify data. Use carefully.</p>
			</div>

			<div class="tab-content-container">
				<div class="tab-pane-custom" id="transaction-pane">
					<div id="transaction-stats-list"></div>
				</div>
				<div class="tab-pane-custom" id="master-pane" style="display: none;">
					<div id="master-stats-list"></div>
				</div>
				<div class="tab-pane-custom" id="migration-pane" style="display: none;">
					<div class="row">
						<div class="col-sm-12">
							<div class="card p-4 border" style="background: #fdfdfd; border-radius: 8px;">
								<div class="d-flex justify-content-between align-items-center mb-3">
									<div>
										<h4 class="m-0"><i class="fa fa-file-code-o"></i> ${__('Import Master Data from JSON')}</h4>
										<p class="text-muted small mt-1">${__('Urutan impor sudah diatur otomatis untuk mencegah kegagalan relasi data.')}</p>
									</div>
									<div class="text-right">
										<button class="btn btn-primary btn-lg btn-start-migration shadow-sm">
											<i class="fa fa-play"></i> ${__('Start Selected Migration')}
										</button>
									</div>
								</div>
								
								<div id="migration-file-list" class="mt-4"></div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-4 pt-3 border-top text-right" id="footer-actions">
				<button class="btn btn-danger btn-lg btn-clear-selected">
					<i class="fa fa-trash"></i> Clear Selected Data
				</button>
			</div>
		</div>

		<style>
			.active-tab-btn { background-color: var(--primary-color) !important; color: white !important; }
			.tab-pane-custom { animation: fadein 0.3s; }
			@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }
			.progress-status { font-weight: bold; margin-bottom: 5px; display: block; }
			.progress { height: 20px; margin-bottom: 10px; background-color: #f5f5f5; border-radius: 4px; box-shadow: inset 0 1px 2px rgba(0,0,0,.1); }
			.progress-bar { float: left; width: 0; height: 100%; font-size: 12px; line-height: 20px; color: #fff; text-align: center; background-color: var(--primary-color); transition: width .3s ease; }
			.bg-info { background-color: #17a2b8 !important; }
		</style>
	`);

	// Tab switching
	$(wrapper).find('.tab-nav-btn').on('click', function() {
		let target = $(this).data('target');
		$(wrapper).find('.tab-nav-btn').removeClass('active-tab-btn btn-primary').addClass('btn-default');
		$(this).removeClass('btn-default').addClass('active-tab-btn');
		$(wrapper).find('.tab-pane-custom').hide();
		$(wrapper).find(`#${target}`).show();
		
		page.current_tab = target.replace('-pane', '');
		
		if (page.current_tab === 'migration') {
			$(wrapper).find('#footer-actions').hide();
			$(wrapper).find('#tool-warning').hide();
			page.load_migration_files();
		} else {
			$(wrapper).find('#footer-actions').show();
			$(wrapper).find('#tool-warning').show();
		}
	});

	// Render Table
	page.render_table = function(target_id, data) {
		let $target = $(`#${target_id}`);
		$target.empty();

		if (!data || data.length === 0) {
			$target.append(`<p class="text-center p-5 text-muted">${__('No data found.')}</p>`);
			return;
		}

		let is_master = target_id.includes('master');
		let html = `
			<table class="table table-bordered table-hover mt-3">
				<thead class="bg-light">
					<tr>
						<th width="5%" class="text-center"><input type="checkbox" class="select-all-cb"></th>
						<th width="35%">${__('DocType')}</th>
						<th width="15%" class="text-right">${__('Count')}</th>
						<th width="45%" class="text-center">${__('Actions')}</th>
					</tr>
				</thead>
				<tbody id="${target_id}-tbody"></tbody>
			</table>
		`;
		$target.append(html);

		data.forEach(row => {
			let has_data = row.count > 0;
			let cb_cell = (has_data) ? `<input type="checkbox" class="doctype-checkbox" data-doctype="${row.doctype}">` : '';
			let action_html = '';
			if (has_data) action_html += `<button class="btn btn-default btn-xs btn-preview mr-1" data-doctype="${row.doctype}" title="Preview"><i class="fa fa-eye"></i></button>`;
			if (is_master) {
				action_html += `<button class="btn btn-success btn-xs btn-upload mr-1" data-doctype="${row.doctype}" title="Standard Upload"><i class="fa fa-upload"></i> ${__('Upload')}</button>`;
				action_html += `<button class="btn btn-primary btn-xs btn-smart-upload mr-1" data-doctype="${row.doctype}" title="AI Smart Upload"><i class="fa fa-magic"></i> ${__('AI Smart')}</button>`;
			}
			if (has_data) action_html += `<button class="btn btn-danger btn-xs btn-clear-single" data-doctype="${row.doctype}" title="Clear Data"><i class="fa fa-trash"></i></button>`;

			let $tr = $(`
				<tr>
					<td class="text-center">${cb_cell}</td>
					<td><strong>${__(row.doctype)}</strong></td>
					<td class="text-right">${row.count}</td>
					<td class="text-center">${action_html}</td>
				</tr>
			`);
			
			$tr.find('.btn-preview').on('click', () => page.show_preview(row.doctype));
			$tr.find('.btn-upload').on('click', () => page.show_upload_dialog(row.doctype));
			$tr.find('.btn-smart-upload').on('click', () => page.show_smart_upload_dialog(row.doctype));
			$tr.find('.btn-clear-single').on('click', () => {
				frappe.confirm(__('Clear all {0} records?', [row.doctype]), () => page.clear_selected([row.doctype]));
			});

			$target.find('tbody').append($tr);
		});

		$target.find('.select-all-cb').on('change', function() {
			$target.find('.doctype-checkbox').prop('checked', $(this).prop('checked'));
		});
	};

	// Refresh
	page.refresh = function() {
		frappe.dom.freeze(__('Loading...'));
		frappe.call({
			method: 'custom_menu.api.get_doctype_stats',
			args: { type_filter: 'transaction' },
			callback: (r) => page.render_table('transaction-stats-list', r.message)
		});
		frappe.call({
			method: 'custom_menu.api.get_doctype_stats',
			args: { type_filter: 'master' },
			callback: (r) => {
				page.render_table('master-stats-list', r.message);
				frappe.dom.unfreeze();
			}
		});
	};

	// Clear Selected
	page.clear_selected = function(doctypes) {
		if (!doctypes || doctypes.length === 0) return;
		page.stop_requested = false;

		let dialog = new frappe.ui.Dialog({
			title: __('Clearing Data'),
			fields: [
				{
					fieldname: 'progress_html',
					fieldtype: 'HTML',
					options: `
						<div id="clear-progress-wrapper">
							<span class="progress-status" id="progress-text">${__('DocType Progress')} (0/${doctypes.length}):</span>
							<div class="progress mb-3">
								<div class="progress-bar" id="progress-bar" role="progressbar" style="width: 0%;">0%</div>
							</div>
							
							<span class="progress-status small" id="clear-record-progress-text">${__('Record Progress')}:</span>
							<div class="progress mb-4" style="height: 12px;">
								<div class="progress-bar bg-danger" id="clear-record-progress-bar" role="progressbar" style="width: 0%;">0%</div>
							</div>

							<div id="progress-details" style="max-height: 150px; overflow-y: auto; font-size: 11px; color: #666; background: #f9f9f9; padding: 10px; border-radius: 4px;"></div>
						</div>
					`
				}
			],
			primary_action_label: __('Stop Process'),
			primary_action: function() {
				page.stop_requested = true;
				dialog.get_primary_btn().prop('disabled', true).text(__('Stopping...'));
			},
			no_focus: true
		});

		// Real-time progress listener for clearing
		frappe.realtime.on('clear_record_progress', (data) => {
			let p = Math.round((data.current / data.total) * 100);
			dialog.$wrapper.find('#clear-record-progress-bar').css('width', p + '%').text(p + '%');
			dialog.$wrapper.find('#clear-record-progress-text').text(`${__('Deleting Records')} for ${__(data.doctype)}: ${data.current} / ${data.total}`);
		});

		dialog.show();
		dialog.get_close_btn().hide();

		let total = doctypes.length;
		let current = 0;
		let all_errors = [];

		let process_next = function() {
			if (page.stop_requested) {
				dialog.$wrapper.find('#progress-text').text(__('Process Stopped by User'));
				dialog.get_primary_btn().hide();
				dialog.get_close_btn().show();
				frappe.realtime.off('clear_record_progress');
				page.refresh();
				return;
			}

			if (current < total) {
				let doctype = doctypes[current];
				let percent = Math.round(((current) / total) * 100);
				
				dialog.$wrapper.find('#progress-text').text(`${__('DocType Progress')} (${current + 1}/${total}): ${__(doctype)}`);
				dialog.$wrapper.find('#progress-bar').css('width', percent + '%').text(percent + '%');
				
				// Reset record progress bar for new DocType
				dialog.$wrapper.find('#clear-record-progress-bar').css('width', '0%').text('0%');
				dialog.$wrapper.find('#clear-record-progress-text').text(`${__('Starting deletion of')} ${__(doctype)}...`);

				frappe.call({
					method: 'custom_menu.api.clear_selected_doctypes',
					args: { doctypes: [doctype] },
					callback: (r) => {
						if (r.message && r.message[doctype]) {
							let res = r.message[doctype];
							if (res.errors && res.errors.length > 0) {
								all_errors.push(`<strong>${doctype}:</strong><br>${res.errors.slice(0, 3).join('<br>')}`);
							}
							dialog.$wrapper.find('#progress-details').prepend(`<div><i class="fa fa-check text-success"></i> ${__(doctype)}: ${res.count} ${__('deleted')}</div>`);
						}
						current++;
						process_next();
					}
				});
			} else {
				dialog.$wrapper.find('#progress-bar').css('width', '100%').text('100%');
				dialog.$wrapper.find('#clear-record-progress-bar').css('width', '100%').text('100%').addClass('bg-success');
				dialog.$wrapper.find('#progress-text').text(__('Clearing Complete!'));
				dialog.$wrapper.find('#clear-record-progress-text').text(__('All selected records deleted.'));
				
				dialog.get_primary_btn().hide();
				dialog.get_close_btn().show();
				frappe.realtime.off('clear_record_progress');

				if (all_errors.length > 0) {
					frappe.msgprint({ title: __('Errors'), message: all_errors.join('<hr>'), indicator: 'orange' });
				}
				page.refresh();
			}
		};
		process_next();
	};

	page.load_migration_files = function() {
		let $list = $(wrapper).find('#migration-file-list');
		$list.html('<div class="text-center p-5"><div class="spinner-border text-primary" role="status"></div><p class="text-muted mt-2">Membaca file JSON...</p></div>');

		frappe.call({
			method: 'custom_menu.api.get_migration_file_list',
			callback: (r) => {
				$list.empty();
				if (!r.message || r.message.length === 0) {
					$list.append('<div class="alert alert-info">Tidak ada file JSON migrasi ditemukan di folder exports.</div>');
					return;
				}

				let html = `
					<div class="table-responsive">
						<table class="table table-hover border">
							<thead>
								<tr class="bg-light">
									<th width="40px" class="text-center">
										<input type="checkbox" class="select-all-migration" style="width: 18px; height: 18px; vertical-align: middle;">
									</th>
									<th>${__('Data Type')}</th>
									<th class="text-center">${__('Records')}</th>
									<th>${__('File Info')}</th>
								</tr>
							</thead>
							<tbody>
				`;
				r.message.forEach(file => {
					html += `
						<tr style="cursor: pointer;" onclick="$(this).find('input').click(); event.stopPropagation();">
							<td class="text-center" onclick="event.stopPropagation();">
								<input type="checkbox" class="migration-item-cb" data-doctype="${file.doctype}" style="width: 18px; height: 18px;">
							</td>
							<td>
								<div class="font-weight-bold" style="font-size: 1.1em;">${__(file.doctype)}</div>
								<div class="text-muted small">${file.description}</div>
							</td>
							<td class="text-center">
								<span class="indicator blue" style="font-size: 0.9em; padding: 2px 10px;">
									${file.count.toLocaleString()} ${__('records')}
								</span>
							</td>
							<td>
								<div class="small text-muted"><i class="fa fa-file-o"></i> ${file.filename}</div>
								<div class="small text-muted"><i class="fa fa-hdd-o"></i> ${file.size}</div>
							</td>
						</tr>
					`;
				});
				html += '</tbody></table></div>';
				$list.append(html);

				$list.find('.select-all-migration').on('change', function() {
					$list.find('.migration-item-cb').prop('checked', $(this).prop('checked'));
				});
			}
		});
	};

	$(wrapper).find('.btn-start-migration').on('click', () => {
		let selected = [];
		$(wrapper).find('.migration-item-cb:checked').each(function() {
			selected.push($(this).data('doctype'));
		});

		if (selected.length === 0) {
			frappe.msgprint(__('Please select at least one item to import.'));
			return;
		}

		frappe.confirm(__('Start sequential migration for selected {0} DocTypes?', [selected.length]), () => {
			page.run_sequential_migration(selected);
		});
	});

	page.run_sequential_migration = function(doctypes) {
		page.stop_requested = false;
		const dependency_order = ["Account", "Customer Group", "Supplier Group", "Payment Terms Template", "Customer", "Supplier", "Address", "Contact"];
		let sorted_selected = dependency_order.filter(dt => doctypes.includes(dt));

		let dialog = new frappe.ui.Dialog({
			title: __('Importing Master Data'),
			fields: [
				{
					fieldname: 'progress_html',
					fieldtype: 'HTML',
					options: `
						<div id="migration-progress-wrapper">
							<span class="progress-status" id="migration-progress-text">${__('DocType Progress')} (0/${sorted_selected.length}):</span>
							<div class="progress mb-3">
								<div class="progress-bar" id="migration-progress-bar" role="progressbar" style="width: 0%;">0%</div>
							</div>
							
							<span class="progress-status small" id="record-progress-text">${__('Record Progress')}:</span>
							<div class="progress mb-4" style="height: 12px;">
								<div class="progress-bar bg-info" id="record-progress-bar" role="progressbar" style="width: 0%;">0%</div>
							</div>
							
							<div id="migration-progress-details" style="max-height: 180px; overflow-y: auto; font-size: 11px; color: #666; background: #f9f9f9; padding: 10px; border-radius: 4px;"></div>
						</div>
					`
				}
			],
			primary_action_label: __('Stop Process'),
			primary_action: function() {
				page.stop_requested = true;
				dialog.get_primary_btn().prop('disabled', true).text(__('Stopping...'));
			},
			no_focus: true
		});

		// Real-time progress listener
		frappe.realtime.on('migration_record_progress', (data) => {
			let p = Math.round((data.current / data.total) * 100);
			dialog.$wrapper.find('#record-progress-bar').css('width', p + '%').text(p + '%');
			dialog.$wrapper.find('#record-progress-text').text(`${__('Importing Records')} for ${__(data.doctype)}: ${data.current} / ${data.total}`);
		});

		dialog.show();
		dialog.get_close_btn().hide();

		let total = sorted_selected.length;
		let current = 0;
		let all_errors = [];

		let process_next = function() {
			if (page.stop_requested) {
				dialog.$wrapper.find('#migration-progress-text').text(__('Migration Stopped by User'));
				dialog.get_primary_btn().hide();
				dialog.get_close_btn().show();
				frappe.realtime.off('migration_record_progress');
				page.refresh();
				return;
			}

			if (current < total) {
				let doctype = sorted_selected[current];
				let percent = Math.round(((current) / total) * 100);
				
				dialog.$wrapper.find('#migration-progress-text').text(`${__('DocType Progress')} (${current + 1}/${total}): ${__(doctype)}`);
				dialog.$wrapper.find('#migration-progress-bar').css('width', percent + '%').text(percent + '%');
				
				dialog.$wrapper.find('#record-progress-bar').css('width', '0%').text('0%');
				dialog.$wrapper.find('#record-progress-text').text(`${__('Starting')} ${__(doctype)}...`);

				frappe.call({
					method: 'custom_menu.api.import_single_doctype',
					args: { doctype: doctype },
					callback: (r) => {
						if (r.message) {
							let res = r.message;
							dialog.$wrapper.find('#migration-progress-details').prepend(`
								<div class="mb-1 border-bottom pb-1">
									<b>${__(doctype)}:</b> <span class="text-success">${res.success} imported</span>, 
									<span class="text-muted">${res.skipped} skipped</span>
									${res.errors.length ? `<br><span class="text-danger small">${res.errors.length} errors</span>` : ''}
								</div>
							`);
							if (res.errors.length) {
								all_errors.push(`<strong>${doctype}:</strong><br>${res.errors.slice(0, 3).join('<br>')}`);
							}
						}
						current++;
						process_next();
					}
				});
			} else {
				dialog.$wrapper.find('#migration-progress-bar').css('width', '100%').text('100%').addClass('bg-success');
				dialog.$wrapper.find('#record-progress-bar').css('width', '100%').text('100%').addClass('bg-success');
				dialog.$wrapper.find('#migration-progress-text').text(__('Migration Complete!'));
				dialog.$wrapper.find('#record-progress-text').text(__('All records processed.'));
				
				dialog.get_primary_btn().hide();
				dialog.get_close_btn().show();
				frappe.realtime.off('migration_record_progress');

				if (all_errors.length > 0) {
					frappe.msgprint({ title: __('Migration Errors'), message: all_errors.join('<hr>'), indicator: 'orange' });
				}
				page.refresh();
			}
		};
		process_next();
	};

	page.show_upload_dialog = function(doctype) {
		let dialog = new frappe.ui.Dialog({
			title: __('Upload Excel: {0}', [doctype]),
			fields: [
				{ fieldname: 'file', label: __('Attach Excel/CSV'), fieldtype: 'Attach' },
				{ fieldname: 'help_html', fieldtype: 'HTML', options: `<div class="mt-2 small text-muted"><p>Header Excel harus sesuai dengan fieldname di DocType.</p></div>` }
			],
			primary_action_label: __('Upload'),
			primary_action: function(values) {
				if (!values.file) return;
				frappe.call({
					method: 'custom_menu.api.upload_master_data',
					args: { doctype: doctype, file_url: values.file },
					callback: (r) => {
						if (r.message.status === 'success' || r.message.status === 'partial') {
							frappe.show_alert({ message: __('Imported {0} records.', [r.message.imported]), indicator: 'green' });
							dialog.hide();
							page.refresh();
						}
					}
				});
			}
		});
		dialog.show();
	};

	page.show_smart_upload_dialog = function(doctype) {
		let dialog = new frappe.ui.Dialog({
			title: __('AI Smart Upload (Gemma/Gemini): {0}', [doctype]),
			fields: [
				{ fieldname: 'file', label: __('Attach Raw Excel/CSV'), fieldtype: 'Attach' },
				{ fieldname: 'analyze_btn', fieldtype: 'Button', label: __('Analyze Columns with AI'), click: function() {
					let values = dialog.get_values();
					if (!values.file) { frappe.msgprint(__('Please attach a file first.')); return; }
					
					frappe.dom.freeze(__('AI is analyzing columns...'));
					frappe.call({
						method: 'custom_menu.api.analyze_with_gemini', // Internal name remains for compat
						args: { doctype: doctype, file_url: values.file },
						callback: (r) => {
							frappe.dom.unfreeze();
							if (r.message && r.message.mapping) {
								dialog.set_df_property('mapping_html', 'options', page.render_mapping_table(r.message.mapping));
								dialog.ai_mapping = r.message;
								dialog.get_primary_btn().show();
							}
						}
					});
				}},
				{ fieldname: 'mapping_html', fieldtype: 'HTML', options: '' }
			],
			primary_action_label: __('Confirm & Start Import'),
			primary_action: function() {
				let values = dialog.get_values();
				frappe.dom.freeze(__('AI is processing data distribution...'));
				frappe.call({
					method: 'custom_menu.api.process_smart_import',
					args: { doctype: doctype, file_url: values.file, mapping: dialog.ai_mapping },
					callback: (r) => {
						frappe.dom.unfreeze();
						let res = r.message;
						let msg = `<b>Import Result:</b><br>- ${doctype}: ${res.parent}<br>- Address: ${res.address}<br>- Contact: ${res.contact}`;
						frappe.msgprint({ title: __('Smart Import Complete'), message: msg, indicator: res.errors.length ? 'orange' : 'green' });
						dialog.hide();
						page.refresh();
					}
				});
			}
		});
		dialog.get_primary_btn().hide();
		dialog.show();
	};

	page.render_mapping_table = function(mapping) {
		let html = `
			<div class="mt-4">
				<div class="alert alert-info small">AI telah mendeteksi kolom berikut. Pastikan target DocType dan Field sudah benar.</div>
				<table class="table table-bordered table-condensed small">
					<thead>
						<tr class="bg-light">
							<th>${__('File Column')}</th>
							<th>${__('Target DocType')}</th>
							<th>${__('Target Field')}</th>
						</tr>
					</thead>
					<tbody>
		`;
		mapping.forEach(m => {
			let badge_class = m.target_doctype === 'Address' ? 'label-warning' : (m.target_doctype === 'Contact' ? 'label-success' : 'label-info');
			html += `
				<tr>
					<td><b>${m.column}</b></td>
					<td><span class="label ${badge_class}">${__(m.target_doctype)}</span></td>
					<td><code>${m.target_fieldname}</code></td>
				</tr>
			`;
		});
		html += `</tbody></table></div>`;
		return html;
	};

	page.show_preview = function(doctype) {
		frappe.call({
			method: 'custom_menu.api.get_preview_data',
			args: { doctype: doctype },
			callback: (r) => {
				if (!r.message || r.message.length === 0) return frappe.msgprint(__('No data to show.'));
				let data = r.message;
				let keys = Object.keys(data[0]);
				let html = '<div class="table-responsive"><table class="table table-condensed table-bordered small"><thead><tr class="bg-light">';
				keys.forEach(k => { html += `<th>${__(k)}</th>`; });
				html += '</tr></thead><tbody>';
				data.forEach(row => {
					html += '<tr>';
					keys.forEach(k => { html += `<td>${row[k] || ''}</td>`; });
					html += '</tr>';
				});
				html += '</tbody></table></div>';
				new frappe.ui.Dialog({ title: __('Recent Records: {0}', [doctype]), fields: [{ fieldname: 'p', fieldtype: 'HTML', options: html }] }).show();
			}
		});
	};

	$(wrapper).find('.btn-clear-selected').on('click', () => {
		let selected = [];
		$(wrapper).find('.doctype-checkbox:checked').each(function() { selected.push($(this).data('doctype')); });
		if (selected.length === 0) return frappe.msgprint(__('Select at least one.'));
		frappe.confirm(__('Clear selected {0} DocTypes?', [selected.length]), () => page.clear_selected(selected));
	});

	page.refresh();
}
