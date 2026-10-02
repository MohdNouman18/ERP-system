import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# EXACT COLUMN STRUCTURE
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
# CSS
# ============================================================

def load_css():

    if os.path.exists("style.css"):

        with open(
            "style.css",
            "r",
            encoding="utf-8"
        ) as f:

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

        st.error(
            "Supabase package is not installed. "
            "Add supabase to requirements.txt."
        )

        return None

    try:

        # Streamlit Cloud secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")

        # Local environment fallback
        if not url:
            url = os.getenv("SUPABASE_URL")

        if not key:
            key = os.getenv("SUPABASE_KEY")

        if not url:

            st.error(
                "SUPABASE_URL is missing. "
                "Add it in Streamlit Secrets."
            )

            return None

        if not key:

            st.error(
                "SUPABASE_KEY is missing. "
                "Add it in Streamlit Secrets."
            )

            return None

        client = create_client(
            url,
            key
        )

        return client

    except Exception as e:

        st.error(
            f"Supabase connection failed: {e}"
        )

        return None


supabase = get_supabase()


# ============================================================
# DATA PREPARATION
# ============================================================

def ensure_columns(
    df,
    columns
):

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

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def safe_numeric(
    df,
    columns
):

    df = df.copy()

    for col in columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def prepare_dataframe(
    name,
    df
):

    if df is None:

        df = pd.DataFrame()

    df = df.copy()

    # --------------------------------------------------------
    # ITEMS
    # --------------------------------------------------------

    if name == "Items":

        df = ensure_columns(
            df,
            ITEM_COLUMNS
        )

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


    # --------------------------------------------------------
    # PRODUCTION
    # --------------------------------------------------------

    if name == "Production":

        df = ensure_columns(
            df,
            PRODUCTION_COLUMNS
        )

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


    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------

    if name == "Stock Control":

        df = ensure_columns(
            df,
            STOCK_COLUMNS
        )

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
# FETCH TABLE FROM SUPABASE
# ============================================================

def fetch_table(name):

    table_name = TABLES[name]

    if supabase is None:

        return prepare_dataframe(
            name,
            pd.DataFrame()
        )

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        data = response.data or []

        df = pd.DataFrame(data)

        return prepare_dataframe(
            name,
            df
        )

    except Exception as e:

        st.error(
            f"""
            Could not load `{table_name}` from Supabase.

            Error:
            {e}
            """
        )

        return prepare_dataframe(
            name,
            pd.DataFrame()
        )


# ============================================================
# LOAD DATA
# ============================================================

items = fetch_table("Items")

production = fetch_table("Production")

stock = fetch_table("Stock Control")


# ============================================================
# REFRESH DATA
# ============================================================

def refresh_app():

    st.cache_resource.clear()

    st.rerun()


# ============================================================
# CRUD FUNCTIONS
# ============================================================

def insert_record(
    table_name,
    record
):

    if supabase is None:

        return (
            False,
            "Supabase is not connected."
        )

    try:

        response = (
            supabase
            .table(table_name)
            .insert(record)
            .execute()
        )

        return (
            True,
            "Record added successfully."
        )

    except Exception as e:

        return (
            False,
            str(e)
        )


def update_record(
    table_name,
    primary_key,
    primary_value,
    record
):

    if supabase is None:

        return (
            False,
            "Supabase is not connected."
        )

    try:

        response = (
            supabase
            .table(table_name)
            .update(record)
            .eq(
                primary_key,
                primary_value
            )
            .execute()
        )

        return (
            True,
            "Record updated successfully."
        )

    except Exception as e:

        return (
            False,
            str(e)
        )


def delete_record(
    table_name,
    primary_key,
    primary_value
):

    if supabase is None:

        return (
            False,
            "Supabase is not connected."
        )

    try:

        response = (
            supabase
            .table(table_name)
            .delete()
            .eq(
                primary_key,
                primary_value
            )
            .execute()
        )

        return (
            True,
            "Record deleted successfully."
        )

    except Exception as e:

        return (
            False,
            str(e)
        )


# ============================================================
# FORMATTING
# ============================================================

