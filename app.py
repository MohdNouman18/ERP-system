import os
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Flex Head Industries ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# COMPANY / DATABASE CONFIG
# ============================================================

COMPANY_NAME = "Flex Head Industries Pvt Ltd"
COMPANY_SHORT = "FHI ERP"

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock Control": "Stock_Control",
}

CSV_FILES = {
    "Items": "Item_Registration.csv",
    "Production": "Production.csv",
    "Stock Control": "Stock_Control.csv",
}

ITEM_COLUMNS = [
    "Item_ID",
    "Material_Grade",
    "Application",
    "Nominal_Diameter_mm",
    "Wall_Thickness_mm",
    "SDR",
    "Color",
    "Standard_Length",
    "Unit",
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
    "Production_Status",
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
    "Stock_Status",
]


# ============================================================
# CSS
# ============================================================

def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_css()


# ============================================================
# SUPABASE CONNECTION
# ============================================================

def get_secret(name):
    """Read a Streamlit secret first, then environment variable."""
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    if value is None or str(value).strip() == "":
        value = os.getenv(name)

    if value is None:
        return None

    return str(value).strip()


@st.cache_resource(show_spinner=False)
def get_supabase():
    if create_client is None:
        return None, "Python package 'supabase' is not installed."

    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")

    if not url:
        return None, "SUPABASE_URL is missing from Streamlit Secrets."

    if not key:
        return None, "SUPABASE_KEY is missing from Streamlit Secrets."

    try:
        client = create_client(url, key)
        return client, None
    except Exception as e:
        return None, f"Supabase client creation failed: {e}"


supabase, supabase_init_error = get_supabase()


# ============================================================
# DATAFRAME HELPERS
# ============================================================

def empty_df(name):
    if name == "Items":
        return pd.DataFrame(columns=ITEM_COLUMNS)
    if name == "Production":
        return pd.DataFrame(columns=PRODUCTION_COLUMNS)
    return pd.DataFrame(columns=STOCK_COLUMNS)


def ensure_columns(df, columns):
    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in columns:
        if col not in df.columns:
            df[col] = None

    return df


def clean_text_columns(df):
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def safe_numeric(df, columns):
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def prepare_dataframe(name, df):
    if df is None:
        return empty_df(name)

    if name == "Items":
        df = ensure_columns(df, ITEM_COLUMNS)
        df = safe_numeric(
            df,
            [
                "Nominal_Diameter_mm",
                "Wall_Thickness_mm",
                "SDR",
                "Standard_Length",
            ],
        )
        df = clean_text_columns(df)
        return df[ITEM_COLUMNS]

    if name == "Production":
        df = ensure_columns(df, PRODUCTION_COLUMNS)
        df = safe_numeric(
            df,
            [
                "Planned_Qty_m",
                "Good_Qty_m",
                "Rejected_Qty_m",
            ],
        )
        df["Production_Date"] = pd.to_datetime(
            df["Production_Date"],
            errors="coerce",
        )
        df = clean_text_columns(df)
        return df[PRODUCTION_COLUMNS]

    df = ensure_columns(df, STOCK_COLUMNS)
    df = safe_numeric(
        df,
        [
            "Opening_Stock_m",
            "Produced_Qty_m",
            "Dispatched_Qty_m",
            "Closing_Stock_m",
        ],
    )
    df["Stock_Date"] = pd.to_datetime(
        df["Stock_Date"],
        errors="coerce",
    )
    df = clean_text_columns(df)
    return df[STOCK_COLUMNS]


# ============================================================
# SUPABASE DATA LOADING
# IMPORTANT:
# Never silently convert a Supabase error into an empty dataframe.
# The exact error is stored in session_state and displayed.
# ============================================================

def fetch_supabase_table(name):
    table_name = TABLES[name]

    if supabase is None:
        return empty_df(name), False, supabase_init_error or "Supabase is not connected."

    try:
        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        data = response.data or []
        df = pd.DataFrame(data)

        return prepare_dataframe(name, df), True, None

    except Exception as e:
        return (
            empty_df(name),
            False,
            f"{table_name}: {type(e).__name__}: {e}",
        )


def fetch_csv_table(name):
    csv_file = CSV_FILES[name]

    if not os.path.exists(csv_file):
        return empty_df(name), False, f"{csv_file} not found."

    try:
        df = pd.read_csv(csv_file)
        return prepare_dataframe(name, df), True, None
    except Exception as e:
        return (
            empty_df(name),
            False,
            f"{csv_file}: {type(e).__name__}: {e}",
        )


