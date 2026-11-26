# Prueba de carga

Prueba de carga con [k6](https://grafana.com/docs/k6/) que valida el requisito de escalabilidad del HLD (soportar 3 veces la carga del pico del sábado). Corre como el workflow `load.yml`, lo dispara una persona con `workflow_dispatch` y la evidencia son los logs y el artefacto de la corrida. No requiere instalar nada en local.

## Supuestos y tasas

Del HLD (sección 2): el pico es el sábado de 9:00 a 11:00, con unas **300 visitas por hora** (5 por minuto). El script (`load.js`) define estos valores como constantes con nombre.

| Supuesto | Valor |
| --- | --- |
| Visitas en el pico | 300 por hora = 5 por minuto |
| Peticiones por visita | 10: 4 estáticas (inicio, hoja de estilos, script de navegación, página de producto) y 6 llamadas al API (lista de productos, detalle de 4 productos y lista otra vez al volver al catálogo) |
| Pedidos | 40 al día entre semana y 120 el fin de semana; la prueba usa 6 por minuto, muy por encima del pico real, para que la corrida sea corta |

| Escenario | Qué hace | Tasa de visitas | Duración medida | Visitas | Peticiones (llamadas al API) | Dónde |
| --- | --- | --- | --- | --- | --- | --- |
| `realistic` | El pico del sábado | 5 por minuto | 5 min | 25 | 250 (150) | dev y prod |
| `peak3x` | 3 veces el pico | 15 por minuto | 5 min | 75 | 750 (450) | dev y prod |
| `stress` | Rampa de llegada: 1 a 5, 20 y 40 visitas por segundo | hasta 40 por segundo (unas 480 veces el pico) | 5 min | unas 5.340 | unas 53.400 (unas 32.000); hasta 240 llamadas al API por segundo | dev y prod |
| `orders` | Crea pedidos de invitado con el cliente `k6 load test` | 6 pedidos por minuto | 3 min | 18 pedidos | 18 | solo dev |

Un calentamiento de 30 s precede a toda corrida y no entra en las duraciones de la tabla.

Las tasas reales son muy bajas, por eso las corridas son cortas y `stress` es el escenario que demuestra el escalado: sube la tasa hasta encontrar dónde se degrada la latencia.

Producción solo recibe lecturas (`GET /api/products`, `GET /api/products/{id}`, páginas y recursos estáticos). El escenario `orders` escribe datos y el workflow lo rechaza en producción antes de pedir la aprobación del environment.

## Umbrales

- `http_req_failed` menor a 1 %.
- `http_req_duration` p95 menor a 1000 ms.
- `dropped_iterations` igual a 0: si k6 no alcanza la tasa pedida (se queda sin VUs), la corrida falla en vez de pasar en silencio.

Los umbrales solo miden los escenarios `visits` y `orders`, y solo se registran para el escenario que corre. Antes de cada corrida hay un calentamiento de 5 iteraciones (`warmup`, `GET /api/health` y `GET /api/products`) porque las primeras peticiones pueden sufrir el arranque en frío de las Functions; ese tráfico queda fuera de los umbrales.

## Cómo correrla

1. En GitHub: Actions, workflow `load`, Run workflow. El workflow aparece en "Run workflow" solo después de que `load.yml` se fusione a la rama por defecto (`main`), y se lanza desde `main`.
2. Elegir `environment` (`dev` o `prod`) y `scenario`. En `prod` el environment pide aprobación.
3. El workflow usa su propio grupo de concurrencia (`load-<ambiente>`) y no coordina con el despliegue: no lo lances mientras haya un despliegue en curso.

## Resultados de las corridas

Corridas del 26 de noviembre de 2026 (UTC). Las peticiones y las iteraciones incluyen el calentamiento y el `setup`.

| Ambiente | Escenario | Corrida | p95 (ms) | Promedio / p90 / máximo (ms) | Fallidas | Peticiones | Iteraciones | Descartadas | VUs máximos | Resultado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | `realistic` | [45757984915](https://github.com/Andr3xDev/migas-en-la-nube/actions/runs/45757984915) | 90 | 61 / 88 / 1.744 | 0 % | 271 | 31 | 0 | 3 | Pasa |
| dev | `orders` | [45758851277](https://github.com/Andr3xDev/migas-en-la-nube/actions/runs/45758851277) | 343 | 185 / 263 / 400 | 0 % | 30 | 24 | 0 | 3 | Pasa |
| prod | `realistic` | [45759342723](https://github.com/Andr3xDev/migas-en-la-nube/actions/runs/45759342723) | 74 | 40 / 62 / 132 | 0 % | 271 | 31 | 0 | 3 | Pasa |
| prod | `peak3x` | [45763172806](https://github.com/Andr3xDev/migas-en-la-nube/actions/runs/45763172806) | 91 | 55 / 87 / 671 | 0 % (0 de 771) | 771 | 81 | 0 | 6 | Pasa |
| prod | `stress` | [45761827371](https://github.com/Andr3xDev/migas-en-la-nube/actions/runs/45761827371) | 111 | 54 / 92 / 4.835 | 0 % | 52.991 (unas 160 por segundo en promedio) | 5.303 | 41 | 62 | Falla solo por `dropped_iterations` |

**Nota sobre `stress`.** El sistema absorbió unas 53.000 peticiones con 0 % de errores y un p95 de 111 ms. Las 41 iteraciones descartadas (0,77 %) vienen de que k6 no asignó VUs con la rapidez necesaria en los saltos de la rampa (`preAllocatedVUs` en 20; solo se usaron 62 de 200): es un límite del generador de carga, no un error del servidor. El máximo de 4,8 s es una cola aislada, probablemente un arranque en frío al escalar. `preAllocatedVUs` sube a 100 para las próximas corridas.

Las corridas anteriores a la corrección del resumen muestran `undefined` en las líneas `Requests (...)` de `summary.txt`; los conteos reales están en `summary.json`.

## Dónde ver los resultados

- Log del paso `Run k6` y resumen en la página de la corrida (`GITHUB_STEP_SUMMARY`).
- Artefacto `load-results-<ambiente>-<escenario>` con `summary.txt` y `summary.json`.
- Los pedidos de la prueba quedan en dev con el nombre `k6 load test`. El stock de dev baja con cada pedido; se repone desde el panel de administración.

## Costo

Cosmos DB serverless cobra por unidad de solicitud y Static Web Apps Standard (prod) incluye 100 GB de transferencia al mes. Las lecturas del catálogo son baratas y el total de peticiones está acotado (unas 53.400 en `stress`), por lo que el costo de cada corrida es despreciable frente al presupuesto.

## Riesgo de disponibilidad en producción

`stress` sobre producción es la validación del escalado y está permitido, pero puede producir errores reales: Cosmos DB serverless puede responder 429 ante una ráfaga y los clientes reales pueden notar latencia. También puede disparar las alertas de 5xx, de disponibilidad de producción y de tráfico alto (correos). Córrelo fuera de horario de atención y una sola vez.

## Evidencia de escalado y desescalado

k6 no muestra instancias. Durante y después de `stress` en prod, en el portal (Application Insights, Logs) ejecuta:

```kusto
requests
| where timestamp > ago(1h)
| summarize instancias = dcount(cloud_RoleInstance), peticiones = count() by bin(timestamp, 1m)
| render timechart
```

`instancias` debe subir durante `stress` y bajar unos minutos después de que termine. No está verificado que las Functions administradas de Static Web Apps reporten un `cloud_RoleInstance` por instancia; si siempre muestra 1, la evidencia es la latencia estable de k6 y la métrica `Total Request Units` de Cosmos DB (portal, cuenta de Cosmos DB, Metrics), junto con la presencia de respuestas 429. La alerta de tráfico alto pasando a `Fired` y luego a `Resolved` también lo muestra. Las capturas van en [docs/hld.md](../docs/hld.md).

## Demostración de la alerta de tráfico alto

La alerta de prod se dispara con más de 1.500 peticiones al API en 5 minutos. `realistic` (150) y `peak3x` (450) no la disparan; `stress` (unas 32.000 llamadas en 5 minutos) sí. Correr `stress` en prod es entonces la demostración de la alerta: pasa a `Fired`, llega el correo y se resuelve al terminar. El procedimiento y las capturas están en la sección de observabilidad de [docs/hld.md](../docs/hld.md).
