# Network and security

Zones, flows and identities. There is no virtual network: services are exposed over HTTPS and protected with keys in the app configuration and with OIDC identities in the pipeline.

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        User["Browser<br/>customer or admin"]
    end

    subgraph GH["GitHub: repository Andr3xDev/migas-en-la-nube"]
        Actions["GitHub Actions<br/>environments dev and prod"]
    end

    subgraph Azure["Azure subscription"]
        subgraph RGProd["rg-pdc-prod"]
            SwaProd["Static Web Apps Standard<br/>Managed Functions"]
            CosmosProd[("Cosmos DB")]
            BlobProd[("Blob Storage images")]
            AiProd["Application Insights"]
            Alerts["Alerts and availability test"]
        end

        subgraph RGDev["rg-pdc-dev"]
            SwaDev["Static Web Apps Free<br/>Managed Functions"]
            CosmosDev[("Cosmos DB")]
            BlobDev[("Blob Storage images")]
            AiDev["Application Insights"]
        end

        subgraph RGTF["rg-pdc-tfstate"]
            IdPlan["id-pdc-ci-plan<br/>Reader on rg-pdc-dev and rg-pdc-prod<br/>Blob Data Reader on the state account"]
            IdDev["id-pdc-deploy-dev<br/>Contributor on rg-pdc-dev<br/>Blob Data Contributor on tfstate-dev"]
            IdProd["id-pdc-deploy-prod<br/>Contributor on rg-pdc-prod<br/>Blob Data Contributor on tfstate-prod"]
            State[("Terraform state storage<br/>no shared keys or anonymous access")]
        end
    end

    Mail["Alert email"]

    User -->|"HTTPS"| SwaProd
    User -->|"PUT image with SAS<br/>(5 min, https)"| BlobProd
    User -->|"GET images (public read)"| BlobProd
    SwaProd -->|"Cosmos key<br/>(app setting)"| CosmosProd
    SwaProd -->|"Storage key, signs the SAS<br/>(app setting)"| BlobProd
    SwaProd -->|"JSON logs"| AiProd
    AiProd --> Alerts
    Alerts -->|"email"| Mail
    SwaDev --> CosmosDev
    SwaDev --> BlobDev
    SwaDev --> AiDev

    Actions -->|"OIDC, subject pull_request"| IdPlan
    Actions -->|"OIDC, subject environment:dev"| IdDev
    Actions -->|"OIDC, subject environment:prod"| IdProd
    IdDev -->|"terraform apply and uploads the artifact"| SwaDev
    IdProd -->|"terraform apply and uploads the artifact"| SwaProd
    IdPlan -->|"reads the state"| State
    IdDev -->|"dev state"| State
    IdProd -->|"prod state"| State
```

The identities and their roles are in `infra/bootstrap/identities.tf` and `infra/bootstrap/roles.tf`. GitHub issues an OIDC token and Microsoft Entra ID exchanges it for access to the identity whose subject matches. Dev has no alerts or availability test.
