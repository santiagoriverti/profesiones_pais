"""Invariantes de integridad sobre las salidas versionadas en data/processed/.

Estos tests corren sin red: leen los parquet/csv commiteados y validan que
el dataset publicado es coherente. Son el guard permanente de la auditoría
2026-07-24 (negativos, nulos, duplicados, códigos huérfanos).
"""
from pathlib import Path

import pandas as pd

from report import load_field_labels

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
CLAVE = ["iso3", "year", "isced_level", "iscedf_narrow"]


def _panel():
    return pd.read_parquet(PROC / "panel.parquet")


def _ind():
    return pd.read_parquet(PROC / "indicators.parquet")


def test_panel_sin_negativos():
    # El guard de build_eurostat_panel fuerza a 0 los artefactos <0 de Eurostat.
    assert (_panel()["graduates"] >= 0).all()


def test_panel_sin_nulos_ni_duplicados():
    panel = _panel()
    assert panel.isna().sum().sum() == 0
    assert not panel.duplicated(CLAVE).any()


def test_panel_codigos_tienen_etiqueta():
    panel = _panel()
    labels = set(load_field_labels().index)
    huerfanos = set(panel["iscedf_narrow"]) - labels
    assert not huerfanos, f"códigos sin etiqueta: {sorted(huerfanos)}"


def test_argentina_presente_y_completa():
    panel = _panel()
    arg = panel[panel["iso3"] == "ARG"]
    assert not arg.empty
    assert set(arg["isced_level"]) == {"ED6", "ED7", "ED8"}


def test_panel_indicadores_join_sin_huerfanos():
    # Toda fila del panel tiene país-año en indicadores.
    panel, ind = _panel(), _ind()
    faltan = set(map(tuple, panel[["iso3", "year"]].values)) - set(
        map(tuple, ind[["iso3", "year"]].values)
    )
    assert not faltan, f"país-año sin indicadores: {sorted(faltan)[:5]}"
