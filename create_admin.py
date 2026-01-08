#!/usr/bin/env python
"""Script to create an admin user"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from api.models.user import User

# Create or update admin user
email = 'admin@gmail.com'
password = 'mtn*556#'

try:
    user = User.objects.get(email=email)
    print(f'User with email {email} already exists. Updating...')
    created = False
except User.DoesNotExist:
    user = User(email=email)
    created = True
    print(f'Creating new user with email {email}...')

# Set user properties
user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.user_type = 'admin'
user.is_active = True
user.save()

if created:
    print(f'✓ Admin user created successfully!')
else:
    print(f'✓ Admin user updated successfully!')

print(f'\nCredentials:')
print(f'  Email: {user.email}')
print(f'  Password: {password}')
print(f'  User Type: {user.user_type}')
print(f'  Superuser: {user.is_superuser}')
print(f'  Staff: {user.is_staff}')
