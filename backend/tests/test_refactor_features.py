"""
Backend API Tests for AgendaHub Refactoring - Sprint 4
Tests for: Layout SaaS, AgendaCompleta slots, Dashboard metrics, Extra Hours Management
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERVISOR_CREDS = {"email": "supervisor2@agenda.com", "password": "password123"}
TELEVENDAS_CREDS = {"email": "tele1@agenda.com", "password": "password123"}

# Expected extra time slots
EXTRA_TIME_SLOTS = ['07:40', '12:40', '18:00', '18:20', '18:40']

@pytest.fixture(scope="module")
def supervisor_token():
    """Get supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
    assert response.status_code == 200, f"Supervisor login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture(scope="module")
def televendas_token():
    """Get televendas authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
    assert response.status_code == 200, f"Televendas login failed: {response.text}"
    return response.json()["token"]

@pytest.fixture
def supervisor_headers(supervisor_token):
    return {"Authorization": f"Bearer {supervisor_token}", "Content-Type": "application/json"}

@pytest.fixture
def televendas_headers(televendas_token):
    return {"Authorization": f"Bearer {televendas_token}", "Content-Type": "application/json"}

class TestAuthAndRoles:
    """Test authentication and role-based access"""
    
    def test_supervisor_login(self):
        """Supervisor can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPERVISOR_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "supervisor"
        assert "token" in data
        print("PASS: Supervisor login successful")
    
    def test_televendas_login(self):
        """Televendas can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=TELEVENDAS_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "televendas"
        print("PASS: Televendas login successful")

class TestSlotsAllEndpoint:
    """Test /api/slots/all endpoint - Agenda Completa"""
    
    def test_supervisor_can_access_slots(self, supervisor_headers):
        """Supervisor can access all slots"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        assert "total_agents" in data
        print(f"PASS: Supervisor can access slots, found {len(data['slots'])} slots")
    
    def test_televendas_can_access_slots(self, televendas_headers):
        """Televendas can access all slots (Agenda Completa)"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=televendas_headers)
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        print(f"PASS: Televendas can access slots, found {len(data['slots'])} slots")
    
    def test_slots_do_not_include_1240_by_default(self, supervisor_headers):
        """12:40 slot should NOT appear by default (it's an extra slot)"""
        today = datetime.now().strftime('%Y-%m-%d')
        # First, ensure extra hours are cleared
        requests.put(f"{BASE_URL}/api/extra-hours?date={today}&slots=", headers=supervisor_headers)
        
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        slot_times = [s["time_slot"] for s in data["slots"]]
        
        # 12:40 should NOT be in normal slots
        assert "12:40" not in slot_times, "12:40 should not appear when extra hours are disabled"
        print("PASS: 12:40 slot not shown by default")
    
    def test_slots_include_normal_lunch_slots(self, supervisor_headers):
        """Normal slots include 12:00 and 12:20 (not 12:40)"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        slot_times = [s["time_slot"] for s in data["slots"]]
        
        assert "12:00" in slot_times
        assert "12:20" in slot_times
        print("PASS: Normal lunch slots 12:00 and 12:20 are present")
    
    def test_slots_have_availability_info(self, supervisor_headers):
        """Slots include availability information"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["slots"]) > 0:
            slot = data["slots"][0]
            assert "available" in slot
            assert "occupied" in slot
            assert "pending" in slot
            assert "total_agents" in slot
            print("PASS: Slots have availability info")
    
    def test_slots_have_extra_flag(self, supervisor_headers):
        """Slots should have is_extra flag"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Activate 07:40 extra slot
        requests.put(f"{BASE_URL}/api/extra-hours?date={today}&slots=07:40", headers=supervisor_headers)
        
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        
        for slot in data["slots"]:
            if slot["time_slot"] == "07:40":
                assert slot.get("is_extra") == True
                print("PASS: Extra slot 07:40 has is_extra=True")
                break

class TestExtraHoursEndpoints:
    """Test extra hours management - /api/extra-hours"""
    
    def test_get_extra_hours(self, supervisor_headers):
        """Get extra hours for a date"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/extra-hours?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        assert "available_slots" in data
        assert "active_slots" in data
        assert set(data["available_slots"]) == set(EXTRA_TIME_SLOTS)
        print(f"PASS: Extra hours endpoint works, available slots: {data['available_slots']}")
    
    def test_update_extra_hours_supervisor(self, supervisor_headers):
        """Supervisor can enable extra hours"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Enable 07:40 and 18:00
        response = requests.put(
            f"{BASE_URL}/api/extra-hours?date={today}&slots=07:40&slots=18:00", 
            headers=supervisor_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "07:40" in data["active_slots"]
        assert "18:00" in data["active_slots"]
        print(f"PASS: Supervisor enabled extra hours: {data['active_slots']}")
    
    def test_update_extra_hours_televendas_forbidden(self, televendas_headers):
        """Televendas cannot modify extra hours"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.put(
            f"{BASE_URL}/api/extra-hours?date={today}&slots=12:40", 
            headers=televendas_headers
        )
        assert response.status_code == 403
        print("PASS: Televendas correctly blocked from modifying extra hours")
    
    def test_extra_hours_appear_in_slots(self, supervisor_headers):
        """Activated extra hours appear in /api/slots/all"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Enable 12:40 extra
        requests.put(f"{BASE_URL}/api/extra-hours?date={today}&slots=12:40", headers=supervisor_headers)
        
        response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        slot_times = [s["time_slot"] for s in data["slots"]]
        
        assert "12:40" in slot_times, "12:40 should appear when enabled as extra hour"
        print("PASS: Extra hour 12:40 appears in slots when enabled")
    
    def test_deactivate_extra_hours(self, supervisor_headers):
        """Supervisor can deactivate extra hours"""
        today = datetime.now().strftime('%Y-%m-%d')
        # Clear all extra hours
        response = requests.put(f"{BASE_URL}/api/extra-hours?date={today}&slots=", headers=supervisor_headers)
        assert response.status_code == 200
        
        # Verify 12:40 no longer appears
        slots_response = requests.get(f"{BASE_URL}/api/slots/all?date={today}", headers=supervisor_headers)
        data = slots_response.json()
        slot_times = [s["time_slot"] for s in data["slots"]]
        
        assert "12:40" not in slot_times
        print("PASS: Extra hours deactivated successfully")

class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    def test_supervisor_can_access_dashboard_stats(self, supervisor_headers):
        """Supervisor can access dashboard stats"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/stats/dashboard?date={today}", headers=supervisor_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_status" in data
        assert "auto_assigned" in data
        print(f"PASS: Dashboard stats - total: {data['total']}, by_status: {data['by_status']}")
    
    def test_televendas_cannot_access_dashboard_stats(self, televendas_headers):
        """Televendas cannot access dashboard stats"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/stats/dashboard?date={today}", headers=televendas_headers)
        assert response.status_code == 403
        print("PASS: Televendas correctly blocked from dashboard stats")

class TestSupervisorOnlyEndpoints:
    """Test endpoints that should only be accessible by supervisor"""
    
    def test_supervisor_can_access_pending(self, supervisor_headers):
        """Supervisor can access pending appointments"""
        response = requests.get(f"{BASE_URL}/api/appointments/pending", headers=supervisor_headers)
        assert response.status_code == 200
        print(f"PASS: Supervisor can access pending appointments")
    
    def test_televendas_cannot_access_pending(self, televendas_headers):
        """Televendas cannot access pending appointments"""
        response = requests.get(f"{BASE_URL}/api/appointments/pending", headers=televendas_headers)
        assert response.status_code == 403
        print("PASS: Televendas correctly blocked from pending appointments")
    
    def test_supervisor_can_access_users(self, supervisor_headers):
        """Supervisor can access users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=supervisor_headers)
        assert response.status_code == 200
        print("PASS: Supervisor can access users list")
    
    def test_televendas_cannot_access_users(self, televendas_headers):
        """Televendas cannot access users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=televendas_headers)
        assert response.status_code == 403
        print("PASS: Televendas correctly blocked from users list")
    
    def test_supervisor_can_access_presence(self, supervisor_headers):
        """Supervisor can access presence endpoint"""
        response = requests.get(f"{BASE_URL}/api/presence/agents", headers=supervisor_headers)
        assert response.status_code == 200
        print("PASS: Supervisor can access presence endpoint")
    
    def test_televendas_cannot_access_presence(self, televendas_headers):
        """Televendas cannot access presence endpoint"""
        response = requests.get(f"{BASE_URL}/api/presence/agents", headers=televendas_headers)
        assert response.status_code == 403
        print("PASS: Televendas correctly blocked from presence endpoint")

class TestTelevendasPermissions:
    """Test what Televendas can access"""
    
    def test_televendas_can_access_appointments(self, televendas_headers):
        """Televendas can access appointments"""
        response = requests.get(f"{BASE_URL}/api/appointments", headers=televendas_headers)
        assert response.status_code == 200
        print("PASS: Televendas can access appointments")
    
    def test_televendas_can_create_appointment(self, televendas_headers):
        """Televendas can create appointments"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        appointment_data = {
            "first_name": "TEST_Maria",
            "last_name": "TestSilva",
            "protocol_number": "TEST_PROTO_123456",
            "has_chat": False,
            "date": tomorrow,
            "time_slot": "10:00"
        }
        response = requests.post(f"{BASE_URL}/api/appointments", json=appointment_data, headers=televendas_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pendente_atribuicao"
        print(f"PASS: Televendas created appointment ID: {data['id']}")
        return data["id"]
    
    def test_televendas_can_access_available_slots(self, televendas_headers):
        """Televendas can access available slots"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        response = requests.get(f"{BASE_URL}/api/appointments/available-slots?date={tomorrow}", headers=televendas_headers)
        assert response.status_code == 200
        print("PASS: Televendas can access available slots")

class TestDateNavigation:
    """Test date navigation for Agenda Completa"""
    
    def test_can_get_slots_for_different_dates(self, supervisor_headers):
        """Can fetch slots for past, today, and future dates"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        for date in [yesterday, today, tomorrow]:
            response = requests.get(f"{BASE_URL}/api/slots/all?date={date}", headers=supervisor_headers)
            assert response.status_code == 200
            print(f"PASS: Can fetch slots for {date}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
