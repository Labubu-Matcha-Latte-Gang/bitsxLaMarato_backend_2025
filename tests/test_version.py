def test_version_returns_configured_version(app, client, helper):
    response = client.get(helper.version_endpoint)
    assert response.status_code == 200
    assert response.data.decode() == app.config.get("API_VERSION")
