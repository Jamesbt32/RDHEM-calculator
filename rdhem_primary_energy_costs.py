import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==================================================
# PAGE CONFIG & TITLE
# ==================================================

st.set_page_config(page_title="RDHEM Full Model", layout="wide")
st.title("RDHEM Heating Technology Cost, Energy, Carbon & Payback Model")

st.info(
    "Default efficiency (COP) assumptions are based on UK Government policy analysis "
    "from the Department for Energy Security & Net Zero (DESNZ): "
    "'Alternative Low-Carbon Heating Technology Costs – Analytical Annex "
    "(Annex B: System Efficiency)'. "
    "All technology parameters are editable for sensitivity testing."
)

# ==================================================
# FORMULAS
# ==================================================

show_formula = st.checkbox("Show calculation formulas")

if show_formula:
    st.markdown("""
    **Electrical demand (kWh)** = Heat demand ÷ Efficiency  
    **Dynamic cost (p/kWh)** = Base electricity price × (1 − Smart tariff discount)  
    **Annual cost (£/yr)** = Electrical demand × Dynamic cost ÷ 100  
    **Extra capex** = Installation cost − Baseline installation cost  
    **Effective extra capex** = Extra capex − Technology-specific grant  
    **Payback** = Effective extra capex ÷ Annual bill savings
    """)

# ==================================================
# DATA
# ==================================================

technologies = [
    "LTASHP","HTASHP","LTGSHP",
    "AAHP","Storage Heater","Electric Boiler","Infrared Heater"
]

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

defaults = {
    "base_costs": dict(zip(technologies,[16.0,17.0,18.9,20.3,22.8,28.0,29.4])),
    "efficiencies": dict(zip(technologies,[2.86,2.73,3.53,2.04,1,1,1])),
    "co2_factors": dict(zip(technologies,[0.074,0.077,0.060,0.103,0.222,0.211,0.211])),
    "install_costs": dict(zip(technologies,[12000,14000,20000,6800,4500,5000,6500]))
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v.copy()

# ==================================================
# SIDEBAR — SCENARIOS
# ==================================================

st.sidebar.header("Scenario A (Base case)")
archetype = st.sidebar.selectbox("Housing archetype", heat_demand_lookup)
baseline = st.sidebar.selectbox("Baseline technology", technologies)
discount_A = st.sidebar.slider("Smart tariff discount A (%)", 0, 50, 10)

st.sidebar.divider()
st.sidebar.header("Scenario B (Comparison)")
enable_B = st.sidebar.checkbox("Enable Scenario B")

discount_B = st.sidebar.slider(
    "Smart tariff discount B (%)",
    0, 50, discount_A,
    disabled=not enable_B
)

eff_mult_B = st.sidebar.slider(
    "Efficiency multiplier B",
    0.8, 1.2, 1.0, 0.05,
    disabled=not enable_B,
    help="Applies to all technologies in Scenario B only."
)

# ==================================================
# SIDEBAR — TECHNOLOGY-SPECIFIC GRANTS
# ==================================================

st.sidebar.divider()
st.sidebar.header("Grants / Subsidies")

enable_grant = st.sidebar.checkbox(
    "Apply technology-specific grant",
    help="Grant applies only to selected technology and reduces its extra capex vs baseline."
)

grant_tech = st.sidebar.selectbox(
    "Grant applies to technology",
    technologies,
    disabled=not enable_grant
)

grant_type = st.sidebar.radio(
    "Grant type",
    ["Flat amount (£)", "Percentage of extra capex"],
    disabled=not enable_grant
)

grant_value = st.sidebar.number_input(
    "Grant value",
    0.0, 30000.0, 7500.0, 500.0,
    disabled=not enable_grant
)

# ==================================================
# SIDEBAR — PER-TECHNOLOGY EDITING
# ==================================================

st.sidebar.divider()
st.sidebar.header("Edit Technologies")

for tech in technologies:
    with st.sidebar.expander(tech):
        st.session_state.base_costs[tech] = st.number_input(
            "Base cost (p/kWh)", 1.0, 60.0,
            float(st.session_state.base_costs[tech]), 0.1, key=f"bc_{tech}"
        )
        st.session_state.efficiencies[tech] = st.number_input(
            "Efficiency / COP", 0.5, 6.0,
            float(st.session_state.efficiencies[tech]), 0.1, key=f"eff_{tech}"
        )
        st.session_state.co2_factors[tech] = st.number_input(
            "CO₂ factor (kg/kWh)", 0.01, 1.0,
            float(st.session_state.co2_factors[tech]), 0.01, key=f"co2_{tech}"
        )
        st.session_state.install_costs[tech] = st.number_input(
            "Installation cost (£)", 1000, 50000,
            int(st.session_state.install_costs[tech]), 500, key=f"capex_{tech}"
        )

# ==================================================
# MODEL FUNCTION
# ==================================================

def run_model(discount, eff_mult=1.0):
    hd = heat_demand_lookup[archetype]
    df = pd.DataFrame({"Technology": technologies})
    df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies) * eff_mult
    df["Electrical Demand (kWh)"] = (hd / df["Efficiency"]).round(2)
    df["Dynamic Cost (p/kWh)"] = (
        df["Technology"].map(st.session_state.base_costs)
        * (1 - discount / 100)
    ).round(2)
    df["Annual Cost"] = df["Electrical Demand (kWh)"] * df["Dynamic Cost (p/kWh)"] / 100
    df["CO2"] = df["Electrical Demand (kWh)"] * df["Technology"].map(st.session_state.co2_factors)
    df["Capex"] = df["Technology"].map(st.session_state.install_costs)
    return df

