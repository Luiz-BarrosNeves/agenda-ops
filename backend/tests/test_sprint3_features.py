"""
Sprint 3 Backend Tests - AgendaHub Sistema de Presença e Relatórios
Features tested:
- Heartbeat/Presence System
- Agent Presence Status
- Daily Reports
- Weekly Hours Reports
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthSetup:
    """Authentication setup for testing"""
    
    @pytest.fixture(scope="class")
    def supervisor_token(self):
        """Login as supervisor"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        if response.status_code != 200:
            pytest.skip("Supervisor login failed - skipping tests")
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def agent_token(self):
        """Login as agent"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agente1@agenda.com",
            "password": "password123"
        })
        if response.status_code != 200:
            pytest.skip("Agent login failed - skipping tests")
        return response.json()["token"]


class TestPresenceHeartbeat(TestAuthSetup):
    """Test heartbeat/presence endpoints"""
    
    def test_heartbeat_as_supervisor(self, supervisor_token):
        """POST /api/presence/heartbeat should update online status"""
        response = requests.post(
            f"{BASE_URL}/api/presence/heartbeat",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "online"
        assert "timestamp" in data
        print(f"Heartbeat successful: {data}")
    
    def test_heartbeat_as_agent(self, agent_token):
        """POST /api/presence/heartbeat should work for agents"""
        response = requests.post(
            f"{BASE_URL}/api/presence/heartbeat",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "online"
        print(f"Agent heartbeat successful: {data}")
    
    def test_heartbeat_unauthorized(self):
        """POST /api/presence/heartbeat should fail without auth"""
        response = requests.post(f"{BASE_URL}/api/presence/heartbeat")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_go_offline(self, agent_token):
        """POST /api/presence/offline should mark user as offline"""
        response = requests.post(
            f"{BASE_URL}/api/presence/offline",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "offline"
        print(f"Go offline successful: {data}")


class TestAgentsPresence(TestAuthSetup):
    """Test agent presence listing"""
    
    def test_get_agents_presence_as_supervisor(self, supervisor_token):
        """GET /api/presence/agents should return agent list with status"""
        response = requests.get(
            f"{BASE_URL}/api/presence/agents",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of agents"
        
        if len(data) > 0:
            agent = data[0]
            assert "id" in agent
            assert "name" in agent
            assert "email" in agent
            assert "is_online" in agent
            assert isinstance(agent["is_online"], bool)
            print(f"Found {len(data)} agents with presence data")
            for a in data:
                print(f"  - {a['name']}: {'online' if a['is_online'] else 'offline'}")
        else:
            print("No agents found in system")
    
    def test_get_agents_presence_unauthorized_for_agent(self, agent_token):
        """GET /api/presence/agents should be restricted for agents"""
        response = requests.get(
            f"{BASE_URL}/api/presence/agents",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Agent correctly denied access to presence list")
    
    def test_get_agents_presence_no_auth(self):
        """GET /api/presence/agents should fail without auth"""
        response = requests.get(f"{BASE_URL}/api/presence/agents")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestDailyReports(TestAuthSetup):
    """Test daily report generation"""
    
    def test_daily_report_today(self, supervisor_token):
        """GET /api/reports/daily should return today's report"""
        response = requests.get(
            f"{BASE_URL}/api/reports/daily",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "date" in data
        assert "generated_at" in data
        assert "summary" in data
        assert "agents" in data
        
        summary = data["summary"]
        assert "total_appointments" in summary
        assert "by_status" in summary
        assert "total_hours_worked" in summary
        assert "auto_assigned" in summary
        
        assert isinstance(summary["total_appointments"], int)
        assert isinstance(summary["by_status"], dict)
        assert isinstance(summary["total_hours_worked"], (int, float))
        assert isinstance(summary["auto_assigned"], int)
        
        print(f"Daily report for {data['date']}:")
        print(f"  Total appointments: {summary['total_appointments']}")
        print(f"  By status: {summary['by_status']}")
        print(f"  Hours worked: {summary['total_hours_worked']}")
        print(f"  Auto-assigned: {summary['auto_assigned']}")
    
    def test_daily_report_with_date_param(self, supervisor_token):
        """GET /api/reports/daily?date=YYYY-MM-DD should work"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = requests.get(
            f"{BASE_URL}/api/reports/daily",
            params={"date": yesterday},
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["date"] == yesterday
        print(f"Report for {yesterday}: {data['summary']['total_appointments']} appointments")
    
    def test_daily_report_agent_data(self, supervisor_token):
        """GET /api/reports/daily should include per-agent breakdown"""
        response = requests.get(
            f"{BASE_URL}/api/reports/daily",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        agents = data["agents"]
        
        if len(agents) > 0:
            agent = agents[0]
            assert "id" in agent
            assert "name" in agent
            assert "total" in agent
            assert "by_status" in agent
            assert "hours_worked" in agent
            print(f"Agent breakdown for {agent['name']}: {agent['total']} appointments, {agent['hours_worked']}h")
    
    def test_daily_report_unauthorized_for_agent(self, agent_token):
        """GET /api/reports/daily should be restricted for agents"""
        response = requests.get(
            f"{BASE_URL}/api/reports/daily",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Agent correctly denied access to daily reports")


class TestWeeklyHoursReport(TestAuthSetup):
    """Test weekly hours calculation"""
    
    def test_weekly_hours_report(self, supervisor_token):
        """GET /api/reports/weekly-hours should return weekly balance"""
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert "generated_at" in data
        assert "agents" in data
        
        print(f"Weekly report: {data['week_start']} to {data['week_end']}")
        
        agents = data["agents"]
        if len(agents) > 0:
            agent = agents[0]
            assert "id" in agent
            assert "name" in agent
            assert "emitidos" in agent
            assert "hours_worked" in agent
            assert "weekly_target" in agent
            assert "balance" in agent
            assert "is_online" in agent
            
            assert isinstance(agent["emitidos"], int)
            assert isinstance(agent["hours_worked"], (int, float))
            assert isinstance(agent["weekly_target"], (int, float))
            assert isinstance(agent["balance"], (int, float))
            assert isinstance(agent["is_online"], bool)
            
            print(f"  {agent['name']}: {agent['hours_worked']}h worked, balance: {agent['balance']}h")
    
    def test_weekly_hours_has_correct_structure(self, supervisor_token):
        """Weekly hours should have balance calculation (hours - target)"""
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours",
            headers={"Authorization": f"Bearer {supervisor_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        for agent in data["agents"]:
            # Verify balance calculation
            expected_balance = round(agent["hours_worked"] - agent["weekly_target"], 2)
            actual_balance = agent["balance"]
            assert abs(actual_balance - expected_balance) < 0.01, \
                f"Balance mismatch for {agent['name']}: expected {expected_balance}, got {actual_balance}"
        
        print("Balance calculation verified for all agents")
    
    def test_weekly_hours_unauthorized_for_agent(self, agent_token):
        """GET /api/reports/weekly-hours should be restricted for agents"""
        response = requests.get(
            f"{BASE_URL}/api/reports/weekly-hours",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Agent correctly denied access to weekly hours report")


class TestHeartbeatUpdatesPresence:
    """Test that heartbeat correctly updates presence status"""
    
    def test_heartbeat_makes_agent_online(self):
        """After heartbeat, agent should appear online in presence list"""
        # Login as agent
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "agente1@agenda.com",
            "password": "password123"
        })
        if login_response.status_code != 200:
            pytest.skip("Agent login failed")
        
        agent_token = login_response.json()["token"]
        agent_id = login_response.json()["user"]["id"]
        
        # Send heartbeat
        heartbeat_response = requests.post(
            f"{BASE_URL}/api/presence/heartbeat",
            headers={"Authorization": f"Bearer {agent_token}"}
        )
        assert heartbeat_response.status_code == 200
        
        # Login as supervisor to check presence
        sup_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "supervisor2@agenda.com",
            "password": "password123"
        })
        if sup_login.status_code != 200:
            pytest.skip("Supervisor login failed")
        
        sup_token = sup_login.json()["token"]
        
        # Get presence list
        presence_response = requests.get(
            f"{BASE_URL}/api/presence/agents",
            headers={"Authorization": f"Bearer {sup_token}"}
        )
        assert presence_response.status_code == 200
        
        agents = presence_response.json()
        target_agent = next((a for a in agents if a["id"] == agent_id), None)
        
        if target_agent:
            assert target_agent["is_online"] == True, f"Agent should be online after heartbeat"
            print(f"Agent {target_agent['name']} correctly shown as online after heartbeat")
        else:
            print(f"Agent {agent_id} not found in presence list (may not be approved agent)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
