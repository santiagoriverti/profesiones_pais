"""Análisis nativo de egresados universitarios de Argentina (SPU).

A diferencia de ``build_panel``/``crosswalk`` (que llevan la SPU a ISCED-F
para comparar con Europa), este módulo trabaja las categorías **propias** de
la Síntesis de Información Universitaria: tipo de universidad, nivel académico
y disciplina específica. Alimenta el notebook ``01_profesiones_argentina``.

Reglas fijas del análisis:
- Solo ``TIPO_ALUMNO == "EGRESADOS"`` (salvo el proxy egreso/estudiantes).
- Se **excluye siempre** ``NIVEL_ACADEM == "Pregrado"`` (ISCED 5).
- El período se toma del propio archivo (2014-2023 hoy; se extiende solo si
  el Excel se actualiza con años nuevos).

Fuente: ``data/external/profesiones_arg.xlsx`` (columnas ANIO, TIPO_UNIV,
NIVEL_ACADEM, OF_ACADEM, DISCIP_OCDE, DISCIP_ESPECIF, TIPO_ALUMNO, U_MED,
VALOR). ``VALOR`` ya viene como entero (cantidad de personas).
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from indicators import fetch_worldbank
from spu_data import SPU_XLSX

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "argentina"
GRAFICOS_DIR = OUTPUT_DIR / "graficos"

DPI = 600
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
          "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PREGRADO = "Pregrado"
COL_CATEGORIA = {"TIPO_UNIV": "tipo_univ", "NIVEL_ACADEM": "nivel_academ"}


# --------------------------------------------------------------------------
# Carga y preparación
# --------------------------------------------------------------------------
def load_arg_raw(path: Path = SPU_XLSX) -> pd.DataFrame:
    """Lee el Excel crudo de la SPU y valida columnas."""
    df = pd.read_excel(path)
    esperadas = {"ANIO", "TIPO_UNIV", "NIVEL_ACADEM", "OF_ACADEM",
                 "DISCIP_ESPECIF", "TIPO_ALUMNO", "VALOR"}
    faltan = esperadas - set(df.columns)
    if faltan:
        raise ValueError(f"Columnas faltantes en {path.name}: {faltan}")
    df["ANIO"] = df["ANIO"].astype(int)
    return df


def egresados(df: pd.DataFrame) -> pd.DataFrame:
    """Egresados excluyendo Pregrado (base de todos los análisis)."""
    return df[(df["TIPO_ALUMNO"] == "EGRESADOS")
              & (df["NIVEL_ACADEM"] != PREGRADO)].copy()


def estudiantes(df: pd.DataFrame) -> pd.DataFrame:
    """Estudiantes excluyendo Pregrado (solo para el proxy de egreso)."""
    return df[(df["TIPO_ALUMNO"] == "ESTUDIANTES")
              & (df["NIVEL_ACADEM"] != PREGRADO)].copy()


def periodo(df: pd.DataFrame) -> tuple[int, int]:
    """(primer_año, último_año) presentes en los datos."""
    return int(df["ANIO"].min()), int(df["ANIO"].max())


def poblacion_arg(year_min: int, year_max: int) -> pd.Series:
    """Población total de Argentina por año (Banco Mundial, SP.POP.TOTL)."""
    pop = fetch_worldbank("SP.POP.TOTL", year_min, year_max)
    return (pop[pop["iso3"] == "ARG"].set_index("year")["value"]
            .sort_index().rename("poblacion"))


# --------------------------------------------------------------------------
# Helpers de tablas y gráficos
# --------------------------------------------------------------------------
def _detalle_categoria(eg: pd.DataFrame, col: str) -> pd.DataFrame:
    """Tabla de detalle tidy por año y categoría de ``col``.

    Columnas: anio, categoria, egresados, base100 (índice base 100 en el
    primer año de cada categoría) y participacion_pct (share dentro del año).
    """
    g = (eg.groupby(["ANIO", col])["VALOR"].sum()
         .rename("egresados").reset_index()
         .rename(columns={col: "categoria", "ANIO": "anio"})
         .sort_values(["categoria", "anio"]))
    g["base100"] = (g.groupby("categoria")["egresados"]
                    .transform(lambda s: s / s.iloc[0] * 100).round(1))
    g["participacion_pct"] = (g.groupby("anio")["egresados"]
                              .transform(lambda s: s / s.sum() * 100).round(2))
    return g.reset_index(drop=True)


def _abrev(texto: str, n: int = 26) -> str:
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def save_fig(fig, name: str, subdir: str = "") -> Path:
    """Guarda la figura a 600 dpi en output/argentina/graficos[/subdir]."""
    destino = GRAFICOS_DIR / subdir if subdir else GRAFICOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    path = destino / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    return path


def _estilo(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(True, axis="y", color="#e6e6e6", linewidth=0.7)
    ax.set_axisbelow(True)


def _fig_base100(detalle: pd.DataFrame, titulo: str):
    """Líneas de evolución base 100 por categoría."""
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for color, (cat, sub) in zip(PALETA, detalle.groupby("categoria")):
        sub = sub.sort_values("anio")
        ax.plot(sub["anio"], sub["base100"], color=color, lw=2, label=cat,
                marker="o", ms=3)
        ax.annotate(cat, (sub["anio"].iloc[-1], sub["base100"].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center",
                    fontsize=9, color="#444444")
    primer = int(detalle["anio"].min())
    ax.axhline(100, color="#bbbbbb", lw=1, ls="--")
    ax.set_title(titulo, loc="left", fontsize=12)
    ax.set_ylabel(f"Índice base 100 = {primer}")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _estilo(ax)
    fig.tight_layout()
    return fig


def _fig_torta_ultimo(detalle: pd.DataFrame, titulo: str):
    """Torta de la composición del último año."""
    ult = int(detalle["anio"].max())
    d = detalle[detalle["anio"] == ult].sort_values("egresados", ascending=False)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.pie(d["egresados"], labels=d["categoria"], autopct="%1.1f%%",
           startangle=90, counterclock=False,
           colors=PALETA[: len(d)],
           wedgeprops={"edgecolor": "white", "linewidth": 1.5},
           textprops={"fontsize": 9})
    ax.set_title(f"{titulo} — {ult}", loc="center", fontsize=12)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1. TIPO_UNIV
# --------------------------------------------------------------------------
def tabla_tipo_univ(eg: pd.DataFrame) -> pd.DataFrame:
    return _detalle_categoria(eg, "TIPO_UNIV")


def fig_tipo_univ_base100(detalle: pd.DataFrame):
    return _fig_base100(
        detalle, "Egresados por tipo de universidad — evolución base 100")


def fig_tipo_univ_torta(detalle: pd.DataFrame):
    return _fig_torta_ultimo(detalle, "Egresados por tipo de universidad")


# --------------------------------------------------------------------------
# 2. NIVEL_ACADEM  (Grado / Posgrado; Pregrado ya excluido)
# --------------------------------------------------------------------------
def tabla_nivel_academ(eg: pd.DataFrame) -> pd.DataFrame:
    return _detalle_categoria(eg, "NIVEL_ACADEM")


def fig_nivel_base100(detalle: pd.DataFrame):
    return _fig_base100(
        detalle, "Egresados por nivel académico — evolución base 100")


def fig_nivel_torta(detalle: pd.DataFrame):
    return _fig_torta_ultimo(detalle, "Egresados por nivel académico")


def tabla_grado_por_mil(eg: pd.DataFrame, pop: pd.Series) -> pd.DataFrame:
    """Egresados de Grado cada mil habitantes, por año."""
    grado = (eg[eg["NIVEL_ACADEM"] == "Grado"]
             .groupby("ANIO")["VALOR"].sum().rename("egresados_grado"))
    out = grado.to_frame().join(pop, how="left")
    out["grado_por_mil"] = (out["egresados_grado"] / out["poblacion"] * 1000).round(3)
    return out.reset_index().rename(columns={"ANIO": "anio", "index": "anio"})


def fig_grado_por_mil(tabla: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.4))
    t = tabla.sort_values("anio")
    ax.plot(t["anio"], t["grado_por_mil"], color=PALETA[0], lw=2.2, marker="o", ms=4)
    for _, r in t.iterrows():
        ax.annotate(f"{r['grado_por_mil']:.2f}", (r["anio"], r["grado_por_mil"]),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=7.5, color="#444444")
    ax.set_title("Egresados de Grado cada mil habitantes — Argentina",
                 loc="left", fontsize=12)
    ax.set_ylabel("Egresados de Grado / 1.000 hab.")
    ax.set_ylim(bottom=0)
    _estilo(ax)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 3. DISCIP_ESPECIF
# --------------------------------------------------------------------------
def tabla_disciplinas(eg: pd.DataFrame) -> pd.DataFrame:
    """Detalle tidy por año y disciplina (todas las categorías).

    Columnas: anio, disciplina, egresados, participacion_pct, ranking
    (posición dentro del año, 1 = más egresados).
    """
    g = (eg.groupby(["ANIO", "DISCIP_ESPECIF"])["VALOR"].sum()
         .rename("egresados").reset_index()
         .rename(columns={"DISCIP_ESPECIF": "disciplina", "ANIO": "anio"}))
    g["participacion_pct"] = (g.groupby("anio")["egresados"]
                              .transform(lambda s: s / s.sum() * 100).round(2))
    g["ranking"] = (g.groupby("anio")["egresados"]
                    .rank(ascending=False, method="min").astype(int))
    return g.sort_values(["anio", "ranking"]).reset_index(drop=True)


def matriz_disciplinas(eg: pd.DataFrame) -> pd.DataFrame:
    """Matriz disciplina × año (egresados) con total, ordenada por total."""
    m = (eg.groupby(["DISCIP_ESPECIF", "ANIO"])["VALOR"].sum()
         .unstack("ANIO", fill_value=0))
    m["Total"] = m.sum(axis=1)
    return m.sort_values("Total", ascending=False).reset_index() \
            .rename(columns={"DISCIP_ESPECIF": "disciplina"})


def _top_n(detalle: pd.DataFrame, anio: int, n: int = 10) -> pd.DataFrame:
    d = detalle[detalle["anio"] == anio].nsmallest(n, "ranking")
    return d.sort_values("egresados", ascending=True)   # para barh ascendente


def fig_top10_por_anio(detalle: pd.DataFrame, n: int = 10):
    """Small multiples: top-N disciplinas por egresados, un panel por año."""
    anios = sorted(detalle["anio"].unique())
    ncols = 5
    nrows = -(-len(anios) // ncols)   # ceil
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.2 * ncols, 2.4 * nrows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]
    for ax, anio in zip(axes, anios):
        d = _top_n(detalle, anio, n)
        ax.barh(range(len(d)), d["egresados"], color=PALETA[0],
                edgecolor="white", linewidth=0.6)
        ax.set_yticks(range(len(d)))
        ax.set_yticklabels([_abrev(x, 22) for x in d["disciplina"]], fontsize=6)
        ax.set_title(str(anio), fontsize=9, loc="left")
        ax.tick_params(axis="x", labelsize=6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    for ax in axes[len(anios):]:
        ax.axis("off")
    fig.suptitle(f"Top {n} disciplinas por egresados, por año",
                 x=0.01, ha="left", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


def fig_top10_comparativo(detalle: pd.DataFrame, n: int = 10):
    """Barras agrupadas: top-N del primer y del último año, comparados."""
    a0, a1 = int(detalle["anio"].min()), int(detalle["anio"].max())
    top0 = set(_top_n(detalle, a0, n)["disciplina"])
    top1 = set(_top_n(detalle, a1, n)["disciplina"])
    disc = sorted(top0 | top1)

    piv = (detalle[detalle["disciplina"].isin(disc)]
           .pivot_table(index="disciplina", columns="anio",
                        values="egresados", fill_value=0))
    piv = piv.sort_values(a1, ascending=True)

    y = range(len(piv))
    h = 0.4
    fig, ax = plt.subplots(figsize=(9, max(4, 0.5 * len(piv))))
    ax.barh([i + h / 2 for i in y], piv[a0], height=h, color=PALETA[0],
            label=str(a0), edgecolor="white", linewidth=0.5)
    ax.barh([i - h / 2 for i in y], piv[a1], height=h, color=PALETA[1],
            label=str(a1), edgecolor="white", linewidth=0.5)
    ax.set_yticks(list(y))
    ax.set_yticklabels([_abrev(x, 30) for x in piv.index], fontsize=8)
    ax.set_title(f"Top {n} disciplinas por egresados: {a0} vs {a1}",
                 loc="left", fontsize=12)
    ax.set_xlabel("Egresados")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.xaxis.grid(True, color="#e6e6e6", linewidth=0.7)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def tabla_ratio_psico_ing(eg: pd.DataFrame,
                          num: str = "Psicología",
                          den: str = "Ingeniería") -> pd.DataFrame:
    """Ratio de egresados ``num`` por cada egresado de ``den``, por año.

    Incluye una fila 'Global (todos los años)' con los acumulados y el ratio
    global. Va en la tabla de detalle de disciplinas.
    """
    p = eg[eg["DISCIP_ESPECIF"] == num].groupby("ANIO")["VALOR"].sum()
    i = eg[eg["DISCIP_ESPECIF"] == den].groupby("ANIO")["VALOR"].sum()
    tabla = pd.DataFrame({"anio": p.index.astype(str),
                          num.lower(): p.values,
                          den.lower(): i.reindex(p.index).values})
    tabla["ratio_psico_por_ing"] = (tabla[num.lower()] / tabla[den.lower()]).round(3)
    global_row = {
        "anio": "Global (todos los años)",
        num.lower(): int(p.sum()),
        den.lower(): int(i.sum()),
        "ratio_psico_por_ing": round(p.sum() / i.sum(), 3),
    }
    return pd.concat([tabla, pd.DataFrame([global_row])], ignore_index=True)


def fig_ratio_psico_ing(tabla: pd.DataFrame):
    t = tabla[tabla["anio"].str.isdigit()].copy()
    t["anio"] = t["anio"].astype(int)
    glob = tabla.iloc[-1]["ratio_psico_por_ing"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.plot(t["anio"], t["ratio_psico_por_ing"], color=PALETA[3], lw=2.2,
            marker="o", ms=4)
    ax.axhline(glob, color="#bbbbbb", lw=1, ls="--",
               label=f"Global = {glob:.2f}")
    for _, r in t.iterrows():
        ax.annotate(f"{r['ratio_psico_por_ing']:.2f}",
                    (r["anio"], r["ratio_psico_por_ing"]),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=7.5, color="#444444")
    ax.set_title("Egresados de Psicología por cada egresado de Ingeniería",
                 loc="left", fontsize=12)
    ax.set_ylabel("Psicología / Ingeniería")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    _estilo(ax)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 5. Proxy egreso/estudiantes (NO es tasa de deserción; ver notebook)
# --------------------------------------------------------------------------
def tabla_egre_vs_estu(df: pd.DataFrame) -> pd.DataFrame:
    """Relación egresados/estudiantes por año (proxy de intensidad de egreso).

    NO es una tasa de deserción: ESTUDIANTES es un stock (matriculados) y
    EGRESADOS un flujo anual; sin ingresantes por cohorte no se puede inferir
    deserción de forma técnicamente coherente. Se reporta el cociente como
    proxy de intensidad de egreso, explícitamente etiquetado.
    """
    eg = (egresados(df).groupby("ANIO")["VALOR"].sum().rename("egresados"))
    es = (estudiantes(df).groupby("ANIO")["VALOR"].sum().rename("estudiantes"))
    out = pd.concat([eg, es], axis=1).reset_index().rename(columns={"ANIO": "anio"})
    out["egresados_por_100_estud"] = (out["egresados"] / out["estudiantes"] * 100).round(2)
    return out


def fig_egre_vs_estu(tabla: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.4))
    t = tabla.sort_values("anio")
    ax.plot(t["anio"], t["egresados_por_100_estud"], color=PALETA[2], lw=2.2,
            marker="o", ms=4)
    ax.set_title("Egresados cada 100 estudiantes — proxy de intensidad de "
                 "egreso (NO deserción)", loc="left", fontsize=11.5)
    ax.set_ylabel("Egresados por 100 estudiantes")
    ax.set_ylim(bottom=0)
    _estilo(ax)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# Orquestación: genera todo, Excel y ZIP
# --------------------------------------------------------------------------
def _notas() -> pd.DataFrame:
    filas = [
        ("Alcance", "Solo EGRESADOS; se excluye siempre Pregrado (ISCED 5). "
         "Período tomado del propio archivo."),
        ("tipo_univ", "Egresados por tipo de universidad (Privado/Pública): "
         "egresados, índice base 100 y participación por año."),
        ("nivel_academ", "Egresados por nivel académico (Grado/Posgrado): "
         "egresados, índice base 100 y participación por año."),
        ("grado_por_mil", "Egresados de Grado cada mil habitantes "
         "(población total Argentina, Banco Mundial SP.POP.TOTL)."),
        ("disciplinas", "Detalle por año y disciplina (todas): egresados, "
         "participación y ranking dentro del año."),
        ("matriz_disciplinas", "Egresados por disciplina × año, con total."),
        ("ratio_psico_ing", "Egresados de Psicología por cada egresado de "
         "Ingeniería, por año y global (todos los años)."),
        ("egre_vs_estu", "Relación egresados/estudiantes (egresados cada 100 "
         "estudiantes). PROXY de intensidad de egreso, NO tasa de deserción: "
         "ESTUDIANTES es stock y EGRESADOS flujo; sin ingresantes por cohorte "
         "no se puede inferir deserción de forma técnicamente coherente."),
    ]
    return pd.DataFrame(filas, columns=["hoja", "descripcion"])


def exportar_todo(path: Path = SPU_XLSX, dpi: int = DPI) -> Path:
    """Genera todos los gráficos (600 dpi), el Excel de detalle y el ZIP.

    Devuelve la ruta del ZIP ``profesiones_argentina_export.zip``.
    """
    df = load_arg_raw(path)
    eg = egresados(df)
    y0, y1 = periodo(df)
    pop = poblacion_arg(y0, y1)

    # Tablas
    t_tipo = tabla_tipo_univ(eg)
    t_nivel = tabla_nivel_academ(eg)
    t_grado_mil = tabla_grado_por_mil(eg, pop)
    t_disc = tabla_disciplinas(eg)
    t_matriz = matriz_disciplinas(eg)
    t_ratio = tabla_ratio_psico_ing(eg)
    t_proxy = tabla_egre_vs_estu(df)

    # Gráficos
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    figs = {
        "01_tipo_univ_base100": fig_tipo_univ_base100(t_tipo),
        "02_tipo_univ_torta": fig_tipo_univ_torta(t_tipo),
        "03_nivel_base100": fig_nivel_base100(t_nivel),
        "04_nivel_torta": fig_nivel_torta(t_nivel),
        "05_grado_por_mil": fig_grado_por_mil(t_grado_mil),
        "06_disciplinas_top10_por_anio": fig_top10_por_anio(t_disc),
        "07_disciplinas_top10_comparativo": fig_top10_comparativo(t_disc),
        "08_ratio_psico_ingenieria": fig_ratio_psico_ing(t_ratio),
        "09_egresados_vs_estudiantes": fig_egre_vs_estu(t_proxy),
    }
    for nombre, fig in figs.items():
        fig.savefig(GRAFICOS_DIR / f"{nombre}.png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)

    # Excel de detalle
    xlsx = OUTPUT_DIR / "analisis_argentina.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        _notas().to_excel(w, sheet_name="notas", index=False)
        t_tipo.to_excel(w, sheet_name="tipo_univ", index=False)
        t_nivel.to_excel(w, sheet_name="nivel_academ", index=False)
        t_grado_mil.to_excel(w, sheet_name="grado_por_mil", index=False)
        t_disc.to_excel(w, sheet_name="disciplinas", index=False)
        t_matriz.to_excel(w, sheet_name="matriz_disciplinas", index=False)
        t_ratio.to_excel(w, sheet_name="ratio_psico_ing", index=False)
        t_proxy.to_excel(w, sheet_name="egre_vs_estu", index=False)

    # ZIP con gráficos + Excel
    zip_path = OUTPUT_DIR / "profesiones_argentina_export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(xlsx, xlsx.name)
        for f in sorted(GRAFICOS_DIR.glob("*.png")):
            zf.write(f, f"graficos/{f.name}")
    return zip_path


if __name__ == "__main__":
    z = exportar_todo()
    print("Export Argentina listo:", z)
