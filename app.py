import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Flex Head Industries ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# TABLE CONFIGURATION
# ============================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock Control": "Stock_Control"
}

ITEM_COLUMNS = [
    "Item_ID",
    "Item_Code",
    "Material_Grade",
    "Application",
    "Nominal_Diameter_mm",
    "Wall_Thickness_mm",
    "SDR",
    "Color",
    "Standard_Length",
    "Unit"
]

PRODUCTION_COLUMNS = [
    "Production_ID",
    "Item_ID",
    "Production_Date",
    "Batch_No",
    "Production_Line",
    "Planned_Qty_m",
    "Good_Qty_m",
    "Rejected_Qty_m",
    "Production_Status"
]

STOCK_COLUMNS = [
    "Stock_ID",
    "Item_ID",
    "Production_ID",
    "Batch_No",
    "Stock_Date",
    "Opening_Stock_m",
    "Produced_Qty_m",
    "Dispatched_Qty_m",
    "Closing_Stock_m",
    "Stock_Status"
]


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #f5f7fa;
    }

    [data-testid="stSidebar"] {
        background: #101820;
        border-right: 1px solid #25313b;
    }

    [data-testid="stSidebar"] * {
        color: #e9eef2 !important;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 4px 24px 4px;
    }

    .brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 11px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #1f8a70, #35b58d);
        color: white;
        font-weight: 800;
        letter-spacing: -1px;
        box-shadow: 0 8px 20px rgba(0,0,0,.22);
    }

    .brand-name {
        font-weight: 800;
        font-size: 15px;
        letter-spacing: .4px;
    }

    .brand-sub {
        font-size: 9px;
        letter-spacing: 1.6px;
        color: #93a2ad !important;
        margin-top: 2px;
    }

    .page-kicker {
        color: #21866e;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.8px;
        margin-bottom: -8px;
    }

    h1 {
        font-weight: 800 !important;
        letter-spacing: -1px;
        color: #16212a;
    }

    h2, h3 {
        color: #1c2933;
        font-weight: 700;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e6ebef;
        border-radius: 15px;
        padding: 18px;
        min-height: 142px;
        box-shadow: 0 5px 18px rgba(16,24,32,.04);
        position: relative;
        overflow: hidden;
    }

    .metric-card:after {
        content: "";
        position: absolute;
        left: 0;
        bottom: 0;
        width: 42px;
        height: 3px;
        background: #2b9b7c;
        border-radius: 0 5px 0 0;
    }

    .metric-icon {
        float: right;
        color: #2b9b7c;
        font-size: 21px;
        font-weight: 700;
    }

    .metric-label {
        font-size: 12px;
        color: #72808b;
        font-weight: 600;
        margin-bottom: 8px;
    }

    .metric-value {
        font-size: 27px;
        color: #17232c;
        font-weight: 800;
        letter-spacing: -1px;
    }

    .metric-caption {
        font-size: 11px;
        color: #8a969f;
        margin-top: 8px;
    }

    .status-box {
        padding: 12px 15px;
        border-radius: 10px;
        background: #ffffff;
        border: 1px solid #e3e9ed;
        margin-bottom: 10px;
    }

    .section-gap {
        height: 12px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #e2e8ec;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #e1e7eb;
        border-radius: 12px;
        overflow: hidden;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 9px;
        font-weight: 700;
        border: 1px solid #d8e0e5;
    }

    button[kind="primary"] {
        background: #21866e !important;
        border-color: #21866e !important;
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    [data-baseweb="select"] > div {
        border-radius: 8px !important;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #e1e7eb;
        border-radius: 12px;
        background: #fff;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5eaee;
        padding: 12px;
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase():

    if create_client is None:
        st.error(
            "Supabase package is not installed. "
            "Add supabase to requirements.txt."
        )
        return None

    url = None
    key = None

    # Streamlit Secrets
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

    # Environment variables fallback
    if not url:
        url = os.getenv("SUPABASE_URL")

    if not key:
        key = os.getenv("SUPABASE_KEY")

    if not url:
        st.error("SUPABASE_URL is missing.")

    if not key:
        st.error("SUPABASE_KEY is missing.")

    if not url or not key:
        return None

    try:
        client = create_client(url, key)

        return client

    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None


supabase = get_supabase()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    logo_path = "logo.png"

    if os.path.exists(logo_path):

        st.markdown(
            """
            <div class="brand">
                <img src="data:image/png;base64,PLACEHOLDER"
                     class="company-logo">
                <div>
                    <div class="brand-name">FLEX HEAD</div>
                    <div class="brand-sub">INDUSTRIES ERP</div>
                </div>
            </div>
            """.replace(
                "PLACEHOLDER",
                __import__("base64")
                .b64encode(open(logo_path, "rb").read())
                .decode()
            ),
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="brand">
                <div class="brand-mark">FH</div>
                <div>
                    <div class="brand-name">FLEX HEAD</div>
                    <div class="brand-sub">INDUSTRIES ERP</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    st.caption("MAIN MENU")

    page = st.radio(
        "Navigation",
        [
            "Executive Dashboard",
            "Item Registration",
            "Production",
            "Stock Control",
            "Custom Analytics",
            "Data Management"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    if supabase is not None:
        st.success("Supabase Connected")
    else:
        st.error("Supabase Not Connected")

    st.caption("Flex Head Industries Pvt Ltd")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def empty_dataframe(columns):

    return pd.DataFrame(columns=columns)


def fetch_table(module):

    if supabase is None:

        return empty_dataframe(
            ITEM_COLUMNS
            if module == "Items"
            else PRODUCTION_COLUMNS
            if module == "Production"
            else STOCK_COLUMNS
        )

    table_name = TABLES[module]

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        data = response.data

        if data is None:

            return empty_dataframe(
                ITEM_COLUMNS
                if module == "Items"
                else PRODUCTION_COLUMNS
                if module == "Production"
                else STOCK_COLUMNS
            )

        df = pd.DataFrame(data)

        return df

    except Exception as e:

        st.error(
            f"""
            ### Supabase Error

            **Module:** {module}

            **Table:** `{table_name}`

            **Error:** `{e}`
            """
        )

        return empty_dataframe(
            ITEM_COLUMNS
            if module == "Items"
            else PRODUCTION_COLUMNS
            if module == "Production"
            else STOCK_COLUMNS
        )


def insert_record(module, data):

    if supabase is None:

        return False, "Supabase connection is not available."

    try:

        table_name = TABLES[module]

        response = (
            supabase
            .table(table_name)
            .insert(data)
            .execute()
        )

        return True, "Record added successfully."

    except Exception as e:

        return False, str(e)


def update_record(module, record_id, id_column, data):

    if supabase is None:

        return False, "Supabase connection is not available."

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .update(data)
            .eq(id_column, record_id)
            .execute()
        )

        return True, "Record updated successfully."

    except Exception as e:

        return False, str(e)


def delete_record(module, record_id, id_column):

    if supabase is None:

        return False, "Supabase connection is not available."

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .delete()
            .eq(id_column, record_id)
            .execute()
        )

        return True, "Record deleted successfully."

    except Exception as e:

        return False, str(e)


def clean_numeric(df, columns):

    for col in columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def ensure_columns(df, columns):

    for col in columns:

        if col not in df.columns:

            df[col] = None

    return df


def format_number(value):

    try:

        return f"{float(value):,.0f}"

    except Exception:

        return "0"


# ============================================================
# LOAD DATA
# ============================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


# ============================================================
# CLEAN DATA
# ============================================================

items = ensure_columns(items, ITEM_COLUMNS)

production = ensure_columns(
    production,
    PRODUCTION_COLUMNS
)

stock = ensure_columns(
    stock,
    STOCK_COLUMNS
)


# IMPORTANT:
# Item_ID remains TEXT
items["Item_ID"] = (
    items["Item_ID"]
    .fillna("")
    .astype(str)
    .str.strip()
)

production["Item_ID"] = (
    production["Item_ID"]
    .fillna("")
    .astype(str)
    .str.strip()
)

stock["Item_ID"] = (
    stock["Item_ID"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# Numeric fields only

items = clean_numeric(
    items,
    [
        "Nominal_Diameter_mm",
        "Wall_Thickness_mm",
        "Standard_Length"
    ]
)

production = clean_numeric(
    production,
    [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]
)

stock = clean_numeric(
    stock,
    [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]
)


# Dates

if "Production_Date" in production.columns:

    production["Production_Date"] = pd.to_datetime(
        production["Production_Date"],
        errors="coerce"
    )

if "Stock_Date" in stock.columns:

    stock["Stock_Date"] = pd.to_datetime(
        stock["Stock_Date"],
        errors="coerce"
    )


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

def dashboard():

    st.markdown(
        '<div class="page-kicker">EXECUTIVE OVERVIEW</div>',
        unsafe_allow_html=True
    )

    st.title("ERP Dashboard")

    st.caption(
        "Flex Head Industries Pvt Ltd — "
        "Manufacturing & Inventory Overview"
    )

    st.markdown("")


    # --------------------------------------------------------
    # KPI CALCULATIONS
    # --------------------------------------------------------

    total_items = len(items)

    planned_qty = production["Planned_Qty_m"].sum()

    good_qty = production["Good_Qty_m"].sum()

    rejected_qty = production["Rejected_Qty_m"].sum()

    dispatched_qty = stock["Dispatched_Qty_m"].sum()

    current_stock = stock["Closing_Stock_m"].sum()


    total_produced = (
        good_qty +
        rejected_qty
    )

    if total_produced > 0:

        production_yield = (
            good_qty /
            total_produced
        ) * 100

    else:

        production_yield = 0


    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">▦</div>

                <div class="metric-label">
                    REGISTERED ITEMS
                </div>

                <div class="metric-value">
                    {total_items}
                </div>

                <div class="metric-caption">
                    Active product specifications
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c2:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">⚙</div>

                <div class="metric-label">
                    GOOD PRODUCTION
                </div>

                <div class="metric-value">
                    {format_number(good_qty)} m
                </div>

                <div class="metric-caption">
                    Accepted production quantity
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c3:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">▤</div>

                <div class="metric-label">
                    CURRENT STOCK
                </div>

                <div class="metric-value">
                    {format_number(current_stock)} m
                </div>

                <div class="metric-caption">
                    Available closing inventory
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c4:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">✓</div>

                <div class="metric-label">
                    PRODUCTION YIELD
                </div>

                <div class="metric-value">
                    {production_yield:.1f}%
                </div>

                <div class="metric-caption">
                    Good production / total output
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)


    # --------------------------------------------------------
    # PRODUCTION TREND
    # --------------------------------------------------------

    col1, col2 = st.columns(2)


    with col1:

        st.subheader("Production Trend")

        trend = production.copy()

        if not trend.empty:

            trend = trend.dropna(
                subset=["Production_Date"]
            )

        if not trend.empty:

            trend = (
                trend
                .groupby("Production_Date", as_index=False)
                [["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"]]
                .sum()
            )

            trend = trend.sort_values(
                "Production_Date"
            )

            fig = px.line(
                trend,
                x="Production_Date",
                y=[
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                markers=True,
                title=""
            )

            fig.update_layout(
                height=360,
                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10
                ),
                legend_title_text=""
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info(
                "No production data available."
            )


    # --------------------------------------------------------
    # PRODUCTION STATUS
    # --------------------------------------------------------

    with col2:

        st.subheader("Production Status")

        if not production.empty:

            status = (
                production
                .groupby(
                    "Production_Status",
                    dropna=False
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            status[
                "Production_Status"
            ] = status[
                "Production_Status"
            ].fillna("Unknown")

            fig = px.pie(
                status,
                names="Production_Status",
                values="Records",
                hole=0.55
            )

            fig.update_layout(
                height=360,
                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info(
                "No production data available."
            )


    # --------------------------------------------------------
    # STOCK BY ITEM
    # --------------------------------------------------------

    st.subheader("Stock by Item")

    if not stock.empty:

        stock_chart = stock.copy()

        stock_chart["Closing_Stock_m"] = pd.to_numeric(
            stock_chart["Closing_Stock_m"],
            errors="coerce"
        ).fillna(0)

        if not items.empty:

            item_lookup = items[
                ["Item_ID", "Item_Code"]
            ].copy()

            item_lookup["Item_ID"] = (
                item_lookup["Item_ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            stock_chart = stock_chart.merge(
                item_lookup,
                on="Item_ID",
                how="left"
            )

        if "Item_Code" not in stock_chart.columns:

            stock_chart["Item_Code"] = (
                stock_chart["Item_ID"]
            )

        stock_chart["Item_Code"] = (
            stock_chart["Item_Code"]
            .fillna(stock_chart["Item_ID"])
        )

        stock_summary = (
            stock_chart
            .groupby(
                "Item_Code",
                as_index=False
            )["Closing_Stock_m"]
            .sum()
        )

        fig = px.bar(
            stock_summary,
            x="Item_Code",
            y="Closing_Stock_m",
            text_auto=".0f"
        )

        fig.update_layout(
            height=380,
            xaxis_title="Item",
            yaxis_title="Closing Stock (m)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "No stock data available."
        )


    # --------------------------------------------------------
    # PRODUCTION QUALITY
    # --------------------------------------------------------

    st.subheader("Production Quality")

    if not production.empty:

        quality = production.copy()

        quality["Total"] = (
            quality["Good_Qty_m"] +
            quality["Rejected_Qty_m"]
        )

        quality["Yield_%"] = 0.0

        valid = quality["Total"] > 0

        quality.loc[
            valid,
            "Yield_%"
        ] = (
            quality.loc[
                valid,
                "Good_Qty_m"
            ]
            /
            quality.loc[
                valid,
                "Total"
            ]
            * 100
        )

        quality = quality[
            [
                "Production_ID",
                "Good_Qty_m",
                "Rejected_Qty_m",
                "Yield_%"
            ]
        ]

        st.dataframe(
            quality,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No production quality records available."
        )


    # --------------------------------------------------------
    # OPERATIONAL SUMMARY
    # --------------------------------------------------------

    st.subheader("Operational Summary")

    a, b, c, d = st.columns(4)

    with a:

        st.metric(
            "Planned Production",
            f"{planned_qty:,.0f} m"
        )

    with b:

        st.metric(
            "Good Production",
            f"{good_qty:,.0f} m"
        )

    with c:

        st.metric(
            "Dispatched",
            f"{dispatched_qty:,.0f} m"
        )

    with d:

        st.metric(
            "Rejected",
            f"{rejected_qty:,.0f} m"
        )


    # --------------------------------------------------------
    # RECENT PRODUCTION
    # --------------------------------------------------------

    st.subheader("Recent Production")

    if not production.empty:

        recent = production.copy()

        if "Production_Date" in recent.columns:

            recent = recent.sort_values(
                "Production_Date",
                ascending=False
            )

        st.dataframe(
            recent.head(10),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No production records available."
        )


# ============================================================
# ITEM REGISTRATION
# ============================================================

def item_registration():

    st.markdown(
        '<div class="page-kicker">MASTER DATA</div>',
        unsafe_allow_html=True
    )

    st.title("Item Registration")

    st.caption(
        "Manage pipe products, dimensions, materials and specifications."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "View Items",
            "Add Item",
            "Update / Delete"
        ]
    )


    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        if not items.empty:

            st.dataframe(
                items,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Items CSV",
                data=items.to_csv(index=False),
                file_name="Item_Registration.csv",
                mime="text/csv"
            )

        else:

            st.info(
                "No item records found."
            )


    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        with st.form(
            "add_item_form",
            clear_on_submit=True
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                item_id = st.text_input(
                    "Item ID",
                    placeholder="ITM-008"
                )

                item_code = st.text_input(
                    "Item Code",
                    placeholder="PE100-WTR-200-SDR11"
                )

                material = st.text_input(
                    "Material Grade",
                    placeholder="PE-100"
                )

            with c2:

                application = st.selectbox(
                    "Application",
                    [
                        "Water",
                        "Sewerage",
                        "Gas",
                        "Industrial"
                    ]
                )

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0
                )

                thickness = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1
                )

            with c3:

                sdr = st.text_input(
                    "SDR",
                    placeholder="SDR 11"
                )

                color = st.text_input(
                    "Color",
                    placeholder="Blue"
                )

                standard_length = st.number_input(
                    "Standard Length",
                    min_value=0.0,
                    step=1.0
                )

                unit = st.text_input(
                    "Unit",
                    value="m"
                )


            submitted = st.form_submit_button(
                "Add Item",
                type="primary"
            )


            if submitted:

                if not item_id.strip():

                    st.error(
                        "Item ID is required."
                    )

                else:

                    data = {
                        "Item_ID": item_id.strip(),
                        "Item_Code": item_code.strip(),
                        "Material_Grade": material.strip(),
                        "Application": application,
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": thickness,
                        "SDR": sdr.strip(),
                        "Color": color.strip(),
                        "Standard_Length": standard_length,
                        "Unit": unit.strip()
                    }

                    success, message = insert_record(
                        "Items",
                        data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


    # --------------------------------------------------------
    # UPDATE / DELETE
    # --------------------------------------------------------

    with tab3:

        if items.empty:

            st.info(
                "No item records available."
            )

        else:

            item_ids = items[
                "Item_ID"
            ].dropna().astype(str).tolist()

            selected_id = st.selectbox(
                "Select Item",
                item_ids
            )

            selected = items[
                items["Item_ID"] == selected_id
            ].iloc[0]

            with st.form(
                "update_item_form"
            ):

                c1, c2, c3 = st.columns(3)

                with c1:

                    new_code = st.text_input(
                        "Item Code",
                        value=str(
                            selected["Item_Code"]
                        )
                    )

                    new_material = st.text_input(
                        "Material Grade",
                        value=str(
                            selected["Material_Grade"]
                        )
                    )

                    new_application = st.text_input(
                        "Application",
                        value=str(
                            selected["Application"]
                        )
                    )

                with c2:

                    new_diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        value=float(
                            selected[
                                "Nominal_Diameter_mm"
                            ]
                        )
                    )

                    new_thickness = st.number_input(
                        "Wall Thickness (mm)",
                        value=float(
                            selected[
                                "Wall_Thickness_mm"
                            ]
                        )
                    )

                    new_sdr = st.text_input(
                        "SDR",
                        value=str(
                            selected["SDR"]
                        )
                    )

                with c3:

                    new_color = st.text_input(
                        "Color",
                        value=str(
                            selected["Color"]
                        )
                    )

                    new_length = st.number_input(
                        "Standard Length",
                        value=float(
                            selected[
                                "Standard_Length"
                            ]
                        )
                    )

                    new_unit = st.text_input(
                        "Unit",
                        value=str(
                            selected["Unit"]
                        )
                    )


                update_button = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


                if update_button:

                    update_data = {
                        "Item_Code": new_code,
                        "Material_Grade": new_material,
                        "Application": new_application,
                        "Nominal_Diameter_mm": new_diameter,
                        "Wall_Thickness_mm": new_thickness,
                        "SDR": new_sdr,
                        "Color": new_color,
                        "Standard_Length": new_length,
                        "Unit": new_unit
                    }

                    success, message = update_record(
                        "Items",
                        selected_id,
                        "Item_ID",
                        update_data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


            st.markdown("---")

            if st.button(
                "Delete Selected Item",
                type="secondary"
            ):

                success, message = delete_record(
                    "Items",
                    selected_id,
                    "Item_ID"
                )

                if success:

                    st.success(message)

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(message)


# ============================================================
# PRODUCTION
# ============================================================

def production_page():

    st.markdown(
        '<div class="page-kicker">MANUFACTURING</div>',
        unsafe_allow_html=True
    )

    st.title("Production")

    st.caption(
        "Manage production batches, quantities, lines and quality status."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Production Records",
            "Add Production",
            "Update / Delete"
        ]
    )


    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        if not production.empty:

            st.dataframe(
                production,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Production CSV",
                data=production.to_csv(index=False),
                file_name="Production.csv",
                mime="text/csv"
            )

        else:

            st.info(
                "No production records found."
            )


    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        item_options = (
            items["Item_ID"]
            .dropna()
            .astype(str)
            .tolist()
        )

        with st.form(
            "add_production_form",
            clear_on_submit=True
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                production_id = st.text_input(
                    "Production ID",
                    placeholder="PRD-001"
                )

                if item_options:

                    production_item = st.selectbox(
                        "Item",
                        item_options
                    )

                else:

                    production_item = st.text_input(
                        "Item ID"
                    )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

            with c2:

                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001"
                )

                production_line = st.text_input(
                    "Production Line",
                    placeholder="Line 01"
                )

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c3:

                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                rejected_qty = st.number_input(
                    "Rejected Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                production_status = st.selectbox(
                    "Production Status",
                    [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Rejected"
                    ]
                )


            submitted = st.form_submit_button(
                "Add Production",
                type="primary"
            )


            if submitted:

                if not production_id.strip():

                    st.error(
                        "Production ID is required."
                    )

                else:

                    data = {
                        "Production_ID": production_id.strip(),
                        "Item_ID": production_item,
                        "Production_Date": str(
                            production_date
                        ),
                        "Batch_No": batch_no.strip(),
                        "Production_Line": production_line.strip(),
                        "Planned_Qty_m": planned_qty,
                        "Good_Qty_m": good_qty,
                        "Rejected_Qty_m": rejected_qty,
                        "Production_Status": production_status
                    }

                    success, message = insert_record(
                        "Production",
                        data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


    # --------------------------------------------------------
    # UPDATE / DELETE
    # --------------------------------------------------------

    with tab3:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            production_ids = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Production Record",
                production_ids
            )

            selected = production[
                production["Production_ID"]
                == selected_id
            ].iloc[0]

            with st.form(
                "update_production_form"
            ):

                c1, c2, c3 = st.columns(3)

                with c1:

                    new_item = st.text_input(
                        "Item ID",
                        value=str(
                            selected["Item_ID"]
                        )
                    )

                    selected_date = pd.to_datetime(
                        selected["Production_Date"],
                        errors="coerce"
                    )

                    if pd.isna(selected_date):

                        selected_date = pd.Timestamp.today()

                    new_date = st.date_input(
                        "Production Date",
                        value=selected_date.date()
                    )

                    new_batch = st.text_input(
                        "Batch No",
                        value=str(
                            selected["Batch_No"]
                        )
                    )

                with c2:

                    new_line = st.text_input(
                        "Production Line",
                        value=str(
                            selected[
                                "Production_Line"
                            ]
                        )
                    )

                    new_planned = st.number_input(
                        "Planned Quantity",
                        value=float(
                            selected[
                                "Planned_Qty_m"
                            ]
                        )
                    )

                    new_good = st.number_input(
                        "Good Quantity",
                        value=float(
                            selected[
                                "Good_Qty_m"
                            ]
                        )
                    )

                with c3:

                    new_rejected = st.number_input(
                        "Rejected Quantity",
                        value=float(
                            selected[
                                "Rejected_Qty_m"
                            ]
                        )
                    )

                    current_status = str(
                        selected[
                            "Production_Status"
                        ]
                    )

                    status_options = [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Rejected"
                    ]

                    if current_status not in status_options:

                        status_options.append(
                            current_status
                        )

                    new_status = st.selectbox(
                        "Production Status",
                        status_options,
                        index=status_options.index(
                            current_status
                        )
                    )


                update_button = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


                if update_button:

                    data = {
                        "Item_ID": new_item,
                        "Production_Date": str(
                            new_date
                        ),
                        "Batch_No": new_batch,
                        "Production_Line": new_line,
                        "Planned_Qty_m": new_planned,
                        "Good_Qty_m": new_good,
                        "Rejected_Qty_m": new_rejected,
                        "Production_Status": new_status
                    }

                    success, message = update_record(
                        "Production",
                        selected_id,
                        "Production_ID",
                        data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


            st.markdown("---")

            if st.button(
                "Delete Selected Production"
            ):

                success, message = delete_record(
                    "Production",
                    selected_id,
                    "Production_ID"
                )

                if success:

                    st.success(message)

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(message)


# ============================================================
# STOCK CONTROL
# ============================================================

def stock_control():

    st.markdown(
        '<div class="page-kicker">INVENTORY</div>',
        unsafe_allow_html=True
    )

    st.title("Stock Control")

    st.caption(
        "Manage opening stock, production, dispatches and closing stock."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Stock Records",
            "Add Stock",
            "Update / Delete"
        ]
    )


    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        if not stock.empty:

            st.dataframe(
                stock,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "Download Stock CSV",
                data=stock.to_csv(index=False),
                file_name="Stock_Control.csv",
                mime="text/csv"
            )

        else:

            st.info(
                "No stock records found."
            )


    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        item_options = (
            items["Item_ID"]
            .dropna()
            .astype(str)
            .tolist()
        )

        with st.form(
            "add_stock_form",
            clear_on_submit=True
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                stock_id = st.text_input(
                    "Stock ID",
                    placeholder="STK-001"
                )

                if item_options:

                    stock_item = st.selectbox(
                        "Item",
                        item_options
                    )

                else:

                    stock_item = st.text_input(
                        "Item ID"
                    )

                production_id = st.text_input(
                    "Production ID",
                    placeholder="PRD-001"
                )

            with c2:

                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001"
                )

                stock_date = st.date_input(
                    "Stock Date",
                    value=date.today()
                )

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c3:

                produced_qty = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                dispatched_qty = st.number_input(
                    "Dispatched Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                closing_stock = st.number_input(
                    "Closing Stock (m)",
                    min_value=0.0,
                    step=1.0
                )

                stock_status = st.selectbox(
                    "Stock Status",
                    [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]
                )


            submitted = st.form_submit_button(
                "Add Stock",
                type="primary"
            )


            if submitted:

                if not stock_id.strip():

                    st.error(
                        "Stock ID is required."
                    )

                else:

                    data = {
                        "Stock_ID": stock_id.strip(),
                        "Item_ID": stock_item,
                        "Production_ID": production_id.strip(),
                        "Batch_No": batch_no.strip(),
                        "Stock_Date": str(
                            stock_date
                        ),
                        "Opening_Stock_m": opening_stock,
                        "Produced_Qty_m": produced_qty,
                        "Dispatched_Qty_m": dispatched_qty,
                        "Closing_Stock_m": closing_stock,
                        "Stock_Status": stock_status
                    }

                    success, message = insert_record(
                        "Stock Control",
                        data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


    # --------------------------------------------------------
    # UPDATE / DELETE
    # --------------------------------------------------------

    with tab3:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            stock_ids = (
                stock["Stock_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Stock Record",
                stock_ids
            )

            selected = stock[
                stock["Stock_ID"] == selected_id
            ].iloc[0]

            with st.form(
                "update_stock_form"
            ):

                c1, c2, c3 = st.columns(3)

                with c1:

                    new_item = st.text_input(
                        "Item ID",
                        value=str(
                            selected["Item_ID"]
                        )
                    )

                    new_production = st.text_input(
                        "Production ID",
                        value=str(
                            selected[
                                "Production_ID"
                            ]
                        )
                    )

                    new_batch = st.text_input(
                        "Batch No",
                        value=str(
                            selected["Batch_No"]
                        )
                    )

                with c2:

                    selected_date = pd.to_datetime(
                        selected["Stock_Date"],
                        errors="coerce"
                    )

                    if pd.isna(selected_date):

                        selected_date = pd.Timestamp.today()

                    new_date = st.date_input(
                        "Stock Date",
                        value=selected_date.date()
                    )

                    new_opening = st.number_input(
                        "Opening Stock",
                        value=float(
                            selected[
                                "Opening_Stock_m"
                            ]
                        )
                    )

                    new_produced = st.number_input(
                        "Produced Quantity",
                        value=float(
                            selected[
                                "Produced_Qty_m"
                            ]
                        )
                    )

                with c3:

                    new_dispatched = st.number_input(
                        "Dispatched Quantity",
                        value=float(
                            selected[
                                "Dispatched_Qty_m"
                            ]
                        )
                    )

                    new_closing = st.number_input(
                        "Closing Stock",
                        value=float(
                            selected[
                                "Closing_Stock_m"
                            ]
                        )
                    )

                    current_status = str(
                        selected[
                            "Stock_Status"
                        ]
                    )

                    status_options = [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]

                    if current_status not in status_options:

                        status_options.append(
                            current_status
                        )

                    new_status = st.selectbox(
                        "Stock Status",
                        status_options,
                        index=status_options.index(
                            current_status
                        )
                    )


                update_button = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )


                if update_button:

                    data = {
                        "Item_ID": new_item,
                        "Production_ID": new_production,
                        "Batch_No": new_batch,
                        "Stock_Date": str(
                            new_date
                        ),
                        "Opening_Stock_m": new_opening,
                        "Produced_Qty_m": new_produced,
                        "Dispatched_Qty_m": new_dispatched,
                        "Closing_Stock_m": new_closing,
                        "Stock_Status": new_status
                    }

                    success, message = update_record(
                        "Stock Control",
                        selected_id,
                        "Stock_ID",
                        data
                    )

                    if success:

                        st.success(message)

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(message)


            st.markdown("---")

            if st.button(
                "Delete Selected Stock"
            ):

                success, message = delete_record(
                    "Stock Control",
                    selected_id,
                    "Stock_ID"
                )

                if success:

                    st.success(message)

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(message)


# ============================================================
# CUSTOM ANALYTICS
# ============================================================

def custom_analytics():

    st.markdown(
        '<div class="page-kicker">BUSINESS INTELLIGENCE</div>',
        unsafe_allow_html=True
    )

    st.title("Custom Analytics")

    st.caption(
        "Build your own analysis from ERP datasets."
    )


    dataset_name = st.selectbox(
        "Select Dataset",
        [
            "Items",
            "Production",
            "Stock Control"
        ]
    )


    if dataset_name == "Items":

        df = items.copy()

    elif dataset_name == "Production":

        df = production.copy()

    else:

        df = stock.copy()


    if df.empty:

        st.warning(
            "Selected dataset has no records."
        )

        return


    st.subheader("Data Preview")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    st.markdown("---")


    # --------------------------------------------------------
    # COLUMN SELECTION
    # --------------------------------------------------------

    columns = df.columns.tolist()

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns.tolist()

    c1, c2, c3 = st.columns(3)


    with c1:

        x_column = st.selectbox(
            "Category / X Axis",
            columns
        )


    with c2:

        if numeric_columns:

            y_column = st.selectbox(
                "Numeric Value",
                numeric_columns
            )

        else:

            y_column = None

            st.info(
                "No numeric column available."
            )


    with c3:

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Bar Chart",
                "Line Chart",
                "Pie Chart",
                "Area Chart",
                "Scatter Plot"
            ]
        )


    # --------------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------------

    if y_column:

        aggregation = st.selectbox(
            "Aggregation",
            [
                "Sum",
                "Average",
                "Count",
                "Minimum",
                "Maximum"
            ]
        )


        grouped = df.groupby(
            x_column,
            dropna=False
        )[y_column]


        if aggregation == "Sum":

            result = grouped.sum()

        elif aggregation == "Average":

            result = grouped.mean()

        elif aggregation == "Count":

            result = grouped.count()

        elif aggregation == "Minimum":

            result = grouped.min()

        else:

            result = grouped.max()


        result = result.reset_index(
            name=y_column
        )


        st.subheader("Analysis")


        if chart_type == "Bar Chart":

            fig = px.bar(
                result,
                x=x_column,
                y=y_column,
                text_auto=True
            )

        elif chart_type == "Line Chart":

            fig = px.line(
                result,
                x=x_column,
                y=y_column,
                markers=True
            )

        elif chart_type == "Area Chart":

            fig = px.area(
                result,
                x=x_column,
                y=y_column
            )

        elif chart_type == "Scatter Plot":

            fig = px.scatter(
                result,
                x=x_column,
                y=y_column,
                size=y_column
            )

        else:

            fig = px.pie(
                result,
                names=x_column,
                values=y_column
            )


        fig.update_layout(
            height=500,
            margin=dict(
                l=20,
                r=20,
                t=30,
                b=20
            )
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


        st.subheader("Analysis Table")

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )


        st.download_button(
            "Download Analysis CSV",
            data=result.to_csv(index=False),
            file_name="custom_analysis.csv",
            mime="text/csv"
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

def data_management():

    st.markdown(
        '<div class="page-kicker">DATA MANAGEMENT</div>',
        unsafe_allow_html=True
    )

    st.title("Data Management")

    st.caption(
        "Review ERP data and export datasets."
    )


    datasets = {
        "Items": items,
        "Production": production,
        "Stock Control": stock
    }


    for name, df in datasets.items():

        with st.expander(
            f"{name} — {len(df)} records"
        ):

            if not df.empty:

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    f"Download {name}",
                    data=df.to_csv(index=False),
                    file_name=f"{name.replace(' ', '_')}.csv",
                    mime="text/csv",
                    key=f"download_{name}"
                )

            else:

                st.info(
                    "No records available."
                )


# ============================================================
# PAGE ROUTING
# ============================================================

if page == "Executive Dashboard":

    dashboard()

elif page == "Item Registration":

    item_registration()

elif page == "Production":

    production_page()

elif page == "Stock Control":

    stock_control()

elif page == "Custom Analytics":

    custom_analytics()

elif page == "Data Management":

    data_management()
