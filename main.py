from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Union
import math
import ast
import operator
import time
# pyrefly: ignore [missing-import]
from recovery_sdk.integrations.fastapi import RecoveryMiddleware


app = FastAPI(
    title="Calculator API Server",
    description="A small, modern REST API server and interactive Web UI for arithmetic and scientific calculations.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    RecoveryMiddleware,
    project_id="proj_7b6fa9e0",        # your project ID from the platform
    environment="production",
    api_url="http://127.0.0.1:8000" # your Overmend API
)

# In-memory history store
history_db: List[dict] = []

# Safe AST Math Evaluator
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

ALLOWED_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "factorial": math.factorial,
    "exp": math.exp,
}

ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value}")
    elif isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Name):
        if node.id in ALLOWED_CONSTANTS:
            return ALLOWED_CONSTANTS[node.id]
        raise ValueError(f"Unknown symbol: '{node.id}'")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator")
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        # if op_type == ast.Div and right == 0:
            # raise ZeroDivisionError("Division by zero")
        return ALLOWED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported operator")
        operand = safe_eval(node.operand)
        return ALLOWED_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")
        func_name = node.func.id
        if func_name not in ALLOWED_FUNCTIONS:
            raise ValueError(f"Unsupported function: '{func_name}'")
        args = [safe_eval(arg) for arg in node.args]
        return ALLOWED_FUNCTIONS[func_name](*args)
    else:
        raise ValueError("Invalid mathematical expression")

def evaluate_expression(expr_str: str) -> Union[int, float]:
    cleaned = expr_str.strip().replace('^', '**').replace('×', '*').replace('÷', '/')
    if not cleaned:
        raise ValueError("Expression cannot be empty")
    tree = ast.parse(cleaned, mode='eval')
    result = safe_eval(tree)
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return round(result, 10) if isinstance(result, float) else result

# Request & Response Models
class CalculationRequest(BaseModel):
    expression: Optional[str] = Field(None, json_schema_extra={"example": "12 * (5 + 3)"}, description="Mathematical string expression")
    operation: Optional[str] = Field(None, json_schema_extra={"example": "add"}, description="Operation: add, subtract, multiply, divide, power, sqrt")
    a: Optional[float] = Field(None, json_schema_extra={"example": 10}, description="First operand for operation")
    b: Optional[float] = Field(None, json_schema_extra={"example": 5}, description="Second operand for operation")

class CalculationResponse(BaseModel):
    expression: str
    result: Union[int, float]
    timestamp: float

# Routes
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "calculator-server"}

@app.post("/api/calculate", response_model=CalculationResponse)
def calculate(req: CalculationRequest):
    try:
        if req.expression:
            expr = req.expression
            res = evaluate_expression(expr)
        elif req.operation:
            op = req.operation.lower()
            if op in ["add", "+"]:
                if req.a is None or req.b is None:
                    raise HTTPException(status_code=400, detail="Operands 'a' and 'b' are required")
                expr = f"{req.a} + {req.b}"
                res = req.a + req.b
            elif op in ["subtract", "-"]:
                if req.a is None or req.b is None:
                    raise HTTPException(status_code=400, detail="Operands 'a' and 'b' are required")
                expr = f"{req.a} - {req.b}"
                res = req.a - req.b
            elif op in ["multiply", "*"]:
                if req.a is None or req.b is None:
                    raise HTTPException(status_code=400, detail="Operands 'a' and 'b' are required")
                expr = f"{req.a} * {req.b}"
                res = req.a * req.b
            elif op in ["divide", "/"]:
                if req.a is None or req.b is None:
                    raise HTTPException(status_code=400, detail="Operands 'a' and 'b' are required")
                if req.b == 0:
                    raise HTTPException(status_code=400, detail="Division by zero")
                expr = f"{req.a} / {req.b}"
                res = req.a / req.b
            elif op in ["power", "^"]:
                if req.a is None or req.b is None:
                    raise HTTPException(status_code=400, detail="Operands 'a' and 'b' are required")
                expr = f"{req.a} ^ {req.b}"
                res = req.a ** req.b
            elif op in ["sqrt"]:
                if req.a is None:
                    raise HTTPException(status_code=400, detail="Operand 'a' is required")
                if req.a < 0:
                    raise HTTPException(status_code=400, detail="Cannot calculate square root of negative number")
                expr = f"sqrt({req.a})"
                res = math.sqrt(req.a)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported operation '{op}'")
        else:
            raise HTTPException(status_code=400, detail="Provide either 'expression' or 'operation' with operands")

        if isinstance(res, float) and res.is_integer():
            res = int(res)
        elif isinstance(res, float):
            res = round(res, 10)

        record = {
            "expression": expr,
            "result": res,
            "timestamp": time.time()
        }
        history_db.append(record)
        if len(history_db) > 50:
            history_db.pop(0)

        return record

    except ZeroDivisionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")

