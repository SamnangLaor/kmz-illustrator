# utils.py
import zipfile, tempfile, os
import geopandas as gpd
import fiona
import pyogrio

fiona.drvsupport.supported_drivers['KML'] = 'rw'

# Optional: KMZ (not always directly supported)
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'


def extract_kml_from_kmz(kmz_path):
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(kmz_path, "r") as kmz:
        kmz.extractall(temp_dir)

    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.endswith(".kml"):
                return os.path.join(root, file)

    raise FileNotFoundError("No KML found")

def load_kmz_as_gdf(kmz_path):
    kml_path = extract_kml_from_kmz(kmz_path)

    all_layer = {}
    layers = pyogrio.list_layers(kml_path)

    for layer_name, _ in layers:
      gdf = gpd.read_file(kml_path, driver="KML", layer=layer_name)

      # Ensure CRS
      gdf = gdf.set_crs("EPSG:4326")

      # Area calculation (meters → hectares)
      gdf_m = gdf.to_crs(epsg=3857)
      gdf["area_ha"] = gdf_m.area / 10_000

      all_layer[layer_name] = gdf

    return all_layer
