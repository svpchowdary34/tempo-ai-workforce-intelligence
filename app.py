# ==============================================================================
# TEMPO AI — Workforce Productivity & Operational Intelligence | ONE Google Colab cell
# Work smarter. Find the friction.
# ==============================================================================
import subprocess, sys, os, re, json, zipfile, html, math, warnings
warnings.filterwarnings("ignore")
def _deps():
    try:
        from importlib.metadata import version
        if int(version("gradio").split(".")[0]) not in (4, 5): raise RuntimeError("gradio")
        for p in ("plotly", "scipy", "requests", "pandas", "numpy"): version(p)
    except Exception:
        print("Installing dependencies (about a minute)...")
        try: subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gradio>=4.44,<6", "plotly", "scipy", "requests", "pandas", "numpy"]); print("Dependencies installed.")
        except Exception as e: print("Install warning:", type(e).__name__, "- check internet access and re-run.")
_deps()
try:
    import numpy as np, pandas as pd, plotly.graph_objects as go, gradio as gr, requests
    from plotly.subplots import make_subplots
    from scipy import stats
except Exception as e:
    raise SystemExit("Libraries could not be imported (" + type(e).__name__ + "). Restart the runtime and re-run this cell.")

C = dict(bg="#172522", sf="#222E2B", mi="#8FE3B5", am="#F2C27B", la="#D3B5FF", tx="#F3F5F0", mu="#A6B7AE", co="#F18C91")
G = {}; TESTS = []; _DEMO = {}
BLANK = ["", "nan", "none", "n/a", "na", "-", "null", "nat"]
esc = lambda x: html.escape(str(x))
norm = lambda s: re.sub(r"\W+", "_", str(s).strip().lower()).strip("_")
nul = lambda v: v is None or (not isinstance(v, str) and bool(pd.isna(v)))
nf = lambda v: "—" if nul(v) else format(v, ",.0f")
fx = lambda v, d=1: "—" if nul(v) else format(v, "." + str(d) + "f")
pc0 = lambda v: "—" if nul(v) else format(v, ".0%")
pc1 = lambda v: "—" if nul(v) else format(v, ".1%")
money = lambda v: "—" if nul(v) else ("-$" if v < 0 else "$") + format(abs(v), ",.0f")
dts = lambda v: "—" if nul(v) else pd.Timestamp(v).strftime("%Y-%m-%d")
SIGN = lambda v: "—" if nul(v) else "%+.0f%%" % (100 * v)
ratio = lambda a, b: np.nan if (nul(a) or nul(b) or b == 0) else float(a) / float(b)
wk = lambda s: (s - pd.to_timedelta(s.dt.dayofweek, unit="D")).dt.normalize()
wk1 = lambda x: (x - pd.Timedelta(days=x.dayofweek)).normalize()
T0 = pd.Timestamp("2025-11-03"); NW = 52
DEF = dict(ot_h=4.0, run=4, task_thr=6.0, util=1.05, ot_pct=.10, rw=.15, blk=.10, absr=.10, conc=.40, cwx=1.0, hrate=45.0, rwc=.35, recv=.95, over=1.05, w=dict(delayed=.2, blocked=.2, cycle=.2, crit=.15, age=.1, recur=.1, down=.05))
def note(t, k="info"):
    col = {"info": C["mu"], "ok": C["mi"], "warn": C["am"], "err": C["co"], "ai": C["la"]}[k]
    return "<div class='note' style='border-left:3px solid %s'>%s</div>" % (col, t)
def card(lab, val, desc, col=C["mi"]): return "<div class='kc'><div class='kl'>%s</div><div class='kv' style='color:%s'>%s</div><div class='kd'>%s</div></div>" % (lab, col, val, desc)
H = lambda t: "<div class='sec'>%s</div>" % t
def tbl(d, cols, fmt=None):
    fmt = fmt or {}; h = "<div class='tw'><table><tr>" + "".join("<th>%s</th>" % n for _, n in cols) + "</tr>"
    for _, r in d.iterrows(): h += "<tr>" + "".join("<td>%s</td>" % (fmt[k](r[k]) if k in fmt else ("—" if nul(r[k]) else esc(r[k]))) for k, _n in cols) + "</tr>"
    return h + "</table></div>"
def sty(f, h=380, t=""):
    f.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=C["tx"]), height=h, title=dict(text=t, x=.02), margin=dict(l=60, r=20, t=55, b=50), legend=dict(orientation="h", y=-.25), colorway=[C["mi"], C["la"], C["am"], C["co"], C["mu"]])
    return f
def empty(msg):
    f = go.Figure(); f.add_annotation(text=msg, showarrow=False, font=dict(color=C["mu"], size=14)); f.update_xaxes(visible=False); f.update_yaxes(visible=False); return sty(f, 300)
def banner(): return note("<b>Illustrative synthetic data.</b> Fictional employees and tasks with deliberately planted patterns; not a real organisation and not an industry benchmark.", "warn") if G.get("demo") else ""
def clean_str(s):
    t = s.astype(str).str.strip(); return t.where(~(s.isna() | t.str.lower().isin(BLANK)), np.nan)
def to_num(s):
    if pd.api.types.is_numeric_dtype(s): return s.astype(float)
    return pd.to_numeric(s.astype(str).str.replace(r"[$,%£€₹\s]", "", regex=True), errors="coerce")
def to_dt(s):
    try: return pd.to_datetime(s, errors="coerce", format="mixed")
    except Exception: return pd.to_datetime(s, errors="coerce")
def read_csv_any(f):
    p = f if isinstance(f, str) else getattr(f, "name", f)
    try: d = pd.read_csv(p)
    except Exception: d = pd.read_csv(p, sep=None, engine="python", encoding_errors="replace")
    if d.empty: raise ValueError("A file contains no rows.")
    return d
def safe(kinds):
    def deco(fn):
        def w(*a):
            def out(msg, k): return tuple((note(msg, k) if i == 0 else "") if c == "h" else empty("No data") for i, c in enumerate(kinds))
            if "D" not in G: return out("Load data first.", "info")
            try: return fn(*a)
            except Exception as e: return out("Could not render this page: " + esc(e), "err")
        return w
    return deco

# ------------------------------ FICTIONAL synthetic data (fixed seed) ------------------------------
fv = lambda x, u: x(u) if callable(x) else x
LAB = lambda u: .16 if (.34 <= u <= .46 or .78 <= u <= .86) else .04
TP = {"Customer Support": dict(lam=15, cap=lambda u: 1.15 - .35 * u, rw=lambda u: .08 + .07 * u, ot=lambda u: 1.5 + 7 * u, ab=.04, dep=.06, bh=8, pok=1, conc=0, apc=.08, cats=["Ticket Resolution", "Escalation", "Knowledge Update"]),
      "Claims Processing": dict(lam=15, cap=lambda u: .85 if u < .58 else 1.3, rw=lambda u: .10 if u < .58 else .05, ot=lambda u: 7 if u < .58 else 2.5, ab=.04, dep=.08, bh=10, pok=1, conc=0, apc=.10, cats=["Claim Intake", "Assessment", "Settlement"]),
      "Finance Operations": dict(lam=13, cap=1.08, rw=.06, ot=3, ab=.04, dep=.55, bh=lambda u: 40 + 50 * u, pok=1, conc=0, apc=.28, cats=["Invoice Processing", "Reconciliation", "Reporting"]),
      "Engineering": dict(lam=13, cap=1.05, rw=.10, ot=3, ab=.04, dep=.06, bh=8, pok=1, conc=1, apc=.08, cats=["Feature Build", "Code Review", "Bug Fix"]),
      "Quality Assurance": dict(lam=11, cap=1.08, rw=.07, ot=2, ab=.04, dep=.06, bh=8, pok=1, conc=0, apc=.08, cats=["Test Execution", "Test Design", "Defect Triage"]),
      "Logistics": dict(lam=13, cap=lambda u: 1.12 * (1 - 1.6 * LAB(u)), rw=.08, ot=3, ab=LAB, dep=.06, bh=8, pok=1, conc=0, apc=.08, cats=["Dispatch", "Routing", "Warehouse Tasks"]),
      "Marketing Operations": dict(lam=11, cap=1.08, rw=.08, ot=.8, ab=.04, dep=.06, bh=8, pok=0, conc=0, apc=.08, cats=["Campaign Setup", "Asset Production", "Reporting"]),
      "Order Fulfilment": dict(lam=17, cap=1.25, rw=lambda u: .05 + .20 * u, ot=3, ab=.04, dep=.06, bh=8, pok=1, conc=0, apc=.08, cats=["Pick and Pack", "Shipping", "Returns"])}
