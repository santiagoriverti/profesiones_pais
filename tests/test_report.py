"""Tests de etiquetas ISCED-F, diccionario y resumen (sin red)."""
import pandas as pd

from build_panel import (clasificacion_orientacion_arg,
                         clasificacion_orientacion_eur, data_dictionary)
from eurostat_api import is_narrow
from report import (BROAD_DURAS, BROAD_HUMANIDADES, disciplina_codes,
                    load_field_labels, tabla_ratio_orientacion,
                    variable_summary)

NFD = {"F000", "F020", "F030", "F040", "F050",
       "F070", "F080", "F090", "F100"}


def test_labels_cubren_todos_los_narrow():
    labels = load_field_labels()
    assert len(labels) == 57
    assert all(is_narrow(c) for c in labels.index)
    assert labels.loc["F061"].startswith("Tecnologías de la información")
    labels_en = load_field_labels("en")
    assert labels_en.loc["F061"] == "Information and communication technologies"


def test_disciplina_codes_excluye_nfd():
    disc = disciplina_codes()
    assert disc.isdisjoint(NFD)          # ningún "not further defined"
    assert len(disc) == 57 - len(NFD)    # el resto sí está
    assert "F061" in disc                # una disciplina real de control


def test_tabla_ratio_orientacion():
    # AAA: humanístico F021=200 / duro F071=100 → 2.0 ; BBB: F031=50 / F061=200 → 0.25
    panel = pd.DataFrame({
        "iso3": ["AAA", "AAA", "BBB", "BBB"],
        "year": [2023] * 4,
        "isced_level": ["ED6"] * 4,
        "iscedf_narrow": ["F021", "F071", "F031", "F061"],
        "graduates": [200.0, 100.0, 50.0, 200.0],
        "source": ["x"] * 4,
    })
    t = tabla_ratio_orientacion(panel, 2023)
    assert list(t["ranking"]) == [1, 2]
    assert t.iloc[0]["iso3"] == "AAA"
    assert abs(t.iloc[0]["ratio_hum_por_dura"] - 2.0) < 1e-6
    assert t.iloc[-1]["iso3"] == "BBB"
    assert abs(t.iloc[-1]["ratio_hum_por_dura"] - 0.25) < 1e-6


def _marca_coherente(df):
    """hum_soc/cien_tec_ing deben coincidir con el prefijo broad del código,
    exactamente como agrupa tabla_ratio_orientacion. Excluyentes entre sí."""
    for _, r in df.iterrows():
        broad = r["iscedf_narrow"][:3]
        assert r["hum_soc"] == ("x" if broad in BROAD_HUMANIDADES else "")
        assert r["cien_tec_ing"] == ("x" if broad in BROAD_DURAS else "")
        assert not (r["hum_soc"] == "x" and r["cien_tec_ing"] == "x")


def test_clas_eur_lista_todos_los_campos_y_marca_bien():
    ce = clasificacion_orientacion_eur()
    assert len(ce) == 57                       # todos los campos ISCED-F narrow
    assert {"hum_soc", "cien_tec_ing"} <= set(ce.columns)
    _marca_coherente(ce)
    # F031 (cs. sociales, incluye Psicología) numerador; F071 (ingeniería) denominador
    assert ce.set_index("iscedf_narrow").loc["F031", "hum_soc"] == "x"
    assert ce.set_index("iscedf_narrow").loc["F071", "cien_tec_ing"] == "x"


def test_clas_arg_lista_todas_las_disciplinas_y_marca_bien():
    ca = clasificacion_orientacion_arg()
    assert len(ca) == 38                       # todas las disciplinas SPU
    assert {"spu_disciplina", "hum_soc", "cien_tec_ing"} <= set(ca.columns)
    _marca_coherente(ca)
    m = ca.set_index("spu_disciplina")
    assert m.loc["Psicología", "hum_soc"] == "x"           # F031 → numerador
    assert m.loc["Ingeniería", "cien_tec_ing"] == "x"      # F071 → denominador
    assert m.loc["Medicina", "hum_soc"] == ""              # F091 → fuera del ratio
    assert m.loc["Medicina", "cien_tec_ing"] == ""


def test_diccionario_estructura():
    dicc = data_dictionary()
    assert list(dicc.columns) == ["hoja", "variable", "definicion", "fuente"]
    variables = set(dicc["variable"])
    # las columnas centrales del dataset tienen definición
    for v in ("iso3", "year", "isced_level", "iscedf_narrow", "graduates",
              "population", "gdp_pc_usd", "gdp_pc_ppp", "hdi",
              "grad_per_1000"):
        assert v in variables, f"falta {v} en el diccionario"


def test_variable_summary_imprime_todas_las_columnas():
    panel = pd.DataFrame({
        "iso3": ["ARG", "DEU"], "year": [2020, 2020],
        "isced_level": ["ED6", "ED6"], "iscedf_narrow": ["F061", "F061"],
        "graduates": [100.0, 200.0], "source": ["spu_crosswalk", "eurostat"],
    })
    ind = pd.DataFrame({
        "iso3": ["ARG", "DEU"], "year": [2020, 2020],
        "population": [45e6, 83e6], "gdp_pc_usd": [10000.0, 50000.0],
        "gdp_pc_ppp": [25000.0, 60000.0], "hdi": [0.85, 0.95],
    })
    texto = variable_summary(panel, ind)
    for col in ("graduates", "population", "gdp_pc_ppp", "hdi",
                "grad_per_1000"):
        assert f"\n{col}" in texto
    assert "RESUMEN DE VARIABLES" in texto
