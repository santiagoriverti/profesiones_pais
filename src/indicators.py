"""Indicadores de desarrollo por país-año: población, PIB per cápita e IDH.

Fuentes (verificadas 2026-07-22):
- Banco Mundial, API v2 (https://api.worldbank.org/v2/):
    SP.POP.TOTL       población total
    NY.GDP.PCAP.CD    PIB per cápita, USD corrientes
    NY.GDP.PCAP.PP.CD PIB per cápita, PPA ($ internacionales corrientes)
- PNUD, Human Development Report 2025 (serie completa de índices
  compuestos, IDH 1990-2023). El CSV viene en encoding latin-1.

Las descargas crudas se cachean en ``data/raw/`` con timestamp, igual que
las de Eurostat: no se re-descarga en cada corrida.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import strftime

import pandas as pd
import requests

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

WB_API = "https://api.worldbank.org/v2/country/all/indicator/{code}"
WB_INDICATORS = {
    "population": "SP.POP.TOTL",
    "gdp_pc_usd": "NY.GDP.PCAP.CD",
    "gdp_pc_ppp": "NY.GDP.PCAP.PP.CD",
}
HDI_URL = (
    "https://hdr.undp.org/sites/default/files/2025_HDR/"
    "HDR25_Composite_indices_complete_time_series.csv"
)


def _cached_download(name: str, url: str, params: dict | None = None,
                     force: bool = False) -> Path:
    """Descarga `url` a data/raw/{name}_{YYYYMMDD} reutilizando cache."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(RAW_DIR.glob(f"{name}_*"))
    if existing and not force:
        logger.info("Cache hit: %s", existing[-1].name)
        return existing[-1]
    logger.info("Descargando %s", name)
    resp = requests.get(url, params=params, timeout=300)
    resp.raise_for_status()
    suffix = ".json" if "json" in resp.headers.get("content-type", "") else ".csv"
    path = RAW_DIR / f"{name}_{strftime('%Y%m%d')}{suffix}"
    path.write_bytes(resp.content)
    return path


def fetch_worldbank(code: str, start_year: int, end_year: int,
                    force: bool = False) -> pd.DataFrame:
    """Serie país-año de un indicador del Banco Mundial.

    Devuelve columnas: iso3, year, value. Incluye todos los países del
    mundo (los agregados regionales del BM se filtran después por iso3).
    """
    path = _cached_download(
        f"worldbank_{code}_{start_year}_{end_year}",
        WB_API.format(code=code),
        params={"format": "json", "date": f"{start_year}:{end_year}",
                "per_page": "20000"},
        force=force,
    )
    # La respuesta es [metadata, filas]
    meta, rows = json.loads(path.read_text(encoding="utf-8"))
    if meta.get("pages", 1) > 1:
        raise RuntimeError(
            f"Respuesta paginada del BM para {code}: subir per_page"
        )
    df = pd.DataFrame(rows)
    df = df.rename(columns={"countryiso3code": "iso3", "date": "year"})
    df = df[df["iso3"].str.len() == 3][["iso3", "year", "value"]]
    df["year"] = df["year"].astype(int)
    return df


def fetch_hdi(force: bool = False) -> pd.DataFrame:
    """IDH por país-año desde la serie completa del HDR (PNUD).

    Devuelve columnas: iso3, year, hdi.
    """
    path = _cached_download("undp_hdi", HDI_URL, force=force)
    wide = pd.read_csv(path, encoding="latin-1", low_memory=False)
    hdi_cols = [c for c in wide.columns
                if c.startswith("hdi_") and c[4:].isdigit()]
    long = wide.melt(id_vars=["iso3"], value_vars=hdi_cols,
                     var_name="year", value_name="hdi")
    long["year"] = long["year"].str[4:].astype(int)
    long["hdi"] = pd.to_numeric(long["hdi"], errors="coerce")
    return long.dropna(subset=["hdi"])


def build_indicators(iso3: list[str], start_year: int, end_year: int,
                     force: bool = False) -> pd.DataFrame:
    """Tabla ancha iso3 × year con población, PIB per cápita (USD y PPA) e IDH.

    Los faltantes quedan NaN (p. ej. PPA de Liechtenstein o IDH de Kosovo
    no existen en las fuentes).
    """
    base = pd.MultiIndex.from_product(
        [sorted(iso3), range(start_year, end_year + 1)],
        names=["iso3", "year"],
    ).to_frame(index=False)

    out = base
    for name, code in WB_INDICATORS.items():
        serie = fetch_worldbank(code, start_year, end_year, force=force)
        serie = serie.rename(columns={"value": name})
        out = out.merge(serie, on=["iso3", "year"], how="left")

    hdi = fetch_hdi(force=force)
    out = out.merge(hdi, on=["iso3", "year"], how="left")

    faltantes = out.drop(columns=["iso3", "year"]).isna().groupby(
        out["iso3"]).sum()
    con_huecos = faltantes[faltantes.sum(axis=1) > 0]
    if not con_huecos.empty:
        logger.info("Indicadores con faltantes por pais:\n%s",
                    con_huecos.to_string())
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo = build_indicators(["ARG", "DEU", "ESP"], 2014, 2023)
    print(demo[demo["year"] == 2023].to_string(index=False))
