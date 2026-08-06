# Estado del proyecto y guía para retomar

> Punto de entrada único para continuar el trabajo. Complementa
> [CLAUDE.md](../CLAUDE.md) (arquitectura y gotchas),
> [docs/metodologia.md](metodologia.md) (metodología de ambos notebooks),
> [docs/decisiones.md](decisiones.md) (registro fechado de decisiones) y
> [docs/fuentes_datos.md](fuentes_datos.md) (estructura verificada de cada
> fuente). Última actualización: **2026-08-06**.

## Qué es

Panel comparativo de egresados de educación superior por campo de estudio
(ISCED-F 2013 nivel *narrow*, `F` + 3 dígitos) e indicadores de desarrollo,
2014 en adelante. Europa vía Eurostat (SDMX 2.1) + Argentina vía SPU.

Dos entregables, cada uno con su notebook Colab:
- **`00_profesiones_mundo`** — panel ISCED-F comparativo entre países
  (`src/build_panel.py`, `src/report.py`); incluye ranking de orientación
  humanística (F02+F03) vs. científico-técnica (F05+F06+F07) por país.
- **`01_profesiones_argentina`** — análisis nativo de la SPU sin ISCED-F
  (tipo de universidad, nivel académico, disciplina), vía `src/argentina.py`.

## Estado actual — checkpoint estable

- **Panel**: 64.650 filas · 39 países (38 Eurostat narrow + ARG) · 2014-2024
  · niveles ED6/ED7/ED8 · 57 campos ISCED-F.
- **Argentina**: 600 filas · 2014-2023 · 21 campos · 1.093.255 egresados
  acumulados (vía crosswalk SPU→ISCED-F).
- **Tests**: 34 pasan (sin red). Auditoría de coherencia superada.
- **Argentina (SPU nativo)**: `src/argentina.py` + notebook
  `01_profesiones_argentina` — tipo de universidad, nivel académico,
  disciplina, ratio Psicología/Ingeniería y proxy de intensidad de egreso.
- **Git**: `main`, sincronizado con `origin/main`.

### Cambios 2026-08-06 (pedido del usuario)

- **Notebook 00 — `dataset.xlsx`**: dos hojas nuevas que documentan qué
  carreras entran al ratio del gráfico `06_ranking_orientacion`, con columnas
  `hum_soc` (numerador, F02+F03) y `cien_tec_ing` (denominador, F05+F06+F07):
  `clas_eur` (57 campos ISCED-F, base Europa) y `clas_arg` (38 disciplinas
  SPU, base Argentina). Generadas por `build_panel.clasificacion_orientacion_eur()`
  y `..._arg()`.
- **Notebook 01 — gráficos** (`src/argentina.py`):
  - `01_tipo_univ_nivel` (ex `01_tipo_univ_base100`): niveles absolutos, no
    base 100; **barras verticales agrupadas** (Privado y Pública en el mismo
    eje). **Renombrado** el archivo.
  - `02_tipo_univ_torta`: color fijo **azul = Privado, naranja = Pública**
    (coincide con el gráfico 01).
  - `03_nivel_academ_nivel` (ex `03_nivel_base100`): niveles absolutos,
    **barras verticales agrupadas** (Grado y Posgrado en el **mismo eje**).
    **Renombrado** el archivo.
  - `07_disciplinas_top10_comparativo`: suma del **trienio 2014-2016** vs.
    suma del **trienio 2021-2023** (antes 2014 vs 2023).

## Cómo correr

```bash
# MUNDO: regenerar todo el dataset (usa cache en data/raw; NO re-descarga)
python src/build_panel.py

# ARGENTINA: análisis nativo SPU → output/argentina/ (gráficos 600 dpi + Excel + ZIP)
python src/argentina.py

# Forzar re-descarga desde las APIs (Eurostat/BM/PNUD)
python -c "import sys; sys.path.insert(0,'src'); from build_panel import main; main(force=True)"

# Tests (sin red)
python -m pytest tests/ -q

# Gráficos del informe + ZIP: se generan corriendo el notebook de Colab
# (notebooks/00_profesiones_mundo.ipynb), que llama a las funciones de
# src/report.py. output/ está gitignoreado (~48 MB regenerables).

# Regenerar los notebooks de Colab (no editar los .ipynb a mano)
python scripts/make_notebook.py       # 00_profesiones_mundo
python scripts/make_notebook_arg.py   # 01_profesiones_argentina
```

