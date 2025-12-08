import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(page_title="RDHEM Full Model", layout="wide")
st.title("RDHEM Heating Technology Cost, Energy, Carbon & Payback Model")

st.info(
    "Default assumptions align with DESNZ policy analysis. "
    "All technology parameters are editable for sensitivity and scenario testing."
)

# ==================================================
# FORMULAS
# ==================================================

show_formula = st.checkbox("Show calculation formulas", key="show_formulas")

if show_formula:
    st.markdown("""
    **Electrical demand (kWh)** = Heat demand ÷ Efficiency  
    **Dynamic cost (p/kWh)** = Base cost × (1 − Smart tariff discount)  
    **Annual cost (£/yr)** = Electrical demand × Dynamic cost ÷ 100  
    **CO₂ (kg/yr)** = Electrical demand × CO₂ factor  
    **Payback** = Δ Capex ÷ Annual cost saving
    """)

# ==================================================
# GLOSSARY
# ==================================================

with st.expander("📘 Glossary"):
    st.markdown("""
    **Efficiency / COP** – Heat output per unit electricity input  
    **Electrical Demand** – Annual electricity required  
    **Dynamic Cost** – Electricity price after smart tariff discount  
    **Annual Cost** – Annual running cost (£/yr)  
    **CO₂** – Annual operational emissions (kg)  
    **Payback** – Time to recover additional capex
    """)

# ==================================================
# DATA
# ==================================================

technologies = [
    "LTASHP","HTASHP","LTGSHP","AAHP",
    "Storage Heater","Electric Boiler","Infrared Heater"
]

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

defaults = {
    "base_costs": dict(zip(technologies,[16.0,17.0,18.9,20.3,22.8,28.0,29.4])),
    "efficiencies": dict(zip(technologies,[2.86,2.73,3.53,2.04,1.0,1.0,1.0])),
    "co2_factors": dict(zip(technologies,[0.074,0.077,0.060,0.103,0.222,0.211,0.211])),
    "install_costs": dict(zip(technologies,[12000,14000,20000,6800,4500,5000,6500]))
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v.copy()

# ==================================================
# SIDEBAR — SCENARIOS
# ==================================================

st.sidebar.header("Scenario A")

archetype = st.sidebar.selectbox(
    "Housing archetype",
    heat_demand_lookup,
    key="archetype"
)

baseline_A = st.sidebar.selectbox(
    "Baseline technology",
    technologies,
    key="baseline_A"
)

discount_A = st.sidebar.slider(
    "Smart tariff discount (%)",
    0, 50, 10,
    key="discount_A"
)

st.sidebar.divider()
st.sidebar.header("Scenario B (comparison)")

enable_B = st.sidebar.checkbox(
    "Enable Scenario B",
    key="enable_B"
)

discount_B = st.sidebar.slider(
    "Smart tariff discount B (%)",
    0, 50, discount_A,
    disabled=not enable_B,
    key="discount_B"
)

eff_mult_B = st.sidebar.slider(
    "Efficiency multiplier B",
    0.8, 1.2, 1.0, 0.05,
    disabled=not enable_B,
    help=(
        "Scenario-wide adjustment applied to all technology efficiencies in Scenario B. "
        "Used to test optimistic or pessimistic real-world system performance "
        "(e.g. commissioning quality, climate, user behaviour)."
    ),
    key="eff_mult_B"
)

# ==================================================
# SIDEBAR — PER-TECHNOLOGY EDITING
# ==================================================

st.sidebar.divider()
st.sidebar.header("Edit Technologies")

for tech in technologies:
    with st.sidebar.expander(tech):

        st.session_state.base_costs[tech] = st.number_input(
            "Base cost (p/kWh)",
            1.0, 60.0,
            float(st.session_state.base_costs[tech]), 0.1,
            key=f"base_{tech}"
        )

        st.session_state.efficiencies[tech] = st.number_input(
            "Efficiency / COP",
            0.5, 6.0,
            float(st.session_state.efficiencies[tech]), 0.1,
            key=f"eff_{tech}"
        )

        st.session_state.co2_factors[tech] = st.number_input(
            "CO₂ factor (kg/kWh)",
            0.01, 1.0,
            float(st.session_state.co2_factors[tech]), 0.01,
            key=f"co2_{tech}"
        )

        st.session_state.install_costs[tech] = st.number_input(
            "Installation cost (£)",
            1000, 50000,
            int(st.session_state.install_costs[tech]), 500,
            key=f"capex_{tech}"
        )

# ==================================================
# MODEL
# ==================================================

def run_model(discount, eff_mult):
    hd = heat_demand_lookup[archetype]
    df = pd.DataFrame({"Technology": technologies})
    df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies) * eff_mult
    df["Electrical Demand"] = hd / df["Efficiency"]
    df["Dynamic Cost"] = df["Technology"].map(st.session_state.base_costs) * (1 - discount / 100)
    df["Annual Cost"] = df["Electrical Demand"] * df["Dynamic Cost"] / 100
    df["CO2"] = df["Electrical Demand"] * df["Technology"].map(st.session_state.co2_factors)
    df["Capex"] = df["Technology"].map(st.session_state.install_costs)
    return df

