from app import app, db
from models import User, Time

with app.app_context():
    db.drop_all()
    db.create_all()
    
    # Create admin user
    from werkzeug.security import generate_password_hash
    admin = User(
        username='admin',
        password=generate_password_hash('admin'),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
