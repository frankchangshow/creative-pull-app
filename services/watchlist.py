from databricks import sql


def insert_watchlist_entry(
	server_hostname: str,
	http_path: str,
	access_token: str,
	creative_id: str,
	user_email: str,
	table: str = "prod_atlas_datalake.pso_sandbox.creative_verification_watchlist",
):
	"""Insert a new watchlist row with PENDING status and current timestamp.

	Relies on Databricks parameterized INSERT; passes string parameters as-is.
	"""
	if not user_email:
		return None
	insert_sql = f"""
	INSERT INTO {table} (creativeId, user_email, status, submitted_timestamp)
	VALUES (?, ?, 'PENDING', current_timestamp())
	"""
	with sql.connect(server_hostname=server_hostname, http_path=http_path, access_token=access_token) as connection:
		with connection.cursor() as cursor:
			cursor.execute(insert_sql, (creative_id, user_email))
			# No result set for INSERT; return success indicator
			return True