df_A = run_model(discount_A)
df_B = run_model(discount_B, eff_mult_B) if enable_B else None

# ==================================================
# PAYBACK FUNCTION
# ==================================================

def apply_payback(df):
    base = df[df.Technology == baseline].iloc[0]

    def pb(r):
        saving = base["Annual Cost"] - r["Annual Cost"]
        extra = r["Capex"] - base["Capex"]

        if extra <= 0:
            return "Immediate"

        if enable_grant and r["Technology"] == grant_tech:
            if grant_type == "Flat amount (£)":
                extra -= grant_value
            else:
                extra -= extra * (grant_value / 100)
            extra = max(extra, 0)

        if saving <= 0:
            return "No payback"
        if extra == 0:
            return "Immediate"

        yrs = extra / saving
        return f"{int(yrs)}y {int((yrs % 1) * 12)}m"

    df["Payback"] = df.apply(pb, axis=1)
    return df

df_A = apply_payback(df_A)
if enable_B:
    df_B = apply_payback(df_B)

# ==================================================
# SUMMARY TABLES
# ==================================================

st.subheader("Technology Summary")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### Scenario A")
    st.dataframe(df_A, use_container_width=True)

with c2:
    st.markdown("### Scenario B")
    if enable_B:
        st.dataframe(df_B, use_container_width=True)
    else:
        st.info("Enable Scenario B to compare")

# ==================================================
# SIDE-BY-SIDE GRAPHS
# ==================================================

st.subheader("Scenario Comparison – Annual Cost (£/yr)")
c1, c2 = st.columns(2)

with c1:
    st.plotly_chart(
        px.bar(df_A, x="Technology", y="Annual Cost"),
        use_container_width=True,
        key="cost_A"
    )

with c2:
    if enable_B:
        st.plotly_chart(
            px.bar(df_B, x="Technology", y="Annual Cost"),
            use_container_width=True,
            key="cost_B"
        )
    else:
        st.info("Enable Scenario B")

st.subheader("Scenario Comparison – CO₂ Emissions (kg/yr)")
c1, c2 = st.columns(2)

with c1:
    st.plotly_chart(
        px.bar(df_A, x="Technology", y="CO2"),
        use_container_width=True,
        key="co2_A"
    )

with c2:
    if enable_B:
        st.plotly_chart(
            px.bar(df_B, x="Technology", y="CO2"),
            use_container_width=True,
            key="co2_B"
        )
    else:
        st.info("Enable Scenario B")

# ==================================================
# FOOTER
# ==================================================

st.caption(
    "Scenario B applies a global efficiency multiplier and/or tariff change for "
    "sensitivity testing. Grants are applied only to the selected technology."
)