def make_data(seed=3):
    r = np.random.default_rng(seed); teams = list(TP); sizes = [40, 38, 36, 40, 30, 38, 34, 44]; DD = lambda n: T0 + pd.Timedelta(days=int(n)); ED = NW * 7 - 1; emp = []; k = 0
    for g, n in zip(teams, sizes):
        for _ in range(n):
            k += 1; pt = r.random() < .12
            emp.append(dict(employee_id="E%03d" % k, department=g, role=str(r.choice(["Analyst", "Specialist", "Coordinator", "Senior Specialist"])), employment_type="Part-time" if pt else "Full-time", contracted_hours=24.0 if pt else 40.0,
                            location=str(r.choice(["Hyderabad", "Pune", "Manchester", "Austin"])), tenure_band=str(r.choice(["<1y", "1-3y", "3-5y", "5y+"], p=[.2, .35, .25, .2]))))
    emp = pd.DataFrame(emp); tid = 0; tasks = []; deps = []
    for g in teams:
        p = TP[g]; ids = emp.employee_id[emp.department == g].values; recs_ = []; apr = []; dl = []
        for w in range(NW):
            u = w / (NW - 1)
            for _ in range(r.poisson(p["lam"])):
                cd = w * 7 + int(r.integers(0, 5)); tid += 1; isap = r.random() < p["apc"]; cat = "Approval" if isap else str(r.choice(p["cats"]))
                cx = int(r.choice([1, 2, 3, 4, 5], p=[.1, .2, .25, .25, .2] if p["conc"] else [.2, .3, .3, .15, .05])); est = round(2 * cx ** 1.1 * float(r.lognormal(0, .3)), 1)
                who = str(r.choice(ids[:3])) if (p["conc"] and cx >= 4 and r.random() < .8) else str(r.choice(ids)); rk = fv(p["rw"], u); rw = int(r.random() < rk) + int(r.random() < rk / 2)
                act = round(est * float(r.lognormal(.05, .25)) * (1 + .35 * rw), 1); blk = 0.0; pred = None
                if (not isap) and apr and r.random() < p["dep"]: pred = apr[int(r.integers(max(0, len(apr) - 15), len(apr)))]; blk = round(float(r.lognormal(math.log(fv(p["bh"], u)), .5)), 1)
                pr = int(r.choice([1, 2, 3, 4], p=[.15, .25, .4, .2]))
                t = dict(tid="T%05d" % tid, cd=cd, cat=cat, pr=pr, cx=cx, est=est, act=act, rw=rw, blk=blk, emp=who, prj="PRJ%02d" % int(r.integers(1, 9)), el=cd + int(math.ceil(blk / 24)))
                t["due"] = cd + int(math.ceil(est / 5 * 1.6)) + {1: 3, 2: 4, 3: 6, 4: 9}[pr]; recs_.append(t)
                if isap: apr.append(t["tid"])
                if pred: dl.append((pred, t["tid"], "Finish-to-start", blk))
        by = {}
        for t in recs_: by.setdefault(t["cd"] // 7, []).append(t)
        hb = np.mean([t["est"] for t in recs_]) * 1.05; pool = []
        for w in range(NW):
            pool += by.get(w, []); u = w / (NW - 1); cap = p["lam"] * hb * fv(p["cap"], u) * float(r.lognormal(0, .06)); used = 0.0
            el = sorted([t for t in pool if t["el"] <= w * 7 + 6], key=(lambda t: (t["pr"], t["cd"])) if p["pok"] else (lambda t: t["cd"]))
            for t in el:
                if used >= cap: break
                used += t["act"]; t["comp"] = max(t["el"], w * 7 + int(min(6, 7 * min(used, cap) / cap * .999))); t["st"] = max(t["el"], t["comp"] - int(math.ceil(t["act"] / 6)))
            pool = [t for t in pool if "comp" not in t]
        byid = {t["tid"]: t for t in recs_}
        for pr_, su, ty, b in dl:
            a, c = byid[pr_], byid[su]
            if "comp" in c and "comp" not in a: continue
            if "comp" in c and c["comp"] < a["comp"]: c["comp"] = a["comp"]; c["st"] = min(c["st"], c["comp"])
            deps.append((pr_, su, ty, b))
        for t in recs_:
            done = "comp" in t
            tasks.append(dict(task_id=t["tid"], team_id=g, assigned_employee_id=t["emp"], project_id=t["prj"], task_category=t["cat"], priority=t["pr"], estimated_hours=t["est"], actual_hours=t["act"] if done else np.nan, created_date=DD(t["cd"]), start_date=DD(t["st"]) if done else pd.NaT,
                              due_date=DD(t["due"]), completed_date=DD(t["comp"]) if done else pd.NaT, status="Completed" if done else ("Blocked" if t["el"] > ED else "Open"), complexity_score=t["cx"], rework_count=t["rw"], blocked_hours=t["blk"]))
    tk = pd.DataFrame(tasks); eidx = {e: i for i, e in enumerate(emp.employee_id)}; dn = tk[tk.completed_date.notna()]
    sw = ((dn.start_date - T0).dt.days // 7).values; cw_ = ((dn.completed_date - T0).dt.days // 7).values; L = cw_ - sw + 1
    act = pd.DataFrame({"e": np.repeat(dn.assigned_employee_id.map(eidx).values, L), "w": np.concatenate([np.arange(a, b + 1) for a, b in zip(sw, cw_)]), "cx": np.repeat(dn.complexity_score.values, L)}).groupby(["e", "w"]).agg(n=("cx", "size"), cx=("cx", "mean"))
    parts = []; us = np.arange(NW) / (NW - 1)
    for g in teams:
        p = TP[g]; ix = np.nonzero((emp.department == g).values)[0]; n = len(ix); con = emp.contracted_hours.values[ix]; abp = np.array([fv(p["ab"], u) for u in us]); absent = r.random((n, NW)) < abp[None, :]
        ah = np.minimum(r.choice([8, 16, 24, 40], (n, NW), p=[.35, .35, .15, .15]), con[:, None]) * absent; ct = np.where(absent, r.choice(["Planned leave", "Sick leave", "Other"], (n, NW), p=[.6, .3, .1]), ""); s = absent.mean(0)
        cover = np.minimum(6, 20 * s / (1 - s + .01)); otm = np.array([fv(p["ot"], u) for u in us]); ef = r.lognormal(0, .25, n)
        if p["conc"]: ef[:3] = 6.0
        extra = np.maximum(r.normal(otm[None, :] * ef[:, None] + cover[None, :], 2.5), 0) * (~absent); actual = np.round(con[:, None] - ah + extra, 1); ot = np.round(np.maximum(actual - con[:, None], 0), 1)
        planned = con[:, None] - ah * (ct == "Planned leave"); miss = r.random((n, NW)) < .015
        parts.append(pd.DataFrame({"e": np.repeat(ix, NW), "w": np.tile(np.arange(NW), n), "planned": planned.ravel(), "actual": actual.ravel(), "ot": ot.ravel(), "avail": np.where(miss, np.nan, con[:, None] - ah).ravel(), "sched": np.repeat(con, NW), "abs": np.where(miss, np.nan, ah).ravel(), "cat": ct.ravel(), "miss": miss.ravel()}))
    wl = pd.concat(parts, ignore_index=True).join(act, on=["e", "w"]); ids_ = emp.employee_id.values[wl["e"].values]; dd_ = T0 + pd.to_timedelta(wl["w"] * 7, unit="D")
    W = pd.DataFrame(dict(employee_id=ids_, date=dd_, planned_hours=wl["planned"].round(1), actual_hours=wl["actual"], overtime_hours=wl["ot"], active_task_count=wl["n"].fillna(0), task_complexity_score=wl["cx"].round(2), available_capacity_hours=wl["avail"]))
    A = pd.DataFrame(dict(employee_id=ids_, date=dd_, scheduled_hours=wl["sched"], absence_hours=wl["abs"], absence_category=np.where(wl["abs"] > 0, wl["cat"], None), attendance_record_status=np.where(wl["miss"], "Missing", "Recorded")))
    mo = pd.date_range("2025-11-01", periods=12, freq="MS"); dep_ = emp.set_index("employee_id").department; ot_t = W.assign(g=dep_.reindex(W.employee_id).values, m=W.date.dt.strftime("%Y-%m")).groupby(["g", "m"]).overtime_hours.mean(); eg = []
    for g in teams:
        for m in mo:
            o = ot_t.get((g, m.strftime("%Y-%m")), 3.0); resp = r.random() > .04
            eg.append(dict(team_id=g, survey_date=m + pd.Timedelta(days=14), engagement_score=round(float(np.clip(74 - 1.5 * o + r.normal(0, 2), 20, 98)), 1) if resp else np.nan, workload_sustainability_score=round(float(np.clip(78 - 3 * o + r.normal(0, 3), 10, 98)), 1) if resp else np.nan, survey_response_status="Complete" if resp else "No response"))
    td = tk[tk.completed_date.notna()].assign(m=lambda x: x.completed_date.dt.strftime("%Y-%m"), wgt=lambda x: x.complexity_score / 3, cyc=lambda x: (x.completed_date - x.created_date).dt.days, rwk=lambda x: x.rework_count > 0)
    pf = td.groupby(["team_id", "m"]).agg(tasks_completed=("task_id", "size"), rework_rate=("rwk", "mean"), cycle_time=("cyc", "median"), output_measure=("wgt", "sum")).reset_index().rename(columns={"m": "observation_period"})
    pf["quality_score"] = (96 - 60 * pf.rework_rate + r.normal(0, 1.5, len(pf))).clip(0, 100).round(1)
    return dict(emp=emp, work=W, tasks=tk, deps=pd.DataFrame(deps, columns=["predecessor_task_id", "successor_task_id", "dependency_type", "blocking_duration"]), att=A, eng=pd.DataFrame(eg), perf=pf)
def get_demo_raw():
    if "raw" not in _DEMO: _DEMO["raw"] = make_data()
    return _DEMO["raw"]
def get_demo():
    if "D" not in _DEMO: _DEMO["D"] = load_all(get_demo_raw())
    return _DEMO["D"]

# ------------------------------ ingestion and validation ------------------------------
SPEC = {
 "emp": {"employee_id": ("s", 1, ["emp_id", "staff_id", "id"]), "department": ("s", 1, ["dept", "team"]), "role": ("s", 0, ["job_role", "title"]), "employment_type": ("s", 0, ["contract_type"]), "contracted_hours": ("n", 1, ["weekly_hours", "contract_hours"]), "location": ("s", 0, []), "tenure_band": ("s", 0, ["tenure"])},
 "work": {"employee_id": ("s", 1, ["emp_id", "staff_id"]), "date": ("d", 1, ["week", "week_start", "week_commencing"]), "planned_hours": ("n", 1, ["planned"]), "actual_hours": ("n", 1, ["hours_worked", "worked_hours"]), "overtime_hours": ("n", 0, ["overtime", "ot_hours"]),
          "active_task_count": ("n", 0, ["active_tasks", "wip"]), "task_complexity_score": ("n", 0, ["avg_complexity"]), "available_capacity_hours": ("n", 0, ["capacity_hours", "available_hours"])},
 "tasks": {"task_id": ("s", 1, ["id"]), "team_id": ("s", 1, ["team", "department"]), "assigned_employee_id": ("s", 0, ["employee_id", "assignee"]), "project_id": ("s", 0, ["project"]), "task_category": ("s", 1, ["category", "task_type", "process"]), "priority": ("n", 1, []), "estimated_hours": ("n", 1, ["estimate_hours", "estimated"]),
           "actual_hours": ("n", 0, ["actual"]), "created_date": ("d", 1, ["created"]), "start_date": ("d", 0, ["started"]), "due_date": ("d", 0, ["due"]), "completed_date": ("d", 0, ["completed", "closed_date"]), "status": ("s", 0, []), "complexity_score": ("n", 0, ["complexity"]),
           "rework_count": ("n", 0, ["reworks"]), "blocked_hours": ("n", 0, ["blocked"])},
 "deps": {"predecessor_task_id": ("s", 1, ["predecessor", "blocker_task_id"]), "successor_task_id": ("s", 1, ["successor", "blocked_task_id"]), "dependency_type": ("s", 0, []), "blocking_duration": ("n", 0, ["blocking_hours"])},
 "att": {"employee_id": ("s", 1, ["emp_id"]), "date": ("d", 1, ["week", "week_start"]), "scheduled_hours": ("n", 1, ["scheduled"]), "absence_hours": ("n", 0, ["absence", "absent_hours"]), "absence_category": ("s", 0, ["absence_type"]), "attendance_record_status": ("s", 0, ["record_status"])},
 "eng": {"team_id": ("s", 0, ["team", "department"]), "employee_id": ("s", 0, []), "survey_date": ("d", 1, ["date"]), "engagement_score": ("n", 0, ["engagement"]), "workload_sustainability_score": ("n", 0, ["sustainability"]), "survey_response_status": ("s", 0, ["response_status"])},
 "perf": {"team_id": ("s", 0, ["team", "department"]), "employee_id": ("s", 0, []), "observation_period": ("s", 1, ["period"]), "tasks_completed": ("n", 0, []), "quality_score": ("n", 0, []), "rework_rate": ("n", 0, []), "cycle_time": ("n", 0, []), "output_measure": ("n", 0, [])}}
TN = dict(emp="employees", work="workload_observations", tasks="task_records", deps="task_dependencies", att="attendance", eng="engagement", perf="performance")
RANGE = dict(priority=(1, 10), complexity_score=(0, 10), engagement_score=(0, 100), workload_sustainability_score=(0, 100), quality_score=(0, 100), rework_rate=(0, 1), contracted_hours=(0, 80))
XR = dict(tasks=[("completed before created", lambda d: d.completed_date < d.created_date), ("start before created", lambda d: d.start_date < d.created_date), ("completed before start", lambda d: d.completed_date < d.start_date),
                 ("due before created", lambda d: d.due_date < d.created_date), ("estimated_hours must be above 0", lambda d: d.estimated_hours <= 0)],
          work=[("overtime_hours above actual_hours", lambda d: d.overtime_hours > d.actual_hours + 1e-9), ("actual_hours above 168 per week", lambda d: d.actual_hours > 168)],
          att=[("absence_hours above scheduled_hours", lambda d: d.absence_hours > d.scheduled_hours)], deps=[("task depends on itself", lambda d: d.predecessor_task_id == d.successor_task_id)])
KEY = dict(emp=["employee_id"], work=["employee_id", "date"], tasks=["task_id"], deps=["predecessor_task_id", "successor_task_id"], att=["employee_id", "date"])
def parse_map(text):
    ov = {}
    for p in re.split(r"[,;\n]", text or ""):
        if "=" in p: k, v = p.split("=", 1); ov[norm(k)] = norm(v)
    return ov
def map_cols(raw, t, ov, iss):
    d = raw.copy(); d.columns = [norm(c) for c in d.columns]; ren = {}
    for f, (k, req, al) in SPEC[t].items():
        c = ov.get(t + "_" + f) or ov.get(f); c = c if c in d.columns else next((a for a in [f] + al if a in d.columns and a not in ren), None)
        if c is None or c in ren:
            if req: iss.append(("error", "%s table: required field '%s' not found. Columns found: %s. Use the mapping box, e.g. %s=your_column." % (TN[t], f, ", ".join(map(str, raw.columns[:12])), f)))
            continue
        if c != f and f in d.columns: d = d.drop(columns=[f])
        ren[c] = f
    d = d.rename(columns=ren); return d.loc[:, ~d.columns.duplicated()]
def rows_txt(ix): return ", ".join(str(int(i)) for i in ix[:6]) + (" (+%d more)" % (len(ix) - 6) if len(ix) > 6 else "")
def ctab(raw, t, ov, iss, ex):
    d = map_cols(raw, t, ov, iss)
    if any(l == "error" for l, _ in iss): return d
    d = d.copy(); d["_row"] = d.index + 2; bad = pd.Series(False, index=d.index)
    for f, (k, req, al) in SPEC[t].items():
        if f not in d.columns: d[f] = np.nan
        elif k == "n": d[f] = to_num(d[f])
        elif k == "d": d[f] = to_dt(d[f])
        else: d[f] = clean_str(d[f])
    def flag(m, why):
        nonlocal bad
        m = m.fillna(False) & ~bad
        if m.any(): ex.append((TN[t], why, int(m.sum()))); iss.append(("warn", "%s: %d rows excluded: %s (rows %s)" % (TN[t], m.sum(), why, rows_txt(d["_row"][m].values)))); bad = bad | m
    for f, (k, req, al) in SPEC[t].items():
        if req: flag(d[f].isna(), "missing " + f)
        if k == "n":
            flag(d[f] < 0, "negative " + f)
            if f in RANGE: flag((d[f] < RANGE[f][0]) | (d[f] > RANGE[f][1]), "%s outside %s-%s" % (f, RANGE[f][0], RANGE[f][1]))
    for why, fn in XR.get(t, []): flag(fn(d), why)
    if t in KEY: flag(d.duplicated(KEY[t], keep="first"), "duplicate " + "+".join(KEY[t]))
    return d[~bad].drop(columns="_row").reset_index(drop=True)
def load_all(raw, mapping=""):
    iss, ex, ov, D = [], [], parse_map(mapping), {}; rows_in = {t: len(raw[t]) for t in SPEC if raw.get(t) is not None}
    for t in ("emp", "work", "tasks"):
        if raw.get(t) is None: iss.append(("error", "Missing required table: %s." % TN[t]))
    if any(l == "error" for l, _ in iss): raise ValueError(" | ".join(m for l, m in iss if l == "error"))
    for t in rows_in: D[t] = ctab(raw[t], t, ov, iss, ex)
    errs = [m for l, m in iss if l == "error"]
    if errs: raise ValueError(" | ".join(errs))
    E = D["emp"]
    if E.empty: raise ValueError("No valid employees remain after validation.")
    if D["tasks"].empty: raise ValueError("No valid task records remain after validation.")
    Wd = D["work"]; n0 = len(Wd); Wd = Wd[Wd.employee_id.isin(E.employee_id)].reset_index(drop=True)
    if len(Wd) < n0: iss.append(("warn", "%d workload rows excluded: employee not in the employee table." % (n0 - len(Wd)))); ex.append((TN["work"], "unknown employee", n0 - len(Wd)))
    if Wd.empty: raise ValueError("No valid workload observations remain after validation.")
    dept = E.set_index("employee_id").department; con = E.set_index("employee_id").contracted_hours; Wd["dept"] = Wd.employee_id.map(dept); Wd["contr"] = Wd.employee_id.map(con)
    nm = Wd.overtime_hours.isna()
    if nm.any(): Wd.loc[nm, "overtime_hours"] = (Wd.actual_hours - Wd.contr).clip(lower=0)[nm]; iss.append(("info", "%d workload rows had no overtime_hours: derived as max(actual - contracted, 0)." % nm.sum()))
    A = D.get("att")
    if A is not None and len(A):
        A = A[A.employee_id.isin(E.employee_id)].copy(); A["dept"] = A.employee_id.map(dept); st = A.attendance_record_status.fillna("Recorded").astype(str).str.lower(); A["rec"] = (~st.str.contains("miss")) & A.absence_hours.notna()
        k = Wd[["employee_id", "date"]].merge(A[["employee_id", "date", "scheduled_hours", "absence_hours", "rec"]], on=["employee_id", "date"], how="left"); m = (Wd.available_capacity_hours.isna() & k.rec.fillna(False).astype(bool).values)
        Wd.loc[m, "available_capacity_hours"] = (k.scheduled_hours - k.absence_hours)[m].values
        if (~A.rec).any(): iss.append(("info", "%d attendance rows are missing or unrecorded: absence and capacity stay unknown for them (never treated as zero absence)." % (~A.rec).sum()))
    else: A = None; iss.append(("info", "No attendance table: absence analysis is unavailable and utilisation uses only the available_capacity_hours you supplied."))
    Tk = D["tasks"]; okE = Tk.assigned_employee_id.isin(E.employee_id); nb = int((Tk.assigned_employee_id.notna() & ~okE).sum())
    if nb: iss.append(("warn", "%d tasks reference employees not in the employee table: assignee left blank (tasks kept)." % nb))
    T = pd.DataFrame(dict(tid=Tk.task_id, dept=Tk.team_id, emp=Tk.assigned_employee_id.where(okE), cat=Tk.task_category, prio=Tk.priority, est=Tk.estimated_hours, act=Tk.actual_hours, created=Tk.created_date, start=Tk.start_date, due=Tk.due_date, comp=Tk.completed_date, status=Tk.status, cx=Tk.complexity_score, rwc=Tk.rework_count, blocked=Tk.blocked_hours, project=Tk.project_id))
    if T.cx.isna().any(): iss.append(("info", "%d tasks have no complexity_score: they get weight 1 in complexity-adjusted output." % T.cx.isna().sum()))
    dp = None
    if D.get("deps") is not None and len(D["deps"]):
        dd = D["deps"]; ok = dd.predecessor_task_id.isin(T.tid) & dd.successor_task_id.isin(T.tid)
        if (~ok).any(): iss.append(("warn", "%d dependencies reference unknown task ids and were excluded." % (~ok).sum())); ex.append((TN["deps"], "unknown task ids", int((~ok).sum())))
        dd = dd[ok]; ct = T.set_index("tid").comp; pc_, sc_ = dd.predecessor_task_id.map(ct), dd.successor_task_id.map(ct); bad = pc_.notna() & sc_.notna() & (sc_ < pc_)
        if bad.any(): iss.append(("warn", "%d dependencies have a successor completed before its predecessor (kept, flagged as inconsistent)." % bad.sum()))
        dp = dd.rename(columns=dict(predecessor_task_id="pred", successor_task_id="succ", blocking_duration="blk", dependency_type="typ")).reset_index(drop=True)
    else: iss.append(("info", "No dependency records: dependency analysis is downgraded to aggregate indicators (blocked_hours)."))
    unk = sorted(set(T.dept) - set(E.department))
    if unk: iss.append(("warn", "Task team_id values not found among employee departments: %s." % ", ".join(map(str, unk[:5]))))
    if len(T) < 200 or Wd.date.nunique() < 12: iss.append(("warn", "Small dataset (%d tasks, %d weeks): trend and bottleneck results are unreliable." % (len(T), Wd.date.nunique())))
    W = Wd.rename(columns=dict(employee_id="eid", planned_hours="planned", actual_hours="actual", overtime_hours="ot", active_task_count="act_tasks", task_complexity_score="cxs", available_capacity_hours="avail"))
    if A is not None: A = A.rename(columns=dict(employee_id="eid", scheduled_hours="sched", absence_hours="abs"))
    return dict(T=T, W=W, A=A, dp=dp, emp=E, eng=D.get("eng"), perf=D.get("perf"), issues=iss, excluded=ex, rows_in=rows_in)

# ------------------------------ metric engine ------------------------------
def trend(y, mn=12):
    y = pd.Series(y, dtype=float).replace([np.inf, -np.inf], np.nan).dropna(); n = len(y)
    if n < mn: return dict(lab="insufficient data", pct=np.nan, p=np.nan)
    if y.std() == 0: return dict(lab="no sustained trend", pct=0.0, p=1.0)
    r = stats.linregress(np.arange(n), y.values); pct = r.slope * (n - 1) / (abs(y.mean()) or 1.0)
    return dict(lab="rising" if (r.pvalue < .05 and pct > .1) else "falling" if (r.pvalue < .05 and pct < -.1) else "no sustained trend", pct=float(pct), p=float(r.pvalue))
def runs(M):
    best = np.zeros(M.shape[0], int); cur_ = np.zeros(M.shape[0], int)
    for j in range(M.shape[1]): cur_ = np.where(M[:, j], cur_ + 1, 0); best = np.maximum(best, cur_)
    return best
def derive(T, S, base):
    T = T.copy(); T["done"] = T.comp.notna(); T["cyc"] = (T.comp - T.created).dt.days; T["wait"] = (T.start - T.created).dt.days; T["proc"] = (T.comp - T.start).dt.days
    T["ontime"] = (T.comp <= T.due).astype(float).where(T.done & T.due.notna()); T["rw"] = T.rwc.fillna(0) > 0; T["cw"] = ((T.cx.fillna(3) / 3).clip(lower=.1)) ** S["cwx"]
    T["cd"] = (T.created - base).dt.days; T["wkc"] = wk(T.created); T["wkf"] = wk(T.comp); return T
def weekly(T, W, A, wks, base, S):
    dps = sorted(set(T.dept.dropna()) | set(W.dept.dropna())); o = pd.DataFrame(index=pd.MultiIndex.from_product([dps, wks], names=["dept", "wk"]))
    def ag(df, key, **kw):
        g = df.groupby(["dept", key]).agg(**kw); g.index.names = ["dept", "wk"]; return g
    o = o.join(ag(T, "wkc", created=("tid", "size"), cs=("cd", "sum"))); Td = T[T.done]
    o = o.join(ag(Td, "wkf", completed=("tid", "size"), cw=("cw", "sum"), ontime=("ontime", "sum"), due_n=("ontime", "count"), rwn=("rw", "sum"), est_h=("est", "sum"), act_h=("act", "sum"), cs_d=("cd", "sum")))
    Wx = W.assign(over_ot=(W.ot > S["ot_h"]).astype(float), over_tk=(W.act_tasks > S["task_thr"]).astype(float), act_av=W.actual.where(W.avail.notna()))
    o = o.join(ag(Wx, "wk", planned=("planned", "sum"), actual=("actual", "sum"), ot=("ot", "sum"), contr=("contr", "sum"), rows=("actual", "size"), over_ot=("over_ot", "sum"), over_tk=("over_tk", "sum"), avail=("avail", "sum"), act_av=("act_av", "sum"), n_av=("avail", "count"), act_tasks=("act_tasks", "mean")))
    if A is not None and len(A): Ax = A.assign(sched_rec=A.sched.where(A.rec), abs_rec=A["abs"].where(A.rec)); o = o.join(ag(Ax, "wk", sched_rec=("sched_rec", "sum"), absn=("abs_rec", "sum")))
    for c in ["created", "cs", "completed", "cw", "ontime", "due_n", "rwn", "est_h", "act_h", "cs_d"]: o[c] = o[c].fillna(0)
    for c in ["sched_rec", "absn"]:
        if c not in o: o[c] = np.nan
    g = o.groupby(level="dept"); o["open"] = g["created"].cumsum() - g["completed"].cumsum(); ed = np.asarray((o.index.get_level_values("wk") + pd.Timedelta(days=6) - base).days)
    o["age_sum"] = (ed * o["open"] - (g["cs"].cumsum() - g["cs_d"].cumsum())).where(o["open"] > 0, 0.0); return o
def kpi(V):
    tw, T = V["tw"], V["T"]; g = tw.groupby(level="wk").sum(min_count=1); s = g.sum(min_count=1); Tc = T[T.done]; last = g.iloc[-1]
    return dict(completed=float(s.completed), cw=float(s.cw), actual=s.actual, planned=s.planned, contr=s.contr, oph=ratio(s.cw, s.actual), opp=ratio(s.cw, s.planned), ontime=ratio(s.ontime, s.due_n), rework=ratio(s.rwn, s.completed), effv=(ratio(s.act_h, s.est_h) - 1) if s.est_h else np.nan,
                open=float(last.open), age=ratio(last.age_sum, last.open), ot=s.ot, otp=ratio(s.ot, s.contr), util=ratio(s.act_av, s.avail), absr=ratio(s.absn, s.sched_rec), created=float(s.created), cyc_med=Tc.cyc.median() if len(Tc) else np.nan)
def view(dep=None, cat=None, d1="", d2=""):
    D, S = G["D"], G["S"]; key = (tuple(sorted(dep or [])), tuple(sorted(cat or [])), d1 or "", d2 or "", json.dumps(S, sort_keys=True, default=str))
    if key in G["_vc"]: return G["_vc"][key]
    T, W, A = D["T"], D["W"], D["A"]; depts = sorted(set(T.dept.dropna()) | set(W.dept.dropna())); sel = [x for x in (dep or []) if x in depts] or depts
    T = T[T.dept.isin(sel)]; W = W[W.dept.isin(sel)]; A = A[A.dept.isin(sel)] if A is not None else None
    if cat: T = T[T.cat.isin(cat)]
    if T.empty or W.empty: raise ValueError("No data matches the selected filters.")
    lo = min(W.date.min(), T.created.min()); hi = max(W.date.max(), T.created.max(), T.comp.max() if T.comp.notna().any() else lo)
    D1 = pd.to_datetime(d1, errors="coerce") if d1 else pd.NaT; D2 = pd.to_datetime(d2, errors="coerce") if d2 else pd.NaT; w1 = wk1(D1 if pd.notna(D1) else lo); w2 = wk1(D2 if pd.notna(D2) else hi)
    if w1 > w2: raise ValueError("The 'from' date is after the 'to' date.")
    base = wk1(lo); wks = pd.date_range(base, wk1(hi), freq="7D"); W = W.assign(wk=wk(W.date)); A = A.assign(wk=wk(A.date)) if A is not None else None
    Tf = derive(T, S, base); tw = weekly(Tf, W, A, wks, base, S); lv = tw.index.get_level_values("wk"); tw = tw[(lv >= w1) & (lv <= w2)]
    if tw.empty: raise ValueError("No weeks fall inside the selected date range.")
    end = w2 + pd.Timedelta(days=6); Tp = Tf[(Tf.created <= end) & ~(Tf.comp < w1)].copy(); Tp.loc[Tp.comp > end, "comp"] = pd.NaT; Tp.loc[Tp.comp.isna(), "act"] = np.nan; Tp.loc[Tp.start > end, "start"] = pd.NaT; Tp = derive(Tp, S, base)
    dp = D["dp"]
    if dp is not None and len(dp):
        ci = D["T"].set_index("tid"); dp = dp[dp.succ.isin(Tp.tid)].assign(pcat=lambda x: x.pred.map(ci.cat), pdept=lambda x: x.pred.map(ci.dept), sdept=lambda x: x.succ.map(ci.dept), scat=lambda x: x.succ.map(ci.cat)); dp["blk"] = dp.blk.fillna(dp.succ.map(Tp.set_index("tid").blocked))
    else: dp = None
    V = dict(S=S, T=Tp, W=W[(W.wk >= w1) & (W.wk <= w2)], A=A[(A.wk >= w1) & (A.wk <= w2)] if A is not None else None, tw=tw, depts=sorted(set(tw.index.get_level_values("dept"))), w1=w1, w2=w2, base=base, end=end, dp=dp, dep_out=dp.groupby("pred").size() if dp is not None and len(dp) else pd.Series(dtype=float))
    V["k"] = kpi(V); V["F"] = score_f(detect(V), S); G["_vc"][key] = V; return V
def team_patterns(V):
    rows = []
    for g, t in V["tw"].groupby(level="dept"):
        t = t.droplevel("dept"); th, to, tp_, tb = trend(t.actual), trend(t.cw), trend(t.cw / t.actual.replace(0, np.nan)), trend(t.open)
        pat = ("High effort, falling output per hour" if th["lab"] == "rising" and tp_["lab"] == "falling" else "Rising hours, output not rising" if th["lab"] == "rising" and to["lab"] != "rising" else "Output decline" if to["lab"] == "falling" else
               "Growing backlog" if tb["lab"] == "rising" else "Backlog falling (improvement)" if tb["lab"] == "falling" else "No sustained pattern")
        rows.append(dict(team=g, hrs=th["lab"], hp=th["pct"], out=to["lab"], op=to["pct"], oph=tp_["lab"], bk=tb["lab"], bp=tb["pct"], pattern=pat))
    return pd.DataFrame(rows)
def team_prod(V):
    tw, T, rows = V["tw"], V["T"], []; pf = G["D"].get("perf")
    for g, t in list(tw.groupby(level="dept")) + [("All teams", tw)]:
        Tc = T[T.done & ((T.dept == g) if g != "All teams" else True)]; s = t.sum(min_count=1); one = (g != "All teams"); op = t.droplevel("dept").open if one else t.groupby(level="wk").open.sum(); ag_ = t.droplevel("dept").age_sum if one else t.groupby(level="wk").age_sum.sum(); q = np.nan
        if pf is not None and len(pf):
            x = pf[pf.team_id == g] if one else pf; x = x[(x.observation_period >= V["w1"].strftime("%Y-%m")) & (x.observation_period <= V["w2"].strftime("%Y-%m"))]
            if x.quality_score.notna().any(): q = float(np.average(x.quality_score.dropna(), weights=x.tasks_completed[x.quality_score.notna()].fillna(1)))
        rows.append(dict(team=g, completed=s.completed, cw=s.cw, actual=s.actual, planned=s.planned, oph=ratio(s.cw, s.actual), opp=ratio(s.cw, s.planned), ontime=ratio(s.ontime, s.due_n), cyc=Tc.cyc.median() if len(Tc) else np.nan, p90=Tc.cyc.quantile(.9) if len(Tc) else np.nan,
                         rework=ratio(s.rwn, s.completed), effv=(ratio(s.act_h, s.est_h) - 1) if s.est_h else np.nan, open=float(op.iloc[-1]), age=ratio(ag_.iloc[-1], op.iloc[-1]), quality=q))
    return pd.DataFrame(rows)
def team_work(V):
    tw, W, S = V["tw"], V["W"], V["S"]; rows = []
    for g, t in tw.groupby(level="dept"):
        t = t.droplevel("dept"); Wg = W[W.dept == g]; P_ = Wg.pivot_table(index="eid", columns="wk", values="ot", aggfunc="sum").fillna(0); sus = int((runs(P_.values > S["ot_h"]) >= S["run"]).sum()) if P_.size else 0; va = Wg[Wg.avail.notna()]
        rows.append(dict(team=g, contr=t.contr.sum(), planned=t.planned.sum(), actual=t.actual.sum(), ot=t.ot.sum(), otp=ratio(t.ot.sum(), t.contr.sum()), util=ratio(t.act_av.sum(), t.avail.sum()), tasks=Wg.act_tasks.mean(), pot=ratio(t.over_ot.sum(), t.rows.sum()), ptk=ratio(t.over_tk.sum(), t.rows.sum()),
                         sus=sus, nemp=Wg.eid.nunique(), idle=float(np.maximum(va.avail - va.actual, 0).sum()), absr=ratio(t.absn.sum(min_count=1), t.sched_rec.sum(min_count=1))))
    return pd.DataFrame(rows)
def monthly(V):
    x = V["tw"].reset_index(); x["m"] = x.wk.dt.strftime("%Y-%m"); a = x.groupby(["dept", "m"]).agg(ot=("ot", "sum"), contr=("contr", "sum"), cw=("cw", "sum"), rwn=("rwn", "sum"), comp=("completed", "sum"), open=("open", "last")).reset_index()
    a["otp"] = a.ot / a.contr.replace(0, np.nan); a["rwr"] = a.rwn / a.comp.replace(0, np.nan); a["cw_next"] = a.groupby("dept").cw.shift(-1); E = G["D"].get("eng")
    if E is not None and len(E): e = E.assign(dept=E.team_id, m=E.survey_date.dt.strftime("%Y-%m")).groupby(["dept", "m"]).agg(eng=("engagement_score", "mean")).reset_index(); a = a.merge(e, on=["dept", "m"], how="left")
    else: a["eng"] = np.nan
    return a
def corr(x, y, mn=10):
    d = pd.concat([x.reset_index(drop=True), y.reset_index(drop=True)], axis=1).dropna()
    if len(d) < mn or d.iloc[:, 0].nunique() < 3 or d.iloc[:, 1].nunique() < 3: return None
    r = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1]); return dict(rho=float(r[0]), p=float(r[1]), n=len(d))

