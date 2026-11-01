from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import auth
from app.core.database import Base, get_db, migrate_admin_password_rotation
from app.core.security import hash_password
from app.models.all_models import ActivityLog, PasswordHistory, Role, User


def test_legacy_admin_migration_marks_existing_accounts_once():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE roles (role_id INTEGER PRIMARY KEY, role_name TEXT)"))
        connection.execute(text(
            "CREATE TABLE users (user_id INTEGER PRIMARY KEY, role_id INTEGER, username TEXT)"
        ))
        connection.execute(text("INSERT INTO roles VALUES (1, 'ADMIN'), (2, 'OPERATOR')"))
        connection.execute(text("INSERT INTO users VALUES (1, 1, 'legacy-admin'), (2, 2, 'operator')"))

    migrate_admin_password_rotation(engine)
    with engine.connect() as connection:
        flags = connection.execute(
            text("SELECT username, must_change_password FROM users ORDER BY user_id")
        ).all()
    assert flags == [("legacy-admin", 1), ("operator", 0)]

    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET must_change_password=0 WHERE user_id=1"))
    migrate_admin_password_rotation(engine)
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT must_change_password FROM users WHERE user_id=1")
        ).scalar_one() == 0
    engine.dispose()


def build_auth_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def test_db():
        with factory() as db:
            yield db

    with factory() as db:
        role = Role(role_name="ADMIN", description="Test administrator")
        db.add(role)
        db.flush()
        db.add(
            User(
                username="rotation-admin",
                email="rotation-admin@example.test",
                password_hash=hash_password("OldAdminPass1!"),
                full_name="Rotation Admin",
                role_id=role.role_id,
                must_change_password=True,
                password_version=0,
            )
        )
        db.commit()

    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    app.dependency_overrides[get_db] = test_db
    app.get("/private")(lambda user=Depends(current_user): {"user": user.username})
    return engine, factory, TestClient(app)


def test_admin_is_restricted_until_password_rotation_and_old_tokens_are_revoked():
    engine, factory, client = build_auth_client()
    with client:
        login = client.post(
            "/auth/login",
            json={"username": "rotation-admin", "password": "OldAdminPass1!"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["must_change_password"] is True
        old_token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {old_token}"

        assert client.get("/auth/me").json()["must_change_password"] is True
        assert client.get("/private").status_code == 403

        changed = client.post(
            "/auth/change-password",
            json={
                "current_password": "OldAdminPass1!",
                "new_password": "NewAdminPassword2#",
            },
        )
        assert changed.status_code == 200
        assert changed.json()["user"]["must_change_password"] is False
        new_token = changed.json()["access_token"]

        client.headers["Authorization"] = f"Bearer {old_token}"
        assert client.get("/auth/me").status_code == 401
        client.headers["Authorization"] = f"Bearer {new_token}"
        assert client.get("/private").status_code == 200
        assert client.get("/auth/me").json()["must_change_password"] is False

    with factory() as db:
        user = db.query(User).filter_by(username="rotation-admin").one()
        assert user.password_version == 1
        assert user.password_changed_at is not None
        assert user.must_change_password is False
        assert db.query(PasswordHistory).filter_by(user_id=user.user_id).count() == 1
        assert db.query(ActivityLog).filter_by(action="PASSWORD_CHANGED").count() == 1
    engine.dispose()


def test_password_rotation_rejects_weak_and_recently_used_passwords():
    engine, _factory, client = build_auth_client()
    with client:
        token = client.post(
            "/auth/login",
            json={"username": "rotation-admin", "password": "OldAdminPass1!"},
        ).json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        weak = client.post(
            "/auth/change-password",
            json={"current_password": "OldAdminPass1!", "new_password": "lowercaseonly"},
        )
        assert weak.status_code == 422

        changed = client.post(
            "/auth/change-password",
            json={
                "current_password": "OldAdminPass1!",
                "new_password": "NewAdminPassword2#",
            },
        )
        assert changed.status_code == 200
        client.headers["Authorization"] = f"Bearer {changed.json()['access_token']}"
        reuse = client.post(
            "/auth/change-password",
            json={
                "current_password": "NewAdminPassword2#",
                "new_password": "OldAdminPass1!",
            },
        )
        assert reuse.status_code == 422
        assert client.get("/auth/me").json()["must_change_password"] is False
    engine.dispose()
