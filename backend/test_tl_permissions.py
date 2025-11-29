import requests
import sys
import datetime

BASE_URL = "http://localhost:8003"

def login(username, password):
    try:
        response = requests.post(f"{BASE_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code != 200:
            print(f"Login failed for {username}: {response.text}")
            return None
        return response.json()["access_token"]
    except Exception as e:
        print(f"Login exception: {e}")
        return None

def test_tl_permissions():
    print("Starting test_tl_permissions...")
    
    # 1. Login as Admin
    admin_token = login("admin", "admin123")
    if not admin_token:
        print("Could not login as admin.")
        return

    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create Team Leader
    tl_username = "test_tl"
    tl_password = "password123"
    
    # Check if exists
    try:
        response = requests.get(f"{BASE_URL}/users/", headers=headers_admin)
        if response.status_code != 200:
            print(f"Failed to get users: {response.status_code} {response.text}")
            return
        users = response.json()
    except Exception as e:
        print(f"Exception getting users: {e}")
        return

    tl_user = next((u for u in users if u["username"] == tl_username), None)
    
    if not tl_user:
        print("Creating Team Leader...")
        response = requests.post(f"{BASE_URL}/users/", json={
            "username": tl_username,
            "password_hash": tl_password,
            "role": "team_leader",
            "full_name": "Test Team Leader"
        }, headers=headers_admin)
        if response.status_code != 200:
            print(f"Failed to create TL: {response.text}")
            return
        tl_user = response.json()
        print(f"Created user: {tl_user}")
    else:
        print("Team Leader already exists.")

    tl_id = tl_user["id"]

    # 3. Login as Team Leader
    tl_token = login(tl_username, tl_password)
    if not tl_token:
        print("Could not login as TL.")
        return
    
    headers_tl = {"Authorization": f"Bearer {tl_token}"}
    
    # 4. Get a project ID
    projects = requests.get(f"{BASE_URL}/projects/", headers=headers_tl).json()
    if not projects:
        print("No projects found.")
        return
    project_id = projects[0]["id"]
    
    # 5. Test Assign Project to Self
    print(f"Testing Assign Project {project_id} to Self ({tl_id})...")
    response = requests.post(f"{BASE_URL}/users/{tl_id}/projects/{project_id}", headers=headers_tl)
    if response.status_code == 200 or (response.status_code == 200 and response.json().get("message") == "Already assigned"):
        print("SUCCESS: Assigned project to self.")
    else:
        print(f"FAILURE: Assign project failed: {response.status_code} {response.text}")

    # 6. Test Unassign Project from Self
    print(f"Testing Unassign Project {project_id} from Self ({tl_id})...")
    response = requests.delete(f"{BASE_URL}/users/{tl_id}/projects/{project_id}", headers=headers_tl)
    if response.status_code == 200:
        print("SUCCESS: Unassigned project from self.")
    else:
        print(f"FAILURE: Unassign project failed: {response.status_code} {response.text}")

    # 7. Test Verify Day for Self
    # First create a timesheet entry
    today = datetime.date.today().isoformat()
    print(f"Creating timesheet entry for {today}...")
    response = requests.post(f"{BASE_URL}/timesheets/", json={
        "user_id": tl_id,
        "project_id": project_id,
        "date": today,
        "hours": 4
    }, headers=headers_tl)
    
    if response.status_code != 200:
        print(f"Failed to create timesheet: {response.text}")
    else:
        print("Timesheet created.")
        
        # Verify it
        print("Testing Verify Day for Self...")
        response = requests.post(f"{BASE_URL}/timesheets/verify", json={
            "user_id": tl_id,
            "date": today
        }, headers=headers_tl)
        
        if response.status_code == 200:
            print("SUCCESS: Verified day for self.")
        else:
            print(f"FAILURE: Verify day failed: {response.status_code} {response.text}")

if __name__ == "__main__":
    test_tl_permissions()
