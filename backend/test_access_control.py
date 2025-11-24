import requests

BASE_URL = "http://localhost:8003"

def get_token(username, password):
    response = requests.post(f"{BASE_URL}/auth/token", data={"username": username, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_access_control():
    print("Testing Access Control & Project Assignment...")
    
    # 1. Login as Admin
    admin_token = get_token("admin", "admin123")
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Create User and Project
    print("\nCreating user and project...")
    requests.post(f"{BASE_URL}/users/", json={"username": "user_p", "password_hash": "pass123", "role": "employee"}, headers=headers_admin)
    requests.post(f"{BASE_URL}/projects/", json={"name": "Secret Project", "description": "Secret"}, headers=headers_admin)
    
    # Get IDs
    users = requests.get(f"{BASE_URL}/users/", headers=headers_admin).json()
    user_id = next(u["id"] for u in users if u["username"] == "user_p")
    
    projects = requests.get(f"{BASE_URL}/projects/", headers=headers_admin).json()
    project_id = next(p["id"] for p in projects if p["name"] == "Secret Project")
    
    # 3. Verify User cannot see Secret Project initially
    print("\nVerifying initial visibility...")
    user_token = get_token("user_p", "pass123")
    headers_user = {"Authorization": f"Bearer {user_token}"}
    
    user_projects = requests.get(f"{BASE_URL}/projects/", headers=headers_user).json()
    visible_names = [p["name"] for p in user_projects]
    print(f"Visible projects: {visible_names}")
    if "Secret Project" in visible_names:
        print("FAIL: Secret Project should not be visible")
    else:
        print("PASS: Secret Project is hidden")
        
    if "Research" in visible_names:
        print("PASS: Default project is visible")
        
    # 4. Assign Project
    print("\nAssigning project...")
    requests.post(f"{BASE_URL}/users/{user_id}/projects/{project_id}", headers=headers_admin)
    
    # 5. Verify Visibility after assignment
    print("Verifying visibility after assignment...")
    user_projects = requests.get(f"{BASE_URL}/projects/", headers=headers_user).json()
    visible_names = [p["name"] for p in user_projects]
    if "Secret Project" in visible_names:
        print("PASS: Secret Project is now visible")
    else:
        print("FAIL: Secret Project is still hidden")
        
    # 6. Change Password
    print("\nChanging password...")
    resp = requests.put(f"{BASE_URL}/users/me/password", json={"current_password": "pass123", "new_password": "newpassword123"}, headers=headers_user)
    print(f"Change password status: {resp.status_code}")
    
    # 7. Verify New Password
    print("Verifying new password login...")
    new_token = get_token("user_p", "newpassword123")
    if new_token:
        print("PASS: Login with new password successful")
    else:
        print("FAIL: Login with new password failed")

    # Cleanup
    requests.delete(f"{BASE_URL}/users/{user_id}", headers=headers_admin)
    requests.delete(f"{BASE_URL}/projects/{project_id}", headers=headers_admin)

if __name__ == "__main__":
    test_access_control()
