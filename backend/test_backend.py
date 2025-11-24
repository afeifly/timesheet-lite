import requests
import sys

BASE_URL = "http://localhost:8003"

def test_api():
    # 1. Login as Admin
    print("Logging in as Admin...")
    response = requests.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "admin123"})
    if response.status_code != 200:
        print(f"Failed to login: {response.text}")
        sys.exit(1)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Create Project
    print("Creating Project...")
    project_data = {"name": "Test Project", "description": "A test project"}
    response = requests.post(f"{BASE_URL}/projects/", json=project_data, headers=headers)
    if response.status_code == 200:
        print(f"Response: {response.text}")
        project_id = response.json()["id"]
        print(f"Project created with ID: {project_id}")
    elif response.status_code == 400 and "already exists" in response.text:
        print("Project already exists, skipping creation.")
        # Get the project to have an ID
        response = requests.get(f"{BASE_URL}/projects/", headers=headers)
        for p in response.json():
            if p["name"] == "Test Project":
                project_id = p["id"]
                break
    else:
        print(f"Failed to create project: {response.text}")
        sys.exit(1)

    # 3. Create Timesheet
    print("Creating Timesheet...")
    import datetime
    today = datetime.date.today().isoformat()
    timesheet_data = {
        "user_id": 1, # Admin user ID is likely 1
        "project_id": project_id,
        "date": today,
        "hours": 8
    }
    response = requests.post(f"{BASE_URL}/timesheets/", json=timesheet_data, headers=headers)
    if response.status_code == 200:
        print("Timesheet created.")
    else:
        print(f"Failed to create timesheet: {response.text}")
        # It might fail if we run this multiple times and exceed 40 hours, which is good!
        if "Weekly limit exceeded" in response.text:
            print("Weekly limit check working.")

    # 4. Get Reports
    print("Getting Reports...")
    start_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    end_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    response = requests.get(f"{BASE_URL}/reports/weekly?start_date={start_date}&end_date={end_date}", headers=headers)
    if response.status_code == 200:
        print(f"Reports received: {len(response.json())} items")
    else:
        print(f"Failed to get reports: {response.text}")

    print("Backend verification complete!")

if __name__ == "__main__":
    test_api()
