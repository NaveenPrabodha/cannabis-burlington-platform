"""Endpoint smoke tests. Hit each endpoint, verify status + shape."""

import pytest


@pytest.mark.asyncio
async def test_root(client):
    r = await client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["db_ok"] is True
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_categories(client):
    r = await client.get("/categories")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and len(items) >= 1
    assert {"name", "count"} <= set(items[0].keys())


@pytest.mark.asyncio
async def test_brands(client):
    r = await client.get("/brands")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_stores_pagination(client):
    r = await client.get("/stores", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert len(body["items"]) <= 5
    assert body["page"] == 1
    first = body["items"][0]
    assert "store_id" in first and "latitude" in first


@pytest.mark.asyncio
async def test_store_detail(client):
    r = await client.get("/stores", params={"page": 1, "page_size": 1})
    sid = r.json()["items"][0]["store_id"]

    r = await client.get(f"/stores/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["store_id"] == sid
    assert "product_count" in body


@pytest.mark.asyncio
async def test_store_not_found(client):
    r = await client.get("/stores/999999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_store_products(client):
    r = await client.get("/stores/1/products", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body


@pytest.mark.asyncio
async def test_list_products_filtered(client):
    r = await client.get(
        "/products", params={"category": "Flower", "page": 1, "page_size": 5, "sort": "-price"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(p["category"] == "Flower" for p in body["items"] if p.get("category"))


@pytest.mark.asyncio
async def test_product_detail(client):
    r = await client.get("/products", params={"page": 1, "page_size": 1, "sort": "stores"})
    pid = r.json()["items"][0]["product_id"]

    r = await client.get(f"/products/{pid}")
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == pid
    assert "available_at" in body


@pytest.mark.asyncio
async def test_deals(client):
    r = await client.get("/deals", params={"page": 1, "page_size": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(d["sale_price"] is not None for d in body["items"])


@pytest.mark.asyncio
async def test_search(client):
    r = await client.get("/search", params={"q": "kush", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "kush"
    assert "products" in body and "stores" in body


@pytest.mark.asyncio
async def test_new_arrivals(client):
    r = await client.get("/products/new-arrivals", params={"days": 30, "limit": 3})
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_featured(client):
    r = await client.get("/featured")
    assert r.status_code == 200
    body = r.json()
    assert "top_deals" in body and "new_arrivals" in body
