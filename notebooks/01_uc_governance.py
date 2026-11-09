# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Unity Catalog governance (before ingest)
# MAGIC
# MAGIC Creates the governance objects the pipeline needs **before** it runs:
# MAGIC
# MAGIC * `gold.rcc_user_entitlements`: maps principals to a role (`care_transitions`, `finance_quality`, `analyst`) and hospital scope.
# MAGIC   In production this would be account groups. This prototype runs in a shared demo workspace where we can't create
# MAGIC   account groups, so entitlements are data-driven instead.
# MAGIC * Column-mask functions `gold.mask_phi` (STRING) and `gold.mask_phi_date` (DATE). The Lakeflow pipeline attaches them to the
# MAGIC   PHI columns of `silver.patients` (`MASK` clause), so only `care_transitions` principals see names, MRN, DOB and phone.
# MAGIC * Role-based column mask `gold.mask_clinical_text` for AI-extracted evidence quotes (verbatim snippets of clinical notes). Only `care_transitions` sees them; analysts, finance and Genie see a placeholder.
# MAGIC * Row-filter function `gold.hospital_scope` restricts patient-level gold tables to the hospitals a principal may see.
# MAGIC * Governance tags on catalog and schemas.

# COMMAND ----------

dbutils.widgets.text("catalog", "cedarbrook_rcc")
catalog = dbutils.widgets.get("catalog")
me = spark.sql("SELECT current_user()").first()[0]
print("catalog:", catalog, "| running as:", me)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog}.gold.rcc_user_entitlements (
  principal STRING COMMENT 'User email or service principal application id',
  role STRING COMMENT 'care_transitions | finance_quality | analyst',
  hospital_scope STRING COMMENT 'hospital_id or * for all hospitals'
) COMMENT 'Data-driven entitlements used by UC column masks and row filters (stand-in for account groups).'
""")
spark.sql(f"""
MERGE INTO {catalog}.gold.rcc_user_entitlements t
USING (SELECT '{me}' AS principal, 'care_transitions' AS role, '*' AS hospital_scope) s
ON t.principal = s.principal AND t.role = s.role
WHEN NOT MATCHED THEN INSERT *
""")
display(spark.table(f"{catalog}.gold.rcc_user_entitlements"))

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.mask_phi(v STRING)
RETURNS STRING
COMMENT 'Column mask: PHI is visible only to care_transitions principals.'
RETURN CASE WHEN EXISTS (SELECT 1 FROM {catalog}.gold.rcc_user_entitlements e
                         WHERE e.principal = current_user() AND e.role = 'care_transitions')
            THEN v ELSE '***MASKED***' END
""")
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.mask_phi_date(v DATE)
RETURNS DATE
COMMENT 'Column mask for PHI dates: non care_transitions principals see only Jan 1 of the year.'
RETURN CASE WHEN EXISTS (SELECT 1 FROM {catalog}.gold.rcc_user_entitlements e
                         WHERE e.principal = current_user() AND e.role = 'care_transitions')
            THEN v ELSE make_date(year(v), 1, 1) END
""")
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.mask_clinical_text(v STRING)
RETURNS STRING
COMMENT 'Role-based column mask for AI-extracted free-text evidence quotes from clinical notes: only care_transitions principals see the quote; everyone else (analysts, finance, the app SP used by Genie) sees a placeholder.'
RETURN CASE WHEN v IS NULL THEN NULL
            WHEN EXISTS (SELECT 1 FROM {catalog}.gold.rcc_user_entitlements e
                         WHERE e.principal = current_user() AND e.role = 'care_transitions')
            THEN v ELSE '[restricted: care-transitions only]' END
""")
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.gold.hospital_scope(hid STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: principals see patient-level rows only for hospitals in their entitlement scope.'
RETURN EXISTS (SELECT 1 FROM {catalog}.gold.rcc_user_entitlements e
               WHERE e.principal = current_user() AND (e.hospital_scope = '*' OR e.hospital_scope = hid))
""")
spark.sql(f"USE CATALOG {catalog}")
display(spark.sql("SHOW USER FUNCTIONS IN gold"))

# COMMAND ----------

spark.sql(f"ALTER CATALOG {catalog} SET TAGS ('data_classification' = 'RESTRICTED', 'rcc_synthetic_data' = 'true', 'rcc_owner_team' = 'care_transitions_analytics', 'rcc_solution' = 'readmission_command_center')")
for s, tier in [("raw", "landing"), ("bronze", "bronze"), ("silver", "silver"), ("gold", "gold"), ("ml", "ml")]:
    spark.sql(f"ALTER SCHEMA {catalog}.{s} SET TAGS ('rcc_medallion_tier' = '{tier}')")
display(spark.sql(f"SELECT schema_name, tag_name, tag_value FROM {catalog}.information_schema.schema_tags ORDER BY schema_name"))
