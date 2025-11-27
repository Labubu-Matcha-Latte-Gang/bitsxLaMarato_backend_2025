def test_health_returns_200(client, helper):
    response = client.get(f"{helper.api_prefix}/health")
    assert response.status_code == 200
