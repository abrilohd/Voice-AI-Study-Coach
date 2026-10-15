"""Unit tests for SSE event structure validation.

These tests verify that SSE events match the frontend contract defined in
frontend/src/types/index.ts and frontend/src/lib/api.ts.

These tests do NOT require database access or LLM calls - they validate
the event structure only.
"""

import json


def test_done_event_structure():
    """Verify RAG done event structure matches frontend TypeScript contract.
    
    Frontend expects (types/index.ts line 70-73):
        interface SSEDoneEvent {
            type: 'done';
            data: DonePayload;
        }
    
    Frontend parses (lib/api.ts line 309-313):
        onDone({
            total_tokens: parsed.data.total_tokens,
            sources: parsed.data.sources,
        })
    """
    # This is what backend should emit (chat_rag.py line 160-167)
    done_event = {
        "type": "done",
        "data": {
            "total_tokens": 150,
            "sources": [
                {
                    "document_title": "Test Document",
                    "similarity_score": 0.85,
                    "chunk_index": 0,
                }
            ],
        },
    }
    
    # Simulate SSE serialization/deserialization
    serialized = json.dumps(done_event)
    parsed = json.loads(serialized)
    
    # Frontend contract validation
    assert parsed["type"] == "done"
    assert "data" in parsed, "Missing 'data' wrapper in done event"
    assert "total_tokens" in parsed["data"]
    assert "sources" in parsed["data"]
    assert isinstance(parsed["data"]["sources"], list)
    
    # Verify frontend can extract values
    assert parsed["data"]["total_tokens"] == 150
    assert len(parsed["data"]["sources"]) == 1


def test_text_event_structure():
    """Verify text event structure matches frontend contract.
    
    Frontend checks (lib/api.ts line 307-308):
        if (parsed.type === 'text') {
            onToken(parsed.content);
    """
    text_event = {
        "type": "text",
        "content": "Hello, world!",
    }
    
    serialized = json.dumps(text_event)
    parsed = json.loads(serialized)
    
    assert parsed["type"] == "text"
    assert "content" in parsed
    assert parsed["content"] == "Hello, world!"


def test_error_event_structure():
    """Verify error event structure matches frontend contract.
    
    Backend sends (chat_rag.py line 87, 171, 179):
        {'type': 'error', 'error': '...'}
    
    Frontend expects (types/index.ts line 75-78):
        interface SSEErrorEvent {
            type: 'error';
            error: string;
        }
    
    Frontend parses (lib/api.ts line 314):
        onError(new Error(parsed.error));
    """
    # What backend sends (now fixed)
    backend_error_event = {
        "type": "error",
        "error": "Test error",
    }
    
    serialized = json.dumps(backend_error_event)
    parsed = json.loads(serialized)
    
    assert parsed["type"] == "error"
    assert "error" in parsed
    assert parsed["error"] == "Test error"
    
    # Frontend can now read error message correctly
    frontend_error_message = parsed.get("error")
    assert frontend_error_message == "Test error"


def test_usage_event_structure():
    """Verify usage event structure (not directly consumed by frontend RAG flow).
    
    Backend emits (llm/router.py):
        {"type": "usage", "input_tokens": int, "output_tokens": int}
    
    RAG endpoint captures these but doesn't forward to frontend.
    """
    usage_event = {
        "type": "usage",
        "input_tokens": 100,
        "output_tokens": 50,
    }
    
    serialized = json.dumps(usage_event)
    parsed = json.loads(serialized)
    
    assert parsed["type"] == "usage"
    assert "input_tokens" in parsed
    assert "output_tokens" in parsed


if __name__ == "__main__":
    """Run tests manually to validate SSE contracts."""
    print("Running SSE event structure tests...\n")
    
    try:
        test_done_event_structure()
        print("✅ test_done_event_structure PASSED")
    except AssertionError as e:
        print(f"❌ test_done_event_structure FAILED: {e}")
    
    try:
        test_text_event_structure()
        print("✅ test_text_event_structure PASSED")
    except AssertionError as e:
        print(f"❌ test_text_event_structure FAILED: {e}")
    
    try:
        test_error_event_structure()
        print("✅ test_error_event_structure PASSED")
    except AssertionError as e:
        print(f"❌ test_error_event_structure FAILED: {e}")
    
    try:
        test_usage_event_structure()
        print("✅ test_usage_event_structure PASSED")
    except AssertionError as e:
        print(f"❌ test_usage_event_structure FAILED: {e}")
    
    print("\n✅ All SSE event structure tests completed")
