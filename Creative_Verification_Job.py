"""
Databricks Notebook Template: Creative Verification and Notification Job

Copy this whole cell into a Python notebook in your Databricks workspace.
Requires:
  - Two secrets in scope 'email-scope': 'gmail-smtp-user', 'gmail-app-password'
  - Tables:
      prod_atlas_datalake.pso_sandbox.creative_verification_watchlist
      prod_atlas_datalake.pso_sandbox.sampled_ads_persistent

What it does:
  1) Refreshes tables and clears Spark cache
  2) Reads PENDING rows from watchlist
  3) Normalizes IDs and joins against persistent table (no collect)
  4) Sends Gmail SMTP email for matches and updates status to NOTIFIED
  5) Prints counts and basic diagnostics
"""

import smtplib, ssl
from email.message import EmailMessage
from pyspark.sql.functions import col, lower, trim, regexp_replace, current_timestamp, collect_set, first
from datetime import datetime
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom
import html as _html
import requests

# Cache for deal name lookups (per-job runtime)
_deal_name_cache: dict[str, str | None] = {}


# ---------------- Configuration ----------------
WATCHLIST_TABLE   = "prod_atlas_datalake.pso_sandbox.creative_verification_watchlist"
PERSISTENT_TABLE  = "prod_atlas_datalake.pso_sandbox.sampled_ads_persistent"
ID_COLUMN         = "creativeId"

EMAIL_SCOPE       = "email-scope"
SMTP_USER_KEY     = "gmail-smtp-user"
SMTP_APP_PW_KEY   = "gmail-app-password"


def _safe_display(df, n=20):
    try:
        display(df.limit(n))  # type: ignore # only in Databricks
    except Exception:
        pass


def send_email_smtp(to_email: str, subject: str, body_html: str, attachments: list[tuple[str, str, str]] | None = None):
    sender = dbutils.secrets.get(EMAIL_SCOPE, SMTP_USER_KEY)  # type: ignore # provided by Databricks
    app_pw = dbutils.secrets.get(EMAIL_SCOPE, SMTP_APP_PW_KEY)  # type: ignore

    msg = EmailMessage()
    msg["From"] = sender
    # Support multiple recipients separated by comma/semicolon/space
    if isinstance(to_email, str):
        recipients = [r.strip() for r in re.split(r"[,;\s]", to_email) if r.strip()]
    else:
        recipients = list(to_email)
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    # Provide both plain text and HTML alternatives
    plain_fallback = re.sub(r"<[^>]+>", "", body_html)
    msg.set_content(plain_fallback)
    msg.add_alternative(body_html, subtype="html")

    # Attachments: list of (filename, text_content, kind) where kind in {"plain","html"}
    if attachments:
        for item in attachments:
            if len(item) == 3:
                fname, text, kind = item
            else:
                fname, text = item
                kind = "plain"
            subtype = "html" if kind == "html" else "plain"
            msg.add_attachment(text, subtype=subtype, filename=fname)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(sender, app_pw)
        s.send_message(msg)


def sanitize(expr):
    """Robust ID normalizer: cast->string, trim, lower, strip zero-width & NBSP."""
    clean = lower(trim(expr.cast("string")))
    clean = regexp_replace(clean, r"[\u200B-\u200D\uFEFF\u00A0]", "")
    return clean


# ---------------- Helpers: Markup processing ----------------
def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def pretty_xml_or_text(text: str) -> str:
    """Pretty format XML if possible; otherwise return as-is."""
    try:
        root = ET.fromstring(text)
        rough = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(rough)
        return parsed.toprettyxml(indent="  ")
    except Exception:
        return text


def decode_html_entities(text: str) -> str:
    try:
        return _html.unescape(text)
    except Exception:
        return text


