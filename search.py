"""Search for 2-factor Hamiltonian cubic braces with a blocked six-cycle."""

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
from pathlib import Path
import random


def graph(rows):
    """Return the opposite adjacency lists, or None if invalid or girth < 6."""
    n = len(rows)
    right = [[] for _ in rows]
    pairs = set()
    for left, neighbors in enumerate(rows):
        if len(neighbors) != 3 or len(set(neighbors)) != 3:
            return None
        for r in neighbors:
            right[r].append(left)
        for pair in combinations(sorted(neighbors), 2):
            if pair in pairs:
                return None
            pairs.add(pair)
    if not all(len(neighbors) == 3 for neighbors in right):
        return None
    return right


def six_cycles(opposite):
    """Yield bipartition classes of each six-cycle in a girth >= 6 graph."""
    common = [{} for _ in opposite]
    for b, neighbors in enumerate(opposite):
        for u, v in combinations(neighbors, 2):
            common[u][v] = b
            common[v][u] = b
    for u, adjacent in enumerate(common):
        later = sorted(v for v in adjacent if v > u)
        for v, w in combinations(later, 2):
            if w in common[v] and len({adjacent[v], adjacent[w], common[v][w]}) == 3:
                yield (u, v, w), (adjacent[v], adjacent[w], common[v][w])


def fixed_edges(rows, opposite, cycle):
    left, right = cycle
    forced = [(u, next(v for v in rows[u] if v not in right)) for u in left]
    forced.extend((next(u for u in opposite[v] if u not in left), v) for v in right)
    return forced


def matching(rows, forced):
    """Find a perfect matching containing the forced edge list, if one exists."""
    n = len(rows)
    owner = [-1] * n
    used_left, used_right = set(), set()
    for left, right in forced:
        if right not in rows[left] or left in used_left or right in used_right:
            return None
        owner[right] = left
        used_left.add(left)
        used_right.add(right)
    allowed = [tuple(v for v in neighbors if v not in used_right) for neighbors in rows]
    for left in sorted(set(range(n)) - used_left, key=lambda u: (len(allowed[u]), u)):
        seen = set()

        def augment(u):
            for v in allowed[u]:
                if v in seen:
                    continue
                seen.add(v)
                if owner[v] < 0 or augment(owner[v]):
                    owner[v] = u
                    return True
            return False

        if not augment(left):
            return None
    result = [-1] * n
    for v, u in enumerate(owner):
        result[u] = v
    return result


def components(rows, assigned):
    """Return sizes of 2-factor cycles from the complement of a matching."""
    n = len(rows)
    opposite = [[] for _ in rows]
    left_edges = [[] for _ in rows]
    for u, neighbors in enumerate(rows):
        for v in neighbors:
            if assigned[u] != v:
                left_edges[u].append(v)
                opposite[v].append(u)
    sizes = []
    remaining = set(range(n))
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        stack = [start]
        left_count = 1
        while stack:
            for r in left_edges[stack.pop()]:
                for u in opposite[r]:
                    if u in remaining:
                        remaining.remove(u)
                        stack.append(u)
                        left_count += 1
        sizes.append(2 * left_count)
    return sorted(sizes)


def perfect_matchings(rows):
    """Enumerate all perfect matchings, branching on a least flexible row."""
    n = len(rows)
    masks = [sum(1 << v for v in neighbors) for neighbors in rows]
    assignment = [-1] * n

    def expand(remaining, available):
        if not remaining:
            yield tuple(assignment)
            return
        best_count = n + 1
        for u in remaining:
            choices = available & masks[u]
            count = choices.bit_count()
            if count < best_count:
                if count == 0:
                    return
                best_u, best_choices, best_count = u, choices, count
        rest = tuple(u for u in remaining if u != best_u)
        while best_choices:
            bit = best_choices & -best_choices
            best_choices ^= bit
            assignment[best_u] = bit.bit_length() - 1
            yield from expand(rest, available ^ bit)

    yield from expand(tuple(range(n)), (1 << n) - 1)


