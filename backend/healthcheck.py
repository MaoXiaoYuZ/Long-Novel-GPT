import http.client
import sys
import os

BACKEND_PORT = int(os.environ.get('BACKEND_PORT', 7860))


def check_health():
    try:
        conn = http.client.HTTPConnection("localhost", BACKEND_PORT)
        conn.request("GET", "/health")
        response = conn.getresponse()
        return response.status == 200
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
