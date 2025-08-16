import html
import re


def decode_html_entities(text: str) -> str:
	"""Decode common HTML entities and numeric codes (stateless helper)."""
	if not text:
		return text
	# First handle numeric entities like &#...;
	def replace_numeric_entity(match):
		code = match.group(1)
		try:
			return chr(int(code))
		except Exception:
			return match.group(0)
	text = re.sub(r"&#(\d+);", replace_numeric_entity, text)
	# Then use html.unescape for named entities
	return html.unescape(text)


def format_xml_element(element, indent_level: int) -> str:
	"""Recursively format XML element with proper indentation (stateless)."""
	spaces = "    " * indent_level
	result = spaces + "<" + element.tag
	for key, value in element.attrib.items():
		result += f' {key}="{value}"'
	children = list(element)
	text_content = element.text.strip() if element.text else ""
	if children or (text_content and len(children) > 0):
		result += ">\n"
		if text_content:
			result += spaces + "    " + text_content + "\n"
		for child in children:
			result += format_xml_element(child, indent_level + 1) + "\n"
		result += spaces + "</" + element.tag + ">"
	elif text_content:
		result += ">" + text_content + "</" + element.tag + ">"
	else:
		result += "/>"
	return result


def simple_format_xml(xml_string: str) -> str:
	"""Simple XML formatting fallback (stateless)."""
	xml_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_string)
	xml_string = xml_string.replace('>', '>\n')
	xml_string = xml_string.replace('<', '\n<')
	xml_string = re.sub(r'\n\n+', '\n', xml_string)
	lines = xml_string.split('\n')
	indent_level = 0
	result = []
	for line in lines:
		line = line.strip()
		if not line:
			continue
		if line.startswith('</'):
			indent_level = max(0, indent_level - 1)
		result.append("    " * indent_level + line)
		if line.startswith('<') and not line.startswith('</') and not line.endswith('/>'):
			indent_level += 1
	return '\n'.join(result)


# ---------- Preview HTML builders and helpers (stateless) ----------

def _safe_creative_field(selected_creative: dict | None, field: str, default_value: str = 'Unknown') -> str:
	if not selected_creative:
		return default_value
	value = selected_creative.get(field)
	return str(value) if value is not None else default_value


def build_display_preview_html(selected_creative: dict | None, current_type: str, markup: str) -> str:
	"""Build HTML content for display ad preview."""
	# Prefer canonical keys but fall back to original dataset fields
	creative_size = 'Unknown'
	creative_id = 'Unknown'
	if selected_creative:
		creative_size = selected_creative.get('size') or selected_creative.get('adSize') or 'Unknown'
		creative_id = selected_creative.get('id') or selected_creative.get('creativeId') or 'Unknown'
	# Normalize banner-like sizes that sometimes arrive swapped (e.g., 50x320)
	max_width_css = "480px"
	max_height_css = "320px"
	if isinstance(creative_size, str) and 'x' in creative_size:
		try:
			decl_w_str, decl_h_str = creative_size.split('x')
			decl_w, decl_h = int(decl_w_str), int(decl_h_str)
			# Heuristic: swap if looks like a banner reported as HxW
			if current_type in ('display', 'banner') and decl_w < decl_h and decl_h >= 300 and decl_w <= 160:
				decl_w, decl_h = decl_h, decl_w
			max_width_css = f"{decl_w}px"
			max_height_css = f"{decl_h}px"
		except Exception:
			pass
	return f"""
	<html>
	<head>
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>Display Ad Preview</title>
		<style>
			body {{ 
				margin: 0; 
				padding: 20px; 
				font-family: Arial, sans-serif; 
				background: #f5f5f5;
			}}
			.ad-container {{ 
				border: 2px solid #ddd; 
				border-radius: 8px;
				padding: 20px; 
				background: white;
				max-width: 100%;
				overflow: auto;
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
			}}
			.ad-content {{ 
				max-width: min({max_width_css}, 95vw);
				max-height: min({max_height_css}, 65vh);
				margin: 0 auto;
				overflow: auto;
				border: 1px dashed #e5e5e5;
				background: #fff;
				padding: 8px;
			}}
			/* Constrain common media without forcing everything */
			.ad-content img {{ max-width: 100%; height: auto; display: block; }}
			.ad-content iframe {{ max-width: 100%; }}
			.ad-content video {{ max-width: 100%; height: auto; }}
			.preview-header {{
				background: #007bff;
				color: white;
				padding: 10px 20px;
				margin: -20px -20px 20px -20px;
				border-radius: 6px 6px 0 0;
				font-weight: bold;
				font-size: 16px;
			}}
			.info-panel {{
				background: #e9ecef;
				border: 1px solid #dee2e6;
				border-radius: 4px;
				padding: 10px;
				margin: 10px 0;
				font-size: 12px;
				color: #495057;
			}}
		</style>
	</head>
	<body>
		<div class="ad-container">
			<div class="preview-header">
				🎨 Display Ad Preview - {creative_size}
			</div>
			<div class="info-panel">
				<strong>Creative Info:</strong> ID: {creative_id}, 
				Size: {creative_size}, Type: {current_type}
			</div>
			<div class="ad-content">
				{markup}
			</div>
		</div>
	</body>
	</html>
	"""


