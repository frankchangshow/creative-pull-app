import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from datetime import datetime, timezone


def create_advanced_features_section(parent, app, show_inline_toggle: bool = False):
	"""Create collapsible advanced features section (primarily Job Runner).

	If show_inline_toggle is True, render a local toggle; otherwise, assume the
	app created `advanced_toggle_var` in a header and will call `toggle_advanced_features`.
	"""
	advanced_frame = ttk.LabelFrame(parent, text="⚙️ Advanced Features")
	advanced_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	if show_inline_toggle:
		app.advanced_toggle_var = getattr(app, 'advanced_toggle_var', tk.BooleanVar(value=False))
		app.advanced_toggle_button = ttk.Checkbutton(
			advanced_frame,
			text="Advanced Features",
			variable=app.advanced_toggle_var,
			command=app.toggle_advanced_features,
		)
		app.advanced_toggle_button.pack(pady=5)

	app.advanced_features_container = ttk.Frame(advanced_frame)

	# Only keep Job Runner in Advanced; Save/Search live in the main left area
	create_job_runner_section(app.advanced_features_container, app)

	# Add a lightweight Savanna Queue Search panel for Advanced window
	create_savanna_search_section(app.advanced_features_container, app)


def create_job_runner_section(container, app):
	"""Create the job runner section with UTC timestamp window."""
	job_frame = ttk.LabelFrame(container, text="🚀 Pull from GCS Bucket")
	job_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	# Start/End Time (UTC): date + hour pickers
	ts_frame = ttk.Frame(job_frame)
	ts_frame.pack(fill=tk.X, padx=5, pady=5)

	# Defaults: today's date and current hour (UTC)
	_now = datetime.now(timezone.utc)
	_default_date = _now.strftime('%Y-%m-%d')
	_default_hour = _now.strftime('%H')

	# Hours list 00..23
	_hours = [f"{h:02d}" for h in range(24)]

	# Use grid to align fields cleanly
	ts_frame.grid_columnconfigure(1, weight=0)

	start_label = ttk.Label(ts_frame, text="Start Time (UTC):")
	start_label.grid(row=0, column=0, sticky='w', padx=(0, 8), pady=2)
	app.start_date_var = tk.StringVar(value=_default_date)
	app.start_date_entry = ttk.Entry(ts_frame, textvariable=app.start_date_var, width=12)
	app.start_date_entry.grid(row=0, column=1, sticky='w', padx=(0, 8), pady=2)
	app.start_hour_var = tk.StringVar(value=_default_hour)
	app.start_hour_combo = ttk.Combobox(ts_frame, textvariable=app.start_hour_var, values=_hours, width=4, state='readonly')
	app.start_hour_combo.grid(row=0, column=2, sticky='w', padx=(0, 0), pady=2)

	end_label = ttk.Label(ts_frame, text="End Time (UTC):")
	end_label.grid(row=1, column=0, sticky='w', padx=(0, 8), pady=2)
	app.end_date_var = tk.StringVar(value=_default_date)
	app.end_date_entry = ttk.Entry(ts_frame, textvariable=app.end_date_var, width=12)
	app.end_date_entry.grid(row=1, column=1, sticky='w', padx=(0, 8), pady=2)
	app.end_hour_var = tk.StringVar(value=_default_hour)
	app.end_hour_combo = ttk.Combobox(ts_frame, textvariable=app.end_hour_var, values=_hours, width=4, state='readonly')
	app.end_hour_combo.grid(row=1, column=2, sticky='w', padx=(0, 0), pady=2)

	# Quick fills
	quick_ts_frame = ttk.Frame(job_frame)
	quick_ts_frame.pack(fill=tk.X, padx=5, pady=2)
	ttk.Button(quick_ts_frame, text="Last 6 Hours", command=app.set_last_6_hours, width=12).pack(side=tk.LEFT, padx=2)
	ttk.Button(quick_ts_frame, text="Today", command=app.set_today_hours, width=8).pack(side=tk.LEFT, padx=2)
	ttk.Button(quick_ts_frame, text="Yesterday", command=app.set_yesterday_hours, width=10).pack(side=tk.LEFT, padx=2)

	button_frame = ttk.Frame(job_frame)
	button_frame.pack(fill=tk.X, padx=5, pady=5)

	app.run_job_button = ttk.Button(button_frame, text="▶️ Run Job", command=app.run_job, style="Accent.TButton")
	app.run_job_button.pack(side=tk.LEFT, padx=(0, 5))

	app.check_job_status_button = ttk.Button(button_frame, text="📊 Check Status", command=app.check_job_status)
	app.check_job_status_button.pack(side=tk.LEFT, padx=2)

	status_frame = ttk.Frame(job_frame)
	status_frame.pack(fill=tk.X, padx=5, pady=5)

	app.job_status_label = ttk.Label(status_frame, text="Ready to run job", font=("Arial", 10), wraplength=400, justify=tk.LEFT)
	app.job_status_label.pack(fill=tk.X, pady=(5, 0))


