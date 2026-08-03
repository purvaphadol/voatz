#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User

def check_users():
    app = create_app()
    with app.app_context():
        users = User.query.all()
        print('Users in database:')
        for user in users:
            print(f'  ID: {user.id}, Name: {user.name}, Email: {user.email}')
            # Try to check password for the rushiraj user
            if user.email == 'rushiraj@datagrid.co.in':
                print(f'    Password hash: {user.password_hash[:50]}...')

if __name__ == "__main__":
    check_users() 