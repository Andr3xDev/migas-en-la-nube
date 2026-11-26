# Contexto (C4 nivel 1)

Quién usa Migas en la Nube y con qué sistemas externos se relaciona. Fuente Mermaid: GitHub la muestra en la vista previa.

```mermaid
flowchart TB
    guest["Cliente invitado<br/>[Persona]<br/>Consulta el catálogo y pide sin cuenta"]
    customer["Cliente registrado<br/>[Persona]<br/>Pide, ve su historial y sus favoritos"]
    admin["Administrador<br/>[Persona]<br/>Gestiona productos, imágenes y pedidos"]

    system["Migas en la Nube<br/>[Sistema de software]<br/>Tienda web para pedir y recoger en tienda"]

    azure["Microsoft Azure<br/>[Sistema externo]<br/>Plataforma que aloja el sistema"]
    github["GitHub<br/>[Sistema externo]<br/>Repositorio y GitHub Actions"]
    mail["Correo electrónico<br/>[Sistema externo]<br/>Recibe las alertas de prod y del presupuesto"]

    guest -->|"Consulta y pide por HTTPS"| system
    customer -->|"Pide y consulta su cuenta por HTTPS"| system
    admin -->|"Administra por HTTPS"| system
    system -->|"Se ejecuta en"| azure
    github -->|"Despliega con Terraform y OIDC"| azure
    azure -->|"Envía alertas"| mail
```

El administrador usa el mismo sitio web que los clientes, con un rol distinto. Las alertas por correo solo existen en producción, y el aviso de presupuesto lo envía la suscripción de Azure.
