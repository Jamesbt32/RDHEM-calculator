import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==================================================
# PAGE CONFIG (MUST BE FIRST STREAMLIT CALL)
# ==================================================
st.set_page_config(
    page_title="RDHEM Heating Model",
    page_icon="🔥",
    layout="wide"
)

# ==================================================
# TITLE & INTRO
# ==================================================
st.title("RDHEM Heating Technology Cost, Energy, Carbon & Payback Model")

st.info(
    "Electricity and gas prices are set separately. "
    "Only gas technologies incur a standing charge. "
    "Grants reduce extra capex vs the baseline technology and affect payback."
)

# ==================================================
# FORMULAS
# ==================================================
show_formula = st.checkbox("Show calculation formulas", key="show_formula")

if show_formula:
    st.markdown("""
    **Fuel demand (kWh)**  
    = Heat demand ÷ Efficiency  

    **Electricity unit cost (p/kWh)**  
    = Electricity price × (1 − Smart tariff discount)

    **Gas unit cost (p/kWh)**  
    = Gas price

    **Annual fuel cost (£/yr)**  
    = Fuel demand × Unit cost ÷ 100  

    **Annual total cost (£/yr)**  
    = Annual fuel cost + Standing charge  

    **Annual CO₂ emissions (kg/yr)**  
    = Fuel demand × Technology-specific CO₂ factor  

    **Annual savings (£/yr)**  
    = Baseline annual cost − Technology annual cost

    **Extra capex (£)**  
    = Technology capex − Baseline capex

    **Effective extra capex (£)**  
    = Extra capex − Grant (for selected technology only)

    **Payback period**  
    = Effective extra capex ÷ Annual savings
    """)

# ==================================================
# TECHNOLOGIES & FUELS
# ==================================================
technologies = [
    "LTASHP", "HTASHP", "LTGSHP", "AAHP",
    "Storage Heater", "Electric Boiler", "Infrared Heater",
    "Gas Condensing Boiler", "Gas Non-Condensing Boiler"
]

fuel_type = {
    "LTASHP": "electric",
    "HTASHP": "electric",
    "LTGSHP": "electric",
    "AAHP": "electric",
    "Storage Heater": "electric",
    "Electric Boiler": "electric",
    "Infrared Heater": "electric",
    "Gas Condensing Boiler": "gas",
    "Gas Non-Condensing Boiler": "gas",
}

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

# ==================================================
# DEFAULT PARAMETERS (editable)
# ==================================================
defaults = {
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

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v.copy()

# ==================================================
# SIDEBAR — SCENARIOS
# ==================================================
st.sidebar.header("Scenario A")
archetype = st.sidebar.selectbox("Housing archetype", heat_demand_lookup, key="archetype")
baseline = st.sidebar.selectbox("Baseline technology", technologies, key="baseline")
discount_A = st.sidebar.slider("Smart tariff discount A (%)", 0, 50, 10, key="disc_A")

st.sidebar.divider()
st.sidebar.header("Scenario B")
enable_B = st.sidebar.checkbox("Enable Scenario B", key="enable_B")
discount_B = st.sidebar.slider(
    "Smart tariff discount B (%)",
    0, 50, discount_A,
    disabled=not enable_B,
    key="disc_B"
)
eff_mult_B = st.sidebar.slider(
    "Efficiency multiplier B",
    0.8, 1.2, 1.0, 0.05,
    disabled=not enable_B,
    key="effmult_B"
)

# ==================================================
# SIDEBAR — GRANTS (RESTORED)
# ==================================================
st.sidebar.divider()
st.sidebar.header("Grants / Subsidies")

enable_grant = st.sidebar.checkbox(
    "Apply technology-specific grant",
    key="enable_grant"
)

grant_tech = st.sidebar.selectbox(
    "Grant applies to technology",
    technologies,
    disabled=not enable_grant,
    key="grant_tech"
)

grant_type = st.sidebar.radio(
    "Grant type",
    ["Flat amount (£)", "Percentage of extra capex"],
    disabled=not enable_grant,
    key="grant_type"
)

grant_value = st.sidebar.number_input(
    "Grant value",
    0.0, 30000.0, 7500.0, 500.0,
    disabled=not enable_grant,
    key="grant_value"
)

# ==================================================
# SIDEBAR — FUEL PRICES (ABOVE EDIT TECHNOLOGIES)
# ==================================================
st.sidebar.divider()
st.sidebar.header("Fuel Prices")

elec_price = st.sidebar.slider(
    "Electricity price (p/kWh)", 5.0, 60.0, 30.0, 0.5, key="elec_price"
)
gas_price = st.sidebar.slider(
    "Gas price (p/kWh)", 2.0, 20.0, 10.0, 0.5, key="gas_price"
)
gas_sc = st.sidebar.number_input(
    "Gas standing charge (£/yr)", 0.0, 500.0, 300.0, 1.0, key="gas_sc"
)

# ==================================================
# SIDEBAR — EDIT TECHNOLOGIES
# ==================================================
st.sidebar.divider()
st.sidebar.header("Edit Technologies")

for tech in technologies:
    with st.sidebar.expander(tech):
        st.session_state.efficiencies[tech] = st.number_input(
            "Efficiency / COP",
            0.4, 6.0,
            float(st.session_state.efficiencies[tech]),
            0.05,
            key=f"eff_{tech}"
        )
        st.session_state.co2_factors[tech] = st.number_input(
            "CO₂ factor (kg/kWh)",
            0.01, 1.0,
            float(st.session_state.co2_factors[tech]),
            0.01,
            key=f"co2_{tech}"
        )
        st.session_state.install_costs[tech] = st.number_input(
            "Installation cost (£)",
            1000, 50000,
            int(st.session_state.install_costs[tech]),
            500,
            key=f"capex_{tech}"
        )

# ==================================================
# MODEL
# ==================================================
def run_model(discount: float, eff_mult: float = 1.0) -> pd.DataFrame:
    hd = heat_demand_lookup[archetype]
    df = pd.DataFrame({"Technology": technologies})

    df["Fuel type"] = df["Technology"].map(fuel_type)
    df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies) * eff_mult
    df["Fuel Demand (kWh)"] = hd / df["Efficiency"]

    df["Unit Cost (p/kWh)"] = df["Fuel type"].map({
        "electric": elec_price * (1 - discount / 100),
        "gas": gas_price
    })

    df["Standing Charge (£/yr)"] = df["Fuel type"].map({
        "electric": 0.0,
        "gas": float(gas_sc)
    })

    df["Annual Cost (£/yr)"] = (
        df["Fuel Demand (kWh)"] * df["Unit Cost (p/kWh)"] / 100
        + df["Standing Charge (£/yr)"]
    )

    df["CO2 (kg/yr)"] = df["Fuel Demand (kWh)"] * df["Technology"].map(st.session_state.co2_factors)
    df["Capex (£)"] = df["Technology"].map(st.session_state.install_costs)

    return df

