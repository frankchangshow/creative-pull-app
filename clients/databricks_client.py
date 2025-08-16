from databricks import sql
import requests
import time


class DatabricksClient:
	"""Thin wrappers around Databricks SQL/REST calls. No UI/threading here."""

	def get_latest_creatives(self, server_hostname: str, http_path: str, access_token: str, table_name: str):
		"""Return list of dicts: day,id,size,width,height,type,markup (matches UI expectations)."""
		connection_params = {
			"server_hostname": server_hostname,
			"http_path": http_path,
			"access_token": access_token,
		}
		query = f"""
		SELECT day, creativeId, adSize, type, markup 
		FROM {table_name}
		ORDER BY day DESC
		LIMIT 500
		"""
		with sql.connect(**connection_params) as connection:
			with connection.cursor() as cursor:
				cursor.execute(query)
				results = cursor.fetchall()
				creatives = []
				for row in results:
					day, creative_id, ad_size, ad_type, markup = row
					size_parts = ad_size.split('x') if ad_size else ['0', '0']
					width = size_parts[0] if len(size_parts) > 0 else '0'
					height = size_parts[1] if len(size_parts) > 1 else '0'
					creatives.append({
						'day': day,
						'id': creative_id,
						'size': ad_size,
						'width': width,
						'height': height,
						'type': ad_type,
						'markup': markup,
					})
				return creatives

	def search_pulling_queue(self, server_hostname: str, http_path: str, access_token: str, pulling_table: str, creative_id: str):
		"""Return rows from creative_pulling for given creative_id."""
		connection_params = {
			"server_hostname": server_hostname,
			"http_path": http_path,
			"access_token": access_token,
		}
		query = f"""
		SELECT 
			creative_id,
			creation_date,
			expire_date,
			active
		FROM {pulling_table}
		WHERE creative_id = '{creative_id}'
		ORDER BY creation_date DESC
		LIMIT 5
		"""
		# Timing instrumentation
		t0 = time.monotonic()
		with sql.connect(**connection_params) as connection:
			t1 = time.monotonic()
			with connection.cursor() as cursor:
				cursor.execute(query)
				t2 = time.monotonic()
				rows = cursor.fetchall()
				t3 = time.monotonic()
		# Print timing breakdown
		print(f"⏱️ search_pulling_queue total={(t3 - t0):.3f}s | connect={(t1 - t0):.3f}s | execute={(t2 - t1):.3f}s | fetch={(t3 - t2):.3f}s")
		return rows

	def run_job(self, workspace_url: str, access_token: str, job_id: int, start_date: str, end_date: str):
		"""Trigger jobs/run-now and return response JSON (expects run_id on success)."""
		api_url = f"{workspace_url}/api/2.1/jobs/run-now"
		headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		}
		payload = {
			"job_id": job_id,
			"notebook_params": {"start_date": start_date, "end_date": end_date},
		}
		resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
		return resp

	def list_recent_runs(self, workspace_url: str, access_token: str, job_id: int, limit: int = 5):
		"""Call jobs/runs/list and return JSON."""
		api_url = f"{workspace_url}/api/2.1/jobs/runs/list"
		headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		}
		params = {"limit": limit, "offset": 0, "job_id": job_id}
		resp = requests.get(api_url, headers=headers, params=params, timeout=30)
		return resp

	def get_run_status(self, workspace_url: str, access_token: str, run_id: int):
		"""Call jobs/runs/get and return JSON."""
		api_url = f"{workspace_url}/api/2.1/jobs/runs/get"
		headers = {
			"Authorization": f"Bearer {access_token}",
			"Content-Type": "application/json",
		}
		params = {"run_id": run_id}
		resp = requests.get(api_url, headers=headers, params=params, timeout=30)
		return resp


