import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client, Client


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Flex Head Industries | ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

.erp-header {
    padding: 20px 25px;
    border-radius: 15px;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #111827, #1f2937);
    color: white;
}

.erp-header h1 {
    margin: 0;
    font-size: 30px;
}

.erp-header p {
    margin-top: 5px;
    color: #d1d5db;
}

.section-title {
    font-size: 24px;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 15px;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 3px 12px rgba(0,0,0,0.06);
    min-height: 145px;
}

.metric-icon {
    font-size: 26px;
    margin-bottom: 8px;
}

.metric-label {
    font-size: 14px;
    color: #6b7280;
    font-weight: 600;
}

.metric-value {
    font-size: 30px;
    font-weight: 800;
    color: #111827;
    margin-top: 5px;
}

.metric-caption {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 5px;
}

.status-card {
    padding: 12px 18px;
    border-radius: 10px;
    margin-bottom: 15px;
}

.success-status {
    background-color: #ecfdf5;
    color: #047857;
    border: 1px solid #a7f3d0;
}

.error-status {
    background-color: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
}

.sidebar-title {
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 5px;
}

.small-note {
    color: #6b7280;
    font-size: 13px;
}

div[data-testid="stMetric"] {
    background-color: white;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# COMPANY HEADER
# ============================================================

st.markdown("""
<div class="erp-header">
    <h1>🏭 Flex Head Industries Pvt Ltd</h1>
    <p>Pipe Manufacturing Enterprise Resource Planning System</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase_client():

    try:

        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        client: Client = create_client(url, key)

        return client, True, "Supabase Connected"

    except Exception as e:

        return None, False, str(e)


supabase, db_connected, db_message = get_supabase_client()


# ============================================================
# DATABASE TABLE NAMES
# ============================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock": "Stock_Control"
}


# ============================================================
# EXACT DATABASE COLUMNS
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
# HELPER FUNCTIONS
# ============================================================

def safe_number(value):
    """
    Convert values safely to numbers.
    """

    if value is None:
        return 0

    try:
        return float(value)
    except:
        return 0


def format_number(value):
    """
    Format numeric values for dashboard.
    """

    try:

        value = float(value)

        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    except:

        return "0"


def clear_data_cache():
    """
    Clear Streamlit data cache after database changes.
    """

    load_table.clear()


# ============================================================
# LOAD TABLE FROM SUPABASE
# ============================================================

@st.cache_data(ttl=10)
def load_table(table_name):

    if supabase is None:
        return pd.DataFrame()

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        if response.data is None:
            return pd.DataFrame()

        return pd.DataFrame(response.data)

    except Exception as e:

        st.error(
            f"Database error while loading `{table_name}`: {e}"
        )

        return pd.DataFrame()


# ============================================================
# LOAD ALL DATA
# ============================================================

def load_all_data():

    items = load_table(TABLES["Items"])
    production = load_table(TABLES["Production"])
    stock = load_table(TABLES["Stock"])

    return items, production, stock


# ============================================================
# PREPARE DATAFRAME
# ============================================================

def prepare_dataframe(df, expected_columns):

    if df is None or df.empty:

        return pd.DataFrame(columns=expected_columns)

    df = df.copy()

    for col in expected_columns:

        if col not in df.columns:
            df[col] = None

    return df


# ============================================================
# SUPABASE INSERT
# ============================================================

def insert_record(table_name, record):

    if supabase is None:

        st.error("Supabase is not connected.")

        return False

    try:

        supabase.table(table_name).insert(record).execute()

        clear_data_cache()

        return True

    except Exception as e:

        st.error(
            f"Insert failed in `{table_name}`: {e}"
        )

        return False


# ============================================================
# SUPABASE UPDATE
# ============================================================

def update_record(table_name, id_column, id_value, record):

    if supabase is None:

        st.error("Supabase is not connected.")

        return False

    try:

        (
            supabase
            .table(table_name)
            .update(record)
            .eq(id_column, id_value)
            .execute()
        )

        clear_data_cache()

        return True

    except Exception as e:

        st.error(
            f"Update failed in `{table_name}`: {e}"
        )

        return False


# ============================================================
# SUPABASE DELETE
# ============================================================

def delete_record(table_name, id_column, id_value):

    if supabase is None:

        st.error("Supabase is not connected.")

        return False

    try:

        (
            supabase
            .table(table_name)
            .delete()
            .eq(id_column, id_value)
            .execute()
        )

        clear_data_cache()

        return True

    except Exception as e:

        st.error(
            f"Delete failed in `{table_name}`: {e}"
        )

        return False


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    '<div class="sidebar-title">🏭 ERP SYSTEM</div>',
    unsafe_allow_html=True
)

st.sidebar.caption(
    "Flex Head Industries Pvt Ltd"
)

st.sidebar.divider()


if db_connected:

    st.sidebar.success("🟢 Supabase Connected")

else:

    st.sidebar.error("🔴 Supabase Not Connected")
    st.sidebar.caption(str(db_message))


page = st.sidebar.radio(
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


st.sidebar.divider()

st.sidebar.caption(
    "Pipe Manufacturing ERP"
)

st.sidebar.caption(
    "PE-80 | PE-100"
)


# ============================================================
# LOAD DATA
# ============================================================

items, production, stock = load_all_data()

items = prepare_dataframe(items, ITEM_COLUMNS)
production = prepare_dataframe(production, PRODUCTION_COLUMNS)
stock = prepare_dataframe(stock, STOCK_COLUMNS)


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

if page == "Executive Dashboard":

    st.markdown(
        '<div class="section-title">📊 Executive Dashboard</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Real-time overview of manufacturing, production and inventory."
    )

    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------

    for col in [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]:

        if col in production.columns:

            production[col] = pd.to_numeric(
                production[col],
                errors="coerce"
            ).fillna(0)


    for col in [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]:

        if col in stock.columns:

            stock[col] = pd.to_numeric(
                stock[col],
                errors="coerce"
            ).fillna(0)


    # --------------------------------------------------------
    # Dashboard calculations
    # --------------------------------------------------------

    registered_items = len(items)

    planned_production = production[
        "Planned_Qty_m"
    ].sum()

    good_production = production[
        "Good_Qty_m"
    ].sum()

    rejected_production = production[
        "Rejected_Qty_m"
    ].sum()

    produced_stock = stock[
        "Produced_Qty_m"
    ].sum()

    dispatched = stock[
        "Dispatched_Qty_m"
    ].sum()

    current_stock = stock[
        "Closing_Stock_m"
    ].sum()

    total_output = (
        good_production +
        rejected_production
    )

    if total_output > 0:

        yield_percentage = (
            good_production /
            total_output
        ) * 100

    else:

        yield_percentage = 0


    # --------------------------------------------------------
    # Main Metrics
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-icon">📦</div>

            <div class="metric-label">
                Registered Items
            </div>

            <div class="metric-value">
                {registered_items:,}
            </div>

            <div class="metric-caption">
                Total product items
            </div>

        </div>
        """, unsafe_allow_html=True)


    with c2:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-icon">✓</div>

            <div class="metric-label">
                Good Production
            </div>

            <div class="metric-value">
                {format_number(good_production)} m
            </div>

            <div class="metric-caption">
                Accepted production
            </div>

        </div>
        """, unsafe_allow_html=True)


    with c3:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-icon">🏭</div>

            <div class="metric-label">
                Current Stock
            </div>

            <div class="metric-value">
                {format_number(current_stock)} m
            </div>

            <div class="metric-caption">
                Closing inventory
            </div>

        </div>
        """, unsafe_allow_html=True)


    with c4:

        st.markdown(f"""
        <div class="metric-card">

            <div class="metric-icon">📈</div>

            <div class="metric-label">
                Production Yield
            </div>

            <div class="metric-value">
                {yield_percentage:.1f}%
            </div>

            <div class="metric-caption">
                Good output / total output
            </div>

        </div>
        """, unsafe_allow_html=True)


    st.write("")


    # --------------------------------------------------------
    # Secondary Metrics
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)


    with c1:
        st.metric(
            "Planned Production",
            f"{format_number(planned_production)} m"
        )


    with c2:
        st.metric(
            "Rejected Production",
            f"{format_number(rejected_production)} m"
        )


    with c3:
        st.metric(
            "Produced to Stock",
            f"{format_number(produced_stock)} m"
        )


    with c4:
        st.metric(
            "Dispatched",
            f"{format_number(dispatched)} m"
        )


    st.divider()


    # ========================================================
    # CHARTS
    # ========================================================

    chart1, chart2 = st.columns(2)


    # --------------------------------------------------------
    # Production Overview
    # --------------------------------------------------------

    with chart1:

        st.subheader("📈 Production Overview")

        if not production.empty:

            chart_data = production.copy()

            chart_data["Production_Date"] = pd.to_datetime(
                chart_data["Production_Date"],
                errors="coerce"
            )

            chart_data = (
                chart_data
                .groupby("Production_Date", as_index=False)
                .agg({
                    "Planned_Qty_m": "sum",
                    "Good_Qty_m": "sum",
                    "Rejected_Qty_m": "sum"
                })
            )

            chart_data = chart_data.dropna(
                subset=["Production_Date"]
            )

            if not chart_data.empty:

                fig = px.line(
                    chart_data,
                    x="Production_Date",
                    y=[
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ],
                    markers=True,
                    title="Daily Production"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "Production dates are not available."
                )

        else:

            st.info(
                "No production data available."
            )


    # --------------------------------------------------------
    # Production Status
    # --------------------------------------------------------

    with chart2:

        st.subheader("📊 Production Status")

        if not production.empty:

            status_data = (
                production[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )

            status_data.columns = [
                "Production_Status",
                "Count"
            ]

            fig = px.pie(
                status_data,
                names="Production_Status",
                values="Count",
                hole=0.45,
                title="Production Status Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info(
                "No production status data available."
            )


    # --------------------------------------------------------
    # Stock By Item
    # --------------------------------------------------------

    st.subheader("📦 Current Stock by Item")

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
        )

        stock_chart = stock_chart.sort_values(
            "Closing_Stock_m",
            ascending=False
        )

        fig = px.bar(
            stock_chart,
            x="Item_ID",
            y="Closing_Stock_m",
            title="Closing Stock by Item",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "No stock data available."
        )


