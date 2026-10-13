"""Reproducible exploratory MARTA analysis and illustrative event scenarios."""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIG = ROOT / "figures"
RESULTS = ROOT / "results"
FIG.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)

stations = pd.read_csv(DATA / "rail_stops.csv")
frequency = pd.read_csv(DATA / "station_frequencies.csv")
ridership = pd.read_csv(DATA / "ntd_marta_clean.csv", parse_dates=["date"])
for col in ("station_name", "lat", "lon"):
    if col not in stations.columns:
        raise ValueError(f"Missing station column: {col}")
assert stations["station_name"].nunique() == 38, "Unexpected station count; inspect data"

# Rail network visualization; lon/lat axes are geographic coordinates, not projected distances.
fig, ax = plt.subplots(figsize=(9, 8))
ax.scatter(stations["lon"], stations["lat"], s=42, color="#2563eb", alpha=.8)
for keyword in ("AIRPORT", "FIVE POINTS", "SEC DISTRICT"):
    subset = stations[stations["station_name"].str.upper().str.contains(keyword, na=False)]
    for _, row in subset.iterrows():
        ax.annotate(row["station_name"].title(), (row["lon"], row["lat"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
ax.set(xlabel="Longitude", ylabel="Latitude", title="MARTA rail station locations (provided station dataset)")
ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(FIG / "station_locations.png", dpi=180);plt.close(fig)

# Historic heavy rail UPT, monthly totals; not event-day station counts.
rail = ridership.loc[ridership["mode_name"].str.contains("Heavy Rail",case=False,na=False)].copy()
rail = rail.dropna(subset=["date", "upt"]).sort_values("date")
if rail.empty:
    raise ValueError("No heavy rail ridership rows found")
fig, ax = plt.subplots(figsize=(11, 4.8))
ax.plot(rail["date"], rail["upt"] / 1e6, lw=1.6, color="#0f766e")
ax.set(xlabel="Month", ylabel="Unlinked passenger trips (millions)", title="MARTA heavy rail monthly ridership (NTD data)")
ax.grid(alpha=.2);fig.tight_layout();fig.savefig(FIG / "historical_rail_ridership.png",dpi=180);plt.close(fig)

# Scenario analysis, explicitly illustrative rather than an operational capacity forecast.
# Attendance is a scenario assumption, not actual observed match attendance.
ATTENDANCE = 75000
shares = {"low (15%)": .15, "medium (30%)": .30, "high (45%)": .45}
# Illustrative 2-hour rail passenger throughput assumptions; NOT calculated from GTFS.
capacities = {"constrained": 14000, "baseline": 24000, "expanded": 36000}
rows = []
for share_label, share in shares.items():
    for capacity_label, capacity in capacities.items():
        demand = round(ATTENDANCE * share)
        rows.append({"rail_share_scenario":share_label,"capacity_scenario":capacity_label,
                     "assumed_attendance":ATTENDANCE,"assumed_rail_share":share,
                     "estimated_rail_riders":demand,"assumed_two_hour_capacity":capacity,
                     "surplus_riders":capacity-demand,"demand_exceeds_capacity":demand>capacity})
scenarios = pd.DataFrame(rows)
scenarios.to_csv(RESULTS / "illustrative_scenarios.csv",index=False)
pivot=scenarios.pivot(index="rail_share_scenario",columns="capacity_scenario",values="surplus_riders")
pivot=pivot.reindex(index=list(shares),columns=list(capacities))
fig,ax=plt.subplots(figsize=(9,4.5))
im=ax.imshow(pivot.values,cmap="RdYlGn",aspect="auto",vmin=-20000,vmax=25000)
ax.set_xticks(range(len(pivot.columns)),pivot.columns)
ax.set_yticks(range(len(pivot.index)),pivot.index)
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        ax.text(j,i,f"{pivot.iloc[i,j]:+,}",ha="center",va="center",fontsize=10,color="black")
ax.set(xlabel="Assumed 2-hour capacity",ylabel="Assumed share of attendees using rail",title="Illustrative rail capacity minus estimated demand")
fig.colorbar(im,ax=ax,label="Surplus (+) / shortfall (-) riders")
fig.tight_layout();fig.savefig(FIG / "scenario_heatmap.png",dpi=180);plt.close(fig)

# Compact reproducibility summary
summary = {
    "unique_station_count": int(stations["station_name"].nunique()),
    "frequency_source_rows": int(len(frequency)),
    "heavy_rail_monthly_records": int(len(rail)),
    "rail_series_start": str(rail["date"].min().date()),
    "rail_series_end": str(rail["date"].max().date()),
    "scenario_count": int(len(scenarios)),
    "scenarios_with_shortfall": int(scenarios["demand_exceeds_capacity"].sum()),
}
pd.Series(summary,name="value").to_csv(RESULTS / "analysis_summary.csv",header=True)
print("Analysis complete:",summary)
