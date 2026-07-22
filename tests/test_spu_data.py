"""Tests del loader SPU (sin depender del Excel real)."""
import pandas as pd

from spu_data import tidy_spu


def _crudo(rows):
    return pd.DataFrame(
        rows,
        columns=["ANIO", "NIVEL_ACADEM", "OF_ACADEM", "DISCIP_ESPECIF",
                 "TIPO_ALUMNO", "VALOR"],
    )


def test_mapeo_niveles_y_exclusiones():
    df = _crudo([
        [2020, "Grado", "Otros", "Medicina", "EGRESADOS", 100],
        [2020, "Posgrado", "Maestría", "Medicina", "EGRESADOS", 10],
        [2020, "Posgrado", "Doctorado", "Medicina", "EGRESADOS", 5],
        [2020, "Posgrado", "Especialidad", "Medicina", "EGRESADOS", 20],
        [2020, "Posgrado", "Otros", "Medicina", "EGRESADOS", 7],   # excluido
        [2020, "Pregrado", "Otros", "Medicina", "EGRESADOS", 50],  # excluido
        [2020, "Grado", "Otros", "Medicina", "ESTUDIANTES", 999],  # excluido
    ])
    out = tidy_spu(df)
    por_nivel = out.set_index("isced_level")["graduates"]
    assert por_nivel["ED6"] == 100
    assert por_nivel["ED7"] == 30  # maestría + especialidad
    assert por_nivel["ED8"] == 5
    assert out["graduates"].sum() == 135


def test_especialidad_excluible():
    df = _crudo([
        [2020, "Posgrado", "Maestría", "Derecho", "EGRESADOS", 10],
        [2020, "Posgrado", "Especialidad", "Derecho", "EGRESADOS", 20],
    ])
    out = tidy_spu(df, include_especialidad=False)
    assert out["graduates"].sum() == 10


def test_agrega_sobre_tipo_universidad():
    df = _crudo([
        [2020, "Grado", "Otros", "Derecho", "EGRESADOS", 10],
        [2020, "Grado", "Otros", "Derecho", "EGRESADOS", 15],  # otra gestión
    ])
    out = tidy_spu(df)
    assert len(out) == 1
    assert out["graduates"].item() == 25
