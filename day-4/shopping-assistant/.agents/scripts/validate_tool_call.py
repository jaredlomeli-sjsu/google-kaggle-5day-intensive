import sys
import json

def main():
    try:
        context = json.load(sys.stdin)
        command = context.get("tool_args", {}).get("CommandLine", "")

        if "rm -rf /" in command or "mkfs" in command:
            print("BLOCKED: Destructive command detected.", file=sys.stderr)
            sys.exit(1)

        print("APPROVED: Command validation passed.")
        sys.exit(0)
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
