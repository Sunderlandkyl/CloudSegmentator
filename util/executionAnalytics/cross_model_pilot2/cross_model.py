"""Cross-MODEL radiomics comparison for pilot2: MOOSE vs TotalSegmentator on the same
30 series (radiomicsjl both). Joins on (SeriesInstanceUID, label_name) — unlike
radiomics_compare.py's (series, model, label_id) join — so agreement measures how
consistently the two segmentation models delineate the same organ on the same CT."""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\d\c\CloudSegmentator\util\executionAnalytics")
from radiomics_compare import load_run, rel_diff, feature_class

HERE = Path(__file__).parent
runs = {m: load_run(m, HERE / m / "extracted", HERE / "_tmp") for m in ("moose", "totalseg")}

# Re-key by (series, label_name); keep the sub-model for reference. Drop rows whose
# radiomics was skipped (no features) and duplicate label_names within a run+series
# (e.g. a name appearing in two MOOSE sub-models) — ambiguous joins are excluded.
by_name = {}
for run, rows in runs.items():
    d = defaultdict(list)
    for (series, model, label_id), rec in rows.items():
        if rec["features"]:
            d[(series, rec["label_name"].strip().lower())].append((model, rec["features"]))
    by_name[run] = d

m_names = {k[1] for k in by_name["moose"]}
t_names = {k[1] for k in by_name["totalseg"]}
shared = sorted(m_names & t_names)
print(f"label vocabulary: moose {len(m_names)}, totalseg {len(t_names)}, "
      f"exact-name overlap {len(shared)}")
print("shared:", ", ".join(shared))
print("\nmoose-only sample:", ", ".join(sorted(m_names - t_names)[:15]))
print("totalseg-only sample:", ", ".join(sorted(t_names - m_names)[:15]))

recs = []
ambiguous = 0
for series_name in sorted(set(by_name["moose"]) & set(by_name["totalseg"])):
    m_list, t_list = by_name["moose"][series_name], by_name["totalseg"][series_name]
    if len(m_list) != 1 or len(t_list) != 1:
        ambiguous += 1
        continue
    (m_model, m_f), (_, t_f) = m_list[0], t_list[0]
    series, name = series_name
    for metric in sorted(set(m_f) & set(t_f)):
        recs.append({"series": series, "organ": name, "moose_submodel": m_model,
                     "metric": metric, "class": feature_class(metric),
                     "moose": m_f[metric], "totalseg": t_f[metric],
                     "rel_diff": rel_diff(m_f[metric], t_f[metric])})
print(f"\njoined (series, organ) pairs -> {len(recs)} (metric, organ, series) comparisons; "
      f"{ambiguous} ambiguous joins dropped")

df = pd.DataFrame(recs)
df.to_csv(HERE / "cross_model_all.csv", index=False)

# Headline: volume agreement per organ (mask overlap proxy).
vol = df[df.metric == "shape_voxel_volume"].copy()
if len(vol):
    g = vol.groupby("organ")["rel_diff"]
    tab = pd.DataFrame({"n_series": g.size(), "median_relvoldiff": g.median(),
                        "max_relvoldiff": g.max()}).sort_values("median_relvoldiff")
    print("\n=== organ volume agreement (shape_voxel_volume, rel diff moose vs totalseg) ===")
    print(tab.to_string(float_format=lambda x: f"{x:.3f}"))
    tab.to_csv(HERE / "cross_model_volume_by_organ.csv")

# Per metric-class agreement.
g = df.groupby("class")["rel_diff"]
print("\n=== agreement by feature class ===")
print(pd.DataFrame({"n": g.size(), "median": g.median(), "p90": g.quantile(0.9),
                    "frac_within_1pct": g.apply(lambda s: (s <= 0.01).mean()),
                    "frac_within_5pct": g.apply(lambda s: (s <= 0.05).mean())})
      .to_string(float_format=lambda x: f"{x:.3f}"))

# Per-metric summary for the shared organs.
g = df.groupby("metric")["rel_diff"]
met = pd.DataFrame({"n": g.size(), "median": g.median(), "p90": g.quantile(0.9)}) \
    .sort_values("median")
met.to_csv(HERE / "cross_model_by_metric.csv")
print("\n=== best/worst agreeing metrics (median rel diff) ===")
print(pd.concat([met.head(6), met.tail(6)]).to_string(float_format=lambda x: f"{x:.3f}"))

# Worst (organ, series) outliers by volume.
if len(vol):
    worst = vol.sort_values("rel_diff", ascending=False).head(10)
    print("\n=== worst volume disagreements ===")
    for _, r in worst.iterrows():
        print(f"  {r.organ:<22} {r.series[-12:]}  moose={r.moose:9.0f}  "
              f"totalseg={r.totalseg:9.0f}  rel={r.rel_diff:.2f}")
