"""Earth Engine helpers shared by acquisition and feasibility scripts."""

import ee

from ecotrack.config import load_config
from ecotrack.geometry import bbox, cluster_zones, corridor_polygon


def init_ee(project: str | None = None):
    """Initialise Earth Engine; run `earthengine authenticate` once beforehand.
    Uses accounts.gee_project from configs/study.yaml unless --project overrides it."""
    project = project or load_config()["accounts"]["gee_project"]
    try:
        ee.Initialize(project=project) if project else ee.Initialize()
    except Exception as exc:
        raise SystemExit(
            f"Earth Engine init failed ({exc}).\n"
            "Run `earthengine authenticate` once, and pass --project <your-gcp-project-id> "
            "(new EE accounts require a registered Cloud project)."
        )


def to_ee(shapely_polygon) -> ee.Geometry:
    return ee.Geometry.Polygon([list(shapely_polygon.exterior.coords)])


def ee_corridor() -> ee.Geometry:
    return to_ee(corridor_polygon())


def ee_bbox(box: dict | None = None) -> ee.Geometry:
    b = box or bbox()
    return ee.Geometry.Rectangle([b["lon_min"], b["lat_min"], b["lon_max"], b["lat_max"]])


def ee_clusters() -> dict:
    return {name: to_ee(poly) for name, poly in cluster_zones().items()}


def tropomi_qc(collection: ee.ImageCollection, cfg: dict) -> tuple[ee.ImageCollection, bool]:
    """
    Mask each TROPOMI L3 image by cloud fraction and solar zenith (and qa_value if present).
    Returns (masked collection, whether a qa_value band was found).

    The GEE OFFL L3 NO2 product is already filtered on qa_value during its HARP conversion
    and may not expose a qa_value band at all; we detect that instead of assuming it.
    Record which case applies in the research log — it changes the QC description in Methods.
    """
    t = cfg["tropomi"]
    has_qa = "qa_value" in collection.first().bandNames().getInfo()

    def mask(img):
        m = img.select("cloud_fraction").lte(t["cloud_fraction_max"]).And(
            img.select("solar_zenith_angle").lte(t["solar_zenith_max"])
        )
        if has_qa:
            m = m.And(img.select("qa_value").gte(t["qa_min"]))
        return img.updateMask(m)

    return collection.map(mask), has_qa
