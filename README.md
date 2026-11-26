# Six-cycle obstructions in cubic bipartite braces

In a cubic bipartite brace of girth at least six, a six-cycle fails to be a component of a 2-factor exactly when its exterior splits into two connected shores. Each shore sends three edges to the cycle and three to the other shore. All six boundary endpoints in each shore have the same bipartition color, with opposite colors between the shores.

At order 46 this reduces the girth-six counterexample search to seven possible sizes for the smaller color class of one shore. Our bounded search certified a disconnected 2-factor for each of 26,010 distinct labeled graphs in the reduced family. In 249 certified braces, every six-cycle was blocked and the rejecting 2-factor used longer cycles. [Proof and research note](note.pdf) · [LaTeX](note.tex)

The archived [specific example](example.json) is a 46-vertex brace with 12 six-cycles, none extendible to a 2-factor. A perfect matching with complementary cycles of orders 22 and 24 rejects it for the conjecture. The independent verifier checks all 2,208 disjoint edge pairs for matching extension.

## Reproduce

Use Python 3.10 or later with the standard library. Run verification from this directory.

    python verify.py

The checker confirms the structural decomposition, girth and connectivity, rejects duplicate labeled graphs, and checks every complementary factor. For all 249 graphs recorded with zero extendible six-cycles it independently recomputes the six-cycle count and tests matching extension through the alternating triple of edges leaving each cycle. It also checks all 549,792 disjoint edge pairs across those 249 graphs to certify that each is a brace. Its brute-force controls are $K_{3,3}$ and the Heawood graph.

The ledgers were generated on Python 3.10.4 with the following commands. Each output path must be new.

    python search.py replay-candidates.jsonl --attempts 35000 --seed 461125
    python walk.py replay-candidates.jsonl replay-walk.jsonl --steps 1200 --seed 461126
    python refine.py replay-refinement.jsonl replay-candidates.jsonl replay-walk.jsonl --limit 18000

| Stage | Graphs | Witness with a six-cycle | Witness with longer cycles |
| --- | ---: | ---: | ---: |
| [Direct sampling](candidates.jsonl) | 763 | 763 | 0 |
| [Switch walks](walk.jsonl) | 7,247 | 7,247 | 0 |
| [Switch neighborhoods](refinement.jsonl) | 18,000 | 17,751 | 249 |

The search samples the reduced family and counts graphs by their labeled adjacency lists. It leaves the unrestricted 46-vertex case and the conjecture open. The related literature studies cubic brace reductions, computational bounds, and generalized matching extension. [Brace reduction](https://arxiv.org/html/2408.08128v2) · [Prior enumeration](https://arxiv.org/html/2504.12095v2) · [Generalized matching extension](https://doi.org/10.1016/j.disc.2026.115182)
