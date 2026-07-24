# -*- coding: utf-8 -*-
"""Genera notebooks/00_profesiones_mundo.ipynb.

El notebook NO se edita a mano: modificar este script, correrlo y validar
la ejecucion end-to-end (nbclient) antes de commitear.
"""
import json

def md(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}

def code(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": source.splitlines(keepends=True)}

cells = []

cells.append(md("""# Profesiones en el mundo — egresados por campo de estudio (Eurostat + Argentina)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/profesiones_pais/blob/main/notebooks/00_profesiones_mundo.ipynb)

Pipeline end-to-end del proyecto **profesiones_pais**: descarga de graduados
por campo ISCED-F 2013 a nivel *narrow* (F011, F021, ...) desde Eurostat,
crosswalk SPU → ISCED-F para Argentina, indicadores de desarrollo
(población, PIB per cápita e IDH) y consolidación del panel
`iso3 × year × isced_level × iscedf_narrow` desde **2014**.

**Notas sobre las fuentes (verificado contra la API el 2026-07-22):**
- `educ_uoe_grad02` viene en `unit=NR` (conteos absolutos) → fuente primaria.
- `educ_uoe_grad10` viene solo en `unit=PC` y es la **distribución por sexo
  dentro de cada campo** (no la composición por campo), por eso no se usa
  para reconstruir absolutos."""))

cells.append(code("""# Setup: instala dependencias y clona (o sincroniza) el repo si estamos en Colab
import os, pathlib, shutil, subprocess, sys

REPO_URL = "https://github.com/santiagoriverti/profesiones_pais.git"
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "pandas", "requests", "pyarrow", "matplotlib", "openpyxl"], check=True)
    repo = pathlib.Path("/content/profesiones_pais")
    if repo.exists():
        # Runtime reutilizado: sincronizar con main pisando cambios locales
        # (las corridas anteriores modifican data/processed/, que está trackeado,
        #  por eso un git pull acá fallaría)
        try:
            subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin"], check=True)
            subprocess.run(["git", "-C", str(repo), "reset", "-q", "--hard",
                            "origin/main"], check=True)
        except subprocess.CalledProcessError:
            shutil.rmtree(repo)   # clon roto: se rehace desde cero
    if not repo.exists():
        subprocess.run(["git", "clone", "-q", REPO_URL, str(repo)], check=True)
    os.chdir(repo)
else:
    root = pathlib.Path.cwd()
    if not (root / "src").exists():
        root = root.parent  # el notebook vive en notebooks/
    os.chdir(root)

sys.path.insert(0, str(pathlib.Path("src").resolve()))
# Purga módulos del proyecto ya importados (por si el kernel tenía una versión vieja)
for _m in ("eurostat_api", "crosswalk", "spu_data", "indicators", "build_panel"):
    sys.modules.pop(_m, None)
print("Directorio de trabajo:", os.getcwd())"""))

cells.append(md("""## Paso 1 — Descarga desde Eurostat

`fetch_graduates()` baja `educ_uoe_grad02` (todos los países y campos,
ED6/ED7/ED8, sexo total, **2014 en adelante** — alineado con la serie
argentina) y cachea el crudo en `data/raw/` con timestamp: las corridas
siguientes no re-descargan."""))

cells.append(code("""import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from eurostat_api import fetch_graduates, is_narrow

df = fetch_graduates()
print(f"{len(df):,} filas | {df['geo'].nunique()} geografías | "
      f"años {df['year'].min()}-{df['year'].max()} | "
      f"{int(df['iscedf13'].map(is_narrow).sum()):,} filas a nivel narrow")
df.head()"""))

cells.append(md("""## Paso 2 — Panel consolidado, indicadores y export

`build_panel.main()` hace todo: filtra los campos *narrow*, convierte los
códigos geo a ISO3, integra Argentina (Excel SPU + crosswalk), descarga los
indicadores de desarrollo (población y PIB per cápita del Banco Mundial;
IDH del PNUD) y escribe en `data/processed/`:

- `panel.parquet` y `indicators.parquet`
- `coverage.csv` (cobertura narrow vs broad por país)
- **`dataset.xlsx`** con todo el dataset procesado (hojas: `panel`,
  `indicadores`, `panel_indicadores` — con egresados cada mil habitantes —,
  `cobertura` y `crosswalk_spu`)."""))

cells.append(code("""from build_panel import main as build_panel_main

panel = build_panel_main()
panel.head()"""))

cells.append(md("""## Paso 3 — Crosswalk SPU → ISCED-F (Argentina)

Argentina no reporta a Eurostat: sus egresados vienen por las disciplinas
de la SPU (`data/external/profesiones_arg.xlsx`, Síntesis de Información
Universitaria, 2014-2023) y `build_panel` los integra automáticamente vía el
crosswalk `data/reference/spu_to_iscedf_narrow.csv` (pensado para revisión
manual). Mapeo de niveles: Grado → ED6; Maestría y Especialidad → ED7;
Doctorado → ED8 (Pregrado y "Posgrado/Otros" quedan fuera). Abajo se listan
los casos del crosswalk que requieren decisión."""))

cells.append(code("""import pandas as pd
from crosswalk import load_crosswalk

pd.set_option("display.max_colwidth", None)
cw = load_crosswalk()
print("Disciplinas mapeadas:", len(cw))
print(cw["confianza"].value_counts().to_string())
cw[cw["confianza"] != "alta"][["spu_disciplina", "iscedf_narrow", "confianza", "nota"]]"""))

cells.append(md("""## Paso 4 — Indicadores de desarrollo

Población total (`SP.POP.TOTL`), PIB per cápita en USD corrientes
(`NY.GDP.PCAP.CD`) y en PPA (`NY.GDP.PCAP.PP.CD`) del Banco Mundial, más el
IDH de la serie completa del Human Development Report (PNUD, hasta 2023).
Liechtenstein no tiene PPA en el Banco Mundial y queda NaN."""))

cells.append(code("""ind = pd.read_parquet("data/processed/indicators.parquet")
print(f"{len(ind):,} filas país-año | {ind['iso3'].nunique()} países | "
      f"{ind['year'].min()}-{ind['year'].max()}")
ind[ind["iso3"] == "ARG"].tail()"""))

cells.append(md("""## Gráficos exploratorios

Argentina resaltada en todos. Cada gráfico se guarda además en
`output/graficos/` a **600 dpi** para el informe (los scatters por campo
tardan unos minutos por la calidad de exportación)."""))

cells.append(code("""import matplotlib.pyplot as plt
from report import (PALETA, fig_argentina_evolucion, fig_scatter_total,
                    save_fig, save_field_scatters)

BROAD_LABELS = {
    "F00": "Genéricos", "F01": "Educación", "F02": "Artes y humanidades",
    "F03": "Cs. sociales y periodismo", "F04": "Negocios, adm. y derecho",
    "F05": "Cs. naturales y matemática", "F06": "TIC",
    "F07": "Ingeniería y construcción", "F08": "Agro y veterinaria",
    "F09": "Salud y bienestar", "F10": "Servicios",
}

# --- 01: Composición de egresados de grado (ED6) por campo broad ---
paises = ["ARG", "DEU", "ESP", "FRA", "ITA", "POL", "SWE"]
ed6 = panel[(panel["isced_level"] == "ED6") & panel["iso3"].isin(paises)]
anio = int(ed6.groupby("iso3")["year"].max().min())  # último año con datos en todos

comp = ed6[ed6["year"] == anio].copy()
comp["broad"] = comp["iscedf_narrow"].str[:3]
comp = comp.groupby(["iso3", "broad"])["graduates"].sum().unstack(fill_value=0)
shares = comp.div(comp.sum(axis=1), axis=0) * 100

# Top 7 campos + "Otros" para mantener ≤ 8 categorías
top = shares.mean().nlargest(7).index.tolist()
plot_df = shares[top].rename(columns=BROAD_LABELS)
plot_df["Otros"] = shares.drop(columns=top).sum(axis=1)

fig, ax = plt.subplots(figsize=(10, 4.5))
plot_df.plot(kind="barh", stacked=True, color=PALETA, width=0.65, ax=ax,
             edgecolor="white", linewidth=1.5)
ax.set_title(f"Composición de egresados de grado por campo de estudio, {anio}",
             loc="left", fontsize=12)
ax.set_xlabel("% de egresados (ED6)")
ax.set_ylabel("")
ax.set_xlim(0, 100)
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=False, fontsize=8)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.xaxis.grid(True, color="#e6e6e6", linewidth=0.8)
ax.set_axisbelow(True)
plt.tight_layout()
save_fig(fig, "01_composicion_campos")
plt.show()"""))

cells.append(code("""# --- 02: Egresados cada mil habitantes vs PIB pc (PPA) y vs IDH ---
anio_ref = int(panel[panel["iso3"] == "ARG"]["year"].max())
fig = fig_scatter_total(panel, ind, anio_ref)
save_fig(fig, "02_egresados_vs_desarrollo")
plt.show()"""))

cells.append(code("""# --- 03: Argentina, evolución de cada campo cada mil habitantes ---
fig = fig_argentina_evolucion(panel, ind)
save_fig(fig, "03_argentina_evolucion_campos")
plt.show()"""))

cells.append(code("""# --- 04: Un scatter de desarrollo por cada campo de estudio ---
# Todos se guardan en output/graficos/por_campo/ (600 dpi); acá se
# muestran tres ejemplos (TIC, Ingeniería y Salud).
campos = save_field_scatters(panel, ind, anio_ref,
                             show=("F061", "F071", "F091"))
print(f"{len(campos)} gráficos por campo guardados en output/graficos/por_campo/")"""))

cells.append(code("""# --- 05: Evolución del share de egresados TIC (F061) en el grado (ED6) ---
foco = ["ARG", "DEU", "ESP", "FRA", "ITA"]
ed6_all = panel[panel["isced_level"] == "ED6"]
tot_y = ed6_all.groupby(["iso3", "year"])["graduates"].sum()
ict = (ed6_all[ed6_all["iscedf_narrow"] == "F061"]
       .groupby(["iso3", "year"])["graduates"].sum())
share_ict = (ict / tot_y * 100).rename("share").reset_index()

fig, ax = plt.subplots(figsize=(9, 4.5))
for color, iso in zip(PALETA, foco):
    s = (share_ict[share_ict["iso3"] == iso]
         .dropna(subset=["share"]).sort_values("year"))
    if s.empty:   # sin datos de F061 para ese país: se omite
        continue
    ax.plot(s["year"], s["share"], color=color, lw=2, label=iso)
    ax.annotate(iso, (s["year"].iloc[-1], s["share"].iloc[-1]),
                xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=9, color="#444444")
ax.set_title("Egresados de TIC (F061) como % del total de grado",
             loc="left", fontsize=12)
ax.set_ylabel("%")
ax.set_ylim(bottom=0)
ax.legend(frameon=False, fontsize=8, loc="upper left")
for s_ in ("top", "right"):
    ax.spines[s_].set_visible(False)
ax.yaxis.grid(True, color="#e6e6e6", linewidth=0.8)
ax.set_axisbelow(True)
plt.tight_layout()
save_fig(fig, "05_share_tic")
plt.show()"""))

cells.append(md("""## Resumen de variables (para el informe)

Definición y estadísticos de cada variable del dataset consolidado."""))

cells.append(code("""from report import variable_summary

print(variable_summary(panel, ind))"""))

cells.append(md("""## Export final

Arma `output/` con todos los gráficos (600 dpi) y el Excel completo
(`dataset.xlsx`, que incluye las hojas `diccionario` y `codigos_iscedf`),
lo comprime en un ZIP y —en Colab— lo descarga automáticamente."""))

cells.append(code("""from report import export_zip

zip_path = export_zip()
print("Export listo:", zip_path)
if IN_COLAB:
    from google.colab import files
    files.download(str(zip_path))"""))

cells.append(md("""## Salidas

- `data/processed/dataset.xlsx` — dataset completo: hojas `panel`,
  `indicadores`, `panel_indicadores` (egresados cada mil habitantes),
  `cobertura`, `crosswalk_spu`, `codigos_iscedf` y **`diccionario`**
- `data/processed/*.parquet` y `coverage.csv` — versiones para análisis
- `output/profesiones_pais_export.zip` — gráficos 600 dpi + Excel, listo
  para el informe

**Próximos pasos:** modelar la relación composición de egresados ↔ desarrollo
(los scatters son descriptivos, no causales)."""))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

import pathlib
out = str(pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "00_profesiones_mundo.ipynb")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("OK", out)