# ============================================================
# ITEM REGISTRATION
# ============================================================

elif page == "Item Registration":

    st.markdown(
        '<div class="section-title">📦 Item Registration</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Manage pipe products and item master data."
    )


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "➕ Create",
            "🔎 Search / Read",
            "✏️ Update",
            "🗑️ Delete"
        ]
    )


    # ========================================================
    # CREATE ITEM
    # ========================================================

    with tab1:

        st.subheader("Add New Item")

        with st.form("add_item_form"):

            c1, c2 = st.columns(2)

            with c1:

                item_id = st.text_input(
                    "Item ID *"
                )

                material_grade = st.selectbox(
                    "Material Grade",
                    [
                        "PE-80",
                        "PE-100"
                    ]
                )

                application = st.selectbox(
                    "Application",
                    [
                        "Water",
                        "Sewerage",
                        "Gas",
                        "Other"
                    ]
                )

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0
                )

                wall_thickness = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1
                )


            with c2:

                sdr = st.number_input(
                    "SDR",
                    min_value=0.0,
                    step=1.0
                )

                color = st.text_input(
                    "Color",
                    value="Black"
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
                "➕ Add Item",
                use_container_width=True
            )


            if submitted:

                if not item_id.strip():

                    st.error(
                        "Item_ID is required."
                    )

                else:

                    record = {

                        "Item_ID": item_id.strip(),

                        "Material_Grade":
                            material_grade,

                        "Application":
                            application,

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall_thickness,

                        "SDR":
                            sdr,

                        "Color":
                            color,

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit
                    }


                    if insert_record(
                        TABLES["Items"],
                        record
                    ):

                        st.success(
                            "Item successfully added."
                        )

                        st.rerun()


    # ========================================================
    # SEARCH / READ
    # ========================================================

    with tab2:

        st.subheader("Item Records")

        search = st.text_input(
            "Search Item",
            placeholder="Enter Item ID, Material Grade, Application..."
        )


        display_df = items.copy()


        if search:

            mask = (
                display_df
                .astype(str)
                .apply(
                    lambda row:
                    row.str.contains(
                        search,
                        case=False,
                        na=False
                    ).any(),
                    axis=1
                )
            )

            display_df = display_df[mask]


        st.dataframe(
            display_df[
                ITEM_COLUMNS
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # UPDATE ITEM
    # ========================================================

    with tab3:

        st.subheader("Update Item")

        if items.empty:

            st.info(
                "No items available for update."
            )

        else:

            selected_item = st.selectbox(
                "Select Item_ID",
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )


            selected_row = items[
                items["Item_ID"].astype(str)
                == selected_item
            ].iloc[0]


            with st.form("update_item_form"):

                material_grade = st.selectbox(
                    "Material Grade",
                    [
                        "PE-80",
                        "PE-100"
                    ],
                    index=(
                        [
                            "PE-80",
                            "PE-100"
                        ].index(
                            selected_row[
                                "Material_Grade"
                            ]
                        )
                        if selected_row[
                            "Material_Grade"
                        ] in ["PE-80", "PE-100"]
                        else 0
                    )
                )


                application_options = [
                    "Water",
                    "Sewerage",
                    "Gas",
                    "Other"
                ]


                current_application = (
                    selected_row[
                        "Application"
                    ]
                )


                application_index = (
                    application_options.index(
                        current_application
                    )
                    if current_application
                    in application_options
                    else 0
                )


                application = st.selectbox(
                    "Application",
                    application_options,
                    index=application_index
                )


                c1, c2 = st.columns(2)


                with c1:

                    diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=safe_number(
                            selected_row[
                                "Nominal_Diameter_mm"
                            ]
                        )
                    )

                    wall_thickness = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=safe_number(
                            selected_row[
                                "Wall_Thickness_mm"
                            ]
                        )
                    )

                    sdr = st.number_input(
                        "SDR",
                        min_value=0.0,
                        value=safe_number(
                            selected_row["SDR"]
                        )
                    )


                with c2:

                    color = st.text_input(
                        "Color",
                        value=str(
                            selected_row["Color"]
                            if pd.notna(
                                selected_row["Color"]
                            )
                            else ""
                        )
                    )

                    standard_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=safe_number(
                            selected_row[
                                "Standard_Length"
                            ]
                        )
                    )

                    unit = st.text_input(
                        "Unit",
                        value=str(
                            selected_row["Unit"]
                            if pd.notna(
                                selected_row["Unit"]
                            )
                            else "m"
                        )
                    )


                submitted = st.form_submit_button(
                    "💾 Update Item",
                    use_container_width=True
                )


                if submitted:

                    record = {

                        "Material_Grade":
                            material_grade,

                        "Application":
                            application,

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall_thickness,

                        "SDR":
                            sdr,

                        "Color":
                            color,

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit
                    }


                    if update_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_item,
                        record
                    ):

                        st.success(
                            "Item successfully updated."
                        )

                        st.rerun()


    # ========================================================
    # DELETE ITEM
    # ========================================================

    with tab4:

        st.subheader("Delete Item")

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            delete_item = st.selectbox(
                "Select Item_ID to Delete",
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist(),
                key="delete_item_select"
            )


            confirm = st.checkbox(
                "I confirm that I want to delete this item."
            )


            if st.button(
                "🗑️ Delete Item",
                type="secondary"
            ):

                if not confirm:

                    st.warning(
                        "Please confirm deletion first."
                    )

                else:

                    if delete_record(
                        TABLES["Items"],
                        "Item_ID",
                        delete_item
                    ):

                        st.success(
                            "Item deleted successfully."
                        )

                        st.rerun()


