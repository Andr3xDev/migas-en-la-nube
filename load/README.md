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

## Resultados

- Log del paso `Run k6` y resumen en la página de la corrida (`GITHUB_STEP_SUMMARY`).
- Artefacto `load-results-<ambiente>-<escenario>` con `summary.txt` y `summary.json`.
- Los pedidos de la prueba quedan en dev con el nombre `k6 load test`. El stock de dev baja con cada pedido; se repone desde el panel de administración.

## Costo

Cosmos DB serverless cobra por unidad de solicitud y Static Web Apps Standard (prod) incluye 100 GB de transferencia al mes. Las lecturas del catálogo son baratas y el total de peticiones está acotado (unas 53.400 en `stress`), por lo que el costo de cada corrida es despreciable frente al presupuesto.

## Riesgo de disponibilidad en producción

`stress` sobre producción es la validación del escalado y está permitido, pero puede producir errores reales: Cosmos DB serverless puede responder 429 ante una ráfaga y los clientes reales pueden notar latencia. También puede disparar las alertas de 5xx y de disponibilidad de producción (correos). Córrelo fuera de horario de atención y una sola vez.
