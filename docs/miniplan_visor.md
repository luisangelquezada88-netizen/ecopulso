# Miniplan — Visor y páginas ambientales (2026-11-24)

Objetivo: ejecutar rápido los cambios de mayor impacto en el visor y en las
páginas temáticas, sin rehacer la arquitectura de datos.

## Diagnóstico verificado

| Tema | Estado real | Implicación |
|------|-------------|-------------|
| Fechas | 45 particiones: 2026-10-02 → 2026-11-22; 150 filas y PM2.5/temp/caudal completos en todas | **No hay días con datos vacíos**. Faltan particiones de calendario: 26-oct y 28-oct→02-nov (7 días) |
| IDW | 46 superficies; 45/45 fechas con datos tienen PNG (~85 KB) y meta (0.25°, p=2, corte 800 km) | Se puede habilitar por fecha; hay una superficie huérfana 2026-10-26 |
| Países | 26 polígonos para 66 ISO3 con datos | Faltan 40 países; hay que regenerar el GeoJSON |
| Ciudades | 150 polígonos y 150 `punto_id` que coinciden 1:1 | Listo para datos por polígono |
| Cuencas | 17 polígonos; solo 10 coinciden con `punto_id` de datos. 7 polígonos huérfanos y 7 puntos `es_cuenca` sin polígono | **Confirmado: las cuencas no están conectadas**. Hay que regenerarlas |
| Puntos de cuenca | 17 `es_cuenca=True`; 16 con caudal > 0 | Hay dato de caudal para poblar cuencas una vez reparado el join |

## Decisiones confirmadas (2026-11-24)

1. **Red como página separada** `red.qmd` (navbar: Visor | Red | Ambiente | Datos | Acerca). El visor queda solo y a página completa; Red contiene Lectura de la red, Pulso diario y Cruces.
2. **Países**: 66 países con datos desde Natural Earth 10m + contorno mundial 110m como contexto neutro.
3. **Cuencas**: **sí se pueden mantener todas**. Verificado: los 17 puntos `es_cuenca=True` caen dentro de un polígono HydroBASINS nivel 6 (17/17). No hay que deshabilitar cuencas ni mover el caudal a polígonos de ciudad.
   - HydroBASINS no trae nombre de cuenca. Se usará un `nombre_cuenca` legible derivado del río/ciudad (p. ej. “Amazonas (Santarém)”, “Nilo (Asuán)”, “Danubio (Budapest)”) y se mostrará `HYBAS_ID`, `SUB_AREA` y nivel.
   - Nivel 6 = subcuenca local, un polígono por punto. El caudal es el del punto de salida (GloFAS ~10 km), no un caudal integrado de toda la cuenca. Si se quieren macrocuencas con varios puntos, se puede evaluar nivel 4/5 en una fase dedicada.
4. **Backfill**: viable. Probado con 2026-10-26: meteorología, calidad del aire e hidrología devolvieron 150 filas cada una. Se backfillean las 7 fechas faltantes (26-oct y 28-oct→02-nov), luego `transform.indicadores` y `superficie_idw` por fecha.
5. **Modo oscuro**: solo cambia el mapa base por defecto a **Oscuro** (Esri Dark Gray). La interfaz/panel sigue clara; no es un tema oscuro global.

## Fases

### Fase A — Reordenar sitio y quick wins (1.5–2 días)

- [ ] Crear `dashboard/red.qmd` y mover allí los bloques de `index.qmd`: `lectura-red`, `pulso-diario`, `cruzados-maestro`.
- [ ] `index.qmd` queda solo con el visor full-bleed (sin scroll interno ni análisis).
- [ ] Navbar: `Visor` (index), `Red` (red.qmd); conservar Ambiente, Datos, Acerca.
- [ ] Páginas temáticas: eliminar la sección “02 · Visor…” y subir los modelos ML inmediatamente después de “01 · Estado de hoy”; renumerar secciones.
- [ ] Quitar imports de Folium/GeoJSON y leyendas de las páginas temáticas para reducir peso.
- [ ] Modo oscuro: mapa base por defecto **Oscuro** (Esri Dark Gray); panel/UI clara.
- [ ] Backfill de las 7 fechas faltantes (26-oct y 28-oct→02-nov): extraer los 3 dominios, `transform.indicadores` y `superficie_idw` por fecha. Probado con 2026-10-26 (150 filas por dominio).
- [ ] Línea temporal: indexar solo `fechas` reales; validar que no haya frames vacíos.

**Aceptación:** navbar con Visor/Red; índice sin análisis debajo; temáticas sin mapas y con ML arriba; mapa base oscuro usable en escritorio y móvil; slider sin frames vacíos; 52 fechas continuas.

### Fase B — Polígonos con datos y toggle (2–3 días)