# ============================================================
# PRODUCTION
# ============================================================

elif page == "Production":

    st.markdown(
        '<div class="section-title">🏭 Production Management</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Manage manufacturing production records."
    )


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "➕ Create",
            "🔎 Search / Read",
            "✏️ Update",
            "🗑️ Delete"
        ]
    )


    # ========================================================
    # CREATE PRODUCTION
    # ========================================================

    with tab1:

        st.subheader("Add Production Record")

        with st.form("add_production_form"):

            c1, c2 = st.columns(2)


            with c1:

                production_id = st.text_input(
                    "Production ID *"
                )

                item_id = st.text_input(
                    "Item ID *"
                )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

                batch_no = st.text_input(
                    "Batch No"
                )

                production_line = st.text_input(
                    "Production Line"
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
                        "Rejected",
                        "On Hold"
                    ]
                )


            submitted = st.form_submit_button(
                "➕ Add Production",
                use_container_width=True
            )


            if submitted:

                if not production_id.strip():

                    st.error(
                        "Production_ID is required."
                    )

                elif not item_id.strip():

                    st.error(
                        "Item_ID is required."
                    )

                else:

                    record = {

                        "Production_ID":
                            production_id.strip(),

                        "Item_ID":
                            item_id.strip(),

                        "Production_Date":
                            str(production_date),

                        "Batch_No":
                            batch_no,

                        "Production_Line":
                            production_line,

                        "Planned_Qty_m":
                            planned_qty,

                        "Good_Qty_m":
                            good_qty,

                        "Rejected_Qty_m":
                            rejected_qty,

                        "Production_Status":
                            production_status
                    }


                    if insert_record(
                        TABLES["Production"],
                        record
                    ):

                        st.success(
                            "Production record added."
                        )

                        st.rerun()


    # ========================================================
    # READ PRODUCTION
    # ========================================================

    with tab2:

        st.subheader("Production Records")

        search = st.text_input(
            "Search Production",
            placeholder="Production ID, Item ID, Batch No..."
        )


        display_df = production.copy()


        if search:

            mask = (
                display_df
                .astype(str)
                .apply(
                    lambda row:
                    row.str.contains(
                        search,
                        case=False,
                        na=False
                    ).any(),
                    axis=1
                )
            )

            display_df = display_df[mask]


        st.dataframe(
            display_df[
                PRODUCTION_COLUMNS
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # UPDATE PRODUCTION
    # ========================================================

    with tab3:

        st.subheader("Update Production")

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


            selected_production = st.selectbox(
                "Select Production_ID",
                production_ids
            )


            row = production[
                production["Production_ID"]
                .astype(str)
                == selected_production
            ].iloc[0]


            with st.form("update_production_form"):

                c1, c2 = st.columns(2)


                with c1:

                    item_id = st.text_input(
                        "Item ID",
                        value=str(
                            row["Item_ID"]
                        )
                    )


                    current_date = pd.to_datetime(
                        row["Production_Date"],
                        errors="coerce"
                    )


                    if pd.isna(current_date):

                        current_date = date.today()

                    else:

                        current_date = current_date.date()


                    production_date = st.date_input(
                        "Production Date",
                        value=current_date
                    )


                    batch_no = st.text_input(
                        "Batch No",
                        value=str(
                            row["Batch_No"]
                            if pd.notna(
                                row["Batch_No"]
                            )
                            else ""
                        )
                    )


                    production_line = st.text_input(
                        "Production Line",
                        value=str(
                            row["Production_Line"]
                            if pd.notna(
                                row["Production_Line"]
                            )
                            else ""
                        )
                    )


                with c2:

                    planned_qty = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Planned_Qty_m"]
                        )
                    )


                    good_qty = st.number_input(
                        "Good Quantity (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Good_Qty_m"]
                        )
                    )


                    rejected_qty = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Rejected_Qty_m"]
                        )
                    )


                    statuses = [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected",
                        "On Hold"
                    ]


                    current_status = row[
                        "Production_Status"
                    ]


                    status_index = (
                        statuses.index(
                            current_status
                        )
                        if current_status in statuses
                        else 0
                    )


                    production_status = st.selectbox(
                        "Production Status",
                        statuses,
                        index=status_index
                    )


                submitted = st.form_submit_button(
                    "💾 Update Production",
                    use_container_width=True
                )


                if submitted:

                    record = {

                        "Item_ID":
                            item_id,

                        "Production_Date":
                            str(production_date),

                        "Batch_No":
                            batch_no,

                        "Production_Line":
                            production_line,

                        "Planned_Qty_m":
                            planned_qty,

                        "Good_Qty_m":
                            good_qty,

                        "Rejected_Qty_m":
                            rejected_qty,

                        "Production_Status":
                            production_status
                    }


                    if update_record(
                        TABLES["Production"],
                        "Production_ID",
                        selected_production,
                        record
                    ):

                        st.success(
                            "Production updated successfully."
                        )

                        st.rerun()


    # ========================================================
    # DELETE PRODUCTION
    # ========================================================

    with tab4:

        st.subheader("Delete Production")

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            delete_production = st.selectbox(
                "Select Production_ID",
                production[
                    "Production_ID"
                ]
                .dropna()
                .astype(str)
                .tolist(),
                key="delete_production"
            )


            confirm = st.checkbox(
                "I confirm that I want to delete this production record."
            )


            if st.button(
                "🗑️ Delete Production"
            ):

                if not confirm:

                    st.warning(
                        "Please confirm deletion first."
                    )

                else:

                    if delete_record(
                        TABLES["Production"],
                        "Production_ID",
                        delete_production
                    ):

                        st.success(
                            "Production record deleted."
                        )

                        st.rerun()


