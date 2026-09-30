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
# TABLE CONFIGURATION
# IMPORTANT: THESE ARE THE ACTUAL SUPABASE TABLE NAMES
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
# LOAD CSS
# =========================================================

def load_css():
    css_path = os.path.join(
        os.path.dirname(__file__),
        "style.css"
    )

    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
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

        try:
            url = st.secrets.get("SUPABASE_URL")
            key = st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass

        if not url:
            url = os.getenv("SUPABASE_URL")

        if not key:
            key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            return None

        return create_client(url, key)

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
            with open(logo_path, "rb") as image_file:

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
# SIDEBAR NAVIGATION
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
# HELPER FUNCTIONS
# =========================================================

def page_header(kicker, title, description=""):

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


def ensure_columns(df, columns):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for column in columns:

        if column not in df.columns:
            df[column] = None

    return df


def clean_text_columns(df, columns):

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


def convert_numeric(df, columns):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


def convert_dates(df, columns):

    df = df.copy()

    for column in columns:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                errors="coerce"
            )

    return df


# =========================================================
# SUPABASE FETCH
# =========================================================

def fetch_table(module):

    if supabase is None:

        st.error(
            "Supabase is not connected. "
            "Check SUPABASE_URL and SUPABASE_KEY."
        )

        return pd.DataFrame()

    table_name = TABLES[module]

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        data = response.data or []

        return pd.DataFrame(data)

    except Exception as e:

        st.error(
            f"Supabase error in {module}: {e}"
        )

        return pd.DataFrame()


# =========================================================
# CRUD FUNCTIONS
# =========================================================

def insert_record(module, data):

    if supabase is None:
        return False, "Supabase is not connected."

    try:

        table_name = TABLES[module]

        (
            supabase
            .table(table_name)
            .insert(data)
            .execute()
        )

        return True, "Record added successfully."

    except Exception as e:

        return False, str(e)


def update_record(
    module,
    record_id,
    id_column,
    data
):

    if supabase is None:
        return False, "Supabase is not connected."

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


def delete_record(
    module,
    record_id,
    id_column
):

    if supabase is None:
        return False, "Supabase is not connected."

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


# =========================================================
# LOAD DATA
# =========================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


# =========================================================
# NORMALIZE ITEMS
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

items = convert_numeric(
    items,
    [
        "Nominal_Diameter_mm",
        "Wall_Thickness_mm",
        "Standard_Length"
    ]
)


# =========================================================
# NORMALIZE PRODUCTION
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

production = convert_numeric(
    production,
    [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]
)

production = convert_dates(
    production,
    [
        "Production_Date"
    ]
)


# =========================================================
# NORMALIZE STOCK
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

stock = convert_numeric(
    stock,
    [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]
)