def create_unified_savanna_section(container, app):
	"""Create the unified Savanna Creative Manager section (migrated)."""
	savanna_frame = ttk.LabelFrame(container, text="🎯 Savanna Creative Manager")
	savanna_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	mode_frame = ttk.Frame(savanna_frame)
	mode_frame.pack(fill=tk.X, padx=5, pady=5)

	ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)
	app.savanna_mode_var = tk.StringVar(value="search")

	search_radio = ttk.Radiobutton(mode_frame, text="🔍 Search Mode", variable=app.savanna_mode_var, value="search", command=app.on_mode_change)
	search_radio.pack(side=tk.LEFT, padx=(10, 5))

	save_radio = ttk.Radiobutton(mode_frame, text="💾 Save Mode", variable=app.savanna_mode_var, value="save", command=app.on_mode_change)
	save_radio.pack(side=tk.LEFT, padx=5)

	input_frame = ttk.Frame(savanna_frame)
	input_frame.pack(fill=tk.X, padx=5, pady=5)

	ttk.Label(input_frame, text="Creative ID:").pack(anchor=tk.W)
	app.unified_creative_id_var = tk.StringVar()
	app.unified_creative_id_entry = ttk.Entry(input_frame, textvariable=app.unified_creative_id_var, width=25)
	app.unified_creative_id_entry.pack(anchor=tk.W, pady=(2, 10))

	app.ad_network_frame = ttk.Frame(input_frame)
	app.ad_network_frame.pack(anchor=tk.W, pady=(0, 10), fill=tk.X)

	# Inline row: label + entry + combobox (align with Creative ID)
	row_adnet = ttk.Frame(app.ad_network_frame)
	row_adnet.pack(fill=tk.X)
	ttk.Label(row_adnet, text="Demand Source ID:").pack(side=tk.LEFT)
	app.unified_ad_network_id_var = tk.StringVar()
	app.unified_ad_network_id_entry = ttk.Entry(row_adnet, textvariable=app.unified_ad_network_id_var, width=25)
	app.unified_ad_network_id_entry.pack(side=tk.LEFT, padx=(8, 8))

	app.network_dropdown_var = tk.StringVar()
	app.network_dropdown = ttk.Combobox(row_adnet, textvariable=app.network_dropdown_var, width=25, state="normal")
	app.network_dropdown.pack(side=tk.LEFT)
	# Default hint text for dropdown
	app.network_dropdown_var.set("ID search for Demand Source")
	app.network_dropdown.bind('<KeyRelease>', app.on_network_search_change)
	app.network_dropdown.bind('<<ComboboxSelected>>', app.on_network_selected)

	app.network_status_label = ttk.Label(app.ad_network_frame, text="Type to search networks or enter ID manually", font=("Arial", 8), foreground="gray")
	app.network_status_label.pack(anchor=tk.W, pady=(0, 5))

	# Email for watchlist notifications (used in Save mode)
	app.email_frame = ttk.Frame(input_frame)
	app.email_frame.pack(anchor=tk.W, pady=(0, 10))
	ttk.Label(app.email_frame, text="Notifications Email(s) (optional, comma-separated):").pack(anchor=tk.W)
	app.unified_email_var = tk.StringVar()
	app.unified_email_entry = ttk.Entry(app.email_frame, textvariable=app.unified_email_var, width=30)
	app.unified_email_entry.pack(anchor=tk.W, pady=(2, 0))

	button_frame = ttk.Frame(savanna_frame)
	button_frame.pack(fill=tk.X, padx=5, pady=5)

	app.unified_action_button = ttk.Button(button_frame, text="🔍 Search", command=app.unified_savanna_action, style="Accent.TButton")
	app.unified_action_button.pack(side=tk.LEFT, padx=(0, 5))

	# Right-aligned utility controls on same row
	_util = ttk.Frame(button_frame)
	_util.pack(side=tk.RIGHT)
	app.advanced_toggle_var = getattr(app, 'advanced_toggle_var', tk.BooleanVar(value=False))
	app.advanced_toggle_button = ttk.Checkbutton(_util, text="Advanced Features", variable=app.advanced_toggle_var, command=app.toggle_advanced_features)
	app.advanced_toggle_button.pack(side=tk.RIGHT, padx=(8, 0))
	app.settings_button = ttk.Button(_util, text="⚙️ Token Settings", command=app.show_settings)
	app.settings_button.pack(side=tk.RIGHT)

	info_frame = ttk.Frame(savanna_frame)
	info_frame.pack(fill=tk.X, padx=5, pady=5)

	app.info_label = ttk.Label(info_frame, text="🔍 Search Mode: Check if a creative exists in the pulling queue", font=("Arial", 9), foreground="gray")
	app.info_label.pack(anchor=tk.W)

	results_frame = ttk.Frame(savanna_frame)
	results_frame.pack(fill=tk.X, padx=5, pady=5)

	app.unified_results = scrolledtext.ScrolledText(results_frame, height=6, font=("Arial", 11))
	app.unified_results.pack(fill=tk.BOTH, expand=True)
	app.unified_results.insert(tk.END, "🎯 Select a mode and enter Creative ID to get started...")
	app.unified_results.config(state=tk.DISABLED)

	app.networks_loaded = False
	app.on_mode_change()