# ============================================================
# STOCK CONTROL
# ============================================================

elif page == "Stock Control":

    st.markdown(
        '<div class="section-title">📦 Stock Control</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Manage inventory, produced quantity and dispatches."
    )


    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "➕ Create",
            "🔎 Search / Read",
            "✏️ Update",
            "🗑️ Delete"
        ]
    )


    # ========================================================
    # CREATE STOCK
    # ========================================================

    with tab1:

        st.subheader("Add Stock Record")

        with st.form("add_stock_form"):

            c1, c2 = st.columns(2)


            with c1:

                stock_id = st.text_input(
                    "Stock ID *"
                )

                item_id = st.text_input(
                    "Item ID *"
                )

                production_id = st.text_input(
                    "Production ID *"
                )

                batch_no = st.text_input(
                    "Batch No"
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
                        "Out of Stock",
                        "Reserved",
                        "Dispatched"
                    ]
                )


            submitted = st.form_submit_button(
                "➕ Add Stock",
                use_container_width=True
            )


            if submitted:

                if not stock_id.strip():

                    st.error(
                        "Stock_ID is required."
                    )

                elif not item_id.strip():

                    st.error(
                        "Item_ID is required."
                    )

                else:

                    record = {

                        "Stock_ID":
                            stock_id.strip(),

                        "Item_ID":
                            item_id.strip(),

                        "Production_ID":
                            production_id.strip(),

                        "Batch_No":
                            batch_no,

                        "Stock_Date":
                            str(stock_date),

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


                    if insert_record(
                        TABLES["Stock"],
                        record
                    ):

                        st.success(
                            "Stock record added successfully."
                        )

                        st.rerun()


    # ========================================================
    # READ STOCK
    # ========================================================

    with tab2:

        st.subheader("Stock Records")

        search = st.text_input(
            "Search Stock",
            placeholder="Stock ID, Item ID, Production ID, Batch No..."
        )


        display_df = stock.copy()


        if search:

            mask = (
                display_df
                .astype(str)
                .apply(
                    lambda row:
                    row.str.contains(
                        search,
                        case=False,
                        na=False
                    ).any(),
                    axis=1
                )
            )

            display_df = display_df[mask]


        st.dataframe(
            display_df[
                STOCK_COLUMNS
            ],
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # UPDATE STOCK
    # ========================================================

    with tab3:

        st.subheader("Update Stock")

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


            selected_stock = st.selectbox(
                "Select Stock_ID",
                stock_ids
            )


            row = stock[
                stock["Stock_ID"]
                .astype(str)
                == selected_stock
            ].iloc[0]


            with st.form("update_stock_form"):

                c1, c2 = st.columns(2)


                with c1:

                    item_id = st.text_input(
                        "Item ID",
                        value=str(
                            row["Item_ID"]
                        )
                    )


                    production_id = st.text_input(
                        "Production ID",
                        value=str(
                            row["Production_ID"]
                            if pd.notna(
                                row["Production_ID"]
                            )
                            else ""
                        )
                    )


                    batch_no = st.text_input(
                        "Batch No",
                        value=str(
                            row["Batch_No"]
                            if pd.notna(
                                row["Batch_No"]
                            )
                            else ""
                        )
                    )


                    current_date = pd.to_datetime(
                        row["Stock_Date"],
                        errors="coerce"
                    )


                    if pd.isna(current_date):

                        current_date = date.today()

                    else:

                        current_date = current_date.date()


                    stock_date = st.date_input(
                        "Stock Date",
                        value=current_date
                    )


                with c2:

                    opening_stock = st.number_input(
                        "Opening Stock (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Opening_Stock_m"]
                        )
                    )


                    produced_qty = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Produced_Qty_m"]
                        )
                    )


                    dispatched_qty = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Dispatched_Qty_m"]
                        )
                    )


                    closing_stock = st.number_input(
                        "Closing Stock (m)",
                        min_value=0.0,
                        value=safe_number(
                            row["Closing_Stock_m"]
                        )
                    )


                    statuses = [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved",
                        "Dispatched"
                    ]


                    current_status = row[
                        "Stock_Status"
                    ]


                    status_index = (
                        statuses.index(
                            current_status
                        )
                        if current_status in statuses
                        else 0
                    )


                    stock_status = st.selectbox(
                        "Stock Status",
                        statuses,
                        index=status_index
                    )


                submitted = st.form_submit_button(
                    "💾 Update Stock",
                    use_container_width=True
                )


                if submitted:

                    record = {

                        "Item_ID":
                            item_id,

                        "Production_ID":
                            production_id,

                        "Batch_No":
                            batch_no,

                        "Stock_Date":
                            str(stock_date),

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


                    if update_record(
                        TABLES["Stock"],
                        "Stock_ID",
                        selected_stock,
                        record
                    ):

                        st.success(
                            "Stock updated successfully."
                        )

                        st.rerun()


    # ========================================================
    # DELETE STOCK
    # ========================================================

    with tab4:

        st.subheader("Delete Stock")

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            delete_stock = st.selectbox(
                "Select Stock_ID",
                stock[
                    "Stock_ID"
                ]
                .dropna()
                .astype(str)
                .tolist(),
                key="delete_stock"
            )


            confirm = st.checkbox(
                "I confirm that I want to delete this stock record."
            )


            if st.button(
                "🗑️ Delete Stock"
            ):

                if not confirm:

                    st.warning(
                        "Please confirm deletion first."
                    )

                else:

                    if delete_record(
                        TABLES["Stock"],
                        "Stock_ID",
                        delete_stock
                    ):

                        st.success(
                            "Stock record deleted."
                        )

                        st.rerun()


# ============================================================
# CUSTOM DASHBOARD
# ============================================================

elif page == "Custom Dashboard":

    st.markdown(
        '<div class="section-title">📊 Custom Dashboard</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Detailed operational view of production and inventory."
    )


    # --------------------------------------------------------
    # Production by Line
    # --------------------------------------------------------

    st.subheader("🏭 Production by Line")

    if not production.empty:

        line_data = (
            production
            .groupby(
                "Production_Line",
                as_index=False
            )
            .agg({
                "Planned_Qty_m": "sum",
                "Good_Qty_m": "sum",
                "Rejected_Qty_m": "sum"
            })
        )


        line_data["Yield_%"] = (
            line_data["Good_Qty_m"]
            /
            (
                line_data["Good_Qty_m"]
                +
                line_data["Rejected_Qty_m"]
            )
            .replace(0, 1)
        ) * 100


        fig = px.bar(
            line_data,
            x="Production_Line",
            y=[
                "Planned_Qty_m",
                "Good_Qty_m",
                "Rejected_Qty_m"
            ],
            barmode="group",
            title="Production by Manufacturing Line"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


        st.dataframe(
            line_data,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No production data available."
        )


    # --------------------------------------------------------
    # Stock Status
    # --------------------------------------------------------

    st.subheader("📦 Stock Status")

    if not stock.empty:

        stock_status_data = (
            stock
            .groupby(
                "Stock_Status",
                as_index=False
            )["Closing_Stock_m"]
            .sum()
        )


        fig = px.pie(
            stock_status_data,
            names="Stock_Status",
            values="Closing_Stock_m",
            hole=0.45,
            title="Stock Distribution by Status"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "No stock data available."
        )


# ============================================================
# ANALYTICS
# ============================================================

elif page == "Analytics":

    st.markdown(
        '<div class="section-title">📈 Analytics</div>',
        unsafe_allow_html=True
    )


    # ========================================================
    # PRODUCTION ANALYTICS
    # ========================================================

    st.subheader("Production Analytics")


    if not production.empty:

        analytics = production.copy()


        analytics["Planned_Qty_m"] = pd.to_numeric(
            analytics["Planned_Qty_m"],
            errors="coerce"
        ).fillna(0)


        analytics["Good_Qty_m"] = pd.to_numeric(
            analytics["Good_Qty_m"],
            errors="coerce"
        ).fillna(0)


        analytics["Rejected_Qty_m"] = pd.to_numeric(
            analytics["Rejected_Qty_m"],
            errors="coerce"
        ).fillna(0)


        total_planned = analytics[
            "Planned_Qty_m"
        ].sum()


        total_good = analytics[
            "Good_Qty_m"
        ].sum()


        total_rejected = analytics[
            "Rejected_Qty_m"
        ].sum()


        total_production = (
            total_good +
            total_rejected
        )


        if total_production > 0:

            overall_yield = (
                total_good /
                total_production
            ) * 100

        else:

            overall_yield = 0


        c1, c2, c3, c4 = st.columns(4)


        with c1:

            st.metric(
                "Total Planned",
                f"{format_number(total_planned)} m"
            )


        with c2:

            st.metric(
                "Total Good",
                f"{format_number(total_good)} m"
            )


        with c3:

            st.metric(
                "Total Rejected",
                f"{format_number(total_rejected)} m"
            )


        with c4:

            st.metric(
                "Overall Yield",
                f"{overall_yield:.2f}%"
            )


        st.divider()


        # ----------------------------------------------------
        # Planned vs Good vs Rejected
        # ----------------------------------------------------

        st.subheader(
            "Planned vs Good vs Rejected"
        )


        production_compare = pd.DataFrame({

            "Type": [
                "Planned",
                "Good",
                "Rejected"
            ],

            "Quantity": [
                total_planned,
                total_good,
                total_rejected
            ]

        })


        fig = px.bar(
            production_compare,
            x="Type",
            y="Quantity",
            text_auto=True,
            title="Overall Production Comparison"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


        # ----------------------------------------------------
        # Item Production
        # ----------------------------------------------------

        st.subheader(
            "Production by Item"
        )


        item_production = (
            analytics
            .groupby(
                "Item_ID",
                as_index=False
            )
            .agg({
                "Planned_Qty_m": "sum",
                "Good_Qty_m": "sum",
                "Rejected_Qty_m": "sum"
            })
        )


        fig = px.bar(
            item_production,
            x="Item_ID",
            y=[
                "Good_Qty_m",
                "Rejected_Qty_m"
            ],
            barmode="group",
            title="Good vs Rejected Production by Item"
        )


        st.plotly_chart(
            fig,
            use_container_width=True
        )


    else:

        st.info(
            "No production data available for analytics."
        )


    # ========================================================
    # STOCK ANALYTICS
    # ========================================================

    st.subheader("Inventory Analytics")


    if not stock.empty:

        stock_analysis = stock.copy()


        for col in [
            "Opening_Stock_m",
            "Produced_Qty_m",
            "Dispatched_Qty_m",
            "Closing_Stock_m"
        ]:

            stock_analysis[col] = pd.to_numeric(
                stock_analysis[col],
                errors="coerce"
            ).fillna(0)


        total_opening = stock_analysis[
            "Opening_Stock_m"
        ].sum()


        total_produced = stock_analysis[
            "Produced_Qty_m"
        ].sum()


        total_dispatched = stock_analysis[
            "Dispatched_Qty_m"
        ].sum()


        total_closing = stock_analysis[
            "Closing_Stock_m"
        ].sum()


        c1, c2, c3, c4 = st.columns(4)


        with c1:

            st.metric(
                "Opening Stock",
                f"{format_number(total_opening)} m"
            )


        with c2:

            st.metric(
                "Produced",
                f"{format_number(total_produced)} m"
            )


        with c3:

            st.metric(
                "Dispatched",
                f"{format_number(total_dispatched)} m"
            )


        with c4:

            st.metric(
                "Closing Stock",
                f"{format_number(total_closing)} m"
            )


        stock_by_item = (
            stock_analysis
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


        fig = px.bar(
            stock_by_item,
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


        st.dataframe(
            stock_by_item,
            use_container_width=True,
            hide_index=True
        )


    else:

        st.info(
            "No stock data available for analytics."
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

elif page == "Data Management":

    st.markdown(
        '<div class="section-title">🗄️ Data Management</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Live data currently loaded from Supabase."
    )


    # ========================================================
    # DATABASE STATUS
    # ========================================================

    if db_connected:

        st.markdown("""
        <div class="status-card success-status">
            🟢 <b>Supabase Connected</b><br>
            Live database connection is active.
        </div>
        """, unsafe_allow_html=True)

    else:

        st.markdown(f"""
        <div class="status-card error-status">
            🔴 <b>Supabase Connection Failed</b><br>
            {db_message}
        </div>
        """, unsafe_allow_html=True)


    # ========================================================
    # ROW COUNTS
    # ========================================================

    st.subheader("Database Records")


    c1, c2, c3 = st.columns(3)


    with c1:

        st.metric(
            "Item Registration",
            len(items)
        )


    with c2:

        st.metric(
            "Production",
            len(production)
        )


    with c3:

        st.metric(
            "Stock Control",
            len(stock)
        )


    st.divider()


    # ========================================================
    # DATABASE DEBUG INFORMATION
    # ========================================================

    st.subheader("🔍 Database Verification")


    st.write(
        "This section confirms that the app is reading your actual Supabase tables."
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        st.write(
            "**Item_Registration columns:**"
        )

        st.code(
            "\n".join(
                items.columns.tolist()
            )
        )


    with c2:

        st.write(
            "**Production columns:**"
        )

        st.code(
            "\n".join(
                production.columns.tolist()
            )
        )


    with c3:

        st.write(
            "**Stock_Control columns:**"
        )

        st.code(
            "\n".join(
                stock.columns.tolist()
            )
        )


    st.divider()


    # ========================================================
    # TABLE VIEWER
    # ========================================================

    st.subheader("📋 Live Table Viewer")


    selected_table = st.selectbox(
        "Select Table",
        [
            "Item_Registration",
            "Production",
            "Stock_Control"
        ]
    )


    if selected_table == "Item_Registration":

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )


    elif selected_table == "Production":

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )


    elif selected_table == "Stock_Control":

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # REFRESH
    # ========================================================

    st.divider()


    if st.button(
        "🔄 Refresh Database Data",
        use_container_width=True
    ):

        clear_data_cache()

        st.rerun()
