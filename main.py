import json
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Header
from passlib.context import CryptContext
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import create_engine, Session, select

from auth import AuthGate
from model.model import *
from schema import UserCreate, UserLogin, RoleModel
from settings import sqlite_url

engine = create_engine(sqlite_url, echo=True)

# Cryptography context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    return pwd_context.hash(password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_db_and_tables():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables:
        SQLModel.metadata.create_all(engine)
        print("Tables created!")
    else:
        print("Tables already exist. Skipping creation.")


def load_data_from_json(file_path: str):
    with open(file_path, "r") as f:
        data = json.load(f)

    with Session(engine) as session:
        for role_data in data.get("roles", []):
            role = Role(**role_data)
            try:
                session.merge(role)
                session.commit()
            except IntegrityError:
                session.rollback()
        print("Data loaded into the database.")


def get_session():
    with Session(engine) as session:
        yield session


auth_gate: AuthGate | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    global auth_gate
    print("Starting application...")
    create_db_and_tables()
    load_data_from_json('fixture/roles.json')
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    auth_gate = await AuthGate.create(host=REDIS_HOST, port=REDIS_PORT)
    yield  # Yield control back to the application
    print("Shutting down application...")


async def validate_token_request(Authorization: Annotated[str | None, Header(convert_underscores=False)] = None):
    if Authorization is None or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid Authorization header format.")

    token = Authorization.split(" ")[1]
    user_id = await auth_gate.validate_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Token is invalid.")
    return token, user_id


def role_validator(role: int):
    async def validate_role(session: Session = Depends(get_session),
                            token_data: tuple = Depends(validate_token_request)):
        _, user_id = token_data
        statement = select(User).where(User.id == user_id).limit(1)
        db_user = session.exec(statement).fetchall()[0]

        if db_user.role_id == role:
            return user_id
        raise HTTPException(status_code=401, detail="Permission Denied")

    return validate_role


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/register")
async def register(user: UserCreate, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == user.username).limit(1)
    db_user = session.exec(statement).fetchall()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new user with hashed password
    hashed_password = await hash_password(user.password)
    statement = select(Role).where(Role.id == user.role)
    db_role = session.exec(statement).fetchall()
    if not db_role:
        raise HTTPException(status_code=400, detail="Role Undefined")
    new_user = User(username=user.username, password=hashed_password, role=db_role[0])
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return {"msg": "User created successfully"}


@app.post("/login")
async def login(user: UserLogin, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == user.username).limit(1)
    db_user = session.exec(statement).fetchall()
    if not db_user:
        raise HTTPException(status_code=400, detail="User Not Found")
    db_user = db_user[0]
    if not await verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Incorrect Password")
    token, active_time = await auth_gate.create_token(db_user)
    return {
        'token': token,
        'active_time': active_time
    }


@app.post('/refresh/token')
async def refresh_token(token_data: tuple = Depends(validate_token_request)):
    token, _ = token_data
    NEW_TOKEN_TIME = await auth_gate.refresh_token(token)
    return {
        'active_time': NEW_TOKEN_TIME,
    }


@app.post('/logout')
async def logout(session_data=Depends(validate_token_request)):
    token, _ = session_data
    await auth_gate.logout(token)
    return {
        'message': 'User logged out successfully'
    }


@app.post('/logout_all')
async def logout_all(session_data=Depends(validate_token_request)):
    token, _ = session_data
    await auth_gate.logout_all(token)
    return {
        'message': 'User logged out from all devices successfully'
    }


@app.get('/admin_path')
async def admin_path(user_id: int = Depends(role_validator(RoleModel.ADMIN))):
    return {"message": f"Welcome, Admin (User ID: {user_id})"}


@app.get('/moderator_path')
async def moderator_path(user_id: int = Depends(role_validator(RoleModel.MODERATOR))):
    return {"message": f"Welcome, Moderator (User ID: {user_id})"}


@app.get('/user_path')
async def user_path(user_id: int = Depends(role_validator(RoleModel.MODERATOR))):
    return {"message": f"Welcome, User (User ID: {user_id})"}