# ------------------------------ bottleneck detection and priority score ------------------------------
NXT = {"Capacity bottleneck": "Compare intake with sustained capacity; test temporary capacity or an intake limit.", "Excessive overtime": "Review which work drives the overtime and who carries it; protect recovery time.", "Workload imbalance": "Check task eligibility and headroom, then rebalance within the team (see Scenario Lab).",
       "Approval or handoff delay": "Map the approval step, measure queue time per approver and test an SLA or delegation.", "Task dependency blockage": "Inspect the recurring predecessor tasks and decouple or reorder them.", "Rework and quality bottleneck": "Sample reworked tasks and classify why they came back.",
       "Absence-related coverage gap": "Identify critical tasks without backup and plan cross-training (aggregate view only).", "Task prioritisation issue": "Audit how priority is assigned and how the queue is ordered.", "Skill or task-complexity mismatch": "Review who is eligible for complex tasks; plan mentoring or cross-training.",
       "Uncertain or insufficient evidence": "Collect dependency, blocked-reason and handoff data before intervening."}
APR = r"approv|sign|author|hand|review|check"
def comps(sc, V, med, end):
    d = sc.done; op = sc[~d]; late = int((d & (sc.ontime == 0)).sum() + ((~d) & (sc.due < end)).sum())
    return dict(delayed=late, blocked=float(sc.blocked.fillna(0).sum()), cycle=float(np.clip(sc.loc[d, "cyc"] - med, 0, None).sum()) if d.any() else 0.0, crit=float(((5 - sc.prio.clip(1, 4)) / 4).mean()) if len(sc) else 0.0, age=float((end - op.created).dt.days.mean()) if len(op) else 0.0, down=int(V["dep_out"].reindex(sc.tid).fillna(0).sum() + len(op)))
