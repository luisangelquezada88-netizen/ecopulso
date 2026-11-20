"""
Componentes geoespaciales compartidos para el dashboard EcoPulso.
Carga GeoJSON de polígonos (países, áreas urbanas, cuencas) y crea
FeatureGroups de Folium listos para agregar a cualquier visor.

Uso en un .qmd:
    from src.geo.map_components import capas_poligonos, leyenda_poligonos
    g_paises, g_urbanas, g_cuencas = capas_poligonos()
    g_paises.add_to(m); g_urbanas.add_to(m); g_cuencas.add_to(m)
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import folium
from folium.features import GeoJson

# El directorio de polígonos puede estar en dashboard/geo/polygons (desde la
# raíz del repo) o, al ejecutarse desde subcarpetas, en rutas relativas.
# Se busca en varias ubicaciones posibles para ser robusto al contexto de
# ejecución (Quarto render desde dashboard/, Actions desde raíz del repo, etc.).
_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "dashboard" / "geo" / "polygons",
    Path(__file__).resolve().parent.parent / "dashboard" / "geo" / "polygons",
    Path("dashboard/geo/polygons").resolve(),
    Path("../dashboard/geo/polygons").resolve(),
]
GEO_DIR = next((c for c in _CANDIDATES if c.exists()), _CANDIDATES[0])

# Estilos por tipo de polígono
ESTILO_PAISES = {
    "color": "#0b3d2e",
    "weight": 1,
    "fillOpacity": 0.05,
    "fillColor": "#0b3d2e",
}
ESTILO_URBANAS = {
    "color": "#52796f",
    "weight": 1.5,
    "fillOpacity": 0.15,
    "fillColor": "#52796f",
}
ESTILO_CUENCAS = {
    "color": "#01497c",
    "weight": 2,
    "fillOpacity": 0.12,
    "fillColor": "#01497c",
}


def _cargar_geojson(nombre_archivo: str) -> dict | None:
    """Carga un archivo GeoJSON del directorio de polígonos."""
    ruta = GEO_DIR / nombre_archivo
    if not ruta.exists():
        print(f"[geo] No encontrado: {ruta}")
        return None
    import json
    return json.loads(ruta.read_text(encoding="utf-8"))


def capas_poligonos() -> Tuple[folium.FeatureGroup | None, ...]:
    """
    Crea tres FeatureGroups de Folium con los polígonos disponibles:
      - países (contexto + clipping futuro del IDW)
      - áreas urbanas (polígonos de ciudad)
      - cuencas (polígonos hidrográficos, nivel 6 HydroBASINS)
    Devuelve (g_paises, g_urbanas, g_cuencas) — cada uno puede ser None si
    el archivo GeoJSON no existe.
    """
    g_paises = g_urbanas = g_cuencas = None

    data_paises = _cargar_geojson("paises_necesarios.geojson")
    if data_paises:
        g_paises = folium.FeatureGroup(name="Países (contexto)", show=True)
        GeoJson(
            data_paises,
            name="Países",
            style_function=lambda feat: ESTILO_PAISES,
            highlight_function=lambda feat: {"weight": 3, "color": "#0b3d2e"},
            tooltip=folium.features.GeoJsonTooltip(
                fields=["NAME"], aliases=["País:"], sticky=True
            ),
        ).add_to(g_paises)

    data_urbanas = _cargar_geojson("areas_urbanas_coincidentes.geojson")
    if data_urbanas:
        g_urbanas = folium.FeatureGroup(name="Áreas urbanas", show=True)
        GeoJson(
            data_urbanas,
            name="Área urbana",
            style_function=lambda feat: ESTILO_URBANAS,
            highlight_function=lambda feat: {"weight": 3, "color": "#52796f"},
            tooltip=folium.features.GeoJsonTooltip(
                fields=["ciudad", "pais"], aliases=["Ciudad:", "País:"], sticky=True
            ),
        ).add_to(g_urbanas)

    data_cuencas = _cargar_geojson("cuencas_coincidentes.geojson")
    if data_cuencas:
        g_cuencas = folium.FeatureGroup(name="Cuencas hidrográficas", show=True)
        GeoJson(
            data_cuencas,
            name="Cuenca",
            style_function=lambda feat: ESTILO_CUENCAS,
            highlight_function=lambda feat: {"weight": 3, "color": "#01497c"},
            tooltip=folium.features.GeoJsonTooltip(
                fields=["ciudad", "pais", "nivel"],
                aliases=["Ciudad:", "País:", "Nivel cuenca:"],
                sticky=True,
            ),
        ).add_to(g_cuencas)

    return g_paises, g_urbanas, g_cuencas


def html_leyenda_poligonos() -> str:
    """HTML de la leyenda para los polígonos (se inyecta en EcoLegend)."""
    items = ""
    if (GEO_DIR / "paises_necesarios.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#0b3d2e'>■</span> Países (contexto)</div>"
        )
    if (GEO_DIR / "areas_urbanas_coincidentes.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#52796f'>■</span> Áreas urbanas</div>"
        )
    if (GEO_DIR / "cuencas_coincidentes.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#01497c'>■</span> Cuencas hidrográficas</div>"
        )
    return items
