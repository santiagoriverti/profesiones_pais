"""Crosswalk SPU (Argentina) → ISCED-F 2013 narrow.

Argentina no reporta a Eurostat: sus egresados vienen clasificados por
las ~37 disciplinas de la Secretaría de Políticas Universitarias (SPU),
agrupadas en 5 ramas (Ciencias Básicas, Aplicadas, Sociales, Humanas y
de la Salud).

El mapeo vive en ``data/reference/spu_to_iscedf_narrow.csv`` (versionado
en git, pensado para revisión manual). Cada fila documenta la decisión:
``confianza`` ∈ {alta, media, baja} y ``nota`` explica los casos dudosos.

Uso típico::

    cw = load_crosswalk()
    panel_arg = apply_crosswalk(df_spu, cw)   # df_spu por disciplina SPU
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from eurostat_api import is_narrow

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_PATH = PROJECT_ROOT / "data" / "reference" / "spu_to_iscedf_narrow.csv"

RAMAS = {
    "Ciencias Aplicadas",
    "Ciencias Básicas",
    "Ciencias de la Salud",
    "Ciencias Humanas",
    "Ciencias Sociales",
}
CONFIANZAS = {"alta", "media", "baja"}


def load_crosswalk(path: Path = CROSSWALK_PATH) -> pd.DataFrame:
    """Carga y valida el crosswalk. Falla ruidosamente si está roto."""
    cw = pd.read_csv(path)
    expected = ["spu_disciplina", "spu_rama", "iscedf_narrow",
                "iscedf_label", "confianza", "nota"]
    if list(cw.columns) != expected:
        raise ValueError(f"Columnas inesperadas en {path.name}: {list(cw.columns)}")

    dupes = cw[cw["spu_disciplina"].duplicated()]["spu_disciplina"].tolist()
    if dupes:
        raise ValueError(f"Disciplinas SPU duplicadas: {dupes}")

    bad_codes = cw.loc[~cw["iscedf_narrow"].map(is_narrow), "iscedf_narrow"]
    if not bad_codes.empty:
        raise ValueError(f"Códigos no-narrow en el crosswalk: {bad_codes.tolist()}")

    bad_ramas = set(cw["spu_rama"]) - RAMAS
    if bad_ramas:
        raise ValueError(f"Ramas SPU desconocidas: {bad_ramas}")

    bad_conf = set(cw["confianza"]) - CONFIANZAS
    if bad_conf:
        raise ValueError(f"Valores de confianza inválidos: {bad_conf}")

    sin_nota = cw[(cw["confianza"] == "baja") & cw["nota"].isna()]
    if not sin_nota.empty:
        raise ValueError(
            "Mapeos de confianza baja sin nota: "
            f"{sin_nota['spu_disciplina'].tolist()}"
        )
    return cw


def apply_crosswalk(
    df_spu: pd.DataFrame,
    crosswalk: pd.DataFrame | None = None,
    min_confianza: str = "baja",
) -> pd.DataFrame:
    """Convierte egresados por disciplina SPU a campos ISCED-F narrow.

    ``df_spu`` necesita columnas: spu_disciplina, year, isced_level,
    graduates. ``min_confianza`` permite excluir mapeos dudosos
    ("media" descarta los baja; "alta" descarta baja y media).

    Devuelve graduates agregados por (year, isced_level, iscedf_narrow).
    Falla si alguna disciplina del input no está en el crosswalk.
    """
    cw = crosswalk if crosswalk is not None else load_crosswalk()

    orden = {"baja": 0, "media": 1, "alta": 2}
    if min_confianza not in orden:
        raise ValueError(f"min_confianza inválida: {min_confianza}")
    cw = cw[cw["confianza"].map(orden) >= orden[min_confianza]]

    faltantes = set(df_spu["spu_disciplina"]) - set(cw["spu_disciplina"])
    if min_confianza == "baja" and faltantes:
        raise ValueError(f"Disciplinas sin mapeo en el crosswalk: {faltantes}")

    merged = df_spu.merge(
        cw[["spu_disciplina", "iscedf_narrow"]], on="spu_disciplina", how="inner"
    )
    return (
        merged.groupby(["year", "isced_level", "iscedf_narrow"], as_index=False)
        ["graduates"].sum()
    )


if __name__ == "__main__":
    cw = load_crosswalk()
    print(f"{len(cw)} disciplinas SPU mapeadas")
    print(cw["confianza"].value_counts().to_string())
    print("\nCasos de confianza baja (revisar a mano):")
    for _, row in cw[cw["confianza"] == "baja"].iterrows():
        print(f"  - {row['spu_disciplina']} → {row['iscedf_narrow']}")