def detect(V):
    S, T, W, tw, dp, end = V["S"], V["T"], V["W"], V["tw"], V["dp"], V["end"]; F = []; Ta = T[T.done]; med = float(Ta.cyc.median()) if len(Ta) else 0.0
    for g in V["depts"]:
        t = tw.xs(g, level="dept"); Tg = T[T.dept == g]; Tc = Tg[Tg.done]; Wg = W[W.dept == g]
        if len(Tg) < 10 or len(t) < 4: continue
        n0 = len(F)
        def add(cat, proc, ev, mask, rec, cave=""):
            sc = Tg[mask] if (mask is not None and mask.any()) else Tg
            F.append(dict(team=g, cat=cat, proc=proc, evidence=ev, recur=float(rec) if pd.notna(rec) else 0.0, n=len(sc), weeks=len(t), nxt=NXT[cat], caveat=cave, comp=comps(sc, V, med, end)))
        u = ratio(t.act_av.sum(), t.avail.sum()); sl = trend(t.open)
        if pd.notna(u) and u >= S["util"] and sl["lab"] == "rising": add("Capacity bottleneck", "team-wide", "Utilisation is %s of available capacity (hours worked ÷ contracted minus recorded absence); open backlog went from %s to %s tasks (%s, p=%s)." % (pc0(u), nf(t.open.iloc[0]), nf(t.open.iloc[-1]), sl["lab"], fx(sl["p"], 3)), None, (t.act_av / t.avail.replace(0, np.nan) >= S["util"]).mean())
        P_ = Wg.pivot_table(index="eid", columns="wk", values="ot", aggfunc="sum").fillna(0); sus = (runs(P_.values > S["ot_h"]) >= S["run"]) if P_.size else np.zeros(0, bool); sh = float(sus.mean()) if len(sus) else np.nan; otp = ratio(t.ot.sum(), t.contr.sum())
        if (pd.notna(otp) and otp >= S["ot_pct"]) or (pd.notna(sh) and sh >= .25):
            add("Excessive overtime", "team-wide", "Overtime is %s of contracted hours; %d of %d employees (%s) worked more than %.0f overtime hours per week for %d or more consecutive weeks." % (pc1(otp), int(sus.sum()), len(sus), pc0(sh), S["ot_h"], S["run"]), Tg.emp.isin(set(P_.index[sus])), (t.ot / t.contr.replace(0, np.nan) >= S["ot_pct"]).mean(), "Overtime is a workload indicator, not a measure of fatigue or commitment.")
        eo = Wg.groupby("eid").ot.sum().sort_values(ascending=False)
        if len(eo) >= 8 and eo.sum() >= 50:
            top = eo.head(int(math.ceil(.2 * len(eo)))); sh2 = top.sum() / eo.sum()
            if sh2 >= S["conc"]:
                s1 = Wg[Wg.eid.isin(top.index)].groupby("wk").ot.sum(); s2 = Wg.groupby("wk").ot.sum()
                add("Workload imbalance", "team-wide", "The top 20%% of employees (%d of %d) carry %s of the team's overtime hours." % (len(top), len(eo), pc0(sh2)), Tg.emp.isin(top.index), (s1.reindex(s2.index).fillna(0) / s2.replace(0, np.nan) >= S["conc"]).mean(), "Employee-level data is used only to compute this aggregate share.")
        bl = Tg[Tg.blocked.fillna(0) > 0]; bsh = ratio(bl.blocked.sum() / 24.0, Tc.cyc.sum() if len(Tc) else 0); dg = dp[dp.sdept == g] if dp is not None and len(dp) else None
        if len(bl) >= 20 and pd.notna(bsh) and bsh >= S["blk"]:
            isap = Tc.cat.str.contains(APR, case=False, na=False); wa, wo = Tc[isap].wait.mean(), Tc[~isap].wait.mean(); cave = ""
            if dg is not None and len(dg):
                tp = dg.groupby("pcat").agg(h=("blk", "sum"), n=("blk", "size"), m=("blk", "mean")).sort_values("h", ascending=False); pcat = str(tp.index[0]); rp = int((dg.groupby("pred").size() >= 3).sum()); cat_ = "Approval or handoff delay" if re.search(APR, pcat, re.I) else "Task dependency blockage"; proc = pcat
                ev = "%d tasks (%s) were blocked for %s hours in total, equal to %s of completed-task cycle days; main blocking category: %s (%d dependencies, mean %.0f h); %d predecessor tasks each hold up 3 or more successors; approval-type tasks wait %s days vs %s for other tasks." % (len(bl), pc0(len(bl) / len(Tg)), nf(bl.blocked.sum()), pc0(bsh), pcat, int(tp.n.iloc[0]), tp.m.iloc[0], rp, fx(wa), fx(wo))
            else:
                cat_, proc = "Task dependency blockage", "tasks with blocked hours"; ev = "%d tasks (%s) report %s blocked hours, equal to %s of completed-task cycle days." % (len(bl), pc0(len(bl) / len(Tg)), nf(bl.blocked.sum()), pc0(bsh)); cave = "Dependency records are unavailable: aggregate indicator from blocked_hours only."
            add(cat_, proc, ev, Tg.blocked.fillna(0) > 0, (Tg.groupby("wkc").blocked.apply(lambda s: int((s.fillna(0) > 0).sum())).reindex(t.index).fillna(0) >= 3).mean(), cave)
        n = len(Tc)
        if n >= 60:
            Ts = Tc.sort_values("comp"); k3 = n // 3; r1, r2, rr = Ts.head(k3).rw.mean(), Ts.tail(k3).rw.mean(), Tc.rw.mean()
            if rr >= S["rw"] or r2 - r1 >= .05: add("Rework and quality bottleneck", "team-wide", "%s of completed tasks needed rework (first third of the period %s, last third %s); mean rework cycles per task %.2f; actual effort is %s above the estimate." % (pc1(rr), pc1(r1), pc1(r2), Tc.rwc.mean(), pc0(ratio(Tc.act.sum(), Tc.est.sum()) - 1)), Tg.rw, (t.rwn / t.completed.replace(0, np.nan) >= S["rw"]).mean())
        ar = t.absn / t.sched_rec.replace(0, np.nan); hi_ = (ar >= S["absr"]).fillna(False).astype(bool); dop = t.open.diff()
        if hi_.sum() >= 3 and (~hi_).sum() >= 3:
            dh, dl = dop[hi_].mean(), dop[~hi_].mean()
            if pd.notna(dh) and pd.notna(dl) and dh - dl >= .5: add("Absence-related coverage gap", "team-wide", "%d weeks had recorded absence of %s or more of scheduled hours; backlog changed by %+.1f tasks per week in those weeks versus %+.1f in other weeks." % (int(hi_.sum()), pc0(S["absr"]), dh, dl), Tg.wkc.isin(t.index[hi_]), hi_.mean(), "Aggregate association only; individual absence is never analysed and legitimate leave is not a performance issue.")
        a_, b_ = Tc[Tc.prio <= 2], Tc[Tc.prio >= 3]
        if len(a_) >= 30 and len(b_) >= 30:
            ra = a_.cyc.median() / max(b_.cyc.median(), 1e-9); oa, ob = a_.ontime.mean(), b_.ontime.mean()
            if ra >= .95 and (pd.isna(oa) or pd.isna(ob) or oa <= ob + .02): add("Task prioritisation issue", "queue ordering", "Priority 1-2 tasks took a median of %s days versus %s for priority 3-4 (ratio %.2f) and were on time %s versus %s: urgent work is not moving faster." % (fx(a_.cyc.median(), 0), fx(b_.cyc.median(), 0), ra, pc0(oa), pc0(ob)), Tg.prio <= 2, (a_.groupby("wkf").ontime.mean() < .8).mean())
        hc = Tg[(Tg.cx >= 4) & Tg.emp.notna()]; ne = Tg.emp.nunique()
        if len(hc) >= 40 and ne >= 8:
            top = hc.emp.value_counts().head(max(1, int(round(.1 * ne)))); sh3 = top.sum() / len(hc)
            if sh3 >= S["conc"]: add("Skill or task-complexity mismatch", "complex tasks (score 4 or more)", "%s of complex tasks (%d) went to the top 10%% of assignees (%d of %d employees)." % (pc0(sh3), len(hc), len(top), ne), Tg.cx >= 4, (hc.assign(z=hc.emp.isin(top.index)).groupby("wkc").z.mean() >= S["conc"]).mean(), "Eligibility rules are not in the data: concentration may be legitimate.")
        so = trend(t.cw)
        if so["lab"] == "falling" and len(F) == n0: add("Uncertain or insufficient evidence", "team-wide", "Weekly output fell (%+.0f%% over the period, p=%s) but no bottleneck category reached its evidence threshold." % (100 * so["pct"], fx(so["p"], 3)), None, 0.0, "Do not infer a cause: collect more process data.")
    return F
def score_f(F, S):
    if not F: return pd.DataFrame()
    d = pd.DataFrame(F); c = pd.DataFrame(list(d.comp)); c["recur"] = d.recur.values; w = S["w"]; sw = sum(w.values()) or 1.0
    for k in w:
        if k not in c: c[k] = 0.0
        mx = c[k].max(); d["c_" + k] = c[k].values; d["n_" + k] = (c[k] / mx).values if (pd.notna(mx) and mx > 0) else 0.0
    d["score"] = 100 * sum(w[k] * d["n_" + k] for k in w) / sw
    d["conf"] = np.where((d.n >= 100) & (d.weeks >= 26), "High", np.where((d.n >= 30) & (d.weeks >= 12), "Moderate", "Low")); return d.sort_values("score", ascending=False).reset_index(drop=True)

# ------------------------------ interventions ------------------------------
INT = {"Capacity bottleneck": ("Demand exceeds sustained capacity.", "Add temporary capacity or cap intake and work in progress; protect recovery time.", "More hours or fewer concurrent tasks raise throughput and shrink queues.", 20, "4-8 weeks", "Backlog, cycle time, on-time rate", "Extra headcount cost; intake limits may delay other teams."),
 "Excessive overtime": ("Sustained overtime may signal under-resourcing or poor flow (not a diagnosis of fatigue).", "Review overtime drivers, rebalance or add capacity, and protect recovery time.", "Lower sustained overtime while keeping output.", 10, "4-6 weeks", "Overtime %, employees with 4+ week runs, output per hour", "Output may fall if hours are cut without removing work."),
 "Workload imbalance": ("A few employees carry a large share of overtime.", "Redistribute eligible work to colleagues with headroom and set per-person WIP limits.", "Spreads load without adding hours.", 8, "2-4 weeks", "Share of overtime held by the top 20%, employees over threshold", "Receivers may become overloaded; eligibility and skills must be checked."),
 "Approval or handoff delay": ("Approval queues delay dependent tasks.", "Simplify or delegate approvals, set approval time targets, batch or auto-approve low-risk items.", "Less waiting shortens end-to-end cycle time.", 12, "4-8 weeks", "Blocked hours, approval wait, cycle time", "Weaker control if approvals are removed without safeguards."),
 "Task dependency blockage": ("Recurring predecessor tasks hold up downstream work.", "Decouple or reorder recurring predecessors and add early warning on blocked tasks.", "Fewer blocked hours and smoother flow.", 12, "4-8 weeks", "Blocked hours, share of blocked tasks, cycle time", "Reordering can shift the delay elsewhere."),
 "Rework and quality bottleneck": ("Rework consumes capacity and delays delivery.", "Add upstream quality checks, clarify acceptance criteria and review rework root causes.", "Fewer rework cycles free capacity.", 15, "6-10 weeks", "Rework rate, effort variance, cycle time", "Extra checks can add handoffs and delay."),
 "Absence-related coverage gap": ("Absence weeks coincide with backlog growth.", "Cross-train staff and define backup coverage for critical tasks.", "Covered tasks continue during absence.", 20, "8-12 weeks", "Backlog change in high-absence weeks, backup coverage", "Training time reduces capacity short term; never penalise legitimate leave."),
 "Task prioritisation issue": ("Urgent tasks are not completed faster than low-priority ones.", "Reorder the queue (urgent first), limit low-value work and review how priority is assigned.", "Urgent work moves ahead of low-value work.", 6, "2-4 weeks", "Priority 1-2 cycle time and on-time rate", "Low-priority work may starve; priorities may be mis-set."),
 "Skill or task-complexity mismatch": ("Complex tasks are concentrated on a few people.", "Cross-train and spread complex work with mentoring; review allocation rules.", "Reduces single points of failure and queues.", 15, "6-12 weeks", "Share of complex tasks held by the top 10%, cycle time of complex tasks", "Quality may dip during knowledge transfer."),
 "Uncertain or insufficient evidence": ("Output falls but no cause is evident in the data.", "Collect dependency, blocked-reason and handoff data and run a short diagnostic review.", "Better evidence before intervening.", 5, "2-4 weeks", "Data coverage; diagnostic completed", "Acting without evidence may waste effort.")}
RCOLS = ["rank", "finding", "evidence", "hypothesis", "intervention", "target", "mechanism", "effort_days", "est_cost", "horizon", "kpis", "risks", "measurement", "status"]
def recs(V):
    F = V["F"]
    if F is None or not len(F): return pd.DataFrame(columns=RCOLS)
    rows = []; rv = (V["end"] + pd.Timedelta(days=28)).strftime("%Y-%m-%d")
    for i, r in F.head(12).iterrows():
        h, act, mech, eff, hz, kp_, risk = INT[r.cat]
        rows.append(dict(rank=i + 1, finding="%s: %s" % (r.team, r.cat), evidence=r.evidence + " Confidence: %s (%d tasks, %d weeks)." % (r.conf, r.n, r.weeks), hypothesis=h + " (hypothesis, not an established cause)", intervention=act, target="%s / %s" % (r.team, r.proc), mechanism=mech, effort_days=eff,
                         est_cost=eff * 8 * V["S"]["hrate"], horizon=hz, kpis=kp_, risks=risk, measurement="Baseline = the 8 weeks before the change. Track %s weekly for the target team, compare with a similar team that did not change, and review on or after %s." % (kp_, rv), status="Proposed: needs human review"))
    return pd.DataFrame(rows, columns=RCOLS)

# ------------------------------ redistribution and scenario engine ------------------------------
def redistribute(load, cap, dept, pct, S):
    L = np.array(load, float).copy(); cap = np.asarray(cap, float); dept = np.asarray(dept); moved = 0.0; unpl = 0.0
    for g in np.unique(dept):
        m = dept == g; l = L[m]; c = cap[m]; ex = np.maximum(l - S["over"] * c, 0); mv = np.minimum(pct * l * (ex > 0), ex); hd = np.maximum(S["recv"] * c - l, 0) * (ex <= 0); tot = min(mv.sum(), hd.sum())
        if tot <= 0 or mv.sum() <= 0: unpl += mv.sum(); continue
        L[m] = l - mv * (tot / mv.sum()) + hd * (tot / hd.sum()); moved += tot; unpl += mv.sum() - tot
    return L, moved, unpl
def baseline(V, N):
    tw, W, S = V["tw"], V["W"], V["S"]; g = tw.groupby(level="wk").sum(min_count=1).tail(N); Nw = len(g)
    if Nw < 4: raise ValueError("At least 4 weeks of data are needed for a scenario baseline.")
    cut = g.index.min(); Tw = V["T"][V["T"].done & (V["T"].comp >= cut)]
    if len(Tw) < 10: raise ValueError("Fewer than 10 completed tasks in the baseline window: scenarios would not be reliable.")
    h0 = Tw.act.mean(); H0 = g.actual.mean(); mu0 = g.completed.mean(); ps = ratio(mu0 * h0, H0)
    if nul(ps) or ps <= 0: raise ValueError("Task hours cannot be related to hours worked in this window.")
    sc = ratio(g.rows.sum(), g.n_av.sum()); Hreg = g.avail.sum() * (sc if pd.notna(sc) else 1) / Nw; Wn = W[W.wk >= cut]
    em = Wn.groupby("eid").agg(load=("actual", "mean"), cap=("avail", "mean"), con=("contr", "mean"), dept=("dept", "first")); em["cap"] = em.cap.fillna(em.con); rwh = float(np.minimum(Tw.est * S["rwc"] * Tw.rwc.fillna(0), Tw.act).mean()); p12 = Tw[Tw.prio <= 2]
    return dict(lam=float(g.created.mean()), mu0=float(mu0), B0=float(g.open.iloc[-1]), h0=float(h0), H0=float(H0), ps=float(ps), Hreg=float(Hreg), ot0=float(g.ot.mean()), abs=float(g.absn.mean()) if g.absn.notna().any() else 0.0, rwh=rwh, wait=float(Tw.wait.mean()), wait12=float(p12.wait.mean()) if len(p12) else np.nan,
                cyc12=float(p12.cyc.mean()) if len(p12) else np.nan, cyc=float(Tw.cyc.mean()), act=float(Wn.act_tasks.mean()) if Wn.act_tasks.notna().any() else np.nan, load=em.load.values, cap=em.cap.values, dept=em.dept.values, N=Nw, util=ratio(g.act_av.sum(), g.avail.sum()), ovl=float(np.maximum(em.load.values - S["over"] * em.cap.values, 0).sum()))
def flow(lam, cap, b0, n):
    b = b0; bs = []; th = []
    for _ in range(n): x = min(cap, b + lam); b = b + lam - x; bs.append(b); th.append(x)
    return np.array(bs), np.array(th)
ZERO = dict(rd=0, wr=0, rw=0, add=0, otc=0, wip=0, mt=0, xc=0, pr=0, impl=0)
def sim_one(B, P, ad, S):
    z = lambda v: 0.0 if nul(v) else float(v); n = int(P["weeks"]); h1 = max(B["h0"] - B["rwh"] * P["rw"] / 100 * ad, .1)
    if P["wip"] > 0 and not nul(B["act"]) and B["act"] > P["wip"]: h1 *= 1 - P["mt"] / 100 * ad * min(1.0, (B["act"] - P["wip"]) / B["act"])
    cov = z(B["abs"]) * P["xc"] / 100 * ad; H1 = max(B["H0"] + P["add"] + cov - B["ot0"] * P["otc"] / 100 * ad, 0.0); Hr1 = B["Hreg"] + cov + P["add"]
    L1, moved, _u = redistribute(B["load"], B["cap"], B["dept"], P["rd"] / 100 * ad, S); cap1 = H1 * B["ps"] / h1; bs, th = flow(B["lam"], cap1, B["B0"], n); tp = float(th.mean())
    cut = z(B["wait"]) * (P["wr"] / 100 * ad + .5 * min(1.0, moved / max(B["ovl"], 1e-9))); ct = 7 * bs.mean() / tp - cut if tp > 0 else np.nan
    c12 = B["cyc12"] - z(B["wait12"]) * (P["wr"] + P["pr"]) / 100 * ad if pd.notna(B["cyc12"]) else np.nan
    return dict(tp=tp, bk=float(bs[-1]), ct=ct, ct12=c12, util=ratio(H1, Hr1), otn=max(B["lam"] * h1 / B["ps"] - Hr1, 0.0), over_n=int((L1 > S["over"] * B["cap"]).sum()), hrs_over=float(np.maximum(L1 - B["cap"], 0).sum()), cost=P["impl"] + P["add"] * n * S["hrate"], traj=bs, moved=moved)
def scenario(B, P, S):
    ad = float(np.clip(P["adopt"], 0, 1)); z0 = dict(ZERO, weeks=P["weeks"]); return dict(base=sim_one(B, z0, 1.0, S), low=sim_one(B, P, ad * .5, S), mid=sim_one(B, P, ad, S), high=sim_one(B, P, min(1.0, ad * 1.25), S))

