import requests
import sys
import json
from datetime import datetime, timedelta

class LaundryAPITester:
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
        """Test pin code availability checker"""
        print("\n🔍 Testing Pin Code Checker...")
        
        # Test valid pin code
        success, response = self.run_test(
            "Pin Code Check - Valid (SW1A1AA)",
            "POST",
            "pincode/check",
            200,
            data={"pin_code": "SW1A1AA"},
            headers={}  # No auth required
        )
        
        if success and response.get('available'):
            print(f"   Found {len(response.get('businesses', []))} businesses")
        
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
        """Test admin login"""
        print("\n🔐 Testing Admin Login...")
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": "admin@freshfold.com",
                "password": "admin123"
            },
            headers={}  # No auth required
        )
        
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   Admin logged in successfully")

    def test_services_api(self):
        """Test services API"""
        print("\n🧺 Testing Services API...")
        
        success, response = self.run_test(
            "Get All Services",
            "GET",
            "services",
            200,
            headers={}  # No auth required
        )
        
        if success:
            services = response if isinstance(response, list) else []
            print(f"   Found {len(services)} services")
            return services
        return []

    def test_order_creation(self, services):
        """Test order creation"""
        print("\n📦 Testing Order Creation...")
        
        if not services:
            self.log_test("Order Creation", False, "No services available for testing")
            return None
        
        # Use first service for test order
        service = services[0]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # Calculate quantity to meet £30 minimum
        quantity_needed = max(2, int(30 / service['base_price']) + 1)
        total_amount = service['base_price'] * quantity_needed
        
        order_data = {
            "items": [{
                "service_id": service['id'],
                "service_name": service['name'],
                "business_id": service['business_id'],
                "business_name": service['business_name'],
                "price": service['base_price'],
                "quantity": quantity_needed
            }],
            "pickup_date": tomorrow,
            "pickup_time": "10:00",
            "delivery_date": day_after,
            "delivery_time": "15:00",
            "address": "123 Test Street, London",
            "pin_code": "SW1A1AA",
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
        
        # Test create business (platform admin only)
        success, response = self.run_test(
            "Create Business",
            "POST",
            "admin/businesses",
            200,
            data={
                "name": f"Test Business {datetime.now().strftime('%H%M%S')}",
                "owner_email": "testowner@test.com",
                "pin_codes": ["SW1A3AA", "SW1A4AA"]
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
                "service_id": "test-service",
                "service_name": "Test Service",
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
            "pin_code": "SW1A1AA",
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
        print("🧪 Starting Laundry Platform API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Test pin code checker (no auth required)
        self.test_pincode_check()
        
        # Test user registration and login
        self.test_user_registration_login()
        
        # Test admin login
        self.test_admin_login()
        
        # Test services (no auth required)
        services = self.test_services_api()
        
        # Test order creation (requires auth)
        if self.token:
            order_id = self.test_order_creation(services)
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
    tester = LaundryAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
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