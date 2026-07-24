# Registro de decisiones

Decisiones metodológicas y técnicas del proyecto, con fecha y razón.
Cambiar cualquiera de estas implica re-generar el panel y documentarlo acá.

## 2026-07-22 — Fuente primaria: educ_uoe_grad02, no grad10

La hipótesis inicial era que grad10 ("Distribution of graduates") venía en
porcentajes y habría que cruzarlo con los totales de grad02 para
reconstruir absolutos. Verificado contra la API: grad10 es la distribución
**por sexo dentro de cada campo** (no la composición por campo) y rechaza
`sex=T`. grad02 ya trae conteos absolutos (`unit=NR`) por campo narrow →
no hay nada que reconstruir. grad10 queda como complemento opcional para
análisis de brecha de género.

## 2026-07-22 — Unidad de análisis: ISCED-F narrow (F###)

57 códigos `F` + 3 dígitos. Los países que solo reportan broad (Georgia)
quedan fuera de la muestra; `coverage.csv` documenta la cobertura por país.

## 2026-07-22 — Niveles: ED6 / ED7 / ED8

Grado, maestría y doctorado. Se excluye ISCED 5 (pregrado/ciclo corto).

## 2026-07-22 — Mapeo de niveles SPU (Argentina) → ISCED

- Grado → ED6; Posgrado/Maestría → ED7; Posgrado/Doctorado → ED8.
- **Posgrado/Especialidad → ED7**: en el mapeo UNESCO de Argentina las
  especializaciones son ISCED 7. Configurable con
  `load_spu_egresados(include_especialidad=False)` si se prefiere una
  definición estricta de maestría (impacto: 91.545 egresados acumulados).
- Pregrado (ISCED 5, 253 mil) y Posgrado/"Otros" (10,7 mil, sin apertura
  por título) quedan excluidos y se reportan en el log.

## 2026-07-22 — Crosswalk SPU → ISCED-F: 38 disciplinas

- Confianza `alta`/`media`/`baja` por fila; toda decisión dudosa tiene
  `nota`. Los 5 casos `baja` (Industrias, Sanidad, Relaciones
  Institucionales y Humanas, Otras Ciencias Aplicadas, Otras Ciencias
  Sociales) requieren revisión manual — PENDIENTE.
- Agregados SPU que ISCED parte en dos campos: "Economía y Administración"
  (F031/F041, se asigna F041), "Sociología, Antropología y Servicio
  Social" (F031/F092, se asigna F031), "Bioquímica y Farmacia"
  (F051/F091, se asigna F091).
- "Salud Pública" → F091 (media): aparece en el Excel real de la SPU.
- "Otras Ciencias Humanas" se mantiene aunque este Excel no la use.

## 2026-07-24 — Ranking de orientación y ajustes de gráficos

- **Ranking humanístico vs. científico-técnico (notebook 00)**: como ISCED-F
  narrow no aísla Psicología (cae en F031, ciencias sociales), a nivel
  comparativo entre países se usa una razón entre campos *broad*:
  **humanidades y ciencias sociales** (F02 Artes y humanidades + F03 Cs.
  sociales/periodismo, incluye Psicología) sobre **ciencias duras, tecnología
  e ingeniería** (F05 Cs. naturales/matemática + F06 TIC + F07 Ingeniería).
  Ratio > 1 = predominio humanístico; < 1 = predominio técnico. Tabla de
  ranking + gráfico de barras (`report.tabla_ratio_orientacion` /
  `fig_ranking_ratio`). En 2023: Chipre lidera (~1,9), Alemania al fondo
  (~0,46), Argentina ~1,05 (puesto 10). El ratio exacto Psicología/Ingeniería
  a nivel disciplina existe aparte en el notebook 01 (datos SPU).
- **Ajustes de gráficos (pedido del usuario)**: se sacaron los títulos
  principales de los gráficos de ambos notebooks (el contexto va en el
  markdown). Notebook 00: gráfico de composición sin "(ED6)" en el eje;
  scatter de desarrollo con eje "Egresados universitarios cada mil
  habitantes", sin título y con más países etiquetados (extremos +
  intermedios, dinámico vía `_destacados_extremos`). Notebook 01: años como
  etiquetas en 45° en las evoluciones base 100, y `grado_por_mil` y
  `ratio_psico_ing` pasan a barras verticales; el comparativo top-10 envuelve
  las etiquetas largas en varias líneas (textwrap) en vez de truncarlas.

## 2026-07-24 — Análisis nativo de Argentina (SPU) y notebook 01

