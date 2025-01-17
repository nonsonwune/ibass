import threading
import requests
import time
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:5001"

def make_request():
    """Make concurrent requests to test endpoints"""
    try:
        # Request featured institutions
        r1 = requests.get(f"{BASE_URL}/api/featured-institutions")
        logger.debug(f"Featured institutions response: {r1.status_code}")
        
        # Request locations
        r2 = requests.get(f"{BASE_URL}/api/locations")
        logger.debug(f"Locations response: {r2.status_code}")
        
        return r1.status_code == 200 and r2.status_code == 200
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return False

def test_concurrent_requests():
    """Test concurrent requests to check for race conditions"""
    num_threads = 10
    logger.info(f"Starting concurrent test with {num_threads} threads")
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        results = list(executor.map(lambda _: make_request(), range(num_threads)))
    
    success_rate = sum(results) / len(results) * 100
    logger.info(f"Test completed. Success rate: {success_rate}%")
    return success_rate

if __name__ == "__main__":
    test_concurrent_requests() 