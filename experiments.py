"""
Kaizen Experiment Runner
=========================
Runs iterative experiments varying line balance, WIP limits, shift patterns,
and operator allocation to find optimal configurations.

Author: Hesham Asim Khan
"""

import copy
import pandas as pd
from simulation import (
    AssemblyLineSimulator, SimulationConfig, StationConfig,
    DEFAULT_STATIONS, DEFAULT_CONFIG
)


def run_experiment(name: str, config: SimulationConfig) -> dict:
    """Run a single experiment and return labeled results."""
    sim = AssemblyLineSimulator(config)
    results = sim.run()
    results['experiment'] = name
    return results


def run_kaizen_experiments() -> pd.DataFrame:
    """
    Run a full set of Kaizen-style experiments:
    1. Baseline (default config)
    2. WIP limit variations (5, 8, 12, unlimited)
    3. Operator rebalancing (add operator to bottleneck)
    4. Cycle time reduction at bottleneck (process improvement)
    5. Shift pattern variations (1 shift, 2 shifts)
    6. Combined best improvements
    """
    all_results = []

    # ----- Experiment 1: Baseline -----
    print("Running: Baseline...")
    baseline = run_experiment("Baseline", DEFAULT_CONFIG)
    all_results.append(baseline)
    bottleneck_name = baseline['bottleneck']
    print(f"  Bottleneck: {bottleneck_name}")
    print(f"  Throughput: {baseline['throughput_per_hour']} units/hr")
    print(f"  OEE: {baseline['overall_oee']}%")

    # ----- Experiment 2: WIP Limit = 5 -----
    print("Running: WIP Limit = 5...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.wip_limit = 5
    cfg.random_seed = 42
    all_results.append(run_experiment("WIP Limit = 5", cfg))

    # ----- Experiment 3: WIP Limit = 8 -----
    print("Running: WIP Limit = 8...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.wip_limit = 8
    cfg.random_seed = 42
    all_results.append(run_experiment("WIP Limit = 8", cfg))

    # ----- Experiment 4: WIP Limit = 12 -----
    print("Running: WIP Limit = 12...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.wip_limit = 12
    cfg.random_seed = 42
    all_results.append(run_experiment("WIP Limit = 12", cfg))

    # ----- Experiment 5: Add operator to bottleneck -----
    print(f"Running: +1 Operator at {bottleneck_name}...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for s in cfg.stations:
        if s.name == bottleneck_name:
            s.num_operators += 1
    cfg.random_seed = 42
    all_results.append(run_experiment(f"+1 Operator at {bottleneck_name}", cfg))

    # ----- Experiment 6: Reduce cycle time at bottleneck by 10% -----
    print(f"Running: -10% Cycle Time at {bottleneck_name}...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for s in cfg.stations:
        if s.name == bottleneck_name:
            s.cycle_time *= 0.9
            s.cycle_time_std *= 0.9
    cfg.random_seed = 42
    all_results.append(run_experiment(f"-10% CT at {bottleneck_name}", cfg))

    # ----- Experiment 7: Line balance (equalize cycle times) -----
    print("Running: Balanced Line...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    avg_ct = sum(s.cycle_time for s in cfg.stations) / len(cfg.stations)
    for s in cfg.stations:
        s.cycle_time = avg_ct
        s.cycle_time_std = 4.0
    cfg.random_seed = 42
    all_results.append(run_experiment("Balanced Line (Equal CT)", cfg))

    # ----- Experiment 8: Two shifts -----
    print("Running: 2 Shifts (16 hrs)...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.num_shifts = 2
    cfg.random_seed = 42
    all_results.append(run_experiment("2 Shifts (16 hrs)", cfg))

    # ----- Experiment 9: Combined best -----
    print("Running: Combined Optimization...")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.wip_limit = 8
    avg_ct = sum(s.cycle_time for s in cfg.stations) / len(cfg.stations)
    for s in cfg.stations:
        s.cycle_time = avg_ct * 0.95  # 5% process improvement across the board
        s.cycle_time_std = 3.5
        if s.name == bottleneck_name:
            s.num_operators += 1
    cfg.random_seed = 42
    all_results.append(run_experiment("Combined Optimization", cfg))

    # Build summary dataframe
    summary_rows = []
    for r in all_results:
        summary_rows.append({
            'Experiment': r['experiment'],
            'Total Units': r['total_units'],
            'Throughput (units/hr)': r['throughput_per_hour'],
            'Actual Takt (s)': r['actual_takt_time'],
            'Takt Compliance (%)': r['takt_compliance'],
            'OEE (%)': r['overall_oee'],
            'Bottleneck': r['bottleneck'],
            'Shift Hours': r['total_time_hrs'],
        })

    summary_df = pd.DataFrame(summary_rows)

    # Calculate improvement vs baseline
    baseline_throughput = summary_df.iloc[0]['Throughput (units/hr)']
    summary_df['Throughput Δ (%)'] = round(
        (summary_df['Throughput (units/hr)'] - baseline_throughput) 
        / baseline_throughput * 100, 1
    )

    baseline_wip = summary_df.iloc[0]['Total Units']

    # Save to CSV
    summary_df.to_csv('experiment_results.csv', index=False)
    print(f"\nResults saved to experiment_results.csv")
    print(f"\n{'='*70}")
    print(summary_df.to_string(index=False))
    print(f"{'='*70}")

    return summary_df, all_results


if __name__ == "__main__":
    summary_df, all_results = run_kaizen_experiments()