def connected(rows, opposite):
    seen = {0}
    stack = [0]
    while stack:
        for v in rows[stack.pop()]:
            for u in opposite[v]:
                if u not in seen:
                    seen.add(u)
                    stack.append(u)
    return len(seen) == len(rows)


def brace(rows, opposite):
    if not connected(rows, opposite):
        return False
    edges = [(u, v) for u, neighbors in enumerate(rows) for v in neighbors]
    return all(matching(rows, (e, f)) is not None for e, f in combinations(edges, 2)
               if e[0] != f[0] and e[1] != f[1])


def fragment(rng, small, large):
    """Give every small vertex degree 3 and keep six slots on the large side."""
    terminals = rng.sample(large, 3)
    slots = [v for v in large for _ in range(2 if v in terminals else 3)]
    # The three C-edges and three inter-shore edges fill the six slots.
    for _ in range(32):
        rng.shuffle(slots)
        rows = [tuple(slots[3*i:3*i+3]) for i in range(len(small))]
        if any(len(set(row)) != 3 for row in rows):
            continue
        pairs = [pair for row in rows for pair in combinations(sorted(row), 2)]
        if len(set(pairs)) == len(pairs):
            edges = [(u, v) for u, neighbors in zip(small, rows, strict=True) for v in neighbors]
            return edges, terminals, slots[-3:]
    return None


def sample(rng, s, t):
    # Left and right are separately numbered. In both, vertices 0..2 belong to C.
    x = fragment(rng, range(3, 3+s), range(3, 5+s))
    if x is None:
        return None
    y = fragment(rng, range(5+s, 5+s+t), range(3+s, 5+s+t))
    if y is None:
        return None
    ex, cx, bx = x
    ey, cy, by = y
    edges = ex + [(v, u) for u, v in ey]
    edges.extend((i, i) for i in range(3))
    edges.extend((i, (i+1) % 3) for i in range(3))
    edges.extend(enumerate(cx))
    edges.extend((v, i) for i, v in enumerate(cy))
    edges.extend(zip(by, bx, strict=True))
    rows = [[] for _ in range(5+s+t)]
    for u, v in edges:
        rows[u].append(v)
    return tuple(tuple(sorted(row)) for row in rows)


def find_disconnected_factor(rows, opposite):
    for cycle in six_cycles(opposite):
        assigned = matching(rows, fixed_edges(rows, opposite, cycle))
        if assigned is not None:
            return assigned, "six_cycle", None
    checked = 0
    for assigned in perfect_matchings(rows):
        checked += 1
        if len(components(rows, assigned)) > 1:
            return assigned, "enumeration", checked
    return None, "all_hamiltonian", checked


def run(attempts, seed, output):
    rng = random.Random(seed)
    counts = Counter()
    seen = set()
    digest = hashlib.sha256()
    widths = (1, 4, 5, 6, 7, 8, 9)
    with output.open("xb") as ledger:
        for attempt in range(attempts):
            s = widths[attempt % len(widths)]
            t = 18 - s
            counts[f"attempts_{s}"] += 1
            rows = sample(rng, s, t)
            if rows is None or rows in seen:
                continue
            opposite = graph(rows)
            if opposite is None or not connected(rows, opposite):
                continue
            seen.add(rows)
            counts[f"accepted_{s}"] += 1
            assigned, route, checked = find_disconnected_factor(rows, opposite)
            counts[route] += 1
            record = {"attempt": attempt, "s": s, "rows": rows, "route": route,
                      "checked": checked, "matching": assigned}
            if assigned is not None:
                record["cycles"] = components(rows, assigned)
            else:
                record["brace"] = brace(rows, opposite)
            line = (json.dumps(record, separators=(",", ":")) + "\n").encode()
            digest.update(line)
            ledger.write(line)
            if record.get("brace"):
                break
    result = {"seed": seed, "attempts_requested": attempts, "counts": dict(counts),
              "candidate_ledger_sha256": digest.hexdigest()}
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--attempts", type=int, default=35_000)
    parser.add_argument("--seed", type=int, default=461125)
    args = parser.parse_args()
    if args.attempts <= 0:
        parser.error("expected at least one attempt")
    run(args.attempts, args.seed, args.output)