def is_portrait_video_from_size(size_text: str | None) -> bool:
	"""Return True if given size string (e.g., '480x320') suggests portrait video."""
	if not size_text:
		return False
	if 'x' not in size_text:
		return False
	try:
		width_text, height_text = size_text.split('x')
		width_value, height_value = int(width_text), int(height_text)
		return height_value > width_value or (width_value <= 480 and height_value <= 640)
	except Exception:
		return False


def build_vast_preview_html(
	selected_creative: dict | None,
	current_type: str,
	vast_url: str,
	click_through_url: str | None,
	is_portrait: bool,
	companion_info_html: str | None,
) -> str:
	"""Build HTML content for a VAST video preview page."""
	creative_size = _safe_creative_field(selected_creative, 'size')
	creative_id = _safe_creative_field(selected_creative, 'id')
	companion_html = companion_info_html if companion_info_html else '<div class="companion-section"><h3>🖼️ Companion Ads</h3><p>No Companion</p></div>'
	container_class = ' portrait' if is_portrait else ' landscape'
	return f"""
	<html>
	<head>
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title>VAST Video Preview</title>
		<style>
			body {{ 
				margin: 0; 
				padding: 20px; 
				font-family: Arial, sans-serif; 
				background: #f5f5f5;
				font-size: 14px;
			}}
			.vast-container {{ 
				border: 2px solid #ddd; 
				border-radius: 8px;
				padding: 30px; 
				background: white;
				text-align: center;
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
				max-width: 95vw;
				width: 100%;
				margin: 0 auto;
				box-sizing: border-box;
			}}
			.vast-player {{
				max-width: 100%;
				margin: 20px auto;
				text-align: center;
			}}
			.video-container {{
				width: 100%;
				max-width: 100%;
				margin: 0 auto;
				overflow: hidden;
				border-radius: 8px;
				box-shadow: 0 4px 8px rgba(0,0,0,0.1);
				position: relative;
			}}
			.video-container video {{
				width: 100%;
				height: auto;
				object-fit: contain;
				display: block;
			}}
			.video-container.portrait {{
				max-width: 320px;
				margin: 20px auto;
			}}
			.video-container.portrait video {{
				max-width: 320px;
				max-height: 540px;
				width: auto;
				height: auto;
			}}
			.video-container.landscape {{
				max-width: 800px;
				margin: 20px auto;
				aspect-ratio: 16/9;
			}}
			.video-container.landscape video {{
				width: 100%;
				height: 100%;
				max-height: 50vh;
				object-fit: contain;
			}}
			/* Responsive design for different screen sizes */
			@media (min-width: 1200px) {{
				.video-container.landscape {{
					max-width: 800px;
					aspect-ratio: 16/9;
				}}
			}}
			@media (min-width: 768px) and (max-width: 1199px) {{
				.video-container.landscape {{
					max-width: 90vw;
					aspect-ratio: 16/9;
				}}
			}}
			@media (max-width: 767px) {{
				.video-container.landscape {{
					max-width: 95vw;
					aspect-ratio: 16/9;
				}}
				.video-container.portrait {{
					max-width: 300px;
				}}
			}}
			.url-section {{
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 15px;
				margin: 20px 0;
			}}
			.vast-url {{
				background: #f8f9fa;
				border: 1px solid #dee2e6;
				border-radius: 8px;
				padding: 15px;
				font-family: monospace;
				word-break: break-all;
				text-align: left;
				font-size: 11px;
				position: relative;
				min-height: 80px;
			}}
			.vast-url.single {{
				grid-column: 1 / -1;
			}}
			@media (max-width: 768px) {{
				.url-section {{
					grid-template-columns: 1fr;
				}}
			}}
			.copy-button {{
				position: absolute;
				top: 5px;
				right: 5px;
				background: #007bff;
				color: white;
				border: none;
				border-radius: 3px;
				padding: 2px 8px;
				font-size: 10px;
				cursor: pointer;
			}}
			.copy-button:hover {{
				background: #0056b3;
			}}
			.inline-actions {{
				margin-top: 8px;
			}}
			.preview-header {{
				background: #28a745;
				color: white;
				padding: 15px 25px;
				margin: -30px -30px 25px -30px;
				border-radius: 6px 6px 0 0;
				font-weight: bold;
				font-size: 18px;
			}}
			.info-panel {{
				background: #e9ecef;
				border: 1px solid #dee2e6;
				border-radius: 6px;
				padding: 15px;
				margin: 15px 0;
				font-size: 14px;
				color: #495057;
			}}
			.companion-section {{
				margin-top: 20px;
				border-top: 2px solid #dee2e6;
				padding-top: 20px;
			}}
			.companion-ad {{
				border: 1px solid #ccc;
				margin: 10px auto;
				max-width: 300px;
				background: white;
			}}
			.button-row {{
				display: flex;
				gap: 10px;
				justify-content: center;
				margin: 15px 0;
				flex-wrap: wrap;
			}}
			.action-button {{
				background: #6c757d;
				color: white;
				border: none;
				border-radius: 4px;
				padding: 8px 16px;
				font-size: 12px;
				cursor: pointer;
				text-decoration: none;
				display: inline-block;
			}}
			.action-button:hover {{
				background: #545b62;
			}}
			.action-button.primary {{
				background: #007bff;
			}}
			.action-button.primary:hover {{
				background: #0056b3;
			}}
		</style>
		<script>
			function copyToClipboard(text) {{
				navigator.clipboard.writeText(text).then(function() {{
					const button = event.target;
					const originalText = button.textContent;
					button.textContent = 'Copied!';
					button.style.background = '#28a745';
					setTimeout(function() {{
						button.textContent = originalText;
						button.style.background = '#007bff';
					}}, 1000);
				}});
			}}
			function resizeVideo() {{
				const videoContainer = document.querySelector('.video-container.landscape');
				const video = videoContainer ? videoContainer.querySelector('video') : null;
				if (video && videoContainer) {{
					const containerWidth = videoContainer.offsetWidth;
					const aspectRatio = 16/9;
					const calculatedHeight = containerWidth / aspectRatio;
					const maxHeight = window.innerHeight * 0.5;
					const finalHeight = Math.min(calculatedHeight, maxHeight);
					videoContainer.style.height = finalHeight + 'px';
					video.style.height = '100%';
					video.style.width = '100%';
				}}
			}}
			window.addEventListener('load', resizeVideo);
			window.addEventListener('resize', resizeVideo);
			document.addEventListener('DOMContentLoaded', function() {{
				const video = document.querySelector('video');
				if (video) {{
					video.addEventListener('loadedmetadata', resizeVideo);
				}}
			}});
		</script>
	</head>
	<body>
		<div class="vast-container">
			<div class="preview-header">
				🎬 VAST Video Ad Player - {creative_size}
			</div>
			<div class="info-panel">
				<strong>Creative Info:</strong> ID: {creative_id}, 
				Size: {creative_size}, Type: {current_type}
			</div>
			<div class="vast-player">
				<div class="video-container{container_class}">
					<video controls>
						<source src="{vast_url}" type="video/mp4">
						<source src="{vast_url}" type="video/webm">
						<source src="{vast_url}" type="video/ogg">
						Your browser does not support the video tag.
					</video>
				</div>
			</div>
			<div class="url-section">
				<div class="vast-url{' single' if not click_through_url else ''}">
					<button class="copy-button" onclick="copyToClipboard('{vast_url}')">Copy</button>
					<strong>🎯 Video URL:</strong><br>
					{vast_url}
					<div class="inline-actions">
						<a class="action-button primary" href="{vast_url}" target="_blank" rel="noopener noreferrer">Open</a>
					</div>
				</div>
				{f"""
				<div class=\"vast-url\">
					<button class=\"copy-button\" onclick=\"copyToClipboard('{click_through_url}')\">Copy</button>
					<strong>🔗 Click-Through URL:</strong><br>
					{click_through_url}
					<div class=\"inline-actions\">
						<a class=\"action-button primary\" href=\"{click_through_url}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a>
					</div>
				</div>
				""" if click_through_url else ''}
			</div>
			{companion_html}
		</div>
	</body>
	</html>
	"""


