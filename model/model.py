from sqlmodel import SQLModel, Field, Relationship


class Role(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    users: list["User"] = Relationship(back_populates="role")


class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password: str
    role_id: int = Field(default=None, foreign_key="role.id")
    role: Role = Relationship(back_populates="users")
