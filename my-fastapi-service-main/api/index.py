from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import re
from dotenv import load_dotenv

# Load environment variables (Make sure you have a .env file with DATABASE_URL)
load_dotenv()

app = FastAPI(title="Omniverse API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your frontend to connect locally
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, and OPTIONS
    allow_headers=["*"],
)

# Database Connection Helper
def get_db_connection():
    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# ---------------------------------------------------------
# AUTHENTICATION & SECURITY (3-TIER SYSTEM)
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str

# 1. Base Security (Allows Admins, Users, and Guests)
def get_current_user(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing Clearance Key")
    
    # Hardcoded Guest bypass
    if x_api_key == "public_guest_clearance":
        return {"username": "Civilian_Guest", "role": "guest"}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT username, role FROM users WHERE api_key = %s;", (x_api_key,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid Clearance Key")
        return user
    finally:
        cursor.close()
        conn.close()

# 2. Middle-Tier Security (Blocks Guests, Allows Users & Admins)
def require_registered(user: dict = Depends(get_current_user)):
    if user['role'] == 'guest':
        raise HTTPException(status_code=403, detail="Forbidden: Registered Agent Clearance Required")
    return user

# 3. Top-Tier Security (Admins Only)
def require_admin(user: dict = Depends(get_current_user)):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Forbidden: Omega Level Admin Clearance Required")
    return user

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT api_key, role FROM users WHERE username = %s AND password = %s;", (req.username, req.password))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid Credentials")
        return {"api_key": user['api_key'], "role": user['role']}
    finally:
        cursor.close()
        conn.close()
# ---------------------------------------------------------
# SECURE PYDANTIC VALIDATION MODELS
# ---------------------------------------------------------

class HeroCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=100, description="Hero/Villain alias")
    civilian_name: Optional[str] = Field(None, max_length=100)
    origin_era: Optional[str] = Field(None, max_length=50)
    publisher: Optional[str] = Field(None, max_length=50)
    alignment: Optional[str] = Field(None, max_length=30)
    power_tier: Optional[str] = Field(None, max_length=50)
    affiliation: Optional[str] = Field(None, max_length=100)
    threat_level: Optional[str] = Field(None, max_length=50)
    base_of_operations: Optional[str] = Field(None, max_length=100)
    primary_powers: Optional[str] = Field(None, max_length=500)
    tactical_vulnerability: Optional[str] = Field(None, max_length=500)
    signature_gear: Optional[str] = Field(None, max_length=255)
    combat_doctrine: Optional[str] = Field(None, max_length=500)
    psychological_dossier: Optional[str] = Field(None, max_length=500)
    arch_nemesis: Optional[str] = Field(None, max_length=100)
    image: Optional[str] = Field(None, max_length=255)

    # Security Sanitizer: Strips trailing spaces and prevents basic XSS injection
    @field_validator('*', mode='before')
    def sanitize_strings(cls, value):
        if isinstance(value, str):
            cleaned = value.strip()
            if re.search(r'<script.*?>.*?</script>', cleaned, re.IGNORECASE):
                raise ValueError("Invalid characters or script tags detected.")
            return cleaned
        return value

    # Publisher whitelist enforcement
    @field_validator('publisher')
    def validate_publisher(cls, value):
        if value:
            allowed_publishers = ['Marvel', 'DC', 'Dynamite', 'Image', 'Valiant', 'Independent']
            matched = next((p for p in allowed_publishers if p.lower() == value.lower()), None)
            if not matched:
                raise ValueError(f"Publisher must be one of: {', '.join(allowed_publishers)}")
            return matched
        return value

class HeroUpdate(HeroCreate):
    # For PUT requests, we make alias optional so partial updates don't fail
    alias: Optional[str] = Field(None, min_length=1, max_length=100)

# ---------------------------------------------------------
# NEON DATABASE CRUD ENDPOINTS
# ---------------------------------------------------------

@app.get("/")
def root():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM comic_archive;")
        count = cursor.fetchone()['count']
        return {"registry_status": "ONLINE", "dossiers_cataloged": count}
    finally:
        cursor.close()
        conn.close()

@app.get("/health")
def health_check():
    return {"status": "online"}

@app.get("/api/heroes/search", dependencies=[Depends(get_current_user)])
def search_heroes(q: Optional[str] = None, publisher: Optional[str] = None, alignment: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM comic_archive WHERE 1=1"
        params = []
        
        if q:
            query += " AND (alias ILIKE %s OR civilian_name ILIKE %s)"
            params.extend([f"%{q}%", f"%{q}%"])
        if publisher:
            query += " AND publisher ILIKE %s"
            params.append(f"%{publisher}%")
        if alignment:
            query += " AND alignment ILIKE %s"
            params.append(f"%{alignment}%")
            
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()
        conn.close()

@app.get("/api/heroes", dependencies=[Depends(get_current_user)])
def get_all_heroes():
    # Guests, Users, and Admins can all view the global catalog
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, alias, publisher, affiliation, origin_era, image, civilian_name FROM comic_archive ORDER BY id ASC;")
        heroes = cursor.fetchall()
        return heroes
    finally:
        cursor.close()
        conn.close()

@app.get("/api/heroes/{hero_id}", dependencies=[Depends(require_registered)])
def get_hero(hero_id: int):
    # Middle-Tier: Only Users and Admins can view highly classified full dossier details
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM comic_archive WHERE id = %s;", (hero_id,))
        hero = cursor.fetchone()
        if not hero:
            raise HTTPException(status_code=404, detail="Dossier not found")
        return hero
    finally:
        cursor.close()
        conn.close()

@app.post("/api/heroes", status_code=201, dependencies=[Depends(require_admin)])
def create_hero(hero: HeroCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = hero.model_dump(exclude_unset=True)
        columns = ', '.join(fields.keys())
        placeholders = ', '.join(['%s'] * len(fields))
        values = tuple(fields.values())

        insert_query = f"INSERT INTO comic_archive ({columns}) VALUES ({placeholders}) RETURNING id;"
        cursor.execute(insert_query, values)
        new_id = cursor.fetchone()['id']
        conn.commit()
        
        return {"message": "Dossier created successfully", "id": new_id, "data": fields}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.put("/api/heroes/{hero_id}", dependencies=[Depends(require_admin)])
def update_hero(hero_id: int, hero: HeroUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = hero.model_dump(exclude_unset=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields provided for update")

        set_clause = ', '.join([f"{key} = %s" for key in fields.keys()])
        values = tuple(fields.values()) + (hero_id,)

        update_query = f"UPDATE comic_archive SET {set_clause} WHERE id = %s RETURNING id;"
        cursor.execute(update_query, values)
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Dossier not found")
            
        conn.commit()
        return {"message": "Dossier updated successfully", "updated_fields": fields}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/heroes/{hero_id}", dependencies=[Depends(require_admin)])
def delete_hero(hero_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM comic_archive WHERE id = %s RETURNING id;", (hero_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Dossier not found")
            
        conn.commit()
        return {"message": f"Dossier {hero_id} purged from archive"}
    finally:
        cursor.close()
        conn.close()