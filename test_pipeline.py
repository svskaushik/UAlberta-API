#!/usr/bin/env python3
"""
End-to-end test script for the University API pipeline.
Tests database connection, scraping, and API endpoints.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_connection():
    """Test database connectivity"""
    print("🔍 Testing database connection...")
    try:
        from database.models import db_manager
        from sqlalchemy import text
        
        with db_manager.get_session() as db:
            result = db.execute(text("SELECT 1")).fetchone()
            if result and result[0] == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_schema_exists():
    """Test if all required tables exist"""
    print("🔍 Testing database schema...")
    try:
        from database.models import db_manager
        from sqlalchemy import text
        
        with db_manager.get_session() as db:
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)).fetchall()
            
            tables = [row[0] for row in result]
            expected_tables = [
                'universities', 'faculties', 'subjects', 'courses', 
                'terms', 'course_sections', 'exam_schedules', 
                'instructors', 'sync_logs'
            ]
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            else:
                print(f"✅ All {len(expected_tables)} required tables exist")
                return True
                
    except Exception as e:
        print(f"❌ Schema check error: {e}")
        return False

def test_scraper_basic():
    """Test basic scraper functionality without full scraping"""
    print("🔍 Testing scraper initialization...")
    try:
        from scrapers.ualberta import UAlbertaScraper
        
        scraper = UAlbertaScraper()
        if hasattr(scraper, 'session') and hasattr(scraper, 'university_code'):
            print("✅ Scraper initialization successful")
            return True
        else:
            print("❌ Scraper missing required attributes")
            return False
            
    except Exception as e:
        print(f"❌ Scraper initialization error: {e}")
        return False

def test_services():
    """Test database services"""
    print("🔍 Testing database services...")
    try:
        from database.models import db_manager
        from database.services import UniversityService, FacultyService, CourseService
        
        with db_manager.get_session() as db:
            # Test university service
            uni_service = UniversityService(db)
            university = uni_service.get_or_create_university(
                code='test_uni',
                name='Test University'
            )
            
            if university and university.id:
                print("✅ University service working")
                
                # Clean up test data
                db.delete(university)
                db.commit()
                return True
            else:
                print("❌ University service failed")
                return False
                
    except Exception as e:
        print(f"❌ Services test error: {e}")
        return False

def test_api_health():
    """Test if API server is running and healthy"""
    print("🔍 Testing API health...")
    try:
        api_url = f"http://localhost:{os.getenv('API_PORT', '8100')}/docs"
        
        request = urllib.request.Request(api_url)
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                print("✅ API server is running and accessible")
                return True
            else:
                print(f"❌ API server returned status {response.status}")
                return False
                
    except Exception as e:
        print(f"❌ API health check error: {e}")
        return False

def test_api_endpoints():
    """Test basic API endpoints"""
    print("🔍 Testing API endpoints...")
    try:
        base_url = f"http://localhost:{os.getenv('API_PORT', '8100')}"
        
        # Test faculties endpoint
        request = urllib.request.Request(f"{base_url}/api/ualberta/faculties")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ Faculties endpoint working (returned {len(data)} faculties)")
            else:
                print(f"❌ Faculties endpoint failed with status {response.status}")
                return False
                
        # Test subjects endpoint
        request = urllib.request.Request(f"{base_url}/api/ualberta/subjects")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ Subjects endpoint working (returned {len(data)} subjects)")
            else:
                print(f"❌ Subjects endpoint failed with status {response.status}")
                return False
                
        # Test courses endpoint with limit
        request = urllib.request.Request(f"{base_url}/api/ualberta/courses?limit=5")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✅ Courses endpoint working (returned {len(data)} courses)")
            else:
                print(f"❌ Courses endpoint failed with status {response.status}")
                return False
        
        # Test cache stats endpoint
        try:
            request = urllib.request.Request(f"{base_url}/api/admin/cache/stats")
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    print("✅ Cache stats endpoint working")
                else:
                    print("⚠️ Cache stats endpoint not accessible")
        except:
            print("⚠️ Cache stats endpoint not available (cache might be disabled)")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test error: {e}")
        return False

def test_course_search():
    """Test course search functionality"""
    print("🔍 Testing course search endpoints...")
    try:
        base_url = f"http://localhost:{os.getenv('API_PORT', '8100')}"
        
        # Test standard search endpoint
        search_url = f"{base_url}/api/ualberta/courses/search?q=nutrition&limit=5"
        request = urllib.request.Request(search_url)
        
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    print(f"✅ Course search working (found {len(data)} courses)")
                else:
                    print(f"❌ Course search failed with status {response.status}")
                    return False
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("⚠️ Course search returned 404 - no courses in database yet")
                return True
            else:
                print(f"❌ Course search failed: {e}")
                return False
        
        # Test optimized search endpoint
        try:
            optimized_url = f"{base_url}/api/ualberta/courses/search/optimized?q=science&limit=3"
            request = urllib.request.Request(optimized_url)
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    print(f"✅ Optimized search working (found {len(data)} courses)")
                else:
                    print("⚠️ Optimized course search not working")
        except Exception as e:
            print(f"⚠️ Optimized course search error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Course search test error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🚀 Starting comprehensive pipeline test...\n")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Schema", test_schema_exists),
        ("Scraper Initialization", test_scraper_basic),
        ("Database Services", test_services),
        ("API Health", test_api_health),
        ("API Endpoints", test_api_endpoints),
        ("Course Search", test_course_search),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Testing: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The pipeline is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        return False

def main():
    """Main test function"""
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