def format_payback_years(years: float) -> str:
    y = int(years)
    m = int(round((years - y) * 12))
    if m == 12:
        y += 1
        m = 0
    return f"{y}y {m}m"

def apply_payback_and_grant(df: pd.DataFrame) -> pd.DataFrame:
    base = df[df["Technology"] == baseline].iloc[0]
    out = df.copy()

    out["Annual Savings (£/yr)"] = base["Annual Cost (£/yr)"] - out["Annual Cost (£/yr)"]
    out["Extra Capex (£)"] = out["Capex (£)"] - base["Capex (£)"]

    # Apply grant only to selected technology and only to positive extra capex
    out["Grant (£)"] = 0.0
    if enable_grant:
        mask = (out["Technology"] == grant_tech) & (out["Extra Capex (£)"] > 0)
        if grant_type == "Flat amount (£)":
            out.loc[mask, "Grant (£)"] = float(grant_value)
        else:
            out.loc[mask, "Grant (£)"] = out.loc[mask, "Extra Capex (£)"] * (float(grant_value) / 100.0)

    out["Effective Extra Capex (£)"] = (out["Extra Capex (£)"] - out["Grant (£)"]).clip(lower=0.0)

    def pb(row):
        extra = row["Extra Capex (£)"]
        eff_extra = row["Effective Extra Capex (£)"]
        saving = row["Annual Savings (£/yr)"]

        if extra <= 0:
            return "Immediate"
        if saving <= 0:
            return "No payback"
        if eff_extra <= 0:
            return "Immediate"

        return format_payback_years(eff_extra / saving)

    out["Payback"] = out.apply(pb, axis=1)
    return out

df_A = apply_payback_and_grant(run_model(discount_A, 1.0))
df_B = apply_payback_and_grant(run_model(discount_B, eff_mult_B)) if enable_B else None

# ==================================================
# TABLE STYLING + FORMATTING
# ==================================================
def highlight_baseline_row(row):
    style = "background-color:#fff3cd; font-weight:bold;" if row["Technology"] == baseline else ""
    return [style] * len(row)

def format_table(styler):
    return styler.format({
        "Efficiency": "{:.2f}",
        "Fuel Demand (kWh)": "{:,.2f}",
        "Unit Cost (p/kWh)": "{:.2f}",
        "Standing Charge (£/yr)": "£{:,.2f}",
        "Annual Cost (£/yr)": "£{:,.2f}",
        "Annual Savings (£/yr)": "£{:,.2f}",
        "CO2 (kg/yr)": "{:,.2f}",
        "Capex (£)": "£{:,.0f}",
        "Extra Capex (£)": "£{:,.0f}",
        "Grant (£)": "£{:,.0f}",
        "Effective Extra Capex (£)": "£{:,.0f}",
    })

