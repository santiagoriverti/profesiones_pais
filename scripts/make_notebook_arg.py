# -*- coding: utf-8 -*-
"""Genera notebooks/01_profesiones_argentina.ipynb.

El notebook NO se edita a mano: modificar este script, correrlo y validar la
ejecucion end-to-end (nbclient) antes de commitear. Analiza las categorias
propias de la SPU (tipo de universidad, nivel academico, disciplina) desde
data/external/profesiones_arg.xlsx via src/argentina.py.
"""
import json
import pathlib


def md(source):
    return {"cell_type": "markdown", "metadata": {},
            "source": source.splitlines(keepends=True)}


def code(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": source.splitlines(keepends=True)}


cells = []

cells.append(md("""# Profesiones en Argentina — egresados universitarios (SPU)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/profesiones_pais/blob/main/notebooks/01_profesiones_argentina.ipynb)

Análisis de los egresados universitarios de Argentina con las **categorías
propias de la SPU** (Síntesis de Información Universitaria), sin pasar por
ISCED-F: tipo de universidad, nivel académico y disciplina específica.

Fuente: `data/external/profesiones_arg.xlsx`. Reglas fijas del análisis:
- Solo **EGRESADOS** (salvo el proxy egreso/estudiantes del final).
- Se **excluye siempre Pregrado** (ISCED 5) de todos los análisis y gráficos.
- El período se toma del propio archivo (**2014-2023** hoy; se extiende solo
  si el Excel se actualiza con años nuevos).

Al final se descargan todos los gráficos a **600 dpi** y un Excel con el
detalle, comprimidos en un ZIP."""))

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
# Purga módulos del proyecto ya importados (por si el kernel tenía versión vieja)
for _m in ("indicators", "spu_data", "argentina"):
    sys.modules.pop(_m, None)

import matplotlib.pyplot as plt
from IPython.display import display
import argentina as a
print("Directorio de trabajo:", os.getcwd())"""))

cells.append(md("""## Datos

`load_arg_raw()` lee el Excel de la SPU; `egresados()` filtra EGRESADOS y
excluye Pregrado. La población de Argentina (para egresados cada mil
habitantes) viene del Banco Mundial (`SP.POP.TOTL`)."""))

cells.append(code("""df = a.load_arg_raw()
eg = a.egresados(df)
y0, y1 = a.periodo(df)
pop = a.poblacion_arg(y0, y1)
print(f"Período: {y0}-{y1} | egresados (excl. Pregrado): {int(eg['VALOR'].sum()):,}")
df.head()"""))

cells.append(md("""## 1. Tipo de universidad (Privado / Pública)

Tabla de detalle (egresados, índice base 100 y participación por año),
evolución base 100 y composición del último año."""))

cells.append(code("""t_tipo = a.tabla_tipo_univ(eg)
display(t_tipo)
a.fig_tipo_univ_base100(t_tipo); plt.show()
a.fig_tipo_univ_torta(t_tipo); plt.show()"""))

cells.append(md("""## 2. Nivel académico (Grado / Posgrado)

Pregrado queda excluido. Tabla de detalle, evolución base 100, torta del
último año y —además— egresados de **Grado cada mil habitantes**."""))

cells.append(code("""t_nivel = a.tabla_nivel_academ(eg)
display(t_nivel)
a.fig_nivel_base100(t_nivel); plt.show()
a.fig_nivel_torta(t_nivel); plt.show()

t_grado_mil = a.tabla_grado_por_mil(eg, pop)
display(t_grado_mil)
a.fig_grado_por_mil(t_grado_mil); plt.show()"""))

cells.append(md("""## 3. Disciplina específica (DISCIP_ESPECIF)

Tabla de detalle sobre **todas** las disciplinas (egresados, participación y
ranking por año) más la matriz disciplina × año. Gráficos: top 10 por año y
comparativo del top 10 del primer vs. último año. Finalmente, la evolución de
la relación **egresados de Psicología por cada egresado de Ingeniería**
(por año y global de todo el período)."""))

cells.append(code("""t_disc = a.tabla_disciplinas(eg)
print(f"{t_disc['disciplina'].nunique()} disciplinas | detalle (primeras filas):")
display(t_disc.head(12))
display(a.matriz_disciplinas(eg))"""))

cells.append(code("""a.fig_top10_por_anio(t_disc); plt.show()
a.fig_top10_comparativo(t_disc); plt.show()"""))

cells.append(code("""t_ratio = a.tabla_ratio_psico_ing(eg)
display(t_ratio)
a.fig_ratio_psico_ing(t_ratio); plt.show()"""))

cells.append(md("""## 4. Nota sobre EGRESADOS vs. ESTUDIANTES

Todo lo anterior usa `TIPO_ALUMNO == "EGRESADOS"`. La columna también trae
`ESTUDIANTES` (matriculados), que se usa solo en el punto siguiente.

## 5. ¿Tasa de deserción?

**No es técnicamente coherente calcular una tasa de deserción con estos
datos.** La deserción requiere seguir **cohortes** (ingresantes de un año y
cuántos de ellos egresan o abandonan años después). El archivo trae un
**stock** anual de estudiantes (matriculados) y un **flujo** anual de
egresados, sin ingresantes por cohorte: cualquier "tasa de deserción" que se
construyera con esto sería un artefacto.

Lo que sí es coherente es reportar la **relación egresados/estudiantes**
(egresados cada 100 estudiantes) como **proxy de intensidad de egreso** —
no de deserción—, dejando explícita la limitación."""))

cells.append(code("""t_proxy = a.tabla_egre_vs_estu(df)
display(t_proxy)
a.fig_egre_vs_estu(t_proxy); plt.show()"""))

cells.append(md("""## Export final

`exportar_todo()` regenera los 9 gráficos a **600 dpi**, arma el Excel
`analisis_argentina.xlsx` con todas las tablas de detalle (una hoja por
análisis + `notas`) y lo comprime en
`output/argentina/profesiones_argentina_export.zip`. En Colab se descarga
automáticamente."""))

cells.append(code("""zip_path = a.exportar_todo()
print("Export listo:", zip_path)
if IN_COLAB:
    from google.colab import files
    files.download(str(zip_path))"""))

cells.append(md("""## Salidas

- `output/argentina/analisis_argentina.xlsx` — hojas: `notas`, `tipo_univ`,
  `nivel_academ`, `grado_por_mil`, `disciplinas`, `matriz_disciplinas`,
  `ratio_psico_ing`, `egre_vs_estu`.
- `output/argentina/graficos/*.png` — 9 gráficos a 600 dpi.
- `output/argentina/profesiones_argentina_export.zip` — todo lo anterior."""))

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

out = str(pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "01_profesiones_argentina.ipynb")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("OK", out)