stock = convert_dates(
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
    # KPIs
    # -----------------------------------------------------

    total_items = len(items)

    total_planned = (
        production["Planned_Qty_m"]
        .fillna(0)
        .sum()
    )

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

    current_stock = (
        stock["Closing_Stock_m"]
        .fillna(0)
        .sum()
    )

    total_dispatched = (
        stock["Dispatched_Qty_m"]
        .fillna(0)
        .sum()
    )

    if total_good + total_rejected > 0:

        yield_rate = (
            total_good /
            (total_good + total_rejected)
        ) * 100

    else:

        yield_rate = 0


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
                    {current_stock:,.0f} m
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


    # -----------------------------------------------------
    # CHART ROW 1
    # -----------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Production Trend")

        if not production.empty:

            trend = production.copy()

            trend["Production_Date"] = pd.to_datetime(
                trend["Production_Date"],
                errors="coerce"
            )

            trend = trend.dropna(
                subset=["Production_Date"]
            )

            if not trend.empty:

                trend = (
                    trend
                    .groupby(
                        "Production_Date",
                        as_index=False
                    )["Good_Qty_m"]
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
                    xaxis_title="Date",
                    yaxis_title="Good Production (m)",
                    height=360
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "Production date data is not available."
                )

        else:

            st.info(
                "No production data available."
            )


    with col2:

        st.subheader("Production Status")

        if not production.empty:

            status = (
                production
                .groupby("Production_Status")
                .size()
                .reset_index(name="Count")
            )

            if not status.empty:

                fig = px.pie(
                    status,
                    names="Production_Status",
                    values="Count",
                    hole=0.48,
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
                    "No production status data."
                )

        else:

            st.info(
                "No production data available."
            )


    # -----------------------------------------------------
    # CHART ROW 2
    # -----------------------------------------------------

    col3, col4 = st.columns(2)

    with col3:

        st.subheader("Stock by Item")

        if not stock.empty:

            s = stock.copy()
            i = items.copy()

            s["Item_ID"] = (
                s["Item_ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            i["Item_ID"] = (
                i["Item_ID"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            s["Closing_Stock_m"] = pd.to_numeric(
                s["Closing_Stock_m"],
                errors="coerce"
            ).fillna(0)

            i = i[
                ["Item_ID", "Item_Code"]
            ].drop_duplicates(
                subset=["Item_ID"]
            )

            s = s.merge(
                i,
                on="Item_ID",
                how="left"
            )

            s["Item_Code"] = (
                s["Item_Code"]
                .fillna(s["Item_ID"])
            )

            stock_chart = (
                s.groupby(
                    "Item_Code",
                    as_index=False
                )["Closing_Stock_m"]
                .sum()
            )

            fig = px.bar(
                stock_chart,
                x="Item_Code",
                y="Closing_Stock_m",
                template="plotly_white",
                text_auto=".2s"
            )

            fig.update_layout(
                xaxis_title="Item",
                yaxis_title="Closing Stock (m)",
                height=360
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info(
                "No stock data available."
            )


    with col4:

        st.subheader("Production Quality")

        quality_df = pd.DataFrame(
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
            quality_df,
            x="Category",
            y="Quantity",
            text_auto=".2s",
            template="plotly_white"
        )

        fig.update_layout(
            xaxis_title="",
            yaxis_title="Quantity (m)",
            height=360
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # -----------------------------------------------------
    # RECENT PRODUCTION
    # -----------------------------------------------------

    st.subheader("Recent Production")

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


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Item",
            "Edit Item",
            "Delete Item"
        ]
    )


    # -----------------------------------------------------
    # ADD
    # -----------------------------------------------------

    with tab1:

        st.subheader("Register New Item")

        with st.form("add_item_form"):

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
                    "Item_ID": item_id.strip(),
                    "Item_Code": item_code.strip(),
                    "Material_Grade": material_grade,
                    "Application": application,
                    "Nominal_Diameter_mm": nominal_diameter,
                    "Wall_Thickness_mm": wall_thickness,
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
                    st.rerun()

                else:

                    st.error(message)


    # -----------------------------------------------------
    # EDIT
    # -----------------------------------------------------

    with tab2:

        st.subheader("Edit Item")

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            item_ids = items["Item_ID"].tolist()

            selected_id = st.selectbox(
                "Select Item",
                item_ids
            )

            selected = items[
                items["Item_ID"] == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                with st.form("edit_item_form"):

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
                            value=float(
                                row["Nominal_Diameter_mm"]
                                or 0
                            ),
                            step=0.1
                        )

                        edit_wall = st.number_input(
                            "Wall Thickness (mm)",
                            value=float(
                                row["Wall_Thickness_mm"]
                                or 0
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
                            value=float(
                                row["Standard_Length"]
                                or 0
                            ),
                            step=1.0
                        )

                        edit_unit = st.text_input(
                            "Unit",
                            value=str(
                                row["Unit"]
                            )
                        )

                    update_button = st.form_submit_button(
                        "Update Item",
                        type="primary",
                        use_container_width=True
                    )


                if update_button:

                    data = {
                        "Item_Code": edit_code.strip(),
                        "Material_Grade": edit_grade.strip(),
                        "Application": edit_application.strip(),
                        "Nominal_Diameter_mm": edit_diameter,
                        "Wall_Thickness_mm": edit_wall,
                        "SDR": edit_sdr.strip(),
                        "Color": edit_color.strip(),
                        "Standard_Length": edit_length,
                        "Unit": edit_unit.strip()
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


    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    with tab3:

        st.subheader("Delete Item")

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            delete_id = st.selectbox(
                "Select Item to Delete",
                items["Item_ID"].tolist(),
                key="delete_item"
            )

            st.warning(
                f"You are about to delete Item: {delete_id}"
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


    # -----------------------------------------------------
    # DATA TABLE
    # -----------------------------------------------------

    st.divider()

    st.subheader("All Registered Items")

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# PRODUCTION
# =========================================================

def production_page():

    page_header(
        "MANUFACTURING",
        "Production Management",
        "Create, update and monitor pipe production batches."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Production",
            "Edit Production",
            "Delete Production"
        ]
    )


    item_list = items["Item_ID"].tolist()

    # -----------------------------------------------------
    # ADD PRODUCTION
    # -----------------------------------------------------

    with tab1:

        st.subheader("Add Production Record")

        with st.form("add_production_form"):

            c1, c2, c3 = st.columns(3)

            with c1:

                production_id = st.text_input(
                    "Production ID",
                    placeholder="PRD-001"
                )

                if item_list:

                    item_id = st.selectbox(
                        "Item ID",
                        item_list
                    )

                else:

                    item_id = st.text_input(
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
                    "Production",
                    data
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


    # -----------------------------------------------------
    # EDIT PRODUCTION
    # -----------------------------------------------------

    with tab2:

        st.subheader("Edit Production")

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
                production_ids
            )

            selected = production[
                production["Production_ID"]
                == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                current_date = pd.to_datetime(
                    row["Production_Date"],
                    errors="coerce"
                )

                if pd.isna(current_date):

                    current_date = date.today()

                else:

                    current_date = current_date.date()


                current_item = str(
                    row["Item_ID"]
                )

                item_options = item_list.copy()

                if current_item and current_item not in item_options:
                    item_options.append(current_item)

                with st.form("edit_production_form"):

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        edit_item = st.selectbox(
                            "Item ID",
                            item_options,
                            index=item_options.index(
                                current_item
                            ) if current_item in item_options else 0
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
                            value=float(
                                row["Planned_Qty_m"]
                                or 0
                            ),
                            step=1.0
                        )

                        edit_good = st.number_input(
                            "Good Quantity (m)",
                            value=float(
                                row["Good_Qty_m"]
                                or 0
                            ),
                            step=1.0
                        )

                    with c3:

                        edit_rejected = st.number_input(
                            "Rejected Quantity (m)",
                            value=float(
                                row["Rejected_Qty_m"]
                                or 0
                            ),
                            step=1.0
                        )

                        status_options = [
                            "Planned",
                            "In Progress",
                            "Completed",
                            "Rejected",
                            "On Hold"
                        ]

                        current_status = str(
                            row["Production_Status"]
                        )

                        if current_status not in status_options:
                            status_options.append(
                                current_status
                            )

                        edit_status = st.selectbox(
                            "Production Status",
                            status_options,
                            index=status_options.index(
                                current_status
                            )
                        )

                    update_button = st.form_submit_button(
                        "Update Production",
                        type="primary",
                        use_container_width=True
                    )


                if update_button:

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


    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    with tab3:

        st.subheader("Delete Production")

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
                key="delete_production"
            )

            st.warning(
                f"You are about to delete: {delete_id}"
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


    # -----------------------------------------------------
    # PRODUCTION TABLE
    # -----------------------------------------------------

    st.divider()

    st.subheader("Production Records")

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
        "Monitor opening stock, production, dispatches and closing inventory."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Stock",
            "Edit Stock",
            "Delete Stock"
        ]
    )


    item_list = items["Item_ID"].tolist()
    production_list = production[
        "Production_ID"
    ].tolist()


    # -----------------------------------------------------
    # ADD STOCK
    # -----------------------------------------------------

    with tab1:

        st.subheader("Add Stock Record")

        with st.form("add_stock_form"):

            c1, c2, c3 = st.columns(3)

            with c1:

                stock_id = st.text_input(
                    "Stock ID",
                    placeholder="STK-001"
                )

                if item_list:

                    stock_item = st.selectbox(
                        "Item ID",
                        item_list
                    )

                else:

                    stock_item = st.text_input(
                        "Item ID"
                    )

                if production_list:

                    stock_production = st.selectbox(
                        "Production ID",
                        production_list
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

            closing_stock = (
                opening_stock
                + produced_qty
                - dispatched_qty
            )

            if not stock_id.strip():

                st.error(
                    "Stock ID is required."
                )

            else:

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


    # -----------------------------------------------------
    # EDIT STOCK
    # -----------------------------------------------------

    with tab2:

        st.subheader("Edit Stock")

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
                stock_ids
            )

            selected = stock[
                stock["Stock_ID"]
                == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                current_date = pd.to_datetime(
                    row["Stock_Date"],
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


                item_options = item_list.copy()

                if (
                    current_item
                    and current_item not in item_options
                ):
                    item_options.append(
                        current_item
                    )


                production_options = production_list.copy()

                if (
                    current_production
                    and current_production
                    not in production_options
                ):
                    production_options.append(
                        current_production
                    )


                with st.form("edit_stock_form"):

                    c1, c2, c3 = st.columns(3)

                    with c1:

                        edit_item = st.selectbox(
                            "Item ID",
                            item_options,
                            index=item_options.index(
                                current_item
                            ) if current_item in item_options else 0
                        )

                        edit_production = st.selectbox(
                            "Production ID",
                            production_options,
                            index=production_options.index(
                                current_production
                            ) if current_production in production_options else 0
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
                            value=float(
                                row["Opening_Stock_m"]
                                or 0
                            ),
                            step=1.0
                        )

                        edit_produced = st.number_input(
                            "Produced Quantity (m)",
                            value=float(
                                row["Produced_Qty_m"]
                                or 0
                            ),
                            step=1.0
                        )

                    with c3:

                        edit_dispatched = st.number_input(
                            "Dispatched Quantity (m)",
                            value=float(
                                row["Dispatched_Qty_m"]
                                or 0
                            ),
                            step=1.0
                        )

                        current_status = str(
                            row["Stock_Status"]
                        )

                        status_options = [
                            "Available",
                            "Low Stock",
                            "Out of Stock",
                            "Reserved"
                        ]

                        if (
                            current_status
                            and current_status
                            not in status_options
                        ):
                            status_options.append(
                                current_status
                            )

                        edit_status = st.selectbox(
                            "Stock Status",
                            status_options,
                            index=status_options.index(
                                current_status
                            ) if current_status in status_options else 0
                        )


                    update_button = st.form_submit_button(
                        "Update Stock",
                        type="primary",
                        use_container_width=True
                    )


                if update_button:

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


    # -----------------------------------------------------
    # DELETE
    # -----------------------------------------------------

    with tab3:

        st.subheader("Delete Stock")

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
                key="delete_stock"
            )

            st.warning(
                f"You are about to delete: {delete_id}"
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


    # -----------------------------------------------------
    # STOCK TABLE
    # -----------------------------------------------------

    st.divider()

    st.subheader("Stock Records")

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
        "Select your own dataset, attributes and chart type."
    )


    st.info(
        "Yahan aap apni marzi se table aur attributes "
        "select karke charts bana sakte hain."
    )


    # -----------------------------------------------------
    # DATASET
    # -----------------------------------------------------

    dataset_name = st.selectbox(
        "1. Select Dataset",
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
            "Selected dataset is empty."
        )

        return


    all_columns = df.columns.tolist()


    # -----------------------------------------------------
    # DETECT NUMERIC COLUMNS
    # -----------------------------------------------------

    numeric_columns = (
        df
        .select_dtypes(
            include=["number"]
        )
        .columns
        .tolist()
    )


    if not numeric_columns:

        st.warning(
            "Selected table does not contain numeric attributes."
        )

        return


    # -----------------------------------------------------
    # CHART TYPE
    # -----------------------------------------------------

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
                "3. Select Category / X Attribute",
                all_columns
            )

        with c2:

            y_column = st.selectbox(
                "4. Select Numeric Attribute",
                numeric_columns
            )


        aggregation = st.selectbox(
            "5. Select Aggregation",
            [
                "Sum",
                "Average",
                "Count",
                "Minimum",
                "Maximum"
            ]
        )


        # -------------------------------------------------
        # GROUP DATA
        # -------------------------------------------------

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


            # Remove missing category values

            grouped = grouped.dropna(
                subset=[x_column]
            )


            if grouped.empty:

                st.warning(
                    "No data available for this chart."
                )

                return


            # -------------------------------------------------
            # CHART
            # -------------------------------------------------

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


            # -------------------------------------------------
            # SHOW DATA
            # -------------------------------------------------

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
                f"Could not create chart: {e}"
            )


    # =====================================================
    # SCATTER
    # =====================================================

    else:

        c1, c2 = st.columns(2)

        with c1:

            x_column = st.selectbox(
                "3. Select X Axis",
                numeric_columns,
                key="scatter_x"
            )

        with c2:

            y_column = st.selectbox(
                "4. Select Y Axis",
                numeric_columns,
                key="scatter_y"
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


        with st.expander(
            "View Chart Data"
        ):

            st.dataframe(
                df[
                    [
                        x_column,
                        y_column
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )


# =========================================================
# DATA MANAGEMENT
# =========================================================

def data_management():

    page_header(
        "SYSTEM DATA",
        "Data Management",
        "View the complete data stored in your ERP database."
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
            "Item Registration Data"
        )

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )

        csv = items.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Items CSV",
            csv,
            "Item_Registration.csv",
            "text/csv"
        )


    with tab2:

        st.subheader(
            "Production Data"
        )

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )

        csv = production.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Production CSV",
            csv,
            "Production.csv",
            "text/csv"
        )


    with tab3:

        st.subheader(
            "Stock Control Data"
        )

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )

        csv = stock.to_csv(
            index=False
        ).encode("utf-8")

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
