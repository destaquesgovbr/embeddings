# Airflow Local Dev (Astro CLI)

## Quick Start

```bash
cd airflow/

# Criar .env a partir do template
cp .env.example .env
# Editar .env com credenciais reais

# Subir (sem TTY, usa .env)
astro dev start --no-browser --settings-file ""

# Com TTY (Claude Code)
script -q /dev/null astro dev start --no-browser --wait 5m

# Airflow UI
open http://localhost:8080

# Parar
astro dev stop
```

## Versões

| Componente | Versão |
|-----------|--------|
| Astro Runtime | 3.0-14 |
| Docker image | `astrocrpublic.azurecr.io/runtime:3.0-14` |

## Estrutura

```
airflow/
├── Dockerfile              # FROM astrocrpublic.azurecr.io/runtime:3.0-14
├── requirements.txt        # Python deps
├── packages.txt            # OS deps (vazio)
├── .env                    # Connections + variables (gitignored)
├── .env.example            # Template das env vars
├── .airflowignore          # Ignora __pycache__, .git, tests
├── .dockerignore           # Ignora .git, .env, logs
├── dags -> ../dags         # Symlink para dags/ na raiz
├── plugins/                # Plugins custom
├── include/                # Assets compartilhados (vazio)
└── tests/                  # Testes DAG
```

## Comandos úteis

```bash
astro dev ps                    # Ver containers
astro dev logs --follow         # Logs
astro dev run dags list         # Listar DAGs
astro dev restart               # Rebuild após mudar requirements.txt
astro dev kill                  # Parar + remover volumes
```

## TTY no Claude Code

O `astro dev start` precisa de TTY para importar `airflow_settings.yaml`. No Claude Code:

```bash
script -q /dev/null astro dev start --no-browser --wait 5m
```

## Template

Este diretório é gerido pelo template [airflow-dgb](https://github.com/destaquesgovbr/airflow-dgb).
Para atualizar: `copier update` na raiz do repo.
