# Databricks notebook source
# MAGIC %scala
# MAGIC // Cell 1 — Inputs, date logic, skip/force days, and auto-fill partial days
# MAGIC
# MAGIC // Widgets
# MAGIC dbutils.widgets.text("start_date", "", "Start Date (YYYY-MM-DD) — leave blank for auto")
# MAGIC dbutils.widgets.text("end_date",   "", "End Date (YYYY-MM-DD) — leave blank for auto")
# MAGIC dbutils.widgets.text("force_process_days", "", "Force days CSV (YYYY-MM-DD, optional)")
# MAGIC dbutils.widgets.text("keep_days", "7", "Keep last N days")
# MAGIC dbutils.widgets.text("min_rows_per_day", "10", "Min rows/day to consider 'complete'")
# MAGIC
# MAGIC // Paths & table config
# MAGIC val baseGcsPath  = "gs://gcs-core-services-agp-exchange-bronze-regional-useast1-prod/jaquet/staging/ADS_SAMPLING"
# MAGIC val catalogName  = "prod_atlas_datalake"
# MAGIC val databaseName = "pso_sandbox"
# MAGIC val tableName    = "sampled_ads_persistent"
# MAGIC val fullTableName = s"$catalogName.$databaseName.$tableName"
# MAGIC
# MAGIC // Date handling
# MAGIC import java.time._
# MAGIC import java.time.format.DateTimeFormatter
# MAGIC import java.time.temporal.ChronoUnit
# MAGIC
# MAGIC val fmt       = DateTimeFormatter.ofPattern("yyyy-MM-dd")
# MAGIC val sIn       = dbutils.widgets.get("start_date").trim
# MAGIC val eIn       = dbutils.widgets.get("end_date").trim
# MAGIC val keepDays  = dbutils.widgets.get("keep_days").trim.toInt
# MAGIC val minRows   = dbutils.widgets.get("min_rows_per_day").trim.toInt
# MAGIC
# MAGIC val forceCsv  = dbutils.widgets.get("force_process_days").trim
# MAGIC val forcedDays: Set[String] =
# MAGIC   if (forceCsv.isEmpty) Set.empty else forceCsv.split(",").map(_.trim).filter(_.nonEmpty).toSet
# MAGIC
# MAGIC // Auto-mode = yesterday + 1-day backfill; manual if both dates provided
# MAGIC val (startDate, endDate, mode) =
# MAGIC   if (sIn.nonEmpty && eIn.nonEmpty) {
# MAGIC     (LocalDate.parse(sIn, fmt), LocalDate.parse(eIn, fmt), "manual-range")
# MAGIC   } else {
# MAGIC     val y  = LocalDate.now(ZoneOffset.UTC).minusDays(1)
# MAGIC     val bf = y.minusDays(1)
# MAGIC     (bf, y, "auto-yesterday+backfill")
# MAGIC   }
# MAGIC
# MAGIC // Build requested days (inclusive)
# MAGIC val requestedDays: Seq[String] =
# MAGIC   (0L to ChronoUnit.DAYS.between(startDate, endDate)).map(i => startDate.plusDays(i).format(fmt))
# MAGIC
# MAGIC println(s"Mode: $mode | start=$startDate | end=$endDate")
# MAGIC println(s"Days requested: ${requestedDays.mkString(", ")}")
# MAGIC if (forcedDays.nonEmpty) println(s"Force process days: ${forcedDays.mkString(", ")}")
# MAGIC
# MAGIC // Figure out which requested days already exist and how many rows they have
# MAGIC val tableExists = spark.catalog.tableExists(fullTableName)
# MAGIC
# MAGIC val existingCounts: Map[String, Long] =
# MAGIC   if (tableExists && requestedDays.nonEmpty)
# MAGIC     spark.sql(
# MAGIC       s"""
# MAGIC          |SELECT date_format(day,'yyyy-MM-dd') AS day_str, COUNT(*) AS c
# MAGIC          |FROM $fullTableName
# MAGIC          |WHERE day IN (${requestedDays.map(d => s"'$d'").mkString(", ")})
# MAGIC          |GROUP BY day_str
# MAGIC        """.stripMargin
# MAGIC     ).collect().map(r => r.getString(0) -> r.getLong(1)).toMap
# MAGIC   else Map.empty[String, Long]
# MAGIC
# MAGIC // Decide which days to process:
# MAGIC // - Not present at all
# MAGIC // - Present but count < minRows (auto-fill partial day)
# MAGIC // - Forced explicitly
# MAGIC val (present, missing) = requestedDays.partition(d => existingCounts.contains(d))
# MAGIC val partial = present.filter(d => existingCounts.getOrElse(d, 0L) < minRows)
# MAGIC val toProcess = (missing ++ partial ++ forcedDays).distinct.filter(requestedDays.toSet)
# MAGIC
# MAGIC // For clarity, compute what we’re skipping
# MAGIC val fullyComplete = present.toSet -- partial.toSet -- forcedDays
# MAGIC val skipped = fullyComplete.toSeq.sorted
# MAGIC
# MAGIC println(s"🔎 Existing counts: ${existingCounts.toSeq.sortBy(_._1).map{case(d,c)=>s"$d:$c"}.mkString(", ")}")
# MAGIC if (partial.nonEmpty) println(s"♻️ Will reprocess partial days (< $minRows rows): ${partial.mkString(", ")}")
# MAGIC if (missing.nonEmpty) println(s"🆕 Will process new days: ${missing.mkString(", ")}")
# MAGIC if (forcedDays.nonEmpty) println(s"🔁 Will force reprocess: ${forcedDays.mkString(", ")}")
# MAGIC if (skipped.nonEmpty) println(s"⏭ Skipping complete days: ${skipped.mkString(", ")}")
# MAGIC
# MAGIC println(s"✅ Days to actually process: ${toProcess.mkString(", ")}")
# MAGIC
# MAGIC // Keep for later cells
# MAGIC val daysToProcessBC = toProcess