Se separa el proyecto en dos notebooks: `00_profesiones_mundo` (panel
ISCED-F comparativo, ex `01_descarga_y_panel`) y `01_profesiones_argentina`
(nuevo). El notebook 01 analiza las categorías **propias** de la SPU sin
pasar por ISCED-F, vía `src/argentina.py`. Decisiones:

- **Alcance fijo**: solo `TIPO_ALUMNO=EGRESADOS` y se **excluye siempre
  Pregrado** (ISCED 5) de todos los análisis y gráficos. Nota: este análisis
  incluye "Posgrado/Otros" (que el crosswalk a ISCED sí excluye por no poder
  asignarle nivel), por eso el total nativo (1.103.953) supera al del panel
  ISCED (1.093.255) en ~10,7 mil.
- **Período dinámico**: se toma de `ANIO` del archivo (2014-2023 hoy); si el
  Excel se actualiza con 2024/2025, todo se extiende solo. El comparativo de
  disciplinas usa primer vs. último año disponibles (hoy 2014 vs 2023).
- **Ratio Psicología/Ingeniería**: egresados de Psicología por cada egresado
  de Ingeniería, por año y global (acumulado); va en la tabla de detalle de
  disciplinas y en un gráfico. Ambas son disciplinas exactas en DISCIP_ESPECIF.
- **Tasa de deserción — NO se calcula**: requiere seguir cohortes
  (ingresantes vs. egreso/abandono N años después). El archivo solo tiene
  stock anual de ESTUDIANTES y flujo anual de EGRESADOS, sin ingresantes: una
  "deserción" así sería un artefacto. Se reporta en su lugar la relación
  egresados/estudiantes (egresados cada 100 estudiantes) como **proxy de
  intensidad de egreso**, explícitamente etiquetado como NO deserción.
- **Salidas**: 9 gráficos a 600 dpi + `analisis_argentina.xlsx` (8 hojas) en
  `output/argentina/` (gitignoreado), comprimidos en
  `profesiones_argentina_export.zip` (en Colab se auto-descarga).

## 2026-07-24 — Auditoría de coherencia del dataset

Auditoría cruzada de panel/indicadores/coverage/dataset.xlsx. La estructura
salió sana (sin duplicados ni nulos en el panel, 57 códigos con etiqueta,
join panel↔indicadores sin huérfanos). Se corrigieron/documentaron:

- **Egresados negativos → 0 (guard en el pipeline)**. Eurostat traía
  `BEL·2014·ED6·F050 = -38`, artefacto de redondeo/confidencialidad en un
  código "not further defined" (residual calculado por diferencia; el resto
  de esa serie es 0). `build_eurostat_panel` ahora fuerza `graduates<0 → 0`
  con `warning` en el log. Reproducible ante re-descargas. Aislado (1 de
  64.650). Guard permanente en `tests/test_data_integrity.py`.
- **Códigos "not further defined" (F0x0) → marcados, no borrados**. Son 9
  códigos residuales de "subcampo desconocido" (F000, F020, F030, F040,
  F050, F070, F080, F090, F100), pesan ~0,6% del total y Argentina nunca
  cae en ellos (0%). Se conservan en el panel y en los totales país (son
  egresados reales), pero se **excluyen de los gráficos/rankings por campo**
  porque distorsionan la comparación (asimetría Europa/ARG). Marca en la
  columna `tipo` de `iscedf_narrow_labels.csv` (disciplina / no_definido);
  `report.disciplina_codes()` es el filtro único. No confundir con los
  residuales `F0x9` ("not elsewhere classified"), que sí son disciplinas y
  son los que usa el crosswalk de ARG.
- **Caveat de ceros (Europa vs Argentina)**. Eurostat reporta 0 explícito
  para combinaciones país-campo-nivel-año sin egresados (~54% de sus filas);
  Argentina, vía crosswalk, solo genera filas donde la SPU tiene dato
  (ausencia = fila faltante, 0% de ceros). Consecuencia para el análisis:
  cualquier promedio/share por campo debe fijar un criterio explícito (p. ej.
  calcular solo sobre países con cobertura narrow completa) para no sesgar la
  comparación. No se altera el dato; queda como advertencia metodológica.
- **Gaps legítimos documentados**: `gdp_pc_ppp` nulo para Liechtenstein
  (LIE) en los 11 años (el Banco Mundial no publica PPA para LIE; sí tiene
  PIB pc USD); `hdi` nulo en 2024 para los 39 países (el HDR llega a 2023).

## 2026-07-24 — Revisión de los mapeos `confianza=baja` del crosswalk