@st.cache_data(ttl=30, show_spinner=False)
def load_all_data():
    results = {}

    for name in TABLES:
        df, ok, error = fetch_supabase_table(name)
        results[name] = {
            "df": df,
            "ok": ok,
            "error": error,
        }

    return results


# ============================================================
# REFRESH CONTROL
# ============================================================

if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False

if st.session_state.force_refresh:
    load_all_data.clear()
    st.session_state.force_refresh = False

data = load_all_data()

items = data["Items"]["df"]
production = data["Production"]["df"]
stock = data["Stock Control"]["df"]


# ============================================================
# CRUD
# ============================================================

def insert_record(table_name, record):
    if supabase is None:
        return False, supabase_init_error or "Supabase is not connected."

    try:
        response = (
            supabase
            .table(table_name)
            .insert(record)
            .execute()
        )

        if response.data is None:
            return False, "Insert returned no data."

        return True, "Record added successfully."

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def update_record(table_name, key_column, key_value, record):
    if supabase is None:
        return False, supabase_init_error or "Supabase is not connected."

    try:
        response = (
            supabase
            .table(table_name)
            .update(record)
            .eq(key_column, key_value)
            .execute()
        )

        if response.data is None:
            return False, "Update returned no data."

        return True, "Record updated successfully."

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def delete_record(table_name, key_column, key_value):
    if supabase is None:
        return False, supabase_init_error or "Supabase is not connected."

    try:
        response = (
            supabase
            .table(table_name)
            .delete()
            .eq(key_column, key_value)
            .execute()
        )

        if response.data is None:
            return False, "Delete returned no data."

        return True, "Record deleted successfully."

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def refresh_after_write():
    load_all_data.clear()
    st.session_state.force_refresh = True
    st.rerun()


# ============================================================
# UI HELPERS
# ============================================================

def page_header(title, subtitle=""):
    st.markdown(
        '<div class="page-kicker">FLEX HEAD INDUSTRIES</div>',
        unsafe_allow_html=True,
    )
    st.title(title)

    if subtitle:
        st.caption(subtitle)


def metric_card(label, value, caption="", icon="●"):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_number(value):
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


def safe_float(value):
    try:
        number = float(value)
        if pd.isna(number):
            return 0.0
        return number
    except Exception:
        return 0.0


