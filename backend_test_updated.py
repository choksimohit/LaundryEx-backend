import requests
import sys
import json
from datetime import datetime, timedelta

class LaundryExpressAPITester:
    def __init__(self, base_url="https://laundry-admin-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "status": "PASSED" if success else "FAILED",
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Response: {error_data}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            
            if success:
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_pincode_check(self):
        """Test pin code availability checker with correct pin codes"""
        print("\n🔍 Testing Pin Code Checker...")
        
        # Test valid pin code CO27FQ
        success, response = self.run_test(
            "Pin Code Check - Valid (CO27FQ)",
            "POST",
            "pincode/check",
            200,
            data={"pin_code": "CO27FQ"},
            headers={}  # No auth required
        )
        
        if success and response.get('available'):
            print(f"   Found {len(response.get('businesses', []))} businesses for CO27FQ")
        
        # Test valid pin code CO1
        success, response = self.run_test(
            "Pin Code Check - Valid (CO1)",
            "POST",
            "pincode/check",
            200,
            data={"pin_code": "CO1"},
            headers={}  # No auth required
        )
        
        # Test invalid pin code
        success, response = self.run_test(
            "Pin Code Check - Invalid (INVALID)",
            "POST",
            "pincode/check",
            200,
            data={"pin_code": "INVALID"},
            headers={}  # No auth required
        )
        
        if success and not response.get('available'):
            print("   Correctly returned no businesses for invalid pin code")

    def test_user_registration_login(self):
        """Test user registration and login"""
        print("\n👤 Testing User Registration & Login...")
        
        # Generate unique test user
        timestamp = datetime.now().strftime('%H%M%S')
        test_email = f"test_user_{timestamp}@test.com"
        test_password = "TestPass123!"
        
        # Test registration
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={
                "email": test_email,
                "password": test_password,
                "name": "Test User",
                "phone": "1234567890"
            },
            headers={}  # No auth required
        )
        
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Registered user: {test_email}")
        
        # Test login
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": test_email,
                "password": test_password
            },
            headers={}  # No auth required
        )
        
        if success and 'token' in response:
            self.token = response['token']
            print(f"   Logged in user: {test_email}")

    def test_admin_login(self):
        """Test admin login with correct credentials"""
        print("\n🔐 Testing Admin Login...")
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": "admin@laundry-express.co.uk",
                "password": "admin123"
            },
            headers={}  # No auth required
        )
        
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin logged in successfully")

    def test_service_types_api(self):
        """Test service types API"""
        print("\n🏷️ Testing Service Types API...")
        
        success, response = self.run_test(
            "Get Service Types",
            "GET",
            "service-types",
            200,
            headers={}  # No auth required
        )
        
        if success:
            service_types = response if isinstance(response, list) else []
            print(f"   Found {len(service_types)} service types")
            for st in service_types:
                print(f"     - {st.get('name', 'Unknown')}")
            return service_types
        return []

    def test_categories_api(self, service_type=None):
        """Test categories API"""
        print(f"\n📂 Testing Categories API{' for ' + service_type if service_type else ''}...")
        
        endpoint = "categories"
        if service_type:
            endpoint += f"?service_type={service_type}"
        
        success, response = self.run_test(
            f"Get Categories{' for ' + service_type if service_type else ''}",
            "GET",
            endpoint,
            200,
            headers={}  # No auth required
        )
        
        if success:
            categories = response if isinstance(response, list) else []
            print(f"   Found {len(categories)} categories")
            for cat in categories:
                print(f"     - {cat.get('name', 'Unknown')}")
            return categories
        return []

    def test_products_api(self, service_type=None):
        """Test products API"""
        print(f"\n🧺 Testing Products API{' for ' + service_type if service_type else ''}...")
        
        endpoint = "products"
        if service_type:
            endpoint += f"?service_type={service_type}"
        
        success, response = self.run_test(
            f"Get Products{' for ' + service_type if service_type else ''}",
            "GET",
            endpoint,
            200,
            headers={}  # No auth required
        )
        
        if success:
            products = response if isinstance(response, list) else []
            print(f"   Found {len(products)} products")
            if products:
                print(f"     Sample product: {products[0].get('name', 'Unknown')} - £{products[0].get('price', 0)}")
            return products
        return []

    def test_order_creation(self, products):
        """Test order creation with new product structure"""
        print("\n📦 Testing Order Creation...")
        
        if not products:
            self.log_test("Order Creation", False, "No products available for testing")
            return None
        
        # Use first product for test order
        product = products[0]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # Calculate quantity to meet £30 minimum
        quantity_needed = max(2, int(30 / product['price']) + 1)
        total_amount = product['price'] * quantity_needed
        
        order_data = {
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "category": product['category'],
                "subcategory": product.get('subcategory'),
                "business_id": product['business_id'],
                "business_name": product['business_name'],
                "price": product['price'],
                "quantity": quantity_needed
            }],
            "pickup_date": tomorrow,
            "pickup_time": "10:00",
            "delivery_date": day_after,
            "delivery_time": "15:00",
            "address": "123 Test Street, Colchester",
            "pin_code": "CO27FQ",
            "payment_method": "cod",
            "total_amount": total_amount
        }
        
        success, response = self.run_test(
            "Create Order",
            "POST",
            "orders",
            200,
            data=order_data
        )
        
        if success and 'order_id' in response:
            print(f"   Created order: {response['order_id']}")
            return response['order_id']
        return None

    def test_order_retrieval(self):
        """Test order retrieval"""
        print("\n📋 Testing Order Retrieval...")
        
        success, response = self.run_test(
            "Get User Orders",
            "GET",
            "orders",
            200
        )
        
        if success:
            orders = response if isinstance(response, list) else []
            print(f"   Found {len(orders)} orders for user")

    def test_admin_functionality(self):
        """Test admin functionality"""
        print("\n👨‍💼 Testing Admin Functionality...")
        
        if not self.admin_token:
            self.log_test("Admin Tests", False, "No admin token available")
            return
        
        # Temporarily store user token and use admin token
        user_token = self.token
        self.token = self.admin_token
        
        # Test admin stats
        success, response = self.run_test(
            "Admin Stats",
            "GET",
            "admin/stats",
            200
        )
        
        if success:
            stats = response
            print(f"   Stats - Orders: {stats.get('total_orders', 0)}, Revenue: £{stats.get('total_revenue', 0)}")
            print(f"   Stats - Businesses: {stats.get('total_businesses', 0)}, Products: {stats.get('total_products', 0)}")
        
        # Test admin orders
        success, response = self.run_test(
            "Admin Orders",
            "GET",
            "admin/orders",
            200
        )
        
        if success:
            orders = response if isinstance(response, list) else []
            print(f"   Found {len(orders)} total orders")
        
        # Test admin businesses
        success, response = self.run_test(
            "Admin Businesses",
            "GET",
            "admin/businesses",
            200
        )
        
        if success:
            businesses = response if isinstance(response, list) else []
            print(f"   Found {len(businesses)} businesses")
            if businesses:
                business_id = businesses[0]['id']
                
                # Test create product
                success, response = self.run_test(
                    "Create Product",
                    "POST",
                    "admin/products",
                    200,
                    data={
                        "business_id": business_id,
                        "service_type": "Dry Cleaning",
                        "category": "Tops",
                        "subcategory": "Shirts",
                        "name": f"Test Product {datetime.now().strftime('%H%M%S')}",
                        "price": 15.99,
                        "icon_url": None
                    }
                )
                
                if success:
                    print(f"   Created product: {response.get('product_id', 'Unknown')}")
        
        # Test create business (platform admin only)
        success, response = self.run_test(
            "Create Business",
            "POST",
            "admin/businesses",
            200,
            data={
                "name": f"Test Business {datetime.now().strftime('%H%M%S')}",
                "owner_email": "testowner@test.com",
                "pin_codes": ["CO3", "CO4"]
            }
        )
        
        if success:
            print(f"   Created business: {response.get('business_id', 'Unknown')}")
        
        # Restore user token
        self.token = user_token

    def test_minimum_order_validation(self):
        """Test minimum order validation"""
        print("\n💰 Testing Minimum Order Validation...")
        
        order_data = {
            "items": [{
                "product_id": "test-product",
                "product_name": "Test Product",
                "category": "Test Category",
                "subcategory": None,
                "business_id": "test-business",
                "business_name": "Test Business",
                "price": 5.0,
                "quantity": 1
            }],
            "pickup_date": "2024-12-20",
            "pickup_time": "10:00",
            "delivery_date": "2024-12-21",
            "delivery_time": "15:00",
            "address": "123 Test Street",
            "pin_code": "CO27FQ",
            "payment_method": "cod",
            "total_amount": 5.0  # Below £30 minimum
        }
        
        success, response = self.run_test(
            "Minimum Order Validation",
            "POST",
            "orders",
            400,  # Should fail with 400
            data=order_data
        )

    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting Laundry Express Platform API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Test pin code checker (no auth required)
        self.test_pincode_check()
        
        # Test user registration and login
        self.test_user_registration_login()
        
        # Test admin login
        self.test_admin_login()
        
        # Test service types (no auth required)
        service_types = self.test_service_types_api()
        
        # Test categories (no auth required)
        if service_types:
            self.test_categories_api(service_types[0]['name'])
        
        # Test products (no auth required)
        products = self.test_products_api()
        if service_types:
            products_by_type = self.test_products_api(service_types[0]['name'])
        
        # Test order creation (requires auth)
        if self.token and products:
            order_id = self.test_order_creation(products)
            self.test_order_retrieval()
            self.test_minimum_order_validation()
        
        # Test admin functionality
        self.test_admin_functionality()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LaundryExpressAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results_updated.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': (tester.tests_passed/tester.tests_run*100) if tester.tests_run > 0 else 0,
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())