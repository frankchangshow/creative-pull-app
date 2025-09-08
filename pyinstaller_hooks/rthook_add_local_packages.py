import os
import sys


def _add_dir_to_sys_path(dirname: str) -> None:
	try:
		base = getattr(sys, "_MEIPASS", None)  # Folder where PyInstaller unpacks data
		if not base:
			return
		candidate = os.path.join(base, dirname)
		if os.path.isdir(candidate) and candidate not in sys.path:
			sys.path.insert(0, candidate)
	except Exception:
		# Best-effort; do not crash app on hook
		pass


for _pkg in ("ui", "utils", "clients", "services", "config"):
	_add_dir_to_sys_path(_pkg)




