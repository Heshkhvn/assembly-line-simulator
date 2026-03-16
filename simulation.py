"""
Assembly Line Simulation Engine
================================
Discrete-event simulation of a multi-station automotive assembly line.
Models cycle times, random breakdowns, buffer queues, and operator allocation.

Author: Hesham Asim Khan
"""

import simpy
import random
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class StationConfig:
    """Configuration for a single assembly station."""
    name: str
    cycle_time: float          # seconds per unit (base)
    cycle_time_std: float      # standard deviation for variability
    num_operators: int         # operators assigned to this station
    buffer_capacity: int       # max units in input buffer
    mtbf: float                # mean time between failures (seconds)
    mttr: float                # mean time to repair (seconds)


@dataclass
class SimulationConfig:
    """Configuration for the entire simulation run."""
    stations: List[StationConfig]
    shift_duration: float = 28800    # 8 hours in seconds
    num_shifts: int = 1
    wip_limit: Optional[int] = None  # global WIP cap (None = unlimited)
    takt_time: float = 60.0          # target takt time in seconds
    random_seed: int = 42


@dataclass
class StationMetrics:
    """Runtime metrics collected for each station."""
    name: str
    units_processed: int = 0
    total_processing_time: float = 0.0
    total_idle_time: float = 0.0
    total_blocked_time: float = 0.0
    total_downtime: float = 0.0
    num_breakdowns: int = 0
    buffer_history: List[tuple] = field(default_factory=list)  # (time, queue_len)


class AssemblyStation:
    """
    A single station on the assembly line.
    
    Each station has:
    - An input buffer (simpy.Store with capacity)
    - Operators (simpy.Resource)
    - Random breakdowns based on MTBF/MTTR
    - Cycle time variability (normal distribution)
    """

    def __init__(self, env: simpy.Environment, config: StationConfig,
                 next_station: Optional['AssemblyStation'] = None,
                 wip_limit: Optional[int] = None,
                 completed_units: Optional[list] = None):
        self.env = env
        self.config = config
        self.next_station = next_station
        self.wip_limit = wip_limit
        self.completed_units = completed_units  # only for last station

        # SimPy resources
        self.buffer = simpy.Store(env, capacity=config.buffer_capacity)
        self.operators = simpy.Resource(env, capacity=config.num_operators)
        self.broken = simpy.Container(env, capacity=1, init=0)

        # Metrics
        self.metrics = StationMetrics(name=config.name)

        # Start breakdown process
        if config.mtbf > 0:
            env.process(self._breakdown_process())

    def _breakdown_process(self):
        """Simulate random breakdowns based on MTBF/MTTR."""
        while True:
            # Time until next failure (exponential distribution)
            time_to_fail = random.expovariate(1.0 / self.config.mtbf)
            yield self.env.timeout(time_to_fail)

            # Machine breaks down
            self.metrics.num_breakdowns += 1
            down_start = self.env.now
            yield self.broken.put(1)

            # Repair time (exponential distribution)
            repair_time = random.expovariate(1.0 / self.config.mttr)
            yield self.env.timeout(repair_time)

            # Machine repaired
            yield self.broken.get(1)
            self.metrics.total_downtime += self.env.now - down_start

    def process_unit(self):
        """Main processing loop for this station."""
        while True:
            # Wait for a unit in the input buffer
            idle_start = self.env.now
            unit = yield self.buffer.get()
            self.metrics.total_idle_time += self.env.now - idle_start

            # Record buffer level
            self.metrics.buffer_history.append(
                (self.env.now, len(self.buffer.items))
            )

            # Request an operator
            with self.operators.request() as req:
                yield req

                # Wait if machine is broken
                while self.broken.level > 0:
                    yield self.env.timeout(1)

                # Process the unit (cycle time with variability)
                ct = max(1, random.gauss(
                    self.config.cycle_time,
                    self.config.cycle_time_std
                ))
                process_start = self.env.now
                yield self.env.timeout(ct)
                self.metrics.total_processing_time += ct
                self.metrics.units_processed += 1

            # Pass to next station or mark complete
            if self.next_station is not None:
                # Check WIP limit before pushing
                if self.wip_limit is not None:
                    while len(self.next_station.buffer.items) >= self.wip_limit:
                        blocked_start = self.env.now
                        yield self.env.timeout(1)
                        self.metrics.total_blocked_time += self.env.now - blocked_start

                yield self.next_station.buffer.put(unit)
            else:
                # Last station: unit is complete
                if self.completed_units is not None:
                    self.completed_units.append(self.env.now)


