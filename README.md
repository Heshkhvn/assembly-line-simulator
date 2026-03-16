# 🏭 Assembly Line Throughput Simulator

**Lean Manufacturing Optimization through Discrete-Event Simulation**

A Python-based simulator that models a multi-station automotive assembly line, runs Kaizen-style optimization experiments, and displays results on a real-time Streamlit dashboard.

---

## Quick Start

```bash
# 1. Clone or download this folder
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the Streamlit dashboard
streamlit run dashboard.py

# Or run experiments from command line
python experiments.py
```

---

## Project Structure

```
assembly-line-simulator/
├── simulation.py        # Core simulation engine (SimPy)
├── experiments.py       # Kaizen experiment runner
├── dashboard.py         # Streamlit dashboard (visualization)
├── requirements.txt     # Python dependencies
└── README.md            # You are here
```

---

## How It Works

### The Assembly Line (simulation.py)

The simulator models 6 stations in a typical automotive assembly sequence:

| Station | Base Cycle Time | Operators | MTBF | MTTR |
|---------|----------------|-----------|------|------|
| Body Shop | 55s | 2 | 2 hrs | 5 min |
| Paint | 65s | 2 | 1.5 hrs | 10 min |
| Trim | 50s | 2 | 2.5 hrs | 4 min |
| Chassis | 58s | 2 | 2 hrs | 6 min |
| Final Assembly | 60s | 3 | 1.7 hrs | 7 min |
| Quality Control | 40s | 2 | 4 hrs | 3 min |

Each station has:
- **Cycle time variability** — normal distribution around the base time (simulates real-world inconsistency)
- **Input buffer** — finite queue between stations (WIP storage)
- **Random breakdowns** — exponential distribution based on MTBF/MTTR
- **Operator resource** — units wait for an available operator before processing

Units flow from Body Shop → Paint → Trim → Chassis → Final Assembly → QC. If a downstream buffer is full, the upstream station is *blocked* (realistic push system behavior).

### Kaizen Experiments (experiments.py)

Runs 9 configurations and compares throughput:

1. **Baseline** — default configuration
2. **WIP Limit = 5** — tight pull system
3. **WIP Limit = 8** — moderate pull system
4. **WIP Limit = 12** — loose pull system
5. **+1 Operator at bottleneck** — resource rebalancing
6. **-10% Cycle Time at bottleneck** — process improvement
7. **Balanced Line** — equalize all cycle times
8. **2 Shifts (16 hrs)** — extended production
9. **Combined Optimization** — best of all improvements together

### Dashboard (dashboard.py)

Interactive Streamlit dashboard showing:
- **OEE Gauge** — Overall Equipment Effectiveness (Availability × Performance × Quality)
- **Takt Time Compliance** — actual cycle time per station vs. target takt
- **Throughput Over Time** — units per minute across the shift
- **Downtime Pareto** — which stations cause the most downtime
- **Station Performance Table** — detailed metrics per station
- **Time Breakdown** — stacked bar of processing, idle, blocked, and downtime
- **Kaizen Experiment Comparison** — bar chart showing throughput improvement per experiment

---

## Key Metrics Explained

| Metric | What It Means |
|--------|---------------|
| **OEE** | Availability × Performance × Quality. World-class = 85%+ |
| **Takt Time** | Available time / customer demand. The heartbeat of the line. |
| **Throughput** | Units completed per hour |
| **MTBF** | Mean Time Between Failures — how often a station breaks |
| **MTTR** | Mean Time To Repair — how long it takes to fix |
| **WIP** | Work In Process — units sitting in buffers between stations |

---

## Technologies

- **Python 3.10+**
- **SimPy** — discrete-event simulation framework
- **Streamlit** — interactive web dashboard
- **Plotly** — charts and gauges
- **Pandas** — data handling and CSV export

---

## Author

**Hesham Asim Khan**
BASc Mechatronic Systems Engineering, Simon Fraser University
[Portfolio](https://heshkhvn.github.io/hesham-khan.github.io/) | [LinkedIn](https://linkedin.com/in/hesham-khan)
