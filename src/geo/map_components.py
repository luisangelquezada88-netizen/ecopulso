"""
Componentes geoespaciales compartidos para el dashboard EcoPulso.
Carga GeoJSON de polígonos (países, áreas urbanas, cuencas) y crea
FeatureGroups de Folium listos para agregar a cualquier visor.

Uso en un .qmd:
    from src.geo.map_components import capas_poligonos, html_leyenda_poligonos
    g_contexto, g_paises, g_urbanas, g_cuencas = capas_poligonos()
    g_contexto.add_to(m); g_paises.add_to(m); g_urbanas.add_to(m); g_cuencas.add_to(m)
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

# ---------------------------------------------------------------------------
# Estilos por tipo de polígono (relleno más visible para Iteración 3)
# ---------------------------------------------------------------------------
ESTILO_CONTEXTO = {
    "color": "#64748b",
    "weight": 0.4,
    "fillOpacity": 0.03,
    "fillColor": "#64748b",
}
ESTILO_PAISES = {
    "color": "#0b3d2e",
    "weight": 0.8,
    "fillOpacity": 0.10,
    "fillColor": "#0b3d2e",
}
ESTILO_URBANAS = {
    "color": "#7b6d8d",
    "weight": 1.0,
    "fillOpacity": 0.30,
    "fillColor": "#7b6d8d",
}
ESTILO_CUENCAS = {
    "color": "#1d6fa5",
    "weight": 1.4,
    "fillOpacity": 0.24,
    "fillColor": "#1d6fa5",
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
    Crea cuatro FeatureGroups de Folium con los polígonos disponibles:
      - contexto mundial (110m, solo fondo)
      - países (66 con datos + clipping futuro del IDW)
      - áreas urbanas (polígonos de ciudad, 100% de cobertura con buffers)
      - cuencas (polígonos hidrográficos, nivel 6 HydroBASINS)

    Orden de capas: contexto -> países -> cuencas -> áreas urbanas -> puntos.
    Devuelve (g_contexto, g_paises, g_urbanas, g_cuencas) — cada uno puede ser
    None si el archivo GeoJSON no existe.
    """
    g_contexto = g_paises = g_urbanas = g_cuencas = None

    # 0. Contexto mundial (NE 110m) — solo para orientación, sin datos.
    data_contexto = _cargar_geojson("mundo_contexto.geojson")
    if data_contexto:
        g_contexto = folium.FeatureGroup(name="Contexto mundial", show=True)
        GeoJson(
            data_contexto,
            name="Contexto",
            style_function=lambda feat: ESTILO_CONTEXTO,
            interactive=False,
        ).add_to(g_contexto)

    # 1. Países (capa de fondo, más abajo en z-index)
    data_paises = _cargar_geojson("paises_necesarios.geojson")
    if data_paises:
        g_paises = folium.FeatureGroup(name="Países (contexto)", show=True)
        GeoJson(
            data_paises,
            name="Países",
            style_function=lambda feat: ESTILO_PAISES,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["nombre"], aliases=["País:"], sticky=True
            ),
        ).add_to(g_paises)

    # 2. Cuencas hidrográficas (sobre países, bajo áreas urbanas)
    data_cuencas = _cargar_geojson("cuencas_coincidentes.geojson")
    if data_cuencas:
        g_cuencas = folium.FeatureGroup(name="Cuencas hidrográficas", show=True)
        GeoJson(
            data_cuencas,
            name="Cuenca",
            style_function=lambda feat: ESTILO_CUENCAS,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["nombre_cuenca", "ciudad", "nivel"],
                aliases=["Cuenca:", "Ciudad:", "Nivel:"],
                sticky=True,
            ),
        ).add_to(g_cuencas)

    # 3. Áreas urbanas (sobre cuencas, bajo marcadores de puntos)
    data_urbanas = _cargar_geojson("areas_urbanas_coincidentes.geojson")
    if data_urbanas:
        g_urbanas = folium.FeatureGroup(name="Áreas urbanas", show=True)
        GeoJson(
            data_urbanas,
            name="Área urbana",
            style_function=lambda feat: ESTILO_URBANAS,
            tooltip=folium.features.GeoJsonTooltip(
                fields=["ciudad", "pais", "tipo"],
                aliases=["Ciudad:", "País:", "Tipo:"],
                sticky=True,
            ),
        ).add_to(g_urbanas)

    return g_contexto, g_paises, g_urbanas, g_cuencas


def html_leyenda_poligonos() -> str:
    """HTML de la leyenda para los polígonos (se inyecta en EcoLegend)."""
    items = ""
    if (GEO_DIR / "paises_necesarios.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#0b3d2e'>■</span> Países (66 con datos)</div>"
        )
    if (GEO_DIR / "areas_urbanas_coincidentes.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#7b6d8d'>■</span> Áreas urbanas</div>"
        )
    if (GEO_DIR / "cuencas_coincidentes.geojson").exists():
        items += (
            "<div><span class='dot' style='color:#1d6fa5'>■</span> Cuencas hidrográficas</div>"
        )
    return items
