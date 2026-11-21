"""Lectura consistente del data lake (bronze → silver → gold) para el dashboard.

Provee funciones estables para leer:
  - lake/raw/{meteorologia,calidad_aire,hidrologia}/fecha=FECHA/*.parquet   (bronze)
  - lake/curated/{meteorologia,calidad_aire,hidrologia}/fecha=FECHA/*.parquet (silver, validado)
  - lake/serving/indicador_diario/fecha=FECHA/*.parquet                     (oro, join 3 pilares)
  - lake/serving/indicador_pais/fecha=FECHA/*.parquet                       (oro agregado país)
  - lake/serving/superficies/fecha=FECHA/{pm25.png, meta.json}              (oro, superficie IDW)

Todas las lecturas:
  * resuelven la ruta relativa al lake desde cualquier directorio de trabajo
  * convierten 'fecha' a string YYYY-MM-DD (evita choque timestamp vs partition)
  * devuelven None si no hay datos (sin lanzar excepción)
  * validan esquema mínimo (punto_id, ciudad, pais, iso3, region, lat, lon, fecha)

Diseñado para alimentar el dashboard (Quarto/Folium) y, en un paso posterior,
PostGIS directamente desde el lake sin dependencias de red externa.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Ubicación del lake (robusta al directorio de trabajo)
# ---------------------------------------------------------------------------
_CANDIDATES_LAKE = [
    Path("lake").resolve(),          # desde raiz del repo
    Path("../lake").resolve(),       # desde dashboard/
    Path(__file__).resolve().parent.parent.parent / "lake",  # desde src/data/
]

LAKE_DIR = next((c for c in _CANDIDATES_LAKE if c.exists()), _CANDIDATES_LAKE[0])

# Columnas mínimas que debe tener todo DataFrame de monitoreo para ser válido.
# 'fecha' se inyecta desde el nombre del partición (fecha=YYYY-MM-DD) cuando
# el parquet de serving no la trae como columna (transform la elimina y la deja
# solo en el directorio Hive).
_COLUMNAS_BASE = ["punto_id", "ciudad", "pais", "iso3", "region", "lat", "lon"]


def _extraer_fecha_particion(ruta: Path) -> Optional[str]:
    """Extrae YYYY-MM-DD de un directorio llamado fecha=YYYY-MM-DD, si aplica."""
    padre = ruta.parent if ruta.is_file() else ruta
    nombre = padre.name
    if nombre.startswith("fecha="):
        return nombre.replace("fecha=", "")
    return None


def _normalizar_fecha(df: pd.DataFrame, fecha_particion: Optional[str] = None) -> pd.DataFrame:
    """Convierte la columna fecha a string YYYY-MM-DD o la inyecta desde partición."""
    df = df.copy()
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d")
    elif fecha_particion:
        df["fecha"] = fecha_particion
    return df


def _validar_base(df: pd.DataFrame, etiqueta: str, requerir_punto: bool = True) -> bool:
    """Devuelve True si el DataFrame tiene las columnas base mínimas (sin fecha).

    Si `requerir_punto=False` (p. ej. indicador_pais, agregado por país) se
    omite la exigencia de punto_id/ciudad/lat/lon.
    """
    columnas = list(_COLUMNAS_BASE)
    if not requerir_punto:
        columnas = [c for c in columnas if c not in ("punto_id", "ciudad", "lat", "lon")]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        print(f"[lake_reader] {etiqueta}: faltan columnas base {faltantes}", flush=True)
        return False
    return True


def _leer_particion(
    ruta: Path,
    etiqueta: str,
    requerir_punto: bool = True,
) -> Optional[pd.DataFrame]:
    """Lee un parquet particionado (fecha=FECHA/archivo.parquet) o archivo directo.

    Inyecta la columna 'fecha' desde el nombre del directorio Hive cuando el
    parquet no la trae (caso serving/indicador_diario y serving/indicador_pais
    tras el transform).
    """
    try:
        if not ruta.exists():
            print(f"[lake_reader] {etiqueta}: no existe {ruta}", flush=True)
            return None
        fecha_particion = _extraer_fecha_particion(ruta)
        if ruta.is_dir():
            fich = sorted(ruta.glob("*.parquet"))
            if not fich:
                print(f"[lake_reader] {etiqueta}: sin parquets en {ruta}", flush=True)
                return None
            df = pd.concat([pd.read_parquet(f) for f in fich], ignore_index=True)
        else:
            df = pd.read_parquet(ruta)
        if df.empty:
            print(f"[lake_reader] {etiqueta}: DataFrame vacío en {ruta}", flush=True)
            return None
        df = _normalizar_fecha(df, fecha_particion)
        if not _validar_base(df, etiqueta, requerir_punto=requerir_punto):
            return None
        print(f"[lake_reader] {etiqueta}: {len(df)} filas desde {ruta}", flush=True)
        return df
    except Exception as e:  # noqa: BLE001
        print(f"[lake_reader] {etiqueta}: error leyendo {ruta}: {e}", flush=True)
        return None


# ===========================================================================
# Lectura por dominio (raw / curated / serving)
# ===========================================================================

def leer_raw(fecha: str, dominio: str, lake: str | Path = LAKE_DIR) -> Optional[pd.DataFrame]:
    """Lee datos brutos (bronze) de un dominio: meteorologia | calidad_aire | hidrologia."""
    ruta = Path(lake) / "raw" / dominio / f"fecha={fecha}" / f"{dominio}.parquet"
    return _leer_particion(ruta, f"raw/{dominio}")


def leer_curated(fecha: str, dominio: str, lake: str | Path = LAKE_DIR) -> Optional[pd.DataFrame]:
    """Lee datos validados (silver) de un dominio: meteorologia | calidad_aire | hidrologia."""
    ruta = Path(lake) / "curated" / dominio / f"fecha={fecha}" / f"{dominio}.parquet"
    return _leer_particion(ruta, f"curated/{dominio}")


def leer_indicador_diario(fecha: str, lake: str | Path = LAKE_DIR) -> Optional[pd.DataFrame]:
    """Lee el oro agregado por punto (serving/indicador_diario)."""
    ruta = Path(lake) / "serving" / "indicador_diario" / f"fecha={fecha}" / "indicador_diario.parquet"
    return _leer_particion(ruta, "serving/indicador_diario")


def leer_indicador_pais(fecha: str, lake: str | Path = LAKE_DIR) -> Optional[pd.DataFrame]:
    """Lee el oro agregado por país (serving/indicador_pais)."""
    ruta = Path(lake) / "serving" / "indicador_pais" / f"fecha={fecha}" / "indicador_pais.parquet"
    return _leer_particion(ruta, "serving/indicador_pais", requerir_punto=False)


# ===========================================================================
# Lectura multi-fecha (para series temporales y ML)
# ===========================================================================

def listar_fechas_disponibles(
    capa: str = "serving",
    conjunto: str = "indicador_diario",
    lake: str | Path = LAKE_DIR,
) -> list[str]:
    """Devuelve las fechas disponibles ordenadas para una capa/conjunto del lake."""
    ruta = Path(lake) / capa / conjunto
    if not ruta.exists():
        return []
    fechas = sorted([d.name.replace("fecha=", "") for d in ruta.iterdir() if d.is_dir() and d.name.startswith("fecha=")])
    return fechas


def leer_rango_fechas(
    fecha_inicio: str,
    fecha_fin: str,
    capa: str = "serving",
    conjunto: str = "indicador_diario",
    lake: str | Path = LAKE_DIR,
) -> pd.DataFrame:
    """Lee todas las particiones entre fecha_inicio y fecha_fin (inclusive) y las concatena."""
    fechas = listar_fechas_disponibles(capa, conjunto, lake)
    seleccion = [f for f in fechas if fecha_inicio <= f <= fecha_fin]
    frames: list[pd.DataFrame] = []
    for f in seleccion:
        if conjunto == "indicador_diario":
            df = leer_indicador_diario(f, lake)
        elif conjunto == "indicador_pais":
            df = leer_indicador_pais(f, lake)
        else:
            df = None
        if df is not None:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ===========================================================================
# Superficies IDW (imagen + metadatos)
# ===========================================================================

def leer_meta_idw(fecha: str, lake: str | Path = LAKE_DIR) -> Optional[dict]:
    """Lee meta.json de la superficie IDW para una fecha."""
    import json

    ruta = Path(lake) / "serving" / "superficies" / f"fecha={fecha}" / "meta.json"
    if not ruta.exists():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"[lake_reader] error leyendo meta IDW {ruta}: {e}", flush=True)
        return None


def existe_superficie_idw(fecha: str, lake: str | Path = LAKE_DIR) -> bool:
    """Indica si existe la imagen IDW para una fecha."""
    ruta = Path(lake) / "serving" / "superficies" / f"fecha={fecha}" / "pm25.png"
    return ruta.exists()


# ===========================================================================
# Resumen del lake (útil para diagnóstico y páginas temáticas)
# ===========================================================================

def resumen_lake(lake: str | Path = LAKE_DIR) -> dict:
    """Devuelve un resumen de lo disponible en el lake (fechas, puntos, dominios)."""
    fechas_diario = listar_fechas_disponibles("serving", "indicador_diario", lake)
    fechas_pais = listar_fechas_disponibles("serving", "indicador_pais", lake)
    resumen = {
        "lake_dir": str(LAKE_DIR),
        "fechas_indicador_diario": fechas_diario,
        "fechas_indicador_pais": fechas_pais,
        "fecha_max_diario": fechas_diario[-1] if fechas_diario else None,
        "fecha_max_pais": fechas_pais[-1] if fechas_pais else None,
        "n_fechas_diario": len(fechas_diario),
        "n_fechas_pais": len(fechas_pais),
        "dominios_raw": [],
    }
    raw_dir = Path(lake) / "raw"
    if raw_dir.exists():
        resumen["dominios_raw"] = sorted([d.name for d in raw_dir.iterdir() if d.is_dir()])
    return resumen
