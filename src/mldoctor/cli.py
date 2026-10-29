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
    from .llm import LLMError, MockClient, OpenAICompatibleClient
    budget = Budget(max_calls=args.max_calls, live=args.live,
                    ledger_path=args.ledger)
    if not args.live:
        return MockClient(budget=budget)
    try:
        if args.base_url or args.model:
            if not args.base_url or not args.model:
                raise SystemExit("--live requires both --base-url and --model (or MLDOCTOR_BASE_URL/MLDOCTOR_MODEL)")
            return OpenAICompatibleClient(
                base_url=args.base_url, model=args.model, budget=budget,
                api_key=(os.environ.get("MLDOCTOR_API_KEY")
                         or os.environ.get("BASETEN_API_KEY")),
                auth_scheme=os.environ.get("MLDOCTOR_AUTH_SCHEME", "Bearer"),
                max_tokens=args.max_tokens)
        client = OpenAICompatibleClient.from_env(budget, max_tokens=args.max_tokens)
        return client
    except LLMError as exc:
        raise SystemExit(str(exc)) from exc


def cmd_fix(args):
    from .events import EventBus
    from .pipeline import format_summary, run_pipeline
    from . import proof as proof_mod
    bus = EventBus(listeners=[lambda e: print(f"[{e['seq']}] {e['type']}", flush=True)])
    s = run_pipeline(args.script, client=_client(args), bus=bus, k=args.k,
                     verify_k=args.verify_k, seed=args.seed,
                     timeout=args.timeout, out_path=args.out, jobs=args.jobs,
                     investigate=args.investigate, vision=args.vision)
    print(format_summary(s))
    if args.proof:
        path, b = proof_mod.write_bundle(args.script, s, args.proof)
        print(f"proof: {path}")
        proof_mod.export_patch_file(args.script, s, args.proof)
    if args.export_patch:
        p = proof_mod.export_patch_file(args.script, s, args.export_patch)
        print(f"patch: {p}")
    return 0 if s["passed"] else 1


def cmd_check(args):
    runs = run_baseline(args.script, k=args.runs, seed=args.seed,
                        timeout=args.timeout)
    result = classify(runs)
    print(f"symptom: {result['symptom']}")
    print(f"reason: {result['reason']}")
    print(f"metrics: {result['metrics']}")
    return 0 if result["symptom"] == "healthy" else 1


def cmd_recheck(args):
    import json
    from . import proof as proof_mod
    with open(args.bundle) as fh:
        bundle = json.load(fh)
    out = proof_mod.recheck_bundle(bundle)
    print(out["message"])
    return 1 if out["verdict_mismatch"] else 0


def cmd_serve(args):
    from .server import serve
    return serve(host=args.host, port=args.port)


def main(argv=None):
    from .llm import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser(prog="mldoctor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="reproduce a script and classify its symptom")
    run.add_argument("script")
    run.add_argument("-k", type=int, default=5,
                     help="baseline same-seed runs to classify (default 5)")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument("--jobs", type=int, default=1)
    run.set_defaults(func=cmd_run)
    fix = sub.add_parser("fix", help="diagnose, patch and verify (mock by default)")
    fix.add_argument("script")
    fix.add_argument("-k", type=int, default=5,
                     help="baseline same-seed runs to classify (default 5)")
    fix.add_argument("--verify-k", type=int, default=None,
                     help="override verification count (default: 10 same-seed runs "
                          "for non_reproducible, 5 seeds for diverged)")
    fix.add_argument("--seed", type=int, default=0)
    fix.add_argument("--timeout", type=int, default=180)
    fix.add_argument("--jobs", type=int, default=1)
    fix.add_argument("--out", default=None,
                     help="patched output (default .mldoctor/patched/<name>.patched.py)")
    fix.add_argument("--max-calls", type=int, default=8)
    fix.add_argument("--ledger", default=None)
    fix.add_argument("--live", action="store_true")
    fix.add_argument("--base-url", default=os.environ.get("MLDOCTOR_BASE_URL"))
    fix.add_argument("--model", default=os.environ.get("MLDOCTOR_MODEL"))
    fix.add_argument("--max-tokens", type=int, default=1024)
    fix.add_argument("--investigate", action="store_true",
                     help="run the fixed experiment-menu investigation loop (max 3)")
    fix.add_argument("--vision", action="store_true",
                     help="opt-in: send the loss-curve PNG with the diagnose probe")
    fix.add_argument("--proof", default=None,
                     help="write a proof bundle .json next to this path")
    fix.add_argument("--export-patch", default=None,
                     help="also write a .patch file plus markdown PR description")
    fix.set_defaults(func=cmd_fix)
    check = sub.add_parser("check", help="exit 0 only when reproducible and healthy")
    check.add_argument("script")
    check.add_argument("--runs", type=int, default=3)
    check.add_argument("--seed", type=int, default=0)
    check.add_argument("--timeout", type=int, default=180)
    check.set_defaults(func=cmd_check)
    recl = sub.add_parser("recheck", help="re-run verification from a proof bundle.json")
    recl.add_argument("bundle")
    recl.set_defaults(func=cmd_recheck)
    serve = sub.add_parser("serve", help="local dashboard (127.0.0.1 only)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=cmd_serve)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
