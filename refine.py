"""Explore switch neighborhoods from candidates with at most one extendible hexagon."""

import argparse
from collections import Counter, deque
import hashlib
from itertools import combinations, product
import json
from pathlib import Path

from search import brace, components, connected, find_disconnected_factor, graph
from walk import evaluate, switch


def run(sources, output, limit):
    seen = set()
    queue = deque()
    for source in sources:
        for line in source.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            rows = tuple(map(tuple, record["rows"]))
            if rows not in seen and record.get("extendible_six_cycles") in (0, 1):
                queue.append((record["s"], rows))
            seen.add(rows)
    counts = Counter({"starting_states": len(queue)})
    digest = hashlib.sha256()
    with output.open("xb") as ledger:
        while queue:
            s, rows = queue.popleft()
            counts["expanded_neighborhoods"] += 1
            for u, v in combinations(range(len(rows)), 2):
                for a, b in product(rows[u], rows[v]):
                    neighbor = switch(rows, s, u, v, a, b)
                    if neighbor is None or neighbor in seen:
                        continue
                    seen.add(neighbor)
                    opposite = graph(neighbor)
                    if opposite is None or not connected(neighbor, opposite):
                        continue
                    metric, assigned = evaluate(neighbor, opposite)
                    score, negative_cycle_count = metric
                    if score <= 1:
                        queue.append((s, neighbor))
                    route, checked = "six_cycle", None
                    if assigned is None:
                        assigned, route, checked = find_disconnected_factor(neighbor, opposite)
                    record = {"s": s, "rows": neighbor, "route": route, "checked": checked,
                              "matching": assigned, "extendible_six_cycles": score,
                              "six_cycles": -negative_cycle_count}
                    if assigned is not None:
                        record["cycles"] = components(neighbor, assigned)
                    else:
                        record["brace"] = brace(neighbor, opposite)
                    line = (json.dumps(record, separators=(",", ":")) + "\n").encode()
                    digest.update(line)
                    ledger.write(line)
                    counts[f"score_{score}"] += 1
                    counts[route] += 1
                    counts["examined_vertices"] += 1
                    if record.get("brace") or counts["examined_vertices"] >= limit:
                        return counts, digest.hexdigest()
    return counts, digest.hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--limit", type=int, default=18_000)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("expected positive limit")
    counts, digest = run(args.sources, args.output, args.limit)
    print(json.dumps({"limit": args.limit, "counts": counts,
                      "candidate_ledger_sha256": digest}, indent=2, sort_keys=True))
