#!/usr/bin/env python3
"""
Multi-seed benchmark for the placer.
Runs every testcase with several random seeds in parallel and reports the mean / std of
HPWL, CC, HPWL*CC and the normalized cost HPWL/HPWL_init + CC/CC_init (the quantity the SA minimizes). Results are saved as JSON so that two
versions of the placer can be compared.

Examples:
  # Baseline with 5 seeds
  python3 bench.py --placer ./placer --out bench/base

  # Another build, compared against the baseline
  python3 bench.py --placer ./placer --out bench/range --compare bench/base/results.json
"""

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FINAL_RE = re.compile(r'Final performance: Wirelength = ([-0-9.eE+]+), CC = ([-0-9.eE+]+)')
INITIAL_RE = re.compile(r'Initial performance: Wirelength = ([-0-9.eE+]+), CC = ([-0-9.eE+]+)')


def run_one(placer, case_file, seed, out_dir):
    case = Path(case_file).stem
    out_file = out_dir / f"{case}_s{seed}.out"
    log_file = out_dir / f"{case}_s{seed}.log"
    start = time.perf_counter()
    with open(log_file, 'w') as log:
        subprocess.run([placer, str(case_file), str(out_file), str(seed)], stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    elapsed = time.perf_counter() - start
    text = log_file.read_text()
    final, initial = FINAL_RE.search(text), INITIAL_RE.search(text)
    if not final or not initial:
        raise RuntimeError(f"no initial/final performance line in {log_file}")
    return (case, seed, float(final.group(1)), float(final.group(2)),
            float(initial.group(1)), float(initial.group(2)), elapsed)


def summarize(values):
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std


def main():
    parser = argparse.ArgumentParser(description='Run the placer on all testcases with several seeds')
    parser.add_argument('--placer', default='./placer', help='Placer binary')
    parser.add_argument('--seeds', type=int, nargs='+', default=[1, 2, 3, 4, 5])
    parser.add_argument('--cases', nargs='+', help='Testcase files (default: testcases/*.txt)')
    parser.add_argument('--out', required=True, help='Directory for outputs, logs and results.json')
    parser.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) // 2),
                        help='Parallel runs (default: half the CPUs)')
    parser.add_argument('--compare', help='results.json of another run to compare against')
    args = parser.parse_args()

    cases = args.cases or sorted(str(p) for p in Path('testcases').glob('*.txt'))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = [(c, s) for c in cases for s in args.seeds]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        runs = list(pool.map(lambda job: run_one(args.placer, job[0], job[1], out_dir), jobs))

    results = {}
    initial = {}
    for case, seed, hpwl, cc, hpwl0, cc0, elapsed in runs:
        results.setdefault(case, {})[str(seed)] = {'HPWL': hpwl, 'CC': cc, 'time': elapsed}
        initial[case] = (hpwl0, cc0)  # the initial placement does not depend on the seed
    (out_dir / 'results.json').write_text(json.dumps(results, indent=2))

    baseline = json.loads(Path(args.compare).read_text()) if args.compare else None

    def norm_cost(r, case):
        hpwl0, cc0 = initial[case]
        return r['HPWL'] / hpwl0 + r['CC'] / cc0

    header = (f"{'case':<10} {'HPWL mean±std':>18} {'CC mean±std':>18} {'HPWL*CC mean±std':>20} "
              f"{'norm cost mean±std':>20} {'time':>7}")
    if baseline:
        header += f" {'HPWL*CC vs base':>16} {'norm vs base':>13}"
    print(header)
    for case in sorted(results):
        per_seed = results[case].values()
        hpwl = summarize([r['HPWL'] for r in per_seed])
        cc = summarize([r['CC'] for r in per_seed])
        prod = summarize([r['HPWL'] * r['CC'] for r in per_seed])
        norm = summarize([norm_cost(r, case) for r in per_seed])
        line = (f"{case:<10} {hpwl[0]:>10.1f}±{hpwl[1]:<7.1f} {cc[0]:>10.4f}±{cc[1]:<7.4f} "
                f"{prod[0]:>11.1f}±{prod[1]:<8.1f} {norm[0]:>11.4f}±{norm[1]:<8.4f} "
                f"{statistics.mean(r['time'] for r in per_seed):>6.1f}s")
        if baseline and case in baseline:
            base_prod = statistics.mean(r['HPWL'] * r['CC'] for r in baseline[case].values())
            base_norm = statistics.mean(norm_cost(r, case) for r in baseline[case].values())
            line += f" {prod[0] / base_prod - 1:>+16.2%} {norm[0] / base_norm - 1:>+13.2%}"
        print(line)
    print(f"\nSaved {out_dir / 'results.json'}")


if __name__ == '__main__':
    sys.exit(main())
