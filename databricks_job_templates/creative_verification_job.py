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
from pyspark.sql.functions import col, lower, trim, regexp_replace, current_timestamp


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


def send_email_smtp(to_email: str, subject: str, body: str):
    sender = dbutils.secrets.get(EMAIL_SCOPE, SMTP_USER_KEY)  # type: ignore # provided by Databricks
    app_pw = dbutils.secrets.get(EMAIL_SCOPE, SMTP_APP_PW_KEY)  # type: ignore

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(sender, app_pw)
        s.send_message(msg)


def sanitize(expr):
    """Robust ID normalizer: cast->string, trim, lower, strip zero-width & NBSP."""
    clean = lower(trim(expr.cast("string")))
    clean = regexp_replace(clean, r"[\u200B-\u200D\uFEFF\u00A0]", "")
    return clean


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
    f"SELECT creativeId, user_email FROM {WATCHLIST_TABLE} WHERE status='PENDING'"
).dropDuplicates())

print("pending.count =", pending.count())
_safe_display(pending)

if pending.count() == 0:
    print("No pending creatives to check.")
    dbutils.notebook.exit("No pending creatives.")  # type: ignore

# Normalize both sides
pending_norm = (pending
    .withColumn("creativeId_norm", sanitize(col("creativeId")))
    .select("creativeId", "user_email", "creativeId_norm")
    .distinct())

persistent_norm = (spark.table(PERSISTENT_TABLE)
    .withColumn("creativeId_norm", sanitize(col(ID_COLUMN)))
    .select("creativeId_norm")
    .distinct())

print("pending_norm.count =", pending_norm.count(), "| persistent_norm.count =", persistent_norm.count())

# Join without collect
found_norm = (pending_norm.alias("p")
    .join(persistent_norm.alias("t"), on="creativeId_norm", how="inner")
    .select("p.creativeId", "p.user_email")
    .distinct())

print("found_norm.count =", found_norm.count())
_safe_display(found_norm)

if found_norm.count() == 0:
    print("No matches after normalized join. Showing up to 200 pending rows that didn't match...")
    missing_norm = (pending_norm.alias("p")
        .join(persistent_norm.alias("t"), on="creativeId_norm", how="left_anti")
        .select("p.creativeId", "p.creativeId_norm", "p.user_email"))
    _safe_display(missing_norm.limit(200))
    dbutils.notebook.exit("No matches found.")  # type: ignore

# Notify and update
rows = found_norm.collect()
notified_total, error_total = 0, 0

for row in rows:
    creative_id = row.creativeId
    user_email = row.user_email
    try:
        send_email_smtp(
            to_email=user_email,
            subject=f"Creative {creative_id} is available",
            body=f"Creative {creative_id} is now available in Databricks.",
        )
        spark.sql(f"""
          UPDATE {WATCHLIST_TABLE}
          SET status = 'NOTIFIED', notified_timestamp = current_timestamp()
          WHERE creativeId = '{creative_id}' AND status = 'PENDING'
        """)
        print(f"NOTIFIED: {creative_id} -> {user_email}")
        notified_total += 1
    except Exception as e:
        spark.sql(f"""
          UPDATE {WATCHLIST_TABLE}
          SET status = 'ERROR'
          WHERE creativeId = '{creative_id}' AND status = 'PENDING'
        """)
        print(f"ERROR notifying {creative_id} -> {user_email}: {e}")
        error_total += 1

print(f"Job completed. notified={notified_total}, errors={error_total}, pending_scanned={pending.count()}")