- [ ] Regenerar `paises_necesarios.geojson` para los 66 ISO3 con datos (`ADMIN`, `ISO_A3`, `NAME`), simplificado ~0.08°.
- [ ] Regenerar `cuencas_coincidentes.geojson` para los 17 puntos `es_cuenca=True` (17/17 caen en HydroBASINS nivel 6), conservando `punto_id`, `HYBAS_ID`, `nivel`, `SUB_AREA` y añadiendo `nombre_cuenca` legible.
- [ ] Enriquecer el payload del visor con `punto_id` e `iso3` por punto.
- [ ] Segmentado de modo: **Puntos | Ciudades | Países | Cuencas**.
- [ ] Estilo de polígonos por dominio y fecha:
  - Aire: color por categoría AQI del valor agregado.
  - Clima: gradiente de temperatura.
  - Agua: escala secuencial azul por caudal.
- [ ] Popups:
  - Ciudad: datos del punto (`punto_id`) para el dominio activo.
  - País: n, mediana, máximo, categoría dominante y ciudad líder.
  - Cuenca: caudal del punto de salida + `HYBAS_ID`, nivel y `SUB_AREA`.
- [ ] Al cambiar fecha/dominio/región, recalcular relleno y popups sin recargar.
- [ ] Ocultar marcadores en modos Ciudades/Países/Cuencas para evitar doble lectura.

**Aceptación:** clic en polígono de ciudad/país/cuenca muestra datos del dominio activo; 66 países y 17 cuencas conectados; colores consistentes con los puntos; sin polígonos huérfanos.

### Fase C — IDW por fecha y QA (1 día)

- [ ] Copiar `lake/serving/superficies` a `_site/superficies` en el pipeline (o `resources` de Quarto) y referenciar `superficies/fecha=.../pm25.png`.
- [ ] Cargar el PNG de la fecha seleccionada bajo demanda; mantener opacidad y toggle.
- [ ] Validar que no haya 404 y que el IDW no tape polígonos/puntos (pane propio).
- [ ] QA: `quarto render`, Playwright escritorio/móvil, `compileall`, `pytest`, `smoke_qmd`.
- [ ] Actualizar `docs/decisiones.md` con D-16 (polígonos con datos, IDW por fecha, dark mode).

**Aceptación:** IDW visible para cualquier fecha con superficie; sin errores de consola; render 7/7 y CI verde.

**Fuera de este sprint (dedicada):** máscara costa/orografía, incertidumbre del IDW, IDW por cuenca, pesos poblacionales, tema oscuro global.

## Estimación

| Fase | Días-persona | Dependencia |
|------|--------------|-------------|
| A. Reorden + dark + timeline | 1.5–2 | Ninguna |
| B. Países + cuencas + polígonos interactivos | 2–3 | GeoJSON + join |
| C. IDW por fecha + QA | 1 | Copia de superficies en build |
| **Total** | **4.5–6** | |

Ruta rápida si se quiere valor inmediato: **Fase A** primero (1.5–2 días), luego B y C.

## Riesgos

- HydroBASINS: 7 puntos `es_cuenca` no tienen polígono; el point-in-polygon puede requerir nivel 5/6 o asignación por proximidad.
- Tamaño: 66 países 10m simplificados + 150 ciudades + 17 cuencas; vigilar el HTML (<3 MB).
- Rendimiento: reestilizar polígonos en cada cambio de fecha/dominio; usar `setStyle` y agregación en JS, no re-render de GeoJSON.
- Backfill: Open-Meteo puede no tener los 7 días; no rellenar con ceros.
- Dark mode: contraste de categorías AQI y cuencas; validar leyenda.

## Decisión abierta

- **Nivel de cuenca**: nivel 6 (17/17 puntos, 17 polígonos únicos; subcuenca local, un polígono por punto; **recomendado para este sprint**) vs nivel 5 (15 únicos) vs nivel 4 (14 únicos; macrocuencas que agrupan varios puntos, p. ej. Amazonas). Nivel 4/5 queda para una fase dedicada si se quiere lectura de macrocuenca.
- **Agregación de país**: mediana de los puntos del país para el dominio activo, más n, máximo y ciudad líder. Sin ponderación poblacional en este sprint.

## Estado de ejecución (2026-11-24)

- [x] Fase A: `red.qmd`, índice solo visor, temáticas sin mapas, ML arriba, mapa base oscuro.
- [x] Backfill: 52 fechas continuas y 52 superficies IDW.
- [x] Fase B: 66 países + contexto 110m, 17 cuencas nivel 6, modos Puntos/Ciudades/Países/Cuencas y popups con datos.
- [x] Fase C: IDW por fecha con copia de superficies al sitio.
- [x] QA final: Quarto render 7/7, Playwright escritorio/móvil, smoke y pytest.
- [ ] Commit/push (pendiente de autorización).