def create_save_mode_section(parent, app):
	"""Aligned Save Mode section (compact, grid-based)."""
	save_frame = ttk.LabelFrame(parent, text="💾 Save Creative to Savanna", style="Card.TLabelframe")
	save_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	grid = ttk.Frame(save_frame)
	grid.pack(fill=tk.X, padx=12, pady=10)
	grid.grid_columnconfigure(1, weight=1)
	grid.grid_columnconfigure(2, weight=1)

	# Creative ID
	ttk.Label(grid, text="Creative ID:", width=16, anchor='w').grid(row=0, column=0, sticky='w', pady=4)
	app.unified_creative_id_var = tk.StringVar()
	# Inline row: Entry + Token Settings (left-aligned), aligned to Demand Source row
	cid_row = ttk.Frame(grid)
	cid_row.grid(row=0, column=1, sticky='w', pady=4)
	app.unified_creative_id_entry = ttk.Entry(cid_row, textvariable=app.unified_creative_id_var, width=22)
	app.unified_creative_id_entry.pack(side=tk.LEFT)
	app.settings_button = ttk.Button(cid_row, text="⚙️ Token Settings", command=app.show_settings)
	app.settings_button.pack(side=tk.LEFT, padx=(8, 0))

	# Demand Source ID (aligned to Creative ID)
	ttk.Label(grid, text="Demand Source ID:", width=16, anchor='w').grid(row=1, column=0, sticky='w', pady=4)
	app.ad_network_frame = ttk.Frame(grid)
	app.ad_network_frame.grid(row=1, column=1, sticky='w', pady=4)
	app.unified_ad_network_id_var = tk.StringVar()
	# Inline row: entry + dropdown on same row, aligned with Creative ID entry
	_adnet_row = ttk.Frame(app.ad_network_frame)
	_adnet_row.pack(fill=tk.X)
	app.unified_ad_network_id_entry = ttk.Entry(_adnet_row, textvariable=app.unified_ad_network_id_var, width=22)
	app.unified_ad_network_id_entry.pack(side=tk.LEFT)
	app.network_dropdown_var = tk.StringVar()
	app.network_dropdown = ttk.Combobox(_adnet_row, textvariable=app.network_dropdown_var, width=22, state="normal")
	app.network_dropdown.pack(side=tk.LEFT, padx=(8, 0))
	app.network_dropdown.bind('<KeyRelease>', app.on_network_search_change)
	app.network_dropdown.bind('<<ComboboxSelected>>', app.on_network_selected)
	app.network_status_label = ttk.Label(app.ad_network_frame, text="Type to search networks or enter ID manually", font=("Arial", 9), foreground="#6B7280")
	app.network_status_label.pack(anchor='w', pady=(2, 0))

	# More options (emails) – compact
	ttk.Label(grid, text="Notification Email(s):", width=16, anchor='w').grid(row=2, column=0, sticky='w', pady=4)
	app.email_frame = ttk.Frame(grid)
	app.email_frame.grid(row=2, column=1, sticky='w', pady=4)
	app.unified_email_var = tk.StringVar()
	# Match right edge of Demand Source dropdown (entry 22 + spacer ~1 + dropdown 22 ≈ 45-46 chars)
	app.unified_email_entry = ttk.Entry(app.email_frame, textvariable=app.unified_email_var, width=46)
	app.unified_email_entry.pack(anchor='w')

	# Actions
	btns = ttk.Frame(save_frame)
	btns.pack(fill=tk.X, padx=12, pady=(6, 4))
	app.unified_action_button = ttk.Button(btns, text="🚀 Submit", command=app.unified_savanna_action, style="Accent.TButton")
	app.unified_action_button.pack(side=tk.LEFT)
	# Inline status next to Submit (e.g., Unauthorized messages)
	app.unified_status_label = ttk.Label(btns, text="", foreground="red", font=("Arial", 8))
	app.unified_status_label.pack(side=tk.LEFT, padx=(10, 0))
	# Right-aligned utility controls: Advanced toggle only
	_util = ttk.Frame(btns)
	_util.pack(side=tk.RIGHT)
	app.advanced_toggle_var = getattr(app, 'advanced_toggle_var', tk.BooleanVar(value=False))
	app.advanced_toggle_button = ttk.Checkbutton(_util, text="Advanced Features", variable=app.advanced_toggle_var, command=app.toggle_advanced_features)
	app.advanced_toggle_button.pack(side=tk.RIGHT, padx=(8, 0))

	# Results (smaller by default)
	results_frame = ttk.Frame(save_frame, style="Card.TLabelframe")
	results_frame.pack(fill=tk.X, padx=12, pady=(4, 2))
	# Provide an info label similar to the original for on_mode_change()
	app.info_label = ttk.Label(results_frame, text="💾 Save Mode: Add a new creative to the pulling queue (optional email notification)", font=("Arial", 9), foreground="#6B7280")
	app.info_label.pack(anchor='w', padx=6, pady=(6, 2))
	app.unified_results = scrolledtext.ScrolledText(results_frame, height=5, font=("Arial", 11))
	app.unified_results.pack(fill=tk.BOTH, expand=True)
	instructions = (
		"Instructions:\n"
		"* Enter Creative ID,  Demand Source ID, then click Submit.\n"
		"* Demand Source ID can auto-fill by typing the DSP name in the dropdown.\n"
		"* You can enter multiple emails, separated by commas (no spaces)."
	)
	app.unified_results.insert(tk.END, instructions)
	app.unified_results.config(state=tk.DISABLED)

	# Ensure handler defaults to save mode
	app.savanna_mode_var = tk.StringVar(value="save")
	app.networks_loaded = False
	app.on_mode_change()


