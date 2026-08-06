"""Tests del análisis nativo de Argentina (src/argentina.py), sin red."""
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

import pandas as pd
import pytest

import argentina as a


@pytest.fixture(scope="module")
def df():
    return a.load_arg_raw()


@pytest.fixture(scope="module")
def eg(df):
    return a.egresados(df)


def test_load_columnas(df):
    for c in ("ANIO", "TIPO_UNIV", "NIVEL_ACADEM", "DISCIP_ESPECIF",
              "TIPO_ALUMNO", "VALOR"):
        assert c in df.columns
    assert df["ANIO"].dtype.kind == "i"


def test_egresados_excluye_pregrado_y_estudiantes(eg):
    assert (eg["TIPO_ALUMNO"] == "EGRESADOS").all()
    assert "Pregrado" not in set(eg["NIVEL_ACADEM"])
    assert set(eg["NIVEL_ACADEM"]) == {"Grado", "Posgrado"}


def test_periodo_dinamico(df):
    y0, y1 = a.periodo(df)
    assert y0 == 2014 and y1 >= 2023      # se extiende si se agregan años


def test_detalle_base100_y_participacion(eg):
    t = a.tabla_tipo_univ(eg)
    # base 100 en el primer año de cada categoría
    primeros = t.sort_values("anio").groupby("categoria").first()
    assert (primeros["base100"] == 100.0).all()
    # participaciones suman ~100 por año
    suma = t.groupby("anio")["participacion_pct"].sum()
    assert ((suma - 100).abs() < 0.1).all()


def test_grado_por_mil(eg):
    pop = pd.Series({2014: 43_000_000, 2015: 43_500_000, 2016: 43_900_000,
                     2017: 44_300_000, 2018: 44_650_000, 2019: 45_000_000,
                     2020: 45_200_000, 2021: 45_300_000, 2022: 45_400_000,
                     2023: 45_500_000}, name="poblacion")
    t = a.tabla_grado_por_mil(eg, pop)
    assert {"anio", "egresados_grado", "poblacion", "grado_por_mil"} <= set(t.columns)
    assert (t["grado_por_mil"] > 0).all()
    # coherencia aritmética de una fila (grado_por_mil está redondeado a 3 dec.)
    fila = t[t["anio"] == 2023].iloc[0]
    assert abs(fila["grado_por_mil"]
               - fila["egresados_grado"] / fila["poblacion"] * 1000) < 1e-3


def test_ratio_psico_ing(eg):
    t = a.tabla_ratio_psico_ing(eg)
    assert t["anio"].iloc[-1].startswith("Global")
    # el ratio global = suma psico / suma ing
    glob = t.iloc[-1]
    assert abs(glob["ratio_psico_por_ing"]
               - glob["psicología"] / glob["ingeniería"]) < 0.01
    años = t[t["anio"].str.isdigit()]
    assert (años["ratio_psico_por_ing"] > 0).all()


def test_disciplinas_ranking(eg):
    t = a.tabla_disciplinas(eg)
    assert t["disciplina"].nunique() == 37
    # ranking 1 existe en cada año y es el de más egresados
    for anio, g in t.groupby("anio"):
        top = g.loc[g["egresados"].idxmax()]
        assert top["ranking"] == 1


def test_proxy_egre_estu(df):
    t = a.tabla_egre_vs_estu(df)
    assert {"anio", "egresados", "estudiantes",
            "egresados_por_100_estud"} <= set(t.columns)
    assert (t["estudiantes"] > t["egresados"]).all()   # stock > flujo anual


def test_figuras_devuelven_figure(eg):
    t_tipo = a.tabla_tipo_univ(eg)
    t_nivel = a.tabla_nivel_academ(eg)
    t_disc = a.tabla_disciplinas(eg)
    t_ratio = a.tabla_ratio_psico_ing(eg)
    assert isinstance(a.fig_tipo_univ_nivel(t_tipo), Figure)   # niveles, mismo eje
    assert isinstance(a.fig_tipo_univ_torta(t_tipo), Figure)
    assert isinstance(a.fig_nivel_nivel(t_nivel), Figure)      # niveles, doble eje
    assert isinstance(a.fig_top10_por_anio(t_disc), Figure)
    assert isinstance(a.fig_top10_comparativo(t_disc), Figure)
    assert isinstance(a.fig_ratio_psico_ing(t_ratio), Figure)
