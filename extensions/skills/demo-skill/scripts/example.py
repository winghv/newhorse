#!/usr/bin/env python3
"""
Demo Skill - Example Script

This is an example helper script that can be executed by the agent.
Scripts in the skills/*/scripts/ directory can perform deterministic
operations that are better handled by code than by the LLM.

Usage:
    python example.py [--name NAME]

Example:
    python example.py --name "World"
    # Output: Hello, World!
"""

import argparse
import json
import sys
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Demo skill example script")
    parser.add_argument("--name", default="Newhorse", help="Name to greet")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = {
        "message": f"Hello, {args.name}!",
        "timestamp": datetime.now().isoformat(),
        "skill": "demo-skill",
        "version": "1.0.0",
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Hello, {args.name}!")
        print(f"Time: {result['timestamp']}")
        print(f"Skill: {result['skill']} v{result['version']}")


if __name__ == "__main__":
    main()