class AssemblyLineSimulator:
    """
    Full assembly line simulator.
    
    Creates a chain of stations, feeds units into the first station,
    and collects throughput and efficiency metrics.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.env = simpy.Environment()
        self.completed_units = []
        self.stations: List[AssemblyStation] = []
        self.throughput_log = []  # (time, cumulative_units)

        random.seed(config.random_seed)
        self._build_line()

    def _build_line(self):
        """Build the chain of stations from last to first."""
        next_station = None
        for i, station_cfg in reversed(list(enumerate(self.config.stations))):
            is_last = (i == len(self.config.stations) - 1)
            station = AssemblyStation(
                env=self.env,
                config=station_cfg,
                next_station=next_station,
                wip_limit=self.config.wip_limit,
                completed_units=self.completed_units if is_last else None,
            )
            self.stations.insert(0, station)
            next_station = station

        # Start processing at each station
        for station in self.stations:
            self.env.process(station.process_unit())

    def _feed_parts(self):
        """Feed raw units into the first station at a steady rate."""
        unit_id = 0
        while True:
            # Feed at takt time rate (slightly faster to keep line fed)
            feed_rate = self.config.takt_time * 0.8
            yield self.env.timeout(feed_rate)

            first_buffer = self.stations[0].buffer
            if first_buffer.capacity > len(first_buffer.items):
                yield first_buffer.put(f"unit_{unit_id}")
                unit_id += 1

    def _throughput_logger(self):
        """Log throughput every 60 seconds."""
        while True:
            yield self.env.timeout(60)
            self.throughput_log.append(
                (self.env.now, len(self.completed_units))
            )

    def run(self) -> Dict:
        """Run the simulation and return results."""
        self.env.process(self._feed_parts())
        self.env.process(self._throughput_logger())

        total_time = self.config.shift_duration * self.config.num_shifts
        self.env.run(until=total_time)

        return self._compute_results(total_time)

    def _compute_results(self, total_time: float) -> Dict:
        """Compute OEE, throughput, and per-station metrics."""
        total_units = len(self.completed_units)

        # Per-station results
        station_results = []
        for s in self.stations:
            m = s.metrics
            availability = 1 - (m.total_downtime / total_time) if total_time > 0 else 0
            performance = (
                (m.units_processed * s.config.cycle_time) / 
                (total_time - m.total_downtime)
            ) if (total_time - m.total_downtime) > 0 else 0
            quality = 1.0  # assume zero defects for now

            station_results.append({
                'station': m.name,
                'units_processed': m.units_processed,
                'processing_time': round(m.total_processing_time, 1),
                'idle_time': round(m.total_idle_time, 1),
                'blocked_time': round(m.total_blocked_time, 1),
                'downtime': round(m.total_downtime, 1),
                'breakdowns': m.num_breakdowns,
                'availability': round(availability * 100, 1),
                'performance': round(min(performance, 1.0) * 100, 1),
                'oee': round(availability * min(performance, 1.0) * quality * 100, 1),
            })

        # Overall metrics
        actual_takt = total_time / total_units if total_units > 0 else float('inf')
        bottleneck = min(station_results, key=lambda x: x['units_processed'])

        # Throughput over time for charting
        throughput_df = pd.DataFrame(
            self.throughput_log, columns=['time', 'cumulative_units']
        )
        if len(throughput_df) > 1:
            throughput_df['units_per_min'] = throughput_df['cumulative_units'].diff().fillna(0)
            throughput_df['time_min'] = throughput_df['time'] / 60
        else:
            throughput_df['units_per_min'] = 0
            throughput_df['time_min'] = 0

        return {
            'total_units': total_units,
            'total_time_hrs': round(total_time / 3600, 2),
            'actual_takt_time': round(actual_takt, 2),
            'target_takt_time': self.config.takt_time,
            'takt_compliance': round(
                (self.config.takt_time / actual_takt) * 100, 1
            ) if actual_takt > 0 else 0,
            'throughput_per_hour': round(total_units / (total_time / 3600), 1),
            'bottleneck': bottleneck['station'],
            'station_results': station_results,
            'throughput_df': throughput_df,
            'overall_oee': round(
                sum(s['oee'] for s in station_results) / len(station_results), 1
            ),
        }


# ============================================================
# DEFAULT LINE CONFIGURATION
# Models a simplified automotive assembly line:
# Body Shop -> Paint -> Trim -> Chassis -> Final Assembly -> QC
# ============================================================

DEFAULT_STATIONS = [
    StationConfig(
        name="Body Shop",
        cycle_time=55, cycle_time_std=5,
        num_operators=2, buffer_capacity=10,
        mtbf=7200, mttr=300,    # breaks every ~2hrs, 5min repair
    ),
    StationConfig(
        name="Paint",
        cycle_time=65, cycle_time_std=8,
        num_operators=2, buffer_capacity=8,
        mtbf=5400, mttr=600,    # breaks every ~1.5hrs, 10min repair
    ),
    StationConfig(
        name="Trim",
        cycle_time=50, cycle_time_std=4,
        num_operators=2, buffer_capacity=12,
        mtbf=9000, mttr=240,
    ),
    StationConfig(
        name="Chassis",
        cycle_time=58, cycle_time_std=6,
        num_operators=2, buffer_capacity=10,
        mtbf=7200, mttr=360,
    ),
    StationConfig(
        name="Final Assembly",
        cycle_time=60, cycle_time_std=7,
        num_operators=3, buffer_capacity=10,
        mtbf=6000, mttr=420,
    ),
    StationConfig(
        name="Quality Control",
        cycle_time=40, cycle_time_std=5,
        num_operators=2, buffer_capacity=15,
        mtbf=14400, mttr=180,
    ),
]

DEFAULT_CONFIG = SimulationConfig(
    stations=DEFAULT_STATIONS,
    shift_duration=28800,  # 8 hours
    num_shifts=1,
    wip_limit=None,
    takt_time=60,
    random_seed=42,
)
