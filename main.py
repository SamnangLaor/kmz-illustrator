# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import folium
import geopandas as gpd
import uuid
import os
import pandas as pd

from utils import load_kmz_as_gdf

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def upload_form():
    return """
    <h2>Upload KMZ files</h2>
    <form action="/upload" enctype="multipart/form-data" method="post">
        <input type="file" name="files" multiple>
        <button type="submit">Upload</button>
    </form>
    """

@app.post("/upload", response_class=HTMLResponse)
async def upload_kmz(files: list[UploadFile] = File(...)):
    gdfs = []

    for file in files:
        path = f"{UPLOAD_DIR}/{uuid.uuid4()}.kmz"
        with open(path, "wb") as f:
            f.write(await file.read())

    layers_dict = load_kmz_as_gdf(path)
    for layer_name, gdf in layers_dict.items():
        # Optional: add columns for layer & filename
        gdf["layer"] = layer_name
        gdf["filename"] = file.filename

        gdfs.append(gdf)

    gdf_all = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")

    # Center map
    center = gdf_all.geometry.unary_union.centroid
    m = folium.Map(location=[center.y, center.x], zoom_start=14)

    # Street map (default)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street",
        control=True
    ).add_to(m)

    # Satellite (Esri – best free option)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        control=True
    ).add_to(m)

    # Color by area
    def style(feature):
        area = feature["properties"]["area_ha"]
        if area < 1:
            color = "green"
        elif area < 5:
            color = "orange"
        else:
            color = "red"

        return {
            "fillColor": color,
            "color": "black",
            "weight": 2,
            "fillOpacity": 0.5,
        }

    # Add layers
    for layer_name, gdf_layer in gdf_all.groupby("layer"):
        folium.GeoJson(
            gdf_layer,
            name=layer_name,
            style_function=style,
            tooltip=folium.GeoJsonTooltip(
                fields=["Name", "area_ha"],
                aliases=["Name", "Area (ha)"],
                localize=True
            ),
        ).add_to(m)

        # Boundary labels
        for _, row in gdf_layer.iterrows():
            centroid = row.geometry.centroid
            folium.Marker(
                [centroid.y, centroid.x],
                icon=folium.DivIcon(
                    html=f"""
                    <div style="font-size:10px; font-weight:bold;">
                        {row.get('Name', '')}<br/>
                        {row.area_ha:.2f} ha
                    </div>
                    """
                ),
            ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    return m._repr_html_()