> En Windows, si un script imprime caracteres no-ASCII (`→`, `—`), correr
> con `python -X utf8` (consola cp1252). Ver gotchas en CLAUDE.md.

## Esquema de datos (`data/processed/`)

| Archivo | Contenido |
|---|---|
| `panel.parquet` | iso3, year, isced_level, iscedf_narrow, graduates, source |
| `indicators.parquet` | iso3, year, population, gdp_pc_usd, gdp_pc_ppp, hdi |
| `coverage.csv` | cobertura narrow vs broad por país (Eurostat) |
| `dataset.xlsx` | 9 hojas: panel, indicadores, panel_indicadores (grad_per_1000), cobertura, crosswalk_spu, codigos_iscedf, diccionario, clas_arg, clas_eur |

`source` ∈ {`eurostat_educ_uoe_grad02`, `spu_crosswalk`}. `data/processed/`
está **versionado a propósito** (outputs usables sin correr el pipeline);
`data/raw/` es cache gitignoreado.

## Reglas de calidad de datos (no re-descubrir)

- **Egresados negativos → 0**: Eurostat trae artefactos <0 en códigos
  "not further defined"; `build_eurostat_panel` los fuerza a 0. Guard en
  `tests/test_data_integrity.py`.
- **Códigos "not further defined" (F0x0, 9 códigos, ~0,6%, ARG=0%)**:
  marcados `tipo=no_definido` en `data/reference/iscedf_narrow_labels.csv`;
  se excluyen de gráficos/rankings por campo vía `report.disciplina_codes()`
  pero cuentan en totales país. **No confundir** con `F0x9` ("not elsewhere
  classified"), que sí son disciplinas (los usa el crosswalk de ARG).
- **Asimetría de ceros Europa/ARG**: Eurostat da 0 explícito para celdas
  sin egresados (~54% de sus filas); ARG solo tiene filas con dato. Fijar
  criterio explícito en promedios/shares por campo (p. ej. solo países con
  cobertura narrow completa).

## Gaps conocidos (legítimos, no errores)

| Gap | Detalle |
|---|---|
| Georgia (GEO) | Solo reporta nivel broad → fuera de la muestra narrow |
| `gdp_pc_ppp` LIE | El Banco Mundial no publica PPA para Liechtenstein (sí PIB pc USD) |
| `hdi` 2024 | El HDR del PNUD llega a 2023 |
| ARG sin 2024 | La serie SPU llega a 2023; Eurostat a 2024 |
| XKX sin IDH | Kosovo no tiene serie del PNUD |

## Pendientes (priorizados)

1. **Cotejar `Industrias` y `Sanidad` con el nomenclador de carreras de la
   SPU** — los 2 mapeos que quedan `confianza=baja` en el crosswalk
   (`data/reference/spu_to_iscedf_narrow.csv`). Volumen: Industrias 3,4%,
   Sanidad 0,2% de egresados ARG. Ver docs/decisiones.md (2026-07-24).
2. **Modelado egresados ↔ desarrollo** — hoy los scatters
   (`report._scatter_desarrollo`) son solo descriptivos; falta análisis
   cuantitativo (correlación/regresión share por campo vs PIB pc / IDH).
3. **Revisar mapeos `confianza=media`** con apertura por carrera si se
   consigue (Economía y Administración, Bioquímica y Farmacia, etc.).

## Mapa de archivos

| Archivo | Rol |
|---|---|
| `src/eurostat_api.py` | Descarga SDMX 2.1 con cache timestampeado |
| `src/spu_data.py` | Lee el Excel SPU y mapea niveles SPU→ISCED |
| `src/crosswalk.py` | Aplica `spu_to_iscedf_narrow.csv` (38 disciplinas) |
| `src/indicators.py` | Población y PIB pc (BM) + IDH (PNUD) |
| `src/build_panel.py` | **Entry point mundo**: consolida y exporta el dataset |
| `src/report.py` | Gráficos 600 dpi (mundo), resumen de variables, ZIP |
| `src/argentina.py` | **Entry point Argentina**: análisis nativo SPU → `output/argentina/` |
| `scripts/make_notebook.py` | Genera `00_profesiones_mundo.ipynb` (no editar el .ipynb) |
| `scripts/make_notebook_arg.py` | Genera `01_profesiones_argentina.ipynb` (no editar el .ipynb) |
