import json

from app.services.alpr import alpr_service


if __name__ == "__main__":
    print(json.dumps(alpr_service.status(), indent=2))