df_A = run_model(discount_A, 1.0)
df_B = run_model(discount_B, eff_mult_B) if enable_B else None

# ==================================================
# SUMMARY TABLES
# ==================================================

def summary(df, baseline):
    base = df[df.Technology == baseline].iloc[0]

    def payback(r):
        saving = base["Annual Cost"] - r["Annual Cost"]
        delta = r["Capex"] - base["Capex"]
        if saving <= 0:
            return "No payback"
        if delta <= 0:
            return "Immediate"
        yrs = delta / saving
        return f"{int(yrs)}y {int((yrs % 1) * 12)}m"

    out = df.copy()
    out["Annual Cost (£/yr)"] = out["Annual Cost"].round(2)
    out["CO₂ (kg/yr)"] = out["CO2"].round(2)
    out["Payback"] = out.apply(payback, axis=1)

    return out[[
        "Technology",
        "Efficiency",
        "Electrical Demand",
        "Dynamic Cost",
        "Annual Cost (£/yr)",
        "CO₂ (kg/yr)",
        "Capex",
        "Payback"
    ]].rename(columns={"Capex": "Installation Cost (£)"})

st.subheader("Technology Summary — Scenario A")
st.dataframe(summary(df_A, baseline_A), use_container_width=True, key="summary_A")

if enable_B:
    st.subheader("Technology Summary — Scenario B")
    st.dataframe(summary(df_B, baseline_A), use_container_width=True, key="summary_B")

# ==================================================
# SIDE-BY-SIDE COMPARISON GRAPHS
# ==================================================

st.subheader("Scenario Comparison — Annual Cost (£/year)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Scenario A**")
    st.plotly_chart(
        px.bar(df_A, x="Technology", y="Annual Cost"),
        use_container_width=True,
        key="cost_A"
    )

with col2:
    st.markdown("**Scenario B**")
    if enable_B:
        st.plotly_chart(
            px.bar(df_B, x="Technology", y="Annual Cost"),
            use_container_width=True,
            key="cost_B"
        )
    else:
        st.info("Enable Scenario B to view comparison")

st.subheader("Scenario Comparison — CO₂ Emissions (kg/year)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Scenario A**")
    st.plotly_chart(
        px.bar(df_A, x="Technology", y="CO2"),
        use_container_width=True,
        key="co2_A"
    )

with col2:
    st.markdown("**Scenario B**")
    if enable_B:
        st.plotly_chart(
            px.bar(df_B, x="Technology", y="CO2"),
            use_container_width=True,
            key="co2_B"
        )
    else:
        st.info("Enable Scenario B to view comparison")

# ==================================================
# CUMULATIVE CASHFLOW
# ==================================================

st.subheader("Cumulative Cashflow vs Baseline (Scenario A)")

years = np.arange(0, 21)
base = df_A[df_A.Technology == baseline_A].iloc[0]

fig = go.Figure()
for _, r in df_A.iterrows():
    cf = -(r.Capex - base.Capex) + (base["Annual Cost"] - r["Annual Cost"]) * years
    fig.add_trace(go.Scatter(x=years, y=cf, mode="lines", name=r.Technology))

fig.add_hline(y=0, line_dash="dash")
fig.update_layout(xaxis_title="Years", yaxis_title="Cumulative cashflow (£)")

st.plotly_chart(fig, use_container_width=True, key="cashflow")

# ==================================================
# FOOTER
# ==================================================

st.caption(
    "RDHEM Model — stable, fully keyed, scenario-based technology appraisal tool "
    "for cost, carbon, and payback analysis."
)
