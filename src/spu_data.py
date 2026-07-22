"""Carga de egresados de Argentina (SPU) desde data/external/profesiones_arg.xlsx.

Estructura del archivo (Síntesis de Información Universitaria, SPU):
    ANIO, TIPO_UNIV, NIVEL_ACADEM, OF_ACADEM, DISCIP_OCDE, DISCIP_ESPECIF,
    TIPO_ALUMNO, U_MED, VALOR

- ``DISCIP_ESPECIF`` son las 37 disciplinas SPU que usa el crosswalk
  (``data/reference/spu_to_iscedf_narrow.csv``).
- ``TIPO_ALUMNO`` distingue EGRESADOS de ESTUDIANTES; acá solo egresados.
- Cobertura verificada: 2014-2023, universidades públicas y privadas.

Mapeo de niveles a ISCED 2011 (decisión documentada):
    Grado                    → ED6
    Posgrado + Maestría      → ED7
    Posgrado + Especialidad  → ED7  (en el mapeo UNESCO de Argentina las
                                     especializaciones son ISCED 7; se puede
                                     excluir con include_especialidad=False)
    Posgrado + Doctorado     → ED8
    Pregrado                 → ISCED 5 (fuera del panel ED6-ED8): se excluye
    Posgrado + Otros         → sin apertura por título: se excluye con aviso
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPU_XLSX = PROJECT_ROOT / "data" / "external" / "profesiones_arg.xlsx"

# (NIVEL_ACADEM, OF_ACADEM) → nivel ISCED 2011
NIVEL_TO_ISCED = {
    ("Grado", "Otros"): "ED6",
    ("Posgrado", "Maestría"): "ED7",
    ("Posgrado", "Especialidad"): "ED7",
    ("Posgrado", "Doctorado"): "ED8",
}


def tidy_spu(df: pd.DataFrame, include_especialidad: bool = True) -> pd.DataFrame:
    """Pasa el crudo SPU al formato que espera el crosswalk.

    Devuelve columnas: spu_disciplina, year, isced_level, graduates
    (agregado sobre tipo de universidad pública/privada).
    """
    eg = df[df["TIPO_ALUMNO"] == "EGRESADOS"].copy()

    niveles = dict(NIVEL_TO_ISCED)
    if not include_especialidad:
        niveles.pop(("Posgrado", "Especialidad"))

    key = list(zip(eg["NIVEL_ACADEM"], eg["OF_ACADEM"]))
    eg["isced_level"] = [niveles.get(k) for k in key]

    excluidos = eg[eg["isced_level"].isna()]
    if not excluidos.empty:
        detalle = (
            excluidos.groupby(["NIVEL_ACADEM", "OF_ACADEM"])["VALOR"].sum()
        )
        logger.info(
            "SPU: se excluyen %s egresados fuera de ED6-ED8:\n%s",
            f"{int(excluidos['VALOR'].sum()):,}", detalle.to_string(),
        )

    out = (
        eg.dropna(subset=["isced_level"])
        .rename(columns={"DISCIP_ESPECIF": "spu_disciplina",
                         "ANIO": "year", "VALOR": "graduates"})
        .groupby(["spu_disciplina", "year", "isced_level"], as_index=False)
        ["graduates"].sum()
    )
    out["year"] = out["year"].astype(int)
    return out


def load_spu_egresados(
    path: Path = SPU_XLSX, include_especialidad: bool = True
) -> pd.DataFrame:
    """Lee el Excel de la SPU y devuelve egresados en formato tidy."""
    df = pd.read_excel(path)
    expected = {"ANIO", "NIVEL_ACADEM", "OF_ACADEM", "DISCIP_ESPECIF",
                "TIPO_ALUMNO", "VALOR"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en {path.name}: {missing}")
    return tidy_spu(df, include_especialidad=include_especialidad)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    tidy = load_spu_egresados()
    print(f"{len(tidy):,} filas | años {tidy['year'].min()}-{tidy['year'].max()}")
    print(tidy.groupby("isced_level")["graduates"].sum().to_string())