@app.get("/divide")
def divide(a: float, b: float):
    # Do NOT catch ZeroDivisionError with try/except!
    # Let Python raise ZeroDivisionError naturally when b=0 so RecoveryMiddleware captures the stacktrace.
    return {"result": a / b}

@app.get("/api/calculate", response_model=CalculationResponse)
def calculate_get(expr: str = Query(..., description="Math expression, e.g. 5*10+2")):
    try:
        res = evaluate_expression(expr)
        record = {
            "expression": expr,
            "result": res,
            "timestamp": time.time()
        }
        history_db.append(record)
        if len(history_db) > 50:
            history_db.pop(0)
        return record
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/history")
def get_history():
    return {"history": list(reversed(history_db))}

@app.delete("/api/history")
def clear_history():
    history_db.clear()
    return {"message": "History cleared"}

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calculator Server App</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --display-bg: rgba(15, 23, 42, 0.8);
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --op-bg: #334155;
            --op-hover: #475569;
            --num-bg: #1e293b;
            --num-hover: #334155;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
            user-select: none;
        }

        body {
            background: radial-gradient(circle at top left, #1e1b4b, #0f172a, #020617);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: var(--text);
        }

        .calculator-container {
            display: grid;
            grid-template-columns: 360px 300px;
            gap: 20px;
            max-width: 700px;
            width: 100%;
        }

        @media (max-width: 700px) {
            .calculator-container {
                grid-template-columns: 1fr;
            }
        }

        .calc-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 24px;
            box-shadow: var(--shadow);
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-dim);
            letter-spacing: 0.5px;
        }

        .badge {
            background: rgba(99, 102, 241, 0.2);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.4);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .display {
            background: var(--display-bg);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            min-height: 90px;
            justify-content: space-between;
            word-break: break-all;
        }

        .display-expr {
            font-size: 0.95rem;
            color: var(--text-dim);
            min-height: 1.2rem;
        }

        .display-main {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text);
            transition: all 0.15s ease;
        }

        .keypad {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }

        button.btn {
            background: var(--num-bg);
            border: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text);
            font-size: 1.25rem;
            font-weight: 500;
            padding: 16px;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        button.btn:hover {
            background: var(--num-hover);
            transform: translateY(-2px);
        }

        button.btn:active {
            transform: translateY(1px);
        }

        button.btn-op {
            background: var(--op-bg);
            color: #c7d2fe;
            font-weight: 600;
        }

        button.btn-op:hover {
            background: var(--op-hover);
        }

        button.btn-accent {
            background: var(--accent);
            color: white;
            font-weight: 700;
        }

        button.btn-accent:hover {
            background: var(--accent-hover);
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        }

        button.btn-fn {
            background: rgba(255, 255, 255, 0.05);
            font-size: 0.95rem;
            color: var(--text-dim);
        }

        .history-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 24px;
            box-shadow: var(--shadow);
            display: flex;
            flex-direction: column;
            max-height: 480px;
        }

        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .history-header h2 {
            font-size: 1rem;
            color: var(--text);
            font-weight: 600;
        }

        .clear-btn {
            background: transparent;
            border: none;
            color: #ef4444;
            font-size: 0.85rem;
            cursor: pointer;
            font-weight: 500;
        }

        .clear-btn:hover {
            text-decoration: underline;
        }

        .history-list {
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            flex: 1;
            padding-right: 4px;
        }

        .history-item {
            background: rgba(15, 23, 42, 0.5);
            border-radius: 12px;
            padding: 10px 14px;
            cursor: pointer;
            transition: background 0.2s;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .history-item:hover {
            background: rgba(99, 102, 241, 0.15);
        }

        .history-expr {
            font-size: 0.8rem;
            color: var(--text-dim);
        }

        .history-res {
            font-size: 1.1rem;
            font-weight: 600;
            color: #a5b4fc;
            text-align: right;
        }

        .empty-history {
            color: var(--text-dim);
            font-size: 0.85rem;
            text-align: center;
            margin-top: 40px;
        }

        .docs-link {
            text-align: center;
            margin-top: 8px;
            font-size: 0.8rem;
        }

        .docs-link a {
            color: #818cf8;
            text-decoration: none;
        }

        .docs-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>

<div class="calculator-container">
    <div class="calc-card">
        <div class="header">
            <h1>CALCULATOR SERVER</h1>
            <span class="badge">REST API</span>
        </div>

        <div class="display">
            <div class="display-expr" id="displayExpr"></div>
            <div class="display-main" id="displayMain">0</div>
        </div>

        <div class="keypad">
            <button class="btn btn-fn" onclick="clearAll()">AC</button>
            <button class="btn btn-fn" onclick="appendFn('sqrt(')">√</button>
            <button class="btn btn-fn" onclick="append('^')">^</button>
            <button class="btn btn-op" onclick="append('÷')">÷</button>

            <button class="btn" onclick="append('7')">7</button>
            <button class="btn" onclick="append('8')">8</button>
            <button class="btn" onclick="append('9')">9</button>
            <button class="btn btn-op" onclick="append('×')">×</button>

            <button class="btn" onclick="append('4')">4</button>
            <button class="btn" onclick="append('5')">5</button>
            <button class="btn" onclick="append('6')">6</button>
            <button class="btn btn-op" onclick="append('-')">-</button>

            <button class="btn" onclick="append('1')">1</button>
            <button class="btn" onclick="append('2')">2</button>
            <button class="btn" onclick="append('3')">3</button>
            <button class="btn btn-op" onclick="append('+')">+</button>

            <button class="btn" onclick="append('0')">0</button>
            <button class="btn" onclick="append('.')">.</button>
            <button class="btn btn-fn" onclick="backspace()">⌫</button>
            <button class="btn btn-accent" onclick="calculate()">=</button>
        </div>

        <div class="docs-link">
            Interactive API Docs: <a href="/docs" target="_blank">/docs</a>
        </div>
    </div>

    <div class="history-card">
        <div class="history-header">
            <h2>History</h2>
            <button class="clear-btn" onclick="clearHistory()">Clear</button>
        </div>
        <div class="history-list" id="historyList">
            <div class="empty-history">No calculations yet</div>
        </div>
    </div>
</div>

<script>
    let currentInput = "0";
    let lastExpr = "";

    const displayMain = document.getElementById('displayMain');
    const displayExpr = document.getElementById('displayExpr');
    const historyList = document.getElementById('historyList');

    function updateDisplay() {
        displayMain.textContent = currentInput;
        displayExpr.textContent = lastExpr;
    }

    function append(char) {
        if (currentInput === "0" && char !== ".") {
            currentInput = char;
        } else {
            currentInput += char;
        }
        updateDisplay();
    }

    function appendFn(fn) {
        if (currentInput === "0") {
            currentInput = fn;
        } else {
            currentInput += fn;
        }
        updateDisplay();
    }

    function clearAll() {
        currentInput = "0";
        lastExpr = "";
        updateDisplay();
    }

    function backspace() {
        if (currentInput.length > 1) {
            currentInput = currentInput.slice(0, -1);
        } else {
            currentInput = "0";
        }
        updateDisplay();
    }

    async function calculate() {
        if (!currentInput) return;
        const expr = currentInput;
        try {
            const res = await fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ expression: expr })
            });

            const data = await res.json();
            if (res.ok) {
                lastExpr = expr + " =";
                currentInput = String(data.result);
                updateDisplay();
                loadHistory();
            } else {
                lastExpr = "Error";
                currentInput = data.detail || "Error";
                updateDisplay();
            }
        } catch (err) {
            lastExpr = "Error";
            currentInput = "Connection failed";
            updateDisplay();
        }
    }

    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            if (data.history && data.history.length > 0) {
                historyList.innerHTML = data.history.map(item => `
                    <div class="history-item" onclick="useHistory('${item.result}')">
                        <div class="history-expr">${item.expression}</div>
                        <div class="history-res">= ${item.result}</div>
                    </div>
                `).join('');
            } else {
                historyList.innerHTML = '<div class="empty-history">No calculations yet</div>';
            }
        } catch (e) {}
    }

    async function clearHistory() {
        await fetch('/api/history', { method: 'DELETE' });
        loadHistory();
    }

    function useHistory(val) {
        currentInput = val;
        updateDisplay();
    }

    // Keyboard support
    document.addEventListener('keydown', (e) => {
        if (e.key >= '0' && e.key <= '9') append(e.key);
        else if (e.key === '.') append('.');
        else if (e.key === '+') append('+');
        else if (e.key === '-') append('-');
        else if (e.key === '*') append('×');
        else if (e.key === '/') append('÷');
        else if (e.key === '^') append('^');
        else if (e.key === 'Enter' || e.key === '=') { e.preventDefault(); calculate(); }
        else if (e.key === 'Backspace') backspace();
        else if (e.key === 'Escape') clearAll();
    });

    loadHistory();
</script>

</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7500, reload=True)