# ==================================================
# KEY OPTIONS (per scenario, used for chart colouring)
# ==================================================
AMBER = "#f59e0b"   # baseline
GREEN = "#22c55e"   # cheapest (cost charts)
PURPLE = "#8b5cf6"  # lowest CO2 (co2 charts)
BLUE = "#3b82f6"    # other

cheapest_A = df_A.loc[df_A["Annual Cost (£/yr)"].idxmin(), "Technology"]
lowest_co2_A = df_A.loc[df_A["CO2 (kg/yr)"].idxmin(), "Technology"]

if enable_B and df_B is not None:
    cheapest_B = df_B.loc[df_B["Annual Cost (£/yr)"].idxmin(), "Technology"]
    lowest_co2_B = df_B.loc[df_B["CO2 (kg/yr)"].idxmin(), "Technology"]
else:
    cheapest_B = None
    lowest_co2_B = None

def colours_cost(df: pd.DataFrame, cheapest: str):
    return [AMBER if t == baseline else GREEN if t == cheapest else BLUE for t in df["Technology"]]

def colours_co2(df: pd.DataFrame, lowest: str):
    return [AMBER if t == baseline else PURPLE if t == lowest else BLUE for t in df["Technology"]]

def add_legend_cost(fig: go.Figure):
    fig.add_trace(go.Bar(name="Baseline technology", x=[0], y=[0], marker_color=AMBER, visible="legendonly"))
    fig.add_trace(go.Bar(name="Cheapest option", x=[0], y=[0], marker_color=GREEN, visible="legendonly"))

def add_legend_co2(fig: go.Figure):
    fig.add_trace(go.Bar(name="Baseline technology", x=[0], y=[0], marker_color=AMBER, visible="legendonly"))
    fig.add_trace(go.Bar(name="Lowest-CO₂ option", x=[0], y=[0], marker_color=PURPLE, visible="legendonly"))

# ==================================================
# TECHNOLOGY SUMMARY TABLES (A then B underneath)
# ==================================================
st.subheader("Technology Summary")

st.markdown("### Scenario A")
st.dataframe(
    format_table(df_A.style.apply(highlight_baseline_row, axis=1)),
    use_container_width=True
)

if enable_B and df_B is not None:
    st.markdown("### Scenario B")
    st.dataframe(
        format_table(df_B.style.apply(highlight_baseline_row, axis=1)),
        use_container_width=True
    )
else:
    st.info("Enable Scenario B to view Scenario B summary")

# ==================================================
# CHARTS (explicit labels, B underneath A)
# ==================================================
st.subheader("Scenario A – Annual Cost (£/yr)")
fig_cost_A = px.bar(df_A, x="Technology", y="Annual Cost (£/yr)")
fig_cost_A.update_traces(marker_color=colours_cost(df_A, cheapest_A))
add_legend_cost(fig_cost_A)
st.plotly_chart(fig_cost_A, use_container_width=True, key="cost_A")

if enable_B and df_B is not None:
    st.subheader("Scenario B – Annual Cost (£/yr)")
    fig_cost_B = px.bar(df_B, x="Technology", y="Annual Cost (£/yr)")
    fig_cost_B.update_traces(marker_color=colours_cost(df_B, cheapest_B))
    add_legend_cost(fig_cost_B)
    st.plotly_chart(fig_cost_B, use_container_width=True, key="cost_B")

st.subheader("Scenario A – CO₂ Emissions (kg/yr)")
fig_co2_A = px.bar(df_A, x="Technology", y="CO2 (kg/yr)")
fig_co2_A.update_traces(marker_color=colours_co2(df_A, lowest_co2_A))
add_legend_co2(fig_co2_A)
st.plotly_chart(fig_co2_A, use_container_width=True, key="co2_A")

if enable_B and df_B is not None:
    st.subheader("Scenario B – CO₂ Emissions (kg/yr)")
    fig_co2_B = px.bar(df_B, x="Technology", y="CO2 (kg/yr)")
    fig_co2_B.update_traces(marker_color=colours_co2(df_B, lowest_co2_B))
    add_legend_co2(fig_co2_B)
    st.plotly_chart(fig_co2_B, use_container_width=True, key="co2_B")

st.caption(
    "Amber = baseline · Green = cheapest (cost charts) · Purple = lowest-CO₂ (CO₂ charts). "
    "Grant is applied only to the selected technology and only reduces positive extra capex vs baseline."
)
