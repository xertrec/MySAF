# mySAF — Informe inicial de calidad de datos

**Fuente:** `saf-espais-2026-equips.xlsx`  
**Ámbito temporal de los datos:** 2026-04-01 a 2026-10-31  
**Estado:** perfilado inicial; no se han modificado los datos originales.

## 1. Inventario de hojas

| Hoja | Filas de datos | Columnas |
|---|---:|---:|
| `Espais` | 42 | `Espai`, `Subespai`, `Aforament` |
| `Horari general` | 3 | `Dies`, `Horari` |
| `Reserves` | 194.567 | `EspaiPare`, `Recurs`, `DataUs`, `DiaSetmana`, `HoraInici`, `HoraFi`, `DuradaMin`, `DuradaHores` |
| `Reserves per franja` | 36.365 | `EspaiPare`, `Recurs`, `DataUs`, `DiaSetmana`, `HoraInici`, `Reserves` |
| `Activitats dirigides` | 48.591 | `DataInscripcio`, `CodiActivitat`, `Activitat`, `AforamentMax`, `Inscrits`, `PctOcupacio`, `HoraInici`, `HoraFi`, `Sala` |

## 2. Completitud y duplicados exactos

No se detectaron celdas vacías en las hojas `Horari general`, `Reserves`, `Reserves per franja` ni `Activitats dirigides`.

En `Espais`, la columna `Subespai` está vacía en 10 de 42 filas. Esos vacíos pueden representar espacios sin subespacio declarado; no deben completarse automáticamente.

| Hoja | Filas | Filas completas únicas | Exceso de repeticiones idénticas |
|---|---:|---:|---:|
| `Espais` | 42 | 40 | 2 |
| `Horari general` | 3 | 3 | 0 |
| `Reserves` | 194.567 | 36.514 | 158.053 |
| `Reserves per franja` | 36.365 | 36.365 | 0 |
| `Activitats dirigides` | 48.591 | 6.758 | 41.833 |

**Advertencia:** las repeticiones idénticas de `Reserves` y `Activitats dirigides` no deben eliminarse como duplicados sin más. La guía del reto indica que una fila de reservas puede representar una persona en salas/piscinas o una reserva de pista; una fila de actividades dirigidas es una inscripción. No hay identificadores de usuario que permitan distinguir esas filas idénticas. Las repeticiones pueden representar volumen real.

En `Espais` aparecen dos pares de filas idénticas que requieren confirmación antes de deduplicar:

- `pistes de pàdel` / `pista 1` / aforo `4` (aparece dos veces).
- `piscina 25 metres` / `carrer 6` / aforo `5` (aparece dos veces).

## 3. Fechas y consistencia

- `Reserves[DataUs]`: del 2026-04-01 al 2026-10-31; 214 fechas distintas.
- `Activitats dirigides[DataInscripcio]`: del 2026-04-01 al 2026-10-31; 212 fechas distintas.
- Todas las filas de `Reserves` tienen un `DiaSetmana` coherente con `DataUs`.
- En todas las filas de `Reserves`, `DuradaHores` coincide con `DuradaMin / 60`.
- `DataUs` y `DataInscripcio` están almacenadas como números de serie de Excel en el archivo original; deben convertirse explícitamente a fechas al cargar los datos.

**Precaución:** la guía advierte que `DataInscripcio` parece ser la fecha en que la persona se inscribió, no necesariamente el día de la clase. No utilizarla como fecha de sesión sin confirmación del SAF.

## 4. Reservas y agregación por franja

- `Reserves` contiene 194.567 filas.
- `Reserves per franja` contiene 36.365 grupos.
- La agregación de `Reserves` por `EspaiPare`, `Recurs`, `DataUs`, `DiaSetmana` y `HoraInici` reproduce exactamente las 36.365 filas de `Reserves per franja`.
- La suma de `Reserves` en la hoja agregada es 194.567.
- Hay 1.371 reservas con duración superior a 240 minutos; la duración máxima observada es 1.035 minutos.

La guía recomienda separar las reservas largas (posibles bloques de clubes o escuelas) de las reservas particulares. No clasificarlas automáticamente sin definir una regla con el equipo.

## 5. Ocupación de actividades dirigidas

- Hay 48.591 inscripciones.
- Se detectaron 34 filas donde `Inscrits > AforamentMax`.
- `PctOcupacio` coincide en todos los registros con el porcentaje truncado (`int(Inscrits / AforamentMax * 100)`), no con el redondeo convencional al entero más cercano. Conservar el valor original o documentar explícitamente la regla si se recalcula.
- Se observan 65 nombres distintos de actividad, 135 códigos de actividad y 14 valores distintos de `Sala`.

Las inscripciones por encima del aforo deben marcarse como anomalías, no borrarse automáticamente.

## 6. Normalización de espacios y recursos

- `Espais` contiene 17 valores distintos de `Espai` y 42 filas de inventario.
- `Reserves` contiene 33 valores distintos de `EspaiPare` y 118 valores distintos de `Recurs`.
- Los nombres no coinciden directamente entre inventario y reservas; además, algunos recursos incorporan diferencias de horario (por ejemplo, `dl-dv` frente a `ds-dg`) o divisiones de pista.

Es necesario crear una tabla de equivalencias (`resource_mapping`) con el nombre original, el espacio/subespacio canónico, el tipo de recurso y el estado de validación. No fusionar recursos únicamente por similitud textual: algunas diferencias identifican recursos o periodos de uso distintos.

## 7. Reglas provisionales de trabajo

1. Conservar siempre una copia de los datos originales.
2. No eliminar filas idénticas de `Reserves` ni de `Activitats dirigides` sin una regla justificada.
3. No completar automáticamente `Subespai` vacío.
4. No tratar `DataInscripcio` como fecha de clase sin confirmación.
5. Distinguir métricas de personas (salas/piscinas) de métricas de reservas de pista.
6. Mantener trazabilidad de cada registro y de cualquier transformación.
7. Mantener los archivos y la base de datos privados, de acuerdo con las condiciones del reto.

## 8. Próximo paso

Construir y revisar `resource_mapping` para enlazar los 33 nombres de `EspaiPare` y los 118 `Recurs` con los 42 registros del inventario de `Espais`. Los casos ambiguos quedarán marcados como pendientes de validación, no se resolverán por inferencia automática.
