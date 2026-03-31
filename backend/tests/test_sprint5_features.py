"""
Sprint 5 Testing - New Features:
1. Appointment History System - GET /api/appointments/{id}/history
2. CSV Export - GET /api/reports/daily/csv, GET /api/reports/weekly-hours/csv
3. Recurring Appointments - POST /api/appointments/recurring
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthAndSetup:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        """Get supervisor token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def televendas_token(self):
        """Get televendas token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tele1@agenda.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Televendas login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_supervisor_login(self, supervisor_token):
        """Test supervisor can login"""
        assert supervisor_token is not None
        print("✓ Supervisor login successful")
    
    def test_televendas_login(self, televendas_token):
        """Test televendas can login"""
        assert televendas_token is not None
        print("✓ Televendas login successful")


class TestAppointmentHistory:
    """Appointment History System Tests"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tele1@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_get_history_endpoint_exists(self, supervisor_token):
        """Test that history endpoint exists and returns proper structure"""
        # First, get any existing appointment
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        apt_response = requests.get(f"{BASE_URL}/api/appointments", headers=headers)
        assert apt_response.status_code == 200
        appointments = apt_response.json()
        
        if appointments:
            apt_id = appointments[0]["id"]
            history_response = requests.get(
                f"{BASE_URL}/api/appointments/{apt_id}/history",
                headers=headers
            )
            assert history_response.status_code == 200
            history = history_response.json()
            assert isinstance(history, list)
            print(f"✓ History endpoint returns list with {len(history)} entries")
        else:
            print("⚠ No appointments to test history - creating one")
            # Create a test appointment
            from datetime import datetime, timedelta
            future_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Get available slots
            slots_response = requests.get(
                f"{BASE_URL}/api/appointments/available-slots?date={future_date}",
                headers=headers
            )
            if slots_response.status_code == 200 and slots_response.json():
                slot = slots_response.json()[0]["time_slot"]
                create_response = requests.post(
                    f"{BASE_URL}/api/appointments",
                    headers=headers,
                    json={
                        "first_name": "TEST_History",
                        "last_name": "User",
                        "protocol_number": "TEST-HIST-001",
                        "date": future_date,
                        "time_slot": slot,
                        "has_chat": False
                    }
                )
                if create_response.status_code == 200:
                    apt_id = create_response.json()["id"]
                    history_response = requests.get(
                        f"{BASE_URL}/api/appointments/{apt_id}/history",
                        headers=headers
                    )
                    assert history_response.status_code == 200
                    print(f"✓ Created test appointment and verified history endpoint")
    
    def test_history_has_correct_structure(self, supervisor_token):
        """Test that history entries have the correct structure"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        apt_response = requests.get(f"{BASE_URL}/api/appointments", headers=headers)
        appointments = apt_response.json()
        
        if appointments:
            apt_id = appointments[0]["id"]
            history_response = requests.get(
                f"{BASE_URL}/api/appointments/{apt_id}/history",
                headers=headers
            )
            history = history_response.json()
            
            if history:
                entry = history[0]
                expected_fields = ['id', 'appointment_id', 'action', 'changed_by', 'changed_by_name', 'changed_at']
                for field in expected_fields:
                    assert field in entry, f"Missing field: {field}"
                print(f"✓ History entry has all required fields: {expected_fields}")
            else:
                print("⚠ No history entries found")
    
    def test_history_404_for_invalid_appointment(self, supervisor_token):
        """Test that history returns 404 for invalid appointment ID"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(
            f"{BASE_URL}/api/appointments/invalid-id-12345/history",
            headers=headers
        )
        assert response.status_code == 404
        print("✓ History returns 404 for invalid appointment ID")


