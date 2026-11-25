# Registro de decisiones (ADR ligero).
# Toda anomalía de datos va aquí, no silenciosa en código.

## D-01 — Unidades y rangos Open-Meteo (2026-10-07)
- Temperatura °C, precipitación mm, viento km/h (forecast daily ya convierte desde m/s).
- PM µg/m³, O₃ µg/m³, CO mg/m³→ el transform solo valida PM10/PM2.5/O₃/NO₂; CO se conserva crudo.
- Rangos de validación en `src/transform/indicadores.py::RANGOS`. Fuera de rango → NULL + log.

## D-02 — GloFAS malla gruesa (2026-10-07)
- `river_discharge` es caudal de celda ~10 km, no estación hidrométrica.
- En ciudades no-cuenca el valor es orientativo; el flag `es_cuenca` distingue puntos de río.
- Decisión: no filtrar ciudades; el dashboard advierte y el oro conserva todo.

## D-03 — GFW exige API key (2026-10-07)
- Data API GFW requiere `GFW_API_KEY` (registro gratuito).
- Sin key: `gfw_deforestacion.py` escribe partición canónica vacía para no bloquear H4.
- Fallback v0.2: OWID `forest-area` / Hansen. Dashboard muestra marcador hasta activar.

## D-04 — OWID CO₂ anual con retraso (2026-10-07)
- OWID publica con ~1 año de retraso; el DAG mensual pide `año previo`.
- Columnas canónicas: `co2` (Mt), `co2_per_capita` (t), `coal/oil/gas/cement_co2`.

## D-05 — PostGIS puerto 5433 en local (2026-10-07)
- Host usa 5432 interno, pero se publica en 5433 para no chocar con Postgres local.
- En compose: `POSTGIS_HOST=postgis`; en local/CI: `POSTGIS_HOST=localhost POSTGIS_PORT=5433`.

## D-06 — DuckDB opcional en Windows dev (2026-10-07)
- Python 3.14 Microsoft Store bloquea la DLL `_duckdb` (App Control) de forma intermitente.
- Decisión: `src/transform/indicadores.py` usa DuckDB si importa, si no fallback pandas
  con la misma semántica (rangos → NULL, mismos parquet). En Airflow (Linux) y Actions
  (ubuntu) DuckDB sí está activo; el contrato de datos no cambia.

## D-07 — MinIO opcional en compose + Airflow SequentialExecutor (2026-10-07)
- `minio/minio` desapareció de Docker Hub y `quay.io/minio/minio` exige auth (401).
  MinIO queda en perfil `minio` (`docker compose --profile minio up`); el lake local
  ya usa rutas S3-compatibles, así que no bloquea H0-H2.
- Airflow: `sqlalchemy>=2.0` en `_PIP_ADDITIONAL_REQUIREMENTS` rompía el arranque
  (Airflow 2.10 exige SQLAlchemy 1.4) → se quitó sqlalchemy/geoalchemy2 del contenedor
  (el load usa psycopg directo). Además `LocalExecutor+SQLite` está prohibido →
  `SequentialExecutor`, suficiente para DAGs secuenciales del MVP.

## D-08 — Flood API solo `river_discharge` + contrato `fecha` string (2026-10-07)
- La Flood API devuelve 400 con `river_discharge_{mean,median,max,min}` o con
  `forecast_days/past_days` combinados con `start/end_date`. Solo vale
  `daily=river_discharge` + rango de fechas; las columnas medio/max/min se
  rellenan con el mismo valor (un dato/dia) y `CHUNK` baja a 25.
- `fecha` en oro siempre string `YYYY-MM-DD` (`dt.strftime` en transform) y el
  load lee archivo concreto (no directorio Hive) para evitar el choque
  `timestamp vs string` de la columna de particion.

## D-09 — 429 en CI por IP compartida de GitHub (2026-10-07)
- Los runners de Actions comparten IPs de salida: Open-Meteo responde 429
  aunque estemos bajo 10k calls/dia. En local no ocurre.
- Mitigacion en `src/extract/_http.py`: respeta `Retry-After`, 6 intentos con
  backoff 5s->180s + jitter. Bloques de 20 puntos + pausa de 3s entre bloques.

## D-10 — Dashboard v2: híbrido tablero + pilares (2026-10-07)
- Se eliminan las páginas vacías (deforestación, CO₂) del render; git las conserva.
- Estructura: Tablero cruzado (KPIs + visor multicapa + scatter cruzados) y páginas
  temáticas (Aire/Clima/Agua) con visor propio. Híbrido > todo-junto (unidades
  incompatibles) y > solo-separado (sin análisis cruzado).
- Tiles: OSM + Esri (calles/satélite); CartoDB exige API key y queda vetado.
- KPIs como HTML precalculado (cero JS, apto para sitio estático).

## D-11 — Las "categorías OMS" eran breakpoints EPA (2026-10-07)
- Los cortes ≤12/35.4/55.4/150.4/250.4 son del AQI estadounidense, no de la OMS
  (la OMS 2021 solo da guía 24h ≤ 15 + objetivos 25/37.5/50/75).
