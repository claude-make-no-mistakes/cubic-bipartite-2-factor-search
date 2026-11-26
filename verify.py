"""Independently check graph structure, rejection witnesses, and zero scores."""

from collections import Counter, deque
from hashlib import sha256
from itertools import combinations, permutations
import json
from pathlib import Path


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate(rows, s):
    n = len(rows)
    check(n == 23 and s in (1, 4, 5, 6, 7, 8, 9), "Unexpected order or shore size")
    for row in rows:
        check(len(row) == 3 and row == sorted(set(row)), "Invalid adjacency list")
        check(all(type(v) is int and 0 <= v < n for v in row), "Invalid right vertex")
    check(Counter(v for row in rows for v in row) == Counter({i: 3 for i in range(n)}),
          "Right degree differs from three")
    left_masks = [sum(1 << v for v in row) for row in rows]
    check(all((a & b).bit_count() <= 1 for a, b in combinations(left_masks, 2)),
          "Four-cycle found")
    check([sorted(v for v in row if v < 3) for row in rows[:3]] == [[0, 1], [1, 2], [0, 2]],
          "Defining six-cycle missing")
    shore_edges = Counter()
    for u, row in enumerate(rows):
        left_group = (u >= 3) + (u >= 3+s)
        for v in row:
            right_group = (v >= 3) + (v >= 5+s)
            shore_edges[left_group, right_group] += 1
    expected = {(0, 0): 6, (0, 1): 3, (2, 0): 3, (2, 1): 3,
                (1, 1): 3*s, (2, 2): 3*(18-s)}
    check(shore_edges == expected, "Wrong decomposition")
    seen = {0}
    frontier = [0]
    while frontier:
        u = frontier.pop()
        for w in range(n):
            if w not in seen and left_masks[u] & left_masks[w]:
                seen.add(w)
                frontier.append(w)
    check(len(seen) == n, "Graph is disconnected")
    return left_masks


def matching_cycle_sizes(rows, assigned):
    n = len(rows)
    check(isinstance(assigned, list) and sorted(assigned) == list(range(n)),
          "Witness is not a permutation")
    inverse = [[] for _ in rows]
    for u, (row, v) in enumerate(zip(rows, assigned, strict=True)):
        check(type(v) is int and v in row, "Witness uses a nonedge")
        for neighbor in row:
            if neighbor != v:
                inverse[neighbor].append(u)
    parents = list(range(n))

    def root(u):
        while parents[u] != u:
            u = parents[u]
        return u

    for u, v in inverse:
        parents[root(v)] = root(u)
    return sorted(2*size for size in Counter(root(u) for u in range(n)).values())


def residual_match(left_masks, fixed_left, fixed_right):
    """Check residual matchability by breadth-first alternating paths."""
    n = len(left_masks)
    all_right = (1 << n) - 1
    active = all_right ^ sum(1 << v for v in fixed_right)
    owner = [-1] * n
    selected = [-1] * n
    for start in range(n):
        if start in fixed_left:
            continue
        queue = deque([start])
        previous = [-1] * n
        unseen = active
        end = -1
        while queue and end < 0:
            u = queue.popleft()
            choices = left_masks[u] & unseen
            while choices:
                bit = choices & -choices
                choices ^= bit
                unseen ^= bit
                v = bit.bit_length() - 1
                previous[v] = u
                if owner[v] < 0:
                    end = v
                    break
                queue.append(owner[v])
        if end < 0:
            return False
        while end >= 0:
            u = previous[end]
            owner[end] = u
            selected[u], end = end, selected[u]
    return True


def hexagon_scores(left_masks):
    common = [[a & b for b in left_masks] for a in left_masks]
    total = extendible = 0
    for a, b, c in combinations(range(len(left_masks)), 3):
        i, j, k = common[a][b], common[a][c], common[b][c]
        if not i or not j or not k or i == j:
            continue
        # With no 4-cycle, any equality of pair-neighbors forces i=j=k.
        total += 1
        cycle_right = i | j | k
        fixed_left = (a, b, c)
        # Force only the outside edges at the three left cycle vertices.
        # Their complements already contain all six edges of the cycle.
        fixed_right = [(left_masks[u] & ~cycle_right).bit_length() - 1 for u in fixed_left]
        if residual_match(left_masks, fixed_left, fixed_right):
            extendible += 1
    return total, extendible


def check_brace(rows, left_masks):
    pairs = 0
    for u, w in combinations(range(len(rows)), 2):
        for v in rows[u]:
            for z in rows[w]:
                if v != z:
                    check(residual_match(left_masks, (u, w), (v, z)),
                          "Two-edge matching does not extend")
                    pairs += 1
    return pairs


def controls():
    k33 = [list(range(3)) for _ in range(3)]
    heawood = [[(u+offset) % 7 for offset in (0, 1, 3)] for u in range(7)]
    for rows, expected in ((k33, 6), (heawood, 24)):
        n = len(rows)
        all_matching = [list(p) for p in permutations(range(n))
                        if all(v in row for v, row in zip(p, rows, strict=True))]
        check(len(all_matching) == expected, "Control matching count differs")
        check(all(matching_cycle_sizes(rows, p) == [2*n] for p in all_matching),
              "Control unexpectedly has a disconnected 2-factor")
    masks = [sum(1 << v for v in row) for row in heawood]
    check(hexagon_scores(masks) == (28, 0), "Heawood six-cycle control differs")


def verify():
    controls()
    runs = (("candidates.jsonl", "summary.json"), ("walk.jsonl", "walk-summary.json"),
            ("refinement.jsonl", "refinement-summary.json"))
    seen = set()
    example = None
    brace_tests = 0
    for filename, summary_path in runs:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        counts = Counter()
        digest = sha256()
        with Path(filename).open("rb") as ledger:
            for line in ledger:
                digest.update(line)
                entry = json.loads(line)
                rows, s = entry["rows"], entry["s"]
                masks = validate(rows, s)
                key = tuple(map(tuple, rows))
                check(key not in seen, "Duplicate labeled graph")
                seen.add(key)
                cycles = matching_cycle_sizes(rows, entry["matching"])
                check(len(cycles) >= 2 and cycles == entry["cycles"], "Wrong component sizes")
                if entry["route"] == "six_cycle":
                    check(6 in cycles, "Missing advertised six-cycle")
                else:
                    check(entry["route"] == "enumeration"
                          and entry["extendible_six_cycles"] == 0,
                          "Unexpected classification")
                    check(hexagon_scores(masks) == (entry["six_cycles"], 0),
                          "Zero-score graph has an extendible six-cycle")
                    brace_tests += check_brace(rows, masks)
                    if example is None:
                        example = entry
                counts[entry["route"]] += 1
        check(digest.hexdigest() == summary["candidate_ledger_sha256"], "Hash mismatch")
        check(all(summary["counts"][route] == count for route, count in counts.items()),
              "Ledger counts differ")
        print(filename, dict(counts))
    check(example is not None, "Missing brace example")
    example_data = json.loads(Path("example.json").read_text(encoding="utf-8"))
    check(example == example_data, "Archived example differs")
    print(f"Verified {len(seen)} distinct labeled graphs and {brace_tests} two-edge "
          f"extension checks. The archived example has cycles {example['cycles']}.")


if __name__ == "__main__":
    verify()
