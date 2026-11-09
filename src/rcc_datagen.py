"""Synthetic data generator for the Cedarbrook Health Readmission Command Center.

Deterministic (seeded). Produces raw EHR-style extracts whose aggregates reproduce
the customer story exactly:

* CUMC 6 North HF 30-day readmission: 14.8% (prior 20 weeks) -> 23.9% (last 20 weeks);
  every other unit stays within ~1.5 pts (all-cause).
* Since 2026-06-19, 6 North Fri-Sun HF discharges: 18% leave with a booked 7-day
  follow-up vs 69% on weekdays.
* HF, trailing 12 months, all hospitals: no 7-day follow-up 29.8% vs with 16.4%.
* HF with "lives alone / no caregiver" (free text only): 33.1% vs 20.6%.
* CUMC HF ERR 1.19, HF line $1.14M of an estimated $1.62M HRRP penalty (3% cap);
  80% weekend follow-up what-if -> ~7 readmissions avoided, ERR 1.14, ~$240K saved.

Only numpy + pandas are required, so it runs locally and on Databricks serverless.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

SEED = 42
DATA_START = pd.Timestamp("2025-05-04")  # Sunday
AS_OF = pd.Timestamp("2026-11-08")  # extract date (Sunday)

# Analysis windows by discharge date (inclusive bounds)
WINDOWS = [
    ("W0", "2025-05-04", "2025-10-04"),  # history, outside trailing 12m
    ("W1", "2025-10-05", "2025-12-28"),  # trailing 12m, before prior-20w
    ("W2", "2025-12-29", "2026-05-17"),  # prior 20 weeks
    ("W3a", "2026-05-18", "2026-06-18"),  # last 20 weeks, before the staffing change
    ("W3b", "2026-06-19", "2026-10-04"),  # last 20 weeks, after the staffing change
    ("W4", "2026-10-05", "2026-11-08"),  # recent, 30-day outcome window still open
]
TRAILING_12M = ("W1", "W2", "W3a", "W3b")
CHANGE_DATE = pd.Timestamp("2026-06-19")

# ---- story targets -------------------------------------------------------
T_6N_PRIOR20 = 14.8
T_6N_LAST20 = 23.9
T_6N_W3A_RATE = 0.150
T_FU_WEEKEND_POST = 0.18
T_FU_WEEKDAY_POST = 0.69
T_FU_WEEKDAY_PRE = 0.71
T_HF_NOFU, T_HF_FU = 0.298, 0.164
T_HF_LA, T_HF_NOLA = 0.331, 0.206
T_WHATIF_FU_TARGET = 0.80
T_WHATIF_AVOID_FRACTION = 0.0421  # avoided / CUMC HF readmissions -> ERR 1.19 -> 1.14

HOSPITALS = [
    ("CUMC", "Cedarbrook University Medical Center", 538, "140321", "Academic"),
    ("FCH", "Fairhaven Community Hospital", 210, "140588", "Community"),
    ("PHMC", "Pine Hollow Medical Center", 165, "140712", "Community"),
]

UNITS = [
    # unit_id, hospital, unit_name, service_line
    ("CUMC-6N", "CUMC", "6 North Telemetry", "Cardiology"),
    ("CUMC-5E", "CUMC", "5 East Cardiology", "Cardiology"),
    ("CUMC-2W", "CUMC", "2 West Step-Down", "Critical Care"),
    ("CUMC-4S", "CUMC", "4 South Pulmonary", "Pulmonology"),
    ("CUMC-7W", "CUMC", "7 West Medicine", "Hospital Medicine"),
    ("CUMC-9N", "CUMC", "9 North General Medicine", "Hospital Medicine"),
    ("CUMC-3N", "CUMC", "3 North Orthopedics", "Orthopedics"),
    ("CUMC-8E", "CUMC", "8 East CV Surgery", "Cardiac Surgery"),
    ("FCH-2A", "FCH", "2A Medical", "Hospital Medicine"),
    ("FCH-2B", "FCH", "2B Surgical", "Surgery"),
    ("FCH-3A", "FCH", "3A Telemetry", "Cardiology"),
    ("FCH-3B", "FCH", "3B Orthopedics", "Orthopedics"),
    ("PHMC-MS1", "PHMC", "Med-Surg 1", "Hospital Medicine"),
    ("PHMC-MS2", "PHMC", "Med-Surg 2", "Surgery"),
    ("PHMC-TEL", "PHMC", "Telemetry", "Cardiology"),
    ("PHMC-ICU", "PHMC", "ICU / Step-Down", "Critical Care"),
]

# (unit, condition, weekly volume, base 30-day readmission rate)
VOLUMES = [
    ("CUMC-6N", "HF", 11.0, None),  # story unit, rates set explicitly
    ("CUMC-6N", "AMI", 3.0, 0.150),
    ("CUMC-6N", "OTHER", 6.0, 0.120),
    ("CUMC-5E", "HF", 3.0, 0.220),
    ("CUMC-5E", "AMI", 3.0, 0.145),
    ("CUMC-5E", "OTHER", 6.0, 0.115),
    ("CUMC-2W", "HF", 1.0, 0.220),
    ("CUMC-2W", "OTHER", 8.0, 0.140),
    ("CUMC-4S", "COPD", 6.0, 0.190),
    ("CUMC-4S", "PN", 2.0, 0.160),
    ("CUMC-4S", "OTHER", 4.0, 0.120),
    ("CUMC-7W", "COPD", 2.0, 0.190),
    ("CUMC-7W", "PN", 5.0, 0.160),
    ("CUMC-7W", "OTHER", 8.0, 0.130),
    ("CUMC-9N", "HF", 1.0, 0.220),
    ("CUMC-9N", "PN", 5.0, 0.165),
    ("CUMC-9N", "OTHER", 9.0, 0.130),
    ("CUMC-3N", "THA_TKA", 7.0, 0.045),
    ("CUMC-3N", "OTHER", 5.0, 0.070),
    ("CUMC-8E", "CABG", 3.0, 0.120),
    ("CUMC-8E", "OTHER", 4.0, 0.110),
    ("FCH-2A", "COPD", 3.0, 0.200),
    ("FCH-2A", "PN", 4.0, 0.170),
    ("FCH-2A", "OTHER", 8.0, 0.130),
    ("FCH-2B", "OTHER", 9.0, 0.080),
    ("FCH-3A", "HF", 5.0, None),  # community HF rate solved for story marginals
    ("FCH-3A", "AMI", 1.5, 0.160),
    ("FCH-3A", "OTHER", 5.0, 0.120),
    ("FCH-3B", "THA_TKA", 5.0, 0.050),
    ("FCH-3B", "OTHER", 3.0, 0.070),
    ("PHMC-MS1", "COPD", 3.0, 0.210),
    ("PHMC-MS1", "PN", 3.0, 0.170),
    ("PHMC-MS1", "OTHER", 7.0, 0.130),
    ("PHMC-MS2", "PN", 2.0, 0.170),
    ("PHMC-MS2", "THA_TKA", 2.0, 0.050),
    ("PHMC-MS2", "OTHER", 6.0, 0.080),
    ("PHMC-TEL", "HF", 4.0, None),
    ("PHMC-TEL", "AMI", 1.0, 0.160),
    ("PHMC-TEL", "OTHER", 4.0, 0.120),
    ("PHMC-ICU", "OTHER", 6.0, 0.150),
]

# ICD-10 principal diagnoses per condition (code, description, DRG)
DX = {
    "HF": [("I50.23", "Acute on chronic systolic heart failure", "291"),
           ("I50.33", "Acute on chronic diastolic heart failure", "291"),
           ("I50.43", "Acute on chronic combined systolic and diastolic heart failure", "291"),
           ("I11.0", "Hypertensive heart disease with heart failure", "292"),
           ("I13.0", "Hypertensive heart and CKD with heart failure", "292")],
    "AMI": [("I21.4", "Non-ST elevation myocardial infarction", "281"),
            ("I21.09", "STEMI involving other coronary artery of anterior wall", "280")],
    "COPD": [("J44.1", "COPD with acute exacerbation", "190"),
             ("J44.0", "COPD with acute lower respiratory infection", "191")],
    "PN": [("J18.9", "Pneumonia, unspecified organism", "193"),
           ("J15.9", "Unspecified bacterial pneumonia", "194")],
    "CABG": [("I25.10", "Atherosclerotic heart disease of native coronary artery (CABG)", "236")],
    "THA_TKA": [("M17.11", "Unilateral primary osteoarthritis, right knee (TKA)", "470"),
                ("M16.12", "Unilateral primary osteoarthritis, left hip (THA)", "470")],
    "OTHER": [("N39.0", "Urinary tract infection", "690"),
              ("A41.9", "Sepsis, unspecified organism", "871"),
              ("K92.2", "Gastrointestinal hemorrhage", "378"),
              ("E11.65", "Type 2 diabetes with hyperglycemia", "638"),
              ("I48.91", "Atrial fibrillation, unspecified", "309"),
              ("R55", "Syncope and collapse", "312"),
              ("K85.90", "Acute pancreatitis", "440"),
              ("L03.115", "Cellulitis of right lower limb", "603")],
}

# HRRP reference (CMS-style). Target ERRs + condition payments; expected rates are
# derived from the generated cohort so that observed/expected = target ERR.
HRRP_TARGETS = {
    "CUMC": {"total_base_payments": 54_000_000, "conditions": {
        "HF": (1.190, 6_000_000), "COPD": (1.080, 3_500_000), "PN": (1.050, 4_000_000),
        "CABG": (1.030, 2_000_000), "AMI": (0.970, 3_200_000), "THA_TKA": (0.940, 5_100_000)}},
    "FCH": {"total_base_payments": 21_500_000, "conditions": {
        "HF": (1.060, 2_400_000), "COPD": (1.040, 1_300_000), "PN": (0.990, 1_600_000),
        "AMI": (1.020, 700_000), "THA_TKA": (0.960, 1_900_000)}},
    "PHMC": {"total_base_payments": 16_800_000, "conditions": {
        "HF": (1.090, 1_900_000), "COPD": (1.050, 1_200_000), "PN": (1.010, 1_400_000),
        "AMI": (0.980, 500_000), "THA_TKA": (0.930, 600_000)}},
}
HRRP_CAP = 0.03

FIRST = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David",
         "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas",
         "Karen", "Charles", "Sarah", "Daniel", "Nancy", "Matthew", "Lisa", "Anthony", "Betty",
         "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley", "Paul", "Dorothy", "Andrew",
         "Kimberly", "Kenneth", "Emily", "George", "Donna", "Luis", "Rosa", "Wei", "Mei", "Arjun",
         "Anita", "Kwame", "Amara", "Diego", "Lucia", "Hiro", "Yuki", "Omar", "Fatima"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
        "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
        "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez",
        "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright",
        "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall",
        "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Okoye", "Chen", "Patel", "Kim"]
COMORBID = ["CKD", "DM2", "AFib", "COPD", "HTN", "CAD", "Obesity", "Anemia", "Depression", "OSA"]
CLINIC = {"HF": "HF Bridge Clinic", "AMI": "Cardiology Clinic", "COPD": "Pulmonary Clinic",
          "PN": "Primary Care", "CABG": "CT Surgery Clinic", "THA_TKA": "Orthopedics Clinic",
          "OTHER": "Primary Care"}

# day-of-week discharge weights (Mon..Sun); Fri-Sun = 36% by default
DOW_W = np.array([0.17, 0.165, 0.16, 0.145, 0.14, 0.11, 0.11])
DOW_W_6N_HF = np.array([0.168, 0.165, 0.163, 0.159, 0.135, 0.105, 0.105])


def window_of(d: pd.Timestamp) -> str:
    for name, a, b in WINDOWS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b) + pd.Timedelta(hours=23, minutes=59):
            return name
    return "OUT"


def fit_count(n: int, target_pct: float, nd: int = 1) -> int | None:
    """Integer k with round(100*k/n, nd) == target_pct, or None."""
    if n <= 0:
        return None
    for k in range(max(0, int(n * target_pct / 100) - 2), int(n * target_pct / 100) + 3):
        if round(100.0 * k / n + 1e-9, nd) == round(target_pct, nd):
            return k
    return None


def largest_remainder(values: np.ndarray, total: int, caps: np.ndarray) -> np.ndarray:
    base = np.minimum(np.floor(values).astype(int), caps)
    rem = values - base
    short = total - base.sum()
    order = np.argsort(-rem)
    i = 0
    while short > 0 and i < len(order) * 3:
        j = order[i % len(order)]
        if base[j] < caps[j]:
            base[j] += 1
            short -= 1
        i += 1
    return base


def gumbel_topk(rng, logw: np.ndarray, k: int) -> np.ndarray:
    if k <= 0:
        return np.array([], dtype=int)
    g = logw + rng.gumbel(size=len(logw))
    return np.argsort(-g)[:k]


@dataclass
class Generated:
    tables: dict
    ground_truth: pd.DataFrame
    calibration: dict


def generate(seed: int = SEED) -> Generated:
    rng = np.random.default_rng(seed)
    n_weeks = int((AS_OF - DATA_START).days // 7) + 1

    # ---------------------------------------------------------------- volumes
    rows = []
    for unit, cond, wk, base in VOLUMES:
        dow_w = DOW_W_6N_HF if (unit == "CUMC-6N" and cond == "HF") else DOW_W
        for w in range(n_weeks):
            wk_start = DATA_START + pd.Timedelta(days=7 * w)  # Sunday
            n = rng.poisson(wk)
            for _ in range(n):
                dow = rng.choice(7, p=dow_w / dow_w.sum())  # 0=Mon
                day = wk_start + pd.Timedelta(days=int((dow + 1) % 7))
                if day > AS_OF:
                    continue
                hour = int(rng.choice([10, 11, 12, 13, 14, 15, 16, 17, 18],
                                      p=[.08, .14, .16, .16, .15, .12, .09, .06, .04]))
                rows.append((unit, cond, day + pd.Timedelta(hours=hour, minutes=int(rng.integers(0, 60)))))
    enc = pd.DataFrame(rows, columns=["unit_id", "condition", "discharge_ts"])
    enc = enc[enc.discharge_ts >= DATA_START].sort_values("discharge_ts").reset_index(drop=True)
    enc["hospital_id"] = enc.unit_id.str.split("-").str[0]
    enc["window"] = enc.discharge_ts.dt.normalize().map(window_of)
    enc["weekend"] = enc.discharge_ts.dt.dayofweek >= 4  # Fri(4), Sat, Sun
    enc["is_6n_hf"] = (enc.unit_id == "CUMC-6N") & (enc.condition == "HF")

    # Make the 6N HF prior-20w / last-20w rates exactly representable (drop rows if needed)
    def make_fit(mask, target, nd=1, pool=None):
        while True:
            idx = enc.index[mask(enc)]
            k = fit_count(len(idx), target, nd)
            if k is not None:
                return k
            drop_from = enc.index[pool(enc)] if pool is not None else idx
            enc.drop(index=rng.choice(drop_from), inplace=True)

    post6 = lambda e: e.is_6n_hf & (e.discharge_ts >= CHANGE_DATE)
    k_fu_wkend = make_fit(lambda e: post6(e) & e.weekend, 100 * T_FU_WEEKEND_POST, nd=0)
    k_fu_wkday = make_fit(lambda e: post6(e) & ~e.weekend, 100 * T_FU_WEEKDAY_POST, nd=0)
    k_prior = make_fit(lambda e: e.is_6n_hf & (e.window == "W2"), T_6N_PRIOR20)
    k_last = make_fit(lambda e: e.is_6n_hf & e.window.isin(["W3a", "W3b"]), T_6N_LAST20,
                      pool=lambda e: e.is_6n_hf & (e.window == "W3a"))
    enc = enc.reset_index(drop=True)

    # ------------------------------------------------------------- patient risk
    n = len(enc)
    age = np.clip(rng.normal(np.where(enc.condition.isin(["HF", "COPD"]), 76, 68), 9), 40, 98).round()
    enc["age"] = age.astype(int)
    enc["comorbidity_count"] = np.clip(rng.poisson(np.where(enc.condition == "HF", 3.2, 2.2)), 0, 8)
    enc["prior_admissions_12m"] = np.clip(rng.poisson(np.where(enc.condition.isin(["HF", "COPD"]), 1.1, 0.5)), 0, 6)
    enc["los_days"] = np.clip(rng.gamma(2.2, np.where(enc.condition == "CABG", 3.0, 2.0)), 1, 25).round().astype(int)
    enc["transport_barrier"] = rng.random(n) < 0.09
    logw = (0.035 * (enc.age - 72) + 0.22 * enc.comorbidity_count + 0.30 * enc.prior_admissions_12m
            + 0.04 * enc.los_days + 0.45 * enc.transport_barrier).to_numpy()

    # ---------------------------------------------------- cell readmission targets
    base = {(u, c): b for u, c, _, b in VOLUMES}
    in12 = enc.window.isin(TRAILING_12M)
    hf12 = in12 & (enc.condition == "HF")

    # 6N HF counts
    m_w3a = enc.is_6n_hf & (enc.window == "W3a")
    k_w3a = int(round(T_6N_W3A_RATE * m_w3a.sum()))
    k_w3b = k_last - k_w3a
    n_w3b = int((enc.is_6n_hf & (enc.window == "W3b")).sum())
    rate_post = k_w3b / n_w3b

    def cell_rate(unit, cond, window):
        if unit == "CUMC-6N" and cond == "HF":
            return {"W0": 0.148, "W1": 0.148, "W2": None, "W3a": None, "W3b": None, "W4": rate_post}[window]
        return base[(unit, cond)]

    # community HF rate solved so that the system-wide HF marginals are consistent
    # with a reasonable "lives alone" prevalence (~12%).
    target_b = 0.12
    target_R = T_HF_NOLA + (T_HF_LA - T_HF_NOLA) * target_b
    fixed = 0.0
    m_6n12 = enc.is_6n_hf & in12
    fixed += 0.148 * (enc.is_6n_hf & (enc.window == "W1")).sum() + k_prior + k_last
    m_cumc_other = hf12 & (enc.hospital_id == "CUMC") & ~enc.is_6n_hf
    fixed += 0.220 * m_cumc_other.sum()
    m_comm = hf12 & enc.hospital_id.isin(["FCH", "PHMC"])
    comm_rate = (target_R * hf12.sum() - fixed) / m_comm.sum()
    for u in ("FCH-3A", "PHMC-TEL"):
        base[(u, "HF")] = float(comm_rate)

    cell_k = {}
    for (u, c, w), idx in enc.groupby(["unit_id", "condition", "window"]).groups.items():
        if u == "CUMC-6N" and c == "HF" and w == "W2":
            cell_k[(u, c, w)] = k_prior
        elif u == "CUMC-6N" and c == "HF" and w == "W3a":
            cell_k[(u, c, w)] = k_w3a
        elif u == "CUMC-6N" and c == "HF" and w == "W3b":
            cell_k[(u, c, w)] = k_w3b
        else:
            cell_k[(u, c, w)] = int(round(cell_rate(u, c, w) * len(idx)))

    R = sum(k for (u, c, w), k in cell_k.items() if c == "HF" and w in TRAILING_12M) / hf12.sum()
    a_target = (R - T_HF_FU) / (T_HF_NOFU - T_HF_FU)  # share of HF 12m without 7d FU
    b_target = (R - T_HF_NOLA) / (T_HF_LA - T_HF_NOLA)

    # ------------------------------------------------------------- follow-up flag
    fu = np.zeros(n, dtype=bool)
    post = enc.is_6n_hf & (enc.discharge_ts >= CHANGE_DATE)
    for wkend, k in ((True, k_fu_wkend), (False, k_fu_wkday)):
        idx = enc.index[post & (enc.weekend == wkend)].to_numpy()
        fu[rng.choice(idx, k, replace=False)] = True

    # 6N pre-change weekend booking rate solved from the what-if target
    cumc_hf_O = sum(k for (u, c, w), k in cell_k.items()
                    if c == "HF" and w in TRAILING_12M and u.startswith("CUMC"))
    conv_target = T_WHATIF_AVOID_FRACTION * cumc_hf_O / (T_HF_NOFU - T_HF_FU)
    w12 = enc.is_6n_hf & in12 & enc.weekend
    booked_post12 = fu[(w12 & (enc.discharge_ts >= CHANGE_DATE)).to_numpy()].sum()
    pre_w = enc.index[enc.is_6n_hf & enc.weekend & (enc.discharge_ts < CHANGE_DATE) & in12].to_numpy()
    booked_pre = int(round(T_WHATIF_FU_TARGET * w12.sum() - booked_post12 - conv_target))
    fu[rng.choice(pre_w, booked_pre, replace=False)] = True
    p_pre_weekend = booked_pre / len(pre_w)
    # out-of-window 6N pre-change weekend + weekday
    rest = enc.index[enc.is_6n_hf & (enc.discharge_ts < CHANGE_DATE) & ~(enc.weekend & in12)].to_numpy()
    for i in rest:
        p = p_pre_weekend if enc.at[i, "weekend"] else T_FU_WEEKDAY_PRE
        fu[i] = rng.random() < p

    # other HF in trailing 12m: exact count so overall no-FU share == a_target
    hf12_idx = enc.index[hf12].to_numpy()
    other_hf12 = enc.index[hf12 & ~enc.is_6n_hf].to_numpy()
    totK12 = sum(k for (u, c, w), k in cell_k.items() if c == "HF" and w in TRAILING_12M)
    N12 = len(hf12_idx)

    def pick_split(share, t_hi, t_lo):
        """n_hi near share*N12 such that k_hi/n_hi -> t_hi and (K-k_hi)/(N12-n_hi) -> t_lo exactly."""
        base_n = int(round(share * N12))
        for dn in sorted(range(-40, 41), key=abs):
            nh = base_n + dn
            kh = fit_count(nh, 100 * t_hi)
            if kh is not None and round(100 * (totK12 - kh) / (N12 - nh) + 1e-9, 1) == round(100 * t_lo, 1):
                return nh, kh
        raise RuntimeError("no exact split found")

    n_nofu, k_nofu = pick_split(a_target, T_HF_NOFU, T_HF_FU)
    n_la, k_la = pick_split(b_target, T_HF_LA, T_HF_NOLA)
    need_fu = (N12 - n_nofu) - fu[enc.index[hf12 & enc.is_6n_hf]].sum()
    wts = np.where(enc.loc[other_hf12, "weekend"], 0.85, 1.0)
    fu[other_hf12[gumbel_topk(rng, np.log(wts), int(need_fu))]] = True
    # everything else: Bernoulli
    rest = enc.index[~enc.is_6n_hf & ~hf12].to_numpy()
    p_rest = np.where(enc.loc[rest, "condition"] == "HF", 0.58, 0.62) - 0.05 * enc.loc[rest, "weekend"]
    fu[rest] = rng.random(len(rest)) < p_rest
    enc["fu7_booked"] = fu

    # ------------------------------------------------------------ lives alone flag
    la = rng.random(n) < 0.12
    la[hf12_idx] = False
    la[rng.choice(hf12_idx, n_la, replace=False)] = True
    enc["lives_alone"] = la

    # ------------------------------------- IPF: readmit counts per (cell, fu, la)
    enc["cell"] = list(zip(enc.unit_id, enc.condition, enc.window))
    sub = enc.groupby(["cell", "fu7_booked", "lives_alone"]).size().rename("n").reset_index()
    sub["is_hf12"] = sub.cell.map(lambda c: c[1] == "HF" and c[2] in TRAILING_12M)
    sub["K"] = sub.cell.map(cell_k)
    beta = {True: 1.0, False: 1.8}  # FU multiplier (fu7_booked -> beta)
    gamma = {True: 1.6, False: 1.0}
    alpha = {c: 1.0 for c in sub.cell.unique()}
    h = sub[sub.is_hf12]
    nofu_n, fu_n = h[~h.fu7_booked].n.sum(), h[h.fu7_booked].n.sum()
    la_n, nola_n = h[h.lives_alone].n.sum(), h[~h.lives_alone].n.sum()
    totK = sum(k for c, k in cell_k.items() if c[1] == "HF" and c[2] in TRAILING_12M)
    F = {False: T_HF_NOFU * nofu_n, True: T_HF_FU * fu_n}
    L = {True: T_HF_LA * la_n, False: T_HF_NOLA * nola_n}
    sF, sL = totK / sum(F.values()), totK / sum(L.values())
    F = {k: v * sF for k, v in F.items()}
    L = {k: v * sL for k, v in L.items()}

    def expected(df):
        return df.n * df.cell.map(alpha) * df.fu7_booked.map(beta) * df.lives_alone.map(gamma)

    for _ in range(200):
        e = expected(sub)
        for c, s in e.groupby(sub.cell).sum().items():
            alpha[c] *= cell_k[c] / s if s > 0 else 1.0
        e = expected(sub)[sub.is_hf12]
        for f in (True, False):
            beta[f] *= F[f] / e[sub.fu7_booked[sub.is_hf12] == f].sum()
        e = expected(sub)[sub.is_hf12]
        for l in (True, False):
            gamma[l] *= L[l] / e[sub.lives_alone[sub.is_hf12] == l].sum()
    sub["e"] = np.minimum(expected(sub), sub.n)
    sub["k"] = 0
    for c, g in sub.groupby("cell"):
        sub.loc[g.index, "k"] = largest_remainder(g.e.to_numpy(), cell_k[c], g.n.to_numpy())

    # greedy integer repair of the HF 12m marginals (moves keep cell totals fixed)
    def marg_err(s):
        hh = s[s.is_hf12]
        return float((hh.k[~hh.fu7_booked].sum() - k_nofu) ** 2 + (hh.k[hh.lives_alone].sum() - k_la) ** 2)

    hf_idx = sub.index[sub.is_hf12].tolist()
    for _ in range(400):
        cur = marg_err(sub)
        if cur == 0:
            break
        best = None
        for c, g in sub.loc[hf_idx].groupby("cell"):
            ids = g.index.tolist()
            for i in ids:
                for j in ids:
                    if i == j or sub.at[i, "k"] <= 0 or sub.at[j, "k"] >= sub.at[j, "n"]:
                        continue
                    sub.at[i, "k"] -= 1; sub.at[j, "k"] += 1
                    e2 = marg_err(sub)
                    sub.at[i, "k"] += 1; sub.at[j, "k"] -= 1
                    if e2 < cur - 1e-9 and (best is None or e2 < best[0]):
                        best = (e2, i, j)
        if best is None:
            break
        sub.at[best[1], "k"] -= 1; sub.at[best[2], "k"] += 1

    # ------------------------------------------------ choose readmitted encounters
    readmit = np.zeros(n, dtype=bool)
    groups = enc.groupby(["cell", "fu7_booked", "lives_alone"]).indices
    for _, r in sub.iterrows():
        idx = groups[(r.cell, r.fu7_booked, r.lives_alone)]
        readmit[idx[gumbel_topk(rng, logw[idx], int(r.k))]] = True
    enc["readmit_30d_truth"] = readmit

    # ---------------------------------------------------------- build raw tables
    enc["admit_ts"] = enc.discharge_ts - pd.to_timedelta(enc.los_days, unit="D") - pd.to_timedelta(
        rng.integers(0, 10, n), unit="h")
    enc["encounter_id"] = [f"E{1000000 + i}" for i in range(n)]
    enc["patient_id"] = [f"P{500000 + i}" for i in rng.permutation(n)]
    dx_pick = [DX[c][rng.integers(0, len(DX[c]))] for c in enc.condition]
    enc["principal_dx_code"] = [d[0] for d in dx_pick]
    enc["principal_dx_desc"] = [d[1] for d in dx_pick]
    enc["drg_code"] = [d[2] for d in dx_pick]
    enc["admission_source"] = np.where(enc.condition.isin(["THA_TKA", "CABG"]), "ELECTIVE",
                                       rng.choice(["ED", "ED", "ED", "CLINIC_REFERRAL", "TRANSFER_IN"], n))
    enc["discharge_disposition"] = rng.choice(["HOME", "HOME_HEALTH", "SNF"], n, p=[.62, .26, .12])
    enc["payer"] = rng.choice(["MEDICARE_FFS", "MEDICARE_ADVANTAGE", "MEDICAID", "COMMERCIAL"], n,
                              p=[.58, .17, .10, .15])
    enc.loc[enc.age >= 65, "payer"] = rng.choice(["MEDICARE_FFS", "MEDICARE_ADVANTAGE"],
                                                 (enc.age >= 65).sum(), p=[.78, .22])
    enc["comorbidities"] = [
        "|".join(sorted(rng.choice(COMORBID, k, replace=False))) if k else "" for k in enc.comorbidity_count]
    enc["encounter_type"] = "INPATIENT"

    # readmission encounters
    ra = enc[enc.readmit_30d_truth].copy()
    days = rng.choice(np.arange(1, 31), len(ra), p=_decay(30))
    ra["admit_ts"] = ra.discharge_ts + pd.to_timedelta(days - 1, unit="D") + pd.to_timedelta(
        rng.integers(1, 23, len(ra)), unit="h")
    observed = ra.admit_ts <= AS_OF
    enc.loc[ra.index[~observed], "readmit_30d_truth"] = False  # not yet observed at extract
    ra = ra[observed].copy()
    ra_los = np.clip(rng.gamma(2.0, 2.0, len(ra)), 1, 15).round().astype(int)
    ra["discharge_ts"] = ra.admit_ts + pd.to_timedelta(ra_los, unit="D")
    ra["los_days"] = ra_los
    ra["index_encounter_id"] = ra.encounter_id
    ra["encounter_id"] = [f"E{3000000 + i}" for i in range(len(ra))]
    same = rng.random(len(ra)) < 0.6
    ra.loc[~same, "principal_dx_code"] = "N17.9"
    ra.loc[~same, "principal_dx_desc"] = "Acute kidney failure, unspecified"
    ra.loc[~same, "drg_code"] = "683"
    ra.loc[~same, "condition"] = "OTHER"
    ra["admission_source"] = "ED"
    ra["discharge_disposition"] = rng.choice(["HOME", "HOME_HEALTH", "SNF"], len(ra), p=[.5, .3, .2])
    ra["prior_admissions_12m"] = ra.prior_admissions_12m + 1
    ra["fu7_booked"] = False
    ra["lives_alone"] = ra.lives_alone
    ra["readmit_30d_truth"] = False
    ra["window"] = "READMIT"

    # extra rows excluded from HRRP index logic (deaths / AMA), not part of story cells
    n_ex = 140
    ex = enc.sample(n_ex, random_state=seed).copy()
    ex["encounter_id"] = [f"E{4000000 + i}" for i in range(n_ex)]
    ex["patient_id"] = [f"P{900000 + i}" for i in range(n_ex)]
    ex["discharge_disposition"] = rng.choice(["EXPIRED", "AMA"], n_ex, p=[.6, .4])
    ex["readmit_30d_truth"] = False
    ex["fu7_booked"] = False
    ex["window"] = "EXCLUDED"

    cols = ["encounter_id", "patient_id", "hospital_id", "unit_id", "admit_ts", "discharge_ts",
            "los_days", "principal_dx_code", "principal_dx_desc", "drg_code", "admission_source",
            "discharge_disposition", "payer", "prior_admissions_12m", "comorbidities", "encounter_type"]
    all_enc = pd.concat([enc[cols], ra[cols], ex[cols]], ignore_index=True)

    # data-quality defects for pipeline expectations: duplicates + bad timestamps
    dup = all_enc.sample(45, random_state=seed + 1)
    bad = all_enc.sample(6, random_state=seed + 2).copy()
    bad["encounter_id"] = [f"E{4900000 + i}" for i in range(len(bad))]
    bad["admit_ts"] = bad.discharge_ts + pd.Timedelta(days=2)
    encounters = pd.concat([all_enc, dup, bad], ignore_index=True)

    # patients
    pats = pd.concat([enc[["patient_id", "age", "hospital_id"]], ex[["patient_id", "age", "hospital_id"]]])
    pats = pats.drop_duplicates("patient_id")
    first = rng.choice(FIRST, len(pats))
    last = rng.choice(LAST, len(pats))
    dob = AS_OF - pd.to_timedelta(pats.age.to_numpy() * 365.25 + rng.integers(0, 365, len(pats)), unit="D")
    patients = pd.DataFrame({
        "patient_id": pats.patient_id.to_numpy(),
        "mrn": [f"MRN{rng.integers(10**7, 10**8)}" for _ in range(len(pats))],
        "first_name": first, "last_name": last,
        "date_of_birth": pd.to_datetime(dob).date,
        "sex": rng.choice(["F", "M"], len(pats)),
        "zip_code": rng.choice(["60601", "60614", "60618", "60629", "60640", "60148", "60174", "60505",
                                "60432", "60451", "60466", "60409"], len(pats)),
        "primary_language": rng.choice(["English", "Spanish", "Polish", "Mandarin"], len(pats), p=[.8, .12, .04, .04]),
        "home_phone": [f"(630) 555-{rng.integers(1000, 9999)}" for _ in range(len(pats))],
    })

    # follow-up appointments
    appts = []
    for r in enc[["encounter_id", "patient_id", "discharge_ts", "condition", "fu7_booked"]].itertuples():
        clinic = CLINIC[r.condition]
        if r.fu7_booked:
            appt = r.discharge_ts.normalize() + pd.Timedelta(days=int(rng.integers(2, 8)), hours=int(rng.choice([9, 10, 11, 13, 14, 15])))
            booked = r.discharge_ts - pd.Timedelta(hours=int(rng.integers(2, 30)))
            appts.append((r.encounter_id, r.patient_id, clinic, appt, booked, "SCHEDULED"))
        elif rng.random() < 0.45:  # booked later by the patient, outside the 7-day window
            appt = r.discharge_ts.normalize() + pd.Timedelta(days=int(rng.integers(9, 22)), hours=10)
            booked = r.discharge_ts + pd.Timedelta(days=int(rng.integers(1, 5)))
            if booked <= AS_OF:
                appts.append((r.encounter_id, r.patient_id, clinic, appt, booked, "SCHEDULED"))
    followups = pd.DataFrame(appts, columns=["encounter_id", "patient_id", "clinic_name", "appointment_ts",
                                             "booked_ts", "status"])
    followups.insert(0, "appointment_id", [f"A{700000 + i}" for i in range(len(followups))])

    # discharge notes
    notes = pd.DataFrame({
        "note_id": [f"N{800000 + i}" for i in range(len(all_enc))],
        "encounter_id": all_enc.encounter_id,
        "note_type": "DISCHARGE_SUMMARY",
        "author_role": rng.choice(["Hospitalist", "Cardiology NP", "Resident", "Attending"], len(all_enc)),
        "note_ts": all_enc.discharge_ts - pd.Timedelta(minutes=30),
    })
    flags = pd.concat([enc[["encounter_id", "condition", "fu7_booked", "lives_alone", "transport_barrier",
                            "unit_id", "discharge_ts", "weekend"]],
                       ra.assign(transport_barrier=False, weekend=False)[
                           ["encounter_id", "condition", "fu7_booked", "lives_alone", "transport_barrier",
                            "unit_id", "discharge_ts", "weekend"]],
                       ex.assign(transport_barrier=False, weekend=False, lives_alone=False)[
                           ["encounter_id", "condition", "fu7_booked", "lives_alone", "transport_barrier",
                            "unit_id", "discharge_ts", "weekend"]]]).set_index("encounter_id")
    appt_map = followups.sort_values("appointment_ts").drop_duplicates("encounter_id").set_index("encounter_id")
    notes["note_text"] = [_note(rng, eid, flags.loc[eid], appt_map) for eid in all_enc.encounter_id]

    staffing = pd.DataFrame([
        ("S1", "CUMC-6N", "2026-06-19", "STAFFING", "Weekend transitions pharmacist position vacated; not backfilled"),
        ("S2", "CUMC", "2026-06-26", "CLINIC_SCHEDULE", "HF Bridge Clinic discontinued Friday afternoon appointment slots"),
        ("S3", "FCH-3A", "2026-02-02", "STAFFING", "Night charge nurse hired"),
        ("S4", "CUMC-4S", "2026-03-16", "PROGRAM", "COPD inhaler teach-back program launched"),
    ], columns=["event_id", "scope_id", "event_date", "event_type", "description"])

    hospitals = pd.DataFrame(HOSPITALS, columns=["hospital_id", "hospital_name", "beds", "cms_ccn", "hospital_type"])
    units = pd.DataFrame(UNITS, columns=["unit_id", "hospital_id", "unit_name", "service_line"])
    dxmap = pd.DataFrame([(code, desc, drg, cond if cond != "OTHER" else None)
                          for cond, lst in DX.items() for code, desc, drg in lst] +
                         [("N17.9", "Acute kidney failure, unspecified", "683", None)],
                         columns=["icd10_code", "description", "drg_code", "hrrp_condition"])

    # HRRP reference: expected rates such that observed/expected == target ERR
    idx = enc[enc.window.isin(TRAILING_12M) & (enc.condition != "OTHER")]
    obs = idx.groupby(["hospital_id", "condition"]).agg(n=("encounter_id", "size"),
                                                      k=("readmit_30d_truth", "sum")).reset_index()
    ref_rows = []
    for r in obs.itertuples():
        tgt = HRRP_TARGETS[r.hospital_id]["conditions"].get(r.condition)
        if tgt is None:
            continue
        err, pay = tgt
        ref_rows.append((r.hospital_id, r.condition, round((r.k / r.n) / err, 6), pay,
                         HRRP_TARGETS[r.hospital_id]["total_base_payments"], 1.0, HRRP_CAP,
                         "FY2027 (synthetic)", "2025-10-05", "2026-10-04"))
    hrrp_ref = pd.DataFrame(ref_rows, columns=[
        "hospital_id", "hrrp_condition", "expected_readmission_rate", "base_op_drg_payments_condition",
        "total_base_op_drg_payments", "neutrality_modifier", "penalty_cap", "program_year",
        "performance_start", "performance_end"])

    truth = enc[["encounter_id", "fu7_booked", "lives_alone", "transport_barrier", "readmit_30d_truth"]]
    calib = dict(rows=len(encounters), index_encounters=len(enc), readmissions=len(ra),
                 hf12_R=float(R), hf12_nofu_share=float(a_target), hf12_la_share=float(b_target),
                 community_hf_rate=float(comm_rate), cumc_hf_readmits_12m=int(cumc_hf_O),
                 sixn_post_change_rate=float(rate_post), sixn_pre_weekend_fu_rate=float(p_pre_weekend),
                 ipf_beta=beta, ipf_gamma=gamma)
    return Generated(
        tables=dict(hospitals=hospitals, units=units, icd10_hrrp_map=dxmap, patients=patients,
                    encounters=encounters, followup_appointments=followups, discharge_notes=notes,
                    staffing_events=staffing, cms_hrrp_reference=hrrp_ref),
        ground_truth=truth, calibration=calib)


def _decay(n):
    p = np.exp(-np.arange(n) / 11.0)
    return p / p.sum()


SOCIAL_LA = [
    "Patient lives alone; daughter lives out of state and calls weekly.",
    "Lives alone in a second-floor apartment. No caregiver at home.",
    "Widowed, lives by themself. No family nearby to help with medications.",
    "Social: lives alone, son visits on weekends only.",
    "Patient reports no one at home to help with daily weights or pill box.",
]
SOCIAL_SUPPORT = [
    "Lives with spouse who manages medications.",
    "Lives with adult daughter who will assist with medications and daily weights.",
    "Lives with partner; family at bedside during discharge teaching.",
    "Resides with son and daughter-in-law. Strong family support.",
    "Lives with wife; she attended discharge education.",
]
TRANSPORT = ["Does not drive, no reliable ride to appointments.",
             "Relies on a neighbor for rides; transportation is uncertain.",
             "No car; bus route requires two transfers."]


def _note(rng, eid, f, appt_map) -> str:
    cond = f.condition
    if cond == "HF":
        ef = int(rng.choice([25, 30, 35, 40, 45, 55, 60]))
        hpi = (f"Admitted with acute decompensated heart failure (EF {ef}%), volume overload, "
               f"dyspnea on exertion. Diuresed with IV furosemide, net negative {rng.integers(2, 7)}.{rng.integers(0, 9)} L. "
               f"Discharge weight {rng.integers(62, 118)} kg.")
        meds = "Furosemide 40 mg PO daily, metoprolol succinate 50 mg daily, sacubitril/valsartan 24/26 mg BID, spironolactone 25 mg daily."
        teach = "Reviewed 2 g sodium diet, 1.5 L fluid restriction, daily weights; call if weight up 2 lb in a day or 5 lb in a week."
    elif cond == "COPD":
        hpi = "Admitted for COPD exacerbation; treated with nebulized bronchodilators, prednisone burst and azithromycin."
        meds = "Prednisone taper, tiotropium daily, albuterol PRN."
        teach = "Inhaler technique reviewed with teach-back."
    elif cond == "PN":
        hpi = "Community-acquired pneumonia, right lower lobe. Treated with ceftriaxone and azithromycin; afebrile x48h."
        meds = "Amoxicillin-clavulanate to complete 7 days."
        teach = "Incentive spirometry encouraged."
    elif cond == "AMI":
        hpi = "NSTEMI; cardiac catheterization with drug-eluting stent to LAD. Troponin trending down."
        meds = "Aspirin 81 mg, ticagrelor 90 mg BID, atorvastatin 80 mg, metoprolol tartrate 25 mg BID."
        teach = "Cardiac rehab referral placed."
    elif cond == "CABG":
        hpi = "Post CABG x3. Sternal precautions. Chest tubes removed POD2."
        meds = "Aspirin, atorvastatin, metoprolol, acetaminophen."
        teach = "Sternal precautions reviewed."
    elif cond == "THA_TKA":
        hpi = "Elective joint arthroplasty, uncomplicated. Ambulating with walker."
        meds = "Apixaban 2.5 mg BID x 35 days, acetaminophen, oxycodone PRN."
        teach = "PT home exercise program."
    else:
        hpi = "Admitted for acute medical illness, improved with treatment."
        meds = "Continue home medications as reconciled."
        teach = "Return precautions reviewed."

    social = rng.choice(SOCIAL_LA) if f.lives_alone else rng.choice(SOCIAL_SUPPORT)
    if f.transport_barrier:
        social += " " + rng.choice(TRANSPORT)

    if f.fu7_booked and eid in appt_map.index:
        a = appt_map.loc[eid]
        fu = f"Follow-up appointment scheduled with {a.clinic_name} on {a.appointment_ts:%Y-%m-%d} at {a.appointment_ts:%H:%M}."
    elif cond == "HF" and f.unit_id == "CUMC-6N" and f.weekend and f.discharge_ts >= CHANGE_DATE:
        fu = rng.choice(["Patient instructed to schedule cardiology follow-up next week.",
                         "Patient to call the HF Bridge Clinic on Monday to schedule follow-up.",
                         "Clinic closed for scheduling; patient instructed to schedule follow-up next week."])
    else:
        fu = rng.choice(["Patient instructed to schedule follow-up with PCP within 1-2 weeks.",
                         "Follow up with primary care as needed.",
                         "Patient to call clinic to arrange follow-up."])
    return (f"DISCHARGE SUMMARY\nHospital course: {hpi}\nDischarge medications: {meds}\n"
            f"Education: {teach}\nSocial history: {social}\nFollow-up: {fu}\n"
            f"Condition at discharge: stable.")


if __name__ == "__main__":
    import json, sys
    g = generate()
    for k, v in g.tables.items():
        print(f"{k:24s} {len(v):>7,d} rows")
    print(json.dumps({k: (v if not isinstance(v, dict) else {str(a): round(b, 4) for a, b in v.items()})
                      for k, v in g.calibration.items()}, indent=2, default=str))
    if len(sys.argv) > 1:
        out = sys.argv[1]
        import os
        os.makedirs(out, exist_ok=True)
        for k, v in g.tables.items():
            v.to_csv(f"{out}/{k}.csv", index=False)
        g.ground_truth.to_csv(f"{out}/_ground_truth.csv", index=False)
