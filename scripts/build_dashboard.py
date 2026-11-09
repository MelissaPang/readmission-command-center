"""Generate the AI/BI (Lakeview) dashboard definition: dashboards/readmissions_hrrp_executive.lvdash.json"""
import json
import sys

CAT = sys.argv[1] if len(sys.argv) > 1 else "cedarbrook_rcc"
G = f"{CAT}.gold"
datasets = {
    "ds_kpi": f"""SELECT h.estimated_penalty, h.largest_condition_contribution AS hf_line, h.largest_condition_err AS hf_err,
  u.last_20w_rate_pct AS sixn_last20, u.prior_20w_rate_pct AS sixn_prior20
FROM {G}.hrrp_hospital_penalty h CROSS JOIN {G}.unit_period_summary u
WHERE h.hospital_id = 'CUMC' AND u.unit_id = 'CUMC-6N' AND u.condition = 'HF'""",
    "ds_units": f"SELECT concat(unit_name, ' (', hospital_id, ')') AS unit, delta_pts, prior_20w_rate_pct, last_20w_rate_pct FROM {G}.unit_period_summary WHERE condition = 'ALL'",
    "ds_weekly": f"""SELECT discharge_week, CASE WHEN unit_id = 'CUMC-6N' THEN '6 North Telemetry' ELSE 'All other units' END AS unit_group,
  sum(readmissions) AS readmissions, sum(index_admissions) AS index_admissions,
  round(100 * sum(readmissions) / sum(index_admissions), 1) AS readmit_rate_pct
FROM {G}.unit_weekly_readmissions WHERE condition = 'HF' AND discharge_week >= '2025-12-29' GROUP BY ALL""",
    "ds_gap": f"SELECT discharge_day_type, period, fu7_booked_pct, discharges FROM {G}.followup_gap WHERE unit_id = 'CUMC-6N' AND condition = 'HF'",
    "ds_penalty": f"SELECT hospital_id, hrrp_condition, err, penalty_contribution, observed_rate, expected_readmission_rate, index_admissions, readmissions FROM {G}.hrrp_condition_err",
    "ds_whatif": f"SELECT fu7_target_pct, readmissions_avoided, penalty_saved, hf_err_scenario FROM {G}.hrrp_whatif WHERE scope = '6N weekend HF'",
    "ds_factors": f"""SELECT concat(factor, ' = ', value) AS factor_value, readmit_rate_pct, index_admissions
FROM {G}.readmission_risk_factors WHERE condition = 'HF' AND factor IN ('fu7_booked', 'ai_lives_alone', 'ai_transport_barrier')""",
    "ds_tiers": f"""SELECT risk_tier, count(*) AS index_admissions, round(100 * avg(CAST(readmit_30d AS INT)), 1) AS observed_readmit_pct
FROM {G}.patient_risk_scores WHERE outcome_complete GROUP BY risk_tier""",
}
W = []


def fld(name, expr=None):
    return {"name": name, "expression": expr or f"`{name}`"}


def widget(name, ds, fields, spec, pos, disagg=False):
    W.append({"widget": {"name": name, "queries": [{"name": "main_query", "query": {"datasetName": ds, "fields": fields, "disaggregated": disagg}}],
                         "spec": spec}, "position": pos})


def counter(name, ds, col, title, x):
    widget(name, ds, [fld(col)], {"version": 2, "widgetType": "counter", "encodings": {"value": {"fieldName": col, "displayName": title}},
                                  "frame": {"showTitle": True, "title": title}}, {"x": x, "y": 1, "width": 1, "height": 2}, disagg=True)


def chart(name, ds, kind, x, y, title, pos, color=None, xscale="categorical", fields=None, extra=None):
    enc = {"x": {"fieldName": x, "scale": {"type": xscale}, "displayName": x}, "y": {"fieldName": y, "scale": {"type": "quantitative"}, "displayName": y}}
    f = fields or [fld(x), fld(y)]
    if color:
        enc["color"] = {"fieldName": color, "scale": {"type": "categorical"}, "displayName": color}
        if not fields:
            f.append(fld(color))
    spec = {"version": 3, "widgetType": kind, "encodings": enc, "frame": {"showTitle": True, "title": title}}
    spec.update(extra or {})
    widget(name, ds, f, spec, pos, disagg=True)


