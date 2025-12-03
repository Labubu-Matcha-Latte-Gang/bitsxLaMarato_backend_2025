from __future__ import annotations

from tests.base_test import BaseTest


class TestSwaggerUI(BaseTest):
    def test_root_redirects_to_swagger_ui(self):
        resp = self.client.get("/")
        assert resp.status_code == 302
        assert resp.headers.get("Location") == self.app.config["OPENAPI_SWAGGER_UI_PATH"]

    def test_swagger_ui_is_accessible(self):
        swagger_path = self.app.config["OPENAPI_SWAGGER_UI_PATH"]
        resp = self.client.get(swagger_path)
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Swagger UI" in body or "swagger-ui" in body.lower()
