# profesiones_pais

Composición de egresados de educación superior por campo de estudio y su
relación con indicadores de desarrollo, comparando países. La unidad de
clasificación es **ISCED-F 2013 a nivel *narrow*** (códigos `F` + 3 dígitos:
F011 Educación, F061 TIC, F091 Salud, ...).

## Notebooks (ejecutables en Colab)

| Notebook | Qué hace | Abrir |
|---|---|---|
| **`00_profesiones_mundo`** | Panel comparativo ISCED-F entre países (Eurostat + Argentina vía crosswalk), indicadores de desarrollo, gráficos y ranking de orientación humanística vs. científico-técnica por país. Pipeline end-to-end. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/profesiones_pais/blob/main/notebooks/00_profesiones_mundo.ipynb) |
| **`01_profesiones_argentina`** | Egresados de Argentina con las categorías propias de la SPU (tipo de universidad, nivel académico, disciplina), sin pasar por ISCED-F. Export de gráficos 600 dpi + Excel en ZIP. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/profesiones_pais/blob/main/notebooks/01_profesiones_argentina.ipynb) |

El producto central es un panel `iso3 × year × isced_level × iscedf_narrow`
con conteos absolutos de graduados (ED6 grado, ED7 maestría, ED8 doctorado)
desde 2014, acompañado de indicadores de desarrollo por país-año
(población, PIB per cápita en USD y PPA, e IDH) y exportado completo a
`data/processed/dataset.xlsx`.

## Fuentes de datos

