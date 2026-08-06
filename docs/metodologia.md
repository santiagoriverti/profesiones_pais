# Metodología

Detalle de la metodología empleada en los dos notebooks del proyecto:
`00_profesiones_mundo` (panel comparativo entre países) y
`01_profesiones_argentina` (análisis nativo de la SPU). Para las fuentes y
su forma de citar, ver [fuentes_datos.md](fuentes_datos.md); para el registro
fechado de decisiones, [decisiones.md](decisiones.md).

Última actualización: 2026-08-06.

---

## Notebook 00 — `profesiones_mundo`

### Objetivo

Construir un panel comparativo de egresados de educación superior por **campo
de estudio** entre países y relacionarlo con indicadores de desarrollo. La
unidad de clasificación es **ISCED-F 2013 a nivel *narrow*** (códigos `F` + 3
dígitos; p. ej. F011 Educación, F061 TIC, F091 Salud), que permite comparar
Europa (vía Eurostat) con Argentina (vía un crosswalk desde las disciplinas de
la SPU).

### Fuentes

| Dato | Fuente | Detalle |
|---|---|---|
| Egresados por campo (Europa) | Eurostat `educ_uoe_grad02` | Conteos absolutos (`unit=NR`), sexo total, niveles ED6/ED7/ED8 |
| Egresados por disciplina (Argentina) | SPU, Síntesis de Información Universitaria | Se llevan a ISCED-F con un crosswalk propio |
| Población y PIB per cápita | Banco Mundial (API v2) | `SP.POP.TOTL`, `NY.GDP.PCAP.CD`, `NY.GDP.PCAP.PP.CD` |
| Índice de Desarrollo Humano | PNUD, Human Development Report 2025 | Serie 1990-2023 |

### Unidad de análisis y niveles

- **Campo de estudio**: ISCED-F 2013 *narrow* (57 códigos `F###`). Los países
  que solo reportan a nivel *broad* (Georgia) quedan fuera de la muestra
  narrow; la cobertura por país se documenta en `coverage.csv`.
- **Nivel educativo**: ISCED 2011 **ED6** (grado/licenciatura), **ED7**
  (maestría o equivalente) y **ED8** (doctorado). Se excluye ISCED 5
  (pregrado/ciclo corto).
- **Período**: 2014 en adelante (Eurostat llega a 2024; Argentina e IDH a 2023).

### Construcción del panel (pipeline `src/build_panel.py`)

1. **Descarga Eurostat** (`src/eurostat_api.py`) por la API SDMX 2.1 de
   diseminación, con cache timestampeado en `data/raw/` (las corridas
   siguientes no re-descargan). El dataset `educ_uoe_grad02` se pide en
   `unit=NR`, sexo total y desde 2014.
2. **Filtrado a nivel narrow** y conversión de códigos geográficos de Eurostat
   (ISO2 con dos excepciones históricas: `EL`=Grecia, `UK`=Reino Unido) a
   ISO-3166 alpha-3. Los agregados (`EU27_2020`, `EA19`, …) se descartan.
3. **Cobertura por país** (`coverage.csv`): se cuenta, por país, cuántas celdas
   campo-nivel-año tienen dato a nivel narrow vs. solo broad. La muestra final
   son los países con cobertura narrow.
4. **Integración de Argentina**: los egresados de la SPU
   (`data/external/profesiones_arg.xlsx`) se mapean a ISCED-F con el crosswalk
   `data/reference/spu_to_iscedf_narrow.csv` y se agregan con
   `source = "spu_crosswalk"`.
5. **Indicadores de desarrollo** (`src/indicators.py`): población y PIB per
   cápita del Banco Mundial e IDH del PNUD, unidos por país-año.
6. **Exportación** a `data/processed/`: `panel.parquet`, `indicators.parquet`,
   `coverage.csv` y `dataset.xlsx` (9 hojas: panel, indicadores,
   panel_indicadores con egresados cada mil habitantes, cobertura,
   crosswalk_spu, codigos_iscedf, diccionario y las dos hojas de
   clasificación del ratio de orientación —`clas_arg` y `clas_eur`, ver
   la sección del ranking).

