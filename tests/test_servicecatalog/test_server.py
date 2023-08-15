"""Test different server responses."""

import moto.server as server
from moto import mock_servicecatalog, mock_s3


@mock_servicecatalog
def test_servicecatalog_create_portfolio():
    backend = server.create_backend_app("servicecatalog")
    test_client = backend.test_client()

    resp = test_client.post(
        "/",
        data={"Name": "Portfolio Name"},
        headers={"X-Amz-Target": "servicecatalog.CreatePortfolio"},
    )

    assert resp.status_code == 200
    assert "PortfolioDetail" in str(resp.data)


@mock_servicecatalog
def test_servicecatalog_create_product():
    backend = server.create_backend_app("servicecatalog")
    test_client = backend.test_client()

    resp = test_client.post(
        "/",
        data={"Name": "Portfolio Name"},
        headers={"X-Amz-Target": "servicecatalog.CreateProduct"},
    )

    assert resp.status_code == 200
    assert "PortfolioDetail" in str(resp.data)
