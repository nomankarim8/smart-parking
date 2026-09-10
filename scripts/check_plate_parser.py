import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.services.plate import parse_plate

examples = [
    'ঢাকা মেট্রো গ ১২-৩৪৫৬',
    'ঢাকা মেট্রো ল ১৭-৭৫৪৪',
    'ঢাকা মেট্রো ক ১১-১২৩৪',
    'DHAKA METRO GA 12-3456',
    'DHAKA METRO L 17 7544',
]
for value in examples:
    print(value, '=>', parse_plate(value))