def parse_ad_response(xml_string: str) -> dict:
    """Extract creative markup and type from IA SimpleM2M SDK response.

    Returns dict with keys: type ('display'|'vast'), creative (str), width, height
    or {'error': '...'} on failure.
    Mirrors utils.markup_parser.parse_ad_response.
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
        return {'type': 'display', 'creative': creative, 'width': width, 'height': height}
    except ET.ParseError as e:
        return {'error': f'XML parsing error: {str(e)}'}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}


def _fetch_inline_vast_xml(vast_url: str, wrapper_count: int = 0) -> str | None:
    MAX_VAST_WRAPPERS = 5
    if wrapper_count > MAX_VAST_WRAPPERS:
        return None
    resp = requests.get(vast_url, timeout=15)
    if resp.status_code != 200:
        return None
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


def _process_vast_chain_for_media(vast_url: str, wrapper_count: int = 0) -> str | None:
    MAX_VAST_WRAPPERS = 5
    if wrapper_count > MAX_VAST_WRAPPERS:
        return None
    resp = requests.get(vast_url, timeout=15)
    if resp.status_code != 200:
        return None
    root = ET.fromstring(resp.text)
    inline = root.find('.//InLine')
    if inline is not None:
        linear = inline.find('.//Linear')
        if linear is None:
            return None
        media_files = []
        for mf in linear.findall('.//MediaFile'):
            url = (mf.text or '').strip()
            mime = (mf.get('type') or '').lower()
            if mime == 'video/mp4' or url.lower().endswith('.mp4'):
                bitrate = int(mf.get('bitrate', '0') or '0')
                media_files.append({'url': url, 'bitrate': bitrate})
        if not media_files:
            return None
        media_files.sort(key=lambda x: x['bitrate'], reverse=True)
        return media_files[0]['url']
    wrapper = root.find('.//Wrapper')
    if wrapper is not None:
        tag = wrapper.find('.//VASTAdTagURI')
        if tag is not None and tag.text:
            return _process_vast_chain_for_media(tag.text.strip(), wrapper_count + 1)
    return None


def _process_vast_chain_for_click(vast_url: str, wrapper_count: int = 0) -> str | None:
    MAX_VAST_WRAPPERS = 5
    if wrapper_count > MAX_VAST_WRAPPERS:
        return None
    resp = requests.get(vast_url, timeout=15)
    if resp.status_code != 200:
        return None
    root = ET.fromstring(resp.text)
    inline = root.find('.//InLine')
    if inline is not None:
        linear = inline.find('.//Linear')
        if linear is None:
            return None
        vc = linear.find('.//VideoClicks')
        if vc is not None:
            ct = vc.find('.//ClickThrough')
            if ct is not None and ct.text:
                return ct.text.strip()
        return None
    wrapper = root.find('.//Wrapper')
    if wrapper is not None:
        tag = wrapper.find('.//VASTAdTagURI')
        if tag is not None and tag.text:
            return _process_vast_chain_for_click(tag.text.strip(), wrapper_count + 1)
    return None


def extract_vast_media_and_click(markup: str) -> tuple[str | None, str | None]:
    """Return (media_url, click_url), following VAST wrappers if needed."""
    if not markup:
        return None, None
    try:
        # If there is a VASTAdTagURI, follow to InLine
        m = re.search(r'<VASTAdTagURI><!\[CDATA\[(.*?)\]\]></VASTAdTagURI>|<VASTAdTagURI>(.*?)</VASTAdTagURI>', markup, re.IGNORECASE | re.DOTALL)
        if m:
            tag_url = _html.unescape((m.group(1) or m.group(2) or '').strip())
            media_url = _process_vast_chain_for_media(tag_url)
            click_url = _process_vast_chain_for_click(tag_url)
            return media_url, click_url

        # Otherwise, try direct MediaFile and ClickThrough in given markup
        root = ET.fromstring(markup)
        media_urls = []
        for mf in root.iter():
            if _strip_ns(mf.tag).lower() == 'mediafile' and mf.text:
                url = mf.text.strip()
                type_attr = (mf.attrib.get('type') or '').lower()
                media_urls.append((url, type_attr))
        media_url = None
        for url, t in media_urls:
            if url.lower().endswith('.mp4') or 'mp4' in t:
                media_url = url
                break
        if not media_url and media_urls:
            media_url = media_urls[0][0]

        click_url = None
        for el in root.iter():
            if _strip_ns(el.tag).lower() == 'clickthrough' and el.text:
                click_url = el.text.strip()
                break
        if not click_url:
            for el in root.iter():
                if _strip_ns(el.tag).lower() == 'clicktracking' and el.text:
                    click_url = el.text.strip()
                    break
        return media_url, click_url
    except Exception:
        return None, None


# ---------------- Body builder ----------------
def build_email_body_html(creative_id: str, submitted_ts: str | None, found_dt: datetime, media_url: str | None, click_url: str | None, meta: dict | None = None) -> str:
    submitted_str = submitted_ts or "Unknown"
    found_str = found_dt.strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        f"<h3>Creative Verification</h3>",
        f"<p><strong>Creative ID:</strong> {creative_id}<br/>",
        f"<strong>Status:</strong> FOUND<br/>",
        f"<strong>Submitted:</strong> {submitted_str}<br/>",
        f"<strong>Found:</strong> {found_str}</p>",
    ]
    if meta:
        ds = meta.get("demand_source")
        ad = meta.get("adomain")
        di = meta.get("dealId")
        dn = meta.get("deal_name")
        lines = []
        if ds:
            lines.append(f"<strong>Demand Source:</strong> {ds}")
        if ad:
            lines.append(f"<strong>Adomain:</strong> {ad}")
        if di:
            lines.append(f"<strong>Deal ID:</strong> {di}")
        if dn:
            lines.append(f"<strong>Deal Name:</strong> {dn}")
        if lines:
            parts.append("<p>" + "<br/>".join(lines) + "</p>")

    if media_url:
        parts.append(f"<p><strong>Video URL:</strong> <a href=\"{media_url}\">{media_url}</a></p>")
    if click_url:
        parts.append(f"<p><strong>Click-through URL:</strong> <a href=\"{click_url}\">{click_url}</a></p>")
    parts.append('<p><a href="https://test-a-tag.com/" target="_blank" rel="noopener">Open test-a-tag.com</a></p>')
    return "\n".join(parts)


# ---------------- Preview HTML builders (simplified, email attachment use) ----------------
def _parse_size_to_css(size: str | None) -> tuple[str, str]:
    max_w, max_h = "480px", "320px"
    if size and 'x' in size:
        try:
            w, h = size.split('x')
            max_w = f"{int(w)}px"
            max_h = f"{int(h)}px"
        except Exception:
            pass
    return max_w, max_h


def build_display_preview_html(markup: str, size: str | None, creative_id: str) -> str:
    max_w, max_h = _parse_size_to_css(size)
    return f"""
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Display Ad Preview - {creative_id}</title>
      <style>
        body {{ margin:0; padding:20px; font-family: Arial, sans-serif; background:#f5f5f5; }}
        .ad-container {{ border:2px solid #ddd; border-radius:8px; padding:20px; background:#fff; }}
        .ad-content {{ max-width: min({max_w}, 95vw); max-height: min({max_h}, 85vh); margin:0 auto; overflow:auto; border:1px dashed #e5e5e5; background:#fff; padding:8px; }}
        .ad-content img {{ max-width:100%; height:auto; display:block; }}
        .ad-content iframe {{ max-width:100%; }}
        .ad-content video {{ max-width:100%; height:auto; }}
      </style>
    </head>
    <body>
      <div class="ad-container">
        <div class="ad-content">{markup}</div>
      </div>
    </body>
    </html>
    """


def build_vast_preview_html(media_url: str, click_url: str | None, size: str | None, creative_id: str) -> str:
    container_class = "landscape"
    return f"""
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>VAST Video Preview - {creative_id}</title>
      <style>
        body {{ margin:0; padding:20px; font-family: Arial, sans-serif; background:#f5f5f5; }}
        .video-container {{ max-width:800px; margin:20px auto; }}
        video {{ width:100%; height:auto; }}
        .links {{ text-align:center; margin-top:10px; }}
        a.button {{ background:#007bff; color:#fff; padding:6px 12px; border-radius:4px; text-decoration:none; margin:0 6px; }}
      </style>
    </head>
    <body>
      <div class="video-container {container_class}">
        <video controls><source src="{media_url}" type="video/mp4"/>Your browser does not support the video tag.</video>
        <div class="links">
          <a class="button" href="{media_url}" target="_blank" rel="noopener">Open Video</a>
          {('<a class="button" href="' + click_url + '" target="_blank" rel="noopener">Click-through</a>') if click_url else ''}
        </div>
      </div>
    </body>
    </html>
    """

# ---------------- Cleanup helper ----------------
_DID_CLEANUP = False

def _cleanup_watchlist_older_than(days: int = 14) -> None:
    """Delete watchlist rows older than N days based on submitted_timestamp.

    Runs a quick count for logging, then issues a DELETE. Swallows errors to avoid
    impacting the main job flow.
    """
    global _DID_CLEANUP
    if _DID_CLEANUP:
        return
    try:
        preview = spark.sql(f"""
          SELECT COUNT(*) AS c
          FROM {WATCHLIST_TABLE}
          WHERE submitted_timestamp < DATE_SUB(CURRENT_TIMESTAMP(), {days})
        """).first()
        purge_count = int(preview["c"]) if preview and "c" in preview.asDict() else 0
        if purge_count > 0:
            print(f"Cleanup: deleting {purge_count} old rows (>={days} days) from {WATCHLIST_TABLE}")
        spark.sql(f"""
          DELETE FROM {WATCHLIST_TABLE}
          WHERE submitted_timestamp < DATE_SUB(CURRENT_TIMESTAMP(), {days})
        """)
        _DID_CLEANUP = True
    except Exception as e:
        print(f"Cleanup warning: {e}")

def _exit_with_cleanup(message: str) -> None:
    """Run cleanup once, then exit the notebook."""
    try:
        _cleanup_watchlist_older_than(14)
    finally:
        dbutils.notebook.exit(message)  # type: ignore

# ---------------- Job Body ----------------
print(f"Watchlist:  {WATCHLIST_TABLE}")
print(f"Persistent: {PERSISTENT_TABLE}.{ID_COLUMN}")

# Refresh and clear caches so we see latest rows
spark.catalog.clearCache()
spark.sql(f"REFRESH TABLE {WATCHLIST_TABLE}")
spark.sql(f"REFRESH TABLE {PERSISTENT_TABLE}")

pending_sql_cnt = spark.sql(f"SELECT COUNT(*) c FROM {WATCHLIST_TABLE} WHERE status='PENDING'").first()["c"]
print("watchlist PENDING count:", pending_sql_cnt)

# Read pending
pending = (spark.sql(
    f"SELECT creativeId, user_email, CAST(submitted_timestamp AS STRING) AS submitted_ts FROM {WATCHLIST_TABLE} WHERE status='PENDING'"
).dropDuplicates())

print("pending.count =", pending.count())
_safe_display(pending)

if pending.count() == 0:
    print("No pending creatives to check.")
    _exit_with_cleanup("No pending creatives.")

# Normalize both sides
pending_norm = (pending
    .withColumn("creativeId_norm", sanitize(col("creativeId")))
    .select("creativeId", "user_email", "submitted_ts", "creativeId_norm")
    .distinct())

persistent_norm = (spark.table(PERSISTENT_TABLE)
    .withColumn("creativeId_norm", sanitize(col(ID_COLUMN)))
    .select("creativeId_norm")
    .distinct())

print("pending_norm.count =", pending_norm.count(), "| persistent_norm.count =", persistent_norm.count())

# Join without collect
found_norm = (pending_norm.alias("p")
    .join(persistent_norm.alias("t"), on="creativeId_norm", how="inner")
    .select("p.creativeId", "p.user_email", "p.submitted_ts")
    .distinct())

print("found_norm.count =", found_norm.count())
_safe_display(found_norm)

if found_norm.count() == 0:
    print("No matches after normalized join. Showing up to 200 pending rows that didn't match...")
    missing_norm = (pending_norm.alias("p")
        .join(persistent_norm.alias("t"), on="creativeId_norm", how="left_anti")
        .select("p.creativeId", "p.creativeId_norm", "p.user_email"))
    _safe_display(missing_norm.limit(200))
    _exit_with_cleanup("No matches found.")

# Notify and update
grouped = (found_norm
    .groupBy("creativeId")
    .agg(
        collect_set("user_email").alias("recipients"),
        first("submitted_ts", ignorenulls=True).alias("submitted_ts")
    ))

rows = grouped.collect()
notified_total, error_total = 0, 0

for row in rows:
    creative_id = row.creativeId
    recipients = list(row.recipients) if row.recipients else []
    submitted_ts = row.submitted_ts if hasattr(row, 'submitted_ts') else None
    # Attempt to extract media/click and build a raw markup attachment
    media_url, click_url = None, None
    attachments: list[tuple[str, str, str]] = []
    try:
        sample = spark.sql(f"SELECT markup FROM {PERSISTENT_TABLE} WHERE {ID_COLUMN} = '{creative_id}' LIMIT 1").collect()
        if sample and sample[0][0]:
            raw = sample[0][0]
            parsed = parse_ad_response(raw)
            if parsed.get('type') == 'vast':
                media_url, click_url = extract_vast_media_and_click(parsed.get('creative') or raw)
                # Attach pretty VAST XML as .txt and a simple preview .html
                creative_xml = pretty_xml_or_text(parsed.get('creative') or raw)
                attachments.append((f"ad_markup_{creative_id}.txt", creative_xml, "plain"))
                if media_url:
                    preview_html = build_vast_preview_html(media_url, click_url, None, creative_id)
                    attachments.append((f"preview_{creative_id}.html", preview_html, "html"))
            else:
                creative_html = parsed.get('creative') or raw
                attachments.append((f"ad_markup_{creative_id}.txt", creative_html, "plain"))
                preview_html = build_display_preview_html(creative_html, None, creative_id)
                attachments.append((f"preview_{creative_id}.html", preview_html, "html"))
    except Exception:
        pass

    # Lightweight metadata (no join): from bids table yesterday; pick latest hour
    meta = None
    try:
        meta_row = spark.sql(f"""
          SELECT creativeId, adomain, demandAccountName AS demand_source, dealId
          FROM dtx_catalog.prod_bids_hourly_full_pq
          WHERE day = date_sub(current_date, 1)
            AND creativeId = '{creative_id}'
          ORDER BY hour DESC
          LIMIT 1
        """).first()
        if meta_row:
            meta = {
                "adomain": meta_row.adomain,
                "demand_source": meta_row.demand_source,
                "dealId": meta_row.dealId,
            }
            # Optional second tiny lookup for deal name (point query, cached)
            if meta_row.dealId:
                deal_id = meta_row.dealId
                deal_name = _deal_name_cache.get(deal_id)
                if deal_name is None:
                    r = spark.sql(f"""
                      SELECT dealFreeInputName AS deal_name
                      FROM prod_inneractive_engines_db.inneractive_engines_db.deals
                      WHERE dealID = '{deal_id}'
                      LIMIT 1
                    """).first()
                    deal_name = r.deal_name if r else None
                    _deal_name_cache[deal_id] = deal_name
                meta["deal_name"] = deal_name
    except Exception:
        meta = None
    try:
        if recipients:
            body_html = build_email_body_html(creative_id, submitted_ts, datetime.utcnow(), media_url, click_url, meta)
            send_email_smtp(
                to_email=recipients,
                subject=f"Creative {creative_id} is available",
                body_html=body_html,
                attachments=attachments,
            )
        spark.sql(f"""
          UPDATE {WATCHLIST_TABLE}
          SET status = 'NOTIFIED', notified_timestamp = current_timestamp()
          WHERE creativeId = '{creative_id}' AND status = 'PENDING'
        """)
        print(f"NOTIFIED: {creative_id} -> {', '.join(recipients)}")
        notified_total += 1
    except Exception as e:
        spark.sql(f"""
          UPDATE {WATCHLIST_TABLE}
          SET status = 'ERROR'
          WHERE creativeId = '{creative_id}' AND status = 'PENDING'
        """)
        print(f"ERROR notifying {creative_id}: {e}")
        error_total += 1

print(f"Job completed. notified={notified_total}, errors={error_total}, pending_scanned={pending.count()}")


# ---------------- Post-job cleanup ----------------
# Also run retention on the normal completion path
_cleanup_watchlist_older_than(14)
