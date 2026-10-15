with open("src/quality/checks.py", "r", encoding="utf-8") as f:
    text = f.read()

start = text.find("def check_schema")
if start != -1:
    end = text.find("def ", start + 1)
    print(text[start:end if end != -1 else start + 1000])
