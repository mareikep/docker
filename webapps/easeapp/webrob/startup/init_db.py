import datetime
from flask import current_app
from webrob.models.users import User


def init_db(app, db):
  
    # Automatically create all DB tables in app/app.sqlite file
    db.create_all()

    db.session.commit()
