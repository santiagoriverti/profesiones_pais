"""Descarga de graduados de educación superior desde la API SDMX 2.1 de Eurostat.

Estructura verificada contra la API el 2026-07-22
=================================================

Consulta usada (¡ojo!: el endpoint NO acepta ``references=all``, solo
``none|children|descendants``)::

    /dataflow/ESTAT/educ_uoe_grad02/1.0?references=descendants
    /dataflow/ESTAT/educ_uoe_grad10/1.0?references=descendants

Hallazgos
---------
1. Orden de dimensiones (define el filtro separado por puntos):

   - ``educ_uoe_grad02``: freq . unit . isced11 . iscedf13 . sex . geo
   - ``educ_uoe_grad10``: freq . sex . isced11 . iscedf13 . unit . geo
     (¡el orden es DISTINTO entre ambos datasets!)

2. Unidades:

   - ``educ_uoe_grad02`` viene en ``unit=NR`` (números absolutos de
     graduados). Es la FUENTE PRIMARIA de este proyecto: ya trae conteos
     por campo ISCED-F narrow, no hay que reconstruir nada.
   - ``educ_uoe_grad10`` viene solo en ``unit=PC`` y su semántica es la
     distribución POR SEXO dentro de cada campo (ej.: F011/AT/2020 →
     F=77.6, M=22.4; suman 100 dentro del campo). Rechaza ``sex=T``.
     NO es la composición por campo, así que no sirve para reconstruir
     absolutos por campo; queda como complemento opcional para análisis
     de brecha de género.

3. Códigos ``iscedf13`` (230 en la codelist):

   - broad:    ``F`` + 2 dígitos (F00..F10), 11 códigos
   - narrow:   ``F`` + 3 dígitos (F011, F021, ...), 57 códigos ← unidad
     de análisis de este proyecto
   - detailed: ``F`` + 4 dígitos, 148 códigos
   - especiales: TOTAL, UNK, NSP, OTH y combinaciones (F03_04, ...)

4. Las series totalmente vacías no aparecen en la respuesta; con
   ``returnData=ALL`` la API las incluye (útil para panel balanceado).

Cache: las descargas crudas se guardan en ``data/raw/`` con timestamp y
un hash del query; corridas posteriores reutilizan el archivo más
reciente para el mismo query salvo ``force=True``.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from time import strftime

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Orden de dimensiones verificado contra el DSD (ver docstring del módulo).
DATASET_DIMS = {
    "educ_uoe_grad02": ("freq", "unit", "isced11", "iscedf13", "sex", "geo"),
    "educ_uoe_grad10": ("freq", "sex", "isced11", "iscedf13", "unit", "geo"),
}

# Niveles ISCED 2011 de interés: grado, maestría, doctorado.
ISCED_LEVELS = ("ED6", "ED7", "ED8")
START_YEAR = 2013

BROAD_RE = re.compile(r"^F\d{2}$")
NARROW_RE = re.compile(r"^F\d{3}$")
DETAILED_RE = re.compile(r"^F\d{4}$")


def is_narrow(code: str) -> bool:
    """True si `code` es un campo ISCED-F 2013 de nivel narrow (F###)."""
    return bool(NARROW_RE.match(code))


def is_broad(code: str) -> bool:
    """True si `code` es un campo ISCED-F 2013 de nivel broad (F##)."""
    return bool(BROAD_RE.match(code))


def build_filter(dataset: str, **dims) -> str:
    """Arma el filtro posicional separado por puntos para `dataset`.

    Cada dimensión puede ser un string, una lista (se une con '+') o
    omitirse (queda vacía = sin filtrar). El orden lo fija DATASET_DIMS.

    >>> build_filter("educ_uoe_grad02", freq="A", unit="NR",
    ...              isced11=["ED6", "ED7"], sex="T")
    'A.NR.ED6+ED7..T.'
    """
    if dataset not in DATASET_DIMS:
        raise ValueError(f"Dataset desconocido: {dataset}")
    unknown = set(dims) - set(DATASET_DIMS[dataset])
    if unknown:
        raise ValueError(f"Dimensiones inválidas para {dataset}: {unknown}")
    parts = []
    for dim in DATASET_DIMS[dataset]:
        value = dims.get(dim, "")
        if isinstance(value, (list, tuple, set)):
            value = "+".join(sorted(value))
        parts.append(str(value))
    return ".".join(parts)


def _cache_paths(dataset: str, query_id: str) -> tuple[Path, list[Path]]:
    """Devuelve (path nuevo con timestamp, matches existentes en cache)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    new = RAW_DIR / f"{dataset}_{query_id}_{strftime('%Y%m%d')}.csv"
    existing = sorted(RAW_DIR.glob(f"{dataset}_{query_id}_*.csv"))
    return new, existing


def download(
    dataset: str,
    filter_expr: str = "",
    start_period: int = START_YEAR,
    end_period: int | None = None,
    balanced: bool = False,
    force: bool = False,
) -> Path:
    """Descarga `dataset` en SDMX-CSV y devuelve el path del archivo crudo.

    - Cachea en data/raw/ como ``{dataset}_{hash}_{YYYYMMDD}.csv``; si ya
      existe una descarga para el mismo query, reutiliza la más reciente
      salvo ``force=True``.
    - ``balanced=True`` agrega ``returnData=ALL`` para que la API incluya
      también las series sin ningún dato (panel balanceado).
    """
    params: dict[str, str] = {"format": "SDMX-CSV", "startPeriod": str(start_period)}
    if end_period is not None:
        params["endPeriod"] = str(end_period)
    if balanced:
        params["returnData"] = "ALL"

    key = hashlib.sha1(
        f"{filter_expr}|{sorted(params.items())}".encode()
    ).hexdigest()[:10]
    new_path, existing = _cache_paths(dataset, key)
    if existing and not force:
        logger.info("Cache hit: %s", existing[-1].name)
        return existing[-1]

    url = f"{BASE_URL}/data/{dataset}/{filter_expr}"
    logger.info("Descargando %s filtro=%r params=%s", dataset, filter_expr, params)
    resp = requests.get(url, params=params, timeout=300)
    resp.raise_for_status()
    if resp.content.startswith(b"<?xml"):
        # La API devuelve un Fault XML con status 200 en algunos errores.
        raise RuntimeError(f"La API devolvió un error SDMX: {resp.text[:500]}")
    new_path.write_bytes(resp.content)
    logger.info("Guardado %s (%.1f KB)", new_path.name, len(resp.content) / 1024)
    return new_path


def fetch_graduates(
    levels: tuple[str, ...] = ISCED_LEVELS,
    fields: list[str] | None = None,
    geo: list[str] | None = None,
    sex: str = "T",
    start_year: int = START_YEAR,
    balanced: bool = False,
    force: bool = False,
) -> pd.DataFrame:
    """Graduados absolutos (educ_uoe_grad02, unit=NR) en formato tidy.

    Por defecto trae todos los campos ISCED-F y todos los países
    disponibles desde 2013, para ED6/ED7/ED8 y sexo total.

    Devuelve columnas: geo, year, isced_level, iscedf13, sex, graduates, flag.
    """
    filt = build_filter(
        "educ_uoe_grad02",
        freq="A",
        unit="NR",
        isced11=list(levels),
        iscedf13=fields or "",
        sex=sex,
        geo=geo or "",
    )
    path = download(
        "educ_uoe_grad02", filt, start_period=start_year,
        balanced=balanced, force=force,
    )
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "isced11": "isced_level",
            "TIME_PERIOD": "year",
            "OBS_VALUE": "graduates",
            "OBS_FLAG": "flag",
        }
    )
    cols = ["geo", "year", "isced_level", "iscedf13", "sex", "graduates", "flag"]
    df = df[cols].copy()
    df["year"] = df["year"].astype(int)
    df["graduates"] = pd.to_numeric(df["graduates"], errors="coerce")
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    frame = fetch_graduates()
    n_narrow = frame["iscedf13"].map(is_narrow).sum()
    print(
        f"{len(frame):,} filas | {frame['geo'].nunique()} geografías | "
        f"{frame['year'].min()}-{frame['year'].max()} | "
        f"{n_narrow:,} filas a nivel narrow"
    )
