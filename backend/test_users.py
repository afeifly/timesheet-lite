import requests

BASE_URL = "http://localhost:8003"

def get_token(username, password):
    response = requests.post(f"{BASE_URL}/auth/token", data={"username": username, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_user_management():
    print("Testing User Management...")
    
    # 1. Login as Admin
    admin_token = get_token("admin", "admin123")
    if not admin_token:
        print("Failed to login as admin")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. List Users
    print("\nListing users...")
    response = requests.get(f"{BASE_URL}/users/", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Users: {len(response.json())}")
    
    # 3. Create User
    print("\nCreating new user 'test_employee'...")
    new_user = {
        "username": "test_employee",
        "password_hash": "password123", # Sending plain password as per implementation
        "role": "employee"
    }
    response = requests.post(f"{BASE_URL}/users/", json=new_user, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        user_id = response.json()["id"]
        print(f"Created user ID: {user_id}")
        
        # 4. Verify Login with new user
        print("\nVerifying login with new user...")
        emp_token = get_token("test_employee", "password123")
        if emp_token:
            print("Login successful")
        else:
            print("Login failed")
            
        # 5. Delete User
        print(f"\nDeleting user ID: {user_id}...")
        response = requests.delete(f"{BASE_URL}/users/{user_id}", headers=headers)
        print(f"Status: {response.status_code}")
        
        # 6. Verify Deletion
        print("\nVerifying deletion...")
        response = requests.get(f"{BASE_URL}/users/", headers=headers)
        users = response.json()
        found = any(u["id"] == user_id for u in users)
        print(f"User found in list: {found}")
    else:
        print(f"Failed to create user: {response.text}")

if __name__ == "__main__":
    test_user_management()
