import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="RDHEM Full Model", layout="wide")
st.title("RDHEM Heating Technology Cost, Energy, Carbon & Payback Model")

# ===============================
# BASE DATA
# ===============================

tech_data = pd.DataFrame({
    "Technology": [
        "LTASHP", "HTASHP", "LTGSHP",
        "AAHP", "Storage Heater", "Electric Boiler", "Infrared Heater"
    ],
    "Base Cost (p/kWh)": [16.0, 17.0, 18.9, 20.3, 22.8, 28.0, 29.4]
})

co2_factors = {
    "LTASHP": 0.074,
    "HTASHP": 0.077,
    "LTGSHP": 0.060,
    "AAHP": 0.103,
    "Storage Heater": 0.222,
    "Electric Boiler": 0.211,
    "Infrared Heater": 0.211
}

install_costs = {
    "LTASHP": 12000,
    "HTASHP": 14000,
    "LTGSHP": 20000,
    "AAHP": 6800,
    "Storage Heater": 4500,
    "Electric Boiler": 5000,
    "Infrared Heater": 6500
}

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

# ===============================
# SESSION STATE – SET ONCE
# ===============================

if "smart_discount" not in st.session_state:
    st.session_state.smart_discount = 10

if "user_base_costs" not in st.session_state:
    st.session_state.user_base_costs = dict(zip(
        tech_data["Technology"],
        tech_data["Base Cost (p/kWh)"]
    ))

if "user_co2" not in st.session_state:
    st.session_state.user_co2 = co2_factors.copy()

if "user_install" not in st.session_state:
    st.session_state.user_install = install_costs.copy()

# ===============================
# SIDEBAR
# ===============================

st.sidebar.header("Controls")

# Reset – SAFE
if st.sidebar.button("Reset to Defaults"):
    st.session_state.smart_discount = 10
    st.session_state.user_base_costs = dict(zip(
        tech_data["Technology"],
        tech_data["Base Cost (p/kWh)"]
    ))
    st.session_state.user_co2 = co2_factors.copy()
    st.session_state.user_install = install_costs.copy()
    st.rerun()

archetype = st.sidebar.selectbox(
    "Housing Archetype",
    list(heat_demand_lookup.keys())
)

baseline_tech = st.sidebar.selectbox(
    "Baseline Technology",
    list(tech_data["Technology"])
)

# Smart discount – NO CONFLICT
st.sidebar.slider(
    "Smart Tariff Discount (%)",
    0, 50,
    key="smart_discount"
)

# Tech editors
st.sidebar.subheader("Edit Technologies")

for tech in tech_data["Technology"]:
    with st.sidebar.expander(tech):
        st.session_state.user_base_costs[tech] = st.number_input(
            "Base Cost (p/kWh)",
            1.0, 60.0,
            value=st.session_state.user_base_costs[tech],
            step=0.1,
            key=f"base_{tech}"
        )

        st.session_state.user_co2[tech] = st.number_input(
            "CO₂ Factor (kg/kWh)",
            0.01, 1.0,
            value=st.session_state.user_co2[tech],
            step=0.01,
            key=f"co2_{tech}"
        )

        st.session_state.user_install[tech] = st.number_input(
            "Installation Cost (£)",
            1000, 50000,
            value=st.session_state.user_install[tech],
            step=500,
            key=f"inst_{tech}"
        )

# ===============================
# CALCULATIONS
# ===============================

heat_demand = heat_demand_lookup[archetype]
discount = st.session_state.smart_discount

df = pd.DataFrame({"Technology": tech_data["Technology"]})
df["Base Cost (p/kWh)"] = df["Technology"].map(st.session_state.user_base_costs)
df["Dynamic Cost (p/kWh)"] = df["Base Cost (p/kWh)"] * (1 - discount / 100)
df["Annual Heat Demand (kWh)"] = heat_demand
df["Annual Cost (£/year)"] = (df["Dynamic Cost (p/kWh)"] / 100) * heat_demand
df["CO2 Emissions (kg/year)"] = df["Technology"].map(st.session_state.user_co2) * heat_demand
df["Installation Cost (£)"] = df["Technology"].map(st.session_state.user_install)

# ===============================
# PAYBACK (FIXED)
# ===============================

baseline = df[df["Technology"] == baseline_tech].iloc[0]
base_capex = baseline["Installation Cost (£)"]
base_opex = baseline["Annual Cost (£/year)"]

def calc_payback(row):
    delta_capex = row["Installation Cost (£)"] - base_capex
    saving = base_opex - row["Annual Cost (£/year)"]

    if saving <= 0:
        return "No Payback"
    if delta_capex <= 0:
        return "Immediate"
    return round(delta_capex / saving, 1)

df["Payback (years)"] = df.apply(calc_payback, axis=1)

# ===============================
# OUTPUT
# ===============================

st.subheader("Full Technology Comparison (Fixed)")

st.dataframe(df, use_container_width=True)

st.subheader("Charts")

st.plotly_chart(px.bar(df, x="Technology", y="Annual Cost (£/year)", title="Annual Cost"), use_container_width=True)
st.plotly_chart(px.bar(df, x="Technology", y="CO2 Emissions (kg/year)", title="CO₂ Emissions"), use_container_width=True)
st.plotly_chart(px.bar(df, x="Technology", y="Installation Cost (£)", title="Installation Cost"), use_container_width=True)

# Payback chart – numeric only
payback_numeric = df.copy()
payback_numeric["Payback_Num"] = pd.to_numeric(payback_numeric["Payback (years)"], errors="coerce")

st.plotly_chart(px.bar(payback_numeric, x="Technology", y="Payback_Num", title=f"Payback vs {baseline_tech}"), use_container_width=True)

# ===============================
# SUMMARY
# ===============================

cheapest = df.loc[df["Annual Cost (£/year)"].idxmin(), "Technology"]

valid_pb = df[df["Payback (years)"].apply(lambda x: isinstance(x, float))]
if not valid_pb.empty:
    fastest = valid_pb.loc[valid_pb["Payback (years)"].astype(float).idxmin(), "Technology"]
else:
    fastest = "None"

col1, col2 = st.columns(2)
col1.metric("Cheapest to Run", cheapest)
col2.metric("Fastest Payback", fastest)

st.caption("RDHEM Model – Fixed & Stable")

