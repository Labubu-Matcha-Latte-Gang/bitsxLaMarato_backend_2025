from tests.base_test import BaseTest


class TestHealth(BaseTest):
    def test_health_returns_200(self):
        response = self.client.get(f"{self.api_prefix}/health")
        assert response.status_code == 200