# ------------------------------ pages ------------------------------
@safe("hppp")
def render_cc(dep, cat, d1, d2):
    V = view(dep, cat, d1, d2); k = V["k"]; F = V["F"]; tw = V["tw"]; tp_ = team_patterns(V); R = recs(V)
    h = banner() + "<div class='kg'>" + card("Output (complexity-weighted)", nf(k["cw"]), "%s tasks completed; weight = (complexity ÷ 3)^%.1f" % (nf(k["completed"]), V["S"]["cwx"])) + card("Output per actual hour", fx(k["oph"], 3), "%s ÷ %s actual hours worked" % (nf(k["cw"]), nf(k["actual"])), C["la"]) + \
        card("Overtime", pc1(k["otp"]), "%s overtime h ÷ %s contracted h" % (nf(k["ot"]), nf(k["contr"])), C["am"]) + card("Capacity utilisation", pc0(k["util"]), "hours worked ÷ (contracted minus recorded absence)", C["am"]) + card("On-time completion", pc0(k["ontime"]), "completed by due date ÷ completed with a due date") + \
        card("Backlog", nf(k["open"]), "open tasks at period end; mean age %s days" % fx(k["age"], 0), C["co"]) + card("Rework rate", pc1(k["rework"]), "completed tasks with rework ÷ completed", C["co"]) + "</div>"
    h += note("Hours worked are never treated as output. Period: %s to %s. Filters apply to every page." % (dts(V["w1"]), dts(V["end"])), "info")
    h += H("Effort versus output by team") + tbl(tp_, [("team", "Team"), ("hrs", "Hours worked"), ("hp", "Change"), ("out", "Output"), ("op", "Change"), ("oph", "Output per hour"), ("bk", "Backlog"), ("bp", "Change"), ("pattern", "Observed pattern")], dict(hp=SIGN, op=SIGN, bp=SIGN)) + note("'Sustained' needs 12+ weeks, p &lt; 0.05 and a change above 10% of the mean; otherwise it is treated as normal fluctuation. Associations, not established causes.", "info")
    h += H("Top operational bottlenecks (priority score = prioritisation aid, not a probability)") + (tbl(F.head(5), [("team", "Team"), ("cat", "Finding"), ("proc", "Process"), ("score", "Priority"), ("conf", "Confidence"), ("evidence", "Evidence")], dict(score=lambda v: fx(v, 0))) if len(F) else note("No bottleneck category reached its evidence threshold in this view.", "ok"))
    h += H("Priority interventions (proposed; human review required)") + (tbl(R.head(3), [("finding", "Finding"), ("intervention", "Intervention"), ("horizon", "Horizon"), ("kpis", "KPIs")]) if len(R) else note("No interventions proposed.", "info"))
    g = tw.groupby(level="wk").sum(min_count=1); f1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.12, subplot_titles=["Hours worked per week (actual)", "Complexity-weighted tasks completed per week"])
    for r_, col, nm, c_ in ((1, "actual", "Actual hours", C["am"]), (2, "cw", "Output", C["mi"])):
        f1.add_trace(go.Scatter(x=g.index, y=g[col], name=nm, line=dict(color=c_, width=1.5), opacity=.6), r_, 1); f1.add_trace(go.Scatter(x=g.index, y=g[col].rolling(4, min_periods=1).mean(), name=nm + " (4-week mean)", line=dict(color=c_, width=3)), r_, 1)
    f1 = sty(f1, 470, "Output versus hours worked (separate panels, no dual axis)")
    f2 = sty(go.Figure([go.Scatter(x=g.index, y=g.created, name="Tasks created", line=dict(color=C["la"])), go.Scatter(x=g.index, y=g.completed, name="Tasks completed", line=dict(color=C["mi"]))]), 340, "Arrivals versus completions per week"); f2.update_yaxes(title="Tasks")
    f3 = sty(go.Figure([go.Scatter(x=t.droplevel("dept").index, y=t.droplevel("dept").open, name=gg) for gg, t in tw.groupby(level="dept")]), 360, "Open backlog by team"); f3.update_yaxes(title="Open tasks"); return h, f1, f2, f3
@safe("hpppp")
def render_prod(dep, cat, d1, d2):
    V = view(dep, cat, d1, d2); P = team_prod(V); S = V["S"]; T = V["T"]; Tc = T[T.done]
    h = banner() + note("<b>Definitions.</b> Output = completed tasks weighted by (complexity ÷ 3)^%.1f (0 = raw count). Output per hour = output ÷ actual hours worked (all recorded hours of the team). Effort variance = actual ÷ estimated hours of completed tasks − 1. Cycle time = created to completed (days). On time = completed on or before due date. Raw counts are not comparable across teams with different complexity." % S["cwx"], "info")
    h += tbl(P, [("team", "Team"), ("completed", "Completed"), ("cw", "Output (weighted)"), ("actual", "Actual hours"), ("oph", "Output ÷ actual h"), ("planned", "Planned hours"), ("opp", "Output ÷ planned h"), ("ontime", "On time"), ("cyc", "Median cycle (d)"), ("p90", "P90 cycle (d)"), ("rework", "Rework"), ("effv", "Effort variance"), ("open", "Backlog"), ("age", "Backlog age (d)"), ("quality", "Quality score")],
                dict(completed=nf, cw=nf, actual=nf, oph=lambda v: fx(v, 3), planned=nf, opp=lambda v: fx(v, 3), ontime=pc0, cyc=lambda v: fx(v, 0), p90=lambda v: fx(v, 0), rework=pc1, effv=SIGN, open=nf, age=lambda v: fx(v, 0), quality=fx))
    m = monthly(V); rows = []
    for lab, x, y in (("Overtime % → next-month output (team-months)", m.otp, m.cw_next), ("Engagement ↔ rework rate", m.eng, m.rwr), ("Engagement ↔ backlog", m.eng, m.open), ("Overtime % ↔ engagement", m.otp, m.eng)):
        c = corr(x, y); rows.append(dict(rel=lab, rho=c["rho"] if c else np.nan, p=c["p"] if c else np.nan, n=c["n"] if c else 0, nt="Spearman rank correlation; association only" if c else "insufficient data (needs 10+ team-months)"))
    h += H("Relationships at team-month level") + tbl(pd.DataFrame(rows), [("rel", "Relationship"), ("rho", "Rho"), ("p", "p-value"), ("n", "n"), ("nt", "Note")], dict(rho=lambda v: fx(v, 2), p=lambda v: fx(v, 3))) + note("Engagement scores are team-level survey signals, not objective measures of effort or capability; no individual condition is inferred. A predictive forecasting model is not part of this build: trends are descriptive.", "warn")
    f1 = sty(go.Figure(go.Histogram(x=Tc.cyc.clip(upper=Tc.cyc.quantile(.99)) if len(Tc) else [], nbinsx=30, marker_color=C["mi"])), 340, "Task cycle-time distribution (days, capped at the 99th percentile)"); f1.update_xaxes(title="Days from created to completed"); f1.update_yaxes(title="Tasks")
    g = V["tw"].groupby(level="wk").sum(min_count=1); wm = Tc.groupby("wkf").cyc.median().reindex(g.index); f2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.14, subplot_titles=["Rework rate (completed tasks with rework)", "Median cycle time of tasks completed that week (days)"])
    f2.add_trace(go.Scatter(x=g.index, y=(g.rwn / g.completed.replace(0, np.nan)).rolling(4, min_periods=1).mean(), line=dict(color=C["co"], width=3), name="Rework (4-week mean)"), 1, 1); f2.add_trace(go.Scatter(x=g.index, y=wm.rolling(4, min_periods=1).mean(), line=dict(color=C["la"], width=3), name="Cycle time (4-week mean)"), 2, 1)
    f2 = sty(f2, 420, "Quality and cycle-time trends"); f2.update_yaxes(tickformat=".0%", row=1, col=1)
    e = V["tw"].groupby(level="dept")[["est_h", "act_h"]].sum().reset_index(); f3 = go.Figure([go.Bar(x=e.dept, y=e.est_h, name="Estimated hours", marker_color=C["mu"]), go.Bar(x=e.dept, y=e.act_h, name="Actual hours", marker_color=C["am"])]); f3.update_layout(barmode="group"); f3 = sty(f3, 340, "Estimated versus actual effort of completed tasks"); f3.update_yaxes(title="Task hours")
    x = V["tw"].reset_index(); x["o"] = x.ot / x.contr.replace(0, np.nan); x["y"] = x.cw / x.actual.replace(0, np.nan)
    f4 = go.Figure([go.Scatter(x=d.o, y=d.y, mode="markers", name=g_, marker=dict(size=6, opacity=.7)) for g_, d in x.groupby("dept")]); f4 = sty(f4, 400, "Overtime share versus output per hour (each point = one team-week)"); f4.update_xaxes(title="Overtime ÷ contracted hours", tickformat=".0%"); f4.update_yaxes(title="Output per actual hour"); return h, f1, f2, f3, f4
@safe("hppp")
def render_wl(dep, cat, d1, d2):
    V = view(dep, cat, d1, d2); Wk = team_work(V); S = V["S"]; tw = V["tw"]
    h = banner() + note("<b>Capacity denominator:</b> contracted hours minus recorded absence (available_capacity_hours). Utilisation = hours worked ÷ that capacity. Overtime % = overtime hours ÷ contracted hours. Thresholds: overtime above %.0f h/week, sustained = %d consecutive weeks, active tasks above %.0f. Sustained pressure is a <b>workload sustainability indicator</b>, not a diagnosis of fatigue or burnout; no employees are ranked." % (S["ot_h"], S["run"], S["task_thr"]), "info")
    h += tbl(Wk, [("team", "Team"), ("planned", "Planned h"), ("actual", "Actual h"), ("ot", "Overtime h"), ("otp", "Overtime %"), ("util", "Utilisation"), ("tasks", "Avg active tasks"), ("pot", "Employee-weeks over OT threshold"), ("ptk", "Employee-weeks over task threshold"), ("sus", "Employees with sustained overtime"), ("nemp", "Employees"), ("idle", "Unallocated capacity h"), ("absr", "Absence rate")],
                dict(planned=nf, actual=nf, ot=nf, otp=pc1, util=pc0, tasks=fx, pot=pc0, ptk=pc0, sus=nf, nemp=nf, idle=nf, absr=pc1)) + note("Absence figures are aggregate and exclude unrecorded weeks. Legitimate leave is never treated as a performance issue.", "warn")
    x = tw.reset_index(); x["m"] = x.wk.dt.strftime("%Y-%m"); pv = x.groupby(["dept", "m"]).apply(lambda d: ratio(d.ot.sum(), d.contr.sum())).unstack("m")
    f1 = sty(go.Figure(go.Heatmap(z=pv.values, x=list(pv.columns), y=list(pv.index), colorscale=[[0, C["sf"]], [.5, C["am"]], [1, C["co"]]], colorbar=dict(title="OT %", tickformat=".0%"), hovertemplate="%{y} %{x}: %{z:.1%}<extra></extra>")), 400, "Overtime heatmap: overtime ÷ contracted hours by team and month")
    Wd = V["W"].groupby("eid").agg(ot=("ot", "mean"), dept=("dept", "first")); f2 = go.Figure([go.Box(y=d.ot, name=g_, boxmean=True) for g_, d in Wd.groupby("dept")]); f2 = sty(f2, 380, "Distribution of employees' mean weekly overtime within each team (no individual named)"); f2.update_yaxes(title="Overtime h / week")
    f3 = empty("No attendance data")
    if V["A"] is not None and tw.absn.notna().any(): a = tw.reset_index(); a["ar"] = a.absn / a.sched_rec.replace(0, np.nan); a = a.groupby(["wk"]).apply(lambda d: ratio(d.absn.sum(), d.sched_rec.sum())); o = tw.groupby(level="wk").open.sum(); f3 = make_subplots(specs=[[{"secondary_y": True}]]); f3.add_trace(go.Bar(x=a.index, y=a.values, name="Absence rate", marker_color=C["la"]), secondary_y=False); f3.add_trace(go.Scatter(x=o.index, y=o.values, name="Open backlog", line=dict(color=C["co"], width=3)), secondary_y=True); f3 = sty(f3, 360, "Aggregate absence rate and backlog (two axes: read each separately)"); f3.update_yaxes(tickformat=".0%", secondary_y=False); f3.update_yaxes(title="Open tasks", secondary_y=True)
    return h, f1, f2, f3
@safe("hppp")
def render_bn(dep, cat, d1, d2):
    V = view(dep, cat, d1, d2); F = V["F"]; S = V["S"]; T = V["T"]
    h = banner() + note("Findings come from documented rules (see Methodology). Each shows evidence, period, magnitude, confidence and a next step. <b>Priority score</b> = weighted blend of normalised components (delayed tasks, blocked hours, cycle-time excess, criticality, backlog age, recurrence, downstream scope); it ranks attention and is <b>not a validated probability</b>. Findings are hypotheses to investigate.", "info")
    if len(F):
        h += tbl(F, [("team", "Team"), ("cat", "Category"), ("proc", "Process"), ("score", "Priority"), ("conf", "Confidence"), ("evidence", "Evidence"), ("nxt", "Next step"), ("caveat", "Caveat")], dict(score=lambda v: fx(v, 0)))
        h += H("Score components (raw value; weight in brackets)") + tbl(F.head(10), [("team", "Team"), ("cat", "Category")] + [("c_" + k, "%s (%.2f)" % (k, S["w"][k])) for k in S["w"]], {"c_" + k: (lambda v: fx(v, 1)) for k in S["w"]})
    else: h += note("No bottleneck category reached its evidence threshold in this view.", "ok")
    if V["dp"] is None: h += note("No dependency data: analysis is limited to aggregate indicators (blocked_hours); a process map cannot be built.", "warn")
    g = T[T.done].groupby("dept").agg(w=("wait", "mean"), p=("proc", "mean")).reset_index(); f1 = go.Figure([go.Bar(x=g.dept, y=g.w, name="Waiting (created → started)", marker_color=C["am"]), go.Bar(x=g.dept, y=g.p, name="Processing (started → completed)", marker_color=C["mi"])]); f1.update_layout(barmode="stack"); f1 = sty(f1, 360, "Mean waiting versus processing days of completed tasks"); f1.update_yaxes(title="Days")
    b = T.groupby("dept").blocked.sum().sort_values(ascending=False); f2 = sty(go.Figure(go.Bar(x=b.index, y=b.values, marker_color=C["co"])), 340, "Blocked hours by team"); f2.update_yaxes(title="Hours")
    f3 = empty("No dependency data for a flow diagram"); dp = V["dp"]
    if dp is not None and len(dp):
        a = dp.groupby(["pcat", "sdept"]).blk.sum().reset_index().sort_values("blk", ascending=False).head(15); L = list(pd.unique(list(a.pcat) + ["→ " + x for x in a.sdept])); ix = {n: i for i, n in enumerate(L)}
        f3 = go.Figure(go.Sankey(node=dict(label=L, color=C["la"], pad=14), link=dict(source=[ix[x] for x in a.pcat], target=[ix["→ " + x] for x in a.sdept], value=list(a.blk), color="rgba(143,227,181,.35)"))); f3 = sty(f3, 420, "Blocked hours flowing from predecessor task category to the team they hold up")
    return h, f1, f2, f3
@safe("hp")
def render_exp(dep, cat, d1, d2, by, auth):
    V = view(dep, cat, d1, d2); col = {"Team": "dept", "Task category": "cat", "Priority": "prio", "Complexity score": "cx"}[by or "Team"]; rows = []
    for k_, x in V["T"].groupby(col):
        c = x[x.done]; rows.append(dict(grp=k_, created=len(x), completed=len(c), open=int((~x.done).sum()), cyc=c.cyc.median(), p90=c.cyc.quantile(.9), ontime=c.ontime.mean(), rework=c.rw.mean(), blocked=x.blocked.sum(), wait=c.wait.mean(), proc=c.proc.mean(), effv=ratio(c.act.sum(), c.est.sum()) - 1))
    t = pd.DataFrame(rows); h = banner() + note("Aggregated view by %s. Workload versus capacity per team is on the Workload Health page." % esc(by), "info") + tbl(t, [("grp", by), ("created", "Created"), ("completed", "Completed"), ("open", "Open"), ("cyc", "Median cycle (d)"), ("p90", "P90 (d)"), ("ontime", "On time"), ("rework", "Rework"), ("blocked", "Blocked h"), ("wait", "Avg wait (d)"), ("proc", "Avg processing (d)"), ("effv", "Effort variance")],
                                                                                                    dict(created=nf, completed=nf, open=nf, cyc=lambda v: fx(v, 0), p90=lambda v: fx(v, 0), ontime=pc0, rework=pc1, blocked=nf, wait=fx, proc=fx, effv=SIGN))
    d = V["T"].sort_values(["cyc", "created"], ascending=[False, True], na_position="first").head(60); cols = [("tid", "Task"), ("dept", "Team"), ("cat", "Category"), ("prio", "Priority"), ("created", "Created"), ("due", "Due"), ("comp", "Completed"), ("status", "Status"), ("cyc", "Cycle (d)"), ("wait", "Wait (d)"), ("blocked", "Blocked h"), ("rwc", "Rework")] + ([("emp", "Assignee")] if auth else [])
    h += H("Drill-down: slowest tasks (assignee hidden unless authorised)") + tbl(d, cols, dict(created=dts, due=dts, comp=dts, cyc=lambda v: fx(v, 0), wait=lambda v: fx(v, 0), blocked=nf, rwc=nf))
    if auth: h += note("Employee-level detail is shown for an authorised operational purpose only. Do not use it to rank or discipline employees.", "warn")
    f = go.Figure([go.Bar(x=t.grp.astype(str), y=t.wait, name="Avg waiting days", marker_color=C["am"]), go.Bar(x=t.grp.astype(str), y=t.proc, name="Avg processing days", marker_color=C["mi"])]); f.update_layout(barmode="stack"); return h, sty(f, 360, "Waiting versus processing by " + (by or "team"))
