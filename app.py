import os
from functools import wraps
from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Read secret key and database URL from .env, or use defaults
app.secret_key = os.getenv('SECRET_KEY', 'default_fallback_key')

basedir = os.path.abspath(os.path.dirname(__file__))
default_db_url = 'sqlite:///' + os.path.join(basedir, 'quickbite.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', default_db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# --- Database Models ---
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    available = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_address = db.Column(db.String(255), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# --- Global Template Variables ---
@app.context_processor
def inject_cart_count():
    cart = session.get('cart', {})
    count = sum(item['quantity'] for item in cart.values())
    return dict(cart_count=count)

# --- Security Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Customer Routes ---
@app.route('/')
def home():
    menu_items = MenuItem.query.filter_by(available=True).all()
    return render_template('index.html', items=menu_items)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    item = MenuItem.query.get_or_404(item_id)
    cart = session.get('cart', {})
    item_id_str = str(item_id)
    if item_id_str in cart:
        cart[item_id_str]['quantity'] += 1
    else:
        cart[item_id_str] = {'name': item.name, 'price': item.price, 'quantity': 1}
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    return render_template('cart.html', cart=cart, total=total)

@app.route('/remove_from_cart/<item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart = session.get('cart', {})
    if item_id in cart:
        del cart[item_id]
        session['cart'] = cart
        session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('home'))
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        new_order = Order(customer_name=name, customer_address=address, total_price=total)
        db.session.add(new_order)
        db.session.commit()
        for item_id, item in cart.items():
            order_item = OrderItem(order_id=new_order.id, menu_item_name=item['name'], price=item['price'], quantity=item['quantity'])
            db.session.add(order_item)
        db.session.commit()
        session.pop('cart', None)
        return redirect(url_for('order_success', order_id=new_order.id))
    return render_template('checkout.html', total=total)

@app.route('/order_success/<int:order_id>')
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_success.html', order=order)

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    orders = Order.query.order_by(Order.id.desc()).all()
    menu_items = MenuItem.query.all()
    return render_template('admin_dashboard.html', orders=orders, menu_items=menu_items)

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
@admin_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = request.form.get('status')
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# --- App Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed Admin User
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('admin123')
            default_admin = Admin(username='admin', password_hash=hashed_pw)
            db.session.add(default_admin)
            db.session.commit()
        
        # Seed Menu Items
        if not MenuItem.query.first():
            sample_data = [
                MenuItem(name="QuickBite Classic Burger", description="Juicy beef patty with cheese, lettuce.", price=8.99, category="Main"),
                MenuItem(name="Crispy Fries", description="Golden, salted French fries.", price=3.99, category="Side"),
            ]
            db.session.add_all(sample_data)
            db.session.commit()
            
    app.run(debug=True)