# COMMAND ----------

# MAGIC %scala
# MAGIC // Lists only days that exist in GCS so we don’t error on missing folders
# MAGIC import scala.collection.mutable.ArrayBuffer
# MAGIC case class DayPath(day: String, path: String)
# MAGIC
# MAGIC val dayPaths = ArrayBuffer[DayPath]()
# MAGIC daysToProcessBC.foreach { d =>
# MAGIC   val checkPath = s"$baseGcsPath/day=$d/"
# MAGIC   try {
# MAGIC     dbutils.fs.ls(checkPath) // exists
# MAGIC     dayPaths += DayPath(d, s"${checkPath}*/*")
# MAGIC   } catch {
# MAGIC     case _: Throwable => println(s"Missing or inaccessible: $checkPath")
# MAGIC   }
# MAGIC }
# MAGIC
# MAGIC if (dayPaths.isEmpty) {
# MAGIC   println("No valid day paths found. Exiting."); dbutils.notebook.exit("NO_DATA")
# MAGIC } else {
# MAGIC   println("Paths to load:"); dayPaths.foreach(dp => println(s"${dp.day} -> ${dp.path}"))
# MAGIC }

# COMMAND ----------

# MAGIC %scala
# MAGIC // Create once if missing (partitioned by day)
# MAGIC spark.sql(s"""
# MAGIC CREATE TABLE IF NOT EXISTS $fullTableName (
# MAGIC   day DATE,
# MAGIC   creativeId STRING,
# MAGIC   adSize STRING,
# MAGIC   type STRING,
# MAGIC   markup STRING
# MAGIC )
# MAGIC USING DELTA
# MAGIC PARTITIONED BY (day)
# MAGIC """)

# COMMAND ----------

