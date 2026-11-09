-- =====================================================================
-- SILVER: typed, de-duplicated, quality-checked records + AI-extracted
-- signals from discharge-note free text.
-- =====================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.encounters (
  CONSTRAINT encounter_id_present EXPECT (encounter_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT patient_id_present EXPECT (patient_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT discharge_after_admit EXPECT (discharge_ts >= admit_ts) ON VIOLATION DROP ROW,
  CONSTRAINT unit_present EXPECT (unit_id IS NOT NULL)
)
COMMENT 'Inpatient encounters: typed, de-duplicated on encounter_id, invalid timestamps dropped.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT
  encounter_id, patient_id, hospital_id, unit_id,
  CAST(admit_ts AS TIMESTAMP) AS admit_ts,
  CAST(discharge_ts AS TIMESTAMP) AS discharge_ts,
  CAST(los_days AS INT) AS los_days,
  principal_dx_code, principal_dx_desc,
  CAST(drg_code AS STRING) AS drg_code,
  admission_source, discharge_disposition, payer,
  CAST(prior_admissions_12m AS INT) AS prior_admissions_12m,
  coalesce(comorbidities, '') AS comorbidities,
  CASE WHEN coalesce(comorbidities, '') = '' THEN 0 ELSE size(split(comorbidities, '\\|')) END AS comorbidity_count,
  encounter_type
FROM ${catalog}.bronze.encounters
QUALIFY row_number() OVER (PARTITION BY encounter_id ORDER BY _ingest_ts DESC, _source_file DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.patients (
  patient_id STRING,
  mrn STRING MASK ${catalog}.gold.mask_phi COMMENT 'Medical record number (PHI)',
  first_name STRING MASK ${catalog}.gold.mask_phi COMMENT 'PHI',
  last_name STRING MASK ${catalog}.gold.mask_phi COMMENT 'PHI',
  date_of_birth DATE MASK ${catalog}.gold.mask_phi_date COMMENT 'PHI',
  sex STRING,
  zip_code STRING,
  primary_language STRING,
  home_phone STRING MASK ${catalog}.gold.mask_phi COMMENT 'PHI',
  CONSTRAINT patient_id_present EXPECT (patient_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Patient demographics. PHI columns carry UC column masks (gold.mask_phi*).'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT patient_id, mrn, first_name, last_name, CAST(date_of_birth AS DATE) AS date_of_birth,
          sex, CAST(zip_code AS STRING) AS zip_code, primary_language, home_phone
FROM ${catalog}.bronze.patients
QUALIFY row_number() OVER (PARTITION BY patient_id ORDER BY _ingest_ts DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.followup_appointments (
  CONSTRAINT appointment_has_encounter EXPECT (encounter_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Post-discharge follow-up appointments with booking timestamp.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT appointment_id, encounter_id, patient_id, clinic_name,
          CAST(appointment_ts AS TIMESTAMP) AS appointment_ts,
          CAST(booked_ts AS TIMESTAMP) AS booked_ts, status
FROM ${catalog}.bronze.followup_appointments;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.hospitals
TBLPROPERTIES ('quality' = 'silver')
AS SELECT hospital_id, hospital_name, CAST(beds AS INT) AS beds, CAST(cms_ccn AS STRING) AS cms_ccn, hospital_type
FROM ${catalog}.bronze.hospitals;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.units
TBLPROPERTIES ('quality' = 'silver')
AS SELECT unit_id, hospital_id, unit_name, service_line FROM ${catalog}.bronze.units;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.icd10_hrrp_map
TBLPROPERTIES ('quality' = 'silver')
AS SELECT icd10_code, description, CAST(drg_code AS STRING) AS drg_code,
          nullif(hrrp_condition, '') AS hrrp_condition
FROM ${catalog}.bronze.icd10_hrrp_map;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.staffing_events
TBLPROPERTIES ('quality' = 'silver')
AS SELECT event_id, scope_id, CAST(event_date AS DATE) AS event_date, event_type, description
FROM ${catalog}.bronze.staffing_events;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.cms_hrrp_reference (
  CONSTRAINT expected_rate_valid EXPECT (expected_readmission_rate > 0 AND expected_readmission_rate < 1) ON VIOLATION FAIL UPDATE
)
TBLPROPERTIES ('quality' = 'silver')
AS SELECT hospital_id, hrrp_condition,
          CAST(expected_readmission_rate AS DOUBLE) AS expected_readmission_rate,
          CAST(base_op_drg_payments_condition AS DOUBLE) AS base_op_drg_payments_condition,
          CAST(total_base_op_drg_payments AS DOUBLE) AS total_base_op_drg_payments,
          CAST(neutrality_modifier AS DOUBLE) AS neutrality_modifier,
          CAST(penalty_cap AS DOUBLE) AS penalty_cap,
          program_year, CAST(performance_start AS DATE) AS performance_start,
          CAST(performance_end AS DATE) AS performance_end
FROM ${catalog}.bronze.cms_hrrp_reference;

CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.discharge_notes (
  CONSTRAINT note_has_text EXPECT (note_text IS NOT NULL AND length(note_text) > 20) ON VIOLATION DROP ROW
)
COMMENT 'Discharge summary notes (free text, PHI-adjacent).'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT note_id, encounter_id, note_type, author_role, CAST(note_ts AS TIMESTAMP) AS note_ts, note_text
FROM STREAM(${catalog}.bronze.discharge_notes);

-- ---------------------------------------------------------------------
-- AI Functions: extract social-risk signals that only exist in free text.
-- Incremental: each note is sent to the model once.
-- ---------------------------------------------------------------------
CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.discharge_note_signals
COMMENT 'AI-extracted signals from discharge notes (ai_query, structured output): lives alone / no caregiver, transportation barrier, follow-up instruction type, supporting evidence quote.'
TBLPROPERTIES ('quality' = 'silver')
AS SELECT
  note_id, encounter_id, note_ts,
  s.lives_alone_no_caregiver AS ai_lives_alone,
  s.transportation_barrier AS ai_transport_barrier,
  s.followup_status AS ai_followup_status,
  s.evidence AS ai_evidence,
  ai_error,
  '${extraction_endpoint}' AS ai_model,
  current_timestamp() AS ai_extracted_ts
FROM (
  SELECT note_id, encounter_id, note_ts,
         from_json(r.result, 'lives_alone_no_caregiver BOOLEAN, transportation_barrier BOOLEAN, followup_status STRING, evidence STRING') AS s,
         r.errorMessage AS ai_error
  FROM (
    SELECT note_id, encounter_id, note_ts,
      ai_query(
        '${extraction_endpoint}',
        concat(
          'You read hospital discharge notes and extract social risk factors. ',
          'Set lives_alone_no_caregiver=true only if the note says the patient lives alone or has no caregiver / no one at home to help. ',
          'Set transportation_barrier=true only if the note says the patient lacks reliable transportation or does not drive. ',
          'followup_status must be one of: booked_appointment (a specific follow-up appointment date is scheduled), ',
          'patient_to_call (patient is told to call or schedule follow-up themselves), none (anything else). ',
          'evidence: the shortest verbatim quote supporting the social risk factors (empty if none). NOTE:\n',
          note_text),
        responseFormat => 'STRUCT<signals:STRUCT<lives_alone_no_caregiver:BOOLEAN, transportation_barrier:BOOLEAN, followup_status:STRING, evidence:STRING>>',
        failOnError => false
      ) AS r
    FROM STREAM(${catalog}.silver.discharge_notes)
  )
);
