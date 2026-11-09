"""Recompute the story metrics from the raw CSV extracts using the same rules as the gold layer.

Usage: python scripts/local_story_check.py /tmp/rcc_out
"""
import sys

import pandas as pd

d = sys.argv[1]
enc = pd.read_csv(f"{d}/encounters.csv", parse_dates=["admit_ts", "discharge_ts"]).drop_duplicates("encounter_id")
enc = enc[enc.discharge_ts >= enc.admit_ts]
dx = pd.read_csv(f"{d}/icd10_hrrp_map.csv")
fu = pd.read_csv(f"{d}/followup_appointments.csv", parse_dates=["appointment_ts", "booked_ts"])
ref = pd.read_csv(f"{d}/cms_hrrp_reference.csv")
gt = pd.read_csv(f"{d}/_ground_truth.csv")
AS_OF = pd.Timestamp("2026-11-08")

enc = enc.merge(dx[["icd10_code", "hrrp_condition"]], left_on="principal_dx_code", right_on="icd10_code", how="left")
enc = enc.sort_values(["patient_id", "admit_ts"])
enc["prev_discharge"] = enc.groupby("patient_id").discharge_ts.shift()
enc["next_admit"] = enc.groupby("patient_id").admit_ts.shift(-1)
enc["is_readmission"] = (enc.admit_ts - enc.prev_discharge).dt.total_seconds().between(0, 30 * 86400)
idx = enc[~enc.discharge_disposition.isin(["EXPIRED", "AMA"]) & ~enc.is_readmission].copy()
idx["readmit_30d"] = (idx.next_admit - idx.discharge_ts).dt.total_seconds().between(0, 30 * 86400)
idx["condition"] = idx.hrrp_condition.fillna("OTHER")
idx = idx.merge(gt[["encounter_id", "lives_alone"]], on="encounter_id", how="left").reset_index(drop=True)
idx["lives_alone"] = idx.lives_alone.fillna(False).astype(bool)
d0 = idx.discharge_ts.dt.normalize()
idx["weekend"] = idx.discharge_ts.dt.dayofweek >= 4
f7 = fu.merge(idx[["encounter_id", "discharge_ts"]], on="encounter_id")
f7 = f7[(f7.booked_ts <= f7.discharge_ts) & (f7.appointment_ts <= f7.discharge_ts.dt.normalize() + pd.Timedelta(days=8))]
idx["fu7"] = idx.encounter_id.isin(f7.encounter_id)

def pct(s):
    return round(100 * s.mean(), 1), len(s)

prior = (d0 >= "2025-12-29") & (d0 <= "2026-05-17")
last = (d0 >= "2026-05-18") & (d0 <= "2026-10-04")
t12 = (d0 >= "2025-10-05") & (d0 <= "2026-10-04")
hf = idx.condition == "HF"
sixn = idx.unit_id == "CUMC-6N"
print("6N HF prior20 / last20:", pct(idx[sixn & hf & prior].readmit_30d), pct(idx[sixn & hf & last].readmit_30d))
u = idx.assign(p=prior, l=last)
tab = pd.DataFrame({"prior": u[u.p].groupby("unit_id").readmit_30d.mean() * 100,
                    "last": u[u.l].groupby("unit_id").readmit_30d.mean() * 100})
tab["delta"] = tab["last"] - tab["prior"]
print(tab.round(1).sort_values("delta"))
post = sixn & hf & (d0 >= "2026-06-19")
print("6N HF since 06-19 FU7 weekend / weekday:", pct(idx[post & idx.weekend].fu7), pct(idx[post & ~idx.weekend].fu7))
print("HF 12m all: noFU / FU:", pct(idx[hf & t12 & ~idx.fu7].readmit_30d), pct(idx[hf & t12 & idx.fu7].readmit_30d))
print("HF 12m all: LA / noLA:", pct(idx[hf & t12 & idx.lives_alone].readmit_30d), pct(idx[hf & t12 & ~idx.lives_alone].readmit_30d))

# HRRP
c12 = idx[t12 & (idx.condition != "OTHER")]
obs = c12.groupby(["hospital_id", "condition"]).agg(n=("readmit_30d", "size"), k=("readmit_30d", "sum")).reset_index()
h = obs.merge(ref, left_on=["hospital_id", "condition"], right_on=["hospital_id", "hrrp_condition"])
h["err"] = (h.k / h.n) / h.expected_readmission_rate
h["line"] = h.base_op_drg_payments_condition * (h.err - 1).clip(lower=0) * h.neutrality_modifier
print(h[["hospital_id", "condition", "n", "k", "err", "line"]].round(3).to_string())
for hid, g in h.groupby("hospital_id"):
    cap = g.total_base_op_drg_payments.iloc[0] * g.penalty_cap.iloc[0]
    print(hid, "uncapped", round(g.line.sum()), "penalty", round(min(cap, g.line.sum())))

# what-if
r_no = idx[hf & t12 & ~idx.fu7].readmit_30d.mean(); r_fu = idx[hf & t12 & idx.fu7].readmit_30d.mean()
w = idx[sixn & hf & t12 & idx.weekend]
conv = max(0, 0.80 * len(w) - w.fu7.sum())
avoided = conv * (r_no - r_fu)
cumc = h[h.hospital_id == "CUMC"].copy()
hfrow = cumc.condition == "HF"
k_new = cumc.loc[hfrow, "k"].iloc[0] - avoided
cumc.loc[hfrow, "err"] = (k_new / cumc.loc[hfrow, "n"].iloc[0]) / cumc.loc[hfrow, "expected_readmission_rate"].iloc[0]
cumc["line2"] = cumc.base_op_drg_payments_condition * (cumc.err - 1).clip(lower=0)
cap = cumc.total_base_op_drg_payments.iloc[0] * 0.03
before = min(cap, h[h.hospital_id == "CUMC"].line.sum()); after = min(cap, cumc.line2.sum())
print(f"what-if: weekend N={len(w)} booked={w.fu7.sum()} converted={conv:.1f} avoided={avoided:.2f} "
      f"ERR->{cumc.loc[hfrow,'err'].iloc[0]:.3f} saved=${before-after:,.0f}")
