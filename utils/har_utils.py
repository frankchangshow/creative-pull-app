import json
import re


def extract_token_from_har(har_file_path: str) -> str:
	"""Extract bearer token from HAR file (exact logic migrated)."""
	try:
		print(f"🔍 Extracting token from HAR file: {har_file_path}")
		with open(har_file_path, 'r', encoding='utf-8') as f:
			har_data = json.load(f)

		# JWT pattern
		bearer_pattern = r'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
		tokens_found = []

		for entry in har_data.get('log', {}).get('entries', []):
			# request headers
			if 'request' in entry:
				headers = entry['request'].get('headers', [])
				for header in headers:
					if header.get('name', '').lower() == 'authorization':
						auth_value = header.get('value', '')
						if 'Bearer ' in auth_value:
							token = auth_value.replace('Bearer ', '')
							if re.match(bearer_pattern, token):
								tokens_found.append({'token': token, 'url': entry['request'].get('url', ''), 'source': 'header'})
			# response bodies
			if 'response' in entry:
				content = entry['response'].get('content', {})
				if 'text' in content:
					text_content = content['text']
					for token in re.findall(bearer_pattern, text_content):
						tokens_found.append({'token': token, 'url': entry['request'].get('url', ''), 'source': 'response_body'})
					access_token_pattern = r'access_token=([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)'
					for token in re.findall(access_token_pattern, text_content):
						tokens_found.append({'token': token, 'url': entry['request'].get('url', ''), 'source': 'access_token'})

		# dedupe
		unique_tokens, seen = [], set()
		for info in tokens_found:
			if info['token'] not in seen:
				unique_tokens.append(info)
				seen.add(info['token'])

		if unique_tokens:
			selected = unique_tokens[0]['token']
			print(f"✅ Found {len(unique_tokens)} tokens, using: {selected[:30]}...{selected[-30:]}")
			return selected
		else:
			print("❌ No tokens found in HAR file")
			return None
	except Exception as e:
		print(f"❌ Error extracting token from HAR: {e}")
		return None


