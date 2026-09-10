from app.services.plate import parse_plate, normalize


def test_bangla_car_ga():
    r = parse_plate("ঢাকা মেট্রো গ ১২-৩৪৫৬")
    assert r["normalized_plate"] == "DHAKA METRO GA 12-3456"
    assert r["class_bn"] == "গ"
    assert r["class_code"] == "GA"
    assert r["series_number"] == "12"
    assert r["vehicle_number"] == "3456"
    assert r["vehicle_category"] == "CAR"
    assert r["suggested_category_id"] == 2


def test_bangla_motorcycle_la():
    r = parse_plate("ঢাকা মেট্রো ল ১৭-৭৫৪৪")
    assert r["normalized_plate"] == "DHAKA METRO LA 17-7544"
    assert r["class_bn"] == "ল"
    assert r["class_code"] == "LA"
    assert r["vehicle_category"] == "MOTORCYCLE"
    assert r["suggested_category_id"] == 1


def test_bangla_car_ka():
    r = parse_plate("ঢাকা মেট্রো ক ১১-১২৩৪")
    assert r["normalized_plate"] == "DHAKA METRO KA 11-1234"
    assert r["class_bn"] == "ক"
    assert r["class_code"] == "KA"


def test_english_ga():
    r = parse_plate("DHAKA METRO GA 12-3456")
    assert r["normalized_plate"] == "DHAKA METRO GA 12-3456"


def test_english_l_maps_to_la():
    r = parse_plate("DHAKA METRO L 17 7544")
    assert r["normalized_plate"] == "DHAKA METRO LA 17-7544"
    assert r["vehicle_category"] == "MOTORCYCLE"


def test_digit_normalization():
    assert normalize("ঢাকা মেট্রো গ ১২-৩৪৫৬") == "DHAKA METRO GA 12-3456"