def number(value):

    try:

        return f"{float(value):,.0f}"

    except Exception:

        return "0"


def decimal(value):

    try:

        return f"{float(value):,.2f}"

    except Exception:

        return "0.00"


def page_header(
    title,
    subtitle=""
):

    st.markdown(
        """
        <div class="page-kicker">
            FLEX HEAD INDUSTRIES
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title(title)

    if subtitle:

        st.caption(subtitle)


def metric_card(
    label,
    value,
    caption,
    icon
):

    st.markdown(
        f"""
        <div class="metric-card">

            <div class="metric-icon">
                {icon}
            </div>

            <div class="metric-label">
                {label}
            </div>

            <div class="metric-value">
                {value}
            </div>

            <div class="metric-caption">
                {caption}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


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

        st.success(
            "● Supabase Connected"
        )

    else:

        st.error(
            "● Supabase Not Connected"
        )

    st.caption(
        "Flex Head Industries ERP"
    )


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

def dashboard():

    page_header(
        "Executive Dashboard",
        "Real-time overview of manufacturing, production and inventory."
    )

    # ========================================================
    # KPI CALCULATIONS
    # ========================================================

    total_items = len(items)

    total_planned = (
        production["Planned_Qty_m"].sum()
        if not production.empty
        else 0
    )

    total_good = (
        production["Good_Qty_m"].sum()
        if not production.empty
        else 0
    )

    total_rejected = (
        production["Rejected_Qty_m"].sum()
        if not production.empty
        else 0
    )

    total_stock = (
        stock["Closing_Stock_m"].sum()
        if not stock.empty
        else 0
    )

    total_dispatched = (
        stock["Dispatched_Qty_m"].sum()
        if not stock.empty
        else 0
    )

    total_produced = (
        stock["Produced_Qty_m"].sum()
        if not stock.empty
        else 0
    )

    total_output = (
        total_good +
        total_rejected
    )

    if total_output > 0:

        yield_percent = (
            total_good /
            total_output
        ) * 100

    else:

        yield_percent = 0


    # ========================================================
    # KPI CARDS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        metric_card(
            "Registered Items",
            number(total_items),
            "Total product items",
            "▣"
        )

    with c2:

        metric_card(
            "Good Production",
            f"{number(total_good)} m",
            "Accepted production",
            "✓"
        )

    with c3:

        metric_card(
            "Current Stock",
            f"{number(total_stock)} m",
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


    st.markdown(
        '<div class="section-gap"></div>',
        unsafe_allow_html=True
    )


    # ========================================================
    # SECONDARY METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Planned Production",
            f"{number(total_planned)} m"
        )

    with c2:

        st.metric(
            "Rejected",
            f"{number(total_rejected)} m"
        )

    with c3:

        st.metric(
            "Produced / Stock",
            f"{number(total_produced)} m"
        )

    with c4:

        st.metric(
            "Dispatched",
            f"{number(total_dispatched)} m"
        )


    st.divider()


    # ========================================================
    # FILTERS
    # ========================================================

    st.subheader(
        "Production Overview"
    )

    col1, col2, col3 = st.columns(3)


    with col1:

        if not production.empty:

            lines = sorted(
                production[
                    "Production_Line"
                ]
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
                production[
                    "Production_Status"
                ]
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
                items[
                    "Item_ID"
                ]
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

        filtered_production = (
            filtered_production[
                filtered_production[
                    "Production_Line"
                ].astype(str)
                == selected_line
            ]
        )


    if selected_status != "All":

        filtered_production = (
            filtered_production[
                filtered_production[
                    "Production_Status"
                ].astype(str)
                == selected_status
            ]
        )


    if selected_item != "All":

        filtered_production = (
            filtered_production[
                filtered_production[
                    "Item_ID"
                ].astype(str)
                == selected_item
            ]
        )


    # ========================================================
    # CHARTS
    # ========================================================

    chart1, chart2 = st.columns(2)


    # --------------------------------------------------------
    # PRODUCTION TREND
    # --------------------------------------------------------

    with chart1:

        if not filtered_production.empty:

            trend = (
                filtered_production
                .groupby(
                    "Production_Date",
                    as_index=False
                )[
                    [
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ]
                ]
                .sum()
                .sort_values(
                    "Production_Date"
                )
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

            st.info(
                "No production data available."
            )


    # --------------------------------------------------------
    # PRODUCTION STATUS
    # --------------------------------------------------------

    with chart2:

        if not filtered_production.empty:

            status_data = (
                filtered_production
                .groupby(
                    "Production_Status",
                    as_index=False
                )[
                    "Good_Qty_m"
                ]
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

            st.info(
                "No production status data."
            )


    # ========================================================
    # STOCK BY ITEM
    # ========================================================

    st.subheader(
        "Current Stock by Item"
    )

    if not stock.empty:

        stock_chart = (
            stock
            .groupby(
                "Item_ID",
                as_index=False
            )[
                "Closing_Stock_m"
            ]
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

        st.info(
            "No stock data available."
        )


    # ========================================================
    # RECENT PRODUCTION
    # ========================================================

    st.subheader(
        "Recent Production"
    )

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

        st.info(
            "No production records found."
        )


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
    # VIEW ITEMS
    # ========================================================

    with tab1:

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download Items CSV",
            items.to_csv(
                index=False
            ).encode("utf-8"),
            "Item_Registration.csv",
            "text/csv"
        )


    # ========================================================
    # ADD ITEM
    # ========================================================

    with tab2:

        st.subheader(
            "Register New Item"
        )

        with st.form(
            "add_item_form"
        ):

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

                item_id = item_id.strip()


                if not item_id:

                    st.error(
                        "Item ID is required."
                    )

                elif (
                    not items.empty
                    and item_id
                    in items[
                        "Item_ID"
                    ].astype(str).values
                ):

                    st.error(
                        "This Item ID already exists."
                    )

                else:

                    record = {

                        "Item_ID":
                            item_id,

                        "Material_Grade":
                            material_grade.strip(),

                        "Application":
                            application.strip(),

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall,

                        "SDR":
                            sdr,

                        "Color":
                            color.strip(),

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit.strip()
                    }


                    success, message = insert_record(
                        TABLES["Items"],
                        record
                    )


                    if success:

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


    # ========================================================
    # EDIT / DELETE ITEM
    # ========================================================

    with tab3:

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            selected_id = st.selectbox(
                "Select Item",
                items[
                    "Item_ID"
                ].astype(str).tolist()
            )

            selected_row = (
                items[
                    items[
                        "Item_ID"
                    ].astype(str)
                    == selected_id
                ]
                .iloc[0]
            )


            st.subheader(
                "Edit Item"
            )


            with st.form(
                "edit_item_form"
            ):

                c1, c2 = st.columns(2)


                with c1:

                    material_grade = st.text_input(
                        "Material Grade",
                        value=str(
                            selected_row[
                                "Material_Grade"
                            ]
                        )
                    )

                    application = st.text_input(
                        "Application",
                        value=str(
                            selected_row[
                                "Application"
                            ]
                        )
                    )

                    diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Nominal_Diameter_mm"
                            ]
                        ),
                        step=1.0
                    )

                    wall = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Wall_Thickness_mm"
                            ]
                        ),
                        step=0.1
                    )


                with c2:

                    sdr = st.number_input(
                        "SDR",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "SDR"
                            ]
                        ),
                        step=0.1
                    )

                    color = st.text_input(
                        "Color",
                        value=str(
                            selected_row[
                                "Color"
                            ]
                        )
                    )

                    standard_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Standard_Length"
                            ]
                        ),
                        step=1.0
                    )

                    unit = st.text_input(
                        "Unit",
                        value=str(
                            selected_row[
                                "Unit"
                            ]
                        )
                    )


                update_btn = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


                if update_btn:

                    record = {

                        "Material_Grade":
                            material_grade.strip(),

                        "Application":
                            application.strip(),

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall,

                        "SDR":
                            sdr,

                        "Color":
                            color.strip(),

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit.strip()
                    }


                    success, message = update_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_id,
                        record
                    )


                    if success:

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


            st.divider()


            st.subheader(
                "Delete Item"
            )


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

                    st.success(
                        message
                    )

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(
                        message
                    )


