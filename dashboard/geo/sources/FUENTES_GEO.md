# Registro de fuentes geográficas para polígonos (ciudades y cuencas)

Este documento registra las fuentes geográficas abiertas integradas al visor
de EcoPulso: países, áreas urbanas y cuencas hidrográficas.

## 1. Polígonos de ciudades / áreas urbanas

### Fuente utilizada — Natural Earth (10m)

- **Populated Places:** https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-populated-places/
- **Urban Areas:** https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-urban-areas/
- **Admin 0 Countries:** https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/
- **Formato:** Shapefile → convertido a GeoJSON con geopandas
- **Licencia:** Public domain (sin restricciones)
- **CRS:** WGS84 (EPSG:4326)

### Opción alternativa descartada

- **OpenStreetMap admin boundaries (Overpass):** ODbL (requiere atribución) y requiere consulta individual por cada una de las 150 ciudades. Mayor esfuerzo manual para beneficio marginal.
- **GADM:** CC-BY-NC-SA (restricción no comercial) — rechazado.

## 2. Polígonos de cuencas hidrográficas

### Fuente utilizada — HydroBASINS (WWF HydroSHEDS)

- **URL:** https://www.hydrosheds.org/products/hydrobasins
- **Continentes descargados:** SA (Sudamérica), EU (Europa), AF (África), AS (Asia), NA (Norteamérica)
- **Niveles:** 1 (cuencas mayores) a 12 (sub-cuencas detalladas); se usó nivel 6 para las cuencas de EcoPulso
- **Licencia:** Gratis para uso comercial y no comercial
- **Geometría:** Polígonos, WGS84

## 3. Límites administrativos nacionales (para clipping del IDW)

### Fuente utilizada — Natural Earth Admin 0 (países)

- **Geometría:** Polígonos de países, WGS84
- **Licencia:** Public domain
- **Útil para:** Recorte (clipping) futuro de la capa raster IDW por límites nacionales

## 4. Plan de integración (prioridad media) — ESTADO: COMPLETADO

1. ✅ Descargado Natural Earth Populated Places (10m), Urban Areas (10m), Admin 0 Countries (10m).
2. ✅ Descargado HydroBASINS de los 5 continentes necesarios (SA, EU, AF, AS, NA), niveles 1-12.
3. ✅ Convertidos Shapefile → GeoJSON con geopandas.
4. ✅ Filtrado solo países/ciudades/cuencas que coinciden con los 150 puntos de `puntos_monitoreo.py`.
   - Ciudades: matching por distancia geográfica (haversine, ≤200 km) — 100% de cobertura.
   - Áreas urbanas: spatial join (punto dentro de polígono urbano).
   - Cuencas: spatial join (punto dentro de polígono HydroBASINS nivel 6).
5. ✅ Simplificadas geometrías (tolerancia 0.01° ≈ 1km, `preserve_topology=True`) para reducir tamaño en dashboard estático.
6. ✅ Integradas en los 4 visores Folium como capas `GeoJson` con estilo de relleno por tipo y borde delgado.
7. ✅ Agregado al `LayerControl`, a la leyenda dinámica (`.eco-legend`) y al control de opacidad.

### Archivos generados en `dashboard/geo/polygons/`

| Archivo | Features | Tamaño | Descripción |
|---------|----------|--------|-------------|
| `paises_necesarios.geojson` | 26 países | 1.6 MB | Límites nacionales de los países presentes en los 150 puntos (Natural Earth Admin 0 10m) |
| `ciudades_coincidentes.geojson` | 150 puntos | 51.5 KB | Coincidencia de ciudades en Natural Earth Populated Places (100% de los 150 puntos, matching por distancia haversine) |
| `areas_urbanas_coincidentes.geojson` | 127 polígonos | 28.6 KB | Áreas urbanas que contienen puntos de monitoreo (spatial join; 127 de 150) |
| `cuencas_coincidentes.geojson` | 17 polígonos | 4.6 KB | Cuencas HydroBASINS nivel 6 asociadas a los 17 puntos `tipo: cuenca` (100% de cobertura, 5 continentes) |
| `ciudades_mapeo.json` | 150 entradas | 28.1 KB | Mapeo detallado punto→ciudad NE con distancia en km y origen del match |
| `faltantes.json` | 3 secciones | 4.5 KB | Registro de puntos sin área urbana (23) para referencia |

### Cobertura sobre los 150 puntos de monitoreo

| Tipo | Coincidentes | Total | Cobertura | Nota |
|------|-------------|-------|-----------|------|
| Ciudades (Natural Earth Populated Places) | 150 | 150 | 100% | Matching por distancia haversine ≤200 km |
| Áreas urbanas (polígonos) | 127 | 150 | 85% | 23 puntos en zonas rurales/ciudades pequeñas sin polígono urbano en NE 10m |
| Cuencas (HydroBASINS nivel 6) | 17 | 17 | 100% | 5 continentes: SA (9), EU (2), AF (2), AS (3), NA (1) |

### Limitaciones conocidas

- **Áreas urbanas:** 23 de 150 puntos no caen dentro de un polígono urbano de Natural Earth 10m (zonas rurales, ciudades pequeñas o islas remotas como Rapa Nui, Galápagos). Es una limitación real de la fuente cartográfica, no un error.
- **Países:** Natural Earth Admin 0 tiene 26 de los países presentes en los puntos con nombres exactos; el resto se mapeó por similitud de nombre. Afecta solo al contexto visual, no a los datos de indicadores.
- Natural Earth es cartográfico, no censal: las fronteras pueden no coincidir exactamente con límites administrativos oficiales.

## 5. Limitaciones técnicas del visor

- Los polígonos se cargan como GeoJSON embebido en el HTML de Folium. Con 26 países (~1.6 MB) el tamaño del HTML del mapa es notable. Para producción se recomienda servir los GeoJSON como archivos estáticos y cargarlos con `L.geoJSON(ajax)` o simplificar más.
- No se implementó clipping automático del raster IDW por límites poligonales porque Folium no soporta máscara de raster nativa; requeriría procesar el PNG con GDAL antes de servirlo.