@safe("h")
def render_int(dep, cat, d1, d2):
    V = view(dep, cat, d1, d2); R = recs(V)
    if R.empty: return (note("No interventions are proposed because no finding reached its evidence threshold.", "info"),)
    h = banner() + note("<b>Observed evidence → analytical interpretation → proposed action</b> are kept separate. Mechanisms are hypotheses; nothing here claims an intervention will cause a specific improvement. Cost = effort days × 8 h × hourly rate (editable in settings). Human review required.", "ai")
    for r in R.itertuples(): h += "<div class='tw'><table><tr><th colspan='2'>%d. %s</th></tr>" % (r.rank, esc(r.finding)) + "".join("<tr><td style='width:190px'>%s</td><td>%s</td></tr>" % (a, esc(b)) for a, b in [("Evidence (observed)", r.evidence), ("Operational hypothesis", r.hypothesis), ("Proposed intervention", r.intervention), ("Target", r.target), ("Expected mechanism", r.mechanism), ("Effort / est. cost", "%d days / %s" % (r.effort_days, money(r.est_cost))), ("Time horizon", r.horizon), ("Success KPIs", r.kpis), ("Risks and unintended consequences", r.risks), ("Follow-up measurement", r.measurement), ("Status", r.status)]) + "</table></div>"
    return (h,)
def int_df(dep, cat, d1, d2):
    try: return recs(view(dep, cat, d1, d2))[["rank", "finding", "intervention", "kpis", "status"]]
    except Exception: return pd.DataFrame(columns=["rank", "finding", "intervention", "kpis", "status"])
@safe("hpp")
def render_scn(dep, cat, d1, d2, N, wks, rd, wr, rw, add, otc, wip, mt, xc, pr, impl, adopt):
    V = view(dep, cat, d1, d2); S = V["S"]; B = baseline(V, int(N)); P = dict(weeks=int(wks), rd=float(rd or 0), wr=float(wr or 0), rw=float(rw or 0), add=float(add or 0), otc=float(otc or 0), wip=float(wip or 0), mt=float(mt or 0), xc=float(xc or 0), pr=float(pr or 0), impl=float(impl or 0), adopt=float(adopt or 0) / 100); R = scenario(B, P, S); b, m, lo, hi = R["base"], R["mid"], R["low"], R["high"]
    rows = [("Estimated throughput (tasks/week)", fx(b["tp"]), fx(lo["tp"]), fx(m["tp"]), fx(hi["tp"])), ("Projected backlog at horizon (tasks)", nf(b["bk"]), nf(lo["bk"]), nf(m["bk"]), nf(hi["bk"])), ("Expected cycle time (days, Little's law)", fx(b["ct"]), fx(lo["ct"]), fx(m["ct"]), fx(hi["ct"])), ("Priority 1-2 cycle time (days)", fx(b["ct12"]), fx(lo["ct12"]), fx(m["ct12"]), fx(hi["ct12"])),
            ("Capacity utilisation (hours worked ÷ regular hours)", pc0(b["util"]), pc0(lo["util"]), pc0(m["util"]), pc0(hi["util"])), ("Overtime needed to sustain arrivals (h/week)", nf(b["otn"]), nf(lo["otn"]), nf(m["otn"]), nf(hi["otn"])), ("Employees above the load limit (after redistribution)", nf(b["over_n"]), nf(lo["over_n"]), nf(m["over_n"]), nf(hi["over_n"])),
            ("Work moved by redistribution (h/week)", fx(b["moved"]), fx(lo["moved"]), fx(m["moved"]), fx(hi["moved"])), ("Cost (implementation + extra hours)", money(0), money(lo["cost"]), money(m["cost"]), money(hi["cost"]))]
    h = banner() + note("<b>Hypothetical scenario, not a forecast and not an implemented change.</b> Baseline = the last %d weeks of the active filter (arrivals %.1f/week, %s open tasks, %s hours/week). Throughput = hours × task-hours per worked hour ÷ hours per task. Redistribution moves load only from employees above %.0f%% of capacity to teammates in the same team up to %.0f%% of capacity; it never loads an already-overloaded employee, and eligibility, skills and dependencies are <b>not</b> in the data, so check them before acting. Low/high use 50%% and 125%% of the adoption rate." % (B["N"], B["lam"], nf(B["B0"]), nf(B["H0"]), 100 * S["over"], 100 * S["recv"]), "warn")
    h += tbl(pd.DataFrame(rows, columns=["m", "b", "l", "s", "hh"]), [("m", "Metric"), ("b", "Baseline"), ("l", "Scenario: low adoption"), ("s", "Scenario: base adoption"), ("hh", "Scenario: high adoption")], dict(b=str, l=str, s=str, hh=str))
    if P["rd"] > 0 and m["moved"] < 1: h += note("Little or no work could be redistributed: there is not enough headroom among teammates, so more capacity (not reshuffling) would be needed.", "warn")
    x = np.arange(1, P["weeks"] + 1); f1 = go.Figure([go.Scatter(x=x, y=b["traj"], name="Baseline", line=dict(color=C["mu"], width=3)), go.Scatter(x=x, y=hi["traj"], name="Scenario (high adoption)", line=dict(color=C["la"], dash="dot")), go.Scatter(x=x, y=lo["traj"], name="Scenario (low adoption)", line=dict(color=C["la"], dash="dot"), fill="tonexty", fillcolor="rgba(211,181,255,.12)"), go.Scatter(x=x, y=m["traj"], name="Scenario (base adoption)", line=dict(color=C["mi"], width=3))])
    f1 = sty(f1, 380, "Projected backlog: baseline vs hypothetical scenario"); f1.update_xaxes(title="Weeks ahead"); f1.update_yaxes(title="Open tasks")
    f2 = go.Figure([go.Bar(x=["Throughput", "Cycle time (d)", "Utilisation ×10", "Overtime needed (h÷10)"], y=[v for v in (b["tp"], b["ct"], 10 * (b["util"] or 0), b["otn"] / 10)], name="Baseline", marker_color=C["mu"]), go.Bar(x=["Throughput", "Cycle time (d)", "Utilisation ×10", "Overtime needed (h÷10)"], y=[m["tp"], m["ct"], 10 * (m["util"] or 0), m["otn"] / 10], name="Scenario (base)", marker_color=C["mi"])]); f2.update_layout(barmode="group"); f2 = sty(f2, 340, "Baseline versus scenario (rescaled for comparison)"); G["scn"] = rows; return h, f1, f2
@safe("hh")
def render_dq():
    D = G["D"]; h = banner() + note("Rows read per table: " + ", ".join("%s %s" % (TN[k], nf(v)) for k, v in D["rows_in"].items()) + ". Raw uploads are never modified: a separate validated copy is analysed. Excluded rows: <b>%d</b> entries (listed below; nothing is dropped silently)." % sum(c for _, _, c in D["excluded"]), "ok")
    h += "".join(note(esc(m), "err" if l == "error" else "warn" if l == "warn" else "info") for l, m in D["issues"]) or note("No validation issues.", "ok")
    if D["excluded"]: h += H("Excluded rows by reason") + tbl(pd.DataFrame(D["excluded"], columns=["t", "w", "c"]), [("t", "Table"), ("w", "Reason"), ("c", "Rows")], dict(c=nf))
    return h, H("Self-test results (run at start-up)") + "".join(note(("PASS " if ok else "FAIL ") + esc(g + ": " + n) + " — " + esc(d), "ok" if ok else "err") for g, n, ok, d in TESTS)

# ------------------------------ strategist ------------------------------
def t_sum(V): k = V["k"]; return "Period %s to %s: %s weighted output from %s completed tasks; %s output per actual hour; overtime %s of contracted hours; utilisation %s; on-time %s; backlog %s open tasks; rework %s." % (dts(V["w1"]), dts(V["end"]), nf(k["cw"]), nf(k["completed"]), fx(k["oph"], 3), pc1(k["otp"]), pc0(k["util"]), pc0(k["ontime"]), nf(k["open"]), pc1(k["rework"]))
def t_bn(V): F = V["F"]; return "Top bottlenecks (prioritisation score, not a probability): " + ("; ".join("%s: %s (score %.0f, %s confidence) — %s" % (r.team, r.cat, r.score, r.conf, r.evidence) for r in F.head(3).itertuples()) if len(F) else "none reached the evidence threshold") + "."
def t_why(V):
    P = team_patterns(V); x = P[P.pattern.isin(["High effort, falling output per hour", "Rising hours, output not rising"])]; return "Teams where hours rise but output does not: " + ("; ".join("%s (hours %s, output per hour %s)" % (r.team, SIGN(r.hp), r.oph) for r in x.itertuples()) if len(x) else "none show a sustained pattern") + ". " + t_bn(V) + " These are associations; the data cannot prove cause."
def t_blk(V):
    b = V["T"].groupby("dept").blocked.sum().sort_values(ascending=False); s = "Blocked hours by team: " + "; ".join("%s %s h" % (k, nf(v)) for k, v in b.head(3).items()) + "."
    dp = V["dp"]
    if dp is not None and len(dp): a = dp.groupby("pcat").blk.sum().sort_values(ascending=False); s += " Largest blocking predecessor category: %s (%s h)." % (a.index[0], nf(a.iloc[0]))
    return s
def t_gap(V): W = team_work(V).sort_values("util", ascending=False); return "Teams by utilisation (hours worked ÷ available capacity): " + "; ".join("%s %s (overtime %s)" % (r.team, pc0(r.util), pc1(r.otp)) for r in W.head(4).itertuples()) + "."
def t_red(V, pct=10):
    B = baseline(V, 12); R = scenario(B, dict(ZERO, weeks=8, rd=pct, adopt=1.0), V["S"]); b, m = R["base"], R["mid"]; return "Hypothetical: redistributing %.0f%% of overloaded employees' work within teams moves about %s h/week; employees above the load limit change from %s to %s, cycle time %s to %s days. Throughput changes only through the assumed waiting-time effect, and eligibility is not checked." % (pct, fx(m["moved"]), nf(b["over_n"]), nf(m["over_n"]), fx(b["ct"]), fx(m["ct"]))
def t_choose(V):
    F = V["F"]; c = F.cat.value_counts() if len(F) else pd.Series(dtype=int); cap = int(c.get("Capacity bottleneck", 0) + c.get("Excessive overtime", 0)); pr_ = int(sum(c.get(k, 0) for k in ("Approval or handoff delay", "Task dependency blockage", "Rework and quality bottleneck"))); po = int(c.get("Task prioritisation issue", 0))
    return "Findings by type: capacity/overtime %d, process friction (approval, dependency, rework) %d, prioritisation %d. " % (cap, pr_, po) + ("Process simplification is the better first test where process friction dominates; add capacity only where utilisation is above the threshold and backlog is rising; change priorities where urgent work is not moving faster." if len(F) else "No finding reached its threshold, so no option is supported by this data.")
def t_lim(): return "Limitations: associations are not causes; scenarios are hypothetical; engagement is a team-level survey signal; task eligibility, skills and approval chains are not fully in the data; the priority score is a prioritisation aid; no individual is assessed. Data notes: " + " | ".join(m for _, m in G["D"]["issues"][:3])
def ask(q, use_llm=False):
    if "D" not in G: return "Load data first."
    V = view(None, None, "", ""); q = (q or "").strip() or "Why is productivity falling while overtime is rising?"; ql = q.lower(); parts = []
    if re.search(r"why|falling|decline|overtime|productiv", ql): parts.append(("trend_analysis", t_why(V)))
    if re.search(r"block|workflow|approval|delay|handoff", ql): parts.append(("blocked_hours_analysis", t_blk(V)))
    if re.search(r"backlog|explain", ql): parts.append(("backlog_analysis", t_bn(V) + " Backlog now %s open tasks." % nf(V["k"]["open"])))
    if re.search(r"gap|capacity|workload", ql): parts.append(("capacity_gap", t_gap(V)))
    m = re.search(r"(\d+)\s*%", ql)
    if re.search(r"redistribut|rebalanc|what would happen|what if", ql): parts.append(("scenario_simulation", t_red(V, float(m.group(1)) if m else 10.0)))
    if re.search(r"should we|simplif|add capacity|priorit|intervention|recommend", ql): parts.append(("intervention_choice", t_choose(V)))
    if re.search(r"limit|caveat|trust", ql): parts.append(("limitations", t_lim()))
    if not parts: parts = [("summary", t_sum(V)), ("bottlenecks", t_bn(V))]
    ctx = "\n".join("[%s] %s" % (n, t) for n, t in parts); out = "### Answer (deterministic, computed by analytical tools)\n" + "\n".join("- **%s**: %s" % (n, t) for n, t in parts) + "\n\n*Every figure comes from the loaded data or is labelled hypothetical. Human review is required before material workforce decisions.*"
    if not use_llm: return out
    k = os.environ.get("ANTHROPIC_API_KEY")
    if not k: return out + "\n\n*External LLM is disabled: no ANTHROPIC_API_KEY environment variable is set. The deterministic answer is complete.*"
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": k, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={"model": "claude-sonnet-5-5", "max_tokens": 800, "system": "You are an operations analytics assistant. Answer ONLY from the TOOL RESULTS. Never invent numbers or causes. Be concise.", "messages": [{"role": "user", "content": "TOOL RESULTS:\n" + ctx + "\n\nQUESTION: " + q}]}, timeout=60); r.raise_for_status()
        return "### LLM-written answer (aggregated tool results only)\n" + "".join(b.get("text", "") for b in r.json().get("content", [])) + "\n\n---\n" + out
    except Exception as e: return out + "\n\n*LLM call failed (%s); deterministic answer shown.*" % type(e).__name__

# ------------------------------ exports ------------------------------
def export_all(dep, cat, d1, d2):
    if "D" not in G: return None, note("Load data first.", "info")
    V = view(dep, cat, d1, d2); out = []
    def w(df, fn):
        df.to_csv(fn, index=False)
        if os.path.exists(fn): out.append(fn)
    w(team_prod(V), "tempo_productivity_metrics.csv"); w(team_work(V), "tempo_workload_overtime.csv"); w(V["tw"].reset_index()[["dept", "wk", "sched_rec", "absn"]].rename(columns={"sched_rec": "scheduled_hours_recorded", "absn": "absence_hours_recorded"}), "tempo_absence_coverage.csv")
    w(V["T"][["tid", "dept", "cat", "prio", "created", "due", "comp", "status", "cyc", "wait", "blocked", "rwc"]].rename(columns={"tid": "task_id", "dept": "team_id", "cat": "task_category"}).assign(is_open=lambda x: x.comp.isna()), "tempo_task_delays_backlog.csv")
    F = V["F"].drop(columns=["comp"]) if len(V["F"]) else pd.DataFrame(); w(F, "tempo_bottleneck_findings.csv"); R = recs(V); w(R, "tempo_intervention_recommendations.csv")
    try: B = baseline(V, 12); Rs = scenario(B, dict(ZERO, weeks=8, rd=10, wr=20, adopt=.7), V["S"]); w(pd.DataFrame([dict(scenario=k, throughput=v["tp"], backlog_end=v["bk"], cycle_time=v["ct"], utilisation=v["util"], overtime_needed=v["otn"], cost=v["cost"]) for k, v in Rs.items()]), "tempo_scenario_comparison_example.csv")
    except Exception: pass
    md = ["# TEMPO AI — Executive summary", "", "_Synthetic data; planted patterns._" if G.get("demo") else "", "", "## Observed patterns", t_sum(V), "", t_why(V), "", "## Most material bottlenecks", t_bn(V), "", "## Recommended interventions (proposed, human review required)"] + ["- %s — %s (KPIs: %s; horizon %s)" % (r.finding, r.intervention, r.kpis, r.horizon) for r in R.itertuples()] + ["", "## KPIs and review", "Review the KPIs above weekly; first review on or after %s." % (V["end"] + pd.Timedelta(days=28)).strftime("%Y-%m-%d"), "", "## Assumptions and limitations", t_lim()]
    open("tempo_executive_summary.md", "w", encoding="utf-8").write("\n".join(md)); out.append("tempo_executive_summary.md")
    css = "body{font-family:Inter,Arial,sans-serif;background:#172522;color:#F3F5F0;max-width:980px;margin:30px auto;padding:0 18px}h1{color:#8FE3B5}table{border-collapse:collapse;width:100%;background:#222E2B}th{background:#2c3b37;color:#8FE3B5;text-align:left;padding:8px}td{padding:7px 8px;border-top:1px solid #ffffff14}"
    open("tempo_executive_summary.html", "w", encoding="utf-8").write("<html><head><meta charset='utf-8'><title>TEMPO AI</title><style>" + css + "</style></head><body><h1>TEMPO AI — Executive summary</h1>" + "".join("<p>%s</p>" % esc(x) for x in [t_sum(V), t_why(V), t_bn(V), t_lim()]) + (tbl(R, [("finding", "Finding"), ("intervention", "Intervention"), ("kpis", "KPIs"), ("horizon", "Horizon")]) if len(R) else "") + "</body></html>"); out.append("tempo_executive_summary.html")
    return [f for f in out if os.path.exists(f)], note("Generated %d files from the active dataset and filters (reproducible with the same inputs)." % len(out), "ok")

