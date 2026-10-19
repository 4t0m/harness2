"""Finite motif viewer with an explicitly configured remote chat-completions model.

The local browser remains bound to 127.0.0.1. Only the operator CLI configures
the upstream endpoint, served alias, checkpoint label, and auth environment.
"""

from __future__ import annotations

import argparse
import json

from .motif_remote_provider import OpenAICompatibleMotifProvider
from .motif_viewer import MotifViewer


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Finite remote-model motif viewer")
    parser.add_argument("--endpoint", required=True,
                        help="HTTPS chat completions endpoint, or literal 127.0.0.1 HTTP")
    parser.add_argument("--model", required=True, help="exact upstream served model alias")
    parser.add_argument("--auth-env", required=True, help="existing token environment variable name")
    parser.add_argument("--checkpoint-name", help="checkpoint identity label; defaults to model alias")
    parser.add_argument("--output", required=True, help="absolute new evidence JSON path")
    parser.add_argument("--lifetime", type=int, default=300, help="seconds, maximum 600")
    args = parser.parse_args(argv)
    provider = OpenAICompatibleMotifProvider(
        args.endpoint, args.model, args.auth_env,
        checkpoint_name=args.checkpoint_name)
    viewer = MotifViewer(
        args.model, args.output, lifetime=args.lifetime, provider=provider,
        provider_metadata=provider.metadata,
        extra_source_files=("harness2/motif_remote_provider.py",
                            "harness2/motif_remote_viewer.py"))
    print(json.dumps({"url": viewer.url, "model": viewer.model,
                      "provider_kind": provider.provider_kind,
                      "checkpoint_name": provider.checkpoint_name,
                      "output": str(viewer.output)}), flush=True)
    try:
        viewer.serve()
    except KeyboardInterrupt:
        viewer._close("keyboard_interrupt")


if __name__ == "__main__":
    main()
