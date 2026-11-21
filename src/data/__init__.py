"""Capa de acceso al data lake (bronze → silver → gold)."""

from src.data.lake_reader import (
    LAKE_DIR,
    leer_curated,
    leer_indicador_diario,
    leer_indicador_pais,
    leer_meta_idw,
    leer_rango_fechas,
    leer_raw,
    listar_fechas_disponibles,
    resumen_lake,
)

__all__ = [
    "LAKE_DIR",
    "leer_raw",
    "leer_curated",
    "leer_indicador_diario",
    "leer_indicador_pais",
    "leer_meta_idw",
    "leer_rango_fechas",
    "listar_fechas_disponibles",
    "resumen_lake",
]
