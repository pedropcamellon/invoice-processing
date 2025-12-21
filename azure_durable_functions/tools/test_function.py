#!/usr/bin/env python3
"""
Simple test script to verify the Azure Function is running and responding.

Usage:
    uv run test_function.py [--base-url URL]
"""

import requests
import argparse
import sys


def test_startup(base_url: str) -> bool:
    """Test the startup endpoint."""
    print(f"\n1. Testing startup endpoint...")
    try:
        url = f"{base_url}/api/startup"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {data.get('status')}")
            print(f"   ✓ Message: {data.get('message')}")
            print(f"   ✓ Containers: {data.get('containers')}")
            return True
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ✗ Connection error - is the function app running at {base_url}?")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_process_endpoint_validation(base_url: str) -> bool:
    """Test the process endpoint validation."""
    print(f"\n2. Testing process endpoint validation...")

    # Test missing invoice_id
    try:
        url = f"{base_url}/api/invoice/process"
        response = requests.post(url, json={}, timeout=30)

        if response.status_code == 400:
            data = response.json()
            if "invoice_id" in data.get("error", "").lower():
                print(f"   ✓ Correctly rejects missing invoice_id")
            else:
                print(f"   ? Unexpected error: {data}")
        else:
            print(f"   ✗ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test missing PDF source
    try:
        response = requests.post(url, json={"invoice_id": "TEST-001"}, timeout=30)

        if response.status_code == 400:
            data = response.json()
            if "pdf" in data.get("error", "").lower():
                print(f"   ✓ Correctly rejects missing PDF source")
            else:
                print(f"   ? Unexpected error: {data}")
        else:
            print(f"   ✗ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    return True


def test_submit_workflow(base_url: str, pdf_path: str = None) -> str:
    """Test submitting a workflow (returns instance_id or empty string)."""
    print(f"\n3. Testing workflow submission...")

    if not pdf_path:
        print(f"   ⚠ No PDF path provided, skipping actual workflow submission")
        return ""

    try:
        url = f"{base_url}/api/invoice/process"
        body = {
            "invoice_id": "TEST-VERIFICATION-001",
            "pdf_path": pdf_path,
            "metadata": {"test": True},
        }

        response = requests.post(url, json=body, timeout=30)

        if response.status_code == 202:
            data = response.json()
            instance_id = data.get("id", "")
            print(f"   ✓ Workflow submitted successfully")
            print(f"   ✓ Instance ID: {instance_id}")
            print(f"   ✓ Status URL: {data.get('statusQueryGetUri', '')[:80]}...")
            return instance_id
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return ""


def test_check_status(base_url: str, instance_id: str) -> bool:
    """Test checking workflow status."""
    if not instance_id:
        return True

    print(f"\n4. Testing status check...")
    try:
        url = f"{base_url}/runtime/webhooks/durabletask/instances/{instance_id}"
        response = requests.get(url, timeout=30)

        # 200 = completed, 202 = still running (both are valid)
        if response.status_code in (200, 202):
            data = response.json()
            status = data.get("runtimeStatus")
            print(f"   ✓ Status: {status}")
            if status == "Completed":
                print(f"   ✓ Workflow completed successfully")
            elif status == "Running":
                print(f"   ⏳ Workflow still running (this is normal for longer PDFs)")
            return True
        else:
            print(f"   ✗ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test the Azure Function endpoints")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8071",
        help="Base URL of the function app",
    )
    parser.add_argument(
        "--pdf-path",
        default=None,
        help="Path to a test PDF file for workflow submission",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Invoice Processing Workflow - Function Test")
    print("=" * 60)
    print(f"Base URL: {args.base_url}")

    all_passed = True

    # Test 1: Startup
    if not test_startup(args.base_url):
        all_passed = False

    # Test 2: Validation
    if not test_process_endpoint_validation(args.base_url):
        all_passed = False

    # Test 3: Submit (if PDF provided)
    instance_id = test_submit_workflow(args.base_url, args.pdf_path)

    # Test 4: Status check
    if instance_id:
        if not test_check_status(args.base_url, instance_id):
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