# ------------------------------ self-tests ------------------------------
def mini_raw():
    emp = pd.DataFrame(dict(employee_id=["A", "B"], department=["X", "X"], contracted_hours=[40.0, 40.0]))
    work = pd.DataFrame(dict(employee_id=["A", "A", "B", "B"], date=["2026-01-05", "2026-01-12"] * 2, planned_hours=[40.0] * 4, actual_hours=[50.0, 40.0, 40.0, 40.0], available_capacity_hours=[40.0] * 4))
    tasks = pd.DataFrame(dict(task_id=["T1", "T2", "T3", "T4"], team_id=["X"] * 4, assigned_employee_id=["A", "A", "B", "B"], task_category=["Build", "Build", "Build", "Approval"], priority=[2, 2, 3, 3], estimated_hours=[4.0, 4.0, 3.0, 2.0], actual_hours=[5.0, 4.0, np.nan, 2.0], created_date=["2026-01-05"] * 4,
                              start_date=["2026-01-06", "2026-01-07", None, "2026-01-06"], due_date=["2026-01-10", "2026-01-12", "2026-01-20", "2026-01-09"], completed_date=["2026-01-07", "2026-01-14", None, "2026-01-08"], status=["Completed", "Completed", "Open", "Completed"], complexity_score=[3] * 4, rework_count=[0, 1, 0, 0], blocked_hours=[0.0] * 4))
    return dict(emp=emp, work=work, tasks=tasks, deps=None, att=None, eng=None, perf=None)
def set_ctx(D, S=None, demo=False): G.clear(); G.update(D=D, S=dict(S or DEF), _vc={}, demo=demo)
def run_selftests(verbose=True):
    if TESTS: return TESTS
    T = []; saved = dict(G)
    def chk(g, n, fn):
        try: ok, d = fn(); T.append((g, n, bool(ok), d))
        except Exception as e: T.append((g, n, False, type(e).__name__ + ": " + str(e)[:90]))
    def v1(): r = mini_raw(); r["tasks"] = r["tasks"].drop(columns=["priority"]); 
    def t_miss():
        r = mini_raw(); r["tasks"] = r["tasks"].drop(columns=["priority"])
        try: load_all(r); return False, "no error"
        except ValueError as e: return "priority" in str(e), "missing column reported with guidance"
    def t_inv():
        r = mini_raw(); r["tasks"] = pd.concat([r["tasks"], r["tasks"].iloc[[0]].assign(task_id="T5", completed_date="2026-01-01"), r["tasks"].iloc[[0]].assign(task_id="T6", estimated_hours=-2), r["tasks"].iloc[[0]]], ignore_index=True); r["work"].loc[0, "actual_hours"] = -3.0
        D = load_all(r); why = {w for _, w, _ in D["excluded"]}; return len(D["T"]) == 4 and any("completed before created" in w for w in why) and any("duplicate" in w for w in why) and any("negative" in w for w in why), "excluded: " + "; ".join(sorted(why))[:90]
    def t_met():
        set_ctx(load_all(mini_raw())); V = view(); k = V["k"]; return abs(k["completed"] - 3) < 1e-9 and abs(k["ontime"] - 2 / 3) < 1e-9 and abs(k["rework"] - 1 / 3) < 1e-9 and abs(k["oph"] - 3 / 170) < 1e-9 and V["T"][V["T"].done].cyc.median() == 3, "completed 3, on-time 67%, rework 33%, output/hour 3/170, median cycle 3 d"
    def t_ot():
        set_ctx(load_all(mini_raw())); k = view()["k"]; return abs(k["otp"] - 10 / 160) < 1e-9 and abs(k["util"] - 170 / 160) < 1e-9, "overtime 6.25% of contracted, utilisation 106.25% of available capacity"
    def t_zero(): return pd.isna(ratio(5, 0)) and pd.isna(ratio(None, 3)) and ratio(6, 3) == 2, "zero or missing denominators give n/a, never 0 or infinity"
    def t_back():
        set_ctx(load_all(mini_raw())); k = view()["k"]; return k["open"] == 1, "created 4 minus completed 3 = backlog 1"
    def t_att(): D = load_all(mini_raw()); return D["A"] is None and any("No attendance" in m for _, m in D["issues"]), "no attendance: absence analysis marked unavailable"
    def t_dep():
        r = mini_raw(); r["deps"] = pd.DataFrame(dict(predecessor_task_id=["T4", "T1", "T9"], successor_task_id=["T2", "T1", "T1"], dependency_type=["FS"] * 3, blocking_duration=[30.0, 5.0, 5.0])); D = load_all(r); return len(D["dp"]) == 1 and D["dp"].blk.iloc[0] == 30, "self-dependency and unknown task excluded; 1 valid dependency kept"
    def t_red():
        S = dict(DEF); L, mv, un = redistribute([60, 30, 50], [40, 40, 40], ["a", "a", "a"], .5, S); return abs(L.sum() - 140) < 1e-9 and L[1] <= S["recv"] * 40 + 1e-9 and abs(mv - 8) < 1e-9 and L[0] < 60 and L[2] < 50, "load conserved; receiver capped at %.0f%% of capacity (moved %.1f h)" % (S["recv"] * 100, mv)
    def t_red2(): L, mv, un = redistribute([60, 58, 70], [40, 40, 40], ["a"] * 3, .5, dict(DEF)); return mv == 0 and list(L) == [60, 58, 70], "no headroom: nothing moved, overload reported unplaced"
    def t_scn():
        D = get_demo(); set_ctx(D, demo=True); V = view(); B = baseline(V, 12); S = V["S"]; R0 = scenario(B, dict(ZERO, weeks=8, adopt=1.0), S); R1 = scenario(B, dict(ZERO, weeks=8, add=200, adopt=1.0), S)
        return abs(R0["mid"]["tp"] - R0["base"]["tp"]) < 1e-9 and R1["mid"]["tp"] >= R0["mid"]["tp"] and R1["mid"]["bk"] <= R0["mid"]["bk"] + 1e-9 and R1["mid"]["cost"] > 0, "zero levers reproduce baseline; +200 h/week lifts throughput %.1f -> %.1f at a cost" % (R0["mid"]["tp"], R1["mid"]["tp"])
    def t_empty():
        r = mini_raw(); r["tasks"] = r["tasks"].iloc[0:0]
        try: load_all(r); return False, "no error"
        except ValueError: return True, "empty task table rejected with a clear message"
    def t_bn():
        D = get_demo(); set_ctx(D, demo=True); F = view()["F"]; got = {(r.team, r.cat) for r in F.itertuples()}; need = [("Customer Support", "Excessive overtime"), ("Finance Operations", "Approval or handoff delay"), ("Order Fulfilment", "Rework and quality bottleneck")]
        return all(x in got for x in need), "planted patterns found: " + "; ".join("%s %s" % x for x in need if x in got) + (" | MISSING: " + "; ".join("%s %s" % x for x in need if x not in got) if not all(x in got for x in need) else "")
    def t_exp():
        D = get_demo(); set_ctx(D, demo=True); files, _ = export_all(None, None, "", ""); n = len(pd.read_csv("tempo_bottleneck_findings.csv")); V = view(); return "tempo_productivity_metrics.csv" in files and n == len(V["F"]), "%d files written; findings export has %d rows matching the analysis" % (len(files), n)
    def t_llm(): D = get_demo(); set_ctx(D, demo=True); a = ask("what are the limitations?", False); return "deterministic" in a and os.environ.get("ANTHROPIC_API_KEY") is None or "deterministic" in a, "deterministic tool-grounded answer without any API key"
    for g, n, f in [("validation", "missing column", t_miss), ("validation", "invalid, duplicate and impossible rows", t_inv), ("validation", "empty dataset", t_empty), ("validation", "dependencies", t_dep), ("metrics", "productivity, cycle time, rework", t_met), ("metrics", "overtime and capacity", t_ot),
                    ("metrics", "zero denominators", t_zero), ("metrics", "backlog", t_back), ("metrics", "missing attendance", t_att), ("scenario", "redistribution respects capacity", t_red), ("scenario", "redistribution with no headroom", t_red2), ("scenario", "recalculation and consistency", t_scn),
                    ("bottleneck", "planted patterns detected on demo data", t_bn), ("reporting", "CSV export consistency", t_exp), ("strategist", "works without an API key", t_llm)]: chk(g, n, f)
    G.clear(); G.update(saved); TESTS[:] = T
    if verbose:
        for g, n, ok, d in T: print(("PASS " if ok else "FAIL ") + g + ": " + n + " :: " + d)
        print("Result: %d of %d self-tests passed." % (sum(1 for t in T if t[2]), len(T)))
    return TESTS

# ------------------------------ project export ------------------------------
METH = """### Methodology
- **Output:** completed tasks weighted by (complexity ÷ 3)^exponent (exponent 0 = raw count). **Output per hour** = output ÷ actual hours worked; the numerator and denominator are shown. Hours are never treated as output.
- **Capacity:** contracted hours minus recorded absence; unrecorded attendance stays unknown. Utilisation = hours worked ÷ that capacity. Overtime % = overtime ÷ contracted hours.
- **Cycle time** = created to completed; **waiting** = created to started; **processing** = started to completed; **backlog** = created minus completed (age from creation).
- **Trends** need 12+ weeks, p &lt; 0.05 and a change above 10% of the mean, otherwise 'no sustained trend'.
- **Bottlenecks:** rule-based categories with thresholds in settings (utilisation, overtime run length, imbalance share, blocked-hour share, rework rate, absence-week backlog change, priority ordering, complex-task concentration). Each finding lists evidence, confidence and next step.
- **Priority score** = 100 × weighted sum of normalised components (delayed tasks, blocked hours, cycle-time excess, criticality, backlog age, recurrence, downstream scope). A prioritisation aid, not a probability.
- **Scenario:** throughput = hours × task-hours per worked hour ÷ hours per task; backlog by weekly flow balance; cycle time by Little's law minus assumed waiting reduction; redistribution moves load only from overloaded to teammates with headroom. Hypothetical.
- **Not included:** a predictive forecasting model (descriptive trends only), OR-Tools optimisation (a deterministic proportional redistribution is used), task-eligibility and skill data.
- **Measured vs inferred vs simulated:** tables show measured counts; findings are inferences from rules; the Scenario Lab is simulated.
"""
DICT = "# Data dictionary\nemployees: employee_id, department, role, employment_type, contracted_hours, location, tenure_band.\nworkload_observations (weekly): employee_id, date, planned_hours, actual_hours, overtime_hours, active_task_count, task_complexity_score, available_capacity_hours.\ntask_records: task_id, team_id, assigned_employee_id, project_id, task_category, priority (1 = highest), estimated_hours, actual_hours, created_date, start_date, due_date, completed_date, status, complexity_score, rework_count, blocked_hours.\ntask_dependencies: predecessor_task_id, successor_task_id, dependency_type, blocking_duration.\nattendance (weekly): employee_id, date, scheduled_hours, absence_hours, absence_category, attendance_record_status.\nengagement: team_id, survey_date, engagement_score, workload_sustainability_score, survey_response_status.\nperformance: team_id, observation_period (YYYY-MM), tasks_completed, quality_score, rework_rate, cycle_time, output_measure.\nAll sample files are synthetic. Column names can be remapped in the app (field=column).\n"
SCORE = "# Bottleneck scoring\nscore = 100 x sum(weight_k x component_k / max component_k) / sum(weights). Components: delayed tasks, blocked hours, cycle-time excess over the overall median, mean criticality, mean open-task age, recurrence (share of weeks the pattern recurs), downstream scope (dependent tasks + open tasks). Weights are editable. The score ranks attention; it is not a probability.\n"
RAI = "# Responsible AI\nTeam and process-level reporting by default; assignee detail only behind an authorisation checkbox. No ranking of employees by overtime; overtime is not a proxy for commitment. No diagnosis of burnout or any medical condition. Legitimate absence is never penalised. Engagement scores are team-level signals, not measures of effort. Productivity indicators must not be the sole basis for disciplinary decisions. Correlation, prediction and causation are kept separate. Human review is required before material workforce decisions. External LLM use is off by default and only aggregated results would be sent.\n"
LIMITS = "# Limitations\nSynthetic demo data contains planted patterns and is not a benchmark. Findings are rule-based hypotheses. Scenarios are hypothetical and do not model eligibility, skills or dependencies for redistribution. No predictive model is included. Weekly granularity hides daily effects. Quality and engagement data may be sparse.\n"
LICENSE = "MIT License\n\nCopyright (c) 2026 TEMPO AI contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n"
README = """# TEMPO AI — Workforce Productivity & Operational Intelligence
Work smarter. Find the friction.

## Business problem
Working hours and overtime are rising while productivity stagnates or falls. TEMPO AI separates high effort from high output, finds operational bottlenecks (capacity, overtime, imbalance, approvals, dependencies, rework, absence cover, prioritisation, complexity mismatch), proposes evidence-linked interventions and simulates their effect. It aims at sustainable productivity, not longer hours. Bundled data is **fictional synthetic data** with planted patterns.

## Features
CSV upload with column mapping and row-level validation; productivity, workload, absence and backlog metrics with explicit denominators; trend detection; bottleneck radar with a configurable priority score; intervention playbook; scenario lab with constrained workload redistribution; deterministic strategist (optional LLM); exports and executive summary.

## Architecture
@@@mermaid
flowchart LR
  A[CSV upload or synthetic data] --> B[Validation + mapping]
  B --> C[Validated tables]
  C --> D[Weekly team metrics]
  D --> E[Trend detection]
  D --> F[Bottleneck detection + priority score]
  F --> G[Intervention engine]
  D --> H[Scenario engine]
  E --> I[Strategist tools]
  F --> I
  G --> I
  H --> I
  I --> J[Gradio UI, exports, report]
@@@

## Run
@@@
pip install -r requirements.txt
python app.py
@@@
Google Colab: paste `app.py` into one cell and run it. The `src/` modules from the brief are consolidated into `app.py`.

## Data, methodology, limits
See `docs/data_dictionary.md`, `docs/methodology.md`, `docs/bottleneck_scoring.md`, `docs/responsible_ai.md`, `docs/limitations.md`. If auto-detection fails, map columns in the app, for example `team_id=department, priority=prio`.

## Tests
@@@
pip install pytest
pytest tests
@@@

## LLM and privacy
Optional and off by default; set `ANTHROPIC_API_KEY` (see `.env.example`). Only aggregated results would be sent. Never commit real employee data or keys. Add screenshots to `screenshots/`.
""".replace("@@@", "`" * 3)
TFILE = "from app import run_selftests\n\n\ndef test_%s():\n    res = [r for r in run_selftests(verbose=False) if r[0] in %s]\n    assert res and all(r[2] for r in res), res\n"
def _src():
    try: return open(__file__, encoding="utf-8").read()
    except Exception: pass
    try:
        for s in list(get_ipython().user_ns.get("In") or [])[::-1]:
            if "TEMPO AI — Workforce Productivity" in s and "def main" in s: return s
    except Exception: pass
    return None
def write_samples():
    raw = get_demo_raw(); os.makedirs("sample_data", exist_ok=True); names = dict(emp="employees", work="workload_observations", tasks="task_records", deps="task_dependencies", att="attendance", eng="engagement", perf="performance"); out = []
    for k, n in names.items(): p = "sample_data/%s.csv" % n; raw[k].to_csv(p, index=False); out.append(p)
    return out
def build_project(files):
    root = "tempo-ai-workforce-intelligence"
    for d in ["sample_data", "tests", "docs", "screenshots"]: os.makedirs(os.path.join(root, d), exist_ok=True)
    src = _src()
    if src: open(root + "/app.py", "w", encoding="utf-8").write(src)
    for f in files: open(os.path.join(root, f), "wb").write(open(f, "rb").read())
    W = {"requirements.txt": "gradio>=4.44,<6\nplotly\nscipy\nrequests\npandas\nnumpy\n", "README.md": README, "LICENSE": LICENSE, ".env.example": "# Optional. Leave empty to keep the external LLM disabled.\nANTHROPIC_API_KEY=\n", ".gitignore": ".env\n*.key\nsecrets*\n__pycache__/\n.ipynb_checkpoints/\n*.zip\ntempo_*.csv\ntempo_*.md\ntempo_*.html\n",
         "docs/methodology.md": METH, "docs/data_dictionary.md": DICT, "docs/bottleneck_scoring.md": SCORE, "docs/responsible_ai.md": RAI, "docs/limitations.md": LIMITS, "screenshots/README.md": "# Screenshots\nAdd your own screenshots of the running app here. None are included.\n",
         "tests/test_data_validation.py": TFILE % ("data_validation", "('validation',)"), "tests/test_productivity_metrics.py": TFILE % ("productivity_metrics", "('metrics',)"), "tests/test_workload_analysis.py": TFILE % ("workload_analysis", "('metrics', 'scenario')"), "tests/test_bottleneck_detection.py": TFILE % ("bottleneck_detection", "('bottleneck',)"),
         "tests/test_intervention_engine.py": TFILE % ("intervention_engine", "('strategist',)"), "tests/test_scenario_simulator.py": TFILE % ("scenario_simulator", "('scenario',)"), "tests/test_reporting.py": TFILE % ("reporting", "('reporting',)")}
    for fn, tx in W.items(): open(os.path.join(root, fn), "w", encoding="utf-8").write(tx)
    z = "tempo_ai_project.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(root):
            for f in fs: zf.write(os.path.join(dp, f))
    return z, bool(src)

