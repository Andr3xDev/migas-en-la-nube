# Documentación de Migas en la Nube

Estos son los entregables de diseño del proyecto del curso; el equipo los renderiza a PDF.

## Entregables de la rúbrica

| Entregable | Archivo o ubicación |
|------------|---------------------|
| HLD | [hld.md](hld.md) |
| ADRs | [adr/](adr/README.md) (5 decisiones) |
| Diagramas | [diagrams/](diagrams/) (contexto, arquitectura cloud, red y seguridad, pipeline, y rollback) |
| Estimación de costos | [hld.md](hld.md) sección 8, más la exportación de la calculadora en [costs/azure.xlsx](costs/azure.xlsx) |
| Diseño de despliegue | [deployment.md](deployment.md) |
| Código en GitHub | [../README.md](../README.md) |
| Prueba de carga | [hld.md](hld.md) sección 6 y [../load/README.md](../load/README.md) |
| Presentación | Externa (a cargo del equipo) |

## Orden sugerido para el PDF

1. [hld.md](hld.md)
2. ADRs, en orden: [0001](adr/0001-serverless-static-web-apps.md), [0002](adr/0002-cosmos-db-serverless.md), [0003](adr/0003-own-jwt-authentication.md), [0004](adr/0004-terraform-github-actions-oidc.md), [0005](adr/0005-python-fastapi-on-functions.md)
3. [deployment.md](deployment.md)
4. Diagramas: [contexto](diagrams/context.drawio), [arquitectura](diagrams/architecture.drawio), [red y seguridad](diagrams/network-security.drawio), [pipeline](diagrams/pipeline.drawio), [rollback](diagrams/rollback.drawio)

## Diagramas

- Los archivos `.drawio` (en `diagrams/`) son las fuentes editables, con iconos de Azure. Cada uno se exporta como PNG con el mismo nombre (`diagrams/*.png`) y esos PNG son los que usan [hld.md](hld.md), [deployment.md](deployment.md) y el [README](../README.md).