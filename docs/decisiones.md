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

`notebooks/01_descarga_y_panel.ipynb` no se edita a mano: se genera con
`scripts/make_notebook.py` (correr `python scripts/make_notebook.py`) y se
valida ejecutándolo end-to-end con nbclient antes de commitear.

## Lecciones técnicas

- `.iloc[-1]` sobre una selección posiblemente vacía → guard
  `if s.empty: continue` (rompió en Colab cuando un país no tenía F061).
- Runtimes reutilizados de Colab: purgar módulos propios de `sys.modules`
  en el setup, o el kernel sigue ejecutando código viejo.
- Consola Windows cp1252: evitar caracteres no-ASCII en `print()` de
  scripts.
- El CSV del PNUD es latin-1; los Fault de Eurostat vienen con HTTP 200.
