from fastapi import FastAPI, Depends, HTTPException, Request, Form, File, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Date, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import text
from datetime import datetime, timedelta, date
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from openpyxl import Workbook
import uvicorn

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./autoglass_mis.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# FastAPI app
app = FastAPI(title="O. Castro Autoglass & Aluminum MIS")
templates = Jinja2Templates(directory="templates")

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="staff")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    description = Column(Text)
    price = Column(Float)
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=10)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    supplier = relationship("Supplier", back_populates="products")

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    contact_person = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="supplier")

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float)
    payment_method = Column(String)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("SaleItem", back_populates="sale")

class SaleItem(Base):
    __tablename__ = "sale_items"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_price = Column(Float)
    
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.username == username).first()
    return user

# Chart generation functions
def generate_sales_chart(db: Session):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    sales_data = db.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total_amount).label('total')
    ).filter(
        Sale.created_at >= start_date
    ).group_by(
        func.date(Sale.created_at)
    ).all()
    
    plt.figure(figsize=(12, 6))
    if sales_data:
        dates = [item.date for item in sales_data]
        amounts = [float(item.total) for item in sales_data]
        
        plt.plot(dates, amounts, marker='o', linewidth=2, markersize=6)
    
    plt.title('Daily Sales - Last 30 Days', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Sales Amount ($)', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png', dpi=150, bbox_inches='tight')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    return chart_url

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid username or password"
        })
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get statistics
    total_products = db.query(Product).count()
    low_stock_items = db.query(Product).filter(Product.stock_quantity <= Product.min_stock_level).count()
    today_sales = db.query(Sale).filter(Sale.created_at >= datetime.now().date()).count()
    total_customers = db.query(Customer).count()
    
    # Recent sales
    recent_sales = db.query(Sale).order_by(Sale.created_at.desc()).limit(5).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "total_products": total_products,
        "low_stock_items": low_stock_items,
        "today_sales": today_sales,
        "total_customers": total_customers,
        "recent_sales": recent_sales
    })

@app.get("/inventory", response_class=HTMLResponse)
async def inventory(request: Request, search: str = "", category: str = "", db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    query = db.query(Product)
    if search:
        query = query.filter(Product.name.contains(search))
    if category:
        query = query.filter(Product.category == category)
    
    products = query.all()
    return templates.TemplateResponse("inventory.html", {
        "request": request,
        "user": user,
        "products": products
    })

@app.get("/inventory/add", response_class=HTMLResponse)
async def add_product_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    suppliers = db.query(Supplier).all()
    return templates.TemplateResponse("add_product.html", {
        "request": request,
        "user": user,
        "suppliers": suppliers
    })

@app.post("/inventory/add")
async def add_product(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    price: float = Form(...),
    stock_quantity: int = Form(...),
    min_stock_level: int = Form(10),
    supplier_id: int = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    product = Product(
        name=name,
        category=category,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        min_stock_level=min_stock_level,
        supplier_id=supplier_id if supplier_id else None
    )
    
    db.add(product)
    db.commit()
    
    return RedirectResponse(url="/inventory", status_code=302)

@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != 'admin':
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Sales statistics
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    daily_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at >= today
    ).scalar() or 0
    
    weekly_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at >= week_ago
    ).scalar() or 0
    
    monthly_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at >= month_ago
    ).scalar() or 0
    
    # Generate charts
    sales_chart = generate_sales_chart(db)
    
    # Top products
    top_products = db.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_sold'),
        func.sum(SaleItem.total_price).label('total_revenue')
    ).join(SaleItem).group_by(Product.id).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(5).all()
    
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user": user,
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "sales_chart": sales_chart,
        "top_products": top_products
    })

# Initialize database with sample data
def init_database():
    db = SessionLocal()
    
    # Create admin user if not exists
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            email="admin@autoglass.com",
            password_hash=get_password_hash("admin123"),
            role="admin"
        )
        db.add(admin)
    
    # Create sample suppliers
    if not db.query(Supplier).first():
        suppliers_data = [
            {"name": "Glass Pro Philippines", "contact_person": "Maria Santos", "phone": "02-8123-4567"},
            {"name": "Metro Aluminum Supply", "contact_person": "Juan Dela Cruz", "phone": "02-8987-6543"},
            {"name": "Auto Parts Central", "contact_person": "Lisa Rodriguez", "phone": "02-8555-1234"}
        ]
        
        for supplier_data in suppliers_data:
            supplier = Supplier(**supplier_data)
            db.add(supplier)
    
    # Create sample products
    if not db.query(Product).first():
        suppliers = db.query(Supplier).all()
        products_data = [
            {"name": "Windshield Glass - Toyota Camry", "category": "glass", "price": 8500.00, "stock_quantity": 15},
            {"name": "Side Mirror - Honda Civic", "category": "accessories", "price": 2500.00, "stock_quantity": 8},
            {"name": "Aluminum Frame - Standard", "category": "aluminum", "price": 1200.00, "stock_quantity": 25},
            {"name": "Rear Window - Ford Focus", "category": "glass", "price": 6500.00, "stock_quantity": 3, "min_stock_level": 8},
        ]
        
        for i, product_data in enumerate(products_data):
            if suppliers:
                product_data["supplier_id"] = suppliers[i % len(suppliers)].id
            product = Product(**product_data)
            db.add(product)
    
    db.commit()
    db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Starting O. Castro Autoglass & Aluminum MIS...")
    print("Access the system at: http://localhost:8000")
    print("Default login: admin / admin123")
    uvicorn.run(app, host="0.0.0.0", port=8000)
