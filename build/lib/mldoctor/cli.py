"""mldoctor CLI: `run`, `fix`, `serve` (chunk C)."""
import argparse
import os

from .budget import Budget
from .runner import classify, run_baseline


def cmd_run(args):
    runs = run_baseline(args.script, k=args.k, seed=args.seed,
                        timeout=args.timeout, jobs=args.jobs)
    result = classify(runs)
    print(f"symptom: {result['symptom']}")
    print(f"reason: {result['reason']}")
    print(f"metrics: {result['metrics']}")
    return 0


def _client(args):
    from .llm import MockClient, OpenAICompatibleClient
    budget = Budget(max_calls=args.max_calls, live=args.live,
                    ledger_path=args.ledger)
    if not args.live:
        return MockClient(budget=budget)
    if not args.base_url or not args.model:
        raise SystemExit("--live requires --base-url and --model")
    return OpenAICompatibleClient(
        base_url=args.base_url, model=args.model, budget=budget,
        api_key=os.environ.get("MLDOCTOR_API_KEY"))


def cmd_fix(args):
    from .events import EventBus
    from .pipeline import format_summary, run_pipeline
    bus = EventBus(listeners=[lambda e: print(f"[{e['seq']}] {e['type']}", flush=True)])
    s = run_pipeline(args.script, client=_client(args), bus=bus, k=args.k,
                     verify_k=args.verify_k, seed=args.seed,
                     timeout=args.timeout, out_path=args.out, jobs=args.jobs)
    print(format_summary(s))
    return 0 if s["passed"] else 1


def cmd_serve(args):
    from .server import serve
    return serve(host=args.host, port=args.port)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mldoctor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="reproduce a script and classify its symptom")
    run.add_argument("script")
    run.add_argument("-k", type=int, default=5)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument("--jobs", type=int, default=1)
    run.set_defaults(func=cmd_run)
    fix = sub.add_parser("fix", help="diagnose, patch and verify (mock by default)")
    fix.add_argument("script")
    fix.add_argument("-k", type=int, default=5)
    fix.add_argument("--verify-k", type=int, default=None)
    fix.add_argument("--seed", type=int, default=0)
    fix.add_argument("--timeout", type=int, default=180)
    fix.add_argument("--jobs", type=int, default=1)
    fix.add_argument("--out", default=None)
    fix.add_argument("--max-calls", type=int, default=8)
    fix.add_argument("--ledger", default=None)
    fix.add_argument("--live", action="store_true")
    fix.add_argument("--base-url", default=os.environ.get("MLDOCTOR_LLM_BASE_URL"))
    fix.add_argument("--model", default=os.environ.get("MLDOCTOR_LLM_MODEL"))
    fix.set_defaults(func=cmd_fix)
    serve = sub.add_parser("serve", help="local dashboard (127.0.0.1 only)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=cmd_serve)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
