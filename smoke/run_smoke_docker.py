import os
import sys
import subprocess
import time


def run(cmd, cwd=None, check=True):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check)


def wait_health(url: str, tries: int = 30, delay: float = 2.0):
    import requests
    for i in range(tries):
        try:
            r = requests.get(url, timeout=3)
            if r.ok:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    compose_file = os.getenv("SMOKE_COMPOSE", "docker-compose.cpu.yml")
    api_base = os.getenv("API_BASE", "http://localhost:8000")

    # Up backend
    try:
        run(["docker", "compose", "-f", compose_file, "build", "backend"], cwd=repo_root)
        run(["docker", "compose", "-f", compose_file, "up", "-d", "backend"], cwd=repo_root)
        if not wait_health(f"{api_base}/health", tries=45, delay=2):
            print("[FAIL] backend /health did not become ready")
            sys.exit(1)
        # Run the existing smoke tests
        env = os.environ.copy()
        env["API_BASE"] = api_base
        py = sys.executable
        res = subprocess.run([py, os.path.join(repo_root, "smoke", "smoke_backend.py")], env=env)
        code = res.returncode
    finally:
        # Teardown
        try:
            run(["docker", "compose", "-f", compose_file, "down", "-v"], cwd=repo_root, check=False)
        except Exception:
            pass
    sys.exit(code)


if __name__ == "__main__":
    main()

