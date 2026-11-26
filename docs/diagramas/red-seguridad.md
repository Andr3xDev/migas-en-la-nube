# Red y seguridad

Zonas, flujos e identidades. No hay red virtual: los servicios se exponen por HTTPS y se protegen con llaves en la configuración de la app y con identidades OIDC en el pipeline.

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        User["Navegador<br/>cliente o administrador"]
    end

    subgraph GH["GitHub: repositorio Andr3xDev/migas-en-la-nube"]
        Actions["GitHub Actions<br/>environments dev y prod"]
    end

    subgraph Azure["Suscripción de Azure"]
        subgraph RGProd["rg-pdc-prod"]
            SwaProd["Static Web Apps Standard<br/>Functions administradas"]
            CosmosProd[("Cosmos DB")]
            BlobProd[("Blob Storage images")]
            AiProd["Application Insights"]
            Alerts["Alertas y prueba de disponibilidad"]
        end

        subgraph RGDev["rg-pdc-dev"]
            SwaDev["Static Web Apps Free<br/>Functions administradas"]
            CosmosDev[("Cosmos DB")]
            BlobDev[("Blob Storage images")]
            AiDev["Application Insights"]
        end

        subgraph RGTF["rg-pdc-tfstate"]
            IdPlan["id-pdc-ci-plan<br/>Reader en rg-pdc-dev y rg-pdc-prod<br/>Blob Data Reader en la cuenta del estado"]
            IdDev["id-pdc-deploy-dev<br/>Contributor en rg-pdc-dev<br/>Blob Data Contributor en tfstate-dev"]
            IdProd["id-pdc-deploy-prod<br/>Contributor en rg-pdc-prod<br/>Blob Data Contributor en tfstate-prod"]
            State[("Storage del estado de Terraform<br/>sin llaves compartidas ni acceso anónimo")]
        end
    end

    Mail["Correo de alertas"]

    User -->|"HTTPS"| SwaProd
    User -->|"PUT de la imagen con SAS<br/>(5 min, https)"| BlobProd
    User -->|"GET de imágenes (lectura pública)"| BlobProd
    SwaProd -->|"llave de Cosmos<br/>(app setting)"| CosmosProd
    SwaProd -->|"llave de Storage, firma el SAS<br/>(app setting)"| BlobProd
    SwaProd -->|"logs JSON"| AiProd
    AiProd --> Alerts
    Alerts -->|"correo"| Mail
    SwaDev --> CosmosDev
    SwaDev --> BlobDev
    SwaDev --> AiDev

    Actions -->|"OIDC, subject pull_request"| IdPlan
    Actions -->|"OIDC, subject environment:dev"| IdDev
    Actions -->|"OIDC, subject environment:prod"| IdProd
    IdDev -->|"terraform apply y sube el artefacto"| SwaDev
    IdProd -->|"terraform apply y sube el artefacto"| SwaProd
    IdPlan -->|"lee el estado"| State
    IdDev -->|"estado de dev"| State
    IdProd -->|"estado de prod"| State
```

Las identidades y sus roles están en `infra/bootstrap/identities.tf` y `infra/bootstrap/roles.tf`. GitHub entrega un token OIDC y Microsoft Entra ID lo cambia por acceso a la identidad cuyo subject coincide. Dev no tiene alertas ni prueba de disponibilidad.
