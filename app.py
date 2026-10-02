import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# COMPANY
# ============================================================

COMPANY = "Flex Head Industries Pvt Ltd"


# ============================================================
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase_client():

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        client: Client = create_client(url, key)

        return client, True, "Supabase Client Ready"

    except Exception as e:

        return None, False, f"Supabase Connection Error: {e}"


supabase, db_connected, db_message = get_supabase_client()


# ============================================================
# DATABASE TABLE NAMES
# ============================================================

TABLES = {
    "Items": "item_registration",
    "Production": "production",
    "Stock": "stock_control"
}


# ============================================================
# EXPECTED COLUMNS
# ============================================================

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
    "Stock_Date",
    "Opening_Stock_m",
    "Produced_Qty_m",
    "Dispatched_Qty_m",
    "Closing_Stock_m"
]


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f7f9fc;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    .erp-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 0px;
    }

    .erp-subtitle {
        color: #6b7280;
        font-size: 15px;
        margin-top: 0px;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 3px 12px rgba(0,0,0,0.05);
        min-height: 145px;
    }

    .metric-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }

    .metric-label {
        color: #6b7280;
        font-size: 14px;
        font-weight: 600;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 800;
        margin-top: 5px;
    }

    .metric-caption {
        color: #9ca3af;
        font-size: 12px;
        margin-top: 4px;
    }

    .section-title {
        font-size: 23px;
        font-weight: 750;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    .status-box {
        padding: 10px 15px;
        border-radius: 10px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_number(value):

    try:
        if value is None:
            return 0.0

        if pd.isna(value):
            return 0.0

        return float(value)

    except Exception:
        return 0.0


def prepare_dataframe(df, expected_columns):

    if df is None:
        return pd.DataFrame(columns=expected_columns)

    df = pd.DataFrame(df)

    for col in expected_columns:

        if col not in df.columns:
            df[col] = None

    return df


def format_number(value):

    value = safe_number(value)

    if value.is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}"


# ============================================================
# SUPABASE READ FUNCTION
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

        data = response.data

        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    except Exception as e:

        st.error(
            f"Unable to load `{table_name}` from Supabase: {e}"
        )

        return pd.DataFrame()


# ============================================================
# LOAD ALL DATABASE DATA
# ============================================================

def load_all_data():

    items = load_table(TABLES["Items"])
    production = load_table(TABLES["Production"])
    stock = load_table(TABLES["Stock"])

    items = prepare_dataframe(
        items,
        ITEM_COLUMNS
    )

    production = prepare_dataframe(
        production,
        PRODUCTION_COLUMNS
    )

    stock = prepare_dataframe(
        stock,
        STOCK_COLUMNS
    )

    return items, production, stock


items, production, stock = load_all_data()


# ============================================================
# CRUD FUNCTIONS
# ============================================================

def insert_record(table_name, record):

    try:

        response = (
            supabase
            .table(table_name)
            .insert(record)
            .execute()
        )

        load_table.clear()

        return True, response

    except Exception as e:

        return False, str(e)


def update_record(table_name, record_id_column, record_id, record):

    try:

        response = (
            supabase
            .table(table_name)
            .update(record)
            .eq(record_id_column, record_id)
            .execute()
        )

        load_table.clear()

        return True, response

    except Exception as e:

        return False, str(e)


def delete_record(table_name, record_id_column, record_id):

    try:

        response = (
            supabase
            .table(table_name)
            .delete()
            .eq(record_id_column, record_id)
            .execute()
        )

        load_table.clear()

        return True, response

    except Exception as e:

        return False, str(e)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center;">
            <h1>🏭</h1>
            <h3>FLEX HEAD INDUSTRIES</h3>
            <p>ERP SYSTEM</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    if db_connected:

        st.success("● Supabase Client Ready")

    else:

        st.error("● Supabase Not Connected")

    st.divider()

    page = st.radio(
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

    st.caption("Flex Head Industries Pvt Ltd")
    st.caption("Manufacturing ERP System")


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="erp-title">{COMPANY}</div>
    <div class="erp-subtitle">
        Enterprise Resource Planning System
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

if page == "Executive Dashboard":

    st.header("Executive Dashboard")

    st.write(
        "Real-time overview of manufacturing, production and inventory."
    )

    # --------------------------------------------------------
    # Refresh
    # --------------------------------------------------------

    col_refresh, col_status = st.columns([1, 4])

    with col_refresh:

        if st.button("🔄 Refresh Data"):

            load_table.clear()
            st.rerun()

    with col_status:

        if db_connected:
            st.success(
                "Live data connected to Supabase"
            )
        else:
            st.error(
                "Supabase connection failed"
            )

    # --------------------------------------------------------
    # Ensure numeric columns
    # --------------------------------------------------------

    for col in [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]:

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

        stock[col] = pd.to_numeric(
            stock[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # Metrics
    # --------------------------------------------------------

    registered_items = len(items)

    good_production = production[
        "Good_Qty_m"
    ].sum()

    rejected_production = production[
        "Rejected_Qty_m"
    ].sum()

    planned_production = production[
        "Planned_Qty_m"
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
    # Metric Cards
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">▣</div>

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
            """,
            unsafe_allow_html=True
        )

    with c2:

        st.markdown(
            f"""
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
            """,
            unsafe_allow_html=True
        )

    with c3:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">▤</div>

                <div class="metric-label">
                    Current Stock
                </div>

                <div class="metric-value">
                    {format_number(current_stock)} m
                </div>

                <div class="metric-caption">
                    Available stock
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">%</div>

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
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # --------------------------------------------------------
    # Secondary Metrics
    # --------------------------------------------------------

    s1, s2, s3, s4 = st.columns(4)

    with s1:

        st.metric(
            "Planned Production",
            f"{format_number(planned_production)} m"
        )

    with s2:

        st.metric(
            "Rejected",
            f"{format_number(rejected_production)} m"
        )

    with s3:

        st.metric(
            "Produced / Stock",
            f"{format_number(produced_stock)} m"
        )

    with s4:

        st.metric(
            "Dispatched",
            f"{format_number(dispatched)} m"
        )

    st.divider()

    # ========================================================
    # PRODUCTION OVERVIEW
    # ========================================================

    st.subheader("Production Overview")

    if not production.empty:

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:

            production_chart = production.copy()

            production_chart["Production_Date"] = pd.to_datetime(
                production_chart["Production_Date"],
                errors="coerce"
            )

            production_by_date = (
                production_chart
                .groupby("Production_Date", dropna=False)
                [["Good_Qty_m", "Rejected_Qty_m"]]
                .sum()
                .reset_index()
            )

            production_by_date = production_by_date.dropna(
                subset=["Production_Date"]
            )

            if not production_by_date.empty:

                fig = px.line(
                    production_by_date,
                    x="Production_Date",
                    y=[
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ],
                    markers=True,
                    title="Good vs Rejected Production"
                )

                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Quantity (m)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info("No valid production dates available.")

        with chart_col2:

            if "Production_Status" in production.columns:

                status_data = (
                    production[
                        "Production_Status"
                    ]
                    .fillna("Unknown")
                    .value_counts()
                    .reset_index()
                )

                status_data.columns = [
                    "Status",
                    "Count"
                ]

                if not status_data.empty:

                    fig_status = px.pie(
                        status_data,
                        names="Status",
                        values="Count",
                        title="Production Status"
                    )

                    st.plotly_chart(
                        fig_status,
                        use_container_width=True
                    )

                else:

                    st.info(
                        "No production status data."
                    )

    else:

        st.info(
            "No production data available from Supabase."
        )

    # ========================================================
    # CURRENT STOCK
    # ========================================================

    st.subheader("Current Stock by Item")

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

            stock_chart = stock_chart.merge(
                item_lookup,
                on="Item_ID",
                how="left"
            )

            stock_chart["Item_Code"] = (
                stock_chart["Item_Code"]
                .fillna(stock_chart["Item_ID"])
            )

            stock_by_item = (
                stock_chart
                .groupby("Item_Code")[
                    "Closing_Stock_m"
                ]
                .sum()
                .reset_index()
            )

        else:

            stock_by_item = (
                stock_chart
                .groupby("Item_ID")[
                    "Closing_Stock_m"
                ]
                .sum()
                .reset_index()
            )

            stock_by_item = stock_by_item.rename(
                columns={
                    "Item_ID": "Item_Code"
                }
            )

        if not stock_by_item.empty:

            fig_stock = px.bar(
                stock_by_item,
                x="Item_Code",
                y="Closing_Stock_m",
                title="Current Closing Stock",
                text_auto=True
            )

            fig_stock.update_layout(
                xaxis_title="Item",
                yaxis_title="Stock (m)"
            )

            st.plotly_chart(
                fig_stock,
                use_container_width=True
            )

        else:

            st.info("No stock data available.")

    else:

        st.info(
            "No stock data available from Supabase."
        )


# ============================================================
# ITEM REGISTRATION
# ============================================================

elif page == "Item Registration":

    st.header("Item Registration")

    st.write(
        "Manage pipe products and item specifications."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 View Items",
            "➕ Add Item",
            "✏️ Update / Delete"
        ]
    )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        search = st.text_input(
            "🔎 Search Item",
            placeholder="Search Item ID, Code, Grade, Application..."
        )

        display_items = items.copy()

        if search:

            mask = (
                display_items
                .astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )

            display_items = display_items[mask]

        st.dataframe(
            display_items,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"Showing {len(display_items)} of {len(items)} items"
        )

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        with st.form("add_item_form"):

            col1, col2 = st.columns(2)

            with col1:

                item_id = st.text_input(
                    "Item ID *"
                )

                item_code = st.text_input(
                    "Item Code *"
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

                nominal_diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0
                )

                wall_thickness = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1
                )

            with col2:

                sdr = st.number_input(
                    "SDR",
                    min_value=0.0,
                    step=0.1
                )

                color = st.text_input(
                    "Color",
                    value="Black"
                )

                standard_length = st.number_input(
                    "Standard Length (m)",
                    min_value=0.0,
                    step=1.0
                )

                unit = st.selectbox(
                    "Unit",
                    [
                        "Meter",
                        "Piece"
                    ]
                )

            submitted = st.form_submit_button(
                "➕ Register Item",
                use_container_width=True
            )

            if submitted:

                if not item_id or not item_code:

                    st.error(
                        "Item ID and Item Code are required."
                    )

                else:

                    duplicate = items[
                        items["Item_ID"]
                        .astype(str)
                        == str(item_id)
                    ]

                    if not duplicate.empty:

                        st.error(
                            "This Item ID already exists."
                        )

                    else:

                        record = {
                            "Item_ID": item_id,
                            "Item_Code": item_code,
                            "Material_Grade": material_grade,
                            "Application": application,
                            "Nominal_Diameter_mm": nominal_diameter,
                            "Wall_Thickness_mm": wall_thickness,
                            "SDR": sdr,
                            "Color": color,
                            "Standard_Length": standard_length,
                            "Unit": unit
                        }

                        success, result = insert_record(
                            TABLES["Items"],
                            record
                        )

                        if success:

                            st.success(
                                "Item registered successfully."
                            )

                            st.rerun()

                        else:

                            st.error(
                                f"Insert failed: {result}"
                            )

    # --------------------------------------------------------
    # UPDATE DELETE
    # --------------------------------------------------------

    with tab3:

        if items.empty:

            st.info("No items available.")

        else:

            selected_item = st.selectbox(
                "Select Item",
                items["Item_ID"]
                .astype(str)
                .tolist()
            )

            selected_row = items[
                items["Item_ID"].astype(str)
                == selected_item
            ]

            if not selected_row.empty:

                row = selected_row.iloc[0]

                with st.form("edit_item_form"):

                    new_code = st.text_input(
                        "Item Code",
                        value=str(
                            row.get("Item_Code", "")
                        )
                    )

                    new_grade = st.text_input(
                        "Material Grade",
                        value=str(
                            row.get(
                                "Material_Grade",
                                ""
                            )
                        )
                    )

                    new_application = st.text_input(
                        "Application",
                        value=str(
                            row.get(
                                "Application",
                                ""
                            )
                        )
                    )

                    new_diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        value=safe_number(
                            row.get(
                                "Nominal_Diameter_mm",
                                0
                            )
                        )
                    )

                    new_wall = st.number_input(
                        "Wall Thickness (mm)",
                        value=safe_number(
                            row.get(
                                "Wall_Thickness_mm",
                                0
                            )
                        )
                    )

                    new_sdr = st.number_input(
                        "SDR",
                        value=safe_number(
                            row.get(
                                "SDR",
                                0
                            )
                        )
                    )

                    new_color = st.text_input(
                        "Color",
                        value=str(
                            row.get(
                                "Color",
                                ""
                            )
                        )
                    )

                    new_length = st.number_input(
                        "Standard Length",
                        value=safe_number(
                            row.get(
                                "Standard_Length",
                                0
                            )
                        )
                    )

                    new_unit = st.text_input(
                        "Unit",
                        value=str(
                            row.get(
                                "Unit",
                                ""
                            )
                        )
                    )

                    update_btn = st.form_submit_button(
                        "💾 Update Item",
                        use_container_width=True
                    )

                    if update_btn:

                        record = {
                            "Item_Code": new_code,
                            "Material_Grade": new_grade,
                            "Application": new_application,
                            "Nominal_Diameter_mm": new_diameter,
                            "Wall_Thickness_mm": new_wall,
                            "SDR": new_sdr,
                            "Color": new_color,
                            "Standard_Length": new_length,
                            "Unit": new_unit
                        }

                        success, result = update_record(
                            TABLES["Items"],
                            "Item_ID",
                            selected_item,
                            record
                        )

                        if success:

                            st.success(
                                "Item updated successfully."
                            )

                            st.rerun()

                        else:

                            st.error(
                                f"Update failed: {result}"
                            )

                st.divider()

                if st.button(
                    "🗑️ Delete Selected Item",
                    type="secondary"
                ):

                    success, result = delete_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_item
                    )

                    if success:

                        st.success(
                            "Item deleted successfully."
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"Delete failed: {result}"
                        )


# ============================================================
# PRODUCTION
# ============================================================

elif page == "Production":

    st.header("Production Management")

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Production Records",
            "➕ Add Production",
            "✏️ Update / Delete"
        ]
    )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        search = st.text_input(
            "🔎 Search Production",
            placeholder="Search Production ID, Item ID, Batch..."
        )

        display_production = production.copy()

        if search:

            mask = (
                display_production
                .astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )

            display_production = display_production[mask]

        st.dataframe(
            display_production,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        with st.form("add_production_form"):

            production_id = st.text_input(
                "Production ID *"
            )

            item_options = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if item_options:

                selected_item_id = st.selectbox(
                    "Item ID",
                    item_options
                )

            else:

                selected_item_id = st.text_input(
                    "Item ID"
                )

            production_date = st.date_input(
                "Production Date",
                value=date.today()
            )

            batch_no = st.text_input(
                "Batch No."
            )

            production_line = st.text_input(
                "Production Line"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with col2:

                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with col3:

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

            submit_production = st.form_submit_button(
                "➕ Add Production",
                use_container_width=True
            )

            if submit_production:

                if not production_id:

                    st.error(
                        "Production ID is required."
                    )

                elif not selected_item_id:

                    st.error(
                        "Item ID is required."
                    )

                else:

                    record = {
                        "Production_ID": production_id,
                        "Item_ID": selected_item_id,
                        "Production_Date": str(
                            production_date
                        ),
                        "Batch_No": batch_no,
                        "Production_Line": production_line,
                        "Planned_Qty_m": planned_qty,
                        "Good_Qty_m": good_qty,
                        "Rejected_Qty_m": rejected_qty,
                        "Production_Status": production_status
                    }

                    success, result = insert_record(
                        TABLES["Production"],
                        record
                    )

                    if success:

                        st.success(
                            "Production record added."
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"Insert failed: {result}"
                        )

    # --------------------------------------------------------
    # UPDATE DELETE
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

            selected_production = st.selectbox(
                "Select Production ID",
                production_ids
            )

            selected_row = production[
                production["Production_ID"]
                .astype(str)
                == selected_production
            ]

            if not selected_row.empty:

                row = selected_row.iloc[0]

                with st.form(
                    "update_production_form"
                ):

                    update_item = st.text_input(
                        "Item ID",
                        value=str(
                            row.get(
                                "Item_ID",
                                ""
                            )
                        )
                    )

                    update_date = st.date_input(
                        "Production Date",
                        value=pd.to_datetime(
                            row.get(
                                "Production_Date",
                                date.today()
                            ),
                            errors="coerce"
                        ).date()
                        if pd.notna(
                            pd.to_datetime(
                                row.get(
                                    "Production_Date",
                                    None
                                ),
                                errors="coerce"
                            )
                        )
                        else date.today()
                    )

                    update_batch = st.text_input(
                        "Batch No.",
                        value=str(
                            row.get(
                                "Batch_No",
                                ""
                            )
                        )
                    )

                    update_line = st.text_input(
                        "Production Line",
                        value=str(
                            row.get(
                                "Production_Line",
                                ""
                            )
                        )
                    )

                    update_planned = st.number_input(
                        "Planned Qty (m)",
                        value=safe_number(
                            row.get(
                                "Planned_Qty_m",
                                0
                            )
                        )
                    )

                    update_good = st.number_input(
                        "Good Qty (m)",
                        value=safe_number(
                            row.get(
                                "Good_Qty_m",
                                0
                            )
                        )
                    )

                    update_rejected = st.number_input(
                        "Rejected Qty (m)",
                        value=safe_number(
                            row.get(
                                "Rejected_Qty_m",
                                0
                            )
                        )
                    )

                    update_status = st.selectbox(
                        "Production Status",
                        [
                            "Planned",
                            "In Progress",
                            "Completed",
                            "Rejected",
                            "On Hold"
                        ],
                        index=(
                            [
                                "Planned",
                                "In Progress",
                                "Completed",
                                "Rejected",
                                "On Hold"
                            ].index(
                                str(
                                    row.get(
                                        "Production_Status",
                                        "Planned"
                                    )
                                )
                            )
                            if str(
                                row.get(
                                    "Production_Status",
                                    "Planned"
                                )
                            ) in [
                                "Planned",
                                "In Progress",
                                "Completed",
                                "Rejected",
                                "On Hold"
                            ]
                            else 0
                        )
                    )

                    update_btn = st.form_submit_button(
                        "💾 Update Production",
                        use_container_width=True
                    )

                    if update_btn:

                        record = {
                            "Item_ID": update_item,
                            "Production_Date": str(
                                update_date
                            ),
                            "Batch_No": update_batch,
                            "Production_Line": update_line,
                            "Planned_Qty_m": update_planned,
                            "Good_Qty_m": update_good,
                            "Rejected_Qty_m": update_rejected,
                            "Production_Status": update_status
                        }

                        success, result = update_record(
                            TABLES["Production"],
                            "Production_ID",
                            selected_production,
                            record
                        )

                        if success:

                            st.success(
                                "Production updated."
                            )

                            st.rerun()

                        else:

                            st.error(
                                f"Update failed: {result}"
                            )

                if st.button(
                    "🗑️ Delete Production"
                ):

                    success, result = delete_record(
                        TABLES["Production"],
                        "Production_ID",
                        selected_production
                    )

                    if success:

                        st.success(
                            "Production deleted."
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"Delete failed: {result}"
                        )


# ============================================================
# STOCK CONTROL
# ============================================================

elif page == "Stock Control":

    st.header("Stock Control")

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Stock Records",
            "➕ Add Stock",
            "✏️ Update / Delete"
        ]
    )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    with tab1:

        search = st.text_input(
            "🔎 Search Stock",
            placeholder="Search Stock ID, Item ID, Production ID..."
        )

        display_stock = stock.copy()

        if search:

            mask = (
                display_stock
                .astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )

            display_stock = display_stock[mask]

        st.dataframe(
            display_stock,
            use_container_width=True,
            hide_index=True
        )

    # --------------------------------------------------------
    # ADD
    # --------------------------------------------------------

    with tab2:

        with st.form("add_stock_form"):

            stock_id = st.text_input(
                "Stock ID *"
            )

            item_options = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if item_options:

                stock_item_id = st.selectbox(
                    "Item ID",
                    item_options
                )

            else:

                stock_item_id = st.text_input(
                    "Item ID"
                )

            production_options = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if production_options:

                stock_production_id = st.selectbox(
                    "Production ID",
                    production_options
                )

            else:

                stock_production_id = st.text_input(
                    "Production ID"
                )

            stock_date = st.date_input(
                "Stock Date",
                value=date.today()
            )

            col1, col2 = st.columns(2)

            with col1:

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

            with col2:

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

            submit_stock = st.form_submit_button(
                "➕ Add Stock",
                use_container_width=True
            )

            if submit_stock:

                if not stock_id:

                    st.error(
                        "Stock ID is required."
                    )

                else:

                    record = {
                        "Stock_ID": stock_id,
                        "Item_ID": stock_item_id,
                        "Production_ID": stock_production_id,
                        "Stock_Date": str(
                            stock_date
                        ),
                        "Opening_Stock_m": opening_stock,
                        "Produced_Qty_m": produced_qty,
                        "Dispatched_Qty_m": dispatched_qty,
                        "Closing_Stock_m": closing_stock
                    }

                    success, result = insert_record(
                        TABLES["Stock"],
                        record
                    )

                    if success:

                        st.success(
                            "Stock record added."
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"Insert failed: {result}"
                        )

    # --------------------------------------------------------
    # UPDATE DELETE
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

            selected_stock = st.selectbox(
                "Select Stock ID",
                stock_ids
            )

            selected_row = stock[
                stock["Stock_ID"]
                .astype(str)
                == selected_stock
            ]

            if not selected_row.empty:

                row = selected_row.iloc[0]

                with st.form(
                    "update_stock_form"
                ):

                    update_item = st.text_input(
                        "Item ID",
                        value=str(
                            row.get(
                                "Item_ID",
                                ""
                            )
                        )
                    )

                    update_production = st.text_input(
                        "Production ID",
                        value=str(
                            row.get(
                                "Production_ID",
                                ""
                            )
                        )
                    )

                    update_stock_date = st.date_input(
                        "Stock Date",
                        value=pd.to_datetime(
                            row.get(
                                "Stock_Date",
                                date.today()
                            ),
                            errors="coerce"
                        ).date()
                        if pd.notna(
                            pd.to_datetime(
                                row.get(
                                    "Stock_Date",
                                    None
                                ),
                                errors="coerce"
                            )
                        )
                        else date.today()
                    )

                    update_opening = st.number_input(
                        "Opening Stock",
                        value=safe_number(
                            row.get(
                                "Opening_Stock_m",
                                0
                            )
                        )
                    )

                    update_produced = st.number_input(
                        "Produced Qty",
                        value=safe_number(
                            row.get(
                                "Produced_Qty_m",
                                0
                            )
                        )
                    )

                    update_dispatched = st.number_input(
                        "Dispatched Qty",
                        value=safe_number(
                            row.get(
                                "Dispatched_Qty_m",
                                0
                            )
                        )
                    )

                    update_closing = st.number_input(
                        "Closing Stock",
                        value=safe_number(
                            row.get(
                                "Closing_Stock_m",
                                0
                            )
                        )
                    )

                    update_btn = st.form_submit_button(
                        "💾 Update Stock",
                        use_container_width=True
                    )

                    if update_btn:

                        record = {
                            "Item_ID": update_item,
                            "Production_ID": update_production,
                            "Stock_Date": str(
                                update_stock_date
                            ),
                            "Opening_Stock_m": update_opening,
                            "Produced_Qty_m": update_produced,
                            "Dispatched_Qty_m": update_dispatched,
                            "Closing_Stock_m": update_closing
                        }

                        success, result = update_record(
                            TABLES["Stock"],
                            "Stock_ID",
                            selected_stock,
                            record
                        )

                        if success:

                            st.success(
                                "Stock updated."
                            )

                            st.rerun()

                        else:

                            st.error(
                                f"Update failed: {result}"
                            )

                if st.button(
                    "🗑️ Delete Stock"
                ):

                    success, result = delete_record(
                        TABLES["Stock"],
                        "Stock_ID",
                        selected_stock
                    )

                    if success:

                        st.success(
                            "Stock deleted."
                        )

                        st.rerun()

                    else:

                        st.error(
                            f"Delete failed: {result}"
                        )


# ============================================================
# CUSTOM DASHBOARD
# ============================================================

elif page == "Custom Dashboard":

    st.header("Custom Dashboard")

    st.write(
        "Create your own business analysis from live Supabase data."
    )

    dataset = st.selectbox(
        "Select Dataset",
        [
            "Items",
            "Production",
            "Stock"
        ]
    )

    if dataset == "Items":

        df = items.copy()

    elif dataset == "Production":

        df = production.copy()

    else:

        df = stock.copy()

    if df.empty:

        st.info(
            "No data available in Supabase."
        )

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Quick Statistics")

        numeric_cols = df.select_dtypes(
            include="number"
        ).columns.tolist()

        if numeric_cols:

            selected_numeric = st.selectbox(
                "Select Numeric Column",
                numeric_cols
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.metric(
                    "Total",
                    format_number(
                        df[selected_numeric].sum()
                    )
                )

            with c2:

                st.metric(
                    "Average",
                    format_number(
                        df[selected_numeric].mean()
                    )
                )

            with c3:

                st.metric(
                    "Maximum",
                    format_number(
                        df[selected_numeric].max()
                    )
                )

            with c4:

                st.metric(
                    "Minimum",
                    format_number(
                        df[selected_numeric].min()
                    )
                )


# ============================================================
# ANALYTICS
# ============================================================

elif page == "Analytics":

    st.header("Analytics")

    st.write(
        "Manufacturing performance analysis using live Supabase data."
    )

    # --------------------------------------------------------
    # Production Analysis
    # --------------------------------------------------------

    st.subheader("Production Performance")

    if production.empty:

        st.info(
            "No production data available."
        )

    else:

        production_analysis = production.copy()

        numeric_columns = [
            "Planned_Qty_m",
            "Good_Qty_m",
            "Rejected_Qty_m"
        ]

        for col in numeric_columns:

            production_analysis[col] = pd.to_numeric(
                production_analysis[col],
                errors="coerce"
            ).fillna(0)

        production_analysis["Total_Output_m"] = (
            production_analysis["Good_Qty_m"] +
            production_analysis["Rejected_Qty_m"]
        )

        production_analysis["Yield_%"] = 0.0

        mask = (
            production_analysis["Total_Output_m"] > 0
        )

        production_analysis.loc[
            mask,
            "Yield_%"
        ] = (
            production_analysis.loc[
                mask,
                "Good_Qty_m"
            ]
            /
            production_analysis.loc[
                mask,
                "Total_Output_m"
            ]
        ) * 100

        st.dataframe(
            production_analysis,
            use_container_width=True,
            hide_index=True
        )

        # Yield chart

        if "Production_ID" in production_analysis.columns:

            fig_yield = px.bar(
                production_analysis,
                x="Production_ID",
                y="Yield_%",
                title="Production Yield by Production ID",
                text_auto=".1f"
            )

            fig_yield.update_layout(
                yaxis_title="Yield (%)"
            )

            st.plotly_chart(
                fig_yield,
                use_container_width=True
            )

    # --------------------------------------------------------
    # Stock Analysis
    # --------------------------------------------------------

    st.subheader("Inventory Analysis")

    if stock.empty:

        st.info(
            "No stock data available."
        )

    else:

        stock_analysis = stock.copy()

        stock_numeric = [
            "Opening_Stock_m",
            "Produced_Qty_m",
            "Dispatched_Qty_m",
            "Closing_Stock_m"
        ]

        for col in stock_numeric:

            stock_analysis[col] = pd.to_numeric(
                stock_analysis[col],
                errors="coerce"
            ).fillna(0)

        stock_summary = (
            stock_analysis
            .groupby("Item_ID")[
                [
                    "Opening_Stock_m",
                    "Produced_Qty_m",
                    "Dispatched_Qty_m",
                    "Closing_Stock_m"
                ]
            ]
            .sum()
            .reset_index()
        )

        st.dataframe(
            stock_summary,
            use_container_width=True,
            hide_index=True
        )

        fig_inventory = px.bar(
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
            fig_inventory,
            use_container_width=True
        )

    # --------------------------------------------------------
    # Item Analysis
    # --------------------------------------------------------

    st.subheader("Product Analysis")

    if items.empty:

        st.info(
            "No item data available."
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            if "Material_Grade" in items.columns:

                grade_data = (
                    items[
                        "Material_Grade"
                    ]
                    .fillna("Unknown")
                    .value_counts()
                    .reset_index()
                )

                grade_data.columns = [
                    "Material Grade",
                    "Items"
                ]

                fig_grade = px.pie(
                    grade_data,
                    names="Material Grade",
                    values="Items",
                    title="Items by Material Grade"
                )

                st.plotly_chart(
                    fig_grade,
                    use_container_width=True
                )

        with col2:

            if "Application" in items.columns:

                application_data = (
                    items[
                        "Application"
                    ]
                    .fillna("Unknown")
                    .value_counts()
                    .reset_index()
                )

                application_data.columns = [
                    "Application",
                    "Items"
                ]

                fig_application = px.bar(
                    application_data,
                    x="Application",
                    y="Items",
                    title="Items by Application",
                    text_auto=True
                )

                st.plotly_chart(
                    fig_application,
                    use_container_width=True
                )


# ============================================================
# DATA MANAGEMENT
# ============================================================

elif page == "Data Management":

    st.header("Data Management")

    st.write(
        "Direct Supabase database information."
    )

    # --------------------------------------------------------
    # Connection
    # --------------------------------------------------------

    st.subheader("Supabase Connection")

    if db_connected:

        st.success(
            "Connected successfully to Supabase."
        )

    else:

        st.error(
            db_message
        )

    # --------------------------------------------------------
    # Table Counts
    # --------------------------------------------------------

    st.subheader("Database Tables")

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

    # --------------------------------------------------------
    # Table Viewer
    # --------------------------------------------------------

    selected_table = st.selectbox(
        "Select Table",
        [
            "item_registration",
            "production",
            "stock_control"
        ]
    )

    table_map = {
        "item_registration": items,
        "production": production,
        "stock_control": stock
    }

    selected_df = table_map[selected_table]

    st.dataframe(
        selected_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # Refresh Database
    # --------------------------------------------------------

    st.divider()

    if st.button(
        "🔄 Reload All Supabase Data",
        use_container_width=True
    ):

        load_table.clear()

        st.success(
            "Supabase data refreshed."
        )

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"© 2026 {COMPANY} | Enterprise Resource Planning System"
)
