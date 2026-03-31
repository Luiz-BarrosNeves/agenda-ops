"""
Sprint 2 Tests: Filtros avançados, Notificações melhoradas, Auto-assign e Dashboard stats
"""
import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERVISOR_EMAIL = "supervisor2@agenda.com"
SUPERVISOR_PASSWORD = "password123"
TELEVENDAS_EMAIL = "tele1@agenda.com"
TELEVENDAS_PASSWORD = "password123"


class TestSetup:
    """Setup fixtures for testing"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        """Login as supervisor and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERVISOR_EMAIL,
            "password": SUPERVISOR_PASSWORD
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        return response.json()['token']
    
    @pytest.fixture(scope="class")
    def televendas_token(self):
        """Login as televendas and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TELEVENDAS_EMAIL,
            "password": TELEVENDAS_PASSWORD
        })
        assert response.status_code == 200, f"Televendas login failed: {response.text}"
        return response.json()['token']
    
    @pytest.fixture(scope="class")
    def supervisor_headers(self, supervisor_token):
        return {
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def televendas_headers(self, televendas_token):
        return {
            "Authorization": f"Bearer {televendas_token}",
            "Content-Type": "application/json"
        }


class TestFilteredAppointments(TestSetup):
    """Tests for GET /api/appointments/filtered endpoint"""
    
    def test_filtered_endpoint_exists(self, supervisor_headers):
        """Test that filtered appointments endpoint exists and responds"""
        response = requests.get(f"{BASE_URL}/api/appointments/filtered", headers=supervisor_headers)
        assert response.status_code == 200, f"Filtered endpoint should return 200, got {response.status_code}: {response.text}"
        assert isinstance(response.json(), list), "Response should be a list"
        print(f"✓ Filtered endpoint works - returned {len(response.json())} appointments")
    
    def test_filter_by_status(self, supervisor_headers):
        """Test filtering by status"""
        response = requests.get(
            f"{BASE_URL}/api/appointments/filtered",
            params={"status": "confirmado"},
            headers=supervisor_headers
        )
        assert response.status_code == 200
        appointments = response.json()
        for apt in appointments:
            assert apt['status'] == 'confirmado', f"Expected status 'confirmado', got '{apt['status']}'"
        print(f"✓ Filter by status works - {len(appointments)} confirmado appointments")
    
    def test_filter_by_date_range(self, supervisor_headers):
        """Test filtering by date range"""
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{BASE_URL}/api/appointments/filtered",
            params={"date_from": today, "date_to": tomorrow},
            headers=supervisor_headers
        )
        assert response.status_code == 200
        appointments = response.json()
        for apt in appointments:
            assert today <= apt['date'] <= tomorrow, f"Date {apt['date']} not in range"
        print(f"✓ Filter by date range works - {len(appointments)} appointments in range")
    
    def test_filter_by_search(self, supervisor_headers):
        """Test search by name or protocol"""
        # Create a test appointment first
        response = requests.get(
            f"{BASE_URL}/api/appointments/filtered",
            params={"search": "TEST"},
            headers=supervisor_headers
        )
        assert response.status_code == 200
        print(f"✓ Search filter works - returned {len(response.json())} results")
    
    def test_combined_filters(self, supervisor_headers):
        """Test multiple filters combined"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{BASE_URL}/api/appointments/filtered",
            params={
                "date_from": today,
                "status": "confirmado",
                "search": ""
            },
            headers=supervisor_headers
        )
        assert response.status_code == 200
        print(f"✓ Combined filters work - {len(response.json())} appointments")


class TestNotificationsEnhanced(TestSetup):
    """Tests for enhanced notifications system"""
    
    def test_get_all_notifications(self, supervisor_headers):
        """Test getting all notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=supervisor_headers)
        assert response.status_code == 200
        notifications = response.json()
        assert isinstance(notifications, list)
        print(f"✓ Get notifications works - {len(notifications)} notifications found")
        return notifications
    
    def test_get_unread_notifications(self, supervisor_headers):
        """Test getting only unread notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            params={"read": False},
            headers=supervisor_headers
        )
        assert response.status_code == 200
        notifications = response.json()
        for notif in notifications:
            assert notif['read'] == False, "Should only return unread notifications"
        print(f"✓ Get unread notifications works - {len(notifications)} unread")
    
    def test_mark_all_read_endpoint(self, supervisor_headers):
        """Test PUT /api/notifications/read-all endpoint"""
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=supervisor_headers)
        assert response.status_code == 200
        result = response.json()
        assert 'message' in result
        print(f"✓ Mark all read works - {result['message']}")
    
    def test_delete_notification_endpoint(self, supervisor_headers):
        """Test DELETE /api/notifications/{id} endpoint"""
        # First get notifications to find one to delete
        get_response = requests.get(f"{BASE_URL}/api/notifications", headers=supervisor_headers)
        notifications = get_response.json()
        
        if notifications:
            notif_id = notifications[0]['id']
            response = requests.delete(f"{BASE_URL}/api/notifications/{notif_id}", headers=supervisor_headers)
            assert response.status_code == 200
            print(f"✓ Delete notification works - deleted {notif_id}")
        else:
            # Test with invalid ID to verify endpoint exists
            response = requests.delete(f"{BASE_URL}/api/notifications/invalid-id", headers=supervisor_headers)
            assert response.status_code == 404, "Should return 404 for non-existent notification"
            print("✓ Delete notification endpoint exists (no notifications to delete)")
    
    def test_delete_all_read_notifications(self, supervisor_headers):
        """Test DELETE /api/notifications endpoint"""
        response = requests.delete(f"{BASE_URL}/api/notifications", headers=supervisor_headers)
        assert response.status_code == 200
        result = response.json()
        assert 'message' in result
        print(f"✓ Delete all read notifications works - {result['message']}")


