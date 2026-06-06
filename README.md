# Mosaico Backend

## Run with UV

```bash
uv sync
uv run flask --app main run
```

## Run with Python

```bash
python -m venv .venv
source .venv/bin/activate
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
