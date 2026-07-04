# Mosaico Backend

[Português (BR)](README.pt-BR.md)

Mosaico is a vault system for storing and managing passwords within images. This backend provides a RESTful API built with Flask for user authentication, vault management, and file operations.

## API Documentation:

Interactive Swagger/OpenAPI docs are available at `http://localhost:5000/docs` (or `http://localhost:5000/openapi/swagger`) when the server is running.

## Run with UV

```bash
uv sync
uv run flask --app main run
```

## Run with Python

```bash
python -m venv .venv

# Linux / Mac:
source .venv/bin/activate

# Windows (Command Prompt):
.venv\Scripts\activate.bat

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
flask --app main run
```

## Running tests

### UV

```bash
uv run pytest
```

### Python

```bash
python -m pytest
```