class TestDashboardStats(TestSetup):
    """Tests for GET /api/stats/dashboard endpoint"""
    
    def test_dashboard_stats_endpoint(self, supervisor_headers):
        """Test dashboard stats endpoint exists and returns data"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=supervisor_headers)
        assert response.status_code == 200, f"Dashboard stats should return 200, got {response.status_code}: {response.text}"
        
        stats = response.json()
        
        # Verify response structure
        assert 'date' in stats, "Stats should include date"
        assert 'total' in stats, "Stats should include total"
        assert 'by_status' in stats, "Stats should include by_status"
        assert 'agents' in stats, "Stats should include agents"
        
        # Verify by_status structure
        by_status = stats['by_status']
        expected_statuses = ['pendentes', 'confirmados', 'emitidos', 'reagendar', 'presencial', 'cancelados']
        for status in expected_statuses:
            assert status in by_status, f"by_status should include {status}"
        
        print(f"✓ Dashboard stats works - date: {stats['date']}, total: {stats['total']}")
        print(f"  - Status breakdown: pendentes={by_status['pendentes']}, confirmados={by_status['confirmados']}")
        print(f"  - Agents: {len(stats['agents'])} agents tracked")
    
    def test_dashboard_stats_with_specific_date(self, supervisor_headers):
        """Test dashboard stats with specific date parameter"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{BASE_URL}/api/stats/dashboard",
            params={"date": tomorrow},
            headers=supervisor_headers
        )
        assert response.status_code == 200
        stats = response.json()
        assert stats['date'] == tomorrow, f"Stats should be for {tomorrow}"
        print(f"✓ Dashboard stats with date param works - date: {stats['date']}")
    
    def test_dashboard_stats_forbidden_for_non_supervisor(self, televendas_headers):
        """Test that televendas cannot access dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=televendas_headers)
        assert response.status_code == 403, f"Televendas should not access stats, got {response.status_code}"
        print("✓ Dashboard stats correctly restricted - televendas gets 403")


class TestAutoAssignSystem(TestSetup):
    """Tests for auto-assign background task"""
    
    def test_auto_assign_field_in_stats(self, supervisor_headers):
        """Test that auto_assigned count is tracked in stats"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=supervisor_headers)
        assert response.status_code == 200
        stats = response.json()
        
        assert 'auto_assigned' in stats, "Stats should include auto_assigned count"
        print(f"✓ Auto-assign tracking works - {stats['auto_assigned']} auto-assigned today")
    
    def test_create_pending_appointment(self, televendas_headers, supervisor_headers):
        """Test creating a pending appointment that could trigger auto-assign"""
        # Create appointment for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        appointment_data = {
            "first_name": "TEST_AutoAssign",
            "last_name": "TestUser",
            "protocol_number": "TEST-AA-001",
            "additional_protocols": [],
            "has_chat": False,
            "date": tomorrow,
            "time_slot": "10:00",
            "notes": "Test auto-assign"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json=appointment_data,
            headers=televendas_headers
        )
        assert response.status_code == 200, f"Should create appointment, got {response.status_code}: {response.text}"
        
        apt = response.json()
        assert apt['status'] == 'pendente_atribuicao', "New appointment should be pending"
        assert apt['user_id'] is None, "New appointment should not have user assigned"
        
        print(f"✓ Created pending appointment {apt['id']} - ready for auto-assign")
        
        # Clean up - assign it manually to avoid leaving pending
        time.sleep(1)
        
        # Get attendants to assign
        attendants_response = requests.get(f"{BASE_URL}/api/users/attendants", headers=supervisor_headers)
        if attendants_response.status_code == 200 and attendants_response.json():
            agent_id = attendants_response.json()[0]['id']
            assign_response = requests.put(
                f"{BASE_URL}/api/appointments/{apt['id']}/assign",
                json={"user_id": agent_id},
                headers=supervisor_headers
            )
            if assign_response.status_code == 200:
                print(f"  - Cleaned up: assigned to agent {agent_id}")


class TestAttendantsEndpoint(TestSetup):
    """Tests for attendants endpoint used by filters"""
    
    def test_get_attendants(self, supervisor_headers):
        """Test GET /api/users/attendants returns agent list"""
        response = requests.get(f"{BASE_URL}/api/users/attendants", headers=supervisor_headers)
        assert response.status_code == 200, f"Should return 200, got {response.status_code}"
        
        agents = response.json()
        assert isinstance(agents, list)
        for agent in agents:
            assert agent['role'] == 'agente', "Should only return agents"
            assert agent['approved'] == True, "Should only return approved agents"
        
        print(f"✓ Get attendants works - {len(agents)} agents available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
