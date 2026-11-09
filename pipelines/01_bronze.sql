-- =====================================================================
-- BRONZE: raw EHR extracts landed in the UC volume, ingested incrementally
-- with Auto Loader (read_files in streaming mode). One table per source feed.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.encounters
COMMENT 'Raw ADT inpatient encounter extract (JSON lines, one file per discharge month). Includes source duplicates and defects on purpose.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/encounters', format => 'json');

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.discharge_notes
COMMENT 'Raw discharge summary notes (free text), JSON lines, one file per month.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/discharge_notes', format => 'json');

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.patients
COMMENT 'Raw patient demographics extract (contains PHI).'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/patients', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.followup_appointments
COMMENT 'Raw ambulatory scheduling extract: post-discharge follow-up appointments and when they were booked.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/followup_appointments', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.hospitals
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/hospitals', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.units
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/units', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.icd10_hrrp_map
COMMENT 'ICD-10 principal diagnosis to CMS HRRP condition cohort mapping.'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/icd10_hrrp_map', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.staffing_events
COMMENT 'Operational change log (staffing, clinic schedule, programs).'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/staffing_events', format => 'csv', header => true);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.cms_hrrp_reference
COMMENT 'CMS HRRP supplemental-file style reference: expected readmission rates and base operating DRG payments per hospital x condition (synthetic).'
TBLPROPERTIES ('quality' = 'bronze')
AS SELECT *, _metadata.file_path AS _source_file, current_timestamp() AS _ingest_ts
FROM STREAM read_files('${landing}/cms_hrrp_reference', format => 'csv', header => true);
