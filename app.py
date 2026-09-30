import os
import base64
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Flex Head Industry | ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# SUPABASE TABLE NAMES
# THESE MUST MATCH SUPABASE EXACTLY
# =========================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock Control": "Stock_Control"
}


# =========================================================
# EXPECTED COLUMNS
# =========================================================

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


# =========================================================
# CSS
# =========================================================

def load_css():

    css_path = os.path.join(
        os.path.dirname(__file__),
        "style.css"
    )

    if os.path.exists(css_path):

        with open(
            css_path,
            "r",
            encoding="utf-8"
        ) as f:

            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )


load_css()


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_supabase():

    if create_client is None:
        return None

    try:

        url = None
        key = None

        # Streamlit Cloud secrets
        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass

        # Local environment variables
        if not url:
            url = os.getenv("SUPABASE_URL")

        if not key:
            key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            return None

        return create_client(
            url,
            key
        )

    except Exception:

        return None


supabase = get_supabase()


# =========================================================
# SIDEBAR BRAND
# =========================================================

def sidebar_brand():

    logo_path = os.path.join(
        os.path.dirname(__file__),
        "logo.png"
    )

    if os.path.exists(logo_path):

        try:

            with open(
                logo_path,
                "rb"
            ) as image_file:

                logo_base64 = base64.b64encode(
                    image_file.read()
                ).decode()

            logo_html = f"""
            <img
                src="data:image/png;base64,{logo_base64}"
                class="company-logo"
            >
            """

        except Exception:

            logo_html = """
            <div class="brand-mark">
                FH
            </div>
            """

    else:

        logo_html = """
        <div class="brand-mark">
            FH
        </div>
        """

    st.sidebar.markdown(
        f"""
        <div class="brand">

            {logo_html}

            <div>

                <div class="brand-name">
                    FLEX HEAD
                </div>

                <div class="brand-sub">
                    INDUSTRY PVT LTD
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


sidebar_brand()


# =========================================================
# NAVIGATION
# =========================================================

st.sidebar.markdown(
    "### ERP MODULES"
)

page = st.sidebar.radio(
    "",
    [
        "Executive Dashboard",
        "Item Registration",
        "Production",
        "Stock Control",
        "Custom Analytics",
        "Data Management"
    ]
)


# =========================================================
# GENERAL FUNCTIONS
# =========================================================

def page_header(
    kicker,
    title,
    description=""
):

    st.markdown(
        f"""
        <div class="page-kicker">
            {kicker}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title(title)

    if description:

        st.caption(description)


def ensure_columns(
    df,
    columns
):

    if df is None:

        df = pd.DataFrame()

    df = df.copy()

    for column in columns:

        if column not in df.columns:

            df[column] = None

    return df


def clean_text_columns(
    df,
    columns
):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def convert_numeric_columns(
    df,
    columns
):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


def convert_date_columns(
    df,
    columns
):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                errors="coerce"
            )

    return df


def safe_float(value):

    try:

        if pd.isna(value):
            return 0.0

        return float(value)

    except Exception:

        return 0.0


# =========================================================
# FETCH DATA FROM SUPABASE
# =========================================================

def fetch_table(module):

    if supabase is None:

        return pd.DataFrame()

    table_name = TABLES[module]

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        if response.data is None:

            return pd.DataFrame()

        return pd.DataFrame(
            response.data
        )

    except Exception as e:

        st.error(
            f"Supabase error in {module}: {e}"
        )

        return pd.DataFrame()


# =========================================================
# CRUD
# =========================================================

