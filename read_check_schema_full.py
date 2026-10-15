import re

checks_path = "src/quality/checks.py"

with open(checks_path, "r", encoding="utf-8") as f:
    code = f.read()

# Procura a funcao check_schema
start = code.find("def check_schema(")
if start != -1:
    end = code.find("def ", start + 1)
    func_code = code[start:end if end != -1 else len(code)]
    
    # Inspeciona e substitui a verificacao de wrong_types para harmonizar object com string
    print("=== CÓDIGO ATUAL DO CHECK_SCHEMA ===")
    print(func_code)
