# Context (C4 level 1)

Who uses Migas en la Nube and which external systems it relates to. Mermaid source: GitHub renders it in the preview.

```mermaid
flowchart TB
    guest["Guest customer<br/>[Person]<br/>Browses the catalog and orders without an account"]
    customer["Registered customer<br/>[Person]<br/>Orders, sees their history and favorites"]
    admin["Admin<br/>[Person]<br/>Manages products, images and orders"]

    system["Migas en la Nube<br/>[Software system]<br/>Web store to order and pick up in store"]

    azure["Microsoft Azure<br/>[External system]<br/>Platform that hosts the system"]
    github["GitHub<br/>[External system]<br/>Repository and GitHub Actions"]
    mail["Email<br/>[External system]<br/>Receives the prod and budget alerts"]

    guest -->|"Browses and orders over HTTPS"| system
    customer -->|"Orders and checks their account over HTTPS"| system
    admin -->|"Administers over HTTPS"| system
    system -->|"Runs on"| azure
    github -->|"Deploys with Terraform and OIDC"| azure
    azure -->|"Sends alerts"| mail
```

The admin uses the same website as customers, with a different role. Email alerts exist only in production, and the budget notice is sent by the Azure subscription.
