from __future__ import annotations

from tests.base_test import BaseTest


class TestSwaggerDocResource(BaseTest):
    def test_can_download_html(self):
        resp = self.client.get(f"{self.api_prefix}/swagger-doc")
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("text/html")
        body = resp.data.decode("utf-8", errors="ignore").lower()
        assert "<html" in body and "documentació openapi" in body
        assert "esquemes" in body

    def test_can_download_pdf(self):
        resp = self.client.get(f"{self.api_prefix}/swagger-doc", query_string={"format": "pdf"})
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type", "").startswith("application/pdf")
        assert resp.data.startswith(b"%PDF")
