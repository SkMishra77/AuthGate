from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: int


class UserLogin(BaseModel):
    username: str
    password: str


class RoleModel:
    ADMIN = 1
    MODERATOR = 2
    USER = 3
