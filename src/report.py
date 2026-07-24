"""Gráficos para el informe, resumen de variables y exportación a carpeta/ZIP.

Todo lo que produce se guarda bajo ``output/`` (gitignoreado):
    output/graficos/*.png            gráficos generales (600 dpi)
    output/graficos/por_campo/*.png  un scatter de desarrollo por campo
    output/dataset.xlsx              copia del Excel completo
    output/profesiones_pais_export.zip  todo lo anterior comprimido
"""

from __future__ import annotations

import math
import shutil
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
GRAFICOS_DIR = OUTPUT_DIR / "graficos"
LABELS_PATH = PROJECT_ROOT / "data" / "reference" / "iscedf_narrow_labels.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

DPI = 600  # calidad pedida para el informe

# Paleta categórica en orden fijo (validada para visión de color)
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
COLOR_ARG = "#eb6834"
COLOR_RESTO = "#9aa0a6"
COLOR_LINEA = "#2a78d6"


def load_field_labels(lang: str = "es") -> pd.Series:
    """Serie iscedf_narrow → etiqueta (es o en)."""
    labels = pd.read_csv(LABELS_PATH)
    return labels.set_index("iscedf_narrow")[f"label_{lang}"]


def disciplina_codes() -> set[str]:
    """Códigos ISCED-F que son disciplinas reales (excluye 'no_definido').

    Los códigos "not further defined" (F0x0) son residuales de subcampo
    desconocido: pesan ~0,6% y Argentina nunca cae en ellos, así que
    distorsionan cualquier comparación por campo. Se excluyen de los
    gráficos y rankings por campo, pero se conservan en los totales país.
    Si el CSV de etiquetas no trae la columna ``tipo`` (versión vieja), se
    devuelven todos los códigos.
    """
    labels = pd.read_csv(LABELS_PATH)
    if "tipo" not in labels.columns:
        return set(labels["iscedf_narrow"])
    return set(labels.loc[labels["tipo"] == "disciplina", "iscedf_narrow"])


def save_fig(fig, name: str, subdir: str = "") -> Path:
    """Guarda la figura a 600 dpi en output/graficos[/subdir]/name.png."""
    destino = GRAFICOS_DIR / subdir if subdir else GRAFICOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    path = destino / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    return path


