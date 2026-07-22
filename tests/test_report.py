"""Tests de etiquetas ISCED-F, diccionario y resumen (sin red)."""
import pandas as pd

from build_panel import data_dictionary
from eurostat_api import is_narrow
from report import load_field_labels, variable_summary


def test_labels_cubren_todos_los_narrow():
    labels = load_field_labels()
    assert len(labels) == 57
    assert all(is_narrow(c) for c in labels.index)
    assert labels.loc["F061"].startswith("Tecnologías de la información")
    labels_en = load_field_labels("en")
    assert labels_en.loc["F061"] == "Information and communication technologies"


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
