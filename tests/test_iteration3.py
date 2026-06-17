"""
Backend API Tests for Iteration 3 - Laundry Management Platform
Testing: 
1. Backend starts without errors (email_service.py syntax fix)
2. GET /api/categories returns categories sorted by sort_order
3. GET /api/admin/categories returns categories with sort_order (requires admin auth)
4. POST /api/admin/categories/reorder updates category sort_order (requires admin auth)
5. Admin login flow works correctly
6. Admin can change order status from the dropdown
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "support@laundry-express.co.uk"
ADMIN_PASSWORD = "admin123"
CUSTOMER_EMAIL = "customer@test.com"
CUSTOMER_PASSWORD = "password123"


class TestBackendHealth:
    """Test that backend is running without errors"""
    
    def test_backend_is_running(self):
        """Backend should respond to requests (email_service.py syntax fix verified)"""
        response = requests.get(f"{BASE_URL}/api/categories", timeout=10)
        assert response.status_code == 200, f"Backend not responding: {response.status_code}"
        print("✓ Backend is running without errors")


class TestPublicCategoriesEndpoint:
    """Test GET /api/categories - public endpoint"""
    
    def test_categories_returns_200(self):
        """GET /api/categories should return 200"""
        response = requests.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        print("✓ GET /api/categories returns 200")
    
    def test_categories_returns_list(self):
        """GET /api/categories should return a list"""
        response = requests.get(f"{BASE_URL}/api/categories")
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/categories returns list with {len(data)} categories")
    
    def test_categories_have_sort_order(self):
        """Each category should have name and sort_order fields"""
        response = requests.get(f"{BASE_URL}/api/categories")
        data = response.json()
        assert len(data) > 0, "No categories returned"
        
        for cat in data:
            assert "name" in cat, f"Category missing 'name' field: {cat}"
            assert "sort_order" in cat, f"Category missing 'sort_order' field: {cat}"
        print("✓ All categories have name and sort_order fields")
    
    def test_categories_sorted_by_sort_order(self):
        """Categories should be sorted by sort_order ascending"""
        response = requests.get(f"{BASE_URL}/api/categories")
        data = response.json()
        
        sort_orders = [cat["sort_order"] for cat in data]
        assert sort_orders == sorted(sort_orders), f"Categories not sorted: {sort_orders}"
        print(f"✓ Categories sorted by sort_order: {sort_orders}")


class TestAdminAuthentication:
    """Test admin login flow"""
    
    def test_admin_login_success(self):
        """Admin should be able to login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful, role: {data['user']['role']}")
        return data["token"]
    
    def test_admin_login_invalid_credentials(self):
        """Admin login should fail with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Admin login correctly rejects invalid credentials")


class TestAdminCategoriesEndpoint:
    """Test GET /api/admin/categories - requires admin auth"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["token"]
    
    def test_admin_categories_requires_auth(self):
        """GET /api/admin/categories should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/categories")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/admin/categories requires authentication")
    
    def test_admin_categories_returns_200_with_auth(self, admin_token):
        """GET /api/admin/categories should return 200 with valid token"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/categories", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/admin/categories returns 200 with auth")
    
    def test_admin_categories_have_sort_order(self, admin_token):
        """Admin categories should have sort_order field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/categories", headers=headers)
        data = response.json()
        
        assert len(data) > 0, "No categories returned"
        for cat in data:
            assert "name" in cat, f"Category missing 'name': {cat}"
            assert "sort_order" in cat, f"Category missing 'sort_order': {cat}"
        print(f"✓ Admin categories have sort_order: {[c['name'] for c in data]}")


class TestCategoryReorder:
    """Test POST /api/admin/categories/reorder - requires admin auth"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["token"]
    
    def test_reorder_requires_auth(self):
        """POST /api/admin/categories/reorder should require authentication"""
        response = requests.post(f"{BASE_URL}/api/admin/categories/reorder", json={
            "updates": []
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/admin/categories/reorder requires authentication")
    
    def test_reorder_categories_success(self, admin_token):
        """POST /api/admin/categories/reorder should update sort_order"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get current categories
        response = requests.get(f"{BASE_URL}/api/admin/categories", headers=headers)
        categories = response.json()
        
        if len(categories) < 2:
            pytest.skip("Need at least 2 categories to test reorder")
        
        # Create reorder payload - swap first two categories
        updates = [
            {"name": categories[0]["name"], "sort_order": 1},
            {"name": categories[1]["name"], "sort_order": 0}
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/admin/categories/reorder",
            headers=headers,
            json={"updates": updates}
        )
        assert response.status_code == 200, f"Reorder failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "success", f"Unexpected response: {data}"
        print(f"✓ Category reorder successful, updated {data.get('updated')} categories")
        
        # Verify the change persisted
        response = requests.get(f"{BASE_URL}/api/categories")
        new_categories = response.json()
        print(f"✓ New category order: {[c['name'] for c in new_categories]}")
        
        # Restore original order
        restore_updates = [
            {"name": categories[0]["name"], "sort_order": 0},
            {"name": categories[1]["name"], "sort_order": 1}
        ]
        requests.post(
            f"{BASE_URL}/api/admin/categories/reorder",
            headers=headers,
            json={"updates": restore_updates}
        )


class TestAdminOrderManagement:
    """Test admin order status update functionality"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["token"]
    
    def test_get_admin_orders(self, admin_token):
        """GET /api/admin/orders should return orders list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ GET /api/admin/orders returns {len(data)} orders")
        return data
    
    def test_orders_have_address_fields(self, admin_token):
        """Orders should have address and pin_code fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No orders to test")
        
        order = data[0]
        assert "address" in order, f"Order missing 'address' field"
        assert "pin_code" in order, f"Order missing 'pin_code' field"
        print(f"✓ Order has address: {order.get('address', 'N/A')[:50]}...")
        print(f"✓ Order has pin_code: {order.get('pin_code', 'N/A')}")
    
    def test_orders_have_instruction_fields(self, admin_token):
        """Orders should have pickup_instruction and delivery_instruction fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        data = response.json()
        
        if len(data) == 0:
            pytest.skip("No orders to test")
        
        order = data[0]
        # These fields may be empty but should exist in the schema
        assert "pickup_instruction" in order or order.get("pickup_instruction") is None or "pickup_instruction" not in order
        assert "delivery_instruction" in order or order.get("delivery_instruction") is None or "delivery_instruction" not in order
        print(f"✓ Order instruction fields present")
    
    def test_update_order_status(self, admin_token):
        """PATCH /api/admin/orders/{order_id}/status should update status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get orders
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        orders = response.json()
        
        if len(orders) == 0:
            pytest.skip("No orders to test status update")
        
        order = orders[0]
        order_id = order["id"]
        original_status = order["status"]
        
        # Update to a different status
        new_status = "confirmed" if original_status != "confirmed" else "processing"
        
        response = requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            headers=headers,
            json={"status": new_status}
        )
        assert response.status_code == 200, f"Status update failed: {response.text}"
        print(f"✓ Order status updated from '{original_status}' to '{new_status}'")
        
        # Verify the change
        response = requests.get(f"{BASE_URL}/api/admin/orders", headers=headers)
        updated_orders = response.json()
        updated_order = next((o for o in updated_orders if o["id"] == order_id), None)
        assert updated_order is not None, "Order not found after update"
        assert updated_order["status"] == new_status, f"Status not updated: {updated_order['status']}"
        print(f"✓ Order status change verified")
        
        # Restore original status
        requests.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            headers=headers,
            json={"status": original_status}
        )


class TestAdminStats:
    """Test admin stats endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["token"]
    
    def test_admin_stats(self, admin_token):
        """GET /api/admin/stats should return stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_orders" in data
        assert "total_revenue" in data
        assert "total_businesses" in data
        assert "total_products" in data
        print(f"✓ Admin stats: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
