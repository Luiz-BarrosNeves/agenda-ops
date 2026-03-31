"""
Comprehensive tests for Team Scheduling Platform - AgendaHub
Tests cover:
- Login with televendas, supervisor, agente roles
- Appointment creation with new fields (first_name, last_name, protocol, additional_protocols, has_chat)
- Available slots endpoint (critical bug fix verification)
- Pending appointments for supervisor
- Assignment workflow
- File upload functionality
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/') or 'http://localhost:8000'

# Test credentials
TELEVENDAS_CREDS = {"email": "tele1@agenda.com", "password": "password123"}
SUPERVISOR_CREDS = {"email": "supervisor2@agenda.com", "password": "password123"}
AGENTE_CREDS = {"email": "agente1@agenda.com", "password": "password123"}


class TestAuthentication:
    """Authentication tests for all user roles"""
    
    def test_televendas_login(self):
        """Test login with televendas user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        assert response.status_code == 200, f"Televendas login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == TELEVENDAS_CREDS["email"]
        assert data["user"]["role"] == "televendas"
        assert data["user"]["approved"] == True
    
    def test_supervisor_login(self):
        """Test login with supervisor user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == SUPERVISOR_CREDS["email"]
        assert data["user"]["role"] == "supervisor"
        assert data["user"]["approved"] == True
    
    def test_agente_login(self):
        """Test login with agente user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=AGENTE_CREDS)
        assert response.status_code == 200, f"Agente login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == AGENTE_CREDS["email"]
        assert data["user"]["role"] == "agente"
        assert data["user"]["approved"] == True
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com", "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestAvailableSlots:
    """Tests for available slots endpoint - critical bug fix verification"""
    
    @pytest.fixture
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        return response.json()["token"]
    
    def test_available_slots_returns_data(self, televendas_token):
        """Verify available slots endpoint returns slots (critical bug fix)"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/appointments/available-slots",
            params={"date": today},
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        assert response.status_code == 200, f"Available slots failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        # Should have some slots available for future times
        if len(data) > 0:
            slot = data[0]
            assert "time_slot" in slot
            assert "available_agents" in slot
            assert "total_agents" in slot
            assert "status" in slot
    
    def test_available_slots_tomorrow(self, televendas_token):
        """Test available slots for tomorrow"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/appointments/available-slots",
            params={"date": tomorrow},
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Tomorrow should have all slots available
        assert len(data) > 0, "Tomorrow should have available slots"


