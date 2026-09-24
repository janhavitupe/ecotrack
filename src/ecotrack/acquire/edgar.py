"""
EDGAR v8 gridded NOx (v8.1 AP) and fossil CO2 (v8.0 GHG), clipped to the Phase 1 cube box.

Both releases share the FT2022 activity data, so their NOx:CO2 ratios are internally consistent.
Files are global 0.1 degree annual emissions (tonnes per cell; NOx as NO2 mass). Each is
downloaded, clipped, saved compactly to data/interim/edgar/, and the global copy deleted.

Role in this project (proposal §5 design rule): a *prior* for the NOx -> CO2 conversion and a
plausibility comparison, never ground truth.

Usage:
    python -m ecotrack.acquire.edgar
"""

import io
import urllib.error
import urllib.request
import zipfile

import h5py
import numpy as np

from ecotrack.config import DATA_INTERIM, load_config

BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets"
RELEASES = {
    "NOx": ("v81_FT2022_AP_new/NOx", "v8.1_FT2022_AP_NOx"),
    "CO2": ("v80_FT2022_GHG/CO2", "v8.0_FT2022_GHG_CO2"),
}
YEARS_TOTALS = [2019, 2020, 2021, 2022]
SECTOR_YEAR = 2021  # pre-/post-COVID-normal year for the sector breakdown
SECTORS = ["ENE", "IND", "TRO", "RCO", "REF_TRF", "TNR_Other", "TNR_Aviation_LTO", "PRO_FFF",
           "NMM", "CHE", "IRO", "NFE", "NEU", "PRU_SOL", "SWD_INC", "AGS", "AWB", "FOO_PAP", "MNM"]
OUT = DATA_INTERIM / "edgar"


def fetch(species: str, year: int, sector: str):
    folder, prefix = RELEASES[species]
    url = f"{BASE}/{folder}/{sector}/emi_nc/{prefix}_{year}_{sector}_emi_nc.zip"
    try:
        with urllib.request.urlopen(url, timeout=300) as resp:
            blob = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None  # sector not reported for this species
        raise
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = next(n for n in z.namelist() if n.endswith(".nc"))
        with h5py.File(io.BytesIO(z.read(name)), "r") as f:
            lat, lon = f["lat"][:], f["lon"][:]
            b = load_config()["inversion"]["cube_box"]
            iy = np.flatnonzero((lat > b["lat_min"]) & (lat < b["lat_max"]))
            ix = np.flatnonzero((lon > b["lon_min"]) & (lon < b["lon_max"]))
            emis = f["emissions"][iy.min(): iy.max() + 1, ix.min(): ix.max() + 1]
            units = f["emissions"].attrs.get("units", b"")
    return lat[iy], lon[ix], emis.astype("float64"), units.decode() if isinstance(units, bytes) else str(units)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(sp, y, "TOTALS") for sp in RELEASES for y in YEARS_TOTALS]
    jobs += [(sp, SECTOR_YEAR, s) for sp in RELEASES for s in SECTORS]
    for species, year, sector in jobs:
        out = OUT / f"{species}_{year}_{sector}.npz"
        if out.exists():
            continue
        got = fetch(species, year, sector)
        if got is None:
            print(f"  {species} {year} {sector}: not available")
            continue
        lat, lon, emis, units = got
        np.savez_compressed(out, lat=lat, lon=lon, emissions_t=emis, units=units)
        print(f"  {species} {year} {sector:18s} box total {emis.sum():12,.0f} {units}")


if __name__ == "__main__":
    run()