# MAGIC %scala
# MAGIC // Cell 4 — per-day read → aggregate → append only if creativeId has < 3 rows in persistent
# MAGIC
# MAGIC import org.apache.spark.sql.functions._
# MAGIC import scala.collection.mutable.ArrayBuffer
# MAGIC
# MAGIC case class DayPath(day: String, path: String)
# MAGIC
# MAGIC // Build day paths from daysToProcessBC
# MAGIC val localDayPaths: Seq[DayPath] = {
# MAGIC   val buf = ArrayBuffer[DayPath]()
# MAGIC   daysToProcessBC.foreach { d =>
# MAGIC     val checkPath = s"$baseGcsPath/day=$d/"
# MAGIC     try {
# MAGIC       dbutils.fs.ls(checkPath) // exists
# MAGIC       buf += DayPath(d, s"${checkPath}*/*")
# MAGIC     } catch {
# MAGIC       case _: Throwable => println(s"Missing or inaccessible: $checkPath")
# MAGIC     }
# MAGIC   }
# MAGIC   buf.toSeq
# MAGIC }
# MAGIC
# MAGIC if (localDayPaths.isEmpty) {
# MAGIC   println("No valid GCS paths to process. Exiting."); dbutils.notebook.exit("NO_DATA")
# MAGIC }
# MAGIC
# MAGIC val wroteDays   = ArrayBuffer[String]()
# MAGIC val skippedDays = ArrayBuffer[String]()
# MAGIC val emptyDays   = ArrayBuffer[String]()
# MAGIC
# MAGIC val threshold = 3 // <-- change if you want a different cap
# MAGIC
# MAGIC localDayPaths.groupBy(_.day).foreach { case (day, entries) =>
# MAGIC   val paths = entries.map(_.path)
# MAGIC   println(s"\n=== Processing day=$day ===")
# MAGIC
# MAGIC   val df = spark.read
# MAGIC     .option("basePath", baseGcsPath.stripSuffix("/"))
# MAGIC     .json(paths: _*)
# MAGIC     .select("creativeId", "adSize", "unitDisplayType", "markup")
# MAGIC
# MAGIC   if (df.head(1).isEmpty) {
# MAGIC     println(s"No records for day=$day; skipping.")
# MAGIC     emptyDays += day
# MAGIC   } else {
# MAGIC     // Aggregate GCS for this day into target shape
# MAGIC     val aggregated = df
# MAGIC       .groupBy(col("creativeId"), col("adSize"), col("unitDisplayType"))
# MAGIC       .agg(min(col("markup")).as("markup"))
# MAGIC       .selectExpr(s"DATE('$day') AS day",
# MAGIC                   "creativeId",
# MAGIC                   "adSize",
# MAGIC                   "unitDisplayType AS type",
# MAGIC                   "markup")
# MAGIC
# MAGIC     if (aggregated.head(1).isEmpty) {
# MAGIC       println(s"No aggregated rows for day=$day; skipping.")
# MAGIC       emptyDays += day
# MAGIC     } else {
# MAGIC       // Running count in persistent table per creativeId
# MAGIC       val withRunningCnt =
# MAGIC         if (spark.catalog.tableExists(fullTableName)) {
# MAGIC           val counts = spark.table(fullTableName)
# MAGIC             .groupBy("creativeId")
# MAGIC             .count()
# MAGIC             .withColumnRenamed("count", "persist_cnt")
# MAGIC
# MAGIC           aggregated
# MAGIC             .join(counts, Seq("creativeId"), "left")
# MAGIC             .na.fill(0, Seq("persist_cnt"))
# MAGIC         } else {
# MAGIC           aggregated.withColumn("persist_cnt", lit(0))
# MAGIC         }
# MAGIC
# MAGIC       // Keep only rows for creativeIds that currently have < threshold rows overall in persistent
# MAGIC       val candidates = withRunningCnt
# MAGIC         .filter(col("persist_cnt") < threshold)
# MAGIC         .drop("persist_cnt")
# MAGIC
# MAGIC       if (candidates.head(1).isEmpty) {
# MAGIC         println(s"All creativeIds already at or above threshold ($threshold) — skipping day=$day.")
# MAGIC         skippedDays += day
# MAGIC       } else {
# MAGIC         // Also avoid inserting duplicates for the same day (idempotent)
# MAGIC         val existingForDay =
# MAGIC           if (spark.catalog.tableExists(fullTableName))
# MAGIC             spark.table(fullTableName)
# MAGIC               .where(s"day = DATE '$day'")
# MAGIC               .select("day","creativeId","adSize","type")
# MAGIC           else spark.emptyDataFrame
# MAGIC
# MAGIC         val toInsert = candidates
# MAGIC           .join(existingForDay, Seq("day","creativeId","adSize","type"), "left_anti")
# MAGIC
# MAGIC         if (toInsert.head(1).isEmpty) {
# MAGIC           println(s"No new rows to insert for day=$day after duplicate check.")
# MAGIC           skippedDays += day
# MAGIC         } else {
# MAGIC           toInsert
# MAGIC             .write
# MAGIC             .format("delta")
# MAGIC             .mode("append")   // <-- append, not overwrite
# MAGIC             .saveAsTable(fullTableName)
# MAGIC
# MAGIC           println(s"Inserted ${toInsert.count()} rows for day=$day into $fullTableName")
# MAGIC           wroteDays += day
# MAGIC         }
# MAGIC       }
# MAGIC     }
# MAGIC   }
# MAGIC }
# MAGIC
# MAGIC // Recap
# MAGIC println("\n📊 Recap:")
# MAGIC if (wroteDays.nonEmpty)   println(s"   ✅ Appended days: ${wroteDays.sorted.mkString(", ")}")
# MAGIC if (skippedDays.nonEmpty) println(s"   ⏭ Skipped days (no candidates or all at threshold): ${skippedDays.sorted.mkString(", ")}")
# MAGIC if (emptyDays.nonEmpty)   println(s"   💤 No data in GCS: ${emptyDays.sorted.mkString(", ")}")

# COMMAND ----------

# MAGIC %scala
# MAGIC import java.time.{LocalDate, ZoneOffset}
# MAGIC import java.time.format.DateTimeFormatter
# MAGIC
# MAGIC val cutoff = LocalDate.now(ZoneOffset.UTC).minusDays(keepDays.toLong).format(fmt)
# MAGIC println(s"\n🧹 Retention: keeping last $keepDays days (cutoff = $cutoff). Deleting older rows…")
# MAGIC spark.sql(s"DELETE FROM $fullTableName WHERE day < DATE '$cutoff'")
# MAGIC println("✅ Retention cleanup complete.")
# MAGIC

# COMMAND ----------

