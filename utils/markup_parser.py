import xml.etree.ElementTree as ET

from ui.preview import decode_html_entities


def parse_ad_response(xml_string: str) -> dict:
	"""Stateless parser to extract creative markup and type from an IA SimpleM2M response.

	Returns dict with keys: type ('display'|'vast'), creative (str), width, height
	OR {'error': '...'} on failure.
	"""
	if not xml_string:
		return {'error': 'No XML content provided'}

	try:
		root = ET.fromstring(xml_string)
		width = None
		height = None
		ad_type = None
		TNS_NAMESPACE_URI = "http://www.inner-active.com/SimpleM2M/M2MResponse"
		width_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdWidth')
		height_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdHeight')
		type_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}AdType')
		if width_elem is not None:
			width = width_elem.get('Value')
		if height_elem is not None:
			height = height_elem.get('Value')
		if type_elem is not None:
			ad_type = type_elem.get('Value')
		ad_elem = root.find(f'.//{{{TNS_NAMESPACE_URI}}}Ad')
		if ad_elem is None:
			ad_elem = root.find('.//Ad')
		if ad_elem is None:
			return {'error': 'No Ad element found'}
		cdata_content = None
		for child in ad_elem:
			if child.tag is ET.Comment:
				continue
			if child.text and child.text.strip():
				cdata_content = child.text.strip()
				break
		if not cdata_content:
			cdata_content = ad_elem.text.strip() if ad_elem.text else ""
		if not cdata_content:
			return {'error': 'No CDATA content found'}
		creative = decode_html_entities(cdata_content)
		if ad_type == '8':
			return {'type': 'vast', 'creative': creative, 'width': width, 'height': height}
		# Default to display (also for unknown types)
		return {'type': 'display', 'creative': creative, 'width': width, 'height': height}
	except ET.ParseError as e:
		return {'error': f'XML parsing error: {str(e)}'}
	except Exception as e:
		return {'error': f'Unexpected error: {str(e)}'}


