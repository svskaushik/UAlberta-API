#!/usr/bin/env python3
"""
Performance testing script for course search endpoints.
Tests the optimization improvements and measures response times.
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Tuple
import argparse

class CourseSearchBenchmark:
    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, params: Dict, iterations: int = 10) -> Dict:
        """Test a single endpoint multiple times and collect performance metrics"""
        response_times = []
        status_codes = []
        result_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                async with self.session.get(f"{self.base_url}{endpoint}", params=params) as response:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                    
                    response_times.append(response_time)
                    status_codes.append(response.status)
                    
                    if response.status == 200:
                        data = await response.json()
                        result_counts.append(len(data))
                    else:
                        result_counts.append(0)
                        
            except Exception as e:
                print(f"Error in iteration {i+1}: {e}")
                response_times.append(float('inf'))
                status_codes.append(0)
                result_counts.append(0)
            
            # Small delay between requests
            if i < iterations - 1:
                await asyncio.sleep(0.1)
        
        # Calculate statistics
        valid_times = [t for t in response_times if t != float('inf')]
        
        if valid_times:
            stats = {
                'avg_response_time': statistics.mean(valid_times),
                'min_response_time': min(valid_times),
                'max_response_time': max(valid_times),
                'median_response_time': statistics.median(valid_times),
                'p95_response_time': self._percentile(valid_times, 95),
                'p99_response_time': self._percentile(valid_times, 99),
                'successful_requests': len(valid_times),
                'failed_requests': iterations - len(valid_times),
                'avg_result_count': statistics.mean(result_counts) if result_counts else 0,
                'total_iterations': iterations
            }
        else:
            stats = {
                'avg_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'median_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0,
                'successful_requests': 0,
                'failed_requests': iterations,
                'avg_result_count': 0,
                'total_iterations': iterations
            }
        
        return stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a sorted list"""
        sorted_data = sorted(data)
        index = (percentile / 100) * len(sorted_data)
        if index.is_integer():
            return sorted_data[int(index) - 1]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    async def run_benchmark(self, university: str = "ualberta", iterations: int = 10) -> Dict:
        """Run comprehensive benchmark comparing different endpoints"""
        
        test_queries = [
            "CMPUT",      # Common subject prefix
            "MATH",       # Another common prefix
            "intro",      # Common word in course names
            "calculus",   # Specific term
            "201",        # Course level
            "programming" # Longer descriptive term
        ]
        
        endpoints = {
            "standard": f"/api/{university}/courses/search",
            "optimized": f"/api/{university}/courses/search/optimized"
        }
        
        results = {}
        
        print(f"Running benchmark with {iterations} iterations per test...")
        print(f"University: {university}")
        print(f"Test queries: {test_queries}")
        print("-" * 60)
        
        for endpoint_name, endpoint_path in endpoints.items():
            print(f"\nTesting {endpoint_name} endpoint: {endpoint_path}")
            endpoint_results = {}
            
            for query in test_queries:
                print(f"  Testing query: '{query}'")
                params = {"q": query, "limit": 50}
                
                stats = await self.test_endpoint(endpoint_path, params, iterations)
                endpoint_results[query] = stats
                
                print(f"    Avg: {stats['avg_response_time']:.2f}ms, "
                      f"P95: {stats['p95_response_time']:.2f}ms, "
                      f"Results: {stats['avg_result_count']:.1f}")
            
            # Calculate overall statistics for this endpoint
            all_times = []
            all_results = []
            total_successful = 0
            total_failed = 0
            
            for query_stats in endpoint_results.values():
                if query_stats['successful_requests'] > 0:
                    # We need to approximate the distribution from summary stats
                    # This is a simplification, but gives us a general idea
                    all_times.extend([query_stats['avg_response_time']] * query_stats['successful_requests'])
                    all_results.extend([query_stats['avg_result_count']] * query_stats['successful_requests'])
                
                total_successful += query_stats['successful_requests']
                total_failed += query_stats['failed_requests']
            
            endpoint_summary = {
                'query_results': endpoint_results,
                'overall_stats': {
                    'avg_response_time': statistics.mean(all_times) if all_times else 0,
                    'median_response_time': statistics.median(all_times) if all_times else 0,
                    'p95_response_time': self._percentile(all_times, 95) if all_times else 0,
                    'total_successful_requests': total_successful,
                    'total_failed_requests': total_failed,
                    'success_rate': (total_successful / (total_successful + total_failed) * 100) if (total_successful + total_failed) > 0 else 0
                }
            }
            
            results[endpoint_name] = endpoint_summary
            
            print(f"  Overall - Avg: {endpoint_summary['overall_stats']['avg_response_time']:.2f}ms, "
                  f"Success Rate: {endpoint_summary['overall_stats']['success_rate']:.1f}%")
        
        return results
    
    def print_comparison(self, results: Dict):
        """Print a comparison between the different endpoints"""
        print("\n" + "=" * 80)
        print("PERFORMANCE COMPARISON")
        print("=" * 80)
        
        if 'standard' in results and 'optimized' in results:
            std_avg = results['standard']['overall_stats']['avg_response_time']
            opt_avg = results['optimized']['overall_stats']['avg_response_time']
            
            if std_avg > 0 and opt_avg > 0:
                improvement = ((std_avg - opt_avg) / std_avg) * 100
                print(f"Average Response Time Improvement: {improvement:.1f}%")
                print(f"Standard Endpoint: {std_avg:.2f}ms")
                print(f"Optimized Endpoint: {opt_avg:.2f}ms")
            
            std_p95 = results['standard']['overall_stats']['p95_response_time']
            opt_p95 = results['optimized']['overall_stats']['p95_response_time']
            
            if std_p95 > 0 and opt_p95 > 0:
                p95_improvement = ((std_p95 - opt_p95) / std_p95) * 100
                print(f"P95 Response Time Improvement: {p95_improvement:.1f}%")
        
        print("\nDetailed Results by Query:")
        for endpoint_name, endpoint_data in results.items():
            print(f"\n{endpoint_name.upper()} ENDPOINT:")
            print("-" * 40)
            for query, stats in endpoint_data['query_results'].items():
                print(f"'{query}': {stats['avg_response_time']:.2f}ms avg, "
                      f"{stats['p95_response_time']:.2f}ms p95, "
                      f"{stats['avg_result_count']:.0f} results")

async def main():
    parser = argparse.ArgumentParser(description='Benchmark course search endpoints')
    parser.add_argument('--university', '-u', default='ualberta', help='University code to test')
    parser.add_argument('--iterations', '-i', type=int, default=10, help='Number of iterations per test')
    parser.add_argument('--base-url', '-b', default='http://localhost:8100', help='Base URL for the API')
    parser.add_argument('--output', '-o', help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    async with CourseSearchBenchmark(args.base_url) as benchmark:
        results = await benchmark.run_benchmark(args.university, args.iterations)
        benchmark.print_comparison(results)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    asyncio.run(main())
