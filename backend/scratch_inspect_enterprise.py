import ast
from pathlib import Path

file_path = Path("backend/api/enterprise.py")
if file_path.exists():
    content = file_path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    
    print("=== ENDPOINTS IN backend/api/enterprise.py ===")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            decorators = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ["get", "post", "put", "delete", "patch"]:
                    # print decorator name and args
                    args_str = ""
                    if dec.args:
                        if isinstance(dec.args[0], ast.Constant):
                            args_str = repr(dec.args[0].value)
                    decorators.append(f"@{dec.func.value.id}.{dec.func.attr}({args_str})")
                elif isinstance(dec, ast.Attribute) and dec.attr in ["get", "post", "put", "delete", "patch"]:
                    decorators.append(f"@{dec.value.id}.{dec.attr}")
            if decorators:
                print(f"Line {node.lineno}: {', '.join(decorators)} def {node.name}(...)")
else:
    print("enterprise.py does not exist")
