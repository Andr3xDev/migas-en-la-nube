# Architecture

Mermaid source: GitHub renders it in the preview. Technical names are kept as in the code. The `.drawio` files in this folder are the editable sources with official Azure icons.

```mermaid
flowchart LR
    Browser["Browser<br/>HTML and ES modules"]
    subgraph SWA["Azure Static Web Apps"]
        Static["Static files from web/<br/>CSP headers"]
        Func["Managed Functions<br/>FastAPI (Python 3.11)"]
    end
    Cosmos[("Cosmos DB NoSQL<br/>serverless<br/>products, orders, users")]
    Blob[("Blob Storage<br/>images container")]
    AI["Application Insights<br/>on Log Analytics"]
    Probe["Availability test<br/>(prod only, 2 locations)"]
    Mail["Alert email<br/>(prod only)"]

    Browser -->|"HTML, CSS, JS"| Static
    Browser -->|"/api/* JSON<br/>X-Pdc-Token: Bearer jwt"| Func
    Func -->|"Cosmos SDK<br/>ETag on stock and products"| Cosmos
    Func -->|"signs SAS URL<br/>(5 min, https)"| Browser
    Browser -->|"PUT image with SAS<br/>(CORS rule)"| Blob
    Func -->|"JSON logs per request<br/>correlation_id"| AI
    Probe -->|"GET /api/health every 15 min"| Func
    Probe --> AI
    AI -->|"availability, 5xx error and high traffic alerts"| Mail
```

## Layers inside the API

```mermaid
flowchart TB
    Routes["api/routes<br/>HTTP only"] --> Services["services<br/>catalog, orders, accounts"]
    Services --> Ports["ports<br/>repositories, auth, images"]
    Ports --> Cosmos["adapters/cosmos"]
    Ports --> Memory["adapters/memory<br/>(local only)"]
    Ports --> BlobA["adapters/blob"]
    Ports --> Auth["adapters/local_auth<br/>scrypt + JWT"]
```
