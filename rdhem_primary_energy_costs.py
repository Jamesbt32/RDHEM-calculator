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
# SIDEBAR — SCENARIO
# ==================================================

st.sidebar.header("Scenario")

archetype = st.sidebar.selectbox("Housing archetype", heat_demand_lookup)
baseline = st.sidebar.selectbox("Baseline technology", technologies)
discount = st.sidebar.slider("Smart tariff discount (%)", 0, 50, 10)

# ==================================================
# SIDEBAR — TECHNOLOGY-SPECIFIC GRANTS
# ==================================================

st.sidebar.divider()
st.sidebar.header("Grants / Subsidies")

enable_grant = st.sidebar.checkbox(
    "Apply technology-specific grant",
    help="Grant applies only to the selected technology and reduces its extra capex vs baseline."
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
    min_value=0.0,
    max_value=30000.0,
    value=7500.0,
    step=500.0,
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
            float(st.session_state.base_costs[tech]), 0.1,
            key=f"bc_{tech}"
        )
        st.session_state.efficiencies[tech] = st.number_input(
            "Efficiency / COP", 0.5, 6.0,
            float(st.session_state.efficiencies[tech]), 0.1,
            key=f"eff_{tech}"
        )
        st.session_state.co2_factors[tech] = st.number_input(
            "CO₂ factor (kg/kWh)", 0.01, 1.0,
            float(st.session_state.co2_factors[tech]), 0.01,
            key=f"co2_{tech}"
        )
        st.session_state.install_costs[tech] = st.number_input(
            "Installation cost (£)", 1000, 50000,
            int(st.session_state.install_costs[tech]), 500,
            key=f"capex_{tech}"
        )

# ==================================================
# MODEL
# ==================================================

heat_demand = heat_demand_lookup[archetype]
df = pd.DataFrame({"Technology": technologies})

df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies)
df["Electrical Demand (kWh)"] = (heat_demand / df["Efficiency"]).round(2)

df["Dynamic Cost (p/kWh)"] = (
    df["Technology"].map(st.session_state.base_costs)
    * (1 - discount / 100)
).round(2)

df["Annual Cost"] = df["Electrical Demand (kWh)"] * df["Dynamic Cost (p/kWh)"] / 100
df["CO2"] = df["Electrical Demand (kWh)"] * df["Technology"].map(st.session_state.co2_factors)
df["Capex"] = df["Technology"].map(st.session_state.install_costs)

base = df[df.Technology == baseline].iloc[0]

# ==================================================
# PAYBACK (TECH-SPECIFIC GRANT)
# ==================================================

def payback(row):
    saving = base["Annual Cost"] - row["Annual Cost"]
    raw_extra = row["Capex"] - base["Capex"]

    if raw_extra <= 0:
        return "Immediate (lower upfront cost)"

    effective_extra = raw_extra

    if enable_grant and row["Technology"] == grant_tech:
        if grant_type == "Flat amount (£)":
            effective_extra -= grant_value
        else:
            effective_extra -= raw_extra * (grant_value / 100)
        effective_extra = max(effective_extra, 0)

    if saving <= 0:
        return "No payback (higher running cost)"

    if effective_extra == 0:
        return "Immediate (grant covers extra cost)"

    yrs = effective_extra / saving
    return f"{int(yrs)}y {int((yrs % 1) * 12)}m"

df["Payback vs baseline"] = df.apply(payback, axis=1)

# ==================================================
# SUMMARY TABLE
# ==================================================

st.subheader("Technology Summary")

display = df.copy()
display["Annual Cost (£/yr)"] = display["Annual Cost"].round(2)
display["CO₂ (kg/yr)"] = display["CO2"].round(2)

st.dataframe(
    display[[
        "Technology","Efficiency","Electrical Demand (kWh)",
        "Dynamic Cost (p/kWh)","Annual Cost (£/yr)",
        "CO₂ (kg/yr)","Capex","Payback vs baseline"
    ]].rename(columns={"Capex":"Installation Cost (£)"}),
    use_container_width=True
)

# ==================================================
# GRAPHS
# ==================================================

st.subheader("Annual Running Cost (£/year)")
fig_cost = px.bar(df, x="Technology", y="Annual Cost")
fig_cost.update_traces(
    hovertemplate="<b>%{x}</b><br>Annual Cost: £%{y:.2f}<extra></extra>"
)
fig_cost.update_yaxes(tickprefix="£", tickformat=",.2f")
st.plotly_chart(fig_cost, use_container_width=True, key="annual_cost")

st.subheader("Annual CO₂ Emissions (kg/year)")
fig_co2 = px.bar(df, x="Technology", y="CO2")
fig_co2.update_traces(
    hovertemplate="<b>%{x}</b><br>CO₂ Emissions: %{y:.2f} kg/yr<extra></extra>"
)
fig_co2.update_yaxes(tickformat=",.2f")
st.plotly_chart(fig_co2, use_container_width=True, key="co2")

# ==================================================
# CUMULATIVE CASHFLOW
# ==================================================

st.subheader("Cumulative Cashflow vs Baseline")

years = np.arange(0, 21)
fig = go.Figure()

for _, r in df.iterrows():
    extra = r["Capex"] - base["Capex"]

    if enable_grant and r["Technology"] == grant_tech:
        if grant_type == "Flat amount (£)":
            extra -= grant_value
        else:
            extra -= extra * (grant_value / 100)
        extra = max(extra, 0)

    cf = -extra + (base["Annual Cost"] - r["Annual Cost"]) * years

    fig.add_trace(go.Scatter(
        x=years,
        y=cf,
        mode="lines",
        name=r.Technology,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Year %{x}<br>"
            "Cashflow: £%{y:.2f}<extra></extra>"
        )
    ))

fig.add_hline(y=0, line_dash="dash")
fig.update_layout(xaxis_title="Years", yaxis_title="Cumulative cashflow (£)")
st.plotly_chart(fig, use_container_width=True, key="cashflow")

# ==================================================
# FOOTER
# ==================================================

st.caption(
    "Grants are applied only to the selected technology and reduce extra upfront cost "
    "relative to the baseline. Payback and cashflow exclude maintenance, financing, "
    "and asset lifetime effects."
)