# ============================================================
# PRODUCTION
# ============================================================

def production_page():

    page_header(
        "Production",
        "Manage daily pipe manufacturing and production batches."
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
            production.to_csv(
                index=False
            ).encode("utf-8"),
            "Production.csv",
            "text/csv"
        )


    # ========================================================
    # ADD
    # ========================================================

    with tab2:

        st.subheader(
            "Add Production Record"
        )


        item_options = (
            items[
                "Item_ID"
            ]
            .astype(str)
            .tolist()
            if not items.empty
            else [""]
        )


        with st.form(
            "add_production_form"
        ):

            c1, c2 = st.columns(2)


            with c1:

                production_id = st.text_input(
                    "Production ID *",
                    placeholder="PRD-001"
                )

                item_id = st.selectbox(
                    "Item ID",
                    item_options
                )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

                batch_no = st.text_input(
                    "Batch No",
                    placeholder="BATCH-001"
                )


            with c2:

                production_line = st.text_input(
                    "Production Line",
                    placeholder="Line 1"
                )

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
                        "Rejected",
                        "On Hold"
                    ]
                )


            submit = st.form_submit_button(
                "Add Production",
                type="primary"
            )


            if submit:

                production_id = production_id.strip()


                if not production_id:

                    st.error(
                        "Production ID is required."
                    )

                elif (
                    not production.empty
                    and production_id
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
                            production_id,

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

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


    # ========================================================
    # EDIT / DELETE
    # ========================================================

    with tab3:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            selected_id = st.selectbox(
                "Select Production",
                production[
                    "Production_ID"
                ].astype(str).tolist()
            )


            selected_row = (
                production[
                    production[
                        "Production_ID"
                    ].astype(str)
                    == selected_id
                ]
                .iloc[0]
            )


            st.subheader(
                "Edit Production"
            )


            item_options = (
                items[
                    "Item_ID"
                ]
                .astype(str)
                .tolist()
                if not items.empty
                else [""]
            )


            current_item = str(
                selected_row[
                    "Item_ID"
                ]
            )


            if current_item not in item_options:

                item_options = (
                    [current_item]
                    + item_options
                )


            current_date = (
                pd.to_datetime(
                    selected_row[
                        "Production_Date"
                    ],
                    errors="coerce"
                )
            )


            if pd.isna(current_date):

                current_date = pd.Timestamp.today()


            with st.form(
                "edit_production_form"
            ):

                c1, c2 = st.columns(2)


                with c1:

                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(
                            current_item
                        )
                    )

                    production_date = st.date_input(
                        "Production Date",
                        value=current_date.date()
                    )

                    batch_no = st.text_input(
                        "Batch No",
                        value=str(
                            selected_row[
                                "Batch_No"
                            ]
                        )
                    )

                    production_line = st.text_input(
                        "Production Line",
                        value=str(
                            selected_row[
                                "Production_Line"
                            ]
                        )
                    )


                with c2:

                    planned_qty = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Planned_Qty_m"
                            ]
                        ),
                        step=1.0
                    )

                    good_qty = st.number_input(
                        "Good Quantity (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Good_Qty_m"
                            ]
                        ),
                        step=1.0
                    )

                    rejected_qty = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Rejected_Qty_m"
                            ]
                        ),
                        step=1.0
                    )

                    statuses = [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected",
                        "On Hold"
                    ]

                    current_status = str(
                        selected_row[
                            "Production_Status"
                        ]
                    )

                    if current_status not in statuses:

                        statuses.append(
                            current_status
                        )

                    production_status = st.selectbox(
                        "Production Status",
                        statuses,
                        index=statuses.index(
                            current_status
                        )
                    )


                update_btn = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


                if update_btn:

                    record = {

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


                    success, message = update_record(
                        TABLES["Production"],
                        "Production_ID",
                        selected_id,
                        record
                    )


                    if success:

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


            st.divider()


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

                    st.success(
                        message
                    )

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(
                        message
                    )


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
            stock.to_csv(
                index=False
            ).encode("utf-8"),
            "Stock_Control.csv",
            "text/csv"
        )


    # ========================================================
    # ADD STOCK
    # ========================================================

    with tab2:

        st.subheader(
            "Add Stock Record"
        )


        item_options = (
            items[
                "Item_ID"
            ]
            .astype(str)
            .tolist()
            if not items.empty
            else [""]
        )


        production_options = (
            production[
                "Production_ID"
            ]
            .astype(str)
            .tolist()
            if not production.empty
            else [""]
        )


        with st.form(
            "add_stock_form"
        ):

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

                stock_id = stock_id.strip()


                if not stock_id:

                    st.error(
                        "Stock ID is required."
                    )

                elif (
                    not stock.empty
                    and stock_id
                    in stock[
                        "Stock_ID"
                    ].astype(str).values
                ):

                    st.error(
                        "This Stock ID already exists."
                    )

                else:

                    record = {

                        "Stock_ID":
                            stock_id,

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

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


    # ========================================================
    # EDIT / DELETE STOCK
    # ========================================================

    with tab3:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            selected_id = st.selectbox(
                "Select Stock Record",
                stock[
                    "Stock_ID"
                ].astype(str).tolist()
            )


            selected_row = (
                stock[
                    stock[
                        "Stock_ID"
                    ].astype(str)
                    == selected_id
                ]
                .iloc[0]
            )


            st.subheader(
                "Edit Stock"
            )


            item_options = (
                items[
                    "Item_ID"
                ]
                .astype(str)
                .tolist()
                if not items.empty
                else [""]
            )


            production_options = (
                production[
                    "Production_ID"
                ]
                .astype(str)
                .tolist()
                if not production.empty
                else [""]
            )


            current_item = str(
                selected_row["Item_ID"]
            )

            current_production = str(
                selected_row["Production_ID"]
            )


            if current_item not in item_options:

                item_options = (
                    [current_item]
                    + item_options
                )


            if current_production not in production_options:

                production_options = (
                    [current_production]
                    + production_options
                )


            current_date = pd.to_datetime(
                selected_row["Stock_Date"],
                errors="coerce"
            )


            if pd.isna(current_date):

                current_date = pd.Timestamp.today()


            with st.form(
                "edit_stock_form"
            ):

                c1, c2 = st.columns(2)


                with c1:

                    item_id = st.selectbox(
                        "Item ID",
                        item_options,
                        index=item_options.index(
                            current_item
                        )
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
                            selected_row[
                                "Batch_No"
                            ]
                        )
                    )

                    stock_date = st.date_input(
                        "Stock Date",
                        value=current_date.date()
                    )


                with c2:

                    opening_stock = st.number_input(
                        "Opening Stock (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Opening_Stock_m"
                            ]
                        ),
                        step=1.0
                    )

                    produced_qty = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Produced_Qty_m"
                            ]
                        ),
                        step=1.0
                    )

                    dispatched_qty = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0.0,
                        value=float(
                            selected_row[
                                "Dispatched_Qty_m"
                            ]
                        ),
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


                    statuses = [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved"
                    ]

                    current_status = str(
                        selected_row[
                            "Stock_Status"
                        ]
                    )

                    if current_status not in statuses:

                        statuses.append(
                            current_status
                        )

                    stock_status = st.selectbox(
                        "Stock Status",
                        statuses,
                        index=statuses.index(
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

                        st.success(
                            message
                        )

                        st.cache_resource.clear()

                        st.rerun()

                    else:

                        st.error(
                            message
                        )


            st.divider()


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

                    st.success(
                        message
                    )

                    st.cache_resource.clear()

                    st.rerun()

                else:

                    st.error(
                        message
                    )


# ============================================================
# CUSTOM DASHBOARD
# ============================================================

def custom_dashboard():

    page_header(
        "Custom Dashboard",
        "Create quick visual analysis from ERP datasets."
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

        st.warning(
            "No data available for this dataset."
        )

        return


    st.subheader(
        "Dataset Preview"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    st.divider()


    # ========================================================
    # PRODUCTION CUSTOM CHART
    # ========================================================

    if dataset == "Production":

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Production by Line",
                "Production by Status",
                "Production by Item",
                "Good vs Rejected",
                "Planned vs Good"
            ]
        )


        if chart_type == "Production by Line":

            data = (
                df.groupby(
                    "Production_Line",
                    as_index=False
                )[
                    "Good_Qty_m"
                ]
                .sum()
            )

            fig = px.bar(
                data,
                x="Production_Line",
                y="Good_Qty_m",
                text_auto=".0f",
                title="Good Production by Line"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Production by Status":

            data = (
                df.groupby(
                    "Production_Status",
                    as_index=False
                )[
                    "Good_Qty_m"
                ]
                .sum()
            )

            fig = px.pie(
                data,
                names="Production_Status",
                values="Good_Qty_m",
                hole=0.4,
                title="Production Status"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Production by Item":

            data = (
                df.groupby(
                    "Item_ID",
                    as_index=False
                )[
                    "Good_Qty_m"
                ]
                .sum()
                .sort_values(
                    "Good_Qty_m",
                    ascending=False
                )
            )

            fig = px.bar(
                data,
                x="Item_ID",
                y="Good_Qty_m",
                text_auto=".0f",
                title="Good Production by Item"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Good vs Rejected":

            good = df[
                "Good_Qty_m"
            ].sum()

            rejected = df[
                "Rejected_Qty_m"
            ].sum()

            chart_df = pd.DataFrame(
                {
                    "Type": [
                        "Good",
                        "Rejected"
                    ],
                    "Quantity": [
                        good,
                        rejected
                    ]
                }
            )

            fig = px.pie(
                chart_df,
                names="Type",
                values="Quantity",
                hole=0.45,
                title="Good vs Rejected"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        else:

            chart_df = pd.DataFrame(
                {
                    "Metric": [
                        "Planned",
                        "Good"
                    ],
                    "Quantity": [
                        df[
                            "Planned_Qty_m"
                        ].sum(),

                        df[
                            "Good_Qty_m"
                        ].sum()
                    ]
                }
            )

            fig = px.bar(
                chart_df,
                x="Metric",
                y="Quantity",
                text_auto=".0f",
                title="Planned vs Good Production"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # STOCK CUSTOM CHART
    # ========================================================

    elif dataset == "Stock Control":

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Closing Stock",
                "Produced vs Dispatched",
                "Stock by Status"
            ]
        )


        if chart_type == "Closing Stock":

            data = (
                df.groupby(
                    "Item_ID",
                    as_index=False
                )[
                    "Closing_Stock_m"
                ]
                .sum()
                .sort_values(
                    "Closing_Stock_m",
                    ascending=False
                )
            )

            fig = px.bar(
                data,
                x="Item_ID",
                y="Closing_Stock_m",
                text_auto=".0f",
                title="Closing Stock by Item"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Produced vs Dispatched":

            data = (
                df.groupby(
                    "Item_ID",
                    as_index=False
                )[
                    [
                        "Produced_Qty_m",
                        "Dispatched_Qty_m"
                    ]
                ]
                .sum()
            )

            data = data.melt(
                id_vars="Item_ID",
                var_name="Metric",
                value_name="Quantity"
            )

            fig = px.bar(
                data,
                x="Item_ID",
                y="Quantity",
                color="Metric",
                barmode="group",
                title="Produced vs Dispatched"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        else:

            data = (
                df.groupby(
                    "Stock_Status",
                    as_index=False
                )[
                    "Closing_Stock_m"
                ]
                .sum()
            )

            fig = px.pie(
                data,
                names="Stock_Status",
                values="Closing_Stock_m",
                hole=0.45,
                title="Stock Status"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # ITEMS CUSTOM CHART
    # ========================================================

    else:

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Items by Material Grade",
                "Items by Application",
                "Items by Color",
                "Diameter Distribution"
            ]
        )


        if chart_type == "Items by Material Grade":

            data = (
                df.groupby(
                    "Material_Grade",
                    as_index=False
                )
                .size()
                .rename(
                    columns={
                        "size": "Count"
                    }
                )
            )

            fig = px.bar(
                data,
                x="Material_Grade",
                y="Count",
                text_auto=True,
                title="Items by Material Grade"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Items by Application":

            data = (
                df.groupby(
                    "Application",
                    as_index=False
                )
                .size()
                .rename(
                    columns={
                        "size": "Count"
                    }
                )
            )

            fig = px.pie(
                data,
                names="Application",
                values="Count",
                hole=0.45,
                title="Items by Application"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        elif chart_type == "Items by Color":

            data = (
                df.groupby(
                    "Color",
                    as_index=False
                )
                .size()
                .rename(
                    columns={
                        "size": "Count"
                    }
                )
            )

            fig = px.bar(
                data,
                x="Color",
                y="Count",
                text_auto=True,
                title="Items by Color"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        else:

            fig = px.histogram(
                df,
                x="Nominal_Diameter_mm",
                nbins=15,
                title="Nominal Diameter Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# ============================================================
# ANALYTICS
# ============================================================

def analytics():

    page_header(
        "Analytics",
        "Detailed production, inventory and operational analysis."
    )


    # ========================================================
    # PRODUCTION ANALYTICS
    # ========================================================

    st.subheader(
        "Production Analytics"
    )


    if production.empty:

        st.info(
            "No production data available."
        )

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

        total_output = (
            total_good +
            total_rejected
        )

        if total_output > 0:

            overall_yield = (
                total_good /
                total_output
            ) * 100

        else:

            overall_yield = 0


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
                f"{overall_yield:.1f}%"
            )


        st.divider()


        # ----------------------------------------------------
        # PRODUCTION BY LINE
        # ----------------------------------------------------

        line_summary = (
            production
            .groupby(
                "Production_Line",
                as_index=False
            )[
                [
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ]
            ]
            .sum()
        )


        st.subheader(
            "Production by Line"
        )


        st.dataframe(
            line_summary,
            use_container_width=True,
            hide_index=True
        )


        fig = px.bar(
            line_summary,
            x="Production_Line",
            y=[
                "Planned_Qty_m",
                "Good_Qty_m",
                "Rejected_Qty_m"
            ],
            barmode="group",
            title="Production Performance by Line"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


        # ----------------------------------------------------
        # YIELD BY LINE
        # ----------------------------------------------------

        line_yield = (
            production
            .groupby(
                "Production_Line",
                as_index=False
            )[
                [
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ]
            ]
            .sum()
        )


        line_yield["Total"] = (
            line_yield[
                "Good_Qty_m"
            ]
            +
            line_yield[
                "Rejected_Qty_m"
            ]
        )


        valid = (
            line_yield["Total"] > 0
        )


        line_yield["Yield_%"] = 0.0


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

    st.subheader(
        "Stock Analytics"
    )


    if stock.empty:

        st.info(
            "No stock data available."
        )

    else:

        stock_summary = (
            stock
            .groupby(
                "Item_ID",
                as_index=False
            )[
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
            .groupby(
                "Stock_Status",
                as_index=False
            )[
                "Closing_Stock_m"
            ]
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
        "Review database connection and ERP datasets."
    )


    # ========================================================
    # CONNECTION STATUS
    # ========================================================

    st.subheader(
        "Database Connection"
    )


    if supabase:

        st.success(
            "Supabase connection is active."
        )

    else:

        st.error(
            "Supabase is NOT connected."
        )

        st.info(
            """
            Make sure SUPABASE_URL and SUPABASE_KEY
            are configured in Streamlit Secrets.
            """
        )


    st.divider()


    # ========================================================
    # COUNTS
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
    # DATASET
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

        filename = (
            "Item_Registration.csv"
        )


    elif selected_dataset == "Production":

        df = production

        filename = (
            "Production.csv"
        )


    else:

        df = stock

        filename = (
            "Stock_Control.csv"
        )


    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


    st.download_button(
        "Download Dataset",
        df.to_csv(
            index=False
        ).encode("utf-8"),
        filename,
        "text/csv"
    )


    st.divider()


    # ========================================================
    # REFRESH
    # ========================================================

    if st.button(
        "Refresh Database Data",
        type="primary"
    ):

        st.cache_resource.clear()

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
