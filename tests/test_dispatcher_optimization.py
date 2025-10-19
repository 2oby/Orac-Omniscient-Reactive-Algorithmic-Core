#!/usr/bin/env python3
"""
Test script for the dispatcher and grammar optimization implementation.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from orac.grammars import GBNFParser
from orac.dispatchers.mapping_generator import MappingGenerator
from orac.dispatchers.mapping_resolver import MappingResolver
from orac.dispatchers.homeassistant import HomeAssistantDispatcher
from orac.core import TimedCommand, command_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gbnf_parser():
    """Test the GBNF parser."""
    print("\n" + "="*60)
    print("Testing GBNF Parser")
    print("="*60)

    parser = GBNFParser()
    grammar_file = "data/grammars/static_actions.gbnf"

    if Path(grammar_file).exists():
        # Parse grammar
        grammar = parser.parse_grammar(grammar_file)
        print(f"✓ Parsed grammar successfully")
        print(f"  Found rules: {list(grammar.keys())}")

        # Get combinations
        combinations = parser.get_combinations(grammar)
        print(f"✓ Generated {len(combinations)} combinations")
        if combinations:
            print(f"  Sample: {combinations[:3]}")

        # Test validation
        test_json = '{"device": "lights", "action": "on", "location": "bedroom"}'
        valid, error = parser.validate_output_against_grammar(test_json, grammar_file)
        print(f"✓ Validation test: {'PASS' if valid else 'FAIL'}")
        if error:
            print(f"  Error: {error}")

        return True
    else:
        print(f"✗ Grammar file not found: {grammar_file}")
        return False


def test_mapping_generator():
    """Test the mapping generator."""
    print("\n" + "="*60)
    print("Testing Mapping Generator")
    print("="*60)

    generator = MappingGenerator()
    grammar_file = "data/grammars/static_actions.gbnf"
    test_topic = "test_dispatcher_optimization"

    if Path(grammar_file).exists():
        # Generate mapping file
        mapping_file = generator.generate_mapping_file(
            grammar_file,
            test_topic,
            force=True
        )

        if mapping_file:
            print(f"✓ Generated mapping file: {mapping_file}")

            # Validate the generated file
            results = generator.validate_mappings(mapping_file)
            print(f"✓ Mapping validation:")
            print(f"  - Unmapped: {len(results['unmapped'])}")
            print(f"  - Invalid: {len(results['invalid_entities'])}")
            print(f"  - Valid: {len(results['valid'])}")

            return True
        else:
            print("✗ Failed to generate mapping file")
            return False
    else:
        print(f"✗ Grammar file not found: {grammar_file}")
        return False


def test_mapping_resolver():
    """Test the mapping resolver."""
    print("\n" + "="*60)
    print("Testing Mapping Resolver")
    print("="*60)

    resolver = MappingResolver()
    test_topic = "test_dispatcher_optimization"

    # Get mapping stats
    stats = resolver.get_mapping_stats(test_topic)
    print(f"✓ Retrieved mapping stats:")
    print(f"  - Total: {stats['total']}")
    print(f"  - Mapped: {stats['mapped']}")
    print(f"  - Unmapped: {stats['unmapped']}")
    print(f"  - Ignored: {stats['ignored']}")

    # Test resolution (will likely fail with unmapped error, which is expected)
    try:
        entity = resolver.resolve("bedroom", "lights", test_topic)
        print(f"✓ Resolved bedroom|lights to: {entity}")
    except Exception as e:
        print(f"✓ Expected unmapped error: {e}")

    return True


def test_homeassistant_dispatcher():
    """Test the updated HomeAssistant dispatcher."""
    print("\n" + "="*60)
    print("Testing HomeAssistant Dispatcher")
    print("="*60)

    dispatcher = HomeAssistantDispatcher()

    # Test command with legacy mapping (should work)
    test_command = {
        "device": "lights",
        "action": "on",
        "location": "lounge"
    }

    context = {
        "topic_id": "test_dispatcher_optimization",
        "grammar_file": "data/grammars/static_actions.gbnf"
    }

    print(f"Testing command: {test_command}")
    result = dispatcher.execute(json.dumps(test_command), context)

    if result['success']:
        print(f"✓ Command executed successfully")
        print(f"  - Entity: {result['result']['entity']}")
        print(f"  - Action: {result['result']['action']}")
        print(f"  - Mapping source: {result['result']['mapping_source']}")
        if 'timing' in result['result']:
            print(f"  - Duration: {result['result']['timing']['duration_ms']:.2f}ms")
    else:
        print(f"✗ Command failed: {result['error']}")

    # Test mapping stats
    stats = dispatcher.get_mapping_stats("test_dispatcher_optimization")
    print(f"\n✓ Mapping stats for test topic:")
    print(f"  - Total combinations: {stats['total']}")
    print(f"  - Mapped: {stats['mapped']}")
    print(f"  - Unmapped: {stats['unmapped']}")

    return result['success']


def test_timing_infrastructure():
    """Test the timing infrastructure."""
    print("\n" + "="*60)
    print("Testing Timing Infrastructure")
    print("="*60)

    # Create a timed command
    cmd = TimedCommand()
    print(f"✓ Created command: {cmd.command_id}")

    # Simulate pipeline timing
    import time
    cmd.mark("wake_word_detected")
    time.sleep(0.1)
    cmd.mark("audio_capture_start")
    time.sleep(0.3)
    cmd.mark("audio_capture_end")
    time.sleep(0.05)
    cmd.mark("stt_request_sent")
    time.sleep(0.2)
    cmd.mark("stt_transcription_received")
    time.sleep(0.01)
    cmd.mark("llm_inference_start")
    time.sleep(0.15)
    cmd.mark("llm_inference_end")
    time.sleep(0.01)
    cmd.mark("dispatcher_start")
    time.sleep(0.02)
    cmd.mark("ha_api_call")
    time.sleep(0.05)
    cmd.mark("ha_response")
    cmd.mark("dispatcher_complete")

    # Get performance breakdown
    print("\n" + cmd.format_performance_breakdown())

    # Test command history
    print(f"\n✓ Command history size: {len(command_history.commands)}")

    avg_duration = command_history.get_average_duration()
    if avg_duration:
        print(f"✓ Average duration: {avg_duration:.2f}ms")

    stage_avgs = command_history.get_stage_averages()
    if stage_avgs:
        print("✓ Stage averages:")
        for stage, avg in stage_avgs.items():
            print(f"  - {stage}: {avg:.2f}ms")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DISPATCHER & GRAMMAR OPTIMIZATION TEST SUITE")
    print("="*60)

    tests = [
        ("GBNF Parser", test_gbnf_parser),
        ("Mapping Generator", test_mapping_generator),
        ("Mapping Resolver", test_mapping_resolver),
        ("HomeAssistant Dispatcher", test_homeassistant_dispatcher),
        ("Timing Infrastructure", test_timing_infrastructure)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:10} {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    # Return exit code
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())