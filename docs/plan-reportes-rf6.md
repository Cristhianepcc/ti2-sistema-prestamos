# Plan de implementación — Historial y Reportes (RF6)

Estado: propuesta v4, pendiente de confirmar las decisiones de la sección 12.
La sección 1 es una fotografía histórica del repositorio al redactar esta propuesta;
no describe el estado de esta rama de trabajo, que incluye cambios posteriores de RF5/RF6.
Para el estado vigente, consultar `docs/01-sdd.md` y `README.md`.
Cambios v4: se corrigió el riesgo obsoleto de `seeds.py` (ya mergeado en PR #65) y
se dejó explícita la decisión de paginación de `/historial` frente a la nota
pendiente de `docs/02-contrato-api.md` §6.
Referencias: `docs/01-sdd.md` §4.8, §5.1, §6.1, §9 · `docs/00-contexto-alcance-propuesta.md` (RF6; historias HF.6.1.1 y HF.6.2.1; "Historial y Reportes: vista de solo lectura").

## 1. Situación actual

- **Frontend:** `frontend/reportes.html` y `frontend/js/reportes.js` solo muestran la nota "llega en una próxima entrega". El sidebar ya muestra el enlace únicamente a `ADMINISTRADOR_SISTEMA` (`frontend/js/shell.js`).
- **Panel de Inicio del administrador:** `frontend/js/inicio.js` tiene las tarjetas "Préstamos activos (sistema)" y "Sanciones activas" con "—", a la espera de un endpoint de RF6.
- **Diseño (SDD §4.8):** define `GET /api/historial?usuario_id=`, `GET /api/reportes/inventario` y `GET /api/reportes/prestamos`. §5.1 prevé `routers/reportes.py`.
- **Historias de usuario:** HF.6.1.1 (estudiante: "consultar mi historial de préstamos") y HF.6.2.1 (Dirección: "ver reportes de inventario y préstamos").
- **Backend:** no existe router, schema ni service de reportes ni de historial. Lo más cercano es `GET /prestamos?mios=true`.
- **Sanciones:** no existe el modelo (RF5 pendiente).
- **Préstamos atrasados:** `prestamo_service.marcar_prestamos_atrasados()` existe pero **nadie la invoca**. En la práctica ningún préstamo llega a `ATRASADO` (ver sección 5).
- **Daño y pérdida:** `registrar_devolucion` recibe `danado` y `perdido` pero no los guarda; solo pone el recurso en `MANTENIMIENTO` y descarta el motivo de sanción (`TODO(RF5)`). No se pueden reportar con exactitud.
- **Solicitudes:** el modelo solo guarda `created_at` y los ids de quién avaló, autorizó y aceptó; **no guarda cuándo** se avaló, autorizó o aceptó.

## 2. Alcance en dos niveles

### Nivel 1 — Mínimo (lo que RF6 pide)

| # | Entregable | Endpoint |
|---|---|---|
| 1 | Historial de préstamos por usuario | `GET /api/historial` |
| 2 | Reporte de inventario | `GET /api/reportes/inventario` |
| 3 | Reporte de préstamos (incluye atrasados) | `GET /api/reportes/prestamos` |
| 4 | Resumen liviano para la tarjeta de Inicio | `GET /api/reportes/resumen` |

### Nivel 2 — Valor agregado (si hay tiempo)

| # | Entregable | Endpoint |
|---|---|---|
| 5 | Reporte de solicitudes (estado, tipo y tiempo de atención) | `GET /api/reportes/solicitudes` |
| 6 | Reporte de reservas por estado | `GET /api/reportes/reservas` |
| 7 | Actividad por usuario (más préstamos, más atrasos) | dentro de `/reportes/prestamos` o endpoint propio |

El nivel 2 se puede dejar fuera sin romper el nivel 1. Los reportes 5 a 7 responden al objetivo del proyecto ("reducir el tiempo de atención y la pérdida de ítems"), pero ninguno es indispensable para cumplir RF6.

## 3. Quién puede ver qué

| Recurso | Quién |
|---|---|
| `/reportes/*` (todos) | Solo `ADMINISTRADOR_SISTEMA` |
| `/historial` sin `usuario_id` | Cualquier usuario autenticado: ve **su propio** historial |
| `/historial?usuario_id=X` | El propio usuario (si `X` es él) o `ADMINISTRADOR_SISTEMA`. Otro usuario recibe 403 |

- **Backend:** `require_role(Rol.ADMINISTRADOR_SISTEMA)` en los reportes; el historial valida el `usuario_id` contra el usuario autenticado. 401 sin sesión.
- **Frontend:** el enlace "Reportes" del sidebar ya está restringido a admin. El historial necesita una entrada o vista para el estudiante/docente (ver sección 8).
- Los custodios mantienen su acceso actual a `GET /prestamos`. No tienen acceso a reportes.

## 4. Contenido y contrato

Todo se calcula en cada petición con `GROUP BY` en la base de datos (no se cargan filas para contar en Python; RNF3). No se persiste nada. Campos en `snake_case`; los conteos vacíos devuelven `0`, nunca `null` ni error.

### 4.1 `GET /api/historial`

Historial de préstamos de un usuario, el más reciente primero.

| Param | Tipo | Defecto | Descripción |
|---|---|---|---|
| `usuario_id` | entero | usuario autenticado | Ver reglas de la sección 3. |
| `estado` | enum de préstamo | todos | Filtro opcional. |
| `limite` | entero 1–100 | 20 | Tamaño de página. |
| `offset` | entero ≥ 0 | 0 | Desplazamiento. |

```json
{
  "total": 12,
  "limite": 20,
  "offset": 0,
  "items": [
    {
      "prestamo_id": 31,
      "recurso": { "id": 3, "codigo": "LIB-003", "nombre": "Clean Code", "tipo_recurso": "LIBRO" },
      "tipo_prestamo": "SIMPLE",
      "modalidad_uso": "RETIRO_TEMPORAL",
      "estado": "DEVUELTO",
      "fecha_entrega": "2026-10-02T15:10:00Z",
      "fecha_limite": "2026-10-09T15:10:00Z",
      "fecha_devolucion": "2026-10-08T11:00:00Z",
      "dias_atraso": 0
    }
  ]
}
```

- `dias_atraso`: si ya se devolvió, días entre `fecha_limite` y `fecha_devolucion` (0 si fue a tiempo); si sigue sin devolverse, días entre `fecha_limite` y ahora (0 si no venció). Usa la regla única de la sección 5.
- Usuario inexistente: 404.
- **Paginación:** `limite`/`offset` resuelve, para este endpoint, la nota "Pendiente de definir" de `docs/02-contrato-api.md` §6 sobre paginar `GET /api/recursos` (`?page/?size` vs `?limit/?offset`). Se adopta `?limite/?offset` en español, consistente con los demás query params de la API (`mias`, `pendientes`, `estado`). No se retroactiva a `/recursos` en esta entrega (el catálogo sigue siendo chico); al implementar, actualizar esa nota en §6 para que apunte a `/historial` como precedente en vez de dejarla abierta.

### 4.2 `GET /api/reportes/inventario`

Sin parámetros. Foto del inventario en el momento de la consulta.

```json
{
  "total_recursos": 42,
  "por_tipo": { "LIBRO": 25, "DEPORTIVO": 10, "ACADEMICO": 7 },
  "por_estado": { "DISPONIBLE": 30, "RESERVADO": 2, "PRESTADO": 8, "MANTENIMIENTO": 2 },
  "por_gestor": { "CENTRO_ESTUDIANTES": 35, "INFRAESTRUCTURA": 7 },
  "tipo_por_estado": {
    "LIBRO": { "DISPONIBLE": 18, "RESERVADO": 1, "PRESTADO": 5, "MANTENIMIENTO": 1 },
    "DEPORTIVO": { "DISPONIBLE": 8, "RESERVADO": 1, "PRESTADO": 1, "MANTENIMIENTO": 0 },
    "ACADEMICO": { "DISPONIBLE": 4, "RESERVADO": 0, "PRESTADO": 2, "MANTENIMIENTO": 1 }
  }
}
```

Todas las claves de los enums aparecen siempre, aunque valgan 0. `MANTENIMIENTO` incluye los recursos retirados por daño o pérdida; no se distingue el motivo (ver sección 1).

### 4.3 `GET /api/reportes/prestamos`

| Param | Tipo | Defecto | Descripción |
|---|---|---|---|
| `desde` | fecha `YYYY-MM-DD` | sin límite | `fecha_entrega >= desde` (inclusive). |
| `hasta` | fecha `YYYY-MM-DD` | sin límite | `fecha_entrega <= hasta`, **incluyendo todo ese día**. |
| `top` | entero 1–20 | 5 | Cantidad en "más prestados" y "usuarios más activos". |
| `limite_atrasados` | entero 1–200 | 50 | Tope de filas en la lista de atrasados. |

```json
{
  "periodo": { "desde": "2026-09-01", "hasta": "2026-11-17" },
  "total_prestamos": 57,
  "por_estado": { "ACTIVO": 8, "ATRASADO": 3, "DEVUELTO": 46 },
  "por_tipo": { "SIMPLE": 40, "POR_CURSO": 14, "EXCEPCIONAL": 3 },
  "por_modalidad": { "EN_SITIO": 22, "RETIRO_TEMPORAL": 35 },
  "mas_prestados": [
    { "recurso_id": 3, "codigo": "LIB-003", "nombre": "Clean Code", "total": 9 }
  ],
  "garantias": { "retenidas": 4, "valor_retenido": "120.00" },
  "atrasados": {
    "total": 3,
    "items": [
      {
        "prestamo_id": 12,
        "recurso": { "id": 7, "codigo": "ACA-002", "nombre": "Osciloscopio" },
        "prestatario": { "id": 5, "codigo": "20230001", "nombres": "Ana Pérez" },
        "fecha_limite": "2026-11-10T18:00:00Z",
        "dias_atraso": 7
      }
    ]
  }
}
```

Reglas:

- `por_estado`, `por_tipo`, `por_modalidad`, `mas_prestados` y `garantias` **respetan el rango** `desde`/`hasta`.
- `atrasados` es una **foto actual** y **ignora el rango**: un préstamo vencido sigue siendo un problema aunque se haya entregado fuera del periodo.
- `garantias.retenidas`: garantías con `devuelta = false` de préstamos aún no devueltos; `valor_retenido` es la suma de su `valor` (cadena decimal, como en `GarantiaPublica`).
- `desde > hasta` o fechas mal formadas responden **422**. Sin rango, `periodo` devuelve `null` en ambos campos.
- Orden de `atrasados.items`: más días de atraso primero. `atrasados.total` es el total real aunque `items` esté recortado.
- Expone datos personales mínimos del prestatario (id, código, nombres); no email ni roles.
- "Usuarios más activos" (entregable 7) agregaría un bloque `usuarios_mas_activos` con `usuario_id`, `codigo`, `nombres`, `total_prestamos`, `total_atrasos`. Solo en nivel 2.

### 4.4 `GET /api/reportes/resumen`

Endpoint liviano, no previsto en el SDD §4.8, para no ejecutar el reporte completo solo por un contador de Inicio.

```json
{ "prestamos_activos": 8, "prestamos_atrasados": 3 }
```

Aquí "activos" **incluye** los atrasados (todo préstamo no devuelto); `prestamos_atrasados` es el subconjunto vencido.

### 4.5 `GET /api/reportes/solicitudes` (nivel 2)

Mismos `desde`/`hasta`, aplicados sobre `solicitud.created_at`.

```json
{
  "periodo": { "desde": null, "hasta": null },
  "total_solicitudes": 80,
  "por_estado": { "SOLICITADA": 5, "AVALADA": 3, "AUTORIZADA": 1, "ACEPTADA": 60, "RECHAZADA": 11 },
  "por_tipo": { "SIMPLE": 55, "POR_CURSO": 20, "EXCEPCIONAL": 5 },
  "pendientes_por_etapa": { "por_avalar": 5, "por_autorizar": 3, "por_aceptar": 1 },
  "tiempo_atencion": {
    "muestras": 60,
    "promedio_horas": 4.2,
    "maximo_horas": 30.5
  }
}
```

- **Tiempo de atención (limitado):** el modelo no guarda cuándo se avaló, autorizó o aceptó. Lo único medible es el tiempo desde que se crea la solicitud (`solicitud.created_at`) hasta que se entrega el recurso (`prestamo.fecha_entrega`), y solo para solicitudes `ACEPTADA` que tengan préstamo. Las rechazadas no tienen fecha de cierre y quedan fuera de la métrica (`muestras` indica cuántas entraron).
- Si se quiere medir cada etapa (aval, autorización, aceptación) hay que agregar columnas de fecha a `solicitud`, lo que implica migración y tocar el trabajo de otra persona. No se propone en esta entrega.
- `pendientes_por_etapa`: `por_avalar` son `SOLICITADA` de tipo `POR_CURSO`/`EXCEPCIONAL`; `por_autorizar` son `AVALADA` de tipo `EXCEPCIONAL`; `por_aceptar` son las que esperan al custodio (`SOLICITADA` SIMPLE, `AVALADA` POR_CURSO o `AUTORIZADA`). Confirmar contra `solicitud_service` antes de implementar.

### 4.6 `GET /api/reportes/reservas` (nivel 2)

```json
{
  "total_reservas": 30,
  "por_estado": { "PENDIENTE": 6, "CONFIRMADA": 10, "CANCELADA": 9, "VENCIDA": 5 }
}
```

Con `desde`/`hasta` sobre `reserva.fecha`.

## 5. Regla única de "atrasado"

El estado `ATRASADO` de la BD no es fiable (nadie ejecuta `marcar_prestamos_atrasados`). Por eso:

- Se define **una sola** función/condición en `reporte_service`: un préstamo está atrasado si `estado IN (ACTIVO, ATRASADO)` y `fecha_limite < ahora`.
- `por_estado` del reporte cuenta con esa regla: los `ACTIVO` vencidos se cuentan como `ATRASADO`.
- El reporte de préstamos, el historial (`dias_atraso`), el resumen de Inicio y los tests usan esa misma regla.
- **Fuera de este issue, pero hay que avisar a quien tenga RF3:** que `marcar_prestamos_atrasados` se invoque (por ejemplo al listar préstamos o con una tarea periódica) para que el estado almacenado coincida con la realidad.

## 6. Fuera de alcance

- **Sanciones:** dependen de RF5. La tarjeta "Sanciones activas" de Inicio seguirá en "—".
- **Daño y pérdida de ítems:** no se guardan hoy. Se incorporan cuando RF5 los persista. Mientras tanto solo se ve el total en `MANTENIMIENTO` (inventario).
- **Tiempo de atención por etapa:** requiere nuevas columnas de fecha en `solicitud`.
- **Tabla `reporte` del SDD:** el reporte es una vista de solo lectura; no se registra quién lo genera.
- **Exportar PDF.**
- **Reporte por gestor para custodios.**

## 7. Cambios por capa

### Backend
| Archivo | Cambio |
|---|---|
| `backend/app/schemas/reporte.py` | Nuevo. Modelos Pydantic de respuesta de reportes e historial. |
| `backend/app/services/reporte_service.py` | Nuevo. Consultas `GROUP BY` y la regla única de atraso. Sin funciones de fecha específicas de un motor (tests en SQLite, producción en PostgreSQL). |
| `backend/app/routers/reporte.py` | Nuevo. `/reportes/*` con `require_role(ADMINISTRADOR_SISTEMA)`; validación de fechas y límites. |
| `backend/app/routers/historial.py` | Nuevo (o dentro de `reporte.py`). `GET /historial` con la regla de propio/admin. |
| `backend/app/main.py` | Registrar los routers con prefijo `/api`. |

### Tests
| Archivo | Cubre |
|---|---|
| `backend/tests/test_reporte_service.py` | Conteos con datos sembrados; **reportes vacíos** (todo en 0); `ACTIVO` vencido contado como atrasado; filtro por rango (inclusive, día final completo); top N y límite de atrasados; garantías retenidas; nivel 2 si se implementa (tiempo de atención solo con solicitudes aceptadas con préstamo). |
| `backend/tests/test_reportes_api.py` | 200 para admin; 403 para **cada** rol no admin (estudiante, docente, custodio CE, custodio Infra); 401 sin token; 422 con `desde > hasta` o fechas inválidas. Patrón de `test_usuarios_api.py` (`crear_cliente`, `crear_admin`). |
| `backend/tests/test_historial_api.py` | Un usuario ve su historial; 403 al pedir el de otro; el admin ve el de cualquiera; 404 con usuario inexistente; paginación y filtro por estado. |

### Frontend
| Archivo | Cambio |
|---|---|
| `frontend/reportes.html` | Reemplazar la nota por contenedores (inventario, préstamos, y solicitudes/reservas si hay nivel 2) y filtro de fechas. |
| `frontend/js/reportes.js` | Llamar a `api.get("/reportes/...")` y pintar con los helpers de `render.js` (cargando / vacío / error). El 401 y 403 se manejan con lo que ya hace `api.js`. |
| `frontend/js/inicio.js` | Tarjeta "Préstamos activos (sistema)" con `GET /reportes/resumen`. |
| Vista de historial | Dónde mostrarlo depende de la decisión 3 (sección 12): ampliar `mis-prestamos.html` o crear `historial.html`. |

### Datos de ejemplo
| Archivo | Cambio |
|---|---|
| `backend/app/seeds.py` | Sembrar préstamos de ejemplo (activos, devueltos, al menos uno vencido, con y sin garantía) y, para nivel 2, solicitudes y reservas en distintos estados. |

### Documentación
| Archivo | Cambio |
|---|---|
| `docs/02-contrato-api.md` | Anexo "RF6 — Historial y Reportes" con los ejemplos de la sección 4. |
| `docs/01-sdd.md` §4.8 y §9 | Agregar `/reportes/resumen` (y los de nivel 2 si se hacen) y actualizar la trazabilidad de RF6. |

No se tocan modelos ni esquema de BD: no hace falta migración ni recrear la base.

## 8. Orden de trabajo

0. Crear rama `feat/rf6-reportes` desde `main`, sin arrastrar los cambios locales ajenos.
1. Fijar el contrato en `docs/02-contrato-api.md` (permite al frontend avanzar con datos mock en paralelo).
2. Backend nivel 1: schemas, service (con la regla de atraso), routers y registro en `main.py`.
3. Tests de nivel 1.
4. Seed de préstamos de ejemplo.
5. Frontend nivel 1: `reportes.html`, `reportes.js`, tarjeta de Inicio y vista de historial.
6. Actualizar SDD (§4.8 y §9).
7. Nivel 2 (solicitudes, reservas, usuarios más activos), repitiendo pasos 2, 3, 4 y 5 para cada reporte.

## 9. Criterios de aceptación

- Un admin ve los reportes con datos reales; cualquier otro rol recibe 403 y sin sesión recibe 401.
- Un estudiante o docente ve su propio historial y no puede ver el de otro (403).
- Con la BD vacía los reportes muestran ceros y la pantalla muestra estado vacío, no error.
- Un préstamo `ACTIVO` con `fecha_limite` vencida aparece como atrasado en el reporte, en la lista, en el historial y en el resumen.
- El filtro `desde`/`hasta` cambia los totales y el top, y no cambia la lista de atrasados.
- Los tests pasan en SQLite y las consultas no usan funciones exclusivas de un motor.
- Nivel 2, si se hace: el tiempo de atención declara cuántas muestras usó y excluye solicitudes sin préstamo.

## 10. Responsables

Por definir. Propuesta de corte natural: una persona hace backend + tests (pasos 1 a 4) y otra frontend (paso 5), apoyándose en el contrato del paso 1.

## 11. Riesgos

- **Estado `ATRASADO` sin mantener:** resuelto en el reporte con la regla única, pero el dato almacenado sigue desactualizado hasta que alguien invoque `marcar_prestamos_atrasados`.
- **Tiempo de atención limitado:** sin fechas por etapa, la métrica es aproximada. Hay que decirlo en la pantalla.
- **Diferencias SQLite/PostgreSQL:** agrupar por `Enum` y comparar fechas con zona horaria puede comportarse distinto; los tests de service deben cubrir el caso.

## 12. Decisiones pendientes

| # | Decisión | Propuesta por defecto |
|---|---|---|
| 1 | ¿Se hace solo el nivel 1 o también el nivel 2? | Nivel 1 ahora; nivel 2 si queda tiempo, empezando por solicitudes |
| 2 | ¿Endpoint liviano `/reportes/resumen` para Inicio, o reutilizar `/reportes/prestamos`? | Endpoint liviano |
| 3 | ¿Dónde se ve el historial del estudiante/docente? | Ampliar `mis-prestamos.html` con paginación y filtro; el admin lo consulta por `usuario_id` |
| 4 | ¿Se agregan fechas por etapa a `solicitud` para medir el tiempo de atención real? | No; usar la aproximación solicitud → entrega |
| 5 | ¿Se persiste daño/pérdida ahora (columnas en `prestamo`) o se espera a RF5? | Esperar a RF5 |
| 6 | ¿Botón de exportar CSV (generado en el navegador a partir del JSON)? | No en esta entrega |
| 7 | ¿Los custodios ven un reporte limitado a su gestor? | No |
| 8 | ¿Quién implementa backend y quién frontend? | Por definir |
