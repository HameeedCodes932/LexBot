import argparse
import subprocess
import sys
import json
from datetime import datetime


def check_packages(requirements_file="requirements.txt"):
    """Check that all required packages are installed."""
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    missing = []
    for req in requirements:
        pkg = req.split("==")[0].split(">=")[0].split("<=")[0].strip()
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", pkg],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            missing.append(pkg)

    return missing


def check_env_file(env_file=".env"):
    """Check that required env vars are set (not empty placeholders)."""
    import dotenv
    dotenv.load_dotenv(env_file)

    required = [
        "SECRET_KEY",
    ]
    optional = [
        "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
        "STRIPE_SECRET_KEY", "SENTRY_DSN",
    ]

    missing = []
    for key in required:
        val = __import__("os").getenv(key, "")
        if not val or val == "change-me-to-a-random-secret":
            missing.append(key)

    warnings = []
    for key in optional:
        val = __import__("os").getenv(key, "")
        if not val:
            warnings.append(f"{key} is empty (ok if unused)")

    return missing, warnings


def main():
    parser = argparse.ArgumentParser(description="LexBot DevOps Health Check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "checks": {},
    }

    print("--- LexBot Health Check ---")

    # Package check
    missing_pkgs = check_packages()
    status["checks"]["packages"] = {
        "status": "pass" if not missing_pkgs else "fail",
        "missing": missing_pkgs,
    }
    if missing_pkgs:
        print(f"[FAIL] Missing packages: {', '.join(missing_pkgs)}")
    else:
        print("[PASS] All packages installed")

    # Env file check
    missing_env, warnings_env = check_env_file()
    status["checks"]["env"] = {
        "status": "pass" if not missing_env else "fail",
        "missing": missing_env,
        "warnings": warnings_env,
    }
    if missing_env:
        print(f"[FAIL] Missing required env vars: {', '.join(missing_env)}")
    if warnings_env:
        for w in warnings_env:
            print(f"[WARN] {w}")
    if not missing_env and not warnings_env:
        print("[PASS] All env vars configured")

    # File structure check
    required_dirs = ["alembic", "frontend/src", "tests"]
    missing_dirs = [d for d in required_dirs if not __import__("os").path.isdir(d)]
    status["checks"]["structure"] = {
        "status": "pass" if not missing_dirs else "fail",
        "missing": missing_dirs,
    }
    if missing_dirs:
        print(f"[FAIL] Missing directories: {', '.join(missing_dirs)}")
    else:
        print("[PASS] Project structure OK")

    overall = "pass" if all(c["status"] == "pass" for c in status["checks"].values()) else "fail"
    status["overall"] = overall

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(f"\nOverall: {'PASS' if overall == 'pass' else 'FAIL'}")

    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