- Corrección: columna `categoria_pm25_oms` → `categoria_pm25_aqi`
  (migración `sql/03_aqi_rename.sql`), etiquetas "AQI (EE. UU.)" y línea verde
  OMS-15 en gráficos. Detectado en revisión pre-fase-2.

## D-12 — Historial versionado para el slider temporal (2026-10-07)
- El runner de Actions es efímero: sin persistencia no hay serie temporal.
  El workflow commitea `lake/serving` al repo en cada run (~30 KB/día).
- `lake/serving/**/*.parquet` sale de `.gitignore` (negación); raw/curated
  siguen ignorados. No hay loop infinito: `lake/**` no está en el trigger.
- Semilla inicial: backfill manual de 4 días; desde ahí el cron acumula solo.

## D-13 — Superficie IDW de PM2.5 (2026-10-07)
- IDW p=2, malla 0.5° (bbox −56…33/−120…−30), corte 1300 km; raster en bandas
  AQI para coherencia punto↔raster; validación leave-one-out publicada (RMSE).
- v2 (2026-10-09): malla 0.25°, corte 800 km y fundido alfa por distancia
  (lejos de estaciones = transparente); el derrame oceánico se vuelve honesto.
- Límites: ignora barreras orográficas (Andes) y no enmascara costa; se muestran,
  no se ocultan. PNG ~90 KB/día dentro de `lake/serving` (entra al historial).

## D-14 — Cron caído por migración de runner (2026-10-26)
- Síntoma: runs programados 22–26 oct fallan en "Superficie IDW" a los ~3 s;
  persistencia, render y deploy quedan skipped → sitio congelado en 2026-10-20.
