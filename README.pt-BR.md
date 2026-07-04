# Mosaico Backend

[English](README.md)

Mosaico é um sistema de cofre para armazenar e gerenciar senhas dentro de imagens. Este backend fornece uma API RESTful construída com Flask para autenticação de usuários, gerenciamento de cofres e operações de arquivos.

## Documentação da API:

A documentação interativa Swagger/OpenAPI está disponível em `http://localhost:5000/docs` (ou `http://localhost:5000/openapi/swagger`) quando o servidor estiver rodando.

## Executar com UV

```bash
uv sync
uv run flask --app main run

# Linux / Mac:
source .venv/bin/activate

# Windows (Prompt de Comando):
.venv\Scripts\activate.bat

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
flask --app main run
```

## Executando testes

### UV

```bash
uv run pytest
```

### Python

```bash
python -m pytest
```
