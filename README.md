# Calculator API Server

A lightweight, high-performance FastAPI server and modern web application for arithmetic and scientific calculations.

## Features

- **REST API Endpoints**:
  - `POST /api/calculate`: Evaluate math expressions or perform specific operations.
  - `GET /api/calculate`: Quick expression evaluation via query parameter.
  - `GET /api/history`: Retrieve recent calculation history.
  - `DELETE /api/history`: Clear calculation history.
  - `GET /health`: Server health check.
- **Embedded Interactive Web UI**: Modern dark-mode glassmorphic interface accessible directly at `http://localhost:7500/`.
- **Interactive OpenAPI Documentation**: Built-in Swagger UI available at `http://localhost:7500/docs`.
- **Safe Evaluation**: Secure expression parsing using Python's Abstract Syntax Tree (`ast`) module (avoids dangerous `eval`).

---

## Quick Start

### 1. Run the Server

```bash
python main.py
```
Or using Uvicorn directly:
```bash
uvicorn main:app --reload --port 7500
```

### 2. Access the Application

- **Web Interface**: [http://localhost:7500/](http://localhost:7500/)
- **API Documentation**: [http://localhost:7500/docs](http://localhost:7500/docs)

---

## API Usage Examples

### Evaluate Expression (POST)

```bash
curl -X POST "http://localhost:7500/api/calculate" \
     -H "Content-Type: application/json" \
     -d '{"expression": "sqrt(16) + 2^10"}'
```

**Response:**
```json
{
  "expression": "sqrt(16) + 2^10",
  "result": 1028,
  "timestamp": 1728211200.0
}
```

### Perform Standard Operation (POST)

```bash
curl -X POST "http://localhost:7500/api/calculate" \
     -H "Content-Type: application/json" \
     -d '{"operation": "multiply", "a": 12, "b": 8}'
```

**Response:**
```json
{
  "expression": "12 * 8",
  "result": 96,
  "timestamp": 1728211200.0
}
```

### Quick GET Request

```bash
curl "http://localhost:7500/api/calculate?expr=15*4-10"
```
