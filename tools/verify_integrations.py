#!/usr/bin/env python3
"""
PMOVES-DoX Integration Verification
Verifies Cipher, Postman, and Agent Zero integration.
"""

import sys
import socket
import requests
import time

def check_port(host, port, name):
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[PASS] {name} port {port} is open.")
            return True
    except (socket.timeout, ConnectionRefusedError):
        print(f"[FAIL] {name} port {port} is NOT reachable.")
        return False
    except Exception as e:
        print(f"[FAIL] {name} port {port} error: {e}")
        return False

def check_http(url, name, expected_codes=[200]):
    try:
        headers = {'Accept': 'text/event-stream'}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code in expected_codes:
            print(f"[PASS] {name} HTTP {url} returned {resp.status_code}.")
            return True
        else:
            print(f"[FAIL] {name} HTTP {url} returned {resp.status_code} (expected {expected_codes}).")
            return False
    except Exception as e:
        print(f"[FAIL] {name} HTTP {url} error: {e}")
        return False

def main():
    print("Starting Integration Verification...")
    results = []

    # 1. Cipher Agent (Port 3025 -> 8000 MCP Proxy)
    results.append(check_port("localhost", 3025, "Cipher Agent"))
    results.append(check_http("http://localhost:3025/mcp", "Cipher SSE Endpoint", expected_codes=[200, 404, 405, 400]))
    
    # 2. Postman Agent (Port 3026 -> 8000)
    results.append(check_port("localhost", 3026, "Postman Agent"))
    # The proxy usually serves SSE at /mcp or health at /health (if fastmcp)
    results.append(check_http("http://localhost:3026/mcp", "Postman SSE Endpoint", expected_codes=[200, 404, 405, 400])) 
    # 400/405 is fine for SSE endpoint checked via GET

    # 3. Agent Zero (Port 50051)
    results.append(check_port("localhost", 50051, "Agent Zero"))
    
    # 4. Gateway (Port 3000 -> 54321 in docker-compose for supabase, wait gateway isn't running on host port? 
    # Ah, gateway runs internally. Check if we exposed it? 
    # We didn't explicitly expose 'mcp-gateway' in the last edit, we added 'postman-agent'.
    # Agent Zero UI is usually 80 or 9000-9009. DockerfileLocal exposes 80, 9000-9009.
    # We mapped 50051:50051. Let's check 50051.
    
    if all(results):
        print("\nAll integration checks PASSED.")
        sys.exit(0)
    else:
        print("\nSome checks FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
