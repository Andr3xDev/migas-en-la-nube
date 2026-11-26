# Arquitectura

Fuente Mermaid: GitHub la muestra en la vista previa. Los nombres técnicos se dejan como en el código. Los archivos `.drawio` de esta carpeta son las fuentes editables con iconos oficiales de Azure.

```mermaid
flowchart LR
    Browser["Navegador<br/>HTML y módulos ES"]
    subgraph SWA["Azure Static Web Apps"]
        Static["Archivos estáticos de web/<br/>cabeceras CSP"]
        Func["Functions administradas<br/>FastAPI (Python 3.11)"]
    end
    Cosmos[("Cosmos DB NoSQL<br/>serverless<br/>products, orders, users")]
    Blob[("Blob Storage<br/>contenedor images")]
    AI["Application Insights<br/>sobre Log Analytics"]
    Probe["Prueba de disponibilidad<br/>(solo prod, 2 ubicaciones)"]
    Mail["Correo de alertas<br/>(solo prod)"]

    Browser -->|"HTML, CSS, JS"| Static
    Browser -->|"/api/* JSON<br/>X-Pdc-Token: Bearer jwt"| Func
    Func -->|"SDK de Cosmos<br/>ETag en stock y productos"| Cosmos
    Func -->|"firma URL SAS<br/>(5 min, https)"| Browser
    Browser -->|"PUT de la imagen con SAS<br/>(regla CORS)"| Blob
    Func -->|"logs JSON por petición<br/>correlation_id"| AI
    Probe -->|"GET /api/health cada 15 min"| Func
    Probe --> AI
    AI -->|"alertas de disponibilidad, errores 5xx y tráfico alto"| Mail
```

## Capas dentro del API

```mermaid
flowchart TB
    Routes["api/routes<br/>solo HTTP"] --> Services["services<br/>catálogo, pedidos, cuentas"]
    Services --> Ports["ports<br/>repositorios, auth, imágenes"]
    Ports --> Cosmos["adapters/cosmos"]
    Ports --> Memory["adapters/memory<br/>(solo local)"]
    Ports --> BlobA["adapters/blob"]
    Ports --> Auth["adapters/local_auth<br/>scrypt + JWT"]
```