class TestCSVExport:
    """CSV Export Tests"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tele1@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_daily_csv_export_supervisor(self, supervisor_token):
        """Test daily CSV export as supervisor"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/daily/csv",
            headers=headers
        )
        assert response.status_code == 200
        assert 'text/csv' in response.headers.get('Content-Type', '')
        
        # Check CSV has content
        content = response.text
        assert len(content) > 0
        # Check header row exists
        assert 'Data' in content or 'Horário' in content
        print(f"✓ Daily CSV export works - {len(content)} bytes")
    
    def test_daily_csv_export_forbidden_for_televendas(self, televendas_token):
        """Test daily CSV export is forbidden for televendas"""
        headers = {"Authorization": f"Bearer {televendas_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/daily/csv",
            headers=headers
        )
        assert response.status_code == 403
        print("✓ Daily CSV export forbidden for televendas (403)")
    
    def test_weekly_hours_csv_export_supervisor(self, supervisor_token):
        """Test weekly hours CSV export as supervisor"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours/csv",
            headers=headers
        )
        assert response.status_code == 200
        assert 'text/csv' in response.headers.get('Content-Type', '')
        
        content = response.text
        assert len(content) > 0
        # Check header row has expected columns
        assert 'Agente' in content or 'Horas' in content
        print(f"✓ Weekly hours CSV export works - {len(content)} bytes")
    
    def test_weekly_hours_csv_export_forbidden_for_televendas(self, televendas_token):
        """Test weekly hours CSV export is forbidden for televendas"""
        headers = {"Authorization": f"Bearer {televendas_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours/csv",
            headers=headers
        )
        assert response.status_code == 403
        print("✓ Weekly hours CSV export forbidden for televendas (403)")


class TestRecurringAppointments:
    """Recurring Appointments Tests"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def televendas_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "tele1@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_recurring_endpoint_exists(self, supervisor_token):
        """Test that recurring endpoint exists"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        from datetime import datetime, timedelta
        
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Get available slots
        slots_response = requests.get(
            f"{BASE_URL}/api/appointments/available-slots?date={future_date}",
            headers=headers
        )
        
        if slots_response.status_code == 200 and slots_response.json():
            slot = slots_response.json()[0]["time_slot"]
            
            response = requests.post(
                f"{BASE_URL}/api/appointments/recurring",
                headers=headers,
                json={
                    "first_name": "TEST_Recurring",
                    "last_name": "User",
                    "base_protocol": "TEST-BASE-001",
                    "new_protocol": "TEST-RECUR-001",
                    "date": future_date,
                    "time_slot": slot,
                    "has_chat": False
                }
            )
            # Should be 200 (success) or 400 (validation) but not 404/405
            assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
            
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert data["protocol_number"] == "TEST-RECUR-001"
                print(f"✓ Recurring appointment created successfully")
            else:
                print(f"⚠ Recurring endpoint exists but returned {response.status_code}: {response.text[:200]}")
        else:
            print("⚠ No available slots for recurring test")
    
    def test_recurring_requires_new_protocol(self, supervisor_token):
        """Test that recurring appointments require a new protocol number"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        from datetime import datetime, timedelta
        
        future_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Try to create without new_protocol
        response = requests.post(
            f"{BASE_URL}/api/appointments/recurring",
            headers=headers,
            json={
                "first_name": "TEST_NoProtocol",
                "last_name": "User",
                "base_protocol": "TEST-BASE-002",
                # Missing new_protocol
                "date": future_date,
                "time_slot": "09:00",
                "has_chat": False
            }
        )
        # Should be 422 (validation error) because new_protocol is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Recurring appointment requires new_protocol field")
    
    def test_recurring_info_endpoint(self, supervisor_token):
        """Test recurring info endpoint"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Get any appointment
        apt_response = requests.get(f"{BASE_URL}/api/appointments", headers=headers)
        appointments = apt_response.json()
        
        if appointments:
            apt_id = appointments[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/appointments/{apt_id}/recurring-info",
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "current" in data
            assert "is_recurring" in data
            assert "related_appointments" in data
            print(f"✓ Recurring info endpoint works correctly")
        else:
            print("⚠ No appointments to test recurring info")


class TestReportsEndpoints:
    """Reports endpoints for completeness"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_daily_report_endpoint(self, supervisor_token):
        """Test daily report JSON endpoint"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/daily",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "summary" in data
        assert "agents" in data
        print(f"✓ Daily report endpoint works - date: {data['date']}")
    
    def test_weekly_hours_endpoint(self, supervisor_token):
        """Test weekly hours JSON endpoint"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert "agents" in data
        print(f"✓ Weekly hours endpoint works - week: {data['week_start']} to {data['week_end']}")


class TestDarkModeBackendSupport:
    """Dark mode doesn't need backend changes, but verify theme toggle doesn't break anything"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        return response.json()["token"]
    
    def test_user_data_no_theme_field(self, supervisor_token):
        """Test that user data is retrieved correctly (theme is client-side)"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Theme preference is stored in localStorage on client-side
        # Backend user object should have standard fields
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "role" in data
        print("✓ User data retrieved correctly - theme is client-side")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
