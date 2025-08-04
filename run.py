from app import app, db, User, Product, Supplier, Customer, Sale, SaleItem
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def init_database():
    """Initialize the database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default users if they don't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@autoglass.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
        
        if not User.query.filter_by(username='staff').first():
            staff = User(
                username='staff',
                email='staff@autoglass.com',
                password_hash=generate_password_hash('staff123'),
                role='staff'
            )
            db.session.add(staff)
        
        if not User.query.filter_by(username='cashier').first():
            cashier = User(
                username='cashier',
                email='cashier@autoglass.com',
                password_hash=generate_password_hash('cashier123'),
                role='cashier'
            )
            db.session.add(cashier)
        
        # Create sample suppliers
        if not Supplier.query.first():
            suppliers_data = [
                {'name': 'Glass Pro Philippines', 'contact_person': 'Maria Santos', 'phone': '02-8123-4567', 'email': 'maria@glasspro.ph'},
                {'name': 'Metro Aluminum Supply', 'contact_person': 'Juan Dela Cruz', 'phone': '02-8987-6543', 'email': 'juan@metroaluminum.com'},
                {'name': 'Auto Parts Central', 'contact_person': 'Lisa Rodriguez', 'phone': '02-8555-1234', 'email': 'lisa@autoparts.ph'}
            ]
            
            for supplier_data in suppliers_data:
                supplier = Supplier(**supplier_data)
                db.session.add(supplier)
        
        # Create sample customers
        if not Customer.query.first():
            customers_data = [
                {'name': 'John Doe', 'phone': '09123456789', 'email': 'john@email.com'},
                {'name': 'Jane Smith', 'phone': '09987654321', 'email': 'jane@email.com'},
                {'name': 'Mike Johnson', 'phone': '09555123456', 'email': 'mike@email.com'}
            ]
            
            for customer_data in customers_data:
                customer = Customer(**customer_data)
                db.session.add(customer)
        
        # Create sample products
        if not Product.query.first():
            suppliers = Supplier.query.all()
            products_data = [
                {'name': 'Windshield Glass - Toyota Camry', 'category': 'glass', 'price': 8500.00, 'stock_quantity': 15, 'supplier_id': suppliers[0].id if suppliers else None},
                {'name': 'Side Mirror - Honda Civic', 'category': 'accessories', 'price': 2500.00, 'stock_quantity': 8, 'supplier_id': suppliers[2].id if suppliers else None},
                {'name': 'Aluminum Frame - Standard', 'category': 'aluminum', 'price': 1200.00, 'stock_quantity': 25, 'supplier_id': suppliers[1].id if suppliers else None},
                {'name': 'Rear Window - Ford Focus', 'category': 'glass', 'price': 6500.00, 'stock_quantity': 3, 'min_stock_level': 8, 'supplier_id': suppliers[0].id if suppliers else None},
                {'name': 'Door Glass - Mitsubishi Montero', 'category': 'glass', 'price': 7000.00, 'stock_quantity': 12, 'supplier_id': suppliers[0].id if suppliers else None}
            ]
            
            for product_data in products_data:
                product = Product(**product_data)
                db.session.add(product)
        
        # Create sample sales data
        if not Sale.query.first():
            users = User.query.all()
            customers = Customer.query.all()
            products = Product.query.all()
            
            if users and products:
                # Create sales for the last 30 days
                for i in range(20):
                    sale_date = datetime.now() - timedelta(days=random.randint(0, 30))
                    sale = Sale(
                        customer_id=random.choice(customers).id if customers and random.choice([True, False]) else None,
                        user_id=random.choice(users).id,
                        total_amount=0,
                        payment_method=random.choice(['cash', 'credit']),
                        created_at=sale_date
                    )
                    db.session.add(sale)
                    db.session.flush()
                    
                    # Add 1-3 items per sale
                    total = 0
                    for _ in range(random.randint(1, 3)):
                        product = random.choice(products)
                        quantity = random.randint(1, 3)
                        unit_price = product.price
                        total_price = unit_price * quantity
                        total += total_price
                        
                        sale_item = SaleItem(
                            sale_id=sale.id,
                            product_id=product.id,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price
                        )
                        db.session.add(sale_item)
                    
                    sale.total_amount = total
        
        db.session.commit()
        print("Database initialized successfully with sample data!")

if __name__ == '__main__':
    init_database()
    print("Starting O. Castro Autoglass & Aluminum MIS...")
    print("Access the system at: http://localhost:5000")
    print("Default login credentials:")
    print("Admin: admin / admin123")
    print("Staff: staff / staff123")
    print("Cashier: cashier / cashier123")
    print("\nFeatures available:")
    print("✓ Dashboard with statistics")
    print("✓ Inventory management")
    print("✓ Sales tracking")
    print("✓ Purchase orders")
    print("✓ Reports with charts (Admin only)")
    print("✓ PDF/Excel export")
    app.run(debug=True, host='0.0.0.0', port=5000)
