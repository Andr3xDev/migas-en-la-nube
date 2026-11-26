# Evidencia de las pruebas

Capturas que referencia [docs/hld.md](../../hld.md) (secciones de observabilidad y prueba de carga). Todas corresponden a la corrida de `stress` en prod del 26 de noviembre de 2026.

| Archivo | Qué capturar |
| --- | --- |
| `traffic-alert-fired.png` | Correo `Fired` de `alert-pdc-prod-traffic` |
| `traffic-alert-resolved.png` | Correo `Resolved` de `alert-pdc-prod-traffic` (05:43:30 UTC) |
| `traffic-alert-history.png` | Monitor > Alertas en el portal: historial de la alerta de `Fired` a `Resolved` |
| `scaling-instances.png` | Gráfico de la consulta KQL de instancias por minuto en Application Insights, 05:25 a 05:50 UTC |
| `cosmos-ru.png` | Métrica `Total Request Units` de la cuenta de Cosmos DB, 05:25 a 05:50 UTC |
