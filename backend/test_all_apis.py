#!/usr/bin/env python3
"""Comprehensive API test script for Planner"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"
ERRORS = []
PASSED = []

def test(name, method, endpoint, expected_status=200, json_data=None, params=None):
    """Run a single test"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            resp = requests.post(url, json=json_data, params=params, timeout=60)
        elif method == "PUT":
            resp = requests.put(url, json=json_data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, params=params, timeout=30)
        else:
            ERRORS.append(f"{name}: Unknown method {method}")
            return None

        if resp.status_code == expected_status:
            PASSED.append(f"{name}")
            print(f"  PASS: {name}")
            return resp.json() if resp.text else {}
        else:
            ERRORS.append(f"{name}: Expected {expected_status}, got {resp.status_code} - {resp.text[:200]}")
            print(f"  FAIL: {name} - {resp.status_code}")
            return None
    except Exception as e:
        ERRORS.append(f"{name}: Exception - {str(e)}")
        print(f"  ERROR: {name} - {str(e)}")
        return None


def main():
    print("\n=== PLANNER API TEST SUITE ===\n")

    # Health check
    print("--- Health ---")
    test("Health check", "GET", "/health")

    # Projects
    print("\n--- Projects ---")
    projects = test("List projects", "GET", "/projects/")
    project_id = projects[0]["id"] if projects else None

    if not project_id:
        # Create a test project
        new_proj = test("Create project", "POST", "/projects/", json_data={
            "name": "Test Project",
            "description": "Auto-created for testing"
        })
        project_id = new_proj["id"] if new_proj else 1

    test("Get single project", "GET", f"/projects/{project_id}")

    # Tasks
    print("\n--- Tasks ---")
    tasks = test("List tasks", "GET", "/tasks/", params={"project_id": project_id})
    test("Create task", "POST", "/tasks/", json_data={
        "project_id": project_id,
        "title": "Test Task from API",
        "priority": "medium",
        "status": "todo"
    })
    tasks = test("List tasks after create", "GET", "/tasks/", params={"project_id": project_id})
    if tasks:
        task_id = tasks[0]["id"]
        test("Get single task", "GET", f"/tasks/{task_id}")
        test("Update task", "PUT", f"/tasks/{task_id}", json_data={"status": "in_progress"})

    # Epics
    print("\n--- Epics ---")
    epics = test("List epics", "GET", "/epics/", params={"project_id": project_id})
    new_epic = test("Create epic", "POST", "/epics/", json_data={
        "project_id": project_id,
        "name": "Test Epic",
        "description": "Auto-created for testing"
    })
    if new_epic:
        test("Get epic", "GET", f"/epics/{new_epic['id']}")
        test("Update epic", "PUT", f"/epics/{new_epic['id']}", json_data={"status": "in_progress"})

    # Sprints
    print("\n--- Sprints ---")
    sprints = test("List sprints", "GET", "/sprints/", params={"project_id": project_id})
    new_sprint = test("Create sprint", "POST", "/sprints/", json_data={
        "project_id": project_id,
        "name": "Test Sprint",
        "goal": "Auto-created for testing"
    })
    if new_sprint:
        test("Get sprint", "GET", f"/sprints/{new_sprint['id']}")
        test("Start sprint", "POST", f"/sprints/{new_sprint['id']}/start")

    # Labels
    print("\n--- Labels ---")
    test("List labels", "GET", "/labels/")

    # GitHub
    print("\n--- GitHub ---")
    test("GitHub status", "GET", "/github/status")
    test("GitHub repos", "GET", "/github/repos")

    # Gmail
    print("\n--- Gmail ---")
    test("Gmail status", "GET", "/gmail/status")
    test("List email filters", "GET", "/gmail/filters")
    test("List emails", "GET", "/gmail/emails")
    test("Calendar events", "GET", "/gmail/calendar")

    # WhatsApp
    print("\n--- WhatsApp ---")
    test("WhatsApp status", "GET", "/whatsapp/status")
    test("List WhatsApp groups", "GET", "/whatsapp/groups")
    test("List WhatsApp messages", "GET", "/whatsapp/messages")

    # Logs
    print("\n--- Logs ---")
    test("List error logs", "GET", "/logs/")

    # AI
    print("\n--- AI ---")
    test("AI status", "GET", "/ai/status")
    test("Create task from text", "POST", "/ai/create-task-from-text", json_data={
        "text": "Test task creation via API",
        "project_id": project_id
    })
    test("Daily digest", "GET", "/ai/daily-digest")

    # Summary
    print("\n" + "="*50)
    print(f"\nRESULTS: {len(PASSED)} passed, {len(ERRORS)} failed")
    print("="*50)

    if ERRORS:
        print("\nFAILURES:")
        for err in ERRORS:
            print(f"  - {err}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
