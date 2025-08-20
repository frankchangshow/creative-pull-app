import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from datetime import datetime, timezone


def create_advanced_features_section(parent, app):
	"""Create collapsible advanced features section (migrated)."""
	advanced_frame = ttk.LabelFrame(parent, text="⚙️ Advanced Features")
	advanced_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	app.advanced_toggle_var = tk.BooleanVar(value=False)
	app.advanced_toggle_button = ttk.Checkbutton(
		advanced_frame,
		text="Show Advanced Features",
		variable=app.advanced_toggle_var,
		command=app.toggle_advanced_features,
	)
	app.advanced_toggle_button.pack(pady=5)

	app.advanced_features_container = ttk.Frame(advanced_frame)

	# Compose subsections using existing callbacks on app
	create_job_runner_section(app.advanced_features_container, app)
	create_unified_savanna_section(app.advanced_features_container, app)


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
	app.ad_network_frame.pack(anchor=tk.W, pady=(0, 10))

	ttk.Label(app.ad_network_frame, text="Ad Network ID:").pack(anchor=tk.W)
	app.unified_ad_network_id_var = tk.StringVar()
	app.unified_ad_network_id_entry = ttk.Entry(app.ad_network_frame, textvariable=app.unified_ad_network_id_var, width=25)
	app.unified_ad_network_id_entry.pack(anchor=tk.W, pady=(2, 5))

	ttk.Label(app.ad_network_frame, text="Or select from networks:").pack(anchor=tk.W)

	app.network_dropdown_var = tk.StringVar()
	app.network_dropdown = ttk.Combobox(app.ad_network_frame, textvariable=app.network_dropdown_var, width=25, state="normal")
	app.network_dropdown.pack(anchor=tk.W, pady=(2, 5))
	app.network_dropdown.bind('<KeyRelease>', app.on_network_search_change)
	app.network_dropdown.bind('<<ComboboxSelected>>', app.on_network_selected)

	app.network_status_label = ttk.Label(app.ad_network_frame, text="Type to search networks or enter ID manually", font=("Arial", 8), foreground="gray")
	app.network_status_label.pack(anchor=tk.W, pady=(0, 5))

	# Email for watchlist notifications (used in Save mode)
	app.email_frame = ttk.Frame(input_frame)
	app.email_frame.pack(anchor=tk.W, pady=(0, 10))
	ttk.Label(app.email_frame, text="Notification Email(s) (optional, comma-separated):").pack(anchor=tk.W)
	app.unified_email_var = tk.StringVar()
	app.unified_email_entry = ttk.Entry(app.email_frame, textvariable=app.unified_email_var, width=30)
	app.unified_email_entry.pack(anchor=tk.W, pady=(2, 0))

	button_frame = ttk.Frame(savanna_frame)
	button_frame.pack(fill=tk.X, padx=5, pady=5)

	app.unified_action_button = ttk.Button(button_frame, text="🔍 Search", command=app.unified_savanna_action, style="Accent.TButton")
	app.unified_action_button.pack(side=tk.LEFT, padx=(0, 5))

	app.clear_button = ttk.Button(button_frame, text="🗑️ Clear", command=app.clear_unified_fields)
	app.clear_button.pack(side=tk.LEFT, padx=2)

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


