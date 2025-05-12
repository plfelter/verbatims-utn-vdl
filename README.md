# verbatims-utn-vdl

A web app to display verbatims written on https://www.registre-dematerialise.fr/6058/.

Reach it online at http://verbatims-utn-vdl.webpil.ovh.

## Database save strategy

```mermaid
---
config:
  theme: neutral
  layout: elk
  elk:
    mergeEdges: true
    nodePlacementStrategy: SIMPLE
---
flowchart TD
    subgraph Server["Ubuntu server"]
        Container
        Ubuntu_db["Production database"]
        Ubuntu_backup_db["Database backup"]
    end
    subgraph Container["Docker container"]
        Container_db["Production database"]
        Production_app["Web app in production"]
    end
    subgraph DevPlatform["Development computer"]
        Dev_app["Web app in development"]
        Dev_backup_db["Database backup"]
    end
    subgraph FTP["FTP server"]
        Freebox_db["Database replica"]
    end
    subgraph Freebox["Freebox server"]
        FTP
    end
    Ubuntu_db -- dumps copies periodically --> Freebox_db
    Dev_app -- deploys to --> Container
    Container_db -- copy on app upgrade --> Ubuntu_backup_db
    Ubuntu_backup_db -- copy on app upgrade --> Dev_backup_db
    Production_app -- edits --> Container_db
    Ubuntu_db <-- Docker bind mount --> Container_db
```