W.append({"widget": {"name": "hdr", "multilineTextboxSpec": {"lines": [
    "# Readmissions & HRRP: Cedarbrook Health (synthetic)\n",
    "6 North heart-failure readmissions rose after the unit lost its weekend transitions pharmacist (2026-06-19) and the HF Bridge Clinic stopped offering Friday afternoon slots (2026-06-26). "
    "Weekend discharges now leave without a booked 7-day follow-up. Heart failure is the largest line of CUMC's HRRP penalty."]}},
    "position": {"x": 0, "y": 0, "width": 6, "height": 1}})
counter("k1", "ds_kpi", "estimated_penalty", "CUMC est. HRRP penalty ($, 3% cap)", 0)
counter("k2", "ds_kpi", "hf_line", "Heart-failure penalty line ($)", 1)
counter("k3", "ds_kpi", "hf_err", "CUMC HF excess readmission ratio", 2)
counter("k4", "ds_kpi", "sixn_prior20", "6N HF readmit %, prior 20 weeks", 3)
counter("k5", "ds_kpi", "sixn_last20", "6N HF readmit %, last 20 weeks", 4)
widget("k6", "ds_whatif", [fld("penalty_saved")], {"version": 2, "widgetType": "counter",
       "encodings": {"value": {"fieldName": "penalty_saved", "displayName": "Saved at 80% weekend follow-up ($)"}},
       "frame": {"showTitle": True, "title": "Penalty saved if 6N books 80% of weekend HF follow-ups ($)"}},
       {"x": 5, "y": 1, "width": 1, "height": 2}, disagg=True)
# k6 filtered to the 80% row via dataset-level SQL variant
datasets["ds_whatif80"] = datasets["ds_whatif"] + " AND fu7_target_pct = 80"
W[-1]["widget"]["queries"][0]["query"]["datasetName"] = "ds_whatif80"

chart("c_weekly", "ds_weekly", "line", "discharge_week", "readmit_rate_pct", "Weekly HF 30-day readmission rate: 6 North vs all other units",
      {"x": 0, "y": 3, "width": 4, "height": 5}, color="unit_group", xscale="temporal")
chart("c_gap", "ds_gap", "bar", "period", "fu7_booked_pct", "6 North HF: % discharged with a booked 7-day follow-up",
      {"x": 4, "y": 3, "width": 2, "height": 5}, color="discharge_day_type", extra={"mark": {"layout": "group"}})
chart("c_units", "ds_units", "bar", "unit", "delta_pts", "Change in all-cause readmission rate, last 20 vs prior 20 weeks (pts)",
      {"x": 0, "y": 8, "width": 3, "height": 6})
chart("c_pen", "ds_penalty", "bar", "hrrp_condition", "penalty_contribution", "HRRP penalty contribution by condition ($)",
      {"x": 3, "y": 8, "width": 3, "height": 6}, color="hospital_id")
chart("c_whatif", "ds_whatif", "line", "fu7_target_pct", "penalty_saved", "What-if: penalty saved vs 6N weekend follow-up booking target (%)",
      {"x": 0, "y": 14, "width": 3, "height": 5}, xscale="quantitative")
chart("c_factors", "ds_factors", "bar", "factor_value", "readmit_rate_pct", "HF 30-day readmission % by risk factor (trailing 12m; AI = from note text)",
      {"x": 3, "y": 14, "width": 3, "height": 5})
chart("c_tiers", "ds_tiers", "bar", "risk_tier", "observed_readmit_pct", "Model risk tier vs observed readmission %",
      {"x": 0, "y": 19, "width": 3, "height": 5})
widget("t_err", "ds_penalty", [fld(c) for c in ["hospital_id", "hrrp_condition", "index_admissions", "readmissions", "observed_rate",
                                                "expected_readmission_rate", "err", "penalty_contribution"]],
       {"version": 1, "widgetType": "table", "encodings": {"columns": [{"fieldName": c, "displayName": c} for c in
        ["hospital_id", "hrrp_condition", "index_admissions", "readmissions", "observed_rate", "expected_readmission_rate", "err", "penalty_contribution"]]},
        "frame": {"showTitle": True, "title": "Excess readmission ratio by hospital and condition"}},
       {"x": 3, "y": 19, "width": 3, "height": 5}, disagg=True)

dash = {"datasets": [{"name": k, "displayName": k, "queryLines": [v]} for k, v in datasets.items()],
        "pages": [{"name": "overview", "displayName": "Readmissions & HRRP", "layout": W, "pageType": "PAGE_TYPE_CANVAS"}]}
out = "dashboards/readmissions_hrrp_executive.lvdash.json"
json.dump(dash, open(out, "w"), indent=2)
print("wrote", out, "with", len(W), "widgets and", len(datasets), "datasets")
