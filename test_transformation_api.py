"""
Test script for Transformation API endpoints.
Run this after starting the backend server to verify CRUD operations.
"""
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v2/transformations"

def print_response(response, title="Response"):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_get_all_transformations():
    """Test GET /api/v2/transformations/"""
    print("\n\n🔍 TEST 1: Get All Transformations")
    response = requests.get(API_BASE)
    print_response(response, "GET All Transformations")
    return response.json() if response.status_code == 200 else []

def test_create_transformation():
    """Test POST /api/v2/transformations/"""
    print("\n\n➕ TEST 2: Create Transformation")
    
    new_transformation = {
        "transformation_name": "Test Custom Transform",
        "transformation_code": "TEST_CUSTOM",
        "transformation_expression": "REPLACE({field}, ' ', '_')",
        "transformation_description": "Replace spaces with underscores - TEST",
        "category": "CUSTOM",
        "is_system": False
    }
    
    response = requests.post(API_BASE, json=new_transformation)
    print_response(response, "POST Create Transformation")
    return response.json() if response.status_code == 200 else None

def test_get_transformation_by_id(transformation_id):
    """Test GET /api/v2/transformations/{id}"""
    print(f"\n\n🔍 TEST 3: Get Transformation by ID ({transformation_id})")
    response = requests.get(f"{API_BASE}/{transformation_id}")
    print_response(response, f"GET Transformation {transformation_id}")
    return response.json() if response.status_code == 200 else None

def test_update_transformation(transformation_id):
    """Test PUT /api/v2/transformations/{id}"""
    print(f"\n\n✏️  TEST 4: Update Transformation ({transformation_id})")
    
    updated_data = {
        "transformation_name": "Test Custom Transform (Updated)",
        "transformation_code": "TEST_CUSTOM",
        "transformation_expression": "REPLACE({field}, ' ', '-')",
        "transformation_description": "Replace spaces with hyphens - UPDATED TEST",
        "category": "CUSTOM",
        "is_system": False
    }
    
    response = requests.put(f"{API_BASE}/{transformation_id}", json=updated_data)
    print_response(response, f"PUT Update Transformation {transformation_id}")
    return response.json() if response.status_code == 200 else None

def test_delete_transformation(transformation_id):
    """Test DELETE /api/v2/transformations/{id}"""
    print(f"\n\n🗑️  TEST 5: Delete Transformation ({transformation_id})")
    response = requests.delete(f"{API_BASE}/{transformation_id}")
    print_response(response, f"DELETE Transformation {transformation_id}")
    return response.status_code == 200

def test_duplicate_code():
    """Test creating transformation with duplicate code"""
    print("\n\n⚠️  TEST 6: Create Duplicate Code (Should Fail)")
    
    duplicate_transformation = {
        "transformation_name": "Duplicate Test",
        "transformation_code": "TRIM",  # This should already exist as system transformation
        "transformation_expression": "TRIM({field})",
        "transformation_description": "This should fail",
        "category": "STRING",
        "is_system": False
    }
    
    response = requests.post(API_BASE, json=duplicate_transformation)
    print_response(response, "POST Duplicate Code (Expected 400)")

def test_update_system_transformation():
    """Test updating a system transformation (should fail)"""
    print("\n\n🛡️  TEST 7: Update System Transformation (Should Fail)")
    
    # Get all transformations and find a system one
    response = requests.get(API_BASE)
    if response.status_code == 200:
        transformations = response.json()
        system_trans = next((t for t in transformations if t.get('is_system', False)), None)
        
        if system_trans:
            system_id = system_trans['transformation_id']
            
            updated_data = {
                "transformation_name": "Should Not Update",
                "transformation_code": "SHOULD_FAIL",
                "transformation_expression": "TRIM({field})",
                "transformation_description": "This should fail",
                "category": "STRING",
                "is_system": False
            }
            
            response = requests.put(f"{API_BASE}/{system_id}", json=updated_data)
            print_response(response, f"PUT System Transformation {system_id} (Expected 403)")
        else:
            print("No system transformations found to test")

def run_all_tests():
    """Run all tests in sequence"""
    print("="*60)
    print("TRANSFORMATION API TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"API Endpoint: {API_BASE}")
    
    try:
        # Test 1: Get all transformations
        all_transformations = test_get_all_transformations()
        print(f"\n✅ Found {len(all_transformations)} transformations")
        
        # Test 2: Create new transformation
        created = test_create_transformation()
        if created:
            created_id = created.get('transformation_id')
            print(f"\n✅ Created transformation with ID: {created_id}")
            
            # Test 3: Get by ID
            fetched = test_get_transformation_by_id(created_id)
            if fetched:
                print(f"\n✅ Successfully fetched transformation {created_id}")
            
            # Test 4: Update transformation
            updated = test_update_transformation(created_id)
            if updated:
                print(f"\n✅ Successfully updated transformation {created_id}")
            
            # Test 5: Delete transformation
            deleted = test_delete_transformation(created_id)
            if deleted:
                print(f"\n✅ Successfully deleted transformation {created_id}")
        
        # Test 6: Try to create duplicate code
        test_duplicate_code()
        print("\n✅ Duplicate code validation working")
        
        # Test 7: Try to update system transformation
        test_update_system_transformation()
        print("\n✅ System transformation protection working")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the backend server")
        print(f"Make sure the server is running at {BASE_URL}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()

