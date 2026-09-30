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
# COMPANY
# ============================================================

COMPANY_NAME = "Flex Head Industries Pvt Ltd"
COMPANY_SHORT = "FHI ERP"


# ============================================================
# EXACT SUPABASE TABLE NAMES
# ============================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock Control": "Stock_Control"
}


# ============================================================
# CSV FILES
# ============================================================

CSV_FILES = {
    "Items": "Item_Registration.csv",
    "Production": "Production.csv",
    "Stock Control": "Stock_Control.csv"
}


# ============================================================
# EXACT SUPABASE SCHEMAS
# ============================================================

ITEM_COLUMNS = [
    "Item_ID",
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
# LOAD CSS
# ============================================================

def load_css():
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )


load_css()


# ============================================================
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase():
    if create_client is None:
        return None

    try:
        url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
        key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))

        if not url or not key:
            return None

        return create_client(url, key)

    except Exception:
        return None


supabase = get_supabase()


# ============================================================
# SESSION STATE
# ============================================================

if "data_source" not in st.session_state:
    st.session_state.data_source = "Supabase" if supabase else "CSV"

if "refresh_data" not in st.session_state:
    st.session_state.refresh_data = False


# ============================================================
# DATA HELPERS
# ============================================================

def ensure_columns(df, columns):
    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in columns:
        if col not in df.columns:
            df[col] = None

    return df


def clean_text_columns(df):
    if df.empty:
        return df

    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def safe_numeric(df, columns):
    df = df.copy()

    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def prepare_dataframe(name, df):
    if df is None:
        df = pd.DataFrame()

    if name == "Items":
        df = ensure_columns(df, ITEM_COLUMNS)

        df = safe_numeric(
            df,
            [
                "Nominal_Diameter_mm",
                "Wall_Thickness_mm",
                "SDR",
                "Standard_Length"
            ]
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
                "Rejected_Qty_m"
            ]
        )

        if "Production_Date" in df.columns:
            df["Production_Date"] = pd.to_datetime(
                df["Production_Date"],
                errors="coerce"
            )

        df = clean_text_columns(df)

        return df[PRODUCTION_COLUMNS]

    if name == "Stock Control":
        df = ensure_columns(df, STOCK_COLUMNS)

        df = safe_numeric(
            df,
            [
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m"
            ]
        )

        if "Stock_Date" in df.columns:
            df["Stock_Date"] = pd.to_datetime(
                df["Stock_Date"],
                errors="coerce"
            )

        df = clean_text_columns(df)

        return df[STOCK_COLUMNS]

    return df


# ============================================================
# FETCH DATA
# ============================================================

def fetch_table(name):
    table_name = TABLES[name]

    # ---------------- SUPABASE ----------------
    if supabase is not None:

        try:
            response = (
                supabase
                .table(table_name)
                .select("*")
                .execute()
            )

            data = response.data

            if data is not None:
                df = pd.DataFrame(data)
                return prepare_dataframe(name, df)

        except Exception as e:
            st.warning(
                f"Supabase error in {table_name}: {str(e)}"
            )

    # ---------------- CSV FALLBACK ----------------

    csv_file = CSV_FILES[name]

    if os.path.exists(csv_file):
        try:
            df = pd.read_csv(csv_file)
            return prepare_dataframe(name, df)

        except Exception as e:
            st.error(
                f"Could not read {csv_file}: {str(e)}"
            )

    # Empty dataframe
    if name == "Items":
        return pd.DataFrame(columns=ITEM_COLUMNS)

    if name == "Production":
        return pd.DataFrame(columns=PRODUCTION_COLUMNS)

    return pd.DataFrame(columns=STOCK_COLUMNS)


# ============================================================
# CRUD FUNCTIONS
# ============================================================

def insert_record(table_name, record):
    if supabase is None:
        return False, "Supabase is not connected."

    try:
        supabase.table(table_name).insert(record).execute()
        return True, "Record added successfully."

    except Exception as e:
        return False, str(e)


