"""
Assembly Line Throughput Dashboard
====================================
Streamlit dashboard for visualizing simulation results.
Displays OEE, takt time compliance, throughput over time,
downtime Pareto charts, and Kaizen experiment comparisons.

Run with: streamlit run dashboard.py

Author: Hesham Asim Khan
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import copy
from simulation import (
    AssemblyLineSimulator, SimulationConfig, DEFAULT_CONFIG, DEFAULT_STATIONS
)
from experiments import run_kaizen_experiments


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Assembly Line Throughput Simulator",
    page_icon="🏭",
    layout="wide",
)

st.title("🏭 Assembly Line Throughput Simulator")
st.caption("Lean Manufacturing Optimization through Discrete-Event Simulation")

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
st.sidebar.header("Simulation Parameters")

num_shifts = st.sidebar.selectbox("Shifts", [1, 2, 3], index=0)
takt_target = st.sidebar.slider("Target Takt Time (s)", 30, 120, 60, 5)
wip_enabled = st.sidebar.checkbox("Enable WIP Limit")
wip_limit = st.sidebar.slider("WIP Limit per Buffer", 3, 20, 8) if wip_enabled else None
seed = st.sidebar.number_input("Random Seed", 1, 999, 42)

st.sidebar.markdown("---")
st.sidebar.subheader("Station Overrides")

# Let user tweak operator counts
operator_overrides = {}
for s in DEFAULT_STATIONS:
    operator_overrides[s.name] = st.sidebar.slider(
        f"{s.name} Operators", 1, 5, s.num_operators
    )

run_sim = st.sidebar.button("▶ Run Simulation", type="primary", use_container_width=True)
run_experiments = st.sidebar.button("🔬 Run Kaizen Experiments", use_container_width=True)

# ============================================================
# RUN SIMULATION
# ============================================================
if run_sim:
    # Build config from sidebar
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.num_shifts = num_shifts
    cfg.takt_time = takt_target
    cfg.wip_limit = wip_limit
    cfg.random_seed = seed
    for s in cfg.stations:
        s.num_operators = operator_overrides[s.name]

    with st.spinner("Simulating assembly line..."):
        sim = AssemblyLineSimulator(cfg)
        results = sim.run()

    # --------------------------------------------------------
    # TOP-LEVEL KPIs
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("Key Performance Indicators")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Units", results['total_units'])
    col2.metric("Throughput", f"{results['throughput_per_hour']} /hr")
    col3.metric("Overall OEE", f"{results['overall_oee']}%")
    col4.metric("Actual Takt", f"{results['actual_takt_time']}s",
                delta=f"{results['takt_compliance'] - 100:.1f}% vs target",
                delta_color="normal")
    col5.metric("Bottleneck", results['bottleneck'])

    # --------------------------------------------------------
    # OEE GAUGE
    # --------------------------------------------------------
    st.markdown("---")
    col_oee, col_takt = st.columns(2)

    with col_oee:
        st.subheader("Overall Equipment Effectiveness")
        fig_oee = go.Figure(go.Indicator(
            mode="gauge+number",
            value=results['overall_oee'],
            title={'text': "OEE (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#00A86B"},
                'steps': [
                    {'range': [0, 40], 'color': "#FF4444"},
                    {'range': [40, 65], 'color': "#FFA500"},
                    {'range': [65, 85], 'color': "#FFD700"},
                    {'range': [85, 100], 'color': "#90EE90"},
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 3},
                    'thickness': 0.8,
                    'value': 85
                },
            }
        ))
        fig_oee.update_layout(height=300, margin=dict(t=40, b=0))
        st.plotly_chart(fig_oee, use_container_width=True)

    # --------------------------------------------------------
    # TAKT TIME COMPLIANCE
    # --------------------------------------------------------
    with col_takt:
        st.subheader("Takt Time Compliance")
        station_df = pd.DataFrame(results['station_results'])
        station_df['effective_ct'] = round(
            station_df['processing_time'] / station_df['units_processed'], 1
        )

        fig_takt = go.Figure()
        fig_takt.add_trace(go.Bar(
            x=station_df['station'],
            y=station_df['effective_ct'],
            name='Effective Cycle Time',
            marker_color='#4A90D9',
        ))
        fig_takt.add_hline(
            y=takt_target, line_dash="dash", line_color="red",
            annotation_text=f"Takt Target: {takt_target}s"
        )
        fig_takt.update_layout(
            height=300,
            yaxis_title="Seconds",
            margin=dict(t=40, b=0),
        )
        st.plotly_chart(fig_takt, use_container_width=True)

    # --------------------------------------------------------
    # THROUGHPUT OVER TIME
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("Throughput Over Time")

    tdf = results['throughput_df']
    if len(tdf) > 2:
        fig_throughput = go.Figure()
        fig_throughput.add_trace(go.Scatter(
            x=tdf['time_min'],
            y=tdf['units_per_min'],
            mode='lines',
            name='Units/min',
            line=dict(color='#4A90D9', width=2),
            fill='tozeroy',
            fillcolor='rgba(74,144,217,0.15)',
        ))
        fig_throughput.update_layout(
            height=350,
            xaxis_title="Time (minutes)",
            yaxis_title="Units per Minute",
            margin=dict(t=20, b=0),
        )
        st.plotly_chart(fig_throughput, use_container_width=True)

    # --------------------------------------------------------
    # DOWNTIME PARETO
    # --------------------------------------------------------
    st.markdown("---")
    col_pareto, col_station = st.columns(2)

    with col_pareto:
        st.subheader("Downtime Pareto Chart")
        pareto_df = station_df[['station', 'downtime', 'breakdowns']].sort_values(
            'downtime', ascending=False
        )
        pareto_df['cumulative_pct'] = (
            pareto_df['downtime'].cumsum() / pareto_df['downtime'].sum() * 100
        )

        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=pareto_df['station'],
            y=pareto_df['downtime'],
            name='Downtime (s)',
            marker_color='#E74C3C',
        ))
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df['station'],
            y=pareto_df['cumulative_pct'],
            name='Cumulative %',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='#2C3E50', width=2),
        ))
        fig_pareto.update_layout(
            height=350,
            yaxis=dict(title='Downtime (seconds)'),
            yaxis2=dict(title='Cumulative %', overlaying='y',
                        side='right', range=[0, 110]),
            margin=dict(t=20, b=0),
            legend=dict(orientation='h', y=-0.15),
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

    # --------------------------------------------------------
    # STATION BREAKDOWN TABLE
    # --------------------------------------------------------
    with col_station:
        st.subheader("Station Performance")
        display_df = station_df[[
            'station', 'units_processed', 'availability',
            'performance', 'oee', 'breakdowns', 'downtime'
        ]].rename(columns={
            'station': 'Station',
            'units_processed': 'Units',
            'availability': 'Avail (%)',
            'performance': 'Perf (%)',
            'oee': 'OEE (%)',
            'breakdowns': 'Breakdowns',
            'downtime': 'Downtime (s)',
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --------------------------------------------------------
    # BUFFER UTILIZATION
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("Time Breakdown by Station")
    fig_time = go.Figure()
    for metric, color, label in [
        ('processing_time', '#2ECC71', 'Processing'),
        ('idle_time', '#F39C12', 'Idle'),
        ('blocked_time', '#E74C3C', 'Blocked'),
        ('downtime', '#8E44AD', 'Downtime'),
    ]:
        fig_time.add_trace(go.Bar(
            x=station_df['station'],
            y=station_df[metric],
            name=label,
            marker_color=color,
        ))
    fig_time.update_layout(
        barmode='stack',
        height=400,
        yaxis_title="Seconds",
        legend=dict(orientation='h', y=-0.15),
        margin=dict(t=20, b=0),
    )
    st.plotly_chart(fig_time, use_container_width=True)


# ============================================================
# KAIZEN EXPERIMENTS
# ============================================================
if run_experiments:
    st.markdown("---")
    st.subheader("🔬 Kaizen Experiment Results")

    with st.spinner("Running 9 experiments..."):
        summary_df, all_results = run_kaizen_experiments()

    # Experiment comparison bar chart
    fig_exp = go.Figure()
    fig_exp.add_trace(go.Bar(
        x=summary_df['Experiment'],
        y=summary_df['Throughput (units/hr)'],
        marker_color=[
            '#95A5A6' if i == 0 else
            ('#2ECC71' if row['Throughput Δ (%)'] > 0 else '#E74C3C')
            for i, (_, row) in enumerate(summary_df.iterrows())
        ],
        text=summary_df['Throughput Δ (%)'].apply(
            lambda x: f"+{x}%" if x > 0 else f"{x}%"
        ),
        textposition='outside',
    ))
    fig_exp.add_hline(
        y=summary_df.iloc[0]['Throughput (units/hr)'],
        line_dash="dash", line_color="gray",
        annotation_text="Baseline"
    )
    fig_exp.update_layout(
        height=450,
        yaxis_title="Throughput (units/hr)",
        xaxis_tickangle=-30,
        margin=dict(t=40, b=80),
    )
    st.plotly_chart(fig_exp, use_container_width=True)

    # Summary table
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # Best experiment callout
    best = summary_df.loc[summary_df['Throughput (units/hr)'].idxmax()]
    if best['Experiment'] != 'Baseline':
        st.success(
            f"**Best Configuration: {best['Experiment']}** — "
            f"{best['Throughput (units/hr)']} units/hr "
            f"({best['Throughput Δ (%)']}% improvement), "
            f"OEE: {best['OEE (%)']}%"
        )


# ============================================================
# FOOTER
# ============================================================
if not run_sim and not run_experiments:
    st.info(
        "👈 Adjust parameters in the sidebar and click "
        "**Run Simulation** to start, or **Run Kaizen Experiments** "
        "to compare optimization strategies."
    )

st.markdown("---")
st.caption(
    "Assembly Line Throughput Simulator | "
    "Discrete-Event Simulation with SimPy | "
    "Hesham Asim Khan"
)
