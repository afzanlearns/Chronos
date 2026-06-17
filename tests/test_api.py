import json
from chronos.api.routes import create_app


class TestAPI:
    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_today_dashboard(self):
        response = self.client.get('/api/dashboard/today')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'stats' in data
        assert 'app_breakdown' in data
        assert 'incomplete_tasks' in data

    def test_week_dashboard(self):
        response = self.client.get('/api/dashboard/week')
        assert response.status_code == 200

    def test_get_tasks(self):
        response = self.client.get('/api/tasks')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_create_task(self):
        response = self.client.post('/api/tasks', json={
            'title': 'API test task',
            'priority': 'high'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data

    def test_complete_task(self):
        create_resp = self.client.post('/api/tasks', json={
            'title': 'Task to complete'
        })
        task_id = json.loads(create_resp.data)['id']

        response = self.client.post(f'/api/tasks/{task_id}/complete')
        assert response.status_code == 200

    def test_get_goals(self):
        response = self.client.get('/api/goals')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_set_goal(self):
        response = self.client.post('/api/goals', json={
            'app_name': 'chrome',
            'daily_limit_minutes': 120
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data
