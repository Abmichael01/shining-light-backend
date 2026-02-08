
import os
import django
import sys

# Setup Django Environment
sys.path.append('/home/urkel/Desktop/MyProjects/Clients/shinninglight/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'serverConfig.settings')
django.setup()

from rest_framework.test import APIRequestFactory
from api.views.biometrics import StudentListView
from django.contrib.auth import get_user_model

User = get_user_model()

def test_endpoint():
    print("Testing StudentListView endpoint...")
    factory = APIRequestFactory()
    
    # Create a dummy request
    request = factory.get('/api/biometrics/students/')
    
    # Simulate Authenticated User
    try:
        user = User.objects.first()
        if not user:
            print("No users found in database!")
            return
        request.user = user
        print(f"Using user: {user.email}")
    except Exception as e:
        print(f"Error getting user: {e}")
        return

    # Call View
    try:
        view = StudentListView.as_view()
        response = view(request)
        print(f"Response Status: {response.status_code}")
        if response.status_code != 200:
            print("Response Data:", response.data)
        else:
            print(f"Success! Got {len(response.data)} students.")
    except Exception as e:
        print("EXCEPTION OCCURRED:")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_endpoint()
