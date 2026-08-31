from app.services.plate import normalize

def test_normalize_spaces_and_case():
    assert normalize(' dhaka metro ga 12-3456 ') == 'DHAKA METRO GA 12-3456'