def extract_companion_ad_info(markup: str) -> dict:
	"""Extract companion ads info from VAST markup and return HTML snippet."""
	import re as _re
	from xml.etree import ElementTree as _ET
	try:
		clean_markup = _re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', markup)
		root = _ET.fromstring(clean_markup)
		# Look inside InLine first if present, else anywhere; also search inside Creatives/Creative[@adID='*-Companion']
		context = root
		inline = root.find('.//InLine')
		if inline is not None:
			context = inline
		companion_ads = context.findall('.//Companion')
		if not companion_ads:
			# Some wrappers provide companion end cards in a separate Creative with adID suffix
			for creative in root.findall(".//Creative[@adID]"):
				adid = creative.get('adID', '')
				if adid.endswith('-Companion'):
					companion_ads = creative.findall('.//Companion')
					if companion_ads:
						break
		if not companion_ads:
			# Try FMPCompanionAssets icons as fallback companions
			icons_parent = root.find(".//Extensions/Extension[@type='FMPCompanionAssets']")
			icons = []
			if icons_parent is not None:
				for icon_node in icons_parent.findall('.//Icon'):
					if icon_node.text:
						icons.append(icon_node.text.strip())
				if icons:
					companion_html = """
					<div class="companion-section">
						<h3>🖼️ Companion Ads (Icons)</h3>
					"""
					for idx, icon_url in enumerate(icons, start=1):
						companion_html += f"""
						<div class=\"companion-ad\">
							<div style=\"padding: 10px; border-bottom: 1px solid #dee2e6;\">
								<strong>Asset {idx}</strong>
							</div>
							<div style=\"padding: 10px;\">
								<img src=\"{icon_url}\" style=\"max-width: 100%; height: auto; border: 1px solid #ddd;\" alt=\"Companion Icon\">
								<div class=\"vast-url\" style=\"margin-top: 10px;\">
									<button class=\"copy-button\" onclick=\"copyToClipboard('{icon_url}')\">Copy</button>
									<strong>🖼️ Image URL:</strong><br>
									{icon_url}
								</div>
							</div>
						</div>
						"""
					companion_html += "</div>"
					return {'found': True, 'html': companion_html}
			return {'found': False, 'html': ''}
		companion_html = """
		<div class="companion-section">
			<h3>🖼️ Companion Ads</h3>
		"""
		for i, companion in enumerate(companion_ads):
			companion_id = companion.get('id', f'companion_{i}')
			width = companion.get('width', 'Unknown')
			height = companion.get('height', 'Unknown')
			static_resource = companion.find('.//StaticResource')
			image_url = static_resource.text.strip() if static_resource is not None and static_resource.text else None
			click_through = companion.find('.//CompanionClickThrough') or companion.find('.//CompanionClickTracking')
			click_url = click_through.text.strip() if click_through is not None and click_through.text else None
			companion_html += f"""
			<div class="companion-ad">
				<div style="padding: 10px; border-bottom: 1px solid #dee2e6;">
					<strong>Companion Ad {i+1}</strong> (ID: {companion_id})<br>
					Size: {width}x{height}
				</div>
			"""
			if image_url:
				# If there is a click URL, make the image clickable
				image_tag = f"<img src=\"{image_url}\" style=\"max-width: 100%; height: auto; border: 1px solid #ddd;\" alt=\"Companion Ad\">"
				if click_url:
					image_tag = f"<a href=\"{click_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{image_tag}</a>"
				companion_html += f"""
				<div style="padding: 10px;">
					{image_tag}
					<div class="vast-url" style="margin-top: 10px;">
						<button class="copy-button" onclick="copyToClipboard('{image_url}')">Copy</button>
						<strong>🖼️ Image URL:</strong><br>
						{image_url}
					</div>
				</div>
				"""
			if click_url:
				companion_html += f"""
				<div class="vast-url" style="margin: 10px;">
					<button class="copy-button" onclick="copyToClipboard('{click_url}')">Copy</button>
					<strong>🔗 Click URL:</strong><br>
					{click_url}
					<div class="inline-actions">
						<a class="action-button primary" href="{click_url}" target="_blank" rel="noopener noreferrer">Open</a>
					</div>
				</div>
				"""
			companion_html += "</div>"
		companion_html += "</div>"
		return {'found': True, 'html': companion_html}
	except _ET.ParseError:
		return {'found': False, 'html': ''}
	except Exception:
		return {'found': False, 'html': ''}


def save_html_to_temp_and_open(html_content: str, label: str = 'preview') -> None:
	"""Write HTML to a temp file and open it in the default browser."""
	import tempfile as _tempfile
	import os as _os
	import webbrowser as _webbrowser
	with _tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as _f:
		_f.write(html_content)
		temp_file = _f.name
	print(f"📄 Created {label} preview file: {temp_file}")
	try:
		print(f"📄 File size: {_os.path.getsize(temp_file)} bytes")
	except Exception:
		pass
	file_url = f"file://{_os.path.abspath(temp_file)}"
	print(f"🌐 Opening URL: {file_url}")
	_webbrowser.open(file_url)


