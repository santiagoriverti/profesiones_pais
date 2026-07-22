"""Consolidación del panel de graduados por campo ISCED-F narrow.

Salidas en ``data/processed/``:
- ``panel.parquet``: iso3, year, isced_level, iscedf_narrow, graduates, source
- ``indicators.parquet``: iso3, year, population, gdp_pc_usd, gdp_pc_ppp, hdi
- ``coverage.csv``: cobertura narrow vs broad por país (Eurostat)
- ``dataset.xlsx``: todo lo anterior en un solo Excel (hojas: panel,
  indicadores, panel_indicadores con egresados cada mil habitantes,
  cobertura y crosswalk)

Fuentes:
- Eurostat ``educ_uoe_grad02`` (unit=NR, conteos absolutos) para los
  países que reportan a la UOE (UE + EFTA + candidatos + algunos más).
- Argentina: ``data/external/profesiones_arg.xlsx`` (Síntesis SPU,
  egresados 2014-2023 por disciplina) se convierte con el crosswalk
  SPU → ISCED-F y se agrega con source="spu_crosswalk". Como fallback
  se acepta ``data/raw/spu_egresados.csv`` con columnas
  [spu_disciplina, year, isced_level, graduates].

Además reporta cobertura por país (¿tiene datos a nivel narrow o solo a
nivel broad?) en ``data/processed/coverage.csv``: eso define la muestra
final del análisis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from crosswalk import apply_crosswalk, load_crosswalk
from eurostat_api import fetch_graduates, is_broad, is_narrow
from indicators import build_indicators
from spu_data import SPU_XLSX, load_spu_egresados

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SPU_INPUT = PROJECT_ROOT / "data" / "raw" / "spu_egresados.csv"

# Eurostat usa códigos tipo ISO2 con dos excepciones históricas:
# EL (Grecia) y UK (Reino Unido). Los agregados (EU27_2020, EA19, ...)
# tienen más de 2 caracteres y se excluyen del panel.
ISO2_TO_ISO3 = {
    "AL": "ALB", "AT": "AUT", "BA": "BIH", "BE": "BEL", "BG": "BGR",
    "CH": "CHE", "CY": "CYP", "CZ": "CZE", "DE": "DEU", "DK": "DNK",
    "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA",
    "GE": "GEO",
    "HR": "HRV", "HU": "HUN", "IE": "IRL", "IS": "ISL", "IT": "ITA",
    "LI": "LIE", "LT": "LTU", "LU": "LUX", "LV": "LVA", "ME": "MNE",
    "MK": "MKD", "MT": "MLT", "NL": "NLD", "NO": "NOR", "PL": "POL",
    "PT": "PRT", "RO": "ROU", "RS": "SRB", "SE": "SWE", "SI": "SVN",
    "SK": "SVK", "TR": "TUR", "UK": "GBR", "XK": "XKX",
}


def build_eurostat_panel(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descarga grad02 y devuelve (panel_narrow, coverage)."""
    df = fetch_graduates(force=force)

    # Solo países (códigos de 2 letras); afuera agregados tipo EU27_2020.
    df = df[df["geo"].str.len() == 2].copy()
    unknown = set(df["geo"]) - set(ISO2_TO_ISO3)
    if unknown:
        logger.warning("Códigos geo sin mapeo ISO3 (se excluyen): %s", sorted(unknown))
        df = df[df["geo"].isin(ISO2_TO_ISO3)]
    df["iso3"] = df["geo"].map(ISO2_TO_ISO3)

    df["nivel_campo"] = "otro"
    df.loc[df["iscedf13"].map(is_broad), "nivel_campo"] = "broad"
    df.loc[df["iscedf13"].map(is_narrow), "nivel_campo"] = "narrow"

    # Cobertura por país: cuántas celdas con dato real (no NaN) tiene a
    # cada nivel de detalle del campo de estudio.
    con_dato = df[df["graduates"].notna()]
    coverage = (
        con_dato.groupby(["iso3", "nivel_campo"])
        .agg(celdas=("graduates", "size"), anios=("year", "nunique"))
        .unstack("nivel_campo", fill_value=0)
    )
    coverage.columns = [f"{a}_{b}" for a, b in coverage.columns]
    coverage = coverage.reset_index()
    coverage["cobertura"] = "sin_datos"
    coverage.loc[coverage.get("celdas_broad", 0) > 0, "cobertura"] = "solo_broad"
    coverage.loc[coverage.get("celdas_narrow", 0) > 0, "cobertura"] = "narrow"

    panel = con_dato[con_dato["nivel_campo"] == "narrow"].copy()
    panel = panel.rename(columns={"iscedf13": "iscedf_narrow"})
    panel["source"] = "eurostat_educ_uoe_grad02"
    panel = panel[
        ["iso3", "year", "isced_level", "iscedf_narrow", "graduates", "source"]
    ].sort_values(["iso3", "year", "isced_level", "iscedf_narrow"])
    return panel, coverage


