#!/usr/bin/env python3
"""
Simple performance test script for course search endpoints.
Tests basic functionality and timing without external dependencies.
"""

import urllib.request
import urllib.parse
import json
import time
import statistics
from typing import List, Dict

def test_endpoint(base_url: str, endpoint: str, params: Dict, iterations: int = 5) -> Dict:
    """Test an endpoint multiple times and return performance stats"""
    response_times = []
    result_counts = []
    successful_requests = 0
    
    full_url = f"{base_url}{endpoint}"
    
    for i in range(iterations):
        query_string = urllib.parse.urlencode(params)
        url_with_params = f"{full_url}?{query_string}"
        
        try:
            start_time = time.time()
            with urllib.request.urlopen(url_with_params) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    response_times.append(response_time)
                    result_counts.append(len(data))
                    successful_requests += 1
                    
        except Exception as e:
            print(f"  Error in iteration {i+1}: {e}")
            continue
        
        # Small delay between requests
        if i < iterations - 1:
            time.sleep(0.1)
    
    if response_times:
        return {
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'successful_requests': successful_requests,
            'failed_requests': iterations - successful_requests,
            'avg_result_count': statistics.mean(result_counts) if result_counts else 0
        }
    else:
        return {
            'avg_response_time': 0,
            'min_response_time': 0,
            'max_response_time': 0,
            'successful_requests': 0,
            'failed_requests': iterations,
            'avg_result_count': 0
        }

def main():
    base_url = "http://localhost:8100"
    university = "ualberta"
    iterations = 5
    
    test_queries = [
        "CMPUT",
        "MATH", 
        "intro",
        "201"
    ]
    
    endpoints = {
        "Standard": f"/api/{university}/courses/search",
        "Optimized": f"/api/{university}/courses/search/optimized"
    }
    
    print(f"Testing Course Search Performance")
    print(f"Base URL: {base_url}")
    print(f"University: {university}")
    print(f"Iterations per test: {iterations}")
    print("-" * 60)
    
    all_results = {}
    
    for endpoint_name, endpoint_path in endpoints.items():
        print(f"\n{endpoint_name} Endpoint: {endpoint_path}")
        endpoint_results = {}
        
        for query in test_queries:
            print(f"  Testing query: '{query}'", end=" ... ")
            params = {"q": query, "limit": 50}
            
            stats = test_endpoint(base_url, endpoint_path, params, iterations)
            endpoint_results[query] = stats
            
            if stats['successful_requests'] > 0:
                print(f"Avg: {stats['avg_response_time']:.1f}ms, Results: {stats['avg_result_count']:.0f}")
            else:
                print("FAILED")
        
        all_results[endpoint_name] = endpoint_results
    
    # Print comparison
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        for endpoint_name in endpoints.keys():
            if query in all_results[endpoint_name]:
                stats = all_results[endpoint_name][query]
                print(f"  {endpoint_name:10}: {stats['avg_response_time']:6.1f}ms avg, {stats['avg_result_count']:3.0f} results")
    
    # Overall averages
    print(f"\nOverall Averages:")
    for endpoint_name in endpoints.keys():
        all_times = []
        for query_stats in all_results[endpoint_name].values():
            if query_stats['successful_requests'] > 0:
                all_times.append(query_stats['avg_response_time'])
        
        if all_times:
            overall_avg = statistics.mean(all_times)
            print(f"  {endpoint_name:10}: {overall_avg:6.1f}ms")

if __name__ == "__main__":
    main()
