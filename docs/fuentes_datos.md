# Fuentes de datos — estructura verificada

Registro de lo que se verificó empíricamente contra cada fuente
(2026-07-22). Si algo falla en el futuro, comparar contra esto.

## Eurostat — API SDMX 2.1 de diseminación

Base: `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1`

### Estructura (dataflow)

- `GET /dataflow/ESTAT/{dataset}/1.0?references=descendants`
- **No acepta `references=all`** → error 140 `ERR_GEN_FLOW_REFERENCES`
  (solo `None|Children|Descendants`).
- Las codelists que devuelve son las genéricas completas (UNIT: 758
  códigos, GEO: 4.292); los códigos realmente usados se descubren
  consultando datos. La respuesta no incluye ContentConstraints.

### educ_uoe_grad02 (fuente primaria)

- Título: *Graduates by education level, programme orientation, sex and
  field of education*.
- Orden de dimensiones del filtro: `freq.unit.isced11.iscedf13.sex.geo`.
- `unit=NR` (números absolutos). Sexo total = `T`.
- Cobertura observada: 2013-2024; 39 geografías-país (códigos de 2
  letras; `EL`=Grecia, `UK`=Reino Unido) + agregados (`EU27_2020`...).
- Georgia (`GE`) reporta solo campos broad, no narrow.

### educ_uoe_grad10 (NO usar para composición)

- Título: *Distribution of male and female graduates...*
- Orden de dimensiones: `freq.sex.isced11.iscedf13.unit.geo` (¡distinto!).
- Solo `unit=PC`; **rechaza `sex=T`** (error 150). Semántica: % de cada
  sexo dentro del campo (F+M = 100 por campo). Útil solo para brecha de
  género.

### Datos

- `GET /data/{dataset}/{filtro}?format=SDMX-CSV&startPeriod=YYYY`
- Filtro posicional separado por puntos; múltiples valores con `+`;
  posición vacía = sin filtrar.
- Series totalmente vacías no aparecen; `&returnData=ALL` las incluye
  (para panel balanceado).
- Errores SDMX pueden venir como XML Fault con HTTP 200: chequear si la
  respuesta empieza con `<?xml`.
- Códigos `iscedf13` (230): broad `F\d{2}` (11), **narrow `F\d{3}` (57)**,
  detailed `F\d{4}` (148), especiales (`TOTAL`, `UNK`, `NSP`, `OTH`,
  combinaciones tipo `F03_04`).

## SPU (Argentina) — data/external/profesiones_arg.xlsx

Síntesis de Información Universitaria. 6.074 filas, 2014-2023.
Columnas: `ANIO, TIPO_UNIV (Pública/Privado), NIVEL_ACADEM
(Pregrado/Grado/Posgrado), OF_ACADEM (Doctorado/Especialidad/Maestría/
Otros), DISCIP_OCDE (6 ramas), DISCIP_ESPECIF (37 disciplinas SPU),
TIPO_ALUMNO (EGRESADOS/ESTUDIANTES), U_MED, VALOR (int)`.

- Las 37 `DISCIP_ESPECIF` matchean el crosswalk; incluye "Salud Pública"
  (no estaba en la lista SPU clásica) y no incluye "Otras Ciencias
  Humanas" (se mantiene en el crosswalk por si aparece en otros cortes).
- Totales de egresados verificados: Grado 940.651 / Maestría 40.601 /
  Especialidad 91.545 / Doctorado 20.458 / Pregrado 253.273 /
  Posgrado-Otros 10.698.

## Banco Mundial — API v2

- `GET https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&date=2014:2024&per_page=20000`
- Respuesta: `[metadata, filas]`; filtrar `countryiso3code` de 3 letras
  (los agregados regionales también tienen iso3: se descartan al mergear
  contra la lista de países del panel).
- Indicadores usados: `SP.POP.TOTL` (población), `NY.GDP.PCAP.CD` (PIB pc
  USD corrientes), `NY.GDP.PCAP.PP.CD` (PIB pc PPA).
- Faltante conocido: Liechtenstein sin PPA.

## PNUD — IDH (Human Development Report 2025)

- CSV: `https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv`
- **Encoding latin-1** (falla como UTF-8). 206 filas × 1.112 columnas.
- IDH en columnas anchas `hdi_1990` ... `hdi_2023` → melt a formato largo.
- Faltantes conocidos: Kosovo (XKX) no está; IDH llega hasta 2023.

## Cache

Todas las descargas crudas van a `data/raw/` con nombre
`{fuente}_{hash|params}_{YYYYMMDD}.*`; las corridas siguientes reutilizan
el archivo más reciente del mismo query (`force=True` para re-descargar).
