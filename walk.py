"""Look for a brace with no extendible six-cycle using two-edge switches."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random

from search import (brace, components, connected, find_disconnected_factor,
                    fixed_edges, graph, matching, six_cycles)


def evaluate(rows, opposite):
    total = score = 0
    witness = None
    for cycle in six_cycles(opposite):
        total += 1
        assigned = matching(rows, fixed_edges(rows, opposite, cycle))
        if assigned is not None:
            score += 1
            witness = assigned
    return (score, -total), witness


def switch(rows, s, u, v, a, b):
    if (u < 3 and a < 3) or (v < 3 and b < 3) or b in rows[u] or a in rows[v]:
        return None
    left_type = lambda x: (x >= 3) + (x >= 3+s)
    right_type = lambda x: (x >= 3) + (x >= 5+s)
    if left_type(u) != left_type(v) and right_type(a) != right_type(b):
        return None
    switched = list(rows)
    switched[u] = tuple(sorted((set(rows[u]) - {a}) | {b}))
    switched[v] = tuple(sorted((set(rows[v]) - {b}) | {a}))
    return tuple(switched)


def swap(rng, rows, s):
    u, v = rng.sample(range(len(rows)), 2)
    return switch(rows, s, u, v, rng.choice(rows[u]), rng.choice(rows[v]))


def run(source, output, seed, steps):
    rng = random.Random(seed)
    starts = defaultdict(list)
    cache = {}
    for line in source.open(encoding="utf-8"):
        original = json.loads(line)
        rows = tuple(tuple(row) for row in original["rows"])
        score, _ = evaluate(rows, graph(rows))
        cache[rows] = score
        starts[original["s"]].append((score, rows))
    counts = Counter()
    best = {}
    digest = hashlib.sha256()
    with output.open("xb") as ledger:
        for s, seeds in sorted(starts.items()):
            for start_score, start_rows in sorted(seeds)[:5]:
                rows, score = start_rows, start_score
                best[s] = min(best.get(s, score[0]), score[0])
                for step in range(steps):
                    counts[f"attempts_{s}"] += 1
                    neighbor = swap(rng, rows, s)
                    if neighbor is None:
                        continue
                    metric = cache.get(neighbor)
                    if metric is None:
                        opposite = graph(neighbor)
                        if opposite is None or not connected(neighbor, opposite):
                            continue
                        metric, assigned = evaluate(neighbor, opposite)
                        cache[neighbor] = metric
                        counts[f"accepted_{s}"] += 1
                        best[s] = min(best[s], metric[0])
                        route = "six_cycle"
                        checked = None
                        if assigned is None:
                            assigned, route, checked = find_disconnected_factor(neighbor, opposite)
                        record = {"s": s, "rows": neighbor, "route": route, "checked": checked,
                                  "matching": assigned, "extendible_six_cycles": metric[0],
                                  "six_cycles": -metric[1]}
                        if assigned is not None:
                            record["cycles"] = components(neighbor, assigned)
                        else:
                            record["brace"] = brace(neighbor, opposite)
                        line = (json.dumps(record, separators=(",", ":")) + "\n").encode()
                        digest.update(line)
                        ledger.write(line)
                        counts[route] += 1
                        if record.get("brace"):
                            return counts, best, digest.hexdigest()
                    difference = max(0, metric[0] - score[0])
                    # Accept some uphill steps and cool toward the end.
                    denominator = (2 + 2 * (step >= steps // 2))**difference
                    if metric <= score or rng.randrange(max(2, denominator)) == 0:
                        rows, score = neighbor, metric
    return counts, best, digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=461126)
    parser.add_argument("--steps", type=int, default=1200)
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("expected positive steps")
    counts, best, digest = run(args.source, args.output, args.seed, args.steps)
    print(json.dumps({"seed": args.seed, "steps_per_start": args.steps, "counts": counts,
                      "best_extendible_six_cycles": best, "candidate_ledger_sha256": digest},
                     indent=2, sort_keys=True))
