# Pipeline de CI/CD

Fuente Mermaid: GitHub la muestra en la vista previa.

```mermaid
flowchart TD
    PR["Pull request"] --> Lint["lint<br/>ruff, terraform fmt"]
    Lint --> Sec["security<br/>Checkov, CodeQL"]
    Lint --> TfPlan["terraform<br/>plan de dev y prod (OIDC de solo lectura)"]
    Sec --> Test["test<br/>pytest, cobertura mínima 70 %"]
    Test --> Build["build<br/>empaqueta api/ y web/"]

    Push["Push a dev o main<br/>(merge del PR)"] --> B["build<br/>artefactos api y web"]
    B --> Gate{"Rama"}
    Gate -->|"dev: environment dev, sin aprobación"| Apply
    Gate -->|"main: environment prod, requiere aprobación"| Apply
    Apply["deploy: login OIDC<br/>terraform apply"] --> Seeds["seed de productos<br/>y del administrador"]
    Seeds --> Upload["sube web y api a SWA"]
    Upload --> Smoke["smoke: espera /api/health<br/>colección Bruno"]
    Smoke -->|"solo main"| Release["release: artefacto release-vN (90 días)<br/>etiqueta vN"]
```

`N` es el número de ejecución de `deploy.yml`. El workflow `ci` corre en el pull request y `deploy` corre al hacer merge: el despliegue no repite lint ni pruebas.
