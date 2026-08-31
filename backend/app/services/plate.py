import re

def clean(raw:str)->str:
    s=raw.upper().replace("—","-").replace("–","-")
    s=re.sub(r"[^A-Z0-9\s-]"," ",s); s=re.sub(r"\s+"," ",s).strip(); return s

def normalize(raw:str)->str:
    s=clean(raw)
    # Keep configurable/region-agnostic. Deterministic key is uppercase + normalized separators.
    s=re.sub(r"\s*-\s*","-",s)
    s=re.sub(r"\s+"," ",s)
    # Common OCR substitutions are applied only when a numeric segment is detected.
    parts=s.split(" ")
    fixed=[]
    for p in parts:
        if any(c.isdigit() for c in p):
            p=p.translate(str.maketrans({"O":"0","I":"1","L":"1","S":"5","B":"8","Z":"2"}))
        fixed.append(p)
    return " ".join(fixed)
