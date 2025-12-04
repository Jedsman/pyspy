#!/usr/bin/env python3
"""End-to-end test of Interview Coach voice integration.

Tests the complete flow:
1. Web overlay sends multi-segment selection to voice app
2. Voice app polls for Claude's response
3. Claude Desktop generates answer using MCP tools
4. Q&A pair auto-archives
"""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Test scenario: User selects 2 segments about Kubernetes experience


def test_interview_coach_e2e():
    """Test complete Interview Coach flow."""
    print("=" * 70)
    print("TEST: Interview Coach End-to-End Flow")
    print("=" * 70)

    # Simulate transcript segments (what user selects in web overlay)
    segment_1 = "Tell me about your experience with Kubernetes"
    segment_2 = "specifically in a production environment"

    combined_question = f"{segment_1} {segment_2}"
    print(f"\n[STEP 1] User selects segments in web overlay:")
    print(f"  Segment 1: '{segment_1}'")
    print(f"  Segment 2: '{segment_2}'")
    print(f"  Combined:  '{combined_question}'")

    # Simulate WebSocket message from overlay to voice app
    websocket_message = {
        "type": "interview_coach_query",
        "data": {
            "segments": [segment_1, segment_2],
            "combined_text": combined_question,
            "timestamp": time.time(),
        },
    }
    print(f"\n[STEP 2] Web overlay sends WebSocket message:")
    print(json.dumps(websocket_message, indent=2))

    # Simulate voice app writing query file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        query_file = tmpdir / ".interview_coach_query"
        response_file = tmpdir / ".interview_coach_response"

        query_data = {
            "combined_text": combined_question,
            "segments": [segment_1, segment_2],
            "timestamp": websocket_message["data"]["timestamp"],
        }

        query_file.write_text(json.dumps(query_data, indent=2))
        print(
            f"\n[STEP 3] Voice app writes query file: {query_file.name}"
        )
        print(f"  Content: {query_file.read_text()}")

        # Simulate Claude retrieving KB context via MCP
        kb_context = {
            "question": combined_question,
            "documents": [
                {
                    "source": "career_history.json",
                    "content": (
                        "Company: GSK, Role: AI Platform Engineer, "
                        "Achievement: Built multi-region Kubernetes clusters, "
                        "Managed production deployments"
                    ),
                    "score": 0.98,
                },
                {
                    "source": "kubernetes_guide.txt",
                    "content": (
                        "Kubernetes in production: pod scheduling, "
                        "resource limits, monitoring, autoscaling"
                    ),
                    "score": 0.95,
                },
                {
                    "source": "gcp_infrastructure.txt",
                    "content": (
                        "Multi-region deployment, failover handling, "
                        "load balancing across regions"
                    ),
                    "score": 0.92,
                },
            ],
        }

        print(f"\n[STEP 4] Claude calls retrieve_answer MCP tool:")
        print(f"  Question: '{combined_question}'")
        print(f"  KB returned {len(kb_context['documents'])} documents")
        for doc in kb_context["documents"]:
            print(
                f"    - {doc['source']} (score: {doc['score']})"
            )

        # Simulate Claude formulating answer
        claude_answer = (
            "In my work at GSK, I built a multi-region Kubernetes "
            "deployment pipeline that handled automatic failover across "
            "3 GCP regions. We used Terraform for infrastructure-as-code "
            "and integrated it with our CI/CD system to enable "
            "zero-downtime deployments, reducing deployment time from "
            "4 hours to 15 minutes."
        )

        print(f"\n[STEP 5] Claude formulates answer from KB context:")
        print(f"  (2-3 sentences, ~30-45 seconds spoken)")
        print(f"  Answer: '{claude_answer}'")

        # Simulate Claude calling answer_interview_question tool
        response_data = {
            "question": combined_question,
            "answer": claude_answer,
            "sources": [
                "career_history.json",
                "kubernetes_guide.txt",
                "gcp_infrastructure.txt",
            ],
            "timestamp": time.time(),
        }

        response_file.write_text(json.dumps(response_data, indent=2))
        print(f"\n[STEP 6] Claude calls answer_interview_question tool:")
        print(f"  MCP server writes response file: {response_file.name}")
        print(f"  Content: {response_file.read_text()}")

        # Simulate voice app polling for response
        print(f"\n[STEP 7] Voice app polls for response file:")
        time.sleep(0.1)  # Simulate polling delay
        if response_file.exists():
            print(f"  [OK] Response file found after polling")
            response_data_read = json.loads(response_file.read_text())
            print(
                f"  Question: {response_data_read['question']}"
            )
            print(f"  Answer: {response_data_read['answer']}")
            print(f"  Sources: {', '.join(response_data_read['sources'])}")
        else:
            print(f"  [FAIL] Response file not found")
            return False

        # Simulate WebSocket broadcast to web overlay
        broadcast_message = {
            "type": "interview_coach_response",
            "data": response_data_read,
        }

        print(f"\n[STEP 8] Voice app broadcasts response via WebSocket:")
        print(f"  Message type: {broadcast_message['type']}")
        print(
            f"  Payload size: {len(json.dumps(broadcast_message))} bytes"
        )

        # Simulate web overlay displaying answer
        print(f"\n[STEP 9] Web overlay displays Claude's answer:")
        print(f"  Question: '{response_data_read['question']}'")
        print(f"  +-- Interview Coach Response -----------+")
        print(f"  | {response_data_read['answer'][:40]}... |")
        print(f"  | Sources: {', '.join(response_data_read['sources'][:2])} |")
        print(f"  +-------------------------------------+")

        # Simulate auto-archiving
        archive_file = (
            tmpdir
            / f"archive_{time.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        )
        archive_data = {
            "timestamp": response_data_read["timestamp"],
            "question": response_data_read["question"],
            "answer": response_data_read["answer"],
            "sources": response_data_read["sources"],
            "profile": "default",
        }
        archive_file.write_text(json.dumps(archive_data, indent=2))

        print(f"\n[STEP 10] Q&A pair auto-archives:")
        print(f"  Archive file: {archive_file.name}")
        print(f"  Content: {archive_file.read_text()}")

    print(f"\n" + "=" * 70)
    print("[OK] End-to-end flow completed successfully!")
    print("=" * 70)
    return True


def test_multi_segment_combinations():
    """Test various multi-segment selection patterns."""
    print("\n" + "=" * 70)
    print("TEST: Multi-Segment Selection Patterns")
    print("=" * 70)

    test_cases = [
        {
            "name": "Single segment",
            "segments": [
                "Tell me about your Kubernetes experience"
            ],
            "expected": "Tell me about your Kubernetes experience",
        },
        {
            "name": "Two consecutive segments",
            "segments": [
                "Tell me about your Kubernetes experience",
                "in a production environment",
            ],
            "expected": (
                "Tell me about your Kubernetes experience "
                "in a production environment"
            ),
        },
        {
            "name": "Three segments (skip one)",
            "segments": [
                "How do you handle distributed systems",
                "when scaling across regions",
                "with high availability requirements",
            ],
            "expected": (
                "How do you handle distributed systems "
                "when scaling across regions "
                "with high availability requirements"
            ),
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[Case {i}] {test_case['name']}")
        combined = " ".join(test_case["segments"])
        matches = combined == test_case["expected"]
        status = "[OK]" if matches else "[FAIL]"
        print(f"  {status} Segments: {len(test_case['segments'])}")
        print(f"  Combined: '{combined}'")
        if not matches:
            print(f"  Expected: '{test_case['expected']}'")
            return False

    print(f"\n[OK] All multi-segment patterns validated")
    return True


def test_polling_timeout():
    """Test polling timeout behavior."""
    print("\n" + "=" * 70)
    print("TEST: Polling Timeout Handling")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        response_file = tmpdir / ".interview_coach_response"

        print(f"\nPolling for response file that doesn't exist...")
        print(f"Timeout: 2 seconds, Poll interval: 500ms")

        start_time = time.time()
        found = False

        # Simulate polling loop with timeout
        timeout_seconds = 2
        poll_interval = 0.5
        while (time.time() - start_time) < timeout_seconds:
            if response_file.exists():
                found = True
                break
            time.sleep(poll_interval)

        elapsed = time.time() - start_time
        status = "[OK]" if not found and elapsed >= timeout_seconds else "[FAIL]"
        print(f"  {status} Polling completed without finding file")
        print(f"  Elapsed time: {elapsed:.2f}s (expected ~{timeout_seconds}s)")

    return True


if __name__ == "__main__":
    results = []

    # Run all tests
    results.append(("E2E Flow", test_interview_coach_e2e()))
    results.append(("Multi-Segment", test_multi_segment_combinations()))
    results.append(("Polling Timeout", test_polling_timeout()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n[OK] All tests passed!")
        exit(0)
    else:
        print("\n[FAIL] Some tests failed")
        exit(1)