# ------------------------------ UI ------------------------------
CSS = """
.gradio-container{background:#172522!important;color:#F3F5F0!important;font-family:Inter,system-ui,-apple-system,sans-serif!important;max-width:1360px!important}
.hdr{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:14px;padding:26px 30px;border-radius:14px;background:#222E2B;border:1px solid #ffffff1a;border-left:4px solid #8FE3B5;margin-bottom:12px}
.brand{display:flex;gap:16px;align-items:center}.logo{width:50px;height:50px;border-radius:10px;border:2px solid #8FE3B5;color:#8FE3B5;font-weight:800;font-size:22px;display:flex;align-items:center;justify-content:center}
.hdr h1{margin:0;font-size:30px;letter-spacing:3px;color:#F3F5F0}.hdr h1 span{color:#8FE3B5}.hdr .sub{color:#D3B5FF;font-size:13px;letter-spacing:2px;text-transform:uppercase}.hdr p{margin:6px 0 0;color:#A6B7AE;font-size:15px;font-style:italic}
.badges span{display:inline-block;margin:3px;padding:4px 11px;border-radius:6px;background:#ffffff0d;border:1px solid #ffffff1a;color:#A6B7AE;font-size:12px}
.kg{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:10px 0}.kc{background:#222E2B;border:1px solid #ffffff14;border-radius:10px;padding:14px 16px}
.kl{color:#A6B7AE;font-size:11px;text-transform:uppercase;letter-spacing:1.2px}.kv{font-size:24px;font-weight:700;margin:6px 0 4px}.kd{color:#A6B7AE;font-size:12px}
.note{background:#222E2B;padding:10px 14px;border-radius:8px;margin:8px 0;color:#F3F5F0;font-size:14px;line-height:1.5}.sec{font-size:15px;font-weight:700;color:#D3B5FF;margin:18px 0 6px;text-transform:uppercase;letter-spacing:1px}
.tw{overflow-x:auto;border-radius:8px;border:1px solid #ffffff14;margin:8px 0}table{border-collapse:collapse;width:100%;background:#222E2B;font-size:13px}th{background:#2c3b37;color:#8FE3B5;text-align:left;padding:9px 10px;font-weight:600}
td{padding:8px 10px;border-top:1px solid #ffffff10;color:#F3F5F0;vertical-align:top}tr:hover td{background:#8FE3B50d}button.primary{background:#8FE3B5!important;color:#172522!important;border:none!important;font-weight:700!important}
@media(max-width:640px){.hdr h1{font-size:22px}.kv{font-size:20px}.hdr{padding:18px}}
"""
HEADER = ("<div class='hdr'><div class='brand'><div class='logo'>TE</div><div><h1>TEMPO <span>AI</span></h1><div class='sub'>Workforce Productivity &amp; Operational Intelligence</div><p>Work smarter. Find the friction.</p></div></div>"
          "<div class='badges'><span>Associations, not causes</span><span>Scenarios are hypothetical</span><span>Human review required</span><span>Core analytics need no API key</span></div></div>")
SK = ["ot_h", "run", "util", "ot_pct", "rw", "blk", "absr", "conc", "cwx", "hrate", "w_delayed", "w_blocked", "w_cycle", "w_crit", "w_age", "w_recur", "w_down"]
def mkS(*v):
    S = dict(DEF); d = dict(zip(SK, v)); S["w"] = {k[2:]: d.pop(k) for k in [x for x in SK if x.startswith("w_")]}; S.update(d); S["run"] = int(S["run"]); return S
def run_all(*a):
    n = len(SK)
    try:
        S = mkS(*a[:n]); files = a[n:n + 7]; mapping = a[n + 7]; demo = files[0] is None
        D = get_demo() if (demo and not mapping) else load_all(get_demo_raw() if demo else dict(zip(["emp", "work", "tasks", "deps", "att", "eng", "perf"], [read_csv_any(f) if f is not None else None for f in files])), mapping)
        set_ctx(D, S, demo); V = view(); k = V["k"]
        return note(("Fictional demo data analysed. " if demo else "Your data analysed. ") + "%s employees, %s tasks, %d weeks; %d bottleneck findings." % (nf(len(D["emp"])), nf(len(D["T"])), V["tw"].index.get_level_values("wk").nunique(), len(V["F"])), "ok")
    except Exception as e: return note("Could not complete the analysis: " + esc(e), "err")
def refresh():
    if "D" not in G: return gr.update(), gr.update()
    D = G["D"]; return gr.update(choices=sorted(set(D["T"].dept.dropna())), value=[]), gr.update(choices=sorted(set(D["T"].cat.dropna())), value=[])
def build_ui(zip_path, sfiles):
    with gr.Blocks(css=CSS, title="TEMPO AI", theme=gr.themes.Base(primary_hue="emerald", neutral_hue="slate")) as demo:
        gr.HTML(HEADER)
        with gr.Accordion("Settings: thresholds and priority-score weights (press Recalculate after changing)", open=False):
            with gr.Row():
                s1 = gr.Slider(1, 15, 4, step=.5, label="Overtime threshold (h/week)"); s2 = gr.Slider(2, 12, 4, step=1, label="Sustained overtime = consecutive weeks"); s3 = gr.Slider(.8, 1.3, 1.05, step=.01, label="Capacity bottleneck: utilisation ≥"); s4 = gr.Slider(.02, .3, .10, step=.01, label="Excessive overtime: overtime % ≥")
            with gr.Row():
                s5 = gr.Slider(.05, .4, .15, step=.01, label="Rework bottleneck: rate ≥"); s6 = gr.Slider(.03, .4, .10, step=.01, label="Blocked-hour share ≥"); s7 = gr.Slider(.03, .3, .10, step=.01, label="High-absence week ≥"); s8 = gr.Slider(.2, .8, .40, step=.05, label="Concentration share ≥")
            with gr.Row():
                s9 = gr.Slider(0, 2, 1, step=.25, label="Complexity weighting exponent (0 = raw count)"); s10 = gr.Number(45, label="Loaded hourly cost for estimates")
            gr.Markdown("**Priority-score weights** (normalised automatically)")
            with gr.Row():
                w1 = gr.Slider(0, 1, .2, step=.05, label="Delayed tasks"); w2 = gr.Slider(0, 1, .2, step=.05, label="Blocked hours"); w3 = gr.Slider(0, 1, .2, step=.05, label="Cycle-time excess"); w4 = gr.Slider(0, 1, .15, step=.05, label="Criticality"); w5 = gr.Slider(0, 1, .1, step=.05, label="Backlog age"); w6 = gr.Slider(0, 1, .1, step=.05, label="Recurrence"); w7 = gr.Slider(0, 1, .05, step=.05, label="Downstream scope")
            run_btn = gr.Button("Recalculate", variant="primary")
        with gr.Accordion("Filters (apply to every page)", open=True):
            with gr.Row():
                f_dep = gr.Dropdown([], multiselect=True, label="Department / team"); f_cat = gr.Dropdown([], multiselect=True, label="Task category"); f_d1 = gr.Textbox(label="From date (YYYY-MM-DD)"); f_d2 = gr.Textbox(label="To date (YYYY-MM-DD)"); ap_btn = gr.Button("Apply filters", variant="primary")
        status = gr.HTML(note("Loading the fictional demo data and running self-tests (about 30-60 seconds)...", "info"))
        FIN = [f_dep, f_cat, f_d1, f_d2]
        with gr.Tabs():
            with gr.Tab("01 Command Centre"):
                cc_h = gr.HTML()
                with gr.Row():
                    cc1 = gr.Plot(); cc2 = gr.Plot()
                cc3 = gr.Plot()
            with gr.Tab("02 Productivity Intelligence"):
                pr_h = gr.HTML()
                with gr.Row():
                    pr1 = gr.Plot(); pr2 = gr.Plot()
                with gr.Row():
                    pr3 = gr.Plot(); pr4 = gr.Plot()
            with gr.Tab("03 Workload Health"):
                wl_h = gr.HTML(); wl1 = gr.Plot()
                with gr.Row():
                    wl2 = gr.Plot(); wl3 = gr.Plot()
            with gr.Tab("04 Bottleneck Radar"):
                bn_h = gr.HTML()
                with gr.Row():
                    bn1 = gr.Plot(); bn2 = gr.Plot()
                bn3 = gr.Plot()
            with gr.Tab("05 Team & Process Explorer"):
                with gr.Row():
                    ex_by = gr.Dropdown(["Team", "Task category", "Priority", "Complexity score"], value="Team", label="Group by"); ex_auth = gr.Checkbox(False, label="I am authorised to view assignee details for an operational purpose (never for ranking or discipline)"); ex_btn = gr.Button("Update", variant="primary")
                ex_h = gr.HTML(); ex_f = gr.Plot()
            with gr.Tab("06 Intervention Studio"):
                iv_h = gr.HTML(); iv_df = gr.Dataframe(interactive=True, wrap=True, label="Action tracker: edit the status column to record human review decisions"); iv_btn = gr.Button("Export edited tracker", variant="primary"); iv_file = gr.File(label="Tracker file", interactive=False)
            with gr.Tab("07 Scenario Lab"):
                gr.Markdown("What-if levers recalculate the scenario. **Hypothetical, not guaranteed.** Baseline = recent weeks of the active filter.")
                with gr.Row():
                    c_n = gr.Slider(4, 26, 12, step=1, label="Baseline window (weeks)"); c_w = gr.Slider(4, 26, 8, step=1, label="Projection horizon (weeks)"); c_ad = gr.Slider(0, 100, 70, step=5, label="Intervention adoption rate (%)"); c_im = gr.Number(0, label="Implementation cost ($)")
                with gr.Row():
                    c_rd = gr.Slider(0, 50, 0, step=5, label="Workload redistributed (% of overloaded employees' work)"); c_wr = gr.Slider(0, 60, 0, step=5, label="Reduction in waiting time (approval/handoff, %)"); c_rw = gr.Slider(0, 60, 0, step=5, label="Rework reduction (%)"); c_ad2 = gr.Number(0, label="Additional hours per week")
                with gr.Row():
                    c_ot = gr.Slider(0, 100, 0, step=5, label="Overtime reduction (% of current overtime)"); c_wip = gr.Number(0, label="WIP limit: max active tasks per person (0 = none)"); c_mt = gr.Slider(0, 30, 0, step=1, label="Assumed time saved by less multitasking (%)"); c_xc = gr.Slider(0, 100, 0, step=5, label="Absence hours covered via cross-training (%)"); c_pr = gr.Slider(0, 60, 0, step=5, label="Faster urgent-task start from reprioritisation (%)")
                sc_btn = gr.Button("Run scenario", variant="primary"); sc_h = gr.HTML()
                with gr.Row():
                    sc1 = gr.Plot(); sc2 = gr.Plot()
            with gr.Tab("08 Reports & Data"):
                gr.Markdown("Upload CSVs (employees, workload, tasks required; dependencies, attendance, engagement, performance optional). Leave empty for the fictional demo. Raw uploads stay unchanged; a validated copy is analysed.")
                with gr.Row():
                    u1 = gr.File(label="employees.csv", file_types=[".csv"]); u2 = gr.File(label="workload_observations.csv", file_types=[".csv"]); u3 = gr.File(label="task_records.csv", file_types=[".csv"]); u4 = gr.File(label="task_dependencies.csv", file_types=[".csv"])
                with gr.Row():
                    u5 = gr.File(label="attendance.csv", file_types=[".csv"]); u6 = gr.File(label="engagement.csv", file_types=[".csv"]); u7 = gr.File(label="performance.csv", file_types=[".csv"])
                mp = gr.Textbox(label="Column mapping (only if auto-detect fails)", placeholder="employee_id=emp_no, team_id=department, priority=prio, tasks_priority=prio", lines=2); ld_btn = gr.Button("Validate and load uploaded data", variant="primary")
                gr.File(value=sfiles, label="Sample CSV templates (synthetic)", file_count="multiple", interactive=False); dq_h = gr.HTML(); t_h = gr.HTML()
                gr.Markdown("### Exports"); xp_btn = gr.Button("Generate exports and executive summary", variant="primary"); xp_msg = gr.HTML(); xp_files = gr.File(label="Exports", file_count="multiple", interactive=False); gr.File(value=zip_path, label="Download GitHub-ready project (ZIP)", interactive=False)
            with gr.Tab("09 Methodology & Trust"):
                gr.Markdown(METH); gr.Markdown(RAI)
            with gr.Tab("TEMPO Strategist"):
                gr.Markdown("Answers come from analytical tools over the current dataset. Try: *Why is productivity falling while overtime is rising?* · *Which workflow is creating the most blocked hours?* · *Which teams have the largest gap between workload and capacity?* · *What would happen if we redistributed 10% of eligible workload?* · *Should we simplify a process, add capacity or change priorities?*")
                ag_q = gr.Textbox(label="Ask a question"); ag_llm = gr.Checkbox(False, label="Use external LLM (off by default; sends only aggregated results; needs ANTHROPIC_API_KEY in the environment; check your privacy policy)"); ag_btn = gr.Button("Ask", variant="primary"); ag_out = gr.Markdown()
        SETIN = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, w1, w2, w3, w4, w5, w6, w7]; RUN = SETIN + [u1, u2, u3, u4, u5, u6, u7, mp]; SCI = FIN + [c_n, c_w, c_rd, c_wr, c_rw, c_ad2, c_ot, c_wip, c_mt, c_xc, c_pr, c_im, c_ad]
        def pages(e):
            e = e.then(render_cc, FIN, [cc_h, cc1, cc2, cc3]).then(render_prod, FIN, [pr_h, pr1, pr2, pr3, pr4]).then(render_wl, FIN, [wl_h, wl1, wl2, wl3]).then(render_bn, FIN, [bn_h, bn1, bn2, bn3]).then(render_exp, FIN + [ex_by, ex_auth], [ex_h, ex_f])
            return e.then(render_int, FIN, [iv_h]).then(int_df, FIN, [iv_df]).then(render_scn, SCI, [sc_h, sc1, sc2]).then(render_dq, None, [dq_h, t_h])
        def full(ev): return pages(ev.then(refresh, None, [f_dep, f_cat]))
        full(run_btn.click(run_all, RUN, [status], show_progress="full")); full(ld_btn.click(run_all, RUN, [status], show_progress="full")); full(demo.load(run_all, RUN, [status])); pages(ap_btn.click(lambda: None, None, None))
        ex_btn.click(render_exp, FIN + [ex_by, ex_auth], [ex_h, ex_f]); sc_btn.click(render_scn, SCI, [sc_h, sc1, sc2], show_progress="full"); xp_btn.click(export_all, FIN, [xp_files, xp_msg], show_progress="full")
        iv_btn.click(lambda d: (pd.DataFrame(d).to_csv("tempo_action_tracker.csv", index=False), ["tempo_action_tracker.csv"])[1], iv_df, iv_file); ag_btn.click(ask, [ag_q, ag_llm], ag_out, show_progress="full"); ag_q.submit(ask, [ag_q, ag_llm], ag_out)
    return demo
def main():
    get_demo(); sf = write_samples(); zp, saved = build_project(sf)
    print("=" * 78); print("TEMPO AI starting. Demo data is FICTIONAL with planted patterns. Core analytics need no API key."); print("Running self-tests (about 30-60 seconds):")
    run_selftests(verbose=True); demo = build_ui(zp, sf)
    print("Project ZIP:", zp, "| standalone app.py included:", "yes" if saved else "NO (create app.py yourself by pasting this cell into it)")
    print("Not included / not tested: predictive forecasting model, OR-Tools optimisation, uploads of your own CSVs, optional external LLM. The public Gradio link is open to anyone: do not load real employee data unless access is restricted.")
    print("=" * 78); demo.queue().launch(debug=False, show_error=True)
if __name__ == "__main__" or "google.colab" in sys.modules:
    main()