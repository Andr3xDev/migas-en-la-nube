# Documentación de Pan de la Casa

Estos son los entregables de diseño del proyecto del curso; el equipo los renderiza a PDF.

## Entregables de la rúbrica

| Entregable | Archivo o ubicación |
|------------|---------------------|
| HLD | [hld.md](hld.md) |
| ADRs | [adr/](adr/README.md) (5 decisiones) |
| Diagramas | [diagramas/](diagramas/) (contexto, arquitectura cloud, red y seguridad, pipeline, y rollback) |
| Estimación de costos | [hld.md](hld.md) sección 8, más la calculadora y el Excel (externos, a cargo del equipo) |
| Diseño de despliegue | [despliegue.md](despliegue.md) |
| Código en GitHub | [../README.md](../README.md) |
| Presentación | Externa (a cargo del equipo) |

## Orden sugerido para el PDF

1. [hld.md](hld.md)
2. ADRs, en orden: [0001](adr/0001-serverless-static-web-apps.md), [0002](adr/0002-cosmos-db-serverless.md), [0003](adr/0003-own-jwt-authentication.md), [0004](adr/0004-terraform-github-actions-oidc.md), [0005](adr/0005-python-fastapi-on-functions.md)
3. [despliegue.md](despliegue.md)
4. Diagramas: [contexto](diagramas/contexto.md), [arquitectura](diagramas/architecture.md), [red y seguridad](diagramas/red-seguridad.md), [pipeline](diagramas/pipeline.md), [rollback](diagramas/rollback.md)

## Diagramas

- Los archivos `.drawio` (en `diagramas/`) son las fuentes editables, con iconos de Azure. Exporta el PNG desde draw.io.
- Los bloques Mermaid de los archivos `.md` se renderizan en GitHub y en la mayoría de herramientas de Markdown a PDF que soporten Mermaid.