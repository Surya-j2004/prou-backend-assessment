from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.security import OAuth2PasswordBearer
from . import schemas, database, security
from .database import get_db_connection
import time
from fastapi.security import OAuth2PasswordRequestForm 
from jose import jwt, JWTError
from .security import SECRET_KEY, ALGORITHM 

app = FastAPI(title="ProU Backend (Advanced)")

# Token helper
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.on_event("startup")
def startup_event():
    database.init_db()

# --- UTILITY: Get Current User (Protects Routes) ---
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# --- BACKGROUND TASK: Simulate Email ---
def send_welcome_email(email: str):
    time.sleep(2) # Simulate delay
    print(f"📧 [Background Task] Email sent to {email}")

# --- AUTH ENDPOINTS ---

@app.post("/register/", response_model=schemas.Employee)
def register(employee: schemas.EmployeeCreate, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the password
    hashed_pwd = security.get_password_hash(employee.password)
    
    try:
        cursor.execute("""
            INSERT INTO employees (name, email, role, password_hash) 
            VALUES (%s, %s, %s, %s) 
            RETURNING id, name, email, role;
        """, (employee.name, employee.email, employee.role, hashed_pwd))
        new_employee = cursor.fetchone()
        conn.commit()
        
        # Trigger Background Email
        background_tasks.add_task(send_welcome_email, employee.email)
        
        return new_employee
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()

@app.post("/login/", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor()
    
   
    cursor.execute("SELECT * FROM employees WHERE email = %s", (form_data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not security.verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = security.create_access_token(data={"sub": user['email']})
    return {"access_token": access_token, "token_type": "bearer"}
#  ANALYTICS ENDPOINT  

@app.get("/stats/dashboard")
def get_analytics(current_user: str = Depends(get_current_user)):
    """Only logged in users can see stats"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Complex query: Joins, Aggregation, and Case Logic
    query = """
    SELECT 
        e.name, 
        e.role,
        COUNT(t.id) as total_tasks,
        SUM(CASE WHEN t.is_completed THEN 1 ELSE 0 END) as completed_tasks,
        ROUND(
            (SUM(CASE WHEN t.is_completed THEN 1 ELSE 0 END)::decimal / NULLIF(COUNT(t.id),0)) * 100, 2
        ) as completion_rate
    FROM employees e
    LEFT JOIN tasks t ON e.id = t.owner_id
    GROUP BY e.id, e.name, e.role
    ORDER BY total_tasks DESC;
    """
    
    cursor.execute(query)
    stats = cursor.fetchall()
    conn.close()
    return stats

#  TASK ENDPOINTS 

@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, email: str = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Find the logged-in user's ID
    cursor.execute("SELECT id FROM employees WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    owner_id = user['id']

    # 2. Insert the Task (Automatically assigned to owner_id)
    try:
        cursor.execute("""
            INSERT INTO tasks (title, description, is_completed, owner_id) 
            VALUES (%s, %s, %s, %s) 
            RETURNING id, title, description, is_completed, owner_id;
        """, (task.title, task.description, task.is_completed, owner_id))
        
        new_task = cursor.fetchone()
        conn.commit()
        return new_task
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()