def create_savanna_search_section(container, app):
	"""Lightweight Savanna queue search (Advanced window only).

	Uses independent widgets and writes results locally to avoid interfering with
	main Save/Search widgets on the left.
	"""
	frame = ttk.LabelFrame(container, text="🔍 Savanna Queue Search")
	frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	row = ttk.Frame(frame)
	row.pack(fill=tk.X, padx=5, pady=5)
	cre_var = tk.StringVar()
	ttk.Label(row, text="Creative ID:").pack(side=tk.LEFT)
	entry = ttk.Entry(row, textvariable=cre_var, width=28)
	entry.pack(side=tk.LEFT, padx=(6, 8))

	btn_frame = ttk.Frame(frame)
	btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

	results = scrolledtext.ScrolledText(frame, height=5, font=("Arial", 11))
	results.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
	results.insert(tk.END, "Enter Creative ID and click Search…")
	results.config(state=tk.DISABLED)

	def set_results(text: str):
		results.config(state=tk.NORMAL)
		results.delete(1.0, tk.END)
		results.insert(tk.END, text)
		results.config(state=tk.DISABLED)

	def run_search():
		cid = cre_var.get().strip()
		if not cid:
			return set_results("Please enter a Creative ID")
		set_results(f"🔍 Searching for Creative ID: {cid}…")
		import threading as _th
		def _worker():
			try:
				from clients.databricks_client import DatabricksClient as _DBC
				from services.savanna_actions import search_creative_in_queue as _search
				client = _DBC()
				# Use app constants and token
				_mod = __import__('creative_previewer_app_webview')
				host = getattr(app, 'DATABRICKS_SERVER_HOSTNAME', getattr(_mod, 'DATABRICKS_SERVER_HOSTNAME'))
				http_path = getattr(app, 'DATABRICKS_HTTP_PATH', getattr(_mod, 'DATABRICKS_HTTP_PATH'))
				table = getattr(app, 'CREATIVE_PULLING_TABLE', getattr(_mod, 'CREATIVE_PULLING_TABLE'))
				results_rows = _search(
					client,
					host,
					http_path,
					app.access_token,
					table,
					cid,
				)
				if results_rows:
					text = f"✅ FOUND: Creative ID '{cid}' is in the pulling queue\n\n"
					from datetime import datetime as _dt
					for i, row in enumerate(results_rows, 1):
						cid2, creation_date, expire_date, active = row
						creation_str = creation_date.strftime('%Y-%m-%d %H:%M:%S') if creation_date else 'N/A'
						expire_str = expire_date.strftime('%Y-%m-%d %H:%M:%S') if expire_date else 'N/A'
						text += f"📋 Record {i}:\n   🕒 Created Time: {creation_str}\n   ⏰ Expire Time: {expire_str}\n"
						if expire_date:
							if expire_date.tzinfo is not None:
								expire_date = expire_date.replace(tzinfo=None)
							current_time = _dt.now().replace(tzinfo=None)
							if expire_date < current_time:
								text += "   ⚠️  Status: EXPIRED\n"
							elif active:
								text += "   ✅ Status: ACTIVE\n"
							else:
								text += "   ❌ Status: INACTIVE\n"
						elif active:
							text += "   ✅ Status: ACTIVE\n"
						else:
							text += "   ❌ Status: INACTIVE\n"
				else:
					text = f"❌ NOT FOUND: Creative ID '{cid}' is not in the pulling queue\n\nThis creative ID has not been added to the pulling queue yet."
			except Exception as e:
				text = f"❌ Error searching for Creative ID: {e}"
			finally:
				frame.after(0, lambda: set_results(text))
		_th.Thread(target=_worker, daemon=True).start()

	search_btn = ttk.Button(btn_frame, text="🔍 Search", command=run_search)
	search_btn.pack(side=tk.LEFT, padx=(0, 5))
	clear_btn = ttk.Button(btn_frame, text="🗑️ Clear", command=lambda: set_results("Enter Creative ID and click Search…"))
	clear_btn.pack(side=tk.LEFT)

