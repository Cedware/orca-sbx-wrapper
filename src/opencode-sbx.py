#!/usr/bin/env python3
"""Host-side OpenCode wrapper for SBX; Python 3, macOS/Linux."""

import json
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


def sbx_ports(sandbox, action, mapping):
    result = subprocess.run(
        ["sbx", "ports", sandbox, action, mapping],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    if result.returncode:
        raise RuntimeError(result.stdout.decode(errors="replace").strip())


def serve(argv):
    # Orca keeps stdin open as the lease; EOF must also stop the sandbox server.
    bootstrap = r'''
set -eu
for name in OPENCODE_PASSWORD OPENCODE_SERVER_USERNAME OPENCODE_SERVER_PASSWORD OPENCODE_DISABLE_SHARE; do
    IFS= read -r value
    export "$name=$value"
done
printf 'ORCA_SBX_NAME=%s\n' "${SANDBOX_NAME:?SBX did not provide SANDBOX_NAME}"
exec opencode "$@"
'''
    args = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--hostname":
            index += 2
            continue
        if not arg.startswith("--hostname="):
            args.append(arg)
        index += 1
    args.extend(["--hostname", "0.0.0.0"])

    names = (
        "OPENCODE_PASSWORD",
        "OPENCODE_SERVER_USERNAME",
        "OPENCODE_SERVER_PASSWORD",
        "OPENCODE_DISABLE_SHARE",
    )
    values = [os.environ.get(name, "") for name in names]
    if any("\n" in value or "\r" in value for value in values):
        raise RuntimeError("OpenCode server environment contains a newline")

    child = subprocess.Popen(
        ["sbx", "--no-input", "env", "exec", "-i", "--", "sh", "-c", bootstrap, "opencode-sbx", *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        # Keep diagnostics separate from Orca's machine-readable stdout.
        stderr=None,
        start_new_session=True,
    )
    sandbox = None
    mapping = None
    published = False
    ready = False
    buffer = b""
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    try:
        child.stdin.write(("\n".join(values) + "\n").encode())
        child.stdin.flush()
        selector.register(child.stdout, selectors.EVENT_READ, "server")
        selector.register(sys.stdin.buffer, selectors.EVENT_READ, "lease")
        while True:
            if not ready and time.monotonic() - started > 45:
                raise RuntimeError("Sandbox server startup timed out")
            for key, _ in selector.select(timeout=0.25):
                data = os.read(key.fileobj.fileno(), 65536)
                if key.data == "lease":
                    if not data:
                        return 0
                    child.stdin.write(data)
                    child.stdin.flush()
                    continue
                if not data:
                    code = child.wait(timeout=2)
                    return code or (0 if ready else 1)
                buffer += data
                if len(buffer) > 1048576:
                    raise RuntimeError("Sandbox server output line is too large")
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode(errors="replace").strip()
                    if text.startswith("ORCA_SBX_NAME="):
                        name = text.split("=", 1)[1]
                        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
                            raise RuntimeError("SBX returned an invalid sandbox name")
                        sandbox = name
                        continue
                    if ready:
                        continue
                    payload = None
                    url = None
                    if "--stdio" in args:
                        try:
                            payload = json.loads(text)
                        except ValueError:
                            continue
                        if isinstance(payload, dict):
                            url = payload.get("url")
                    elif text.startswith("opencode server listening on "):
                        url = text.split(" on ", 1)[1]
                    if not isinstance(url, str):
                        continue
                    address = urlsplit(url)
                    if address.scheme != "http" or not address.port or not sandbox:
                        raise RuntimeError("Sandbox server returned an invalid address")
                    if address.hostname not in ("0.0.0.0", "127.0.0.1", "localhost", "::", "::1"):
                        raise RuntimeError("Sandbox server returned an unexpected hostname")
                    with socket.socket() as reservation:
                        reservation.bind(("127.0.0.1", 0))
                        host_port = reservation.getsockname()[1]
                    mapping = f"127.0.0.1:{host_port}:{address.port}/tcp4"
                    sbx_ports(sandbox, "--publish", mapping)
                    published = True
                    local_url = f"http://127.0.0.1:{host_port}"
                    if payload is not None:
                        payload["url"] = local_url
                        print(json.dumps(payload), flush=True)
                    else:
                        print(f"opencode server listening on {local_url}", flush=True)
                    ready = True
    finally:
        selector.close()
        try:
            child.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        if published:
            try:
                sbx_ports(sandbox, "--unpublish", mapping)
            except Exception as error:
                print(f"opencode-sbx: port cleanup failed: {error}", file=sys.stderr)
        try:
            child.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()


def interrupted(signum, frame):
    raise KeyboardInterrupt


def local_opencode():
    wrapper = Path(__file__).resolve()
    configured = os.environ.get("OPENCODE_SBX_LOCAL_BINARY")
    if configured:
        candidates = [Path(configured).expanduser()]
        if not candidates[0].is_absolute():
            raise RuntimeError("OPENCODE_SBX_LOCAL_BINARY must be an absolute executable path")
    else:
        candidates = [(Path(directory) / "opencode").absolute() for directory in os.get_exec_path()]
    for binary in candidates:
        if binary.is_file() and os.access(binary, os.X_OK) and binary.resolve() != wrapper:
            return binary
    raise RuntimeError(
        "Local opencode not found; set OPENCODE_SBX_LOCAL_BINARY to the absolute path of the local OpenCode executable"
    )


def local_models(argv):
    try:
        binary = local_opencode()
    except RuntimeError as error:
        print(f"opencode-sbx: {error}", file=sys.stderr)
        return 1
    try:
        os.execv(str(binary), [str(binary), *argv])
    except OSError as error:
        print(f"opencode-sbx: Could not execute local OpenCode at {binary}: {error}", file=sys.stderr)
        return 1


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "models":
        return local_models(argv)
    if not argv or argv[0] != "serve":
        sbx_args = ["sbx", "env", "exec", "-i"]
        if sys.stdin.isatty() and sys.stdout.isatty():
            sbx_args.append("-t")
        os.execvp("sbx", [*sbx_args, "--", "opencode", *argv])
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        return serve(argv)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        print(f"opencode-sbx: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
