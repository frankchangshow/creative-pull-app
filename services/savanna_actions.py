from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


def search_creative_in_queue(
	client,
	server_hostname: str,
	http_path: str,
	access_token: str,
	pulling_table: str,
	creative_id: str,
):
	"""Thin orchestration wrapper around the Databricks client's search.

	Returns rows as provided by the client. No UI formatting here.
	"""
	return client.search_pulling_queue(
		server_hostname,
		http_path,
		access_token,
		pulling_table,
		creative_id,
	)


def build_creation_and_expire_dates(now: Optional[datetime] = None) -> Tuple[str, str]:
	"""Return formatted creation and expire timestamps (expire = now + 24h)."""
	if now is None:
		now = datetime.now()
	creation_date = now.strftime('%Y-%m-%d %H:%M:%S')
	expire_date = (now + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
	return creation_date, expire_date


def submit_creative(
	client,
	creative_id: str,
	ad_network_id: int,
	creation_date: str,
	expire_date: str,
	active: bool = True,
):
	"""Post the creative to Savanna's creative-pulling via the provided client.

	The client is expected to expose `post_to_creative_pulling(creative_data)`.
	Returns the client's response.
	"""
	creative_data = {
		"creative_id": creative_id,
		"ad_network_id": int(ad_network_id),
		"creation_date": creation_date,
		"expire_date": expire_date,
		"active": bool(active),
	}
	return client.post_to_creative_pulling(creative_data)


