"""
G4 — interactive waypoint check map (outputs/feasibility/g4_map.html).

Shows the configured waypoints (draggable), their OpenStreetMap geocodes from
g4_verify_waypoints, the corridor and cluster zones, and all OSM industrial land in the area.
Drag each waypoint onto the highway at the right place, then "Copy YAML" and paste the block
over `waypoints:` in configs/study.yaml.

Usage:
    python -m ecotrack.feasibility.g4_verify_waypoints   # once, for the OSM positions
    python -m ecotrack.feasibility.g4_map                 # then open the HTML file in a browser
"""

import json
import urllib.parse
import urllib.request

from shapely.geometry import mapping

from ecotrack.config import OUTPUTS
from ecotrack.config import load_config
from ecotrack.geometry import cluster_zones, corridor_polygon, waypoints

OVERPASS = "https://overpass-api.de/api/interpreter"
AREA = (18.45, 73.60, 18.80, 73.95)  # south, west, north, east


def industrial_land() -> dict:
    s, w, n, e = AREA
    query = f"""[out:json][timeout:90];
    (way["landuse"="industrial"]({s},{w},{n},{e}););
    out geom;"""
    req = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "EcoTrack-final-year-project/0.1 (academic research)"},
    )
    with urllib.request.urlopen(req, timeout=140) as resp:
        elements = json.load(resp)["elements"]
    features = []
    for el in elements:
        ring = [[p["lon"], p["lat"]] for p in el.get("geometry", [])]
        if len(ring) < 4 or ring[0] != ring[-1]:
            continue
        features.append({
            "type": "Feature",
            "properties": {"name": el.get("tags", {}).get("name", "")},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return {"type": "FeatureCollection", "features": features}


def run():
    osm_path = OUTPUTS / "feasibility" / "g4_waypoints.json"
    osm = {r["name"]: r for r in json.loads(osm_path.read_text())} if osm_path.exists() else {}
    data = {
        "waypoints": [
            {**w, "osm_lat": osm.get(w["name"], {}).get("osm_lat"), "osm_lon": osm.get(w["name"], {}).get("osm_lon")}
            for w in waypoints()
        ],
        "corridor": mapping(corridor_polygon()),
        "centreline": [[lat, lon] for lat, lon in load_config().get("centreline", [])],
        "clusters": {name: mapping(poly) for name, poly in cluster_zones().items()},
        "industrial": industrial_land(),
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    out = OUTPUTS / "feasibility" / "g4_map.html"
    out.write_text(html, encoding="utf-8")
    print(f"{len(data['industrial']['features'])} industrial areas loaded.\nOpen in your browser: {out}")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>EcoTrack waypoint check</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
  :root { --bg:#fff; --fg:#1d1d1f; --muted:#666; --line:#ddd; --accent:#1f6feb; --warn:#c2410c; --ok:#15803d; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.4 system-ui, sans-serif; color:var(--fg); background:var(--bg); display:flex; height:100vh; }
  #map { flex:1; }
  #panel { width:380px; overflow:auto; border-left:1px solid var(--line); padding:14px; }
  h1 { font-size:16px; margin:0 0 4px; } p { margin:4px 0 10px; color:var(--muted); }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td, th { padding:5px 4px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
  .num { font-variant-numeric: tabular-nums; text-align:right; }
  .flag { color:var(--warn); font-weight:600; } .ok { color:var(--ok); } .moved { color:var(--accent); font-weight:600; }
  button { font:inherit; padding:6px 10px; border:1px solid var(--line); background:#f6f6f6; border-radius:6px; cursor:pointer; }
  button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
  .small { font-size:12px; padding:2px 6px; }
  textarea { width:100%; height:190px; font:12px monospace; margin-top:8px; }
  .legend span { display:inline-block; width:12px; height:12px; margin-right:4px; vertical-align:-1px; border-radius:2px; }
  @media (max-width: 800px) { body { flex-direction:column; } #panel { width:auto; height:45vh; border-left:0; border-top:1px solid var(--line);} }
</style></head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>Waypoint check (G4)</h1>
  <p>Drag each <b>blue</b> marker onto the highway where the place really is. The <b>orange</b> dot is OpenStreetMap's centre of that place, a hint, not the answer. It opens in satellite view; switch to <b>Map</b> (top right) for road and place names.</p>
  <div class="legend">
    <span style="background:#1f6feb"></span>your waypoint &nbsp;
    <span style="background:#f97316"></span>OSM position &nbsp;
    <span style="background:#7c3aed55;border:1px solid #7c3aed"></span>industrial land &nbsp;
    <span style="background:#10b98133;border:1px solid #10b981"></span>corridor (as configured) &nbsp;
    <span style="background:#facc15"></span>highway centreline
  </div>
  <table id="tbl"><thead><tr><th>Waypoint</th><th class="num">to OSM</th><th></th></tr></thead><tbody></tbody></table>
  <p style="margin-top:10px">The green corridor is drawn from the saved config. After pasting the new YAML, rerun <code>python -m ecotrack.feasibility.g4_map</code> to redraw it, and check Bhosari MIDC and Talegaon MIDC fall inside.</p>
  <button class="primary" id="copy">Copy YAML for study.yaml</button>
  <textarea id="yaml" readonly></textarea>
</div>
<script>
const D = __DATA__;
const today = new Date().toISOString().slice(0,10);
const map = L.map('map');
// tile.openstreetmap.org refuses pages opened from a local file (no Referer), so use CARTO's
// OSM-based tiles for the street map.
const osm = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {maxZoom:20, subdomains:'abcd', attribution:'© OpenStreetMap contributors © CARTO'});
const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {maxZoom:19, attribution:'Esri World Imagery'});
sat.addTo(map);
const corridor = L.geoJSON(D.corridor, {style:{color:'#10b981', weight:2, fillOpacity:0.12}}).addTo(map);
const centre = L.polyline(D.centreline, {color:'#facc15', weight:3}).addTo(map);
const clusters = L.layerGroup(Object.entries(D.clusters).map(([n,g]) =>
  L.geoJSON(g, {style:{color:'#64748b', weight:1, dashArray:'4 4', fill:false}}).bindTooltip(n))).addTo(map);
const ind = L.geoJSON(D.industrial, {style:{color:'#7c3aed', weight:1, fillOpacity:0.3},
  onEachFeature:(f,l)=>{ if (f.properties.name) l.bindTooltip(f.properties.name); }}).addTo(map);
L.control.layers({'Satellite':sat, 'Map':osm}, {'Corridor':corridor, 'Highway centreline':centre, 'Clusters (5 km)':clusters, 'Industrial land (OSM)':ind}).addTo(map);
map.fitBounds(corridor.getBounds().pad(0.1));

function dist(a,b,c,d){ const R=6371000, r=Math.PI/180, x=(d-b)*r*Math.cos((a+c)/2*r), y=(c-a)*r; return Math.hypot(x,y)*R; }
const blueIcon = L.divIcon({className:'', html:'<div style="width:16px;height:16px;border-radius:50%;background:#1f6feb;border:2px solid #fff;box-shadow:0 0 3px #000"></div>', iconSize:[16,16], iconAnchor:[8,8]});
const state = D.waypoints.map(w => ({...w, orig:[w.lat,w.lon], moved:false}));

state.forEach((w,i) => {
  if (w.osm_lat != null) {
    L.circleMarker([w.osm_lat,w.osm_lon], {radius:6, color:'#f97316', fillOpacity:0.9}).addTo(map).bindTooltip('OSM: '+w.name);
    w.link = L.polyline([[w.lat,w.lon],[w.osm_lat,w.osm_lon]], {color:'#f97316', weight:1, dashArray:'3 3'}).addTo(map);
  }
  w.marker = L.marker([w.lat,w.lon], {draggable:true, icon:blueIcon}).addTo(map)
    .bindTooltip(w.name, {permanent:true, direction:'right', offset:[8,0]});
  w.marker.on('dragend', e => { const p=e.target.getLatLng(); setPos(i,p.lat,p.lng); });
});

function setPos(i, lat, lon){
  const w = state[i]; w.lat = +lat.toFixed(4); w.lon = +lon.toFixed(4); w.moved = true;
  w.marker.setLatLng([w.lat,w.lon]); if (w.link) w.link.setLatLngs([[w.lat,w.lon],[w.osm_lat,w.osm_lon]]);
  render();
}
function render(){
  const tb = document.querySelector('#tbl tbody'); tb.innerHTML = '';
  state.forEach((w,i) => {
    const d = w.osm_lat!=null ? Math.round(dist(w.lat,w.lon,w.osm_lat,w.osm_lon)) : null;
    const cls = w.moved ? 'moved' : (d!=null && d>500 ? 'flag' : 'ok');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="${cls}">${w.name}${w.moved?' ✓':''}<br><span style="color:#888;font-weight:400">${w.lat.toFixed(4)}, ${w.lon.toFixed(4)}</span></td>
      <td class="num">${d==null?'–':d+' m'}</td>
      <td><button class="small" data-z="${i}">zoom</button> ${w.osm_lat!=null?`<button class="small" data-o="${i}">use OSM</button>`:''}</td>`;
    tb.appendChild(tr);
  });
  tb.querySelectorAll('[data-z]').forEach(b => b.onclick = () => { const w=state[b.dataset.z]; map.setView([w.lat,w.lon], 15); });
  tb.querySelectorAll('[data-o]').forEach(b => b.onclick = () => { const w=state[b.dataset.o]; setPos(+b.dataset.o, w.osm_lat, w.osm_lon); });
  document.getElementById('yaml').value = 'waypoints:\n' + state.map(w => {
    const status = w.moved ? `verified map ${today}` : w.status;
    return `  - {name: ${w.name}, lat: ${w.lat.toFixed(4)}, lon: ${w.lon.toFixed(4)}, category: ${w.category}, status: ${status}}`;
  }).join('\n');
}
document.getElementById('copy').onclick = async () => {
  const t = document.getElementById('yaml'); t.select();
  try { await navigator.clipboard.writeText(t.value); } catch(e) { document.execCommand('copy'); }
  document.getElementById('copy').textContent = 'Copied ✓';
};
render();
</script>
</body></html>
"""

if __name__ == "__main__":
    run()
