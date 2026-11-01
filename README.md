# FPGA Placement with Simulated Annealing: Approach Report

## 1. Overview
This project implements a simulated annealing (SA) based placer for FPGA logic blocks and IOs. The placer aims to minimize total wirelength and congestion, efficiently handling large netlists and grid sizes by leveraging incremental update techniques and careful cost function design.

![Overall flow](docs/figures/flow.png)

### Performance Summary
| Case Name | Initial Wirelength | Final Wirelength | Initial CC | Final CC | Net count | IO count | Block count |
|-----------|--------------------|------------------|------------|----------|-----------|----------|-------------|
|   alu4    |    5952.000000     |   2655.000000    |  1.607460  | 1.065947 |    222    |    16    |     475     |
|   apex4   |    7803.000000     |   3954.000000    |  1.693350  | 1.042499 |    335    |    16    |     411     |
|  clma_2   |    95364.000000    |   41661.000000   |  1.650540  | 1.029874 |   1559    |    61    |    3580     |
| elliptic  |    15920.000000    |   5752.000000    |  1.407780  | 1.035103 |    467    |   128    |     968     |
|    pdc    |    37012.000000    |   17811.000000   |  1.660340  | 1.042976 |    784    |    34    |    1513     |




## 2. Simulated Annealing Cost Function Design and Parameters
Each move is evaluated by the cost change, which weighs the relative changes of total wirelength and congestion cost equally:

$$
	\Delta\text{Cost} = S \cdot \left( \frac{\Delta \text{HPWL}}{\text{HPWL}_\text{prev}} + \frac{\Delta \text{CC}}{\text{CC}_\text{prev}} \right)
$$