def fig_argentina_evolucion(panel: pd.DataFrame, ind: pd.DataFrame):
    """Small multiples: evolución de cada campo en Argentina, cada mil hab.

    Suma ED6+ED7+ED8 por campo y año, normalizada por población.
    """
    labels = load_field_labels()
    disc = disciplina_codes()
    arg = panel[(panel["iso3"] == "ARG") & (panel["iscedf_narrow"].isin(disc))]
    pop = ind[ind["iso3"] == "ARG"].set_index("year")["population"]

    serie = (arg.groupby(["iscedf_narrow", "year"])["graduates"].sum()
             .unstack("year"))
    serie = serie.div(pop, axis=1) * 1000
    # Campos ordenados por volumen (más egresados primero)
    campos = serie.sum(axis=1).sort_values(ascending=False).index.tolist()

    ncols = 4
    nrows = math.ceil(len(campos) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 2.1 * nrows),
                             sharex=True)
    ymax = float(serie.max().max()) * 1.08
    for ax, campo in zip(axes.flat, campos):
        s = serie.loc[campo].dropna()
        ax.plot(s.index, s.values, color=COLOR_LINEA, lw=1.8)
        etiqueta = labels.get(campo, campo)
        if len(etiqueta) > 34:
            etiqueta = etiqueta[:32] + "…"
        ax.set_title(f"{campo} · {etiqueta}", fontsize=7.5, loc="left")
        ax.set_ylim(0, ymax)
        ax.tick_params(labelsize=7)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.yaxis.grid(True, color="#e6e6e6", linewidth=0.6)
        ax.set_axisbelow(True)
    for ax in axes.flat[len(campos):]:
        ax.axis("off")
    fig.suptitle(
        "Argentina: egresados por campo de estudio cada mil habitantes "
        "(ED6-ED8)", x=0.01, ha="left", fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def _scatter_desarrollo(datos: pd.DataFrame, titulo: str, ylabel: str,
                        destacados=("ARG", "DEU", "ESP", "FRA", "ITA",
                                    "POL", "SWE", "TUR", "LUX")):
    """Dos paneles: y vs PIB pc PPA (log) e y vs IDH; ARG resaltada.

    ``datos``: index iso3, columnas [grad_1000, gdp_pc_ppp, hdi].
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, xvar, xlabel, logx in [
        (axes[0], "gdp_pc_ppp",
         "PIB per cápita, PPA ($ internacionales, eje log)", True),
        (axes[1], "hdi", "Índice de Desarrollo Humano", False),
    ]:
        sub = datos.dropna(subset=[xvar, "grad_1000"])
        resto = sub.drop(index="ARG", errors="ignore")
        ax.scatter(resto[xvar], resto["grad_1000"], s=38, color=COLOR_RESTO,
                   alpha=0.75, edgecolor="white", linewidth=1)
        if "ARG" in sub.index:
            ax.scatter(sub.loc["ARG", xvar], sub.loc["ARG", "grad_1000"],
                       s=110, color=COLOR_ARG, edgecolor="white",
                       linewidth=1.5, zorder=3)
        for iso in destacados:
            if iso in sub.index:
                ax.annotate(iso, (sub.loc[iso, xvar], sub.loc[iso, "grad_1000"]),
                            xytext=(5, 4), textcoords="offset points",
                            fontsize=8, color="#333333",
                            fontweight="bold" if iso == "ARG" else "normal")
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel(xlabel, fontsize=9)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(True, color="#e6e6e6", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel(ylabel)
    if titulo:                       # título opcional (los scatters por campo lo usan)
        fig.suptitle(titulo, x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    return fig


def _destacados_extremos(datos: pd.DataFrame, n_extremos: int = 6,
                         n_intermedios: int = 6) -> tuple[str, ...]:
    """Selecciona países a etiquetar: extremos por egresados/mil + intermedios.

    Toma los ``n_extremos`` de arriba y de abajo del eje y (grad_1000) más una
    muestra espaciada de intermedios, y siempre incluye Argentina.
    """
    orden = datos.dropna(subset=["grad_1000"]).sort_values("grad_1000")
    iso = orden.index.tolist()
    sel = set(iso[:n_extremos]) | set(iso[-n_extremos:]) | {"ARG"}
    medio = iso[n_extremos:-n_extremos] if len(iso) > 2 * n_extremos else []
    if medio and n_intermedios:
        paso = max(1, len(medio) // n_intermedios)
        sel |= set(medio[::paso])
    return tuple(sel)


def fig_scatter_total(panel: pd.DataFrame, ind: pd.DataFrame, anio_ref: int):
    """Scatter de desarrollo para el total de egresados universitarios."""
    tot = (panel[panel["year"] == anio_ref]
           .groupby("iso3")["graduates"].sum().rename("egresados"))
    datos = tot.to_frame().join(
        ind[ind["year"] == anio_ref].set_index("iso3"), how="left")
    datos["grad_1000"] = datos["egresados"] / datos["population"] * 1000
    return _scatter_desarrollo(
        datos, "", "Egresados universitarios cada mil habitantes",
        destacados=_destacados_extremos(datos))


def save_field_scatters(panel: pd.DataFrame, ind: pd.DataFrame,
                        anio_ref: int, min_paises: int = 8,
                        show: tuple[str, ...] = ()) -> list[str]:
    """Un scatter de desarrollo por campo de estudio, guardado a 600 dpi.

    Genera output/graficos/por_campo/{campo}.png para cada campo narrow
    con datos en ``anio_ref`` en al menos ``min_paises`` países. Muestra
    en pantalla solo los campos de ``show``; el resto se guarda y cierra.
    Devuelve la lista de campos graficados.
    """
    labels = load_field_labels()
    disc = disciplina_codes()
    ind_ref = ind[ind["year"] == anio_ref].set_index("iso3")
    corte = panel[(panel["year"] == anio_ref)
                  & (panel["iscedf_narrow"].isin(disc))]

    graficados = []
    for campo in sorted(corte["iscedf_narrow"].unique()):
        por_pais = (corte[corte["iscedf_narrow"] == campo]
                    .groupby("iso3")["graduates"].sum().rename("egresados"))
        if len(por_pais) < min_paises:
            continue
        datos = por_pais.to_frame().join(ind_ref, how="left")
        datos["grad_1000"] = datos["egresados"] / datos["population"] * 1000
        fig = _scatter_desarrollo(
            datos,
            f"{campo} · {labels.get(campo, campo)} — "
            f"egresados vs desarrollo, {anio_ref}",
            f"Egresados de {campo} cada mil habitantes",
        )
        save_fig(fig, campo, subdir="por_campo")
        graficados.append(campo)
        if campo in show:
            plt.show()
        else:
            plt.close(fig)
    return graficados


# Orientación humanística/social vs. científico-técnica ("duras"), por país.
# ISCED-F narrow no aísla Psicología (cae en F031, Cs. sociales), así que a
# nivel comparativo se usan los campos broad: F02 Artes y humanidades + F03
# Cs. sociales/periodismo (incluye Psicología) como orientación humanística,
# y F05 Cs. naturales/matemática + F06 TIC + F07 Ingeniería como "duras".
BROAD_HUMANIDADES = ("F02", "F03")
BROAD_DURAS = ("F05", "F06", "F07")


def tabla_ratio_orientacion(panel: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Ranking de países por egresados humanísticos/sociales por cada "duro".

    Cociente = (F02+F03) / (F05+F06+F07) en ``anio`` (suma ED6-ED8). Devuelve
    columnas: ranking, iso3, humanidades_sociales, ciencias_tecnologia,
    ratio_hum_por_dura; ordenado de mayor a menor ratio.
    """
    d = panel[panel["year"] == anio].copy()
    d["broad"] = d["iscedf_narrow"].str[:3]
    hum = (d[d["broad"].isin(BROAD_HUMANIDADES)].groupby("iso3")["graduates"]
           .sum().rename("humanidades_sociales"))
    dur = (d[d["broad"].isin(BROAD_DURAS)].groupby("iso3")["graduates"]
           .sum().rename("ciencias_tecnologia"))
    t = pd.concat([hum, dur], axis=1).dropna()
    t = t[t["ciencias_tecnologia"] > 0]
    t["ratio_hum_por_dura"] = (t["humanidades_sociales"]
                               / t["ciencias_tecnologia"]).round(3)
    t = (t.sort_values("ratio_hum_por_dura", ascending=False)
         .reset_index().rename(columns={"index": "iso3"}))
    t.insert(0, "ranking", range(1, len(t) + 1))
    return t


def fig_ranking_ratio(tabla: pd.DataFrame, anio: int):
    """Barras horizontales del ranking del ratio humanidades/duras (ARG resaltada)."""
    t = tabla.sort_values("ratio_hum_por_dura")
    colores = [COLOR_ARG if iso == "ARG" else COLOR_RESTO for iso in t["iso3"]]
    fig, ax = plt.subplots(figsize=(9, max(5, 0.28 * len(t))))
    ax.barh(range(len(t)), t["ratio_hum_por_dura"], color=colores,
            edgecolor="white", linewidth=0.6)
    ax.axvline(1, color="#888888", lw=1, ls="--")   # paridad
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(t["iso3"], fontsize=7.5)
    ax.set_xlabel(f"Egresados de humanidades y cs. sociales por cada egresado "
                  f"de ciencias, tecnología e ingeniería ({anio})")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.xaxis.grid(True, color="#e6e6e6", linewidth=0.7)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def variable_summary(panel: pd.DataFrame, ind: pd.DataFrame) -> str:
    """Resumen imprimible de todas las variables del dataset (para informe)."""
    from build_panel import data_dictionary

    panel_ind = panel.merge(ind, on=["iso3", "year"], how="left")
    panel_ind["grad_per_1000"] = (
        panel_ind["graduates"] / panel_ind["population"] * 1000
    )
    dicc = data_dictionary().set_index("variable")["definicion"]

    lineas = [
        "=" * 78,
        "RESUMEN DE VARIABLES — dataset profesiones_pais",
        "=" * 78,
        f"Panel: {len(panel):,} filas | {panel['iso3'].nunique()} países | "
        f"años {panel['year'].min()}-{panel['year'].max()} | "
        f"{panel['iscedf_narrow'].nunique()} campos de estudio | "
        f"niveles {', '.join(sorted(panel['isced_level'].unique()))}",
        f"Indicadores: {len(ind):,} filas país-año",
        "-" * 78,
    ]
    for col in panel_ind.columns:
        serie = panel_ind[col]
        definicion = dicc.get(col, "")
        lineas.append(f"\n{col}")
        if definicion:
            lineas.append(f"  {definicion}")
        n_falt = int(serie.isna().sum())
        if pd.api.types.is_numeric_dtype(serie) and col != "year":
            lineas.append(
                f"  n={serie.notna().sum():,} | faltantes={n_falt:,} | "
                f"min={serie.min():,.2f} | mediana={serie.median():,.2f} | "
                f"media={serie.mean():,.2f} | max={serie.max():,.2f}"
            )
        else:
            valores = serie.dropna().unique()
            muestra = ", ".join(map(str, sorted(valores)[:8]))
            extra = "…" if len(valores) > 8 else ""
            lineas.append(
                f"  n={serie.notna().sum():,} | únicos={len(valores)} "
                f"({muestra}{extra})"
            )
    lineas.append("\n" + "=" * 78)
    return "\n".join(lineas)


def export_zip() -> Path:
    """Arma output/ con gráficos + Excel y lo comprime en un ZIP."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    xlsx = PROCESSED_DIR / "dataset.xlsx"
    if xlsx.exists():
        shutil.copy2(xlsx, OUTPUT_DIR / "dataset.xlsx")

    zip_path = OUTPUT_DIR / "profesiones_pais_export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUTPUT_DIR.rglob("*")):
            if f.is_file() and f != zip_path:
                zf.write(f, f.relative_to(OUTPUT_DIR))
    return zip_path
