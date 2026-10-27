"""mldoctor CLI (chunk A: `run` only; `serve` lands in chunk C)."""
import argparse

from .runner import classify, run_baseline


def cmd_run(args):
    runs = run_baseline(args.script, k=args.k, seed=args.seed,
                        timeout=args.timeout, jobs=args.jobs)
    result = classify(runs)
    print(f"symptom: {result['symptom']}")
    print(f"reason: {result['reason']}")
    print(f"metrics: {result['metrics']}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mldoctor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="reproduce a script and classify its symptom")
    run.add_argument("script", help="target training script path")
    run.add_argument("-k", type=int, default=5, help="baseline runs (default 5)")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--jobs", type=int, default=1)
    run.set_defaults(func=cmd_run)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
