"""
RAG Flow E2E Smoke Test
Run this after starting the backend server: uv run uvicorn app.main:app --reload --port 8000
No hardcoded user credentials, keys, or paths.
"""

import json
import time
import tempfile
from pathlib import Path
import requests
import os
import sys

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30

def print_step(step_num, description):
    print(f"\n{'='*80}")
    print(f"Step {step_num}: {description}")
    print('='*80)

def print_result(check, expected, actual, passed):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {check}")
    print(f"  Expected: {expected}")
    print(f"  Actual: {actual}")
    return passed

def main():
    results = []
    
    # Generate unique email for test user
    test_email = f"test.rag.{int(time.time())}@example.com"
    test_password = "TestPass123!"
    
    # Step 1: Test Auth - Register
    print_step(1, "Test Auth - Register User")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": test_email,
                "password": test_password
            },
            timeout=TIMEOUT
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Handle nested token structure: {"tokens": {"access_token": "..."}}
            tokens = data.get("tokens", {})
            access_token = tokens.get("access_token") or data.get("access_token")
            
            passed = bool(access_token)
            results.append(print_result(
                "Auth /register",
                "200/201 + token",
                f"{response.status_code} + token={bool(access_token)}",
                passed
            ))
            
            if not passed:
                print(f"\n❌ STOP: No access token returned")
                print(f"Response: {json.dumps(data, indent=2)}")
                return False
                
            print(f"\n✅ Access token obtained: {access_token[:20]}...")
            
        else:
            results.append(print_result(
                "Auth /register",
                "200/201 + token",
                f"{response.status_code}",
                False
            ))
            print(f"\n❌ STOP: Registration failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ STOP: Cannot connect to backend at {BASE_URL}")
        print("Please start the backend first:")
        print("  cd backend")
        print("  uv run uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"\n❌ STOP: Registration error: {e}")
        return False
    
    # Step 2: Upload Test Document
    print_step(2, "Upload Test Document")
    
    # Create test document with OS scheduling content
    test_content = """Operating System Process Scheduling

Process scheduling is the OS mechanism for selecting which process runs next on the CPU.
The scheduler uses various algorithms to make this decision efficiently.

Common Scheduling Algorithms:

1. First-Come First-Served (FCFS)
   - Simplest algorithm: processes are executed in arrival order
   - Non-preemptive
   - Can lead to convoy effect with long processes

2. Shortest Job First (SJF)
   - Selects process with shortest burst time
   - Minimizes average waiting time
   - Requires knowledge of burst times (difficult in practice)

3. Round Robin (RR)
   - Preemptive algorithm
   - Assigns equal time slices (quantum) to each process
   - Fair allocation, good for time-sharing systems
   - Performance depends on quantum size

4. Priority Scheduling
   - Each process has a priority value
   - Higher priority processes execute first
   - Can lead to starvation of low-priority processes
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        test_file_path = f.name
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('os_scheduling.txt', f, 'text/plain')}
            data = {'title': 'OS Scheduling Notes'}
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = requests.post(
                f"{BASE_URL}/api/v1/documents/",
                files=files,
                data=data,
                headers=headers,
                timeout=TIMEOUT
            )
        
        if response.status_code == 200:
            doc_data = response.json()
            status = doc_data.get('status', 'unknown')
            doc_id = doc_data.get('id')
            
            print(f"Document uploaded: ID={doc_id}, status={status}")
            
            # Wait for processing if needed
            if status in ["processing", "pending"]:
                print("Waiting 10 seconds for document processing...")
                time.sleep(10)
                
                # Check status
                response = requests.get(
                    f"{BASE_URL}/api/v1/documents/",
                    headers=headers,
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    docs = response.json()
                    if docs and len(docs) > 0:
                        status = docs[0].get('status', 'unknown')
                        print(f"Document status after waiting: {status}")
            
            passed = status in ["ready", "completed"]
            results.append(print_result(
                "Document upload",
                "status=ready/completed",
                f"status={status}",
                passed
            ))
            
            if not passed:
                print(f"\n❌ STOP: Document not ready for retrieval")
                print(f"Full response: {json.dumps(doc_data, indent=2)}")
                return False
                
        else:
            results.append(print_result(
                "Document upload",
                "200 + status=ready",
                f"{response.status_code}",
                False
            ))
            print(f"\n❌ STOP: Document upload failed")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ STOP: Document upload error: {e}")
        return False
    finally:
        # Cleanup temp file
        Path(test_file_path).unlink(missing_ok=True)
    
    # Step 3: Test RAG Streaming (relevant query)
    print_step(3, "Test RAG Streaming (Relevant Query)")
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/rag-stream",
            headers=headers,
            json={
                "messages": [
                    {"role": "user", "content": "What is Round Robin scheduling?"}
                ],
                "use_rag": True
            },
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            results.append(print_result(
                "RAG stream: relevant query tokens",
                "data: {\"type\":\"text\"...}",
                f"HTTP {response.status_code}",
                False
            ))
            results.append(print_result(
                "RAG stream: relevant query sources",
                "sources[0].document_title",
                "N/A - request failed",
                False
            ))
            print(f"\n❌ STOP: RAG stream request failed")
            print(f"Response: {response.text}")
            return False
        
        # Parse SSE stream
        text_events = []
        done_event = None
        error_event = None
        
        print("\nSSE Stream Output (relevant query):")
        print("-" * 80)
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                if line.startswith('data: '):
                    try:
                        data_str = line[6:]  # Remove 'data: ' prefix
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'text':
                            text_events.append(data)
                            print(data.get('content', ''), end='', flush=True)
                        elif data.get('type') == 'done':
                            done_event = data
                            print(f"\n[DONE] {len(data.get('data', {}).get('sources', []))} sources")
                        elif data.get('type') == 'error':
                            error_event = data
                            print(f"\n[ERROR] {data.get('error')}")
                    except json.JSONDecodeError:
                        pass
        
        print("-" * 80)
        
        # Verify text tokens streamed
        tokens_passed = len(text_events) > 0
        results.append(print_result(
            "RAG stream: relevant query tokens",
            "data: {\"type\":\"text\"...}",
            f"{len(text_events)} text events received",
            tokens_passed
        ))
        
        if not tokens_passed:
            print(f"\n❌ FAIL: No text tokens streamed")
            if error_event:
                print(f"Error event: {json.dumps(error_event, indent=2)}")
        
        # Verify sources in done event
        sources_passed = False
        if done_event:
            sources = done_event.get('data', {}).get('sources', [])
            if sources and len(sources) > 0:
                first_source_title = sources[0].get('document_title', 'N/A')
                sources_passed = True  # At least one source found
                
                results.append(print_result(
                    "RAG stream: relevant query sources",
                    "sources non-empty",
                    f"Found {len(sources)} sources: {first_source_title}",
                    sources_passed
                ))
            else:
                results.append(print_result(
                    "RAG stream: relevant query sources",
                    "sources non-empty",
                    "sources array is empty",
                    False
                ))
                print(f"\n❌ FAIL: RAG retrieval found no documents")
                print("This means similarity search returned no chunks.")
        else:
            results.append(print_result(
                "RAG stream: relevant query sources",
                "sources non-empty",
                "No done event received",
                False
            ))
            print(f"\n❌ FAIL: No done event received in stream")
        
    except Exception as e:
        print(f"\n❌ STOP: RAG streaming error (relevant query): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test RAG Streaming (unrelated query)
    print_step(4, "Test RAG Streaming (Unrelated Query)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/rag-stream",
            headers=headers,
            json={
                "messages": [
                    {"role": "user", "content": "What is a good pancake recipe?"}
                ],
                "use_rag": True
            },
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            results.append(print_result(
                "RAG stream: unrelated query tokens",
                "data: {\"type\":\"text\"...}",
                f"HTTP {response.status_code}",
                False
            ))
            results.append(print_result(
                "RAG stream: unrelated query sources",
                "sources empty or minimal",
                "N/A - request failed",
                False
            ))
            print(f"\n❌ STOP: RAG stream request failed (unrelated query)")
            print(f"Response: {response.text}")
            return False
        
        # Parse SSE stream
        text_events = []
        done_event = None
        error_event = None
        
        print("\nSSE Stream Output (unrelated query):")
        print("-" * 80)
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                if line.startswith('data: '):
                    try:
                        data_str = line[6:]
                        data = json.loads(data_str)
                        
                        if data.get('type') == 'text':
                            text_events.append(data)
                            print(data.get('content', ''), end='', flush=True)
                        elif data.get('type') == 'done':
                            done_event = data
                            print(f"\n[DONE] {len(data.get('data', {}).get('sources', []))} sources")
                        elif data.get('type') == 'error':
                            error_event = data
                            print(f"\n[ERROR] {data.get('error')}")
                    except json.JSONDecodeError:
                        pass
        
        print("-" * 80)
        
        # Verify text tokens streamed (should still stream answer)
        tokens_passed = len(text_events) > 0 and error_event is None
        results.append(print_result(
            "RAG stream: unrelated query tokens",
            "data: {\"type\":\"text\"...}, no error event",
            f"{len(text_events)} text events, error={error_event is not None}",
            tokens_passed
        ))
        
        # Verify sources are empty for unrelated query
        sources_passed = False
        if done_event:
            sources = done_event.get('data', {}).get('sources', [])
            sources_passed = len(sources) == 0  # Should be empty
            
            results.append(print_result(
                "RAG stream: unrelated query sources",
                "sources empty",
                f"{len(sources)} sources found",
                sources_passed
            ))
        else:
            results.append(print_result(
                "RAG stream: unrelated query sources",
                "sources empty",
                "No done event received",
                False
            ))
        
    except Exception as e:
        print(f"\n❌ STOP: RAG streaming error (unrelated query): {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Final Report
    print_step(5, "Smoke Test Report")
    
    print("\n| Check | Result |")
    print("|-------|--------|")
    for i, result in enumerate(results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"| Check {i+1} | {status} |")
    
    all_passed = all(results)
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL CHECKS PASSED - RAG pipeline is working correctly!")
    else:
        print("❌ SOME CHECKS FAILED - Fix issues before proceeding")
    print("="*80)
    
    return all_passed

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   Voice AI Study Coach - RAG Smoke Test                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Prerequisites:
1. Backend server must be running
   Command: cd backend && uv run uvicorn app.main:app --reload --port 8000

2. PostgreSQL database must be running with migrations applied
   Command: cd backend && uv run python -m alembic upgrade head

3. Set BACKEND_URL environment variable if not using default (http://localhost:8000)

Starting smoke test...
""")
    
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