| Fuente | Dataset | Rol |
|---|---|---|
| [Eurostat — educ_uoe_grad02](https://ec.europa.eu/eurostat/databrowser/product/view/educ_uoe_grad02) | Graduates by education level, programme orientation, sex and field of education | **Primaria**: conteos absolutos (`unit=NR`) por campo narrow |
| [Eurostat — educ_uoe_grad10](https://ec.europa.eu/eurostat/databrowser/product/view/educ_uoe_grad10) | Distribution of male and female graduates | Complemento opcional: viene solo en `unit=PC` y es la **distribución por sexo dentro de cada campo** (no la composición por campo) |
| [SPU — Síntesis de Información Universitaria](https://www.argentina.gob.ar/educacion/universidades/informacion/publicaciones/sintesis) | Egresados por disciplina (Argentina, 2014-2023) | `data/external/profesiones_arg.xlsx`, se incorpora vía crosswalk SPU → ISCED-F |
| [Banco Mundial — API v2](https://api.worldbank.org/v2/) | `SP.POP.TOTL`, `NY.GDP.PCAP.CD`, `NY.GDP.PCAP.PP.CD` | Población y PIB per cápita (USD corrientes y PPA) por país-año |
| [PNUD — Human Development Report](https://hdr.undp.org/data-center/documentation-and-downloads) | Serie completa de índices compuestos (HDR 2025) | IDH por país-año, hasta 2023 |

El acceso a Eurostat es por la [API SDMX 2.1 de diseminación](https://wikis.ec.europa.eu/display/EUROSTATHELP/API+SDMX+2.1+-+data+query).
La estructura de ambos datasets (orden de dimensiones, unidades, códigos)
está verificada contra la API y documentada en
[`src/eurostat_api.py`](src/eurostat_api.py). Dos detalles no obvios:

- el endpoint de estructura no acepta `references=all` (usar `descendants`);
- el orden de dimensiones **difiere entre los dos datasets** (grad02:
  `freq.unit.isced11.iscedf13.sex.geo`; grad10: `freq.sex.isced11.iscedf13.unit.geo`).

## Estructura

```
profesiones_pais/
├── README.md
├── requirements.txt
├── src/
│   ├── eurostat_api.py       # descarga SDMX + cache en data/raw/
│   ├── crosswalk.py          # mapeo SPU -> ISCED-F narrow (Argentina)
│   ├── spu_data.py           # carga del Excel SPU y mapeo de niveles a ISCED
│   ├── indicators.py         # población, PIB pc (USD/PPA) e IDH por país-año
│   ├── build_panel.py        # consolidación, cobertura y export a Excel
│   ├── report.py             # gráficos 600 dpi, resumen de variables y ZIP
│   └── argentina.py          # análisis nativo SPU (tipo univ., nivel, disciplina)
├── data/
│   ├── raw/                  # descargas crudas con timestamp (gitignored)
│   ├── reference/            # crosswalks versionados (SÍ commiteados)
│   ├── external/             # datos fuente sin API (Excel SPU, commiteado)
│   └── processed/            # panel.parquet + coverage.csv
├── notebooks/
│   ├── 00_profesiones_mundo.ipynb        # panel ISCED-F comparativo (Colab)
│   └── 01_profesiones_argentina.ipynb    # análisis nativo SPU Argentina (Colab)
├── scripts/                  # generadores de los notebooks (no editar .ipynb a mano)
└── tests/
```

## Cómo correr local

```bash
git clone https://github.com/santiagoriverti/profesiones_pais.git
cd profesiones_pais
pip install -r requirements.txt

python src/build_panel.py     # descarga (cacheada), consolida y reporta cobertura
python -m pytest tests/ -q    # tests (sin red)
```

Salidas en `data/processed/`:

- `panel.parquet` — esquema `iso3, year, isced_level, iscedf_narrow, graduates, source`
- `indicators.parquet` — `iso3, year, population, gdp_pc_usd, gdp_pc_ppp, hdi`
- `coverage.csv` — qué países tienen datos a nivel narrow y cuáles solo broad
- **`dataset.xlsx`** — todo el dataset procesado en un solo Excel, con hojas
  `panel`, `indicadores`, `panel_indicadores` (incluye egresados cada mil
  habitantes), `cobertura`, `crosswalk_spu`, `codigos_iscedf` (etiquetas
  ES/EN de cada campo) y `diccionario` (definición y fuente de cada variable)

El notebook además genera `output/` (gitignoreado, vía `src/report.py`):
todos los gráficos a **600 dpi** — incluyendo la evolución de cada campo en
Argentina cada mil habitantes y un scatter de desarrollo por cada campo de
estudio en `graficos/por_campo/` —, una copia del Excel, y el ZIP
`profesiones_pais_export.zip` (en Colab se descarga solo). También imprime
un resumen de todas las variables listo para pegar en un informe.

**Argentina** entra automáticamente: `build_panel.py` lee
`data/external/profesiones_arg.xlsx` (egresados SPU 2014-2023), mapea los
niveles (Grado → ED6; Maestría y Especialidad → ED7; Doctorado → ED8) y
aplica el crosswalk. Pregrado (ISCED 5) y "Posgrado/Otros" quedan fuera
del panel y se reportan en el log.

## Limitaciones conocidas

- **Cobertura geográfica**: Eurostat solo cubre países que reportan a la
  recolección UOE (UE + EFTA + candidatos + Reino Unido). En la última
  corrida: 38 países con datos a nivel narrow; Georgia reporta solo a nivel
  broad y queda fuera de la muestra narrow. Países de América Latina, Asia o
  África requieren otras fuentes (p. ej. UNESCO UIS) y no están integrados.
- **Crosswalk SPU → ISCED-F**: varias disciplinas SPU no tienen contraparte
  limpia a nivel narrow. Tras la revisión del 2026-07-24 quedan dos casos con
  `confianza=baja` en
  [`data/reference/spu_to_iscedf_narrow.csv`](data/reference/spu_to_iscedf_narrow.csv)
  — "Industrias" y "Sanidad" —, que requieren cotejo con el nomenclador de
  carreras de la SPU (cada duda está documentada en la columna `nota`; ver
  [`docs/decisiones.md`](docs/decisiones.md)). Además hay agregados que ISCED
  parte en dos campos (p. ej. "Economía y Administración" mezcla F031 y F041;
  "Sociología, Antropología y Servicio Social" mezcla F031 y F092).
- **Argentina — niveles ISCED**: las especializaciones de posgrado se mapean
  a ED7 junto con las maestrías (criterio del mapeo UNESCO para Argentina);
  si se prefiere una definición estricta de maestría, usar
  `load_spu_egresados(include_especialidad=False)`. La serie argentina
  cubre 2014-2023 (Eurostat llega a 2024) y "Posgrado/Otros" (~10,7 mil
  egresados acumulados) no puede asignarse a nivel y queda excluido.
- **Indicadores**: el IDH del HDR 2025 llega hasta 2023 (los años
  posteriores del panel quedan NaN); Liechtenstein no tiene PIB PPA en el
  Banco Mundial y Kosovo no tiene IDH. Los scatters egresados/desarrollo
  son descriptivos, no causales.
- **Comparabilidad**: los totales nacionales pueden diferir de publicaciones
  locales por diferencias de cobertura institucional y de año académico
  vs. calendario. Las series con flag de ruptura o estimación conservan el
  flag de Eurostat en la descarga cruda.
