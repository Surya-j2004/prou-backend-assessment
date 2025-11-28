from pydantic import BaseModel, EmailStr
from typing import List, Optional

# --- Shared ---
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Tasks ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_completed: bool = False

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    owner_id: int

# --- Employees ---
class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    role: str

class EmployeeCreate(EmployeeBase):
    password: str  

class Employee(EmployeeBase):
    id: int
    