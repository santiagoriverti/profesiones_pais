"""Tests de armado de filtros y clasificación de códigos (sin red)."""
import pytest

from eurostat_api import build_filter, is_broad, is_narrow


def test_filter_order_grad02():
    # Orden verificado contra el DSD: freq.unit.isced11.iscedf13.sex.geo
    filt = build_filter(
        "educ_uoe_grad02", freq="A", unit="NR",
        isced11=["ED6", "ED7"], iscedf13="F011", sex="T", geo=["AT", "DE"],
    )
    assert filt == "A.NR.ED6+ED7.F011.T.AT+DE"


def test_filter_order_grad10_differs():
    # grad10 tiene sex en 2.ª posición y unit en 5.ª (¡distinto a grad02!)
    filt = build_filter(
        "educ_uoe_grad10", freq="A", sex="F",
        isced11="ED6", iscedf13="F011", unit="PC", geo="AT",
    )
    assert filt == "A.F.ED6.F011.PC.AT"


def test_filter_empty_dims_are_wildcards():
    assert build_filter("educ_uoe_grad02", freq="A") == "A....."


def test_filter_rejects_unknown_dataset_and_dims():
    with pytest.raises(ValueError):
        build_filter("no_existe", freq="A")
    with pytest.raises(ValueError):
        build_filter("educ_uoe_grad02", banana="X")


def test_narrow_broad_classification():
    assert is_narrow("F011") and is_narrow("F109")
    assert not is_narrow("F01") and not is_narrow("F0111")
    assert not is_narrow("TOTAL") and not is_narrow("F03_04")
    assert is_broad("F01") and not is_broad("F011")
