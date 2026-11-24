# Avisos de terceros y datos

El **código** de EcoPulso se distribuye bajo la licencia MIT (ver `LICENSE`).
Los **datos, capas geográficas y mosaicos de mapas** no quedan cubiertos por
esa licencia y conservan las condiciones de sus fuentes.

## Datos y cartografía

- **Open-Meteo** — datos meteorológicos, de calidad del aire e hidrología.
  Datos bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  La API gratuita está limitada a uso no comercial; el uso comercial requiere
  un plan pago. Atribución: “Datos de Open-Meteo.com (CC BY 4.0)”.
  <https://open-meteo.com/en/license>
- **Copernicus Emergency Management Service — GloFAS** — caudal de río.
  Datos Copernicus; se requiere atribución a Copernicus/GloFAS y aceptar la
  política de datos de Copernicus. <https://www.copernicus.eu/>
- **Natural Earth** — países y contexto mundial. Dominio público; no requiere
  permiso. Atribución sugerida: “Made with Natural Earth”.
  <https://www.naturalearthdata.com/about/terms-of-use/>
- **HydroSHEDS / HydroBASINS** — cuencas hidrográficas. Disponibles para uso
  científico, educativo y comercial bajo la licencia HydroSHEDS incluida en su
  documentación técnica; conservar atribución y condiciones de redistribución.
  <https://www.hydrosheds.org/products/hydrobasins>
  Referencia: Lehner, B., Grill G. (2013). *Global river hydrography and
  network routing*. Hydrological Processes, 27(15), 2171–2186.
- **Mosaicos de mapas** — Esri (World Imagery, Light/Dark Gray Canvas,
  Reference) y OpenStreetMap. Cada proveedor conserva su atribución y términos.

## Software de terceros

Las dependencias de Python y JavaScript se usan bajo sus propias licencias
(por ejemplo MIT, BSD, Apache-2.0 o LGPL). Consulte `requirements.txt`, los
metadatos de cada paquete y los archivos de licencia de las librerías
distribuidas con el sitio (Plotly, Folium, Leaflet, Bootstrap, Quarto).

## Datos derivados del repositorio

`lake/serving`, las superficies IDW y los GeoJSON derivados se incluyen para
que el sitio sea reproducible, pero **no se relicencian como MIT**: siguen
sujetos a las licencias de sus fuentes descritas arriba.
