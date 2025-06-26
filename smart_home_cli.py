#!/usr/bin/env python3
"""
Smart Home CLI Parser

A simple command-line interface for parsing natural language commands
into structured JSON format using the smart home grammar.
"""

import argparse
import json
import sys
import os
from typing import Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from orac.smart_home_parser import SmartHomeParserSync, parse_smart_home_command_sync
except ImportError:
    # Fallback to standalone parser if ORAC is not available
    from smart_home_parser import SmartHomeParser

def parse_command(user_input: str, model_path: str, grammar_path: Optional[str] = None) -> dict:
    """
    Parse a natural language command into JSON.
    
    Args:
        user_input: The natural language command
        model_path: Path to the GGUF model
        grammar_path: Optional path to custom grammar file
        
    Returns:
        Parsed JSON result
    """
    try:
        if grammar_path:
            parser = SmartHomeParserSync(model_path, grammar_path)
        else:
            parser = SmartHomeParserSync(model_path)
        
        result = parser.parse_command(user_input)
        return result
    except Exception as e:
        return {"action": "error", "device": "unknown", "error": str(e)}

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse natural language commands into structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Turn on the bathroom lights"
  %(prog)s "toggle kitchen lights" --model ./models/qwen2.5-0.5b.gguf
  %(prog)s "Turn off bedroom lights" --grammar ./data/custom.gbnf
  %(prog)s --interactive --model ./models/model.gguf
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        help="Natural language command to parse"
    )
    
    parser.add_argument(
        "--model", "-m",
        default=os.getenv("SMART_HOME_MODEL_PATH"),
        help="Path to GGUF model file (default: SMART_HOME_MODEL_PATH env var)"
    )
    
    parser.add_argument(
        "--grammar", "-g",
        default="data/smart_home.gbnf",
        help="Path to GBNF grammar file (default: data/smart_home.gbnf)"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Pretty print JSON output"
    )
    
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Validate the parsed result"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress error messages"
    )
    
    args = parser.parse_args()
    
    # Check if model path is provided
    if not args.model:
        if not args.quiet:
            print("❌ Error: No model path provided", file=sys.stderr)
            print("Set SMART_HOME_MODEL_PATH environment variable or use --model", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(args.model):
        if not args.quiet:
            print(f"❌ Error: Model file not found: {args.model}", file=sys.stderr)
        sys.exit(1)
    
    # Interactive mode
    if args.interactive:
        print("🎮 Interactive Smart Home Parser")
        print("=" * 35)
        print("Type natural language commands to parse them into JSON")
        print("Type 'quit' or 'exit' to stop")
        print()
        
        try:
            while True:
                try:
                    user_input = input("💬 Command: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 Goodbye!")
                        break
                    
                    if not user_input:
                        continue
                    
                    result = parse_command(user_input, args.model, args.grammar)
                    
                    if args.pretty:
                        print(json.dumps(result, indent=2))
                    else:
                        print(json.dumps(result))
                    
                    if args.validate:
                        # Simple validation
                        valid_actions = {"turn on", "turn off", "toggle"}
                        valid_devices = {
                            "bedroom lights", "bathroom lights", 
                            "kitchen lights", "living room lights"
                        }
                        
                        action = result.get("action")
                        device = result.get("device")
                        is_valid = action in valid_actions and device in valid_devices
                        
                        if is_valid:
                            print("✅ Valid command")
                        else:
                            print("❌ Invalid command")
                    
                    print()
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    if not args.quiet:
                        print(f"❌ Error: {e}", file=sys.stderr)
        
        except Exception as e:
            if not args.quiet:
                print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Single command mode
    elif args.command:
        try:
            result = parse_command(args.command, args.model, args.grammar)
            
            if args.pretty:
                print(json.dumps(result, indent=2))
            else:
                print(json.dumps(result))
            
            if args.validate:
                # Simple validation
                valid_actions = {"turn on", "turn off", "toggle"}
                valid_devices = {
                    "bedroom lights", "bathroom lights", 
                    "kitchen lights", "living room lights"
                }
                
                action = result.get("action")
                device = result.get("device")
                is_valid = action in valid_actions and device in valid_devices
                
                if is_valid:
                    print("✅ Valid command", file=sys.stderr)
                else:
                    print("❌ Invalid command", file=sys.stderr)
                    sys.exit(1)
        
        except Exception as e:
            if not args.quiet:
                print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)
    
    # No command provided
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() 