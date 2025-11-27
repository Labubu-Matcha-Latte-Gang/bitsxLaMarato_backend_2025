from tests.base_test import BaseTest


class TestVersion(BaseTest):
    def test_version_returns_configured_version(self):
        response = self.client.get(self.version_endpoint)
        assert response.status_code == 200
        assert response.data.decode() == self.app.config.get("API_VERSION")
