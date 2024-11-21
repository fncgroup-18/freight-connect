from app import create_app

app = create_app()

with app.app_context():
    from extensions import db
    db.drop_all()  # This will clear existing tables
    db.create_all()  # This will create all tables
    print("Database initialized successfully!")
