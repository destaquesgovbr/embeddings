# Ambiente Airflow Local — embeddings

> Desenvolva e teste DAGs localmente sem depender do Cloud Composer.

---

## Pré-requisitos

- **Docker** instalado e rodando
- **Astro CLI** instalado:

```bash
# Linux / DevVM
curl -sSL install.astronomer.io | sudo bash -s

# macOS (Homebrew)
brew install astro
```

---

## Quick Start

```bash
cd airflow/

# 1. Criar arquivo de configuração local
cp .env.example .env
# Editar .env com credenciais reais (ver Secret Manager)

# 2. Subir o ambiente
astro dev start --no-browser --settings-file ""

# 3. Acessar Airflow UI
open http://localhost:8080
# Login: admin / admin

# 4. Parar o ambiente
astro dev stop
```

---

## Estrutura de Arquivos

```
airflow/
├── Dockerfile              # Imagem base (Astro Runtime 3.0-14)
├── requirements.txt        # Dependências Python
├── packages.txt            # Dependências OS (vazio)
├── .env.example            # Template de variáveis de ambiente
├── .env                    # Configuração local (gitignored)
├── docker-compose.override.yml  # Serviços extras (opcional)
├── dags -> ../dags         # Symlink para DAGs na raiz do repo
├── plugins/                # Plugins Airflow
├── include/                # Assets compartilhados
└── tests/                  # Testes de DAG
```

A pasta `dags/` é um symlink para `../dags` — as DAGs ficam na raiz do repositório, e o Airflow local as lê automaticamente com hot-reload.

---

## Configurando Connections

As connections são configuradas via variáveis de ambiente no `.env`, seguindo o padrão `AIRFLOW_CONN_{CONN_ID}`:

```bash
# Exemplo
AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://user:pass@host:5432/db
```

Para variáveis Airflow, usar `AIRFLOW_VAR_{VARIABLE_NAME}`.

Consulte o `.env.example` para ver quais connections este projeto precisa.

---

## Comandos Úteis

| Comando | Descrição |
|---------|-----------|
| `astro dev start` | Subir ambiente |
| `astro dev stop` | Parar ambiente |
| `astro dev restart` | Rebuild (após mudar requirements.txt) |
| `astro dev kill` | Parar + remover volumes |
| `astro dev ps` | Ver containers |
| `astro dev logs --follow` | Ver logs em tempo real |
| `astro dev run dags list` | Listar DAGs |
| `astro dev run dags trigger <dag_id>` | Trigger manual |

---

## Diferenças: Local vs Cloud Composer (Produção)

| Aspecto | Local (Astro CLI) | Produção (Cloud Composer) |
|---------|-------------------|--------------------------|
| Airflow version | 3.0-14 (Runtime) | Airflow 3.0.x |
| Executor | Local | Celery / Kubernetes |
| Connections | `.env` / variáveis de ambiente | Secret Manager |
| Deploy | Automático (hot-reload) | GitHub Actions → GCS bucket |
| Plugins | Symlink / volume mount | `gsutil rsync` para bucket |
| Escala | Single worker | Multi-worker |

---

## Plugins e Volume Mounts

Symlinks não funcionam dentro de containers Docker. Para montar plugins locais, use `docker-compose.override.yml`:

```yaml
services:
  scheduler:
    volumes:
      - ../src/meu_plugin:/usr/local/airflow/plugins/meu_plugin:ro
      - ../dags:/usr/local/airflow/dags:ro
  dag-processor:
    volumes:
      - ../src/meu_plugin:/usr/local/airflow/plugins/meu_plugin:ro
      - ../dags:/usr/local/airflow/dags:ro
  api-server:
    volumes:
      - ../src/meu_plugin:/usr/local/airflow/plugins/meu_plugin:ro
      - ../dags:/usr/local/airflow/dags:ro
  triggerer:
    volumes:
      - ../src/meu_plugin:/usr/local/airflow/plugins/meu_plugin:ro
      - ../dags:/usr/local/airflow/dags:ro
```

---

## Gestão via Copier (airflow-dgb)

Este diretório `airflow/` foi gerado pelo template **[airflow-dgb](https://github.com/destaquesgovbr/airflow-dgb)** usando [Copier](https://copier.readthedocs.io/).

### O que é o Copier?

Copier é uma ferramenta que gera projetos a partir de templates e permite atualizá-los quando o template evolui. O arquivo `.copier-answers.yml` na raiz do repo registra a versão do template e as respostas usadas na geração.

### Atualizando o template

Quando o `airflow-dgb` receber atualizações (ex: nova versão do Astro Runtime), execute na raiz do repo:

```bash
copier update
```

O Copier aplica as mudanças do template preservando suas customizações locais via three-way merge. Em caso de conflito, ele cria marcadores como no git merge.

### Arquivos geridos pelo template vs. customizáveis

| Arquivo | Gerido pelo template? | Notas |
|---------|----------------------|-------|
| `Dockerfile` | Sim | Atualizado pelo Copier |
| `.astro/config.yaml` | Sim | Atualizado pelo Copier |
| `packages.txt` | Sim | Atualizado pelo Copier |
| `.dockerignore` | Sim | Atualizado pelo Copier |
| `.airflowignore` | Sim | Atualizado pelo Copier |
| `CLAUDE.md` | Sim | Atualizado pelo Copier |
| `README.md` | Sim | Atualizado pelo Copier |
| **`requirements.txt`** | Parcial | Gerado na criação, merge em updates |
| **`.env.example`** | Parcial | Gerado na criação, merge em updates |
| **`docker-compose.override.yml`** | Nunca | Sempre customizado, nunca sobrescrito |
| **`.env`** | Nunca | Gitignored, local apenas |

### Instalando o Copier

```bash
pipx install copier
# ou
pip install copier
```

---

## Troubleshooting

### `ModuleNotFoundError` em DAGs

O plugin não está montado no container. Verifique `docker-compose.override.yml` e confirme que os volume mounts estão corretos para todos os serviços (scheduler, dag-processor, api-server, triggerer).

### `astro dev start` falha com erro de porta

Outra instância pode estar rodando. Execute `astro dev kill` e tente novamente.

### DAGs não aparecem na UI

1. Verifique se o symlink `dags -> ../dags` existe
2. Verifique `.airflowignore` — o arquivo da DAG pode estar sendo ignorado
3. Verifique logs: `astro dev logs scheduler`

### Erro de conexão com PostgreSQL

Verifique se o `.env` tem a connection string correta e se o IP do Cloud SQL aceita conexões do seu IP.
