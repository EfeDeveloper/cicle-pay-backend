# AGENTS

Instrucciones portables para asistentes de desarrollo en `cicle-pay-backend`.

## Contexto del producto

Stack, convenciones y dominio viven **solo** en [`openspec/config.yaml`](openspec/config.yaml). Léelo antes de diseñar, implementar, probar o revisar. No copies esas reglas a este archivo ni a los agentes.

## Flujo (OpenSpec manda)

No uses un pipeline fijo de roles. Elige el comando y, dentro de él, solo los roles que el change necesita.

| Intención | Comando |
|-----------|---------|
| Pensar / investigar | `/opsx-explore` |
| Planear un change | `/opsx-propose` |
| Ajustar artifacts existentes | `/opsx-update` |
| Implementar tasks | `/opsx-apply` |
| Volcar deltas a specs main | `/opsx-sync` |
| Cerrar un change hecho | `/opsx-archive` |

## Roles (invocar, no orquestar)

| Rol | Cuándo |
|-----|--------|
| `developer` | Hay tasks de implementación de código, endpoints o schemas. |
| `tech-reviewer` | Al cerrar apply, con pruebas verdes o verificadas. Una vez. |

(Como este backend no contiene UI frontend, no se invocan roles de `ui-designer` ni `qa-tester` con Playwright).

## Layout del repo

`openspec/`, `app/`, `tests/` y los archivos de configuración (`requirements.txt`, `.env`) viven en la **raíz del repositorio**.
