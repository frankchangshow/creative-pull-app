class SavannaClientWrapper:
	"""Thin wrapper that delegates to an existing SavannaBearerClient instance."""

	def __init__(self, bearer_client):
		self.client = bearer_client

	def search_networks(self, url: str, params: dict, timeout: int = 15):
		"""GET the ad networks endpoint using the client's session."""
		return self.client.session.get(url, params=params, timeout=timeout)

	def post_to_creative_pulling(self, creative_data: dict, timeout: int = 10):
		"""POST to creative-pulling via the bearer client helper (keeps refresh behavior)."""
		return self.client.post_to_creative_pulling(creative_data)


