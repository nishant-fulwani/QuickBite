import pytest
from app import app, db, MenuItem

@pytest.fixture
def client():
    # Configure app for testing using an in-memory SQLite database
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # Add a test menu item
            test_item = MenuItem(name="Test Burger", description="A delicious test", price=5.99, category="Main")
            db.session.add(test_item)
            db.session.commit()
            
            yield client
            
        # Clean up after tests
        with app.app_context():
            db.drop_all()

def test_home_page(client):
    """Test if the home page loads and displays the test menu item."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Test Burger" in response.data
    assert b"$5.99" in response.data

def test_add_to_cart(client):
    """Test if adding an item to the cart updates the session."""
    # Add the item with ID 1 to the cart
    response = client.post('/add_to_cart/1', follow_redirects=True)
    assert response.status_code == 200
    
    # Check if the cart page reflects the added item
    response_cart = client.get('/cart')
    assert b"Test Burger" in response_cart.data
    assert b"1" in response_cart.data # Quantity