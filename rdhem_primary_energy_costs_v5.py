import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_icon="🔥",
    layout="wide"
)



# ==================================================
# DEFAULTS
# ==================================================
BASE_DEFAULTS = {
    "archetype": "Smaller Mid-Terrace On-Gas",
    "baseline": "Gas Condensing Boiler",
    "disc_A": 10,
    "enable_B": False,
    "disc_B": 10,
    "effmult_B": 1.0,
    "enable_grant": False,
    "grant_tech": "LTASHP",
    "grant_value": 7500.0,
    "elec_price": 30.0,
    "gas_price": 10.0,
    "elec_sc": 150.0,
    "gas_sc": 300.0,
}

TECH_DEFAULTS = {
    "efficiencies": {
        "LTASHP": 2.86, "HTASHP": 2.73, "LTGSHP": 3.53, "AAHP": 2.04,
        "Storage Heater": 1.0, "Electric Boiler": 1.0, "Infrared Heater": 1.0,
        "Gas Condensing Boiler": 0.895, "Gas Non-Condensing Boiler": 0.6
    },
    "co2_factors": {
        "LTASHP": 0.074, "HTASHP": 0.077, "LTGSHP": 0.060, "AAHP": 0.103,
        "Storage Heater": 0.222, "Electric Boiler": 0.211, "Infrared Heater": 0.211,
        "Gas Condensing Boiler": 0.184, "Gas Non-Condensing Boiler": 0.184
    },
    "install_costs": {
        "LTASHP": 12000, "HTASHP": 14000, "LTGSHP": 20000, "AAHP": 6800,
        "Storage Heater": 4500, "Electric Boiler": 5000, "Infrared Heater": 6500,
        "Gas Condensing Boiler": 3500, "Gas Non-Condensing Boiler": 3000
    }
}

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

# ==================================================
# INIT SESSION STATE
# ==================================================
for k, v in BASE_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

for k, v in TECH_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v.copy()

technologies = list(st.session_state["efficiencies"].keys())

for tech in technologies:
    st.session_state.setdefault(f"eff_{tech}", st.session_state["efficiencies"][tech])
    st.session_state.setdefault(f"co2_{tech}", st.session_state["co2_factors"][tech])
    st.session_state.setdefault(f"capex_{tech}", st.session_state["install_costs"][tech])

# ==================================================
# RESET BUTTON
# ==================================================
if st.sidebar.button("🔄 Reset all inputs to defaults"):
    st.session_state.clear()
    st.rerun()

# ==================================================
# TITLE
# ==================================================
st.title("Clean heat operation carbon and cost tool")

with st.expander("How to use this tool", expanded=False):
    st.markdown("""
• **Select a housing archetype** to define annual heat demand  
• **Choose a baseline technology** – all savings and payback are calculated relative to this  
• **Set fuel prices and standing charges**, including any smart tariff discounts  
• **Review or edit technology assumptions** such as efficiencies, emissions factors, and installation costs  

**Scenario comparison**  
• **Scenario A** represents the primary or reference case  
• **Scenario B** allows testing alternative assumptions alongside Scenario A  
  – Different electricity tariff discount  
  – Different assumed system efficiency  
• Results are shown side-by-side for comparison  

**Interpreting results**  
• *Annual cost* includes fuel and standing charges  
• *Payback (years)* shows simple payback versus the baseline  
  – *Immediate* = lower upfront cost than baseline  
  – *No payback* = higher running cost than baseline  
""")

# ==================================================
# FUEL TYPES
# ==================================================
fuel_type = {
    "LTASHP": "electric", "HTASHP": "electric", "LTGSHP": "electric", "AAHP": "electric",
    "Storage Heater": "electric", "Electric Boiler": "electric", "Infrared Heater": "electric",
    "Gas Condensing Boiler": "gas", "Gas Non-Condensing Boiler": "gas"
}

# ==================================================
# SIDEBAR — SCENARIOS
# ==================================================
st.sidebar.header("Scenario A")
st.sidebar.selectbox("Housing archetype", heat_demand_lookup.keys(), key="archetype")
st.sidebar.selectbox("Baseline technology", technologies, key="baseline")
st.sidebar.slider("Smart tariff discount A (%)", 0, 50, key="disc_A")

st.sidebar.divider()
st.sidebar.header("Scenario B")
st.sidebar.checkbox("Enable Scenario B", key="enable_B")
st.sidebar.slider("Smart tariff discount B (%)", 0, 50,
                  disabled=not st.session_state.enable_B, key="disc_B")
st.sidebar.slider("Efficiency multiplier B", 0.8, 1.2, step=0.05,
                  disabled=not st.session_state.enable_B, key="effmult_B")

# ==================================================
# SIDEBAR — GRANTS
# ==================================================
st.sidebar.divider()
st.sidebar.header("Grants")
st.sidebar.checkbox("Apply grant", key="enable_grant",
                    help="Grants reduce upfront capex only and affect payback.")
st.sidebar.selectbox("Grant applies to technology", technologies,
                     disabled=not st.session_state.enable_grant, key="grant_tech")
st.sidebar.number_input("Grant amount (£)", 0.0, 30000.0, step=500.0,
                        disabled=not st.session_state.enable_grant, key="grant_value")

# ==================================================
# SIDEBAR — FUEL PRICES
# ==================================================
st.sidebar.divider()
st.sidebar.header("Fuel Prices")
st.sidebar.slider("Electricity price (p/kWh)", 5.0, 60.0, step=0.5, key="elec_price")
st.sidebar.number_input("Electricity standing charge (£/yr)", 0.0, 500.0, step=1.0, key="elec_sc")
st.sidebar.slider("Gas price (p/kWh)", 2.0, 20.0, step=0.5, key="gas_price")
st.sidebar.number_input("Gas standing charge (£/yr)", 0.0, 500.0, step=1.0, key="gas_sc")