def build_argentina_panel() -> pd.DataFrame | None:
    """Panel de Argentina vía crosswalk SPU, si hay datos disponibles.

    Fuente primaria: ``data/external/profesiones_arg.xlsx`` (Síntesis
    SPU). Fallback: ``data/raw/spu_egresados.csv`` ya en formato tidy
    (columnas: spu_disciplina, year, isced_level, graduates). Si no hay
    ninguno, devuelve None.
    """
    if SPU_XLSX.exists():
        df_spu = load_spu_egresados()
    elif SPU_INPUT.exists():
        df_spu = pd.read_csv(SPU_INPUT)
    else:
        logger.info(
            "No hay %s ni %s; el panel sale sin Argentina.",
            SPU_XLSX.name, SPU_INPUT.name,
        )
        return None
    panel_arg = apply_crosswalk(df_spu, load_crosswalk())
    panel_arg["iso3"] = "ARG"
    panel_arg["source"] = "spu_crosswalk"
    return panel_arg[
        ["iso3", "year", "isced_level", "iscedf_narrow", "graduates", "source"]
    ]


def main(force: bool = False) -> pd.DataFrame:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    panel, coverage = build_eurostat_panel(force=force)

    panel_arg = build_argentina_panel()
    if panel_arg is not None:
        panel = pd.concat([panel, panel_arg], ignore_index=True)
        print(
            f"Argentina via crosswalk SPU: {len(panel_arg):,} filas, "
            f"anios {panel_arg['year'].min()}-{panel_arg['year'].max()}"
        )

    # Indicadores de desarrollo para todos los países del panel
    indicadores = build_indicators(
        sorted(panel["iso3"].unique()),
        int(panel["year"].min()), int(panel["year"].max()),
    )

    # Panel + indicadores, con egresados cada mil habitantes
    panel_ind = panel.merge(indicadores, on=["iso3", "year"], how="left")
    panel_ind["grad_per_1000"] = (
        panel_ind["graduates"] / panel_ind["population"] * 1000
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PROCESSED_DIR / "panel.parquet", index=False)
    indicadores.to_parquet(PROCESSED_DIR / "indicators.parquet", index=False)
    coverage.to_csv(PROCESSED_DIR / "coverage.csv", index=False)

    xlsx = PROCESSED_DIR / "dataset.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        panel.to_excel(writer, sheet_name="panel", index=False)
        indicadores.to_excel(writer, sheet_name="indicadores", index=False)
        panel_ind.to_excel(writer, sheet_name="panel_indicadores", index=False)
        coverage.to_excel(writer, sheet_name="cobertura", index=False)
        load_crosswalk().to_excel(writer, sheet_name="crosswalk_spu", index=False)

    narrow = coverage[coverage["cobertura"] == "narrow"]["iso3"].tolist()
    solo_broad = coverage[coverage["cobertura"] == "solo_broad"]["iso3"].tolist()
    print(f"\nPanel: {len(panel):,} filas -> {PROCESSED_DIR / 'panel.parquet'}")
    print(f"Indicadores: {len(indicadores):,} filas pais-anio -> indicators.parquet")
    print(f"Dataset completo -> {xlsx}")
    print(f"Países con datos a nivel narrow ({len(narrow)}): {', '.join(narrow)}")
    print(f"Países solo a nivel broad ({len(solo_broad)}): {', '.join(solo_broad) or '—'}")
    print("La muestra final del análisis son los países con cobertura narrow.")
    return panel


if __name__ == "__main__":
    main()
