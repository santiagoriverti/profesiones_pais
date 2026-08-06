# profesiones_pais — contexto del proyecto

Panel comparativo de egresados de educación superior por campo de estudio
(ISCED-F 2013 nivel *narrow*, códigos `F` + 3 dígitos) e indicadores de
desarrollo, 2014 en adelante. Europa vía Eurostat + Argentina vía SPU.

**Para retomar**: [docs/estado.md](docs/estado.md) (estado, cómo correr,
esquema de datos, pendientes y gaps — punto de entrada único).
**Memoria detallada**: [docs/fuentes_datos.md](docs/fuentes_datos.md)
(estructura verificada de cada fuente) y
[docs/decisiones.md](docs/decisiones.md) (registro de decisiones).

## Arquitectura

| Archivo | Rol |
|---|---|
| `src/eurostat_api.py` | Descarga SDMX 2.1 con cache timestampeado en `data/raw/` |
| `src/spu_data.py` | Lee `data/external/profesiones_arg.xlsx` y mapea niveles SPU → ISCED |
| `src/crosswalk.py` | Aplica `data/reference/spu_to_iscedf_narrow.csv` (38 disciplinas) |
| `src/indicators.py` | Población y PIB pc (Banco Mundial) + IDH (PNUD HDR) |
| `src/build_panel.py` | **Entry point** (mundo): consolida todo y exporta `data/processed/dataset.xlsx` (9 hojas, incluye `diccionario`, `codigos_iscedf` y `clas_arg`/`clas_eur` con la clasificación del ratio de orientación) |
| `src/report.py` | Gráficos del informe (600 dpi → `output/`, gitignoreado), resumen de variables y ZIP exportable |
| `src/argentina.py` | **Entry point** (Argentina): análisis nativo SPU (tipo univ., nivel, disciplina, ratio psico/ing, proxy egreso) → `output/argentina/` (600 dpi + Excel + ZIP) |

Correr mundo: `python src/build_panel.py` (usa cache; no re-descarga).
Correr Argentina: `python src/argentina.py` (baja población del BM, cacheada).
Tests: `python -m pytest tests/ -q` (sin red). **Dos notebooks Colab** — NO
editarlos a mano, se regeneran con sus scripts y se validan con nbclient:
`notebooks/00_profesiones_mundo.ipynb` (← `scripts/make_notebook.py`) y
`notebooks/01_profesiones_argentina.ipynb` (← `scripts/make_notebook_arg.py`).

## Gotchas críticos (no re-descubrir)

- `educ_uoe_grad10` viene SOLO en `unit=PC` y es la **distribución por sexo
  dentro de cada campo** (rechaza `sex=T`). NO sirve para composición por
  campo. La fuente primaria es `educ_uoe_grad02` (`unit=NR`, absolutos).
- El **orden de dimensiones difiere** entre datasets de Eurostat
  (grad02: `freq.unit.isced11.iscedf13.sex.geo`;
  grad10: `freq.sex.isced11.iscedf13.unit.geo`).
- El endpoint de estructura exige `references=descendants` (no acepta `all`).
- Consolas Windows (cp1252): no imprimir `→` ni caracteres no-ASCII en
  scripts; usar `python -X utf8` si hace falta.
- El notebook en Colab sincroniza el clon con `git fetch` + `reset --hard
  origin/main` (un `pull` falla porque las corridas modifican
  `data/processed/`, que está trackeado) y purga los módulos del proyecto
  de `sys.modules` (runtimes reutilizados cachean código viejo).
- `data/processed/` está trackeado a propósito (outputs versionados);
  `data/raw/` es cache gitignoreado.
- Eurostat trae valores <0 en códigos "not further defined" (F0x0);
  `build_eurostat_panel` los fuerza a 0. No quitar el guard.
- Códigos `F0x0` ("not further defined", 9 códigos, ~0,6%, ARG=0%) están
  marcados `tipo=no_definido` en `iscedf_narrow_labels.csv` y se excluyen
  de los gráficos por campo vía `report.disciplina_codes()` (pero cuentan
  en los totales país). Distintos de los `F0x9` ("not elsewhere
  classified"), que sí son disciplinas (los usa el crosswalk de ARG).
- Asimetría de ceros: Eurostat da 0 explícito para celdas sin egresados
  (~54%); ARG solo tiene filas con dato (ausencia ≠ 0). Fijar criterio
  explícito en promedios/shares por campo.
- `src/argentina.py` (análisis nativo SPU): SIEMPRE excluye Pregrado y usa
  solo EGRESADOS (salvo el proxy egreso/estudiantes). El período se toma del
  archivo (`periodo(df)`), no se hardcodea 2014-2023. No se calcula "tasa de
  deserción" (no hay ingresantes por cohorte): solo el proxy egresados/
  estudiantes, explícitamente NO deserción. `VALOR` ya es entero en el xlsx.
- Los gráficos de ambos notebooks van **sin título principal** a propósito
  (el contexto va en el markdown del notebook); no re-agregarlos.
- Ranking de orientación (NB00, `report.tabla_ratio_orientacion`): razón
  broad humanidades+cs sociales (F02+F03, incluye Psicología, que narrow no
  aísla) / ciencias duras+tec (F05+F06+F07). Distinto del ratio exacto
  Psicología/Ingeniería del NB01 (disciplinas SPU). La composición del ratio
  está documentada en dos hojas del Excel (`build_panel.clasificacion_orientacion_arg`
  / `_eur`): `clas_arg` (38 disciplinas SPU) y `clas_eur` (57 campos ISCED-F),
  con columnas `hum_soc`/`cien_tec_ing` marcadas por el prefijo broad. Ojo:
  los residuales F0x0 cuentan por su prefijo (igual que el ratio), aunque
  sean `tipo=no_definido`.
- NB01 (`src/argentina.py`): los gráficos 01 y 03 son **niveles absolutos**,
  NO base 100 (la columna `base100` sigue en las tablas del Excel). `01_tipo_univ_nivel`
  (Privado/Pública, mismo eje) y `03_nivel_academ_nivel` (Grado/Posgrado, doble
  eje por escala ~5×) fueron **renombrados** (antes `*_base100`). Colores fijos
  `COLOR_TIPO`/`COLOR_NIVEL` (azul/naranja) para que líneas y tortas coincidan.
  `07_disciplinas_top10_comparativo` compara **suma de trienios** (primeros 3
  años vs últimos 3: 2014-2016 vs 2021-2023), no primer vs último año.

## Estado y pendientes

- Panel: 64.650 filas, 39 países (38 Eurostat narrow + ARG), 2014-2024.
  Georgia solo reporta nivel broad (fuera de la muestra narrow).
- Crosswalk revisado 2026-07-24: quedan 2 casos `confianza=baja`
  (Industrias, Sanidad) que requieren el nomenclador de carreras de la
  SPU; el resto pasó a `media` (ver docs/decisiones.md).
- Pendiente: cotejar Industrias/Sanidad con el nomenclador SPU; modelado
  egresados ↔ desarrollo (los scatters son descriptivos).

## Reglas del repo

- Commits sin atribución de Claude, solo usuario Santiago Riverti.
- No hardcodear tokens/credenciales; auth de GitHub vía Git Credential
  Manager o `gh auth login`.
