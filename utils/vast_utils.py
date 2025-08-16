import re
import html as _html
from xml.etree import ElementTree as ET
import requests


def extract_vast_url(markup: str) -> str | None:
	"""Return a playable MP4 URL from VAST markup.
	- If markup contains a VASTAdTagURI, follow wrappers to the InLine and pick the highest-bitrate MP4.
	- Otherwise, try to read <MediaFile> tags or fallback to regex URL extraction.
	"""
	# First, look for VASTAdTagURI (wrapper)
	vast_ad_tag_patterns = [
		r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>',
		r'<VASTAdTagURI>(.*?)</VASTAdTagURI>',
	]
	for pattern in vast_ad_tag_patterns:
		m = re.search(pattern, markup, re.IGNORECASE)
		if m:
			vast_xml_url = _html.unescape(m.group(1).strip())
			return _process_vast_chain(vast_xml_url)

	# No wrapper → try direct XML media files
	try:
		clean_markup = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', markup)
		root = ET.fromstring(clean_markup)
		media_files = []
		for media_file in root.findall('.//MediaFile'):
			url = (media_file.text or '').strip()
			media_type = media_file.get('type', '')
			if media_type == 'video/mp4' or url.endswith('.mp4'):
				bitrate = int(media_file.get('bitrate', '0') or '0')
				media_files.append({'url': url, 'bitrate': bitrate})
		if media_files:
			media_files.sort(key=lambda x: x['bitrate'], reverse=True)
			return media_files[0]['url']
	except ET.ParseError:
		pass

	# Fallback regex scan
	def _sanitize_media_url(raw: str) -> str | None:
		candidate = _html.unescape(raw or '').strip()
		mp4_match = re.search(r'(https?://[^\s<>"\']+?\.mp4[^\s<>"\']*)', candidate, re.IGNORECASE)
		if mp4_match:
			return mp4_match.group(1)
		any_match = re.search(r'(https?://[^\s<>"\']+)', candidate, re.IGNORECASE)
		return any_match.group(1) if any_match else None

	for pattern in [
		r'<MediaFile[^>]*><!\[CDATA\[(.*?)\]\]></MediaFile>',
		r'<MediaFile[^>]*>(.*?)</MediaFile>',
		r'<URL><!\[CDATA\[(.*?)\]\]></URL>',
		r'<URL>(.*?)</URL>',
	]:
		m = re.search(pattern, markup, re.IGNORECASE | re.DOTALL)
		if m:
			url = _sanitize_media_url(m.group(1))
			if url and (url.endswith('.mp4') or 'video' in url):
				return url

	return None


def extract_vast_click_through(markup: str) -> str | None:
	"""Follow VAST wrappers (if present) and return a ClickThrough URL; fallback to direct scan."""
	for pattern in [
		r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>',
		r'<VASTAdTagURI>(.*?)</VASTAdTagURI>',
	]:
		m = re.search(pattern, markup, re.IGNORECASE)
		if m:
			vast_xml_url = _html.unescape(m.group(1).strip())
			return _extract_click_through_from_vast_chain(vast_xml_url)

	for pattern in [
		r'<ClickThrough><!\[CDATA\[(.*?)\]\]></ClickThrough>',
		r'<ClickThrough>(.*?)</ClickThrough>',
		r'<ClickTracking><!\[CDATA\[(.*?)\]\]></ClickTracking>',
		r'<ClickTracking>(.*?)</ClickTracking>',
	]:
		m = re.search(pattern, markup, re.IGNORECASE)
		if m:
			return m.group(1)
	return None


def get_inline_vast_xml_from_markup(markup: str) -> str | None:
	"""If markup has a VASTAdTagURI, follow to the final InLine VAST XML and return its text."""
	try:
		for pattern in [
			r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>',
			r'<VASTAdTagURI>(.*?)</VASTAdTagURI>',
		]:
			m = re.search(pattern, markup, re.IGNORECASE)
			if m:
				vast_url = _html.unescape(m.group(1).strip())
				return _fetch_inline_vast_xml(vast_url, 0)
		return None
	except Exception:
		return None


def _process_vast_chain(vast_url: str, wrapper_count: int = 0) -> str:
	MAX_VAST_WRAPPERS = 5
	if wrapper_count > MAX_VAST_WRAPPERS:
		raise Exception('Exceeded maximum VAST wrapper redirects')
	resp = requests.get(vast_url, timeout=10)
	resp.raise_for_status()
	vast_xml = resp.text
	root = ET.fromstring(vast_xml)
	inline = root.find('.//InLine')
	if inline is not None:
		linear = inline.find('.//Linear')
		if linear is None:
			raise Exception('InLine VAST missing Linear')
		media_files = []
		for mf in linear.findall('.//MediaFile'):
			url = (mf.text or '').strip()
			mime = mf.get('type', '')
			if mime == 'video/mp4' or url.endswith('.mp4'):
				bitrate = int(mf.get('bitrate', '0') or '0')
				media_files.append({'url': url, 'bitrate': bitrate})
		if not media_files:
			raise Exception('No MP4 in InLine VAST')
		media_files.sort(key=lambda x: x['bitrate'], reverse=True)
		return media_files[0]['url']
	wrapper = root.find('.//Wrapper')
	if wrapper is not None:
		tag = wrapper.find('.//VASTAdTagURI')
		if tag is None or not tag.text:
			raise Exception('Wrapper missing VASTAdTagURI')
		return _process_vast_chain(tag.text.strip(), wrapper_count + 1)
	raise Exception('VAST contains neither InLine nor Wrapper')


def _fetch_inline_vast_xml(vast_url: str, wrapper_count: int = 0) -> str | None:
	MAX_VAST_WRAPPERS = 5
	if wrapper_count > MAX_VAST_WRAPPERS:
		return None
	resp = requests.get(vast_url, timeout=10)
	if resp.status_code != 200:
		return None
	root = None
	try:
		root = ET.fromstring(resp.text)
	except ET.ParseError:
		return None
	inline = root.find('.//InLine')
	if inline is not None:
		return resp.text
	wrapper = root.find('.//Wrapper')
	if wrapper is not None:
		tag = wrapper.find('.//VASTAdTagURI')
		if tag is not None and tag.text:
			return _fetch_inline_vast_xml(tag.text.strip(), wrapper_count + 1)
	return None


def _extract_click_through_from_vast_chain(vast_url: str, wrapper_count: int = 0) -> str | None:
	MAX_VAST_WRAPPERS = 5
	if wrapper_count > MAX_VAST_WRAPPERS:
		raise Exception('Exceeded maximum VAST wrapper redirects')
	resp = requests.get(vast_url, timeout=10)
	resp.raise_for_status()
	root = ET.fromstring(resp.text)
	inline = root.find('.//InLine')
	if inline is not None:
		linear = inline.find('.//Linear')
		if linear is None:
			return None
		video_clicks = linear.find('.//VideoClicks')
		if video_clicks is not None:
			ct = video_clicks.find('.//ClickThrough')
			if ct is not None and ct.text:
				return ct.text.strip()
		return None
	wrapper = root.find('.//Wrapper')
	if wrapper is not None:
		tag = wrapper.find('.//VASTAdTagURI')
		if tag is not None and tag.text:
			return _extract_click_through_from_vast_chain(tag.text.strip(), wrapper_count + 1)
	return None


