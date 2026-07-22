"""Tests del crosswalk SPU → ISCED-F narrow."""
import pandas as pd
import pytest

from crosswalk import apply_crosswalk, load_crosswalk

CASOS_BAJA_ESPERADOS = {
    "Industrias",
    "Sanidad",
    "Relaciones Institucionales y Humanas",
    "Otras Ciencias Aplicadas",
    "Otras Ciencias Sociales",
}


def test_crosswalk_valido_y_completo():
    cw = load_crosswalk()  # load_crosswalk ya valida códigos, ramas, etc.
    assert len(cw) == 37
    assert cw["spu_rama"].nunique() == 5


def test_casos_ambiguos_marcados_baja_con_nota():
    cw = load_crosswalk()
    bajas = set(cw[cw["confianza"] == "baja"]["spu_disciplina"])
    assert CASOS_BAJA_ESPERADOS <= bajas
    con_nota = cw[cw["confianza"] == "baja"]["nota"].notna().all()
    assert con_nota


def test_apply_crosswalk_agrega_por_campo():
    df_spu = pd.DataFrame({
        "spu_disciplina": ["Medicina", "Odontología", "Derecho"],
        "year": [2020, 2020, 2020],
        "isced_level": ["ED6", "ED6", "ED6"],
        "graduates": [100, 50, 200],
    })
    out = apply_crosswalk(df_spu)
    # Medicina y Odontología colapsan en F091
    f091 = out[out["iscedf_narrow"] == "F091"]["graduates"].item()
    assert f091 == 150
    assert out[out["iscedf_narrow"] == "F042"]["graduates"].item() == 200


def test_apply_crosswalk_falla_con_disciplina_desconocida():
    df_spu = pd.DataFrame({
        "spu_disciplina": ["Alquimia"], "year": [2020],
        "isced_level": ["ED6"], "graduates": [1],
    })
    with pytest.raises(ValueError, match="sin mapeo"):
        apply_crosswalk(df_spu)


def test_min_confianza_filtra():
    df_spu = pd.DataFrame({
        "spu_disciplina": ["Sanidad", "Medicina"],
        "year": [2020, 2020],
        "isced_level": ["ED6", "ED6"],
        "graduates": [10, 100],
    })
    out = apply_crosswalk(df_spu, min_confianza="alta")
    assert set(out["iscedf_narrow"]) == {"F091"}
    assert out["graduates"].sum() == 100
