# CI/CD pipeline

Mermaid source: GitHub renders it in the preview.

```mermaid
flowchart TD
    PR["Pull request"] --> Lint["lint<br/>ruff, terraform fmt"]
    Lint --> Sec["security<br/>Checkov, CodeQL"]
    Lint --> TfPlan["terraform<br/>dev and prod plan (read-only OIDC)"]
    Sec --> Test["test<br/>pytest, minimum coverage 70 %"]
    Test --> Build["build<br/>packages api/ and web/"]

    Push["Push to dev or main<br/>(PR merge)"] --> B["build<br/>api and web artifacts"]
    B --> Gate{"Branch"}
    Gate -->|"dev: environment dev, no approval"| Apply
    Gate -->|"main: environment prod, requires approval"| Apply
    Apply["deploy: OIDC login<br/>terraform apply"] --> Seeds["seed products<br/>and the admin"]
    Seeds --> Upload["upload web and api to SWA"]
    Upload --> Smoke["smoke: wait for /api/health<br/>Bruno collection"]
    Smoke -->|"main only"| Release["release: release-vN artifact (90 days)<br/>tag vN"]
```

`N` is the run number of `deploy.yml`. The `ci` workflow runs on the pull request and `deploy` runs on merge: the deployment does not repeat lint or tests.