# ==================================================
# SIDEBAR — EDIT TECHNOLOGIES
# ==================================================
st.sidebar.divider()
st.sidebar.header("Edit Technologies")

for tech in technologies:
    with st.sidebar.expander(tech):
        st.number_input("Efficiency / COP", 0.4, 6.0, step=0.05, key=f"eff_{tech}")
        st.number_input("CO₂ factor (kg/kWh)", 0.01, 1.0, step=0.01, key=f"co2_{tech}")
        st.number_input("Installation cost (£)", 1000.0, 50000.0, step=500.0, key=f"capex_{tech}")

for tech in technologies:
    st.session_state["efficiencies"][tech] = st.session_state[f"eff_{tech}"]
    st.session_state["co2_factors"][tech] = st.session_state[f"co2_{tech}"]
    st.session_state["install_costs"][tech] = st.session_state[f"capex_{tech}"]

# ==================================================
# MODEL
# ==================================================
def run_model(discount, eff_mult=1.0):
    hd = heat_demand_lookup[st.session_state.archetype]
    df = pd.DataFrame({"Technology": technologies})

    df["Fuel type"] = df["Technology"].map(fuel_type)
    df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies) * eff_mult
    df["Fuel Demand (kWh)"] = hd / df["Efficiency"]

    df["Unit Cost (p/kWh)"] = df["Fuel type"].map({
        "electric": st.session_state.elec_price * (1 - discount / 100),
        "gas": st.session_state.gas_price
    })

    df["Standing Charge (£/yr)"] = df["Fuel type"].map({
        "electric": st.session_state.elec_sc,
        "gas": st.session_state.gas_sc
    })

    df["Annual Cost (£/yr)"] = (
        df["Fuel Demand (kWh)"] * df["Unit Cost (p/kWh)"] / 100
        + df["Standing Charge (£/yr)"]
    )

    df["CO2 (kg/yr)"] = df["Fuel Demand (kWh)"] * df["Technology"].map(st.session_state.co2_factors)
    df["Capex (£)"] = df["Technology"].map(st.session_state.install_costs)

    if st.session_state.enable_grant:
        mask = df["Technology"] == st.session_state.grant_tech
        df.loc[mask, "Capex (£)"] = (df.loc[mask, "Capex (£)"] - st.session_state.grant_value).clip(lower=0)

    return df

def apply_payback(df):
    base = df[df["Technology"] == st.session_state.baseline].iloc[0]
    out = df.copy()

    out["Annual Savings (£/yr)"] = base["Annual Cost (£/yr)"] - out["Annual Cost (£/yr)"]
    out["Net Capex vs Baseline (£)"] = out["Capex (£)"] - base["Capex (£)"]

    def pb(r):
        if r["Net Capex vs Baseline (£)"] <= 0:
            return "Immediate"
        if r["Annual Savings (£/yr)"] <= 0:
            return "No payback"
        return int(round(r["Net Capex vs Baseline (£)"] / r["Annual Savings (£/yr)"]))

    out["Payback (years)"] = out.apply(pb, axis=1)
    return out

df_A = apply_payback(run_model(st.session_state.disc_A))
df_B = apply_payback(run_model(st.session_state.disc_B, st.session_state.effmult_B)) if st.session_state.enable_B else None

# ==================================================
# TABLE FORMATTING
# ==================================================
def format_table(df):
    return df.style.format({
        "Efficiency": "{:.2f}",
        "Fuel Demand (kWh)": "{:,.2f}",
        "Unit Cost (p/kWh)": "{:.2f}",
        "Standing Charge (£/yr)": "£{:,.2f}",
        "Annual Cost (£/yr)": "£{:,.2f}",
        "Annual Savings (£/yr)": "£{:,.2f}",
        "Net Capex vs Baseline (£)": "£{:,.2f}",
        "CO2 (kg/yr)": "{:,.2f}",
        "Capex (£)": "£{:,.2f}",
    })

# ==================================================
# DISPLAY
# ==================================================
st.subheader("Technology Summary – Scenario A")
st.dataframe(format_table(df_A), use_container_width=True)

if df_B is not None:
    st.subheader("Technology Summary – Scenario B")
    st.dataframe(format_table(df_B), use_container_width=True)

# ==================================================
# CHARTS (unchanged)
# ==================================================
AMBER, GREEN, PURPLE, BLUE = "#f59e0b", "#22c55e", "#8b5cf6", "#3b82f6"

def colours(df, highlight, colour):
    return [AMBER if t == st.session_state.baseline else colour if t == highlight else BLUE for t in df["Technology"]]

cheapest_A = df_A.loc[df_A["Annual Cost (£/yr)"].idxmin(), "Technology"]
lowest_co2_A = df_A.loc[df_A["CO2 (kg/yr)"].idxmin(), "Technology"]

st.subheader("Scenario A – Annual Cost (£/yr)")
fig = px.bar(df_A, x="Technology", y="Annual Cost (£/yr)")
fig.update_traces(marker_color=colours(df_A, cheapest_A, GREEN))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Scenario A – CO₂ Emissions (kg/yr)")
fig = px.bar(df_A, x="Technology", y="CO2 (kg/yr)")
fig.update_traces(marker_color=colours(df_A, lowest_co2_A, PURPLE))
st.plotly_chart(fig, use_container_width=True)
