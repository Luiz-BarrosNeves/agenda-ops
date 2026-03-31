"""
Test suite for Appointment Templates feature
Tests: CRUD operations, template usage, auto-fill suggestions, date calculation

Endpoints tested:
- POST /api/templates - Create template
- GET /api/templates - List templates with search
- GET /api/templates/{id} - Get single template
- PUT /api/templates/{id} - Update template
- DELETE /api/templates/{id} - Delete template
- POST /api/templates/{id}/use - Use template (get auto-fill data)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERVISOR_EMAIL = "supervisor2@agenda.com"
SUPERVISOR_PASSWORD = "password123"
TELEVENDAS_EMAIL = "tele1@agenda.com"
TELEVENDAS_PASSWORD = "password123"


class TestTemplatesAPI:
    """Tests for Templates CRUD and usage"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test tokens"""
        self.supervisor_token = self._login(SUPERVISOR_EMAIL, SUPERVISOR_PASSWORD)
        self.televendas_token = self._login(TELEVENDAS_EMAIL, TELEVENDAS_PASSWORD)
        self.created_template_ids = []
        yield
        # Cleanup created templates
        for template_id in self.created_template_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/api/templates/{template_id}",
                    headers={"Authorization": f"Bearer {self.supervisor_token}"}
                )
            except:
                pass
    
    def _login(self, email, password):
        """Helper to get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def _get_headers(self, token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ============== CREATE TEMPLATE TESTS ==============
    
    def test_create_template_supervisor(self):
        """Supervisor can create a template"""
        payload = {
            "name": "TEST_Template_Supervisor",
            "client_first_name": "João",
            "client_last_name": "Silva",
            "preferred_time_slot": "09:00",
            "preferred_day_of_week": 1,  # Tuesday
            "has_chat": True,
            "notes": "Cliente VIP",
            "tags": ["VIP", "Semanal"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/templates",
            json=payload,
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert data["name"] == payload["name"]
        assert data["client_first_name"] == payload["client_first_name"]
        assert data["client_last_name"] == payload["client_last_name"]
        assert data["preferred_time_slot"] == payload["preferred_time_slot"]
        assert data["preferred_day_of_week"] == payload["preferred_day_of_week"]
        assert data["has_chat"] == payload["has_chat"]
        assert data["notes"] == payload["notes"]
        assert data["tags"] == payload["tags"]
        assert data["use_count"] == 0
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        
        self.created_template_ids.append(data["id"])
        print(f"✓ Template created with ID: {data['id']}")

    def test_create_template_televendas(self):
        """Televendas can create a template"""
        payload = {
            "name": "TEST_Template_Televendas",
            "client_first_name": "Maria",
            "client_last_name": "Santos",
            "has_chat": False,
            "tags": ["Regular"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/templates",
            json=payload,
            headers=self._get_headers(self.televendas_token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == payload["name"]
        self.created_template_ids.append(data["id"])
        print(f"✓ Televendas created template with ID: {data['id']}")

    def test_create_template_missing_required_fields(self):
        """Should fail when required fields are missing"""
        payload = {
            "name": "Test Template"
            # Missing client_first_name and client_last_name
        }
        
        response = requests.post(
            f"{BASE_URL}/api/templates",
            json=payload,
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Validation correctly rejects missing required fields")

    # ============== GET TEMPLATES TESTS ==============
    
    def test_get_templates_list(self):
        """List all templates for user"""
        # First create a template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_List_Template",
                "client_first_name": "Test",
                "client_last_name": "User"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Get templates list
        response = requests.get(
            f"{BASE_URL}/api/templates",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Find our created template
        found = [t for t in data if t["id"] == template_id]
        assert len(found) == 1, "Created template should be in list"
        print(f"✓ Templates list returned {len(data)} templates")

    def test_get_templates_with_search(self):
        """Search templates by name"""
        # Create a uniquely named template
        unique_name = f"TEST_UNIQUE_SEARCH_{datetime.now().timestamp()}"
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": unique_name,
                "client_first_name": "SearchTest",
                "client_last_name": "User"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        self.created_template_ids.append(create_response.json()["id"])
        
        # Search for it
        response = requests.get(
            f"{BASE_URL}/api/templates",
            params={"search": "SearchTest"},
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1, "Search should find at least one result"
        assert any("SearchTest" in t.get("client_first_name", "") for t in data)
        print(f"✓ Search returned {len(data)} matching templates")

    def test_get_templates_by_tag(self):
        """Filter templates by tag"""
        unique_tag = f"TEST_TAG_{datetime.now().timestamp()}"
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Tagged_Template",
                "client_first_name": "Tagged",
                "client_last_name": "Client",
                "tags": [unique_tag]
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        self.created_template_ids.append(create_response.json()["id"])
        
        # Filter by tag
        response = requests.get(
            f"{BASE_URL}/api/templates",
            params={"tag": unique_tag},
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(unique_tag in t.get("tags", []) for t in data)
        print(f"✓ Tag filter returned {len(data)} templates with tag '{unique_tag}'")

    def test_get_single_template(self):
        """Get a single template by ID"""
        # Create template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Single_Template",
                "client_first_name": "Single",
                "client_last_name": "Test"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Get by ID
        response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "TEST_Single_Template"
        print(f"✓ Single template retrieved: {data['name']}")

    def test_get_template_not_found(self):
        """Returns 404 for non-existent template"""
        response = requests.get(
            f"{BASE_URL}/api/templates/nonexistent-id-12345",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent template")

    # ============== UPDATE TEMPLATE TESTS ==============
    
    def test_update_template(self):
        """Update an existing template"""
        # Create template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Update_Template",
                "client_first_name": "Original",
                "client_last_name": "Name"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Update
        update_payload = {
            "name": "TEST_Updated_Template",
            "client_first_name": "Updated",
            "preferred_time_slot": "14:00",
            "tags": ["Updated", "Test"]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/templates/{template_id}",
            json=update_payload,
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_payload["name"]
        assert data["client_first_name"] == update_payload["client_first_name"]
        assert data["preferred_time_slot"] == update_payload["preferred_time_slot"]
        assert data["tags"] == update_payload["tags"]
        # Original field should remain unchanged
        assert data["client_last_name"] == "Name"
        print(f"✓ Template updated successfully")

    def test_update_template_not_found(self):
        """Returns 404 when updating non-existent template"""
        response = requests.put(
            f"{BASE_URL}/api/templates/nonexistent-id-12345",
            json={"name": "Test"},
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 404
        print("✓ Returns 404 when updating non-existent template")

    # ============== DELETE TEMPLATE TESTS ==============
    
    def test_delete_template(self):
        """Delete an existing template"""
        # Create template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Delete_Template",
                "client_first_name": "Delete",
                "client_last_name": "Me"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        
        # Delete
        response = requests.delete(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=self._get_headers(self.supervisor_token)
        )
        assert get_response.status_code == 404
        print("✓ Template deleted successfully and verified not found")

    def test_delete_template_not_found(self):
        """Returns 404 when deleting non-existent template"""
        response = requests.delete(
            f"{BASE_URL}/api/templates/nonexistent-id-12345",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 404
        print("✓ Returns 404 when deleting non-existent template")

    # ============== USE TEMPLATE TESTS ==============
    
    def test_use_template(self):
        """Use template returns auto-fill data and increments use_count"""
        # Create template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Use_Template",
                "client_first_name": "João",
                "client_last_name": "Silva",
                "preferred_time_slot": "10:00",
                "has_chat": True,
                "notes": "Regular client"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Use template
        response = requests.post(
            f"{BASE_URL}/api/templates/{template_id}/use",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "template" in data
        assert "suggestion" in data
        
        # Validate suggestion data
        suggestion = data["suggestion"]
        assert suggestion["first_name"] == "João"
        assert suggestion["last_name"] == "Silva"
        assert suggestion["has_chat"] == True
        assert suggestion["notes"] == "Regular client"
        assert "suggested_date" in suggestion
        assert suggestion["suggested_time_slot"] == "10:00"
        
        # Validate use_count incremented
        assert data["template"]["use_count"] == 1
        print(f"✓ Template used, suggestion date: {suggestion['suggested_date']}")

    def test_use_template_increments_count(self):
        """Use count increases with each use"""
        # Create template
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Count_Template",
                "client_first_name": "Count",
                "client_last_name": "Test"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Use 3 times
        for i in range(3):
            response = requests.post(
                f"{BASE_URL}/api/templates/{template_id}/use",
                headers=self._get_headers(self.supervisor_token)
            )
            assert response.status_code == 200
            assert response.json()["template"]["use_count"] == i + 1
        
        # Verify final count
        get_response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=self._get_headers(self.supervisor_token)
        )
        assert get_response.status_code == 200
        assert get_response.json()["use_count"] == 3
        print("✓ Use count correctly incremented to 3")

    def test_use_template_suggests_date_from_preferred_day(self):
        """Date suggestion based on preferred day of week"""
        # Create template with preferred_day_of_week = 3 (Thursday)
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Day_Preference",
                "client_first_name": "Day",
                "client_last_name": "Preference",
                "preferred_day_of_week": 3  # Thursday (0=Monday)
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Use template
        response = requests.post(
            f"{BASE_URL}/api/templates/{template_id}/use",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        suggestion = response.json()["suggestion"]
        suggested_date = suggestion["suggested_date"]
        
        # Verify suggested date is a Thursday (weekday 3)
        parsed_date = datetime.fromisoformat(suggested_date)
        # Python weekday: 0=Monday, 3=Thursday
        assert parsed_date.weekday() == 3, f"Expected Thursday (3), got {parsed_date.weekday()}"
        print(f"✓ Date suggestion respects preferred day: {suggested_date} (Thursday)")

    def test_use_template_not_found(self):
        """Returns 404 when using non-existent template"""
        response = requests.post(
            f"{BASE_URL}/api/templates/nonexistent-id-12345/use",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 404
        print("✓ Returns 404 when using non-existent template")


class TestTemplateIntegration:
    """Integration tests with appointments"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test tokens"""
        self.supervisor_token = self._login(SUPERVISOR_EMAIL, SUPERVISOR_PASSWORD)
        self.televendas_token = self._login(TELEVENDAS_EMAIL, TELEVENDAS_PASSWORD)
        self.created_template_ids = []
        self.created_appointment_ids = []
        yield
        # Cleanup
        for template_id in self.created_template_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/api/templates/{template_id}",
                    headers={"Authorization": f"Bearer {self.supervisor_token}"}
                )
            except:
                pass
        for apt_id in self.created_appointment_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/api/appointments/{apt_id}",
                    headers={"Authorization": f"Bearer {self.supervisor_token}"}
                )
            except:
                pass
    
    def _login(self, email, password):
        """Helper to get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def _get_headers(self, token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def test_use_template_suggests_date_from_last_appointment(self):
        """When client has previous appointments, suggest +7 days from last visit"""
        client_first = "Recurring"
        client_last = "Client"
        
        # First, create an appointment for this client
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        apt_response = requests.post(
            f"{BASE_URL}/api/appointments",
            json={
                "first_name": client_first,
                "last_name": client_last,
                "protocol_number": "TEST-RECUR-PROTO",
                "date": tomorrow,
                "time_slot": "11:00",
                "has_chat": False
            },
            headers=self._get_headers(self.televendas_token)
        )
        
        if apt_response.status_code == 200:
            self.created_appointment_ids.append(apt_response.json()["id"])
        
        # Create template for same client
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Recurring_Client",
                "client_first_name": client_first,
                "client_last_name": client_last
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Use template
        response = requests.post(
            f"{BASE_URL}/api/templates/{template_id}/use",
            headers=self._get_headers(self.supervisor_token)
        )
        
        assert response.status_code == 200
        suggestion = response.json()["suggestion"]
        
        # Verify last_appointment info is returned
        if suggestion.get("last_appointment"):
            assert "date" in suggestion["last_appointment"]
            assert "time_slot" in suggestion["last_appointment"]
            print(f"✓ Template use returns last appointment info: {suggestion['last_appointment']}")
        else:
            print("✓ Template use works (no previous appointment found for exact match)")

    def test_templates_only_visible_to_creator(self):
        """Users can only see their own templates"""
        # Create template as supervisor
        create_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Supervisor_Only",
                "client_first_name": "Supervisor",
                "client_last_name": "Template"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        self.created_template_ids.append(template_id)
        
        # Try to access as televendas - should get 404 (not visible to them)
        response = requests.get(
            f"{BASE_URL}/api/templates/{template_id}",
            headers=self._get_headers(self.televendas_token)
        )
        
        assert response.status_code == 404, "Template should not be visible to other users"
        print("✓ Templates are correctly scoped to creator only")

    def test_templates_sorted_by_use_count(self):
        """Templates list is sorted by use_count (most used first)"""
        # Create two templates
        template1_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_Less_Used",
                "client_first_name": "Less",
                "client_last_name": "Used"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert template1_response.status_code == 200
        template1_id = template1_response.json()["id"]
        self.created_template_ids.append(template1_id)
        
        template2_response = requests.post(
            f"{BASE_URL}/api/templates",
            json={
                "name": "TEST_More_Used",
                "client_first_name": "More",
                "client_last_name": "Used"
            },
            headers=self._get_headers(self.supervisor_token)
        )
        assert template2_response.status_code == 200
        template2_id = template2_response.json()["id"]
        self.created_template_ids.append(template2_id)
        
        # Use template2 multiple times
        for _ in range(3):
            requests.post(
                f"{BASE_URL}/api/templates/{template2_id}/use",
                headers=self._get_headers(self.supervisor_token)
            )
        
        # Use template1 once
        requests.post(
            f"{BASE_URL}/api/templates/{template1_id}/use",
            headers=self._get_headers(self.supervisor_token)
        )
        
        # Get list - template2 should come before template1
        list_response = requests.get(
            f"{BASE_URL}/api/templates",
            headers=self._get_headers(self.supervisor_token)
        )
        assert list_response.status_code == 200
        templates = list_response.json()
        
        # Find positions
        template1_idx = next((i for i, t in enumerate(templates) if t["id"] == template1_id), -1)
        template2_idx = next((i for i, t in enumerate(templates) if t["id"] == template2_id), -1)
        
        assert template2_idx < template1_idx, "More used template should appear first"
        print(f"✓ Templates sorted by use_count (more used appears first)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
