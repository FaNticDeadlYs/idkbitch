from app import app, db
from models import User, Time
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create fresh database
    db.drop_all()
    db.create_all()
    
    # Create admin user
    admin = User(
        username='admin',
        password=generate_password_hash('admin'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    print("Database created successfully with admin user!")