### Crosswalk SPU → ISCED-F (Argentina)

Argentina no reporta a Eurostat, así que sus egresados vienen por las 37
disciplinas de la SPU. El crosswalk (elaboración propia, versionado y pensado
para revisión manual) asigna cada disciplina a un campo ISCED-F narrow, con una
etiqueta de **confianza** (`alta`/`media`/`baja`) y una nota que documenta cada
decisión dudosa. Mapeo de niveles: Grado → ED6; Maestría y Especialidad → ED7;
Doctorado → ED8. Tras la revisión del 2026-07-24 quedan dos casos `baja`
(Industrias, Sanidad) que requieren cotejo con el nomenclador de carreras de la
SPU (ver [decisiones.md](decisiones.md)).

### Reglas de calidad del dato

- **Egresados negativos → 0**: Eurostat trae ocasionalmente valores `< 0` en los
  códigos "not further defined" (residuales que calcula por diferencia); un
  conteo no puede ser negativo, así que se fuerzan a 0.
- **Códigos "not further defined" (F0x0)**: 9 códigos de "subcampo desconocido"
  (~0,6% del total; Argentina no los usa). Se **conservan en los totales país**
  pero se **excluyen de los gráficos y rankings por campo** (marca `tipo` en
  `iscedf_narrow_labels.csv`, filtro `report.disciplina_codes()`), porque
  distorsionan la comparación. No confundir con los `F0x9` ("not elsewhere
  classified"), que sí son disciplinas.
- **Asimetría de ceros Europa/Argentina**: Eurostat reporta 0 explícito para
  celdas sin egresados (~54% de sus filas); Argentina, vía crosswalk, solo tiene
  filas con dato (ausencia ≠ 0). Todo promedio o *share* por campo debe fijar un
  criterio explícito para no sesgar la comparación.

### Indicadores y métricas derivadas

- **Egresados cada mil habitantes**: `graduates / population × 1000`.
- Los cruces egresados ↔ desarrollo (PIB per cápita PPA e IDH) son
  **descriptivos, no causales**.

### Gráficos

1. **Composición por campo** (`01_composicion_campos`): para un conjunto de
   países, participación de cada campo *broad* en los egresados de grado (ED6),
   como barras apiladas al 100%.
2. **Egresados vs. desarrollo** (`02_egresados_vs_desarrollo`): dispersión de
   egresados universitarios cada mil habitantes contra PIB per cápita PPA (eje
   log) e IDH; Argentina resaltada y etiquetas de países extremos e intermedios.
3. **Evolución por campo en Argentina** (`03_argentina_evolucion_campos`):
   *small multiples* de cada campo cada mil habitantes.
4. **Un scatter de desarrollo por campo** (`graficos/por_campo/`): un gráfico
   por campo narrow con datos en ≥ 8 países.
5. **Share de TIC** (`05_share_tic`): egresados de TIC (F061) como % del grado.
6. **Ranking de orientación** (`06_ranking_orientacion`): ver abajo.

### Ranking de orientación humanística vs. científico-técnica

ISCED-F *narrow* no aísla Psicología (cae en F031, ciencias sociales), así que a
nivel comparativo entre países se usa una razón entre campos **broad**:

```
ratio =  egresados en humanidades y ciencias sociales (F02 + F03)
         ────────────────────────────────────────────────────────
         egresados en ciencias, tecnología e ingeniería (F05 + F06 + F07)
```

- **Numerador** — orientación humanística/social: F02 (Artes y humanidades) +
  F03 (Ciencias sociales, periodismo e información; **incluye Psicología**).
- **Denominador** — orientación científico-técnica ("duras"): F05 (Ciencias
  naturales, matemática y estadística) + F06 (TIC) + F07 (Ingeniería,
  manufactura y construcción).
- Se calcula sobre el total ED6-ED8 del año de referencia. Ratio **> 1** =
  predominio humanístico/social; **< 1** = predominio científico-técnico. Se
  presenta como tabla de ranking y gráfico de barras, con Argentina resaltada y
  la paridad (1) marcada.
- El ratio **exacto** Psicología/Ingeniería a nivel disciplina existe en el
  notebook 01 (datos SPU, que sí las separan).

**Hojas `clas_arg` y `clas_eur` (qué carreras entran al ratio).** El
`dataset.xlsx` documenta la composición del ratio en dos hojas, una por base,
con columnas `hum_soc` (marca `x` = numerador, F02 + F03) y `cien_tec_ing`
(marca `x` = denominador, F05 + F06 + F07):

- **`clas_eur`**: los 57 campos ISCED-F *narrow* (base Europa/Eurostat),
  marcados por su código *broad*. Los residuales F0x0 ("not further defined")
  también cuentan por su prefijo, igual que en `tabla_ratio_orientacion`.
- **`clas_arg`**: las 38 disciplinas de la SPU (base Argentina), clasificadas
  por el campo ISCED-F al que las lleva el crosswalk (13 al numerador, 12 al
  denominador). Las que no llevan marca no intervienen en el ratio: educación
  (F011), negocios/derecho (F04), salud (F09), agro y veterinaria (F08) y
  servicios (F10).

### Limitaciones

- Eurostat solo cubre países que reportan a la recolección UOE (UE + EFTA +
  candidatos + Reino Unido); América Latina, Asia y África requieren otras
  fuentes.
- El crosswalk SPU → ISCED-F tiene disciplinas sin contraparte limpia (dos casos
  `baja`) y agregados que ISCED parte en dos campos.
- El IDH llega hasta 2023; Liechtenstein no tiene PIB PPA; Kosovo no tiene IDH.

---

## Notebook 01 — `profesiones_argentina`

### Objetivo

Analizar los egresados universitarios de Argentina con las **categorías propias
de la SPU** (sin pasar por ISCED-F): tipo de universidad, nivel académico y
disciplina específica. La lógica vive en `src/argentina.py`.

### Fuente y alcance

- **Fuente**: `data/external/profesiones_arg.xlsx` (Síntesis de Información
  Universitaria, SPU). Columnas: `ANIO, TIPO_UNIV (Privado/Pública),
  NIVEL_ACADEM (Pregrado/Grado/Posgrado), OF_ACADEM, DISCIP_OCDE, DISCIP_ESPECIF
  (37 disciplinas), TIPO_ALUMNO (EGRESADOS/ESTUDIANTES), U_MED, VALOR`. `VALOR`
  ya viene como cantidad entera de personas.
- **Población** (para egresados cada mil habitantes): Banco Mundial
  `SP.POP.TOTL`.

### Reglas fijas del análisis

- Se usa **solo `TIPO_ALUMNO = EGRESADOS`** (salvo el proxy de egreso del punto
  5, que también usa ESTUDIANTES).
- Se **excluye siempre `NIVEL_ACADEM = Pregrado`** (ISCED 5) de todos los
  análisis y gráficos.
- El **período se toma del propio archivo** (`ANIO`): hoy 2014-2023, pero se
  extiende automáticamente si el Excel se actualiza con años nuevos. Ningún año
  está hardcodeado; el comparativo de disciplinas usa primer vs. último año
  disponibles.

Nota: este análisis incluye la categoría "Posgrado/Otros" (que el crosswalk a
ISCED sí excluye por no poder asignarle nivel), por eso el total nativo de
egresados (≈ 1,10 millón) supera al del panel ISCED (≈ 1,09 millón).

### Métricas y fórmulas

- **Índice base 100**: por categoría, `valor_año / valor_primer_año × 100` (el
  primer año de la serie = 100).
- **Participación**: `valor_categoría_año / total_del_año × 100`.
- **Egresados de Grado cada mil habitantes**: `egresados_grado_año /
  población_año × 1000`.
- **Ratio Psicología/Ingeniería**: `egresados_Psicología / egresados_Ingeniería`,
  por año y **global** (acumulado de todo el período).
- **Proxy de intensidad de egreso**: `egresados / estudiantes × 100` (egresados
  cada 100 estudiantes).

### Análisis y gráficos

**1. Tipo de universidad (Privado / Pública).** Tabla de detalle con egresados,
índice base 100 y participación por año; gráfico de evolución **en niveles
absolutos** (privadas y públicas en el mismo eje, escala parecida; **azul =
Privado, naranja = Pública**) y torta de composición del último año con los
mismos colores (`01_tipo_univ_nivel`, `02_tipo_univ_torta`).

**2. Nivel académico (Grado / Posgrado).** Con Pregrado excluido. Tabla de
detalle (base 100 y participación), evolución **en niveles absolutos** con
**un eje Y por categoría** (Grado y Posgrado difieren ~5× en escala, así que
cada serie va en su propio eje con el color de su eje; `03_nivel_academ_nivel`),
torta del último año y **egresados de Grado cada mil habitantes** (barras por
año, usando la población del Banco Mundial).

**3. Disciplina específica (37 disciplinas).** Tabla de detalle sobre **todas**
las disciplinas (egresados, participación y ranking dentro de cada año) y matriz
disciplina × año. Gráficos: **top 10 por año** (*small multiples*, un panel por
año) y **comparativo del top 10** entre el **trienio inicial** (suma 2014-2016)
y el **trienio final** (suma 2021-2023), tomando los tres primeros y los tres
últimos años de la serie (`07_disciplinas_top10_comparativo`). Además, la
evolución de la **relación Psicología/Ingeniería** (por año y valor global),
que también se incluye en la tabla de detalle.

**4. EGRESADOS vs. ESTUDIANTES.** Los puntos 1-3 usan egresados; la columna
`TIPO_ALUMNO` también trae estudiantes (matriculados), que se usan solo en el
punto 5.

**5. ¿Tasa de deserción? — no se calcula.** Inferir una tasa de deserción con
estos datos **no es técnicamente coherente**: la deserción exige seguir
**cohortes** (ingresantes de un año y cuántos egresan o abandonan años después),
y el archivo solo trae un **stock** anual de estudiantes y un **flujo** anual de
egresados, sin ingresantes por cohorte. Cualquier "tasa de deserción" así sería
un artefacto. En su lugar se reporta la **relación egresados/estudiantes**
(egresados cada 100 estudiantes) como **proxy de intensidad de egreso**,
explícitamente etiquetado como **NO** deserción.

### Salidas

Al ejecutar `exportar_todo()` (celda final del notebook) se generan, en
`output/argentina/` (gitignoreado, regenerable):

- **9 gráficos a 600 dpi** en `graficos/`.
- **`analisis_argentina.xlsx`** con una hoja por análisis (`notas`, `tipo_univ`,
  `nivel_academ`, `grado_por_mil`, `disciplinas`, `matriz_disciplinas`,
  `ratio_psico_ing`, `egre_vs_estu`).
- **`profesiones_argentina_export.zip`** con todo lo anterior (en Colab se
  descarga automáticamente al finalizar).

---

## Reproducibilidad

- Ambos notebooks corren end-to-end en Google Colab desde los badges del README;
  el setup clona/sincroniza el repo (`git fetch` + `reset --hard origin/main`) y
  purga los módulos del proyecto de `sys.modules` para evitar código viejo
  cacheado en runtimes reutilizados.
- Los notebooks **no se editan a mano**: se generan con
  `scripts/make_notebook.py` (00) y `scripts/make_notebook_arg.py` (01) y se
  validan ejecutándolos con nbclient antes de commitear.
- Las descargas crudas se cachean con timestamp en `data/raw/` (gitignoreado);
  `data/processed/` está versionado para que el dataset sea usable sin correr el
  pipeline. Los gráficos y ZIP (`output/`) son regenerables y no se versionan.
