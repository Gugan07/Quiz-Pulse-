from app import app
print('Testing app context')
with app.app_context():
    print('App context works')
    from models import db
    print('DB import works')
    db.create_all()
    print('DB tables created')