def show_data_status():
    failed = []

    for name, info in data.items():
        if not info["ok"]:
            failed.append((name, info["error"]))

    if failed:
        st.error("Supabase data loading problem detected.")

        for name, error in failed:
            st.markdown(f"**{name}**")
            st.code(str(error))

        st.info(
            "Agar yahan RLS / permission / table-not-found error aa raha hai, "
            "Supabase mein usi error ke mutabiq policy ya table access fix karna hoga."
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    if os.path.exists("logo.png"):
        st.image("logo.png", width=55)

    st.markdown(
        f"""
        <div class="brand">
            <div>
                <div class="brand-name">{COMPANY_NAME}</div>
                <div class="brand-sub">ENTERPRISE RESOURCE PLANNING</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    menu = st.radio(
        "Navigation",
        [
            "Executive Dashboard",
            "Item Registration",
            "Production",
            "Stock Control",
            "Custom Dashboard",
            "Analytics",
            "Data Management",
        ],
    )

    st.divider()

    if supabase is not None:
        st.success("● Supabase Client Ready")
    else:
        st.error("● Supabase Not Connected")

    if st.button("↻ Refresh Supabase Data", use_container_width=True):
        load_all_data.clear()
        st.rerun()

    st.caption("Flex Head Industries ERP")


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

def dashboard():

    page_header(
        "Executive Dashboard",
        "Real-time overview of manufacturing, production and inventory.",
    )

    show_data_status()

    # ---------------- KPIs ----------------

    total_items = len(items)
    total_planned = production["Planned_Qty_m"].sum()
    total_good = production["Good_Qty_m"].sum()
    total_rejected = production["Rejected_Qty_m"].sum()
    total_stock = stock["Closing_Stock_m"].sum()
    total_dispatched = stock["Dispatched_Qty_m"].sum()
    total_produced = stock["Produced_Qty_m"].sum()

    total_output = total_good + total_rejected
    yield_percent = (total_good / total_output * 100) if total_output > 0 else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "Registered Items",
            format_number(total_items),
            "Total product items",
            "▣",
        )

    with c2:
        metric_card(
            "Good Production",
            f"{format_number(total_good)} m",
            "Accepted production",
            "✓",
        )

    with c3:
        metric_card(
            "Current Stock",
            f"{format_number(total_stock)} m",
            "Available stock",
            "▤",
        )

    with c4:
        metric_card(
            "Production Yield",
            f"{yield_percent:.1f}%",
            "Good output / total output",
            "%",
        )

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    # Secondary KPIs
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Planned Production", f"{format_number(total_planned)} m")

    with c2:
        st.metric("Rejected", f"{format_number(total_rejected)} m")

    with c3:
        st.metric("Produced / Stock", f"{format_number(total_produced)} m")

    with c4:
        st.metric("Dispatched", f"{format_number(total_dispatched)} m")

    st.divider()

    # ---------------- FILTERS ----------------

    st.subheader("Production Overview")

    col1, col2, col3 = st.columns(3)

    if not production.empty:
        lines = sorted(
            production["Production_Line"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        statuses = sorted(
            production["Production_Status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    else:
        lines = []
        statuses = []

    with col1:
        selected_line = st.selectbox(
            "Production Line",
            ["All"] + lines,
        )

    with col2:
        selected_status = st.selectbox(
            "Production Status",
            ["All"] + statuses,
        )

    with col3:
        item_ids = sorted(
            items["Item_ID"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        ) if not items.empty else []

        selected_item = st.selectbox(
            "Item",
            ["All"] + item_ids,
        )

    filtered_production = production.copy()

    if selected_line != "All":
        filtered_production = filtered_production[
            filtered_production["Production_Line"].astype(str)
            == selected_line
        ]

    if selected_status != "All":
        filtered_production = filtered_production[
            filtered_production["Production_Status"].astype(str)
            == selected_status
        ]

    if selected_item != "All":
        filtered_production = filtered_production[
            filtered_production["Item_ID"].astype(str)
            == selected_item
        ]

    # ---------------- CHARTS ----------------

    chart1, chart2 = st.columns(2)

    with chart1:
        if not filtered_production.empty:
            trend = (
                filtered_production
                .dropna(subset=["Production_Date"])
                .groupby("Production_Date", as_index=False)[
                    [
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m",
                    ]
                ]
                .sum()
                .sort_values("Production_Date")
            )

            if not trend.empty:
                trend_melt = trend.melt(
                    id_vars="Production_Date",
                    value_vars=[
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m",
                    ],
                    var_name="Metric",
                    value_name="Quantity",
                )

                fig = px.line(
                    trend_melt,
                    x="Production_Date",
                    y="Quantity",
                    color="Metric",
                    markers=True,
                    title="Production Trend",
                )

                fig.update_layout(height=400, legend_title="")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Production dates are empty/invalid.")
        else:
            st.info("No production data available.")

    with chart2:
        if not filtered_production.empty:
            status_data = (
                filtered_production
                .groupby("Production_Status", as_index=False)["Good_Qty_m"]
                .sum()
            )

            if not status_data.empty:
                fig = px.pie(
                    status_data,
                    names="Production_Status",
                    values="Good_Qty_m",
                    hole=0.45,
                    title="Production Status",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No production status data.")
        else:
            st.info("No production status data.")

    # ---------------- STOCK ----------------

    st.subheader("Current Stock by Item")

    if not stock.empty:
        stock_chart = (
            stock
            .groupby("Item_ID", as_index=False)["Closing_Stock_m"]
            .sum()
            .sort_values("Closing_Stock_m", ascending=False)
        )

        fig = px.bar(
            stock_chart,
            x="Item_ID",
            y="Closing_Stock_m",
            text_auto=".0f",
            title="Closing Stock",
        )

        fig.update_layout(
            height=400,
            xaxis_title="Item",
            yaxis_title="Stock (m)",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No stock data available.")

    # ---------------- RECENT PRODUCTION ----------------

    st.subheader("Recent Production")

    if not production.empty:
        recent = (
            production
            .sort_values("Production_Date", ascending=False)
            .head(10)
        )

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No production records found.")


# ============================================================
# ITEM REGISTRATION
# ============================================================

def item_registration():

    page_header(
        "Item Registration",
        "Manage pipe products and material specifications.",
    )

    show_data_status()

    tab1, tab2, tab3 = st.tabs(
        ["View Items", "Add Item", "Edit / Delete"]
    )

    with tab1:
        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Items CSV",
            items.to_csv(index=False).encode("utf-8"),
            "Item_Registration.csv",
            "text/csv",
        )

    with tab2:
        st.subheader("Register New Item")

        with st.form("add_item_form"):
            c1, c2 = st.columns(2)

            with c1:
                item_id = st.text_input("Item ID *", placeholder="ITM-001")
                material_grade = st.text_input(
                    "Material Grade", placeholder="PE100"
                )
                application = st.text_input(
                    "Application", placeholder="Water Supply"
                )
                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0,
                )
                wall = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1,
                )

            with c2:
                sdr = st.number_input(
                    "SDR", min_value=0.0, step=0.1
                )
                color = st.text_input(
                    "Color", placeholder="Black"
                )
                standard_length = st.number_input(
                    "Standard Length",
                    min_value=0.0,
                    step=1.0,
                )
                unit = st.text_input("Unit", value="m")

            submit = st.form_submit_button(
                "Add Item", type="primary"
            )

            if submit:
                item_id = item_id.strip()

                if not item_id:
                    st.error("Item ID is required.")
                elif (
                    not items.empty
                    and item_id in items["Item_ID"].astype(str).values
                ):
                    st.error("This Item ID already exists.")
                else:
                    record = {
                        "Item_ID": item_id,
                        "Material_Grade": material_grade.strip(),
                        "Application": application.strip(),
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": wall,
                        "SDR": sdr,
                        "Color": color.strip(),
                        "Standard_Length": standard_length,
                        "Unit": unit.strip(),
                    }

                    success, message = insert_record(
                        TABLES["Items"], record
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

    with tab3:
        if items.empty:
            st.info("No items available.")
        else:
            selected_id = st.selectbox(
                "Select Item",
                items["Item_ID"].astype(str).tolist(),
            )

            row = items[
                items["Item_ID"].astype(str) == selected_id
            ].iloc[0]

            st.subheader("Edit Item")

            with st.form("edit_item_form"):
                c1, c2 = st.columns(2)

                with c1:
                    material_grade = st.text_input(
                        "Material Grade",
                        value=str(row["Material_Grade"]),
                    )
                    application = st.text_input(
                        "Application",
                        value=str(row["Application"]),
                    )
                    diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=safe_float(row["Nominal_Diameter_mm"]),
                    )
                    wall = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=safe_float(row["Wall_Thickness_mm"]),
                    )

                with c2:
                    sdr = st.number_input(
                        "SDR",
                        min_value=0.0,
                        value=safe_float(row["SDR"]),
                    )
                    color = st.text_input(
                        "Color",
                        value=str(row["Color"]),
                    )
                    standard_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=safe_float(row["Standard_Length"]),
                    )
                    unit = st.text_input(
                        "Unit",
                        value=str(row["Unit"]),
                    )

                update_btn = st.form_submit_button(
                    "Update Item", type="primary"
                )

                if update_btn:
                    record = {
                        "Material_Grade": material_grade.strip(),
                        "Application": application.strip(),
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": wall,
                        "SDR": sdr,
                        "Color": color.strip(),
                        "Standard_Length": standard_length,
                        "Unit": unit.strip(),
                    }

                    success, message = update_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_id,
                        record,
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

            st.divider()

            if st.button(
                "Delete Selected Item",
                type="secondary",
            ):
                success, message = delete_record(
                    TABLES["Items"],
                    "Item_ID",
                    selected_id,
                )

                if success:
                    st.success(message)
                    refresh_after_write()
                else:
                    st.error(message)


# ============================================================
# PRODUCTION
# ============================================================

def production_page():

    page_header(
        "Production",
        "Manage manufacturing plans, output, rejection and status.",
    )

    show_data_status()

    tab1, tab2, tab3 = st.tabs(
        ["Production Records", "Add Production", "Edit / Delete"]
    )

    with tab1:
        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Production CSV",
            production.to_csv(index=False).encode("utf-8"),
            "Production.csv",
            "text/csv",
        )

    with tab2:
        st.subheader("Add Production Record")

        item_options = (
            items["Item_ID"].dropna().astype(str).tolist()
            if not items.empty
            else [""]
        )

        with st.form("add_production_form"):
            c1, c2 = st.columns(2)

            with c1:
                production_id = st.text_input(
                    "Production ID *",
                    placeholder="PRD-001",
                )
                item_id = st.selectbox(
                    "Item ID", item_options
                )
                production_date = st.date_input(
                    "Production Date",
                    value=date.today(),
                )
                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001",
                )
                production_line = st.text_input(
                    "Production Line",
                    placeholder="Line 1",
                )

            with c2:
                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0.0,
                    step=1.0,
                )
                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0.0,
                    step=1.0,
                )
                rejected_qty = st.number_input(
                    "Rejected Quantity (m)",
                    min_value=0.0,
                    step=1.0,
                )
                production_status = st.selectbox(
                    "Production Status",
                    [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "On Hold",
                        "Cancelled",
                    ],
                )

            submit = st.form_submit_button(
                "Add Production",
                type="primary",
            )

            if submit:
                production_id = production_id.strip()

                if not production_id:
                    st.error("Production ID is required.")
                elif (
                    not production.empty
                    and production_id
                    in production["Production_ID"].astype(str).values
                ):
                    st.error("This Production ID already exists.")
                elif not item_id:
                    st.error("Please register an Item first.")
                else:
                    record = {
                        "Production_ID": production_id,
                        "Item_ID": item_id,
                        "Production_Date": production_date.isoformat(),
                        "Batch_No": batch_no.strip(),
                        "Production_Line": production_line.strip(),
                        "Planned_Qty_m": planned_qty,
                        "Good_Qty_m": good_qty,
                        "Rejected_Qty_m": rejected_qty,
                        "Production_Status": production_status,
                    }

                    success, message = insert_record(
                        TABLES["Production"], record
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

    with tab3:
        if production.empty:
            st.info("No production records available.")
        else:
            selected_id = st.selectbox(
                "Select Production ID",
                production["Production_ID"].astype(str).tolist(),
            )

            row = production[
                production["Production_ID"].astype(str)
                == selected_id
            ].iloc[0]

            st.subheader("Edit Production")

            current_date = row["Production_Date"]
            if pd.isna(current_date):
                current_date = date.today()
            else:
                current_date = current_date.date()

            item_options = (
                items["Item_ID"].astype(str).tolist()
                if not items.empty
                else [str(row["Item_ID"])]
            )

            current_item = str(row["Item_ID"])
            if current_item not in item_options:
                item_options = [current_item] + item_options

            statuses = [
                "Planned",
                "In Progress",
                "Completed",
                "On Hold",
                "Cancelled",
            ]

            current_status = str(row["Production_Status"])
            if current_status not in statuses:
                statuses = [current_status] + statuses

            with st.form("edit_production_form"):
                c1, c2 = st.columns(2)

                with c1:
                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(current_item),
                    )
                    production_date = st.date_input(
                        "Production Date",
                        value=current_date,
                    )
                    batch_no = st.text_input(
                        "Batch No",
                        value=str(row["Batch_No"]),
                    )
                    production_line = st.text_input(
                        "Production Line",
                        value=str(row["Production_Line"]),
                    )

                with c2:
                    planned_qty = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0.0,
                        value=safe_float(row["Planned_Qty_m"]),
                    )
                    good_qty = st.number_input(
                        "Good Quantity (m)",
                        min_value=0.0,
                        value=safe_float(row["Good_Qty_m"]),
                    )
                    rejected_qty = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0.0,
                        value=safe_float(row["Rejected_Qty_m"]),
                    )
                    production_status = st.selectbox(
                        "Production Status",
                        statuses,
                        index=statuses.index(current_status),
                    )

                update_btn = st.form_submit_button(
                    "Update Production",
                    type="primary",
                )

                if update_btn:
                    record = {
                        "Item_ID": item_id,
                        "Production_Date": production_date.isoformat(),
                        "Batch_No": batch_no.strip(),
                        "Production_Line": production_line.strip(),
                        "Planned_Qty_m": planned_qty,
                        "Good_Qty_m": good_qty,
                        "Rejected_Qty_m": rejected_qty,
                        "Production_Status": production_status,
                    }

                    success, message = update_record(
                        TABLES["Production"],
                        "Production_ID",
                        selected_id,
                        record,
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

            st.divider()

            if st.button(
                "Delete Selected Production",
                type="secondary",
            ):
                success, message = delete_record(
                    TABLES["Production"],
                    "Production_ID",
                    selected_id,
                )

                if success:
                    st.success(message)
                    refresh_after_write()
                else:
                    st.error(message)


# ============================================================
# STOCK CONTROL
# ============================================================

def stock_control():

    page_header(
        "Stock Control",
        "Monitor opening stock, production, dispatch and closing inventory.",
    )

    show_data_status()

    tab1, tab2, tab3 = st.tabs(
        ["Stock Records", "Add Stock", "Edit / Delete"]
    )

    with tab1:
        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Stock CSV",
            stock.to_csv(index=False).encode("utf-8"),
            "Stock_Control.csv",
            "text/csv",
        )

    with tab2:
        st.subheader("Add Stock Record")

        item_options = (
            items["Item_ID"].dropna().astype(str).tolist()
            if not items.empty
            else [""]
        )

        production_options = (
            production["Production_ID"].dropna().astype(str).tolist()
            if not production.empty
            else [""]
        )

        with st.form("add_stock_form"):
            c1, c2 = st.columns(2)

            with c1:
                stock_id = st.text_input(
                    "Stock ID *",
                    placeholder="STK-001",
                )
                item_id = st.selectbox(
                    "Item ID",
                    item_options,
                )
                production_id = st.selectbox(
                    "Production ID",
                    production_options,
                )
                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001",
                )
                stock_date = st.date_input(
                    "Stock Date",
                    value=date.today(),
                )

            with c2:
                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0.0,
                    step=1.0,
                )
                produced_qty = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0.0,
                    step=1.0,
                )
                dispatched_qty = st.number_input(
                    "Dispatched Quantity (m)",
                    min_value=0.0,
                    step=1.0,
                )

                closing_stock = (
                    opening_stock
                    + produced_qty
                    - dispatched_qty
                )

                st.info(
                    f"Calculated Closing Stock: {closing_stock:,.2f} m"
                )

                stock_status = st.selectbox(
                    "Stock Status",
                    [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved",
                    ],
                )

            submit = st.form_submit_button(
                "Add Stock",
                type="primary",
            )

            if submit:
                stock_id = stock_id.strip()

                if not stock_id:
                    st.error("Stock ID is required.")
                elif (
                    not stock.empty
                    and stock_id in stock["Stock_ID"].astype(str).values
                ):
                    st.error("This Stock ID already exists.")
                elif not item_id:
                    st.error("Please register an Item first.")
                else:
                    record = {
                        "Stock_ID": stock_id,
                        "Item_ID": item_id,
                        "Production_ID": production_id,
                        "Batch_No": batch_no.strip(),
                        "Stock_Date": stock_date.isoformat(),
                        "Opening_Stock_m": opening_stock,
                        "Produced_Qty_m": produced_qty,
                        "Dispatched_Qty_m": dispatched_qty,
                        "Closing_Stock_m": closing_stock,
                        "Stock_Status": stock_status,
                    }

                    success, message = insert_record(
                        TABLES["Stock Control"], record
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

    with tab3:
        if stock.empty:
            st.info("No stock records available.")
        else:
            selected_id = st.selectbox(
                "Select Stock ID",
                stock["Stock_ID"].astype(str).tolist(),
            )

            row = stock[
                stock["Stock_ID"].astype(str) == selected_id
            ].iloc[0]

            current_date = row["Stock_Date"]
            if pd.isna(current_date):
                current_date = date.today()
            else:
                current_date = current_date.date()

            item_options = (
                items["Item_ID"].astype(str).tolist()
                if not items.empty
                else [str(row["Item_ID"])]
            )

            current_item = str(row["Item_ID"])
            if current_item not in item_options:
                item_options = [current_item] + item_options

            production_options = (
                production["Production_ID"].astype(str).tolist()
                if not production.empty
                else [str(row["Production_ID"])]
            )

            current_production = str(row["Production_ID"])
            if current_production not in production_options:
                production_options = (
                    [current_production] + production_options
                )

            statuses = [
                "Available",
                "Low Stock",
                "Out of Stock",
                "Reserved",
            ]

            current_status = str(row["Stock_Status"])
            if current_status not in statuses:
                statuses = [current_status] + statuses

            st.subheader("Edit Stock")

            with st.form("edit_stock_form"):
                c1, c2 = st.columns(2)

                with c1:
                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(current_item),
                    )
                    production_id = st.selectbox(
                        "Production ID",
                        production_options,
                        index=production_options.index(current_production),
                    )
                    batch_no = st.text_input(
                        "Batch No",
                        value=str(row["Batch_No"]),
                    )
                    stock_date = st.date_input(
                        "Stock Date",
                        value=current_date,
                    )

                with c2:
                    opening_stock = st.number_input(
                        "Opening Stock (m)",
                        min_value=0.0,
                        value=safe_float(row["Opening_Stock_m"]),
                    )
                    produced_qty = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0.0,
                        value=safe_float(row["Produced_Qty_m"]),
                    )
                    dispatched_qty = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0.0,
                        value=safe_float(row["Dispatched_Qty_m"]),
                    )

                    closing_stock = (
                        opening_stock
                        + produced_qty
                        - dispatched_qty
                    )

                    st.info(
                        f"Calculated Closing Stock: {closing_stock:,.2f} m"
                    )

                    stock_status = st.selectbox(
                        "Stock Status",
                        statuses,
                        index=statuses.index(current_status),
                    )

                update_btn = st.form_submit_button(
                    "Update Stock",
                    type="primary",
                )

                if update_btn:
                    record = {
                        "Item_ID": item_id,
                        "Production_ID": production_id,
                        "Batch_No": batch_no.strip(),
                        "Stock_Date": stock_date.isoformat(),
                        "Opening_Stock_m": opening_stock,
                        "Produced_Qty_m": produced_qty,
                        "Dispatched_Qty_m": dispatched_qty,
                        "Closing_Stock_m": closing_stock,
                        "Stock_Status": stock_status,
                    }

                    success, message = update_record(
                        TABLES["Stock Control"],
                        "Stock_ID",
                        selected_id,
                        record,
                    )

                    if success:
                        st.success(message)
                        refresh_after_write()
                    else:
                        st.error(message)

            st.divider()

            if st.button(
                "Delete Selected Stock",
                type="secondary",
            ):
                success, message = delete_record(
                    TABLES["Stock Control"],
                    "Stock_ID",
                    selected_id,
                )

                if success:
                    st.success(message)
                    refresh_after_write()
                else:
                    st.error(message)


# ============================================================
# CUSTOM DASHBOARD
# ============================================================

def custom_dashboard():

    page_header(
        "Custom Dashboard",
        "Build charts from the live Supabase datasets.",
    )

    datasets = {
        "Items": items,
        "Production": production,
        "Stock Control": stock,
    }

    dataset_name = st.selectbox(
        "Dataset",
        list(datasets.keys()),
    )

    df = datasets[dataset_name]

    if df.empty:
        st.info(f"No data available in {dataset_name}.")
        show_data_status()
        return

    st.dataframe(
        df.head(100),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    chart_type = st.selectbox(
        "Chart Type",
        ["Bar Chart", "Line Chart", "Pie Chart"],
    )

    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(
        include="number"
    ).columns.tolist()

    if chart_type == "Bar Chart":
        c1, c2 = st.columns(2)

        with c1:
            x_col = st.selectbox("X Axis", columns)

        with c2:
            if numeric_cols:
                y_col = st.selectbox("Y Axis", numeric_cols)

                grouped = (
                    df.groupby(x_col, as_index=False)[y_col]
                    .sum()
                    .sort_values(y_col, ascending=False)
                    .head(30)
                )

                fig = px.bar(
                    grouped,
                    x=x_col,
                    y=y_col,
                    title=f"{y_col} by {x_col}",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
            else:
                st.warning("No numeric column available.")

    elif chart_type == "Line Chart":
        if numeric_cols:
            c1, c2 = st.columns(2)

            with c1:
                x_col = st.selectbox("X Axis", columns)

            with c2:
                y_col = st.selectbox("Y Axis", numeric_cols)

            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                markers=True,
                title=f"{y_col} Trend",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        else:
            st.warning("No numeric columns available.")

    else:
        category_cols = df.select_dtypes(
            exclude="number"
        ).columns.tolist()

        if category_cols and numeric_cols:
            c1, c2 = st.columns(2)

            with c1:
                name_col = st.selectbox(
                    "Category",
                    category_cols,
                )

            with c2:
                value_col = st.selectbox(
                    "Value",
                    numeric_cols,
                )

            grouped = (
                df.groupby(name_col, as_index=False)[value_col]
                .sum()
            )

            fig = px.pie(
                grouped,
                names=name_col,
                values=value_col,
                hole=0.4,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        else:
            st.warning(
                "Need one category and one numeric column."
            )


# ============================================================
# ANALYTICS
# ============================================================

def analytics():

    page_header(
        "Analytics",
        "Detailed production and inventory performance analysis.",
    )

    show_data_status()

    st.subheader("Production Analytics")

    if production.empty:
        st.info("No production data available.")
    else:
        total_planned = production["Planned_Qty_m"].sum()
        total_good = production["Good_Qty_m"].sum()
        total_rejected = production["Rejected_Qty_m"].sum()
        total_output = total_good + total_rejected

        yield_rate = (
            total_good / total_output * 100
            if total_output > 0
            else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Planned",
            f"{total_planned:,.0f} m",
        )
        c2.metric(
            "Good",
            f"{total_good:,.0f} m",
        )
        c3.metric(
            "Rejected",
            f"{total_rejected:,.0f} m",
        )
        c4.metric(
            "Yield",
            f"{yield_rate:.1f}%",
        )

        by_line = (
            production
            .groupby("Production_Line", as_index=False)[
                [
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m",
                ]
            ]
            .sum()
        )

        if not by_line.empty:
            by_line["Yield_%"] = (
                by_line["Good_Qty_m"]
                / (
                    by_line["Good_Qty_m"]
                    + by_line["Rejected_Qty_m"]
                )
                .replace(0, pd.NA)
                * 100
            ).fillna(0)

            st.subheader("Production by Line")
            st.dataframe(
                by_line,
                use_container_width=True,
                hide_index=True,
            )

            fig = px.bar(
                by_line,
                x="Production_Line",
                y=["Good_Qty_m", "Rejected_Qty_m"],
                barmode="group",
                title="Good vs Rejected by Production Line",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    st.divider()

    st.subheader("Stock Analytics")

    if stock.empty:
        st.info("No stock data available.")
    else:
        summary = (
            stock
            .groupby("Item_ID", as_index=False)[
                [
                    "Opening_Stock_m",
                    "Produced_Qty_m",
                    "Dispatched_Qty_m",
                    "Closing_Stock_m",
                ]
            ]
            .sum()
        )

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
        )

        fig = px.bar(
            summary,
            x="Item_ID",
            y=[
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m",
            ],
            barmode="group",
            title="Inventory Movement",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

def data_management():

    page_header(
        "Data Management",
        "Live database status, table diagnostics and downloadable data.",
    )

    st.subheader("Supabase Connection")

    if supabase is None:
        st.error(
            supabase_init_error
            or "Supabase client is not connected."
        )
    else:
        st.success("Supabase client created successfully.")

    st.divider()

    st.subheader("Live Table Diagnostics")

    rows = []

    for name, table_name in TABLES.items():
        info = data[name]

        rows.append(
            {
                "Module": name,
                "Supabase Table": table_name,
                "Loaded": "YES" if info["ok"] else "NO",
                "Rows": len(info["df"]),
                "Error": "" if info["ok"] else str(info["error"]),
            }
        )

    diagnostics = pd.DataFrame(rows)

    st.dataframe(
        diagnostics,
        use_container_width=True,
        hide_index=True,
    )

    failed = diagnostics[
        diagnostics["Loaded"] == "NO"
    ]

    if not failed.empty:
        st.error(
            "One or more Supabase tables could not be read. "
            "Dashboard zeros are expected until these errors are fixed."
        )

        for _, row in failed.iterrows():
            st.markdown(
                f"**{row['Supabase Table']} error:**"
            )
            st.code(str(row["Error"]))

    st.divider()

    st.subheader("Current Row Counts")

    c1, c2, c3 = st.columns(3)

    c1.metric("Items", len(items))
    c2.metric("Production", len(production))
    c3.metric("Stock", len(stock))

    st.divider()

    dataset_name = st.selectbox(
        "Download Dataset",
        ["Items", "Production", "Stock Control"],
    )

    selected_df = {
        "Items": items,
        "Production": production,
        "Stock Control": stock,
    }[dataset_name]

    st.dataframe(
        selected_df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Current Data as CSV",
        selected_df.to_csv(index=False).encode("utf-8"),
        f"{dataset_name.replace(' ', '_')}.csv",
        "text/csv",
    )

    st.divider()

    st.subheader("Required Supabase Tables")

    st.code(
        """
Item_Registration
Production
Stock_Control
        """.strip()
    )

    st.caption(
        "The application intentionally does not silently switch to CSV when "
        "Supabase fails. This makes database errors visible instead of showing false 0 values."
    )


# ============================================================
# ROUTER
# ============================================================

if menu == "Executive Dashboard":
    dashboard()

elif menu == "Item Registration":
    item_registration()

elif menu == "Production":
    production_page()

elif menu == "Stock Control":
    stock_control()

elif menu == "Custom Dashboard":
    custom_dashboard()

elif menu == "Analytics":
    analytics()

elif menu == "Data Management":
    data_management()