def insert_record(
    module,
    data
):

    if supabase is None:

        return (
            False,
            "Supabase connection is not available."
        )

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .insert(data)
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
    module,
    record_id,
    id_column,
    data
):

    if supabase is None:

        return (
            False,
            "Supabase connection is not available."
        )

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .update(data)
            .eq(
                id_column,
                record_id
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
    module,
    record_id,
    id_column
):

    if supabase is None:

        return (
            False,
            "Supabase connection is not available."
        )

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .delete()
            .eq(
                id_column,
                record_id
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


# =========================================================
# LOAD DATABASE
# =========================================================

items = fetch_table("Items")

production = fetch_table("Production")

stock = fetch_table("Stock Control")


# =========================================================
# PREPARE ITEMS
# =========================================================

items = ensure_columns(
    items,
    ITEM_COLUMNS
)

items = clean_text_columns(
    items,
    [
        "Item_ID",
        "Item_Code",
        "Material_Grade",
        "Application",
        "SDR",
        "Color",
        "Unit"
    ]
)

items = convert_numeric_columns(
    items,
    [
        "Nominal_Diameter_mm",
        "Wall_Thickness_mm",
        "Standard_Length"
    ]
)


# =========================================================
# PREPARE PRODUCTION
# =========================================================

production = ensure_columns(
    production,
    PRODUCTION_COLUMNS
)

production = clean_text_columns(
    production,
    [
        "Production_ID",
        "Item_ID",
        "Batch_No",
        "Production_Line",
        "Production_Status"
    ]
)

production = convert_numeric_columns(
    production,
    [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]
)

production = convert_date_columns(
    production,
    [
        "Production_Date"
    ]
)


# =========================================================
# PREPARE STOCK
# =========================================================

stock = ensure_columns(
    stock,
    STOCK_COLUMNS
)

stock = clean_text_columns(
    stock,
    [
        "Stock_ID",
        "Item_ID",
        "Production_ID",
        "Batch_No",
        "Stock_Status"
    ]
)

stock = convert_numeric_columns(
    stock,
    [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]
)

stock = convert_date_columns(
    stock,
    [
        "Stock_Date"
    ]
)


# =========================================================
# DASHBOARD
# =========================================================

def dashboard():

    page_header(
        "EXECUTIVE OVERVIEW",
        "ERP Dashboard",
        "Flex Head Industry Pvt Ltd — Manufacturing & Inventory Overview"
    )

    # -----------------------------------------------------
    # KPI VALUES
    # -----------------------------------------------------

    total_items = len(items)

    total_good = (
        production["Good_Qty_m"]
        .fillna(0)
        .sum()
    )

    total_rejected = (
        production["Rejected_Qty_m"]
        .fillna(0)
        .sum()
    )

    total_stock = (
        stock["Closing_Stock_m"]
        .fillna(0)
        .sum()
    )

    total_dispatched = (
        stock["Dispatched_Qty_m"]
        .fillna(0)
        .sum()
    )

    total_production = (
        production["Planned_Qty_m"]
        .fillna(0)
        .sum()
    )

    total_output = (
        total_good + total_rejected
    )

    if total_output > 0:

        yield_rate = (
            total_good /
            total_output
        ) * 100

    else:

        yield_rate = 0


    # -----------------------------------------------------
    # KPI CARDS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ◈
                </div>

                <div class="metric-label">
                    REGISTERED ITEMS
                </div>

                <div class="metric-value">
                    {total_items}
                </div>

                <div class="metric-caption">
                    Product catalogue
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c2:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ▣
                </div>

                <div class="metric-label">
                    GOOD PRODUCTION
                </div>

                <div class="metric-value">
                    {total_good:,.0f} m
                </div>

                <div class="metric-caption">
                    Total accepted production
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c3:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ◉
                </div>

                <div class="metric-label">
                    CURRENT STOCK
                </div>

                <div class="metric-value">
                    {total_stock:,.0f} m
                </div>

                <div class="metric-caption">
                    Closing inventory
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with c4:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    %
                </div>

                <div class="metric-label">
                    PRODUCTION YIELD
                </div>

                <div class="metric-value">
                    {yield_rate:.1f}%
                </div>

                <div class="metric-caption">
                    Good vs rejected
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown(
        '<div class="section-gap"></div>',
        unsafe_allow_html=True
    )


    # =====================================================
    # CHART 1 — PRODUCTION TREND
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "Production Trend"
        )

        if not production.empty:

            trend = production.copy()

            trend = trend.dropna(
                subset=[
                    "Production_Date"
                ]
            )

            if not trend.empty:

                trend = (
                    trend
                    .groupby(
                        "Production_Date",
                        as_index=False
                    )[
                        "Good_Qty_m"
                    ]
                    .sum()
                )

                fig = px.line(
                    trend,
                    x="Production_Date",
                    y="Good_Qty_m",
                    markers=True,
                    template="plotly_white"
                )

                fig.update_layout(
                    height=360,
                    xaxis_title="Production Date",
                    yaxis_title="Good Production (m)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "Production records exist, but no valid production dates were found."
                )

        else:

            st.info(
                "No production data available."
            )


    # =====================================================
    # CHART 2 — PRODUCTION STATUS
    # =====================================================

    with col2:

        st.subheader(
            "Production Status"
        )

        if not production.empty:

            status_df = production.copy()

            status_df[
                "Production_Status"
            ] = (
                status_df[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .replace("", "Unknown")
            )

            status = (
                status_df
                .groupby(
                    "Production_Status"
                )
                .size()
                .reset_index(
                    name="Count"
                )
            )

            if not status.empty:

                fig = px.pie(
                    status,
                    names="Production_Status",
                    values="Count",
                    hole=0.45,
                    template="plotly_white"
                )

                fig.update_layout(
                    height=360
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "No production status data available."
                )

        else:

            st.info(
                "No production data available."
            )


    # =====================================================
    # CHART 3 — STOCK BY ITEM
    # =====================================================

    col3, col4 = st.columns(2)

    with col3:

        st.subheader(
            "Stock by Item"
        )

        if not stock.empty:

            stock_chart = stock.copy()

            stock_chart[
                "Item_ID"
            ] = (
                stock_chart[
                    "Item_ID"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            stock_chart[
                "Closing_Stock_m"
            ] = pd.to_numeric(
                stock_chart[
                    "Closing_Stock_m"
                ],
                errors="coerce"
            ).fillna(0)


            # Create Item Code lookup
            item_lookup = items[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].copy()


            item_lookup[
                "Item_ID"
            ] = (
                item_lookup[
                    "Item_ID"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )


            item_lookup = (
                item_lookup
                .drop_duplicates(
                    subset=[
                        "Item_ID"
                    ]
                )
            )


            stock_chart = stock_chart.merge(
                item_lookup,
                on="Item_ID",
                how="left"
            )


            stock_chart[
                "Display_Item"
            ] = stock_chart[
                "Item_Code"
            ].fillna("")


            stock_chart[
                "Display_Item"
            ] = stock_chart[
                "Display_Item"
            ].where(
                stock_chart[
                    "Display_Item"
                ].str.strip() != "",
                stock_chart[
                    "Item_ID"
                ]
            )


            stock_chart = (
                stock_chart
                .groupby(
                    "Display_Item",
                    as_index=False
                )[
                    "Closing_Stock_m"
                ]
                .sum()
            )


            if not stock_chart.empty:

                fig = px.bar(
                    stock_chart,
                    x="Display_Item",
                    y="Closing_Stock_m",
                    text_auto=".2s",
                    template="plotly_white"
                )

                fig.update_layout(
                    height=360,
                    xaxis_title="Item",
                    yaxis_title="Closing Stock (m)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "No stock quantities available."
                )

        else:

            st.info(
                "No stock data available."
            )


    # =====================================================
    # CHART 4 — PRODUCTION QUALITY
    # =====================================================

    with col4:

        st.subheader(
            "Production Quality"
        )

        quality = pd.DataFrame(
            {
                "Category": [
                    "Good",
                    "Rejected"
                ],
                "Quantity": [
                    total_good,
                    total_rejected
                ]
            }
        )

        fig = px.bar(
            quality,
            x="Category",
            y="Quantity",
            text_auto=".2s",
            template="plotly_white"
        )

        fig.update_layout(
            height=360,
            xaxis_title="",
            yaxis_title="Quantity (m)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # =====================================================
    # EXTRA KPIs
    # =====================================================

    st.subheader(
        "Operational Summary"
    )

    a1, a2, a3 = st.columns(3)

    with a1:

        st.metric(
            "Planned Production",
            f"{total_production:,.0f} m"
        )

    with a2:

        st.metric(
            "Dispatched",
            f"{total_dispatched:,.0f} m"
        )

    with a3:

        st.metric(
            "Rejected",
            f"{total_rejected:,.0f} m"
        )


    # =====================================================
    # RECENT PRODUCTION
    # =====================================================

    st.subheader(
        "Recent Production"
    )

    if not production.empty:

        recent = production.copy()

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


# =========================================================
# ITEM REGISTRATION
# =========================================================

def item_registration():

    page_header(
        "MASTER DATA",
        "Item Registration",
        "Manage pipe products and technical specifications."
    )


    add_tab, edit_tab, delete_tab = st.tabs(
        [
            "Add Item",
            "Edit Item",
            "Delete Item"
        ]
    )


    # =====================================================
    # ADD
    # =====================================================

    with add_tab:

        st.subheader(
            "Register New Item"
        )

        with st.form(
            "add_item_form"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                item_id = st.text_input(
                    "Item ID",
                    placeholder="ITM-008"
                )

                item_code = st.text_input(
                    "Item Code",
                    placeholder="PE100-WTR-315-SDR17"
                )

                material_grade = st.selectbox(
                    "Material Grade",
                    [
                        "PE-80",
                        "PE-100"
                    ]
                )


            with c2:

                application = st.selectbox(
                    "Application",
                    [
                        "Water",
                        "Sewerage",
                        "Gas",
                        "Industrial",
                        "Other"
                    ]
                )

                nominal_diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=0.1
                )

                wall_thickness = st.number_input(
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


            submit = st.form_submit_button(
                "Add Item",
                type="primary",
                use_container_width=True
            )


        if submit:

            if not item_id.strip():

                st.error(
                    "Item ID is required."
                )

            elif not item_code.strip():

                st.error(
                    "Item Code is required."
                )

            else:

                data = {

                    "Item_ID":
                        item_id.strip(),

                    "Item_Code":
                        item_code.strip(),

                    "Material_Grade":
                        material_grade,

                    "Application":
                        application,

                    "Nominal_Diameter_mm":
                        nominal_diameter,

                    "Wall_Thickness_mm":
                        wall_thickness,

                    "SDR":
                        sdr.strip(),

                    "Color":
                        color.strip(),

                    "Standard_Length":
                        standard_length,

                    "Unit":
                        unit.strip()
                }

                success, message = insert_record(
                    "Items",
                    data
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    # =====================================================
    # EDIT
    # =====================================================

    with edit_tab:

        st.subheader(
            "Edit Item"
        )

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            item_ids = items[
                "Item_ID"
            ].tolist()

            selected_id = st.selectbox(
                "Select Item",
                item_ids,
                key="edit_item_select"
            )

            selected = items[
                items["Item_ID"]
                == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                with st.form(
                    "edit_item_form"
                ):

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        edit_code = st.text_input(
                            "Item Code",
                            value=str(
                                row["Item_Code"]
                            )
                        )

                        edit_grade = st.text_input(
                            "Material Grade",
                            value=str(
                                row["Material_Grade"]
                            )
                        )

                        edit_application = st.text_input(
                            "Application",
                            value=str(
                                row["Application"]
                            )
                        )


                    with c2:

                        edit_diameter = st.number_input(
                            "Nominal Diameter (mm)",
                            value=safe_float(
                                row[
                                    "Nominal_Diameter_mm"
                                ]
                            ),
                            step=0.1
                        )

                        edit_wall = st.number_input(
                            "Wall Thickness (mm)",
                            value=safe_float(
                                row[
                                    "Wall_Thickness_mm"
                                ]
                            ),
                            step=0.1
                        )

                        edit_sdr = st.text_input(
                            "SDR",
                            value=str(
                                row["SDR"]
                            )
                        )


                    with c3:

                        edit_color = st.text_input(
                            "Color",
                            value=str(
                                row["Color"]
                            )
                        )

                        edit_length = st.number_input(
                            "Standard Length",
                            value=safe_float(
                                row[
                                    "Standard_Length"
                                ]
                            ),
                            step=1.0
                        )

                        edit_unit = st.text_input(
                            "Unit",
                            value=str(
                                row["Unit"]
                            )
                        )


                    update = st.form_submit_button(
                        "Update Item",
                        type="primary",
                        use_container_width=True
                    )


                if update:

                    data = {

                        "Item_Code":
                            edit_code.strip(),

                        "Material_Grade":
                            edit_grade.strip(),

                        "Application":
                            edit_application.strip(),

                        "Nominal_Diameter_mm":
                            edit_diameter,

                        "Wall_Thickness_mm":
                            edit_wall,

                        "SDR":
                            edit_sdr.strip(),

                        "Color":
                            edit_color.strip(),

                        "Standard_Length":
                            edit_length,

                        "Unit":
                            edit_unit.strip()
                    }

                    success, message = update_record(
                        "Items",
                        selected_id,
                        "Item_ID",
                        data
                    )

                    if success:

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)


    # =====================================================
    # DELETE
    # =====================================================

    with delete_tab:

        st.subheader(
            "Delete Item"
        )

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            delete_id = st.selectbox(
                "Select Item",
                items[
                    "Item_ID"
                ].tolist(),
                key="delete_item_select"
            )

            if st.button(
                "Delete Item",
                type="primary"
            ):

                success, message = delete_record(
                    "Items",
                    delete_id,
                    "Item_ID"
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    st.divider()

    st.subheader(
        "Registered Items"
    )

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# PRODUCTION PAGE
# =========================================================

def production_page():

    page_header(
        "MANUFACTURING",
        "Production Management",
        "Create, update and monitor production batches."
    )


    add_tab, edit_tab, delete_tab = st.tabs(
        [
            "Add Production",
            "Edit Production",
            "Delete Production"
        ]
    )


    item_ids = items[
        "Item_ID"
    ].dropna().tolist()


    # =====================================================
    # ADD
    # =====================================================

    with add_tab:

        st.subheader(
            "Add Production Record"
        )

        with st.form(
            "add_production_form"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                production_id = st.text_input(
                    "Production ID",
                    placeholder="PRD-001"
                )

                if item_ids:

                    production_item = st.selectbox(
                        "Item ID",
                        item_ids
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
                    placeholder="LINE-01"
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
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected",
                        "On Hold"
                    ]
                )


            submit = st.form_submit_button(
                "Add Production",
                type="primary",
                use_container_width=True
            )


        if submit:

            if not production_id.strip():

                st.error(
                    "Production ID is required."
                )

            else:

                data = {

                    "Production_ID":
                        production_id.strip(),

                    "Item_ID":
                        production_item,

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
                    "Production",
                    data
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    # =====================================================
    # EDIT
    # =====================================================

    with edit_tab:

        st.subheader(
            "Edit Production"
        )

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            production_ids = production[
                "Production_ID"
            ].tolist()

            selected_id = st.selectbox(
                "Select Production Record",
                production_ids,
                key="edit_production_select"
            )

            selected = production[
                production[
                    "Production_ID"
                ] == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                current_date = pd.to_datetime(
                    row[
                        "Production_Date"
                    ],
                    errors="coerce"
                )

                if pd.isna(current_date):

                    current_date = date.today()

                else:

                    current_date = current_date.date()


                current_item = str(
                    row["Item_ID"]
                )

                item_options = item_ids.copy()

                if (
                    current_item
                    and current_item
                    not in item_options
                ):

                    item_options.append(
                        current_item
                    )


                with st.form(
                    "edit_production_form"
                ):

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        edit_item = st.selectbox(
                            "Item ID",
                            item_options,
                            index=item_options.index(
                                current_item
                            )
                            if current_item
                            in item_options
                            else 0
                        )

                        edit_date = st.date_input(
                            "Production Date",
                            value=current_date
                        )

                        edit_batch = st.text_input(
                            "Batch No",
                            value=str(
                                row["Batch_No"]
                            )
                        )


                    with c2:

                        edit_line = st.text_input(
                            "Production Line",
                            value=str(
                                row["Production_Line"]
                            )
                        )

                        edit_planned = st.number_input(
                            "Planned Quantity (m)",
                            value=safe_float(
                                row[
                                    "Planned_Qty_m"
                                ]
                            ),
                            step=1.0
                        )

                        edit_good = st.number_input(
                            "Good Quantity (m)",
                            value=safe_float(
                                row[
                                    "Good_Qty_m"
                                ]
                            ),
                            step=1.0
                        )


                    with c3:

                        edit_rejected = st.number_input(
                            "Rejected Quantity (m)",
                            value=safe_float(
                                row[
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
                            row[
                                "Production_Status"
                            ]
                        )

                        if (
                            current_status
                            and current_status
                            not in statuses
                        ):

                            statuses.append(
                                current_status
                            )

                        edit_status = st.selectbox(
                            "Production Status",
                            statuses,
                            index=statuses.index(
                                current_status
                            )
                            if current_status
                            in statuses
                            else 0
                        )


                    update = st.form_submit_button(
                        "Update Production",
                        type="primary",
                        use_container_width=True
                    )


                if update:

                    data = {

                        "Item_ID":
                            edit_item,

                        "Production_Date":
                            edit_date.isoformat(),

                        "Batch_No":
                            edit_batch.strip(),

                        "Production_Line":
                            edit_line.strip(),

                        "Planned_Qty_m":
                            edit_planned,

                        "Good_Qty_m":
                            edit_good,

                        "Rejected_Qty_m":
                            edit_rejected,

                        "Production_Status":
                            edit_status
                    }

                    success, message = update_record(
                        "Production",
                        selected_id,
                        "Production_ID",
                        data
                    )

                    if success:

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)


    # =====================================================
    # DELETE
    # =====================================================

    with delete_tab:

        st.subheader(
            "Delete Production"
        )

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            delete_id = st.selectbox(
                "Select Production Record",
                production[
                    "Production_ID"
                ].tolist(),
                key="delete_production_select"
            )

            if st.button(
                "Delete Production",
                type="primary"
            ):

                success, message = delete_record(
                    "Production",
                    delete_id,
                    "Production_ID"
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    st.divider()

    st.subheader(
        "Production Records"
    )

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# STOCK CONTROL
# =========================================================

def stock_control_page():

    page_header(
        "INVENTORY",
        "Stock Control",
        "Manage opening stock, production, dispatches and closing stock."
    )


    add_tab, edit_tab, delete_tab = st.tabs(
        [
            "Add Stock",
            "Edit Stock",
            "Delete Stock"
        ]
    )


    item_ids = items[
        "Item_ID"
    ].dropna().tolist()

    production_ids = production[
        "Production_ID"
    ].dropna().tolist()


    # =====================================================
    # ADD
    # =====================================================

    with add_tab:

        st.subheader(
            "Add Stock Record"
        )

        with st.form(
            "add_stock_form"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                stock_id = st.text_input(
                    "Stock ID",
                    placeholder="STK-001"
                )

                if item_ids:

                    stock_item = st.selectbox(
                        "Item ID",
                        item_ids
                    )

                else:

                    stock_item = st.text_input(
                        "Item ID"
                    )

                if production_ids:

                    stock_production = st.selectbox(
                        "Production ID",
                        production_ids
                    )

                else:

                    stock_production = st.text_input(
                        "Production ID"
                    )


            with c2:

                stock_batch = st.text_input(
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
                type="primary",
                use_container_width=True
            )


        if submit:

            if not stock_id.strip():

                st.error(
                    "Stock ID is required."
                )

            else:

                closing_stock = (
                    opening_stock
                    + produced_qty
                    - dispatched_qty
                )

                data = {

                    "Stock_ID":
                        stock_id.strip(),

                    "Item_ID":
                        stock_item,

                    "Production_ID":
                        stock_production,

                    "Batch_No":
                        stock_batch.strip(),

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
                    "Stock Control",
                    data
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    # =====================================================
    # EDIT
    # =====================================================

    with edit_tab:

        st.subheader(
            "Edit Stock"
        )

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            stock_ids = stock[
                "Stock_ID"
            ].tolist()

            selected_id = st.selectbox(
                "Select Stock Record",
                stock_ids,
                key="edit_stock_select"
            )

            selected = stock[
                stock[
                    "Stock_ID"
                ] == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                current_date = pd.to_datetime(
                    row[
                        "Stock_Date"
                    ],
                    errors="coerce"
                )

                if pd.isna(current_date):

                    current_date = date.today()

                else:

                    current_date = current_date.date()


                current_item = str(
                    row["Item_ID"]
                )

                current_production = str(
                    row["Production_ID"]
                )


                item_options = item_ids.copy()

                if (
                    current_item
                    and current_item
                    not in item_options
                ):

                    item_options.append(
                        current_item
                    )


                production_options = production_ids.copy()

                if (
                    current_production
                    and current_production
                    not in production_options
                ):

                    production_options.append(
                        current_production
                    )


                with st.form(
                    "edit_stock_form"
                ):

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        edit_item = st.selectbox(
                            "Item ID",
                            item_options,
                            index=item_options.index(
                                current_item
                            )
                            if current_item
                            in item_options
                            else 0
                        )

                        edit_production = st.selectbox(
                            "Production ID",
                            production_options,
                            index=production_options.index(
                                current_production
                            )
                            if current_production
                            in production_options
                            else 0
                        )

                        edit_batch = st.text_input(
                            "Batch No",
                            value=str(
                                row["Batch_No"]
                            )
                        )


                    with c2:

                        edit_date = st.date_input(
                            "Stock Date",
                            value=current_date
                        )

                        edit_opening = st.number_input(
                            "Opening Stock (m)",
                            value=safe_float(
                                row[
                                    "Opening_Stock_m"
                                ]
                            ),
                            step=1.0
                        )

                        edit_produced = st.number_input(
                            "Produced Quantity (m)",
                            value=safe_float(
                                row[
                                    "Produced_Qty_m"
                                ]
                            ),
                            step=1.0
                        )


                    with c3:

                        edit_dispatched = st.number_input(
                            "Dispatched Quantity (m)",
                            value=safe_float(
                                row[
                                    "Dispatched_Qty_m"
                                ]
                            ),
                            step=1.0
                        )

                        statuses = [
                            "Available",
                            "Low Stock",
                            "Out of Stock",
                            "Reserved"
                        ]

                        current_status = str(
                            row[
                                "Stock_Status"
                            ]
                        )

                        if (
                            current_status
                            and current_status
                            not in statuses
                        ):

                            statuses.append(
                                current_status
                            )

                        edit_status = st.selectbox(
                            "Stock Status",
                            statuses,
                            index=statuses.index(
                                current_status
                            )
                            if current_status
                            in statuses
                            else 0
                        )


                    update = st.form_submit_button(
                        "Update Stock",
                        type="primary",
                        use_container_width=True
                    )


                if update:

                    closing_stock = (
                        edit_opening
                        + edit_produced
                        - edit_dispatched
                    )

                    data = {

                        "Item_ID":
                            edit_item,

                        "Production_ID":
                            edit_production,

                        "Batch_No":
                            edit_batch.strip(),

                        "Stock_Date":
                            edit_date.isoformat(),

                        "Opening_Stock_m":
                            edit_opening,

                        "Produced_Qty_m":
                            edit_produced,

                        "Dispatched_Qty_m":
                            edit_dispatched,

                        "Closing_Stock_m":
                            closing_stock,

                        "Stock_Status":
                            edit_status
                    }

                    success, message = update_record(
                        "Stock Control",
                        selected_id,
                        "Stock_ID",
                        data
                    )

                    if success:

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)


    # =====================================================
    # DELETE
    # =====================================================

    with delete_tab:

        st.subheader(
            "Delete Stock"
        )

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            delete_id = st.selectbox(
                "Select Stock Record",
                stock[
                    "Stock_ID"
                ].tolist(),
                key="delete_stock_select"
            )

            if st.button(
                "Delete Stock",
                type="primary"
            ):

                success, message = delete_record(
                    "Stock Control",
                    delete_id,
                    "Stock_ID"
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    st.divider()

    st.subheader(
        "Stock Records"
    )

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CUSTOM ANALYTICS
# =========================================================

def custom_analytics():

    page_header(
        "BUSINESS INTELLIGENCE",
        "Custom Analytics",
        "Build your own charts by selecting dataset, attributes and aggregation."
    )


    # =====================================================
    # DATASET
    # =====================================================

    dataset = st.selectbox(
        "1. Select Dataset",
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
            "Selected dataset has no records."
        )

        return


    # =====================================================
    # CLEAN COLUMN TYPES FOR ANALYTICS
    # =====================================================

    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .fillna("Unknown")
            )


    all_columns = df.columns.tolist()

    numeric_columns = (
        df
        .select_dtypes(
            include=["number"]
        )
        .columns
        .tolist()
    )


    # =====================================================
    # CHART TYPE
    # =====================================================

    chart_type = st.selectbox(
        "2. Select Chart Type",
        [
            "Bar",
            "Line",
            "Pie",
            "Scatter"
        ]
    )


    # =====================================================
    # BAR / LINE / PIE
    # =====================================================

    if chart_type in [
        "Bar",
        "Line",
        "Pie"
    ]:

        c1, c2 = st.columns(2)

        with c1:

            x_column = st.selectbox(
                "3. Category / X Attribute",
                all_columns
            )

        with c2:

            if numeric_columns:

                y_column = st.selectbox(
                    "4. Numeric Attribute",
                    numeric_columns
                )

            else:

                st.warning(
                    "This dataset has no numeric columns."
                )

                return


        aggregation = st.selectbox(
            "5. Aggregation",
            [
                "Sum",
                "Average",
                "Count",
                "Minimum",
                "Maximum"
            ]
        )


        try:

            if aggregation == "Sum":

                grouped = (
                    df
                    .groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .sum()
                )

            elif aggregation == "Average":

                grouped = (
                    df
                    .groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .mean()
                )

            elif aggregation == "Count":

                grouped = (
                    df
                    .groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .count()
                )

            elif aggregation == "Minimum":

                grouped = (
                    df
                    .groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .min()
                )

            else:

                grouped = (
                    df
                    .groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .max()
                )


            if chart_type == "Bar":

                fig = px.bar(
                    grouped,
                    x=x_column,
                    y=y_column,
                    text_auto=".2s",
                    template="plotly_white"
                )


            elif chart_type == "Line":

                fig = px.line(
                    grouped,
                    x=x_column,
                    y=y_column,
                    markers=True,
                    template="plotly_white"
                )


            else:

                fig = px.pie(
                    grouped,
                    names=x_column,
                    values=y_column,
                    hole=0.45,
                    template="plotly_white"
                )


            fig.update_layout(
                height=500
            )


            st.plotly_chart(
                fig,
                use_container_width=True
            )


            with st.expander(
                "View Chart Data"
            ):

                st.dataframe(
                    grouped,
                    use_container_width=True,
                    hide_index=True
                )


        except Exception as e:

            st.error(
                f"Chart creation error: {e}"
            )


    # =====================================================
    # SCATTER
    # =====================================================

    else:

        if len(numeric_columns) < 2:

            st.warning(
                "Scatter chart requires at least two numeric columns."
            )

            return


        c1, c2 = st.columns(2)

        with c1:

            x_column = st.selectbox(
                "3. X Axis",
                numeric_columns,
                key="analytics_scatter_x"
            )

        with c2:

            y_column = st.selectbox(
                "4. Y Axis",
                numeric_columns,
                key="analytics_scatter_y"
            )


        fig = px.scatter(
            df,
            x=x_column,
            y=y_column,
            template="plotly_white"
        )


        fig.update_layout(
            height=500
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# DATA MANAGEMENT
# =========================================================

def data_management():

    page_header(
        "SYSTEM DATA",
        "Data Management",
        "View and download ERP database records."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Items",
            "Production",
            "Stock"
        ]
    )


    with tab1:

        st.subheader(
            "Item Registration"
        )

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )

        csv = items.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            "Download Items CSV",
            csv,
            "Item_Registration.csv",
            "text/csv"
        )


    with tab2:

        st.subheader(
            "Production"
        )

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )

        csv = production.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            "Download Production CSV",
            csv,
            "Production.csv",
            "text/csv"
        )


    with tab3:

        st.subheader(
            "Stock Control"
        )

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )

        csv = stock.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            "Download Stock CSV",
            csv,
            "Stock_Control.csv",
            "text/csv"
        )


# =========================================================
# PAGE ROUTING
# =========================================================

if page == "Executive Dashboard":

    dashboard()

elif page == "Item Registration":

    item_registration()

elif page == "Production":

    production_page()

elif page == "Stock Control":

    stock_control_page()

elif page == "Custom Analytics":

    custom_analytics()

elif page == "Data Management":

    data_management()