- Evidencia: ingesta (22 min, normal) y transform OK; fallo instantáneo solo en el
  paso que importa matplotlib. Coincide con la migración gradual de `ubuntu-latest`
  a Ubuntu 26.04 anunciada para 19-oct→19-nov (actions/runner-images#14748).
- Corrección: (1) `runs-on: ubuntu-24.04` fijo en pipeline y CI; (2) IDW degradable:
  <3 PM2.5 válidos → meta `estado=sin_datos`, sin PNG y exit 0; (3) step IDW con
  `continue-on-error` para que un extra visual nunca bloquee ingesta ni despliegue;
  (4) anotaciones `::warning::` públicas (visibles sin logs) con el diagnóstico.
- Deuda: probar Ubuntu 26 en rama aparte; el pin a 24.04 es temporal.
- Backfill manual de 2026-10-21..25 para reparar la serie del slider.

## D-15 — Visor único full-bleed y filtros reales (2026-11-23)
- El índice deja de ser un tablero con dos mapas: un solo visor a ancho completo
  (`100dvh - navbar`) y los análisis (KPIs, pulso diario, cruces) debajo en
  `.main-container`. Se elimina el mapa duplicado del slider temporal.
- El HTML anidado con 4+ espacios se interpretaba como bloque de código por
  Pandoc. Se retira el `nav` duplicado (ya existe el navbar de Quarto) y todo el
  HTML del visor se genera desde Python/Folium, no desde Markdown indentado.
- Filtros de fecha, dominio y región **client-side**: se embebe un payload
  compacto con todas las fechas del lake (43 al cierre) y JS reconstruye los
  `circleMarker`. No hay recarga ni render por fecha; el botón ▶ anima la serie.
- `FeatureGroup(show=False)` en Folium **no oculta** la capa (se sigue dibujando).
  Por eso se abandona `LayerControl` y se usa un panel propio con registro de
  capas, toggles y opacidad reales (países, cuencas, áreas urbanas, IDW).
- Polígonos: países con relleno suave, cuencas con opacidad dependiente del zoom
  (contorno a escala ciudad) y áreas urbanas visibles al acercar. Selector de
  ciudad ordenado alfabéticamente para descubrir los polígonos urbanos.
- CartoDB sigue vetado (API key). Fondo por defecto: Esri Light Gray + reference;
  alternativas Esri Satellite, OSM y Esri Dark Gray. El IDW vive en un pane
  propio debajo de polígonos y puntos.
- `embed-resources: false` (antes `true`): el índice baja de ~21.5 MB a ~1.6 MB.
  `paises_necesarios.geojson` se simplifica a 0.08° (1.6 MB → 0.47 MB).
- Plotly se fija a `<6`: con Plotly 6/7, Quarto 1.11 emite un import ESM a
  `cdn.plot.ly/plotly-*.min` (sin `.js`) que devuelve 403. Con 5.24 el import map
  no se ejecuta y el sitio queda sin errores de consola (salvo favicon 404).
- Las páginas temáticas conservan su visor propio y su TOC; solo se hace robusta
  la inserción de `ROOT` para que `quarto render` funcione sin `PYTHONPATH`.
  *(Actualizado por D-16: Red separada, 52 fechas y temáticas sin visor.)*

## D-16 — Red separada, backfill y polígonos con datos (2026-11-24)
- Se separa `red.qmd` (navbar Visor | Red | Ambiente | Datos | Acerca). El índice
  queda solo con el visor full-bleed; KPIs, pulso diario y cruces viven en Red.
- Las páginas temáticas pierden su visor geográfico; los modelos ML suben
  inmediatamente después de “01 · Estado de hoy”. El HTML baja de ~1.3 MB a
  ~0.09 MB por página.
- Backfill de las 7 fechas faltantes (26-oct y 28-oct→02-nov) con los tres
  extractores + transform + IDW. La serie queda continua: 52 fechas
  (2026-10-02 → 2026-11-22), 52 superficies. Sin frames vacíos en el slider.
- Países: 66 ISO3 con datos desde Natural Earth 10m (GUF se extrae de la parte
  del MultiPolygon de Francia), simplificados a 0.10°, más contexto mundial
  110m (136 KB). Total ~1.13 MB.
- Cuencas: los 17 puntos `es_cuenca=True` caen dentro de HydroBASINS nivel 6
  (17/17, 17 polígonos únicos). Se regeneran con `punto_id`, `HYBAS_ID`,
  `SUB_AREA`, `nivel` y `nombre_cuenca` legible. El caudal es el del punto de
  salida, no un caudal integrado de toda la cuenca.
- Visor: segmentado Puntos | Ciudades | Países | Cuencas. Los polígonos se
  rellenan con la paleta del dominio (AQI, temperatura, azul secuencial) y
  muestran popup al hacer clic. Países agregan mediana/máximo/n/ciudad líder;
  ciudades y cuencas muestran el punto y, en cuencas, la metadata HydroBASINS.
- Mapa base por defecto: Oscuro (Esri Dark Gray). La UI/panel sigue clara.
- IDW por fecha: los PNG de `lake/serving/superficies` se copian a
  `dashboard/_site/superficies` en el pipeline y el visor los carga bajo demanda
  con `L.imageOverlay`; el toggle ya no está limitado a la última fecha.
  *(Deshabilitado por D-18: mala adherencia a límites urbanos.)*
- `plotly>=5.22,<6` se mantiene por el import ESM roto de Quarto con Plotly 6/7.

## D-18 — Popups, zoom, footer y datos tempranos (2026-11-24)
- **IDW PM2.5 deshabilitado**: se retira el control del panel y el paso de
  superficie del pipeline. La capa histórica queda en `lake/serving/superficies`
  para una tarea dedicada. Un raster de temperatura requeriría generalizar
  `superficie_idw` y resolver el recorte; queda pendiente.
- **Clics en polígonos**: el renderer canvas de los marcadores tapaba los
  polígonos y bloqueaba los popups. Se elimina el canvas propio, se usa el
  renderer único del mapa y los popups se enlazan una sola vez con funciones
  que leen `VISTA` al abrir. Clics de país y ciudad verificados.
- **UX**: `scrollWheelZoom=True` (trackpad), footer de Quarto oculto en el
  visor, grid de `#quarto-content` ajustado a `100dvh - navbar` sin fila
  sobrante. El mapa ocupa toda la ventana y ya no hay scroll de página.
- **Default**: Países + Clima al cargar; el visor abre con la capa de países
  coloreada por temperatura.
- **Datos tempranos**: 46 parquet de `indicador_diario`/`indicador_pais`
  (2026-10-02..24) tenían la columna `fecha` y esquema antiguo; en CI/Pages no
  se leían y el visor arrancaba vacío hasta 2026-10-25. Se normalizaron a
  pyarrow 24 sin `fecha` (la partición inyecta la fecha). Verificado local:
  payload con todas las fechas y 150 observaciones por fecha.
- **Relleno de aire**: se descartó el IDW intraciudad (un punto por ciudad no
  permite un campo real). Se implementó un **hatch diagonal** como
  `CanvasPattern` sobre el canvas único, solo para Aire y solo en la capa
  activa. Mantiene el color de la categoría AQI y añade textura sin inventar
  datos espaciales. El patrón se cachea por color; clics y popups no cambian.
- **Pendiente**: raster de temperatura. Requiere generalizar `superficie_idw`
  y resolver el recorte a polígonos; no se incluyó en este sprint.


## D-17 — Licencia MIT para código y datos aparte (2026-11-24)
- Proyecto personal de portafolio, sin empleador/cliente ni coautores.
- Se elige **MIT** para el código por simplicidad, compatibilidad con el stack
  (Python/Quarto/Plotly/Folium/scikit-learn/PostGIS) y máxima reutilización.
- Los datos, GeoJSON derivados, superficies IDW y mosaicos **no** se relicencian
  como MIT: conservan las licencias de Open-Meteo (CC BY 4.0), Copernicus/GloFAS,
  Natural Earth (dominio público) y HydroSHEDS/HydroBASINS. Ver `NOTICE.md`.
- Se descarta Apache-2.0 para este sprint: no hay patentes propias que proteger
  y el proyecto no necesita el aparato de NOTICE/patentes; se puede migrar si
  aparecen contribuciones corporativas o preocupación por patentes.
