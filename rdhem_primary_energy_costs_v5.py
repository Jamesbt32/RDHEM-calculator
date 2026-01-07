import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="RDHEM Heating Model",
    page_icon="🔥",
    layout="wide"
)

# ==================================================
# TITLE
# ==================================================

st.title("RDHEM Heating Technology Cost, Energy, Carbon & Payback Model")

st.info(
    "Electricity and gas prices are set separately. "
    "Only gas technologies incur a standing charge. "
    "Standing charge is stacked on top of fuel cost in charts."
)

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
    "Gas Non-Condensing Boiler": "gas"
}

heat_demand_lookup = {
    "Smaller Mid-Terrace On-Gas": 6400,
    "Larger Detached On-Gas": 17600,
    "Larger Detached Off-Gas": 21800
}

# ==================================================
# DEFAULT PARAMETERS
# ==================================================

defaults = {
    "efficiencies": {
        "LTASHP": 2.86, "HTASHP": 2.73, "LTGSHP": 3.53, "AAHP": 2.04,
        "Storage Heater": 1.00, "Electric Boiler": 1.00, "Infrared Heater": 1.00,
        "Gas Condensing Boiler": 0.895, "Gas Non-Condensing Boiler": 0.60
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
archetype = st.sidebar.selectbox("Housing archetype", heat_demand_lookup, key="arch")
baseline = st.sidebar.selectbox("Baseline technology", technologies, key="baseline")
discount_A = st.sidebar.slider("Smart tariff discount A (%)", 0, 50, 10, key="discA")

st.sidebar.divider()
st.sidebar.header("Scenario B")

enable_B = st.sidebar.checkbox("Enable Scenario B", key="enableB")
discount_B = st.sidebar.slider(
    "Smart tariff discount B (%)", 0, 50, discount_A,
    disabled=not enable_B, key="discB"
)
eff_mult_B = st.sidebar.slider(
    "Efficiency multiplier B", 0.8, 1.2, 1.0, 0.05,
    disabled=not enable_B, key="effB"
)

st.sidebar.divider()
lock_y = st.sidebar.checkbox("Lock Y-axis across charts", True, key="lockY")

# ==================================================
# SIDEBAR — GRANTS
# ==================================================

st.sidebar.divider()
st.sidebar.header("Grants")

enable_grant = st.sidebar.checkbox("Apply grant", key="enable_grant")

grant_tech = st.sidebar.selectbox(
    "Grant technology",
    technologies,
    disabled=not enable_grant,
    key="grant_tech"
)

grant_type = st.sidebar.radio(
    "Grant type",
    ["Flat amount (£)", "Percentage of capex"],
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
# SIDEBAR — FUEL PRICES
# ==================================================

st.sidebar.divider()
st.sidebar.header("Fuel Prices")

elec_price = st.sidebar.slider("Electricity price (p/kWh)", 5.0, 60.0, 30.0, 0.5, key="ep")
gas_price = st.sidebar.slider("Gas price (p/kWh)", 2.0, 20.0, 10.0, 0.5, key="gp")
gas_sc = st.sidebar.slider("Gas standing charge (£/yr)", 0, 400, 300, 10, key="gsc")

# ==================================================
# SIDEBAR — EDIT TECHNOLOGIES
# ==================================================

st.sidebar.divider()
st.sidebar.header("Edit Technologies")

for tech in technologies:
    with st.sidebar.expander(tech):
        st.session_state.efficiencies[tech] = st.number_input(
            "Efficiency / COP", 0.4, 6.0,
            float(st.session_state.efficiencies[tech]), 0.05,
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

def run_model(discount, eff_mult=1.0):
    hd = heat_demand_lookup[archetype]
    df = pd.DataFrame({"Technology": technologies})

    df["Fuel type"] = df["Technology"].map(fuel_type)
    df["Efficiency"] = df["Technology"].map(st.session_state.efficiencies) * eff_mult
    df["Fuel Demand (kWh)"] = hd / df["Efficiency"]

    elec_unit = (elec_price / 100) * (1 - discount / 100)
    gas_unit = gas_price / 100

    df["Unit Cost (£/kWh)"] = df["Fuel type"].map({
        "electric": elec_unit,
        "gas": gas_unit
    })

    df["Fuel Cost (£/yr)"] = df["Fuel Demand (kWh)"] * df["Unit Cost (£/kWh)"]
    df["Standing Charge (£/yr)"] = df["Fuel type"].map({"electric": 0.0, "gas": gas_sc})
    df["Annual Cost (£/yr)"] = df["Fuel Cost (£/yr)"] + df["Standing Charge (£/yr)"]

    df["CO2 (kg/yr)"] = (
        df["Fuel Demand (kWh)"]
        * df["Technology"].map(st.session_state.co2_factors)
    )

    df["Capex (£)"] = df["Technology"].map(st.session_state.install_costs).astype(float)
    df["Effective Capex (£)"] = df["Capex (£)"]

    if enable_grant:
        mask = df["Technology"] == grant_tech
        if grant_type == "Flat amount (£)":
            df.loc[mask, "Effective Capex (£)"] -= grant_value
        else:
            df.loc[mask, "Effective Capex (£)"] *= (1 - grant_value / 100)
        df["Effective Capex (£)"] = df["Effective Capex (£)"].clip(lower=0)

    return df.round(2)

df_A = run_model(discount_A)
df_B = run_model(discount_B, eff_mult_B) if enable_B else None

# ==================================================
# PAYBACK
# ==================================================

def apply_payback(df):
    base = df[df["Technology"] == baseline].iloc[0]

    def pb(r):
        saving = base["Annual Cost (£/yr)"] - r["Annual Cost (£/yr)"]
        extra = r["Effective Capex (£)"] - base["Effective Capex (£)"]
        if extra <= 0:
            return "Immediate"
        if saving <= 0:
            return "No payback"
        yrs = extra / saving
        return f"{int(yrs)}y {int((yrs % 1) * 12)}m"

    df["Payback"] = df.apply(pb, axis=1)
    return df

df_A = apply_payback(df_A)
if enable_B:
    df_B = apply_payback(df_B)

# ==================================================
# TABLES
# ==================================================

def format_table(styler):
    return styler.format({
        "Efficiency": "{:.2f}",
        "Fuel Demand (kWh)": "{:,.2f}",
        "Unit Cost (£/kWh)": "£{:,.2f}",
        "Fuel Cost (£/yr)": "£{:,.2f}",
        "Standing Charge (£/yr)": "£{:,.2f}",
        "Annual Cost (£/yr)": "£{:,.2f}",
        "CO2 (kg/yr)": "{:,.2f}",
        "Capex (£)": "£{:,.2f}",
        "Effective Capex (£)": "£{:,.2f}",
    })

st.subheader("Technology Summary — Scenario A")
st.dataframe(format_table(df_A.style), use_container_width=True)

if enable_B:
    st.subheader("Technology Summary — Scenario B")
    st.dataframe(format_table(df_B.style), use_container_width=True)

# ==================================================
# CHART HELPERS
# ==================================================

category_order = technologies
component_order = ["Fuel Cost (£/yr)", "Standing Charge (£/yr)"]

def stacked_cost_chart(df, title):
    df_stack = df[["Technology"] + component_order].melt(
        id_vars="Technology",
        value_vars=component_order,
        var_name="Component",
        value_name="£/yr"
    )

    df_stack["Component"] = pd.Categorical(
        df_stack["Component"],
        categories=component_order,
        ordered=True
    )

    fig = px.bar(
        df_stack,
        x="Technology",
        y="£/yr",
        color="Component",
        title=title
    )

    fig.update_layout(
        xaxis=dict(type="category", categoryorder="array", categoryarray=category_order),
        bargap=0.2,
        bargroupgap=0.0,
        legend_title_text="",
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right")
    )

    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{legendgroup}: £%{y:.2f}/yr<extra></extra>"
    )

    return fig

# ==================================================
# CHARTS
# ==================================================

st.subheader("Annual Cost Breakdown — Scenario A")
st.plotly_chart(
    stacked_cost_chart(df_A, "Fuel Cost with Standing Charge on Top"),
    use_container_width=True,
    key="costA"
)

if enable_B:
    st.subheader("Annual Cost Breakdown — Scenario B")
    st.plotly_chart(
        stacked_cost_chart(df_B, "Fuel Cost with Standing Charge on Top"),
        use_container_width=True,
        key="costB"
)

st.caption("Standing charge is stacked above fuel cost. All values shown to 2 decimal places.")
