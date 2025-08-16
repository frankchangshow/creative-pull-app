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
	"""Create the job runner section with date range selection (migrated)."""
	job_frame = ttk.LabelFrame(container, text="🚀 Job Runner")
	job_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

	date_frame = ttk.Frame(job_frame)
	date_frame.pack(fill=tk.X, padx=5, pady=5)

	start_date_frame = ttk.Frame(date_frame)
	start_date_frame.pack(fill=tk.X, pady=2)
	ttk.Label(start_date_frame, text="Start Date (GMT):").pack(side=tk.LEFT)

	current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
	app.start_date_var = tk.StringVar(value=current_date)
	app.start_date_entry = ttk.Entry(start_date_frame, textvariable=app.start_date_var, width=12)
	app.start_date_entry.pack(side=tk.RIGHT)

	end_date_frame = ttk.Frame(date_frame)
	end_date_frame.pack(fill=tk.X, pady=2)
	ttk.Label(end_date_frame, text="End Date (GMT):").pack(side=tk.LEFT)

	app.end_date_var = tk.StringVar(value=current_date)
	app.end_date_entry = ttk.Entry(end_date_frame, textvariable=app.end_date_var, width=12)
	app.end_date_entry.pack(side=tk.RIGHT)

	quick_date_frame = ttk.Frame(job_frame)
	quick_date_frame.pack(fill=tk.X, padx=5, pady=2)

	ttk.Button(quick_date_frame, text="Today", command=app.set_today, width=8).pack(side=tk.LEFT, padx=2)
	ttk.Button(quick_date_frame, text="Yesterday", command=app.set_yesterday, width=8).pack(side=tk.LEFT, padx=2)
	ttk.Button(quick_date_frame, text="Last 3 Days", command=app.set_last_3_days, width=10).pack(side=tk.LEFT, padx=2)
	ttk.Button(quick_date_frame, text="Last 7 Days", command=app.set_last_7_days, width=10).pack(side=tk.LEFT, padx=2)

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