Revisión de los 6 mapeos marcados `baja`. El panel no cambia: el pipeline
corre con `min_confianza="baja"` (incluye todo); la revisión solo reclasifica
confianza y reescribe notas.

- **Reclasificados a `media`** (mapeo correcto por construcción, no una
  adivinanza): los tres residuales *Otras Ciencias Aplicadas* → F079,
  *Otras Ciencias Sociales* → F039 y *Otras Ciencias Humanas* → F029 son el
  residual ISCED del mismo campo amplio de la rama SPU (07, 03, 02
  respectivamente); el campo amplio es cierto y F_x9 es su residual por
  definición. *Relaciones Institucionales y Humanas* → F041: RRHH (0413) y
  RRPP/publicidad (0414) caen ambas en F041, así que el agregado aterriza en
  F041 sin importar el split interno.
- **Se mantienen `baja`** (ambigüedad de contenido real, requieren el
  nomenclador de carreras de la SPU): *Industrias* → F072 (la SPU tiene
  *Ingeniería* aparte → "Industrias" es sobre todo procesamiento/alimentos,
  pero puede arrastrar ingeniería industrial F071; 3,4% de egresados ARG,
  volumen material) y *Sanidad* → F102 (cara o ceca entre F091 salud pública
  y F102 higiene/seguridad ocupacional; la existencia de *Salud Pública*
  aparte inclina a F102; 0,2%).
- **Reconciliación 5 vs 6**: el CSV tiene 6 filas `baja` pero *Otras Ciencias
  Humanas* no aparece en el Excel vigente de la SPU (fila defensiva, 0
  egresados), por eso los conteos previos hablaban de "5". Tras esta revisión
  quedan **2** casos `baja` reales (Industrias, Sanidad).

## 2026-07-22 — Rango temporal: desde 2014

Originalmente 2013+; se alineó a 2014 porque la serie argentina de la SPU
arranca en 2014. Eurostat llega a 2024; ARG e IDH a 2023.

## 2026-07-22 — Indicadores: Banco Mundial + PNUD

Población y PIB pc (USD y PPA) del BM (cubre Argentina, cosa que Eurostat
no); IDH de la serie completa del HDR 2025. Los scatters
egresados/desarrollo son descriptivos, no causales.

## 2026-07-22 — data/processed/ versionado

Los outputs (`panel.parquet`, `indicators.parquet`, `coverage.csv`,
`dataset.xlsx`) se commitean para que el dataset sea usable sin correr el
pipeline. Consecuencia: en Colab el clon queda "sucio" tras correr, por
eso el setup del notebook sincroniza con `fetch` + `reset --hard` (nunca
`pull`).

## 2026-07-22 — Notebook generado por script

Los notebooks no se editan a mano: se generan con sus scripts y se validan
ejecutándolos end-to-end con nbclient antes de commitear. `make_notebook.py`
→ `00_profesiones_mundo.ipynb` (renombrado el 2026-07-24; antes
`01_descarga_y_panel.ipynb`); `make_notebook_arg.py` →
`01_profesiones_argentina.ipynb`.

## 2026-07-22 — Capa de reporte (src/report.py) y export

- Todos los gráficos del informe se generan a 600 dpi en `output/`
  (gitignoreado: son regenerables y pesados). El ZIP
  `output/profesiones_pais_export.zip` junta gráficos + Excel; en Colab
  se descarga automáticamente al final del notebook.
- Un scatter de desarrollo por cada campo narrow con datos en ≥8 países
  (~50 gráficos en `graficos/por_campo/`); inline solo se muestran F061,
  F071 y F091 para no saturar el notebook.
- Etiquetas de campos en `data/reference/iscedf_narrow_labels.csv`
  (57 códigos, ES + EN); el Excel las incluye como hoja `codigos_iscedf`
  junto con la hoja `diccionario` (definición y fuente de cada variable,
  generada por `build_panel.data_dictionary()`).
- `report.variable_summary()` imprime el resumen de todas las variables
  (n, faltantes, min/mediana/media/max) para pegar en el informe.

## Lecciones técnicas

- `.iloc[-1]` sobre una selección posiblemente vacía → guard
  `if s.empty: continue` (rompió en Colab cuando un país no tenía F061).
- Runtimes reutilizados de Colab: purgar módulos propios de `sys.modules`
  en el setup, o el kernel sigue ejecutando código viejo.
- Consola Windows cp1252: evitar caracteres no-ASCII en `print()` de
  scripts.
- El CSV del PNUD es latin-1; los Fault de Eurostat vienen con HTTP 200.