def update_record(table_name, column_name, value, record):
    if supabase is None:
        return False, "Supabase is not connected."

    try:
        (
            supabase
            .table(table_name)
            .update(record)
            .eq(column_name, value)
            .execute()
        )

        return True, "Record updated successfully."

    except Exception as e:
        return False, str(e)


def delete_record(table_name, column_name, value):
    if supabase is None:
        return False, "Supabase is not connected."

    try:
        (
            supabase
            .table(table_name)
            .delete()
            .eq(column_name, value)
            .execute()
        )

        return True, "Record deleted successfully."

    except Exception as e:
        return False, str(e)


# ============================================================
# LOAD ALL DATA
# ============================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


# ============================================================
# GENERAL UI
# ============================================================

def page_header(title, subtitle=""):
    st.markdown(
        '<div class="page-kicker">FLEX HEAD INDUSTRIES</div>',
        unsafe_allow_html=True
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
        unsafe_allow_html=True
    )


def format_number(value):
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    if os.path.exists("logo.png"):
        st.image(
            "logo.png",
            width=55
        )

    st.markdown(
        f"""
        <div class="brand">
            <div>
                <div class="brand-name">
                    {COMPANY_NAME}
                </div>
                <div class="brand-sub">
                    ENTERPRISE RESOURCE PLANNING
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
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
            "Data Management"
        ]
    )

    st.divider()

    if supabase:
        st.success("● Supabase Connected")
    else:
        st.warning("● CSV Mode")

    st.caption("Flex Head Industries ERP")


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

def dashboard():

    page_header(
        "Executive Dashboard",
        "Real-time overview of manufacturing, production and inventory."
    )

    # ---------------- KPIs ----------------

    total_items = len(items)

    total_planned = production["Planned_Qty_m"].sum()

    total_good = production["Good_Qty_m"].sum()

    total_rejected = production["Rejected_Qty_m"].sum()

    total_stock = stock["Closing_Stock_m"].sum()

    total_dispatched = stock["Dispatched_Qty_m"].sum()

    total_produced = stock["Produced_Qty_m"].sum()

    total_output = total_good + total_rejected

    if total_output > 0:
        yield_percent = (
            total_good /
            total_output
        ) * 100
    else:
        yield_percent = 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "Registered Items",
            format_number(total_items),
            "Total product items",
            "▣"
        )

    with c2:
        metric_card(
            "Good Production",
            f"{format_number(total_good)} m",
            "Accepted production",
            "✓"
        )

    with c3:
        metric_card(
            "Current Stock",
            f"{format_number(total_stock)} m",
            "Available stock",
            "▤"
        )

    with c4:
        metric_card(
            "Production Yield",
            f"{yield_percent:.1f}%",
            "Good output / total output",
            "%"
        )

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    # ---------------- FILTERS ----------------

    st.subheader("Production Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        if not production.empty:
            lines = sorted(
                production["Production_Line"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_line = st.selectbox(
                "Production Line",
                ["All"] + lines
            )
        else:
            selected_line = "All"

    with col2:
        if not production.empty:
            statuses = sorted(
                production["Production_Status"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_status = st.selectbox(
                "Production Status",
                ["All"] + statuses
            )
        else:
            selected_status = "All"

    with col3:
        if not items.empty:
            item_ids = sorted(
                items["Item_ID"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            selected_item = st.selectbox(
                "Item",
                ["All"] + item_ids
            )
        else:
            selected_item = "All"

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
                .groupby("Production_Date", as_index=False)[
                    [
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ]
                ]
                .sum()
                .sort_values("Production_Date")
            )

            trend_melt = trend.melt(
                id_vars="Production_Date",
                value_vars=[
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                var_name="Metric",
                value_name="Quantity"
            )

            fig = px.line(
                trend_melt,
                x="Production_Date",
                y="Quantity",
                color="Metric",
                markers=True,
                title="Production Trend"
            )

            fig.update_layout(
                height=400,
                legend_title=""
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("No production data available.")

    with chart2:

        if not filtered_production.empty:

            status_data = (
                filtered_production
                .groupby("Production_Status", as_index=False)
                ["Good_Qty_m"]
                .sum()
            )

            fig = px.pie(
                status_data,
                names="Production_Status",
                values="Good_Qty_m",
                hole=0.45,
                title="Production Status"
            )

            fig.update_layout(
                height=400
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.info("No production status data.")

    # ---------------- STOCK BY ITEM ----------------

    st.subheader("Current Stock by Item")

    if not stock.empty:

        stock_chart = (
            stock
            .groupby("Item_ID", as_index=False)
            ["Closing_Stock_m"]
            .sum()
            .sort_values(
                "Closing_Stock_m",
                ascending=False
            )
        )

        fig = px.bar(
            stock_chart,
            x="Item_ID",
            y="Closing_Stock_m",
            text_auto=".0f",
            title="Closing Stock"
        )

        fig.update_layout(
            height=400,
            xaxis_title="Item",
            yaxis_title="Stock (m)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        st.info("No stock data available.")

    # ---------------- RECENT PRODUCTION ----------------

    st.subheader("Recent Production")

    if not production.empty:

        recent = (
            production
            .sort_values(
                "Production_Date",
                ascending=False
            )
            .head(10)
        )

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No production records found.")


# ============================================================
# ITEM REGISTRATION
# ============================================================

def item_registration():

    page_header(
        "Item Registration",
        "Manage pipe products and material specifications."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "View Items",
            "Add Item",
            "Edit / Delete"
        ]
    )

    # ========================================================
    # VIEW
    # ========================================================

    with tab1:

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Items CSV",
            items.to_csv(index=False).encode("utf-8"),
            "Item_Registration.csv",
            "text/csv"
        )

    # ========================================================
    # ADD
    # ========================================================

    with tab2:

        st.subheader("Register New Item")

        with st.form("add_item_form"):

            c1, c2 = st.columns(2)

            with c1:

                item_id = st.text_input(
                    "Item ID *",
                    placeholder="ITM-001"
                )

                material_grade = st.text_input(
                    "Material Grade",
                    placeholder="PE100"
                )

                application = st.text_input(
                    "Application",
                    placeholder="Water Supply"
                )

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0
                )

                wall = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1
                )

            with c2:

                sdr = st.number_input(
                    "SDR",
                    min_value=0.0,
                    step=0.1
                )

                color = st.text_input(
                    "Color",
                    placeholder="Black"
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

            submit = st.form_submit_button(
                "Add Item",
                type="primary"
            )

            if submit:

                if not item_id.strip():
                    st.error("Item ID is required.")

                elif (
                    not items.empty
                    and item_id.strip()
                    in items["Item_ID"].astype(str).values
                ):
                    st.error("This Item ID already exists.")

                else:

                    record = {
                        "Item_ID": item_id.strip(),
                        "Material_Grade": material_grade.strip(),
                        "Application": application.strip(),
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": wall,
                        "SDR": sdr,
                        "Color": color.strip(),
                        "Standard_Length": standard_length,
                        "Unit": unit.strip()
                    }

                    success, message = insert_record(
                        TABLES["Items"],
                        record
                    )

                    if success:
                        st.success(message)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(message)

    # ========================================================
    # EDIT / DELETE
    # ========================================================

    with tab3:

        if items.empty:
            st.info("No items available.")
        else:

            selected_id = st.selectbox(
                "Select Item",
                items["Item_ID"].astype(str).tolist()
            )

            selected_row = items[
                items["Item_ID"].astype(str)
                == selected_id
            ].iloc[0]

            st.subheader("Edit Item")

            with st.form("edit_item_form"):

                c1, c2 = st.columns(2)

                with c1:

                    material_grade = st.text_input(
                        "Material Grade",
                        value=str(
                            selected_row["Material_Grade"]
                        )
                    )

                    application = st.text_input(
                        "Application",
                        value=str(
                            selected_row["Application"]
                        )
                    )

                    diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Nominal_Diameter_mm"
                            ]
                        )
                    )

                    wall = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Wall_Thickness_mm"
                            ]
                        )
                    )

                with c2:

                    sdr = st.number_input(
                        "SDR",
                        min_value=0.0,
                        value=float(
                            selected_row["SDR"]
                        )
                    )

                    color = st.text_input(
                        "Color",
                        value=str(
                            selected_row["Color"]
                        )
                    )

                    standard_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Standard_Length"
                            ]
                        )
                    )

                    unit = st.text_input(
                        "Unit",
                        value=str(
                            selected_row["Unit"]
                        )
                    )

                update_btn = st.form_submit_button(
                    "Update Item",
                    type="primary"
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
                        "Unit": unit.strip()
                    }

                    success, message = update_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_id,
                        record
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            st.divider()

            st.subheader("Delete Item")

            if st.button(
                "Delete Selected Item",
                type="secondary"
            ):

                success, message = delete_record(
                    TABLES["Items"],
                    "Item_ID",
                    selected_id
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# ============================================================
# PRODUCTION
# ============================================================

def production_page():

    page_header(
        "Production Management",
        "Track manufacturing batches, quantities and production performance."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Production Records",
            "Add Production",
            "Edit / Delete"
        ]
    )

    # ========================================================
    # VIEW
    # ========================================================

    with tab1:

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Production CSV",
            production.to_csv(index=False).encode("utf-8"),
            "Production.csv",
            "text/csv"
        )

    # ========================================================
    # ADD
    # ========================================================

    with tab2:

        st.subheader("Add Production Record")

        item_options = []

        if not items.empty:
            item_options = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

        with st.form("add_production_form"):

            c1, c2 = st.columns(2)

            with c1:

                production_id = st.text_input(
                    "Production ID *",
                    placeholder="PRD-001"
                )

                item_id = st.selectbox(
                    "Item ID",
                    item_options
                    if item_options
                    else [""]
                )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001"
                )

                production_line = st.text_input(
                    "Production Line",
                    placeholder="Line 1"
                )

            with c2:

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

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
                        "Planned",
                        "In Progress",
                        "Completed",
                        "On Hold",
                        "Cancelled"
                    ]
                )

            submit = st.form_submit_button(
                "Add Production",
                type="primary"
            )

            if submit:

                if not production_id.strip():
                    st.error("Production ID is required.")

                elif (
                    not production.empty
                    and production_id.strip()
                    in production[
                        "Production_ID"
                    ].astype(str).values
                ):
                    st.error(
                        "This Production ID already exists."
                    )

                else:

                    record = {
                        "Production_ID":
                            production_id.strip(),

                        "Item_ID":
                            item_id,

                        "Production_Date":
                            production_date.isoformat(),

                        "Batch_No":
                            batch_no.strip(),

                        "Production_Line":
                            production_line.strip(),

                        "Planned_Qty_m":
                            planned_qty,

                        "Good_Qty_m":
                            good_qty,

                        "Rejected_Qty_m":
                            rejected_qty,

                        "Production_Status":
                            production_status
                    }

                    success, message = insert_record(
                        TABLES["Production"],
                        record
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # ========================================================
    # EDIT / DELETE
    # ========================================================

    with tab3:

        if production.empty:

            st.info("No production records available.")

        else:

            selected_id = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist()
            )

            row = production[
                production[
                    "Production_ID"
                ].astype(str)
                == selected_id
            ].iloc[0]

            st.subheader("Edit Production")

            with st.form("edit_production_form"):

                c1, c2 = st.columns(2)

                with c1:

                    item_options = (
                        items["Item_ID"]
                        .astype(str)
                        .tolist()
                        if not items.empty
                        else [str(row["Item_ID"])]
                    )

                    current_item = str(row["Item_ID"])

                    if current_item not in item_options:
                        item_options.append(current_item)

                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(
                            current_item
                        )
                    )

                    production_date_value = pd.to_datetime(
                        row["Production_Date"],
                        errors="coerce"
                    )

                    if pd.isna(production_date_value):
                        production_date_value = pd.Timestamp(
                            date.today()
                        )

                    production_date = st.date_input(
                        "Production Date",
                        value=production_date_value.date()
                    )

                    batch_no = st.text_input(
                        "Batch No",
                        value=str(row["Batch_No"])
                    )

                    production_line = st.text_input(
                        "Production Line",
                        value=str(
                            row["Production_Line"]
                        )
                    )

                with c2:

                    planned_qty = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0.0,
                        value=float(
                            row["Planned_Qty_m"]
                        )
                    )

                    good_qty = st.number_input(
                        "Good Quantity (m)",
                        min_value=0.0,
                        value=float(
                            row["Good_Qty_m"]
                        )
                    )

                    rejected_qty = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0.0,
                        value=float(
                            row["Rejected_Qty_m"]
                        )
                    )

                    status_options = [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "On Hold",
                        "Cancelled"
                    ]

                    current_status = str(
                        row["Production_Status"]
                    )

                    if current_status not in status_options:
                        status_options.append(
                            current_status
                        )

                    production_status = st.selectbox(
                        "Production Status",
                        status_options,
                        index=status_options.index(
                            current_status
                        )
                    )

                update_btn = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )

                if update_btn:

                    record = {
                        "Item_ID": item_id,
                        "Production_Date":
                            production_date.isoformat(),
                        "Batch_No":
                            batch_no.strip(),
                        "Production_Line":
                            production_line.strip(),
                        "Planned_Qty_m":
                            planned_qty,
                        "Good_Qty_m":
                            good_qty,
                        "Rejected_Qty_m":
                            rejected_qty,
                        "Production_Status":
                            production_status
                    }

                    success, message = update_record(
                        TABLES["Production"],
                        "Production_ID",
                        selected_id,
                        record
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            st.divider()

            st.subheader("Delete Production")

            if st.button(
                "Delete Selected Production",
                type="secondary"
            ):

                success, message = delete_record(
                    TABLES["Production"],
                    "Production_ID",
                    selected_id
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# ============================================================
# STOCK CONTROL
# ============================================================

def stock_control():

    page_header(
        "Stock Control",
        "Monitor opening stock, production, dispatch and closing inventory."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Stock Records",
            "Add Stock",
            "Edit / Delete"
        ]
    )

    # ========================================================
    # VIEW
    # ========================================================

    with tab1:

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Stock CSV",
            stock.to_csv(index=False).encode("utf-8"),
            "Stock_Control.csv",
            "text/csv"
        )

    # ========================================================
    # ADD
    # ========================================================

    with tab2:

        st.subheader("Add Stock Record")

        item_options = (
            items["Item_ID"]
            .astype(str)
            .tolist()
            if not items.empty
            else [""]
        )

        production_options = (
            production["Production_ID"]
            .astype(str)
            .tolist()
            if not production.empty
            else [""]
        )

        with st.form("add_stock_form"):

            c1, c2 = st.columns(2)

            with c1:

                stock_id = st.text_input(
                    "Stock ID *",
                    placeholder="STK-001"
                )

                item_id = st.selectbox(
                    "Item ID",
                    item_options
                )

                production_id = st.selectbox(
                    "Production ID",
                    production_options
                )

                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001"
                )

                stock_date = st.date_input(
                    "Stock Date",
                    value=date.today()
                )

            with c2:

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0.0,
                    step=1.0
                )

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

                closing_stock = (
                    opening_stock
                    + produced_qty
                    - dispatched_qty
                )

                st.metric(
                    "Calculated Closing Stock",
                    f"{closing_stock:,.2f} m"
                )

                stock_status = st.selectbox(
                    "Stock Status",
                    [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved"
                    ]
                )

            submit = st.form_submit_button(
                "Add Stock",
                type="primary"
            )

            if submit:

                if not stock_id.strip():

                    st.error(
                        "Stock ID is required."
                    )

                elif (
                    not stock.empty
                    and stock_id.strip()
                    in stock["Stock_ID"]
                    .astype(str)
                    .values
                ):

                    st.error(
                        "This Stock ID already exists."
                    )

                else:

                    record = {
                        "Stock_ID":
                            stock_id.strip(),

                        "Item_ID":
                            item_id,

                        "Production_ID":
                            production_id,

                        "Batch_No":
                            batch_no.strip(),

                        "Stock_Date":
                            stock_date.isoformat(),

                        "Opening_Stock_m":
                            opening_stock,

                        "Produced_Qty_m":
                            produced_qty,

                        "Dispatched_Qty_m":
                            dispatched_qty,

                        "Closing_Stock_m":
                            closing_stock,

                        "Stock_Status":
                            stock_status
                    }

                    success, message = insert_record(
                        TABLES["Stock Control"],
                        record
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # ========================================================
    # EDIT / DELETE
    # ========================================================

    with tab3:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            selected_id = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist()
            )

            row = stock[
                stock["Stock_ID"].astype(str)
                == selected_id
            ].iloc[0]

            st.subheader("Edit Stock")

            with st.form("edit_stock_form"):

                c1, c2 = st.columns(2)

                with c1:

                    item_options = (
                        items["Item_ID"]
                        .astype(str)
                        .tolist()
                        if not items.empty
                        else [str(row["Item_ID"])]
                    )

                    current_item = str(
                        row["Item_ID"]
                    )

                    if current_item not in item_options:
                        item_options.append(
                            current_item
                        )

                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(
                            current_item
                        )
                    )

                    production_options = (
                        production[
                            "Production_ID"
                        ]
                        .astype(str)
                        .tolist()
                        if not production.empty
                        else [str(row["Production_ID"])]
                    )

                    current_production = str(
                        row["Production_ID"]
                    )

                    if (
                        current_production
                        not in production_options
                    ):
                        production_options.append(
                            current_production
                        )

                    production_id = st.selectbox(
                        "Production ID",
                        production_options,
                        index=production_options.index(
                            current_production
                        )
                    )

                    batch_no = st.text_input(
                        "Batch No",
                        value=str(
                            row["Batch_No"]
                        )
                    )

                    stock_date_value = pd.to_datetime(
                        row["Stock_Date"],
                        errors="coerce"
                    )

                    if pd.isna(stock_date_value):
                        stock_date_value = pd.Timestamp(
                            date.today()
                        )

                    stock_date = st.date_input(
                        "Stock Date",
                        value=stock_date_value.date()
                    )

                with c2:

                    opening_stock = st.number_input(
                        "Opening Stock (m)",
                        min_value=0.0,
                        value=float(
                            row["Opening_Stock_m"]
                        )
                    )

                    produced_qty = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0.0,
                        value=float(
                            row["Produced_Qty_m"]
                        )
                    )

                    dispatched_qty = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0.0,
                        value=float(
                            row["Dispatched_Qty_m"]
                        )
                    )

                    closing_stock = (
                        opening_stock
                        + produced_qty
                        - dispatched_qty
                    )

                    st.metric(
                        "Calculated Closing Stock",
                        f"{closing_stock:,.2f} m"
                    )

                    status_options = [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved"
                    ]

                    current_status = str(
                        row["Stock_Status"]
                    )

                    if (
                        current_status
                        not in status_options
                    ):
                        status_options.append(
                            current_status
                        )

                    stock_status = st.selectbox(
                        "Stock Status",
                        status_options,
                        index=status_options.index(
                            current_status
                        )
                    )

                update_btn = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )

                if update_btn:

                    record = {
                        "Item_ID":
                            item_id,

                        "Production_ID":
                            production_id,

                        "Batch_No":
                            batch_no.strip(),

                        "Stock_Date":
                            stock_date.isoformat(),

                        "Opening_Stock_m":
                            opening_stock,

                        "Produced_Qty_m":
                            produced_qty,

                        "Dispatched_Qty_m":
                            dispatched_qty,

                        "Closing_Stock_m":
                            closing_stock,

                        "Stock_Status":
                            stock_status
                    }

                    success, message = update_record(
                        TABLES["Stock Control"],
                        "Stock_ID",
                        selected_id,
                        record
                    )

                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            st.divider()

            st.subheader("Delete Stock Record")

            if st.button(
                "Delete Selected Stock",
                type="secondary"
            ):

                success, message = delete_record(
                    TABLES["Stock Control"],
                    "Stock_ID",
                    selected_id
                )

                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# ============================================================
# CUSTOM DASHBOARD
# ============================================================

def custom_dashboard():

    page_header(
        "Custom Dashboard",
        "Build your own operational view using the available datasets."
    )

    dataset = st.selectbox(
        "Select Dataset",
        [
            "Items",
            "Production",
            "Stock Control"
        ]
    )

    if dataset == "Items":
        df = items.copy()

    elif dataset == "Production":
        df = production.copy()

    else:
        df = stock.copy()

    if df.empty:
        st.info("No data available.")
        return

    st.subheader("Dataset Preview")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Create Chart")

    chart_type = st.selectbox(
        "Chart Type",
        [
            "Bar Chart",
            "Line Chart",
            "Pie Chart"
        ]
    )

    columns = df.columns.tolist()

    if chart_type == "Bar Chart":

        c1, c2 = st.columns(2)

        with c1:
            x_col = st.selectbox(
                "X Axis",
                columns
            )

        with c2:

            numeric_cols = df.select_dtypes(
                include="number"
            ).columns.tolist()

            if numeric_cols:

                y_col = st.selectbox(
                    "Y Axis",
                    numeric_cols
                )

                fig = px.bar(
                    df,
                    x=x_col,
                    y=y_col,
                    title=f"{y_col} by {x_col}"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:
                st.warning(
                    "No numeric column available."
                )

    elif chart_type == "Line Chart":

        numeric_cols = df.select_dtypes(
            include="number"
        ).columns.tolist()

        if numeric_cols:

            x_col = st.selectbox(
                "X Axis",
                columns
            )

            y_col = st.selectbox(
                "Y Axis",
                numeric_cols
            )

            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                markers=True,
                title=f"{y_col} Trend"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:
            st.warning(
                "No numeric columns available."
            )

    else:

        category_cols = df.select_dtypes(
            exclude="number"
        ).columns.tolist()

        numeric_cols = df.select_dtypes(
            include="number"
        ).columns.tolist()

        if category_cols and numeric_cols:

            c1, c2 = st.columns(2)

            with c1:
                name_col = st.selectbox(
                    "Category",
                    category_cols
                )

            with c2:
                value_col = st.selectbox(
                    "Value",
                    numeric_cols
                )

            grouped = (
                df
                .groupby(name_col, as_index=False)
                [value_col]
                .sum()
            )

            fig = px.pie(
                grouped,
                names=name_col,
                values=value_col,
                hole=0.4
            )

            st.plotly_chart(
                fig,
                use_container_width=True
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
        "Detailed production and inventory performance analysis."
    )

    # ========================================================
    # PRODUCTION ANALYTICS
    # ========================================================

    st.subheader("Production Analytics")

    if production.empty:

        st.info("No production data available.")

    else:

        total_planned = production[
            "Planned_Qty_m"
        ].sum()

        total_good = production[
            "Good_Qty_m"
        ].sum()

        total_rejected = production[
            "Rejected_Qty_m"
        ].sum()

        total = total_good + total_rejected

        if total > 0:
            yield_rate = (
                total_good / total
            ) * 100
        else:
            yield_rate = 0

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Planned",
                f"{total_planned:,.0f} m"
            )

        with c2:
            st.metric(
                "Good",
                f"{total_good:,.0f} m"
            )

        with c3:
            st.metric(
                "Rejected",
                f"{total_rejected:,.0f} m"
            )

        with c4:
            st.metric(
                "Yield",
                f"{yield_rate:.2f}%"
            )

        st.divider()

        # Production by line

        line_data = (
            production
            .groupby("Production_Line")
            [
                [
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ]
            ]
            .sum()
            .reset_index()
        )

        line_long = line_data.melt(
            id_vars="Production_Line",
            var_name="Metric",
            value_name="Quantity"
        )

        fig = px.bar(
            line_long,
            x="Production_Line",
            y="Quantity",
            color="Metric",
            barmode="group",
            title="Production by Line"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # Yield by line

        line_yield = (
            production
            .groupby("Production_Line")
            [
                [
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ]
            ]
            .sum()
            .reset_index()
        )

        line_yield["Total"] = (
            line_yield["Good_Qty_m"]
            + line_yield["Rejected_Qty_m"]
        )

        line_yield["Yield_%"] = 0.0

        valid = line_yield["Total"] > 0

        line_yield.loc[
            valid,
            "Yield_%"
        ] = (
            line_yield.loc[
                valid,
                "Good_Qty_m"
            ]
            /
            line_yield.loc[
                valid,
                "Total"
            ]
            * 100
        )

        fig = px.bar(
            line_yield,
            x="Production_Line",
            y="Yield_%",
            text="Yield_%",
            title="Production Yield by Line"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # ========================================================
    # STOCK ANALYTICS
    # ========================================================

    st.subheader("Stock Analytics")

    if stock.empty:

        st.info("No stock data available.")

    else:

        stock_summary = (
            stock
            .groupby("Item_ID", as_index=False)
            [
                [
                    "Opening_Stock_m",
                    "Produced_Qty_m",
                    "Dispatched_Qty_m",
                    "Closing_Stock_m"
                ]
            ]
            .sum()
        )

        st.dataframe(
            stock_summary,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            stock_summary,
            x="Item_ID",
            y=[
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m"
            ],
            barmode="group",
            title="Inventory Movement by Item"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        status_summary = (
            stock
            .groupby("Stock_Status", as_index=False)
            ["Closing_Stock_m"]
            .sum()
        )

        fig = px.pie(
            status_summary,
            names="Stock_Status",
            values="Closing_Stock_m",
            hole=0.45,
            title="Stock Status Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

def data_management():

    page_header(
        "Data Management",
        "Review and export the ERP datasets."
    )

    st.subheader("Database Connection")

    if supabase:
        st.success(
            "Supabase connection is active."
        )
    else:
        st.warning(
            "Supabase is not connected. "
            "The application is using CSV files."
        )

    st.divider()

    # ========================================================
    # DATASET COUNTS
    # ========================================================

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Items",
            len(items)
        )

    with c2:
        st.metric(
            "Production Records",
            len(production)
        )

    with c3:
        st.metric(
            "Stock Records",
            len(stock)
        )

    st.divider()

    # ========================================================
    # DATASETS
    # ========================================================

    selected_dataset = st.selectbox(
        "Select Dataset",
        [
            "Items",
            "Production",
            "Stock Control"
        ]
    )

    if selected_dataset == "Items":
        df = items
        filename = "Item_Registration.csv"

    elif selected_dataset == "Production":
        df = production
        filename = "Production.csv"

    else:
        df = stock
        filename = "Stock_Control.csv"

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Dataset",
        df.to_csv(index=False).encode("utf-8"),
        filename,
        "text/csv"
    )

    st.divider()

    # ========================================================
    # REFRESH
    # ========================================================

    if st.button(
        "Refresh Data",
        type="primary"
    ):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# ROUTING
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
