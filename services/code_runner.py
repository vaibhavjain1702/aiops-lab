"""
Code Runner Service — Isolated code execution for generated code testing
Port: 8004 (internal network only)

Security:
  - Runs in dedicated container
  - Read-only root filesystem
  - Small tmpfs for temp files
  - CPU/memory/PID limits
  - AST validation before execution
  - Dangerous import/builtin rejection
  - Hard subprocess timeout

NOTE: This is a classroom/local evaluation runner, NOT a production security boundary.
"""

import ast
import sys
import json
import subprocess
import tempfile
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code_runner")

# --- Configuration ---
EXECUTION_TIMEOUT = 10  # seconds
MAX_OUTPUT_SIZE = 10000  # characters

# Dangerous modules to reject
DANGEROUS_MODULES = {
    "os", "sys", "subprocess", "socket", "pathlib",
    "shutil", "ctypes", "signal", "multiprocessing",
    "threading", "http", "urllib", "requests", "httpx",
    "ftplib", "smtplib", "telnetlib", "xmlrpc",
    "pickle", "shelve", "marshal",
}

# Dangerous builtins to reject
DANGEROUS_BUILTINS = {
    "eval", "exec", "compile", "open", "input",
    "breakpoint", "__import__", "globals", "locals",
    "getattr", "setattr", "delattr", "vars",
}


def validate_code_ast(code: str) -> dict:
    """Validate Python code using AST analysis."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error: {e.msg} (line {e.lineno})",
            "type": "syntax_error"
        }
    
    violations = []
    
    for node in ast.walk(tree):
        # Check for dangerous imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split('.')[0]
                if module_root in DANGEROUS_MODULES:
                    violations.append(f"Forbidden import: {alias.name}")
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split('.')[0]
                if module_root in DANGEROUS_MODULES:
                    violations.append(f"Forbidden import from: {node.module}")
        
        # Check for dangerous builtins
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_BUILTINS:
                    violations.append(f"Forbidden builtin call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in DANGEROUS_BUILTINS:
                    violations.append(f"Forbidden method call: {node.func.attr}")
    
    if violations:
        return {
            "valid": False,
            "error": "; ".join(violations),
            "type": "security_violation",
            "violations": violations
        }
    
    return {"valid": True, "error": None, "type": "ok"}


def execute_code_with_tests(code: str, tests: list) -> dict:
    """Execute code with test assertions in an isolated subprocess."""
    # Validate AST first
    validation = validate_code_ast(code)
    if not validation["valid"]:
        return {
            "status": "validation_failed",
            "validation": validation,
            "passed": 0,
            "failed": len(tests),
            "total": len(tests),
            "pass_rate": 0.0,
            "details": [],
            "stdout": "",
            "stderr": validation["error"]
        }
    
    results = {
        "status": "completed",
        "validation": validation,
        "passed": 0,
        "failed": 0,
        "total": len(tests),
        "pass_rate": 0.0,
        "details": [],
        "stdout": "",
        "stderr": ""
    }
    
    for i, test in enumerate(tests):
        # Combine code + test into a single script
        test_script = f"{code}\n\n# Test {i+1}\ntry:\n    {test}\n    print('PASS')\nexcept AssertionError as e:\n    print(f'FAIL: {{e}}')\nexcept Exception as e:\n    print(f'ERROR: {{e}}')\n"
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
                f.write(test_script)
                temp_path = f.name
            
            proc = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
                cwd='/tmp'
            )
            
            stdout = proc.stdout.strip()[:MAX_OUTPUT_SIZE]
            stderr = proc.stderr.strip()[:MAX_OUTPUT_SIZE]
            
            if stdout.startswith("PASS"):
                results["passed"] += 1
                status = "passed"
            elif stdout.startswith("FAIL"):
                results["failed"] += 1
                status = "failed"
            else:
                results["failed"] += 1
                status = "error"
            
            results["details"].append({
                "test_index": i + 1,
                "test": test,
                "status": status,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": proc.returncode
            })
            
        except subprocess.TimeoutExpired:
            results["failed"] += 1
            results["details"].append({
                "test_index": i + 1,
                "test": test,
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution timed out after {EXECUTION_TIMEOUT}s"
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "test_index": i + 1,
                "test": test,
                "status": "error",
                "stdout": "",
                "stderr": str(e)
            })
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    results["pass_rate"] = round(results["passed"] / results["total"], 4) if results["total"] > 0 else 0.0
    return results


class CodeRunnerHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for the code runner service."""
    
    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "healthy",
                "service": "code-runner",
                "timeout": EXECUTION_TIMEOUT,
                "note": "Classroom/local evaluation runner, not production security boundary"
            })
        else:
            self._send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                code = data.get("code", "")
                tests = data.get("tests", [])
                
                if not code:
                    self._send_json(400, {"error": "No code provided"})
                    return
                
                result = execute_code_with_tests(code, tests)
                self._send_json(200, result)
                
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Invalid JSON"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not found"})
    
    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        logger.info(format % args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8004"))
    server = HTTPServer(("0.0.0.0", port), CodeRunnerHandler)
    logger.info(f"Code Runner listening on port {port}")
    server.serve_forever()