Where:
- $\text{HPWL}$ is the sum of half-perimeter wirelengths of all nets.
- $\text{CC} = N \cdot \sum U^2 / (\sum U)^2 = 1 + (\sigma_U / \mu_U)^2$ is the congestion cost of the cell coverage map $U$ over its $N$ cells, computed from the linear and quadratic sums of $U$. $\text{CC} = 1$ means perfectly uniform coverage.
- $S = 100 \times 800{,}000$ is a fixed cost scale (100 times the first round's initial temperature). It does not change between rounds, so lowering the initial temperature of a later round really makes that round start colder.

$\Delta\text{Cost}$ is the step of $S \cdot \ln(\text{HPWL} \cdot \text{CC})$, so the quantity being minimized is $\text{HPWL} \cdot \text{CC}$. A move is accepted if $\Delta\text{Cost} < 0$, or otherwise with probability $e^{-\Delta\text{Cost} / T}$.

**Best solution:** whenever an accepted move gives a lower $\text{HPWL} \cdot \text{CC}$ than the best placement seen so far, that placement is saved. The saved best placement is written as the output.

**Parameter values used:**
- SA rounds: 5
- Initial temperature: $T_0 = 800{,}000$ for round 1; each later round starts at $0.66\times$ the previous round's initial temperature
- Cooling interval: every 5,000 iterations
- Cooling rates: $0.9$ (acceptance rate $>0.95$), $0.99$ ($>0.8$), $0.99$ ($>0.15$), $0.9$ (otherwise)
- Termination: each round ends when $T < 10^{-3}$, with a safety time limit of 235 seconds for the whole run





## 3. Temperature Tuning Logic
The temperature schedule is adaptive and dynamically controlled based on the acceptance rate of moves:

**Initialization and rounds:**
- The initial temperature $T_0$ is set to a high value (800,000) to allow broad exploration.
- SA runs for 5 rounds. Each round continues from the placement left by the previous round and reheats to $0.66\times$ the previous round's initial temperature ($800{,}000 \to 528{,}000 \to 348{,}480 \to 229{,}997 \to 151{,}798$), so later rounds explore less and refine more.

**Cooling Schedule:**
- Every 5000 iterations, the acceptance rate (ratio of accepted moves to attempted moves) is measured.
- The cooling rate is chosen according to the following logic:

```
if (acceptRate > 0.95)
	coolingRate = 0.9;
else if (acceptRate > 0.8)
	coolingRate = 0.99;
else if (acceptRate > 0.15)
	coolingRate = 0.99;
else
	coolingRate = 0.9;
T = T * coolingRate;
```

- This means the temperature drops quickly ($\times 0.9$) at both ends: when almost every move is accepted (accept rate $>0.95$, the placement is still random), and when almost every move is rejected (accept rate $\le 0.15$, the placement is frozen). In between, where most of the useful optimization happens, it cools slowly ($\times 0.99$).
- A round ends when $T < 10^{-3}$. A time limit of 235 seconds for the whole run is kept as a safety net, but the test cases finish well before it (28 to 97 seconds for all 5 rounds).

## 4. Fast Incremental Updates for Nets, U, and Congestion Costs
To achieve high performance, the code uses several incremental update techniques:


### 4.1. Net Bounding Box Updates
- Each net maintains its bounding box ($x_{min}$, $x_{max}$, $y_{min}$, $y_{max}$).
- When a block is moved or swapped, only the nets connected to the affected blocks are considered.
- Nets that contain **both** moving blocks (during a swap) are filtered out since their bounding box cannot change.
- For each affected net, a fast anchor check is performed:
	- If the moved block was on the bounding box boundary, we check if another block/IO still "anchors" that boundary.
	- If an anchor is found, the boundary is preserved without full recalculation.
	- Otherwise, the full bounding box is recalculated by scanning all connected blocks and IOs.
- The recalculation is performed separately for X and Y axes to avoid mixing partial results.
- All changes are recorded in a `NetDiff` structure, allowing efficient rollback if a move is rejected.

![Net bounding box update](docs/figures/bbox_update.png)

**Pseudocode:**
```
for each affected net:
		save old bounding box (x_min, x_max, y_min, y_max)
		update bounding box with new block positions:
				if moved block extends box:
						x_min = min(x_min, new_x)
						x_max = max(x_max, new_x + 1)
						... (same for y)
				if moved block was on box edge:
						scan all connected blocks and IOs to find new min/max
		record new bounding box in NetDiff
```


### 4.2. U Grid and Congestion Cost Updates
- The cell coverage map $U$ is updated incrementally:
	- For each affected net, the old bounding box region is decremented and the new region is incremented.
- Congestion costs ($CC_{linear}$ and $CC_{square}$) are updated in place as $U$ changes, avoiding full recomputation.
- Rollback is supported by applying the inverse of the recorded diffs.

![U incremental update](docs/figures/u_update.png)

**Pseudocode:**
```
for each NetDiff in net_diffs:
		// Remove old coverage
		for x in ceil(old_x_min) to floor(old_x_max)-1:
				for y in ceil(old_y_min) to floor(old_y_max)-1:
						CC_linear -= U[x][y]
						CC_square -= U[x][y] * U[x][y]
						U[x][y] -= 1
		// Add new coverage
		for x in ceil(new_x_min) to floor(new_x_max)-1:
				for y in ceil(new_y_min) to floor(new_y_max)-1:
						U[x][y] += 1
						CC_linear += U[x][y]
						CC_square += U[x][y] * U[x][y]
```


### 4.3. Efficient Data Structures
- Static buffers (`static vector<pair<int, bool>> affected_nets` and `static vector<NetDiff> net_diffs`, see `SA_update.cpp`) are used for affected nets and net diffs to avoid repeated allocations.
- All updates and rollbacks are performed in-place, minimizing overhead and maximizing cache efficiency.

## 5. Optimization Improvements

### 5.1 Affected Net Filtering
During block swaps, nets that connect both moving blocks are excluded from the cost evaluation since their bounding box is invariant to the swap. This is detected using a hash set intersection in $O(n_1 + n_2)$ time, avoiding redundant calculations.

![Affected net filtering](docs/figures/net_filter.png)

### 5.2 Anchor-Based Boundary Checks
The bounding box update uses anchor checks to determine when a boundary can change:
- If a block moves away from a boundary, we search for another block/IO ("anchor") that still occupies that boundary position.
- If an anchor exists, the boundary is preserved without full recalculation.
- If no anchor exists, only that specific axis needs full recalculation, reducing redundant work.

![Anchor check](docs/figures/anchor_check.png)

## 6. Visualization
- With `SA_TRACE` enabled in `src/main.cpp` (on by default), the placer writes `<output>_trace.csv` next to the output file, with one row per temperature step: round, iteration, time, $T$, acceptance rate, and the current and best HPWL and CC.
- `./plot_all.sh` turns the results in `result/` into these plots in `plot/`:

| Plot | Script | Content |
|------|--------|---------|
| `<case>_density.png` | `plot_placement.py --mode density` | Initial and final placement side by side, colored by $U$ on a shared scale |
| `<case>_cc.png` | `plot_placement.py --mode cc` | Initial and final $U / \text{mean}(U)$ on a shared scale centered at 1 |
| `<case>_hpwl.png` | `plot_metrics.py` | Per-net HPWL, initial vs final |
| `<case>_sa.png` | `plot_sa.py` | HPWL, CC, cost, temperature and acceptance rate over the SA iterations |
| `summary.png` | `plot_metrics.py --all` | HPWL and excess congestion $\text{CC} - 1$ of all cases, final as a percentage of initial |

- The diagrams in this report are generated by `python3 docs/make_diagrams.py` into `docs/figures/` (PNG and SVG).


## References
<!-- To be completed manually -->
1. “A Congestion Driven Placement Algorithm for FPGA Synthesis”, In Proceedings of the International Conference on Field Programmable Logic and Applications (FPL 2006)
2. Vaughn Betz and Jonathan Rose. 1997. VPR: A new packing, placement and routing tool for FPGA research. In Proceedings of the 7th International Workshop on Field-Programmable Logic and Applications (FPL '97). Springer-Verlag, Berlin, Heidelberg, 213–222.