class TestAppointmentCreation:
    """Tests for appointment creation with new fields"""
    
    @pytest.fixture
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        return response.json()["token"]
    
    def get_future_slot(self, token):
        """Get a future available slot"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/appointments/available-slots",
            params={"date": tomorrow},
            headers={"Authorization": f"Bearer {token}"}
        )
        slots = response.json()
        if len(slots) > 0:
            return tomorrow, slots[0]["time_slot"]
        return tomorrow, "09:00"
    
    def test_create_appointment_with_new_fields(self, televendas_token):
        """Test creating appointment with all new fields"""
        date, time_slot = self.get_future_slot(televendas_token)
        
        appointment_data = {
            "first_name": "TEST_João",
            "last_name": "TEST_Silva",
            "protocol_number": "TEST-2026-001234",
            "additional_protocols": ["TEST-2026-001235", "TEST-2026-001236"],
            "has_chat": True,
            "date": date,
            "time_slot": time_slot,
            "notes": "Teste com campos novos"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        data = response.json()
        
        # Verify new fields
        assert data["first_name"] == "TEST_João"
        assert data["last_name"] == "TEST_Silva"
        assert data["protocol_number"] == "TEST-2026-001234"
        assert data["additional_protocols"] == ["TEST-2026-001235", "TEST-2026-001236"]
        assert data["has_chat"] == True
        assert data["status"] == "pendente_atribuicao"
        assert data["user_id"] is None  # Not assigned yet
        
        return data["id"]
    
    def test_create_appointment_minimal(self, televendas_token):
        """Test creating appointment with minimal required fields"""
        date, time_slot = self.get_future_slot(televendas_token)
        
        appointment_data = {
            "first_name": "TEST_Maria",
            "last_name": "TEST_Santos",
            "protocol_number": "TEST-2026-MINIMAL",
            "has_chat": False,
            "date": date,
            "time_slot": "10:00"  # Use different slot
        }
        
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        data = response.json()
        
        assert data["first_name"] == "TEST_Maria"
        assert data["last_name"] == "TEST_Santos"
        assert data["has_chat"] == False
        assert data["additional_protocols"] == []
    
    def test_has_chat_toggle_true(self, televendas_token):
        """Test has_chat field with True value"""
        date, time_slot = self.get_future_slot(televendas_token)
        
        appointment_data = {
            "first_name": "TEST_Chat",
            "last_name": "TEST_True",
            "protocol_number": "TEST-CHAT-TRUE",
            "has_chat": True,
            "date": date,
            "time_slot": "11:00"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        
        assert response.status_code in [200, 201]
        assert response.json()["has_chat"] == True
    
    def test_has_chat_toggle_false(self, televendas_token):
        """Test has_chat field with False value"""
        date, time_slot = self.get_future_slot(televendas_token)
        
        appointment_data = {
            "first_name": "TEST_Chat",
            "last_name": "TEST_False",
            "protocol_number": "TEST-CHAT-FALSE",
            "has_chat": False,
            "date": date,
            "time_slot": "11:20"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        
        assert response.status_code in [200, 201]
        assert response.json()["has_chat"] == False


class TestPendingAssignments:
    """Tests for supervisor pending assignments workflow"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        return response.json()["token"]
    
    def test_supervisor_sees_pending_appointments(self, supervisor_token):
        """Test that supervisor can see pending appointments"""
        response = requests.get(
            f"{BASE_URL}/api/appointments/pending",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All pending appointments should have status pendente_atribuicao
        for apt in data:
            assert apt["status"] == "pendente_atribuicao"
    
    def test_supervisor_gets_attendants_list(self, supervisor_token):
        """Test that supervisor can get list of available agents"""
        response = requests.get(
            f"{BASE_URL}/api/users/attendants",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Should have at least one agent"
        for agent in data:
            assert agent["role"] == "agente"
            assert agent["approved"] == True


class TestAssignmentWorkflow:
    """Tests for the complete assignment workflow"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        return response.json()["token"]
    
    @pytest.fixture
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        return response.json()["token"]
    
    def test_full_assignment_workflow(self, televendas_token, supervisor_token):
        """Test complete workflow: create -> see pending -> assign"""
        # Step 1: Televendas creates appointment
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        appointment_data = {
            "first_name": "TEST_Workflow",
            "last_name": "TEST_Assignment",
            "protocol_number": "TEST-WORKFLOW-ASSIGN",
            "additional_protocols": [],
            "has_chat": True,
            "date": tomorrow,
            "time_slot": "14:00",
            "notes": "Test workflow assignment"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        appointment_id = create_response.json()["id"]
        
        # Step 2: Supervisor sees in pending list
        pending_response = requests.get(
            f"{BASE_URL}/api/appointments/pending",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert pending_response.status_code == 200
        pending_ids = [apt["id"] for apt in pending_response.json()]
        assert appointment_id in pending_ids, "Created appointment should be in pending list"
        
        # Step 3: Get agent to assign
        agents_response = requests.get(
            f"{BASE_URL}/api/users/attendants",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert agents_response.status_code == 200
        agents = agents_response.json()
        assert len(agents) > 0
        agent_id = agents[0]["id"]
        
        # Step 4: Supervisor assigns to agent
        assign_response = requests.put(
            f"{BASE_URL}/api/appointments/{appointment_id}/assign",
            json={"user_id": agent_id},
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert assign_response.status_code == 200, f"Assign failed: {assign_response.text}"
        
        assigned_apt = assign_response.json()
        assert assigned_apt["user_id"] == agent_id
        assert assigned_apt["status"] == "confirmado"
        
        # Step 5: Verify no longer in pending list
        pending_after = requests.get(
            f"{BASE_URL}/api/appointments/pending",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        pending_ids_after = [apt["id"] for apt in pending_after.json()]
        assert appointment_id not in pending_ids_after, "Assigned appointment should not be in pending list"


class TestFileUpload:
    """Tests for file upload functionality"""
    
    @pytest.fixture
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        return response.json()["token"]
    
    def test_upload_multiple_files(self, televendas_token):
        """Test uploading multiple files to an appointment"""
        # First create an appointment
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        appointment_data = {
            "first_name": "TEST_Upload",
            "last_name": "TEST_Files",
            "protocol_number": "TEST-UPLOAD-MULTI",
            "has_chat": False,
            "date": tomorrow,
            "time_slot": "15:00"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        assert create_response.status_code in [200, 201]
        appointment_id = create_response.json()["id"]
        
        # Upload multiple files
        files = [
            ('files', ('test_doc1.txt', b'Test document 1 content', 'text/plain')),
            ('files', ('test_doc2.txt', b'Test document 2 content', 'text/plain')),
        ]
        
        upload_response = requests.post(
            f"{BASE_URL}/api/appointments/{appointment_id}/upload",
            files=files,
            headers={"Authorization": f"Bearer {televendas_token}"}
        )
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        data = upload_response.json()
        assert "2 file(s) uploaded successfully" in data["message"]
        assert len(data["filenames"]) == 2


class TestCleanup:
    """Cleanup test data after tests"""
    
    @pytest.fixture
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        return response.json()["token"]
    
    def test_cleanup_test_appointments(self, supervisor_token):
        """Clean up TEST_ prefixed appointments"""
        # Get all appointments
        response = requests.get(
            f"{BASE_URL}/api/appointments",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        if response.status_code == 200:
            appointments = response.json()
            for apt in appointments:
                if apt.get("first_name", "").startswith("TEST_") or apt.get("protocol_number", "").startswith("TEST-"):
                    delete_response = requests.delete(
                        f"{BASE_URL}/api/appointments/{apt['id']}",
                        headers={"Authorization": f"Bearer {supervisor_token}"}
                    )
                    print(f"Cleaned up appointment: {apt['id']}")
        
        assert True  # Cleanup is best-effort
