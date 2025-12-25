from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None

    # pydantic v2: use `from_attributes` in model_config instead of orm_mode
    model_config = {"from_attributes": True}
