```python
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

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
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: #172033;
}

.erp-title {
    font-size: 34px;
    font-weight: 800;
    color: #172033;
    margin-bottom: 3px;
}

.erp-subtitle {
    color: #667085;
    font-size: 15px;
    margin-bottom: 25px;
}

.metric-card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e7eaf0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    min-height: 145px;
}

.metric-icon {
    font-size: 28px;
    margin-bottom: 8px;
}

.metric-label {
    color: #667085;
    font-size: 14px;
    font-weight: 600;
}

.metric-value {
    color: #172033;
    font-size: 28px;
    font-weight: 800;
    margin-top: 4px;
}

.metric-caption {
    color: #98a2b3;
    font-size: 12px;
    margin-top: 4px;
}

.section-title {
    font-size: 21px;
    font-weight: 750;
    color: #172033;
    margin-top: 25px;
    margin-bottom: 12px;
}

.success-box {
    padding: 12px 16px;
    border-radius: 10px;
    background: #ecfdf3;
    border: 1px solid #abefc6;
    color: #067647;
    margin-bottom: 15px;
}

.warning-box {
    padding: 12px 16px;
    border-radius: 10px;
    background: #fffaeb;
    border: 1px solid #fedf89;
    color: #b54708;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_supabase_client() -> Client:

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        if not url or not key:
            raise ValueError("Supabase URL or Key is empty.")

        return create_client(url, key)

    except Exception as e:
        st.error("❌ Supabase connection failed.")
        st.error(str(e))
        st.stop()


supabase = get_supabase_client()


# =========================================================
# EXACT SUPABASE TABLE NAMES
# =========================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock": "Stock_Control"
}


# =========================================================
# EXPECTED COLUMNS
# =========================================================

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


# =========================================================
# LOAD TABLE
# =========================================================

def load_table(table_name):

    try:

        response = (
            supabase
            .table(table_name)
            .select("*")
            .execute()
        )

        data = response.data

        if data is None:
            return pd.DataFrame()

        return pd.DataFrame(data)

    except Exception as e:

        st.error(f"❌ Error loading `{table_name}`")
        st.error(str(e))

        return pd.DataFrame()


# =========================================================
# LOAD ALL DATA
# =========================================================

def load_all_data():

    items = load_table(TABLES["Items"])
    production = load_table(TABLES["Production"])
    stock = load_table(TABLES["Stock"])

    return items, production, stock


# =========================================================
# PREPARE DATAFRAME
# =========================================================

def prepare_dataframe(df, expected_columns):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in expected_columns:

        if col not in df.columns:
            df[col] = None

    return df


# =========================================================
# CACHE CLEAR
# =========================================================

def refresh_data():

    st.cache_data.clear()
    st.rerun()


# =========================================================
# INSERT DATA
# =========================================================

def insert_record(table_name, record):

    try:

        supabase.table(table_name).insert(record).execute()

        st.success("✅ Record added successfully.")

        st.rerun()

    except Exception as e:

        st.error("❌ Insert failed.")
        st.error(str(e))


# =========================================================
# UPDATE DATA
# =========================================================

def update_record(table_name, id_column, id_value, record):

    try:

        (
            supabase
            .table(table_name)
            .update(record)
            .eq(id_column, id_value)
            .execute()
        )

        st.success("✅ Record updated successfully.")

        st.rerun()

    except Exception as e:

        st.error("❌ Update failed.")
        st.error(str(e))


# =========================================================
# DELETE DATA
# =========================================================

def delete_record(table_name, id_column, id_value):

    try:

        (
            supabase
            .table(table_name)
            .delete()
            .eq(id_column, id_value)
            .execute()
        )

        st.success("✅ Record deleted successfully.")

        st.rerun()

    except Exception as e:

        st.error("❌ Delete failed.")
        st.error(str(e))


# =========================================================
# LOAD LIVE DATA
# =========================================================

items, production, stock = load_all_data()

items = prepare_dataframe(items, ITEM_COLUMNS)
production = prepare_dataframe(production, PRODUCTION_COLUMNS)
stock = prepare_dataframe(stock, STOCK_COLUMNS)


# =========================================================
# NUMERIC CONVERSION
# =========================================================

numeric_production_columns = [
    "Planned_Qty_m",
    "Good_Qty_m",
    "Rejected_Qty_m"
]

for col in numeric_production_columns:

    production[col] = pd.to_numeric(
        production[col],
        errors="coerce"
    ).fillna(0)


numeric_stock_columns = [
    "Opening_Stock_m",
    "Produced_Qty_m",
    "Dispatched_Qty_m",
    "Closing_Stock_m"
]

for col in numeric_stock_columns:

    stock[col] = pd.to_numeric(
        stock[col],
        errors="coerce"
    ).fillna(0)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🏭 Flex Head ERP")

st.sidebar.caption(
    "Pipe Manufacturing Management System"
)

st.sidebar.divider()

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

st.sidebar.info(
    "Live database: Supabase"
)

if st.sidebar.button("🔄 Refresh Data"):

    st.cache_data.clear()
    st.rerun()


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

if page == "Executive Dashboard":

    st.markdown(
        '<div class="erp-title">Executive Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="erp-subtitle">'
        'Real-time overview of manufacturing, production and inventory.'
        '</div>',
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # CALCULATIONS
    # -----------------------------------------------------

    registered_items = len(items)

    good_production = production["Good_Qty_m"].sum()

    rejected_production = production["Rejected_Qty_m"].sum()

    planned_production = production["Planned_Qty_m"].sum()

    produced_stock = stock["Produced_Qty_m"].sum()

    dispatched = stock["Dispatched_Qty_m"].sum()

    current_stock = stock["Closing_Stock_m"].sum()

    total_produced = good_production + rejected_production

    if total_produced > 0:

        production_yield = (
            good_production /
            total_produced
        ) * 100

    else:

        production_yield = 0


    # -----------------------------------------------------
    # METRIC CARDS
    # -----------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown(
            f"""
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
            """,
            unsafe_allow_html=True
        )


    with col2:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">✓</div>

                <div class="metric-label">
                    Good Production
                </div>

                <div class="metric-value">
                    {good_production:,.0f} m
                </div>

                <div class="metric-caption">
                    Accepted production
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col3:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">🏭</div>

                <div class="metric-label">
                    Current Stock
                </div>

                <div class="metric-value">
                    {current_stock:,.0f} m
                </div>

                <div class="metric-caption">
                    Available inventory
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col4:

        st.markdown(
            f"""
            <div class="metric-card">

                <div class="metric-icon">📈</div>

                <div class="metric-label">
                    Production Yield
                </div>

                <div class="metric-value">
                    {production_yield:.1f}%
                </div>

                <div class="metric-caption">
                    Good vs total production
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    # -----------------------------------------------------
    # SECONDARY METRICS
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">Production & Inventory Summary</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Planned Production",
        f"{planned_production:,.0f} m"
    )

    c2.metric(
        "Rejected Production",
        f"{rejected_production:,.0f} m"
    )

    c3.metric(
        "Produced to Stock",
        f"{produced_stock:,.0f} m"
    )

    c4.metric(
        "Dispatched",
        f"{dispatched:,.0f} m"
    )


    # -----------------------------------------------------
    # CHARTS
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">Production Overview</div>',
        unsafe_allow_html=True
    )

    chart_col1, chart_col2 = st.columns(2)


    # Production by date

    with chart_col1:

        if not production.empty:

            temp = production.copy()

            temp["Production_Date"] = pd.to_datetime(
                temp["Production_Date"],
                errors="coerce"
            )

            temp = temp.dropna(
                subset=["Production_Date"]
            )

            if not temp.empty:

                daily = (
                    temp
                    .groupby("Production_Date")[
                        [
                            "Planned_Qty_m",
                            "Good_Qty_m",
                            "Rejected_Qty_m"
                        ]
                    ]
                    .sum()
                    .reset_index()
                )

                fig = px.line(
                    daily,
                    x="Production_Date",
                    y=[
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ],
                    markers=True,
                    title="Production by Date"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info("No valid production dates available.")

        else:

            st.info("No production data available.")


    # Production status

    with chart_col2:

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
                title="Production Status"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No production status data available.")


    # -----------------------------------------------------
    # STOCK CHART
    # -----------------------------------------------------

    st.markdown(
        '<div class="section-title">Current Stock by Item</div>',
        unsafe_allow_html=True
    )

    if not stock.empty:

        stock_chart = (
            stock
            .groupby("Item_ID")["Closing_Stock_m"]
            .sum()
            .reset_index()
            .sort_values(
                "Closing_Stock_m",
                ascending=False
            )
        )

        if not stock_chart.empty:

            fig = px.bar(
                stock_chart,
                x="Item_ID",
                y="Closing_Stock_m",
                title="Closing Stock by Item"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No stock data available.")

    else:

        st.info("No stock data available.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.title("📦 Item Registration")

    st.write(
        "Manage pipe product master data."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Item",
            "✏️ Update Item",
            "🗑️ Delete Item"
        ]
    )


    # -----------------------------------------------------
    # ADD ITEM
    # -----------------------------------------------------

    with tab1:

        with st.form("add_item_form"):

            item_id = st.text_input(
                "Item ID"
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
                    "Gas"
                ]
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=1.0
                )

            with c2:

                wall = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    step=0.1
                )

            with c3:

                sdr = st.number_input(
                    "SDR",
                    min_value=0.0,
                    step=0.1
                )

            c4, c5, c6 = st.columns(3)

            with c4:

                color = st.text_input(
                    "Color"
                )

            with c5:

                standard_length = st.number_input(
                    "Standard Length",
                    min_value=0.0,
                    step=1.0
                )

            with c6:

                unit = st.text_input(
                    "Unit",
                    value="m"
                )

            submitted = st.form_submit_button(
                "➕ Add Item"
            )

            if submitted:

                if not item_id.strip():

                    st.warning(
                        "Item ID is required."
                    )

                else:

                    record = {

                        "Item_ID":
                            item_id.strip(),

                        "Material_Grade":
                            material_grade,

                        "Application":
                            application,

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall,

                        "SDR":
                            sdr,

                        "Color":
                            color,

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit

                    }

                    insert_record(
                        TABLES["Items"],
                        record
                    )


    # -----------------------------------------------------
    # UPDATE ITEM
    # -----------------------------------------------------

    with tab2:

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            selected_item = st.selectbox(
                "Select Item ID",
                items["Item_ID"].astype(str).tolist()
            )

            row = items[
                items["Item_ID"].astype(str)
                == str(selected_item)
            ]

            if not row.empty:

                current = row.iloc[0]

                material_grade = st.selectbox(
                    "Material Grade",
                    ["PE-80", "PE-100"],
                    index=(
                        1
                        if current["Material_Grade"] == "PE-100"
                        else 0
                    )
                )

                application_options = [
                    "Water",
                    "Sewerage",
                    "Gas"
                ]

                current_application = current[
                    "Application"
                ]

                app_index = (
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
                    index=app_index
                )

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    value=float(
                        pd.to_numeric(
                            current[
                                "Nominal_Diameter_mm"
                            ],
                            errors="coerce"
                        ) or 0
                    )
                )

                wall = st.number_input(
                    "Wall Thickness (mm)",
                    value=float(
                        pd.to_numeric(
                            current[
                                "Wall_Thickness_mm"
                            ],
                            errors="coerce"
                        ) or 0
                    )
                )

                sdr = st.number_input(
                    "SDR",
                    value=float(
                        pd.to_numeric(
                            current["SDR"],
                            errors="coerce"
                        ) or 0
                    )
                )

                color = st.text_input(
                    "Color",
                    value=str(
                        current["Color"]
                        if pd.notna(current["Color"])
                        else ""
                    )
                )

                standard_length = st.number_input(
                    "Standard Length",
                    value=float(
                        pd.to_numeric(
                            current[
                                "Standard_Length"
                            ],
                            errors="coerce"
                        ) or 0
                    )
                )

                unit = st.text_input(
                    "Unit",
                    value=str(
                        current["Unit"]
                        if pd.notna(current["Unit"])
                        else "m"
                    )
                )

                if st.button(
                    "💾 Update Item"
                ):

                    record = {

                        "Material_Grade":
                            material_grade,

                        "Application":
                            application,

                        "Nominal_Diameter_mm":
                            diameter,

                        "Wall_Thickness_mm":
                            wall,

                        "SDR":
                            sdr,

                        "Color":
                            color,

                        "Standard_Length":
                            standard_length,

                        "Unit":
                            unit

                    }

                    update_record(
                        TABLES["Items"],
                        "Item_ID",
                        selected_item,
                        record
                    )


    # -----------------------------------------------------
    # DELETE ITEM
    # -----------------------------------------------------

    with tab3:

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            delete_item = st.selectbox(
                "Select Item to Delete",
                items["Item_ID"].astype(str).tolist(),
                key="delete_item"
            )

            confirm = st.checkbox(
                "I understand that this item will be deleted."
            )

            if st.button(
                "🗑️ Delete Item"
            ):

                if confirm:

                    delete_record(
                        TABLES["Items"],
                        "Item_ID",
                        delete_item
                    )

                else:

                    st.warning(
                        "Please confirm deletion first."
                    )


    st.divider()

    st.subheader("Registered Items")

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.title("🏭 Production Management")

    st.write(
        "Manage manufacturing production records."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Production",
            "✏️ Update Production",
            "🗑️ Delete Production"
        ]
    )


    # -----------------------------------------------------
    # ADD PRODUCTION
    # -----------------------------------------------------

    with tab1:

        with st.form("add_production_form"):

            production_id = st.text_input(
                "Production ID"
            )

            item_list = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
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
                "Production Date"
            )

            batch_no = st.text_input(
                "Batch No."
            )

            production_line = st.text_input(
                "Production Line"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c2:

                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c3:

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
                    "Cancelled"
                ]
            )

            submitted = st.form_submit_button(
                "➕ Add Production"
            )

            if submitted:

                if not production_id.strip():

                    st.warning(
                        "Production ID is required."
                    )

                else:

                    record = {

                        "Production_ID":
                            production_id.strip(),

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

                    insert_record(
                        TABLES["Production"],
                        record
                    )


    # -----------------------------------------------------
    # UPDATE PRODUCTION
    # -----------------------------------------------------

    with tab2:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            selected_production = st.selectbox(
                "Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist()
            )

            row = production[
                production["Production_ID"].astype(str)
                == str(selected_production)
            ]

            current = row.iloc[0]

            item_list = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            current_item = str(
                current["Item_ID"]
            )

            if current_item in item_list:

                item_index = item_list.index(
                    current_item
                )

            else:

                item_index = 0

            if item_list:

                item_id = st.selectbox(
                    "Item ID",
                    item_list,
                    index=item_index
                )

            else:

                item_id = st.text_input(
                    "Item ID",
                    value=current_item
                )

            production_date = st.date_input(
                "Production Date",
                value=pd.to_datetime(
                    current["Production_Date"],
                    errors="coerce"
                ).date()
                if pd.notna(
                    pd.to_datetime(
                        current["Production_Date"],
                        errors="coerce"
                    )
                )
                else pd.Timestamp.today().date()
            )

            batch_no = st.text_input(
                "Batch No.",
                value=str(
                    current["Batch_No"]
                    if pd.notna(current["Batch_No"])
                    else ""
                )
            )

            production_line = st.text_input(
                "Production Line",
                value=str(
                    current["Production_Line"]
                    if pd.notna(
                        current["Production_Line"]
                    )
                    else ""
                )
            )

            planned_qty = st.number_input(
                "Planned Quantity (m)",
                value=float(
                    pd.to_numeric(
                        current["Planned_Qty_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            good_qty = st.number_input(
                "Good Quantity (m)",
                value=float(
                    pd.to_numeric(
                        current["Good_Qty_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            rejected_qty = st.number_input(
                "Rejected Quantity (m)",
                value=float(
                    pd.to_numeric(
                        current["Rejected_Qty_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            status_options = [
                "Planned",
                "In Progress",
                "Completed",
                "Rejected",
                "Cancelled"
            ]

            current_status = current[
                "Production_Status"
            ]

            status_index = (
                status_options.index(
                    current_status
                )
                if current_status in status_options
                else 0
            )

            production_status = st.selectbox(
                "Production Status",
                status_options,
                index=status_index
            )

            if st.button(
                "💾 Update Production"
            ):

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

                update_record(
                    TABLES["Production"],
                    "Production_ID",
                    selected_production,
                    record
                )


    # -----------------------------------------------------
    # DELETE PRODUCTION
    # -----------------------------------------------------

    with tab3:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            delete_production = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist(),
                key="delete_production"
            )

            confirm = st.checkbox(
                "I understand that this production record will be deleted."
            )

            if st.button(
                "🗑️ Delete Production"
            ):

                if confirm:

                    delete_record(
                        TABLES["Production"],
                        "Production_ID",
                        delete_production
                    )

                else:

                    st.warning(
                        "Please confirm deletion first."
                    )


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

elif page == "Stock Control":

    st.title("📊 Stock Control")

    st.write(
        "Manage warehouse and inventory records."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Stock",
            "✏️ Update Stock",
            "🗑️ Delete Stock"
        ]
    )


    # -----------------------------------------------------
    # ADD STOCK
    # -----------------------------------------------------

    with tab1:

        with st.form("add_stock_form"):

            stock_id = st.text_input(
                "Stock ID"
            )

            item_list = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
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

            production_list = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            if production_list:

                production_id = st.selectbox(
                    "Production ID",
                    production_list
                )

            else:

                production_id = st.text_input(
                    "Production ID"
                )

            batch_no = st.text_input(
                "Batch No."
            )

            stock_date = st.date_input(
                "Stock Date"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c2:

                produced_qty = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

            with c3:

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

            st.info(
                f"Calculated Closing Stock: "
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

            submitted = st.form_submit_button(
                "➕ Add Stock"
            )

            if submitted:

                if not stock_id.strip():

                    st.warning(
                        "Stock ID is required."
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

                    insert_record(
                        TABLES["Stock"],
                        record
                    )


    # -----------------------------------------------------
    # UPDATE STOCK
    # -----------------------------------------------------

    with tab2:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            selected_stock = st.selectbox(
                "Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist()
            )

            row = stock[
                stock["Stock_ID"].astype(str)
                == str(selected_stock)
            ]

            current = row.iloc[0]

            item_list = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            current_item = str(
                current["Item_ID"]
            )

            if current_item in item_list:

                item_index = item_list.index(
                    current_item
                )

            else:

                item_index = 0

            if item_list:

                item_id = st.selectbox(
                    "Item ID",
                    item_list,
                    index=item_index
                )

            else:

                item_id = st.text_input(
                    "Item ID",
                    value=current_item
                )

            production_list = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            current_production = str(
                current["Production_ID"]
            )

            if (
                current_production
                in production_list
            ):

                production_index = (
                    production_list.index(
                        current_production
                    )
                )

            else:

                production_index = 0

            if production_list:

                production_id = st.selectbox(
                    "Production ID",
                    production_list,
                    index=production_index
                )

            else:

                production_id = st.text_input(
                    "Production ID",
                    value=current_production
                )

            batch_no = st.text_input(
                "Batch No.",
                value=str(
                    current["Batch_No"]
                    if pd.notna(
                        current["Batch_No"]
                    )
                    else ""
                )
            )

            stock_date = st.date_input(
                "Stock Date",
                value=pd.to_datetime(
                    current["Stock_Date"],
                    errors="coerce"
                ).date()
                if pd.notna(
                    pd.to_datetime(
                        current["Stock_Date"],
                        errors="coerce"
                    )
                )
                else pd.Timestamp.today().date()
            )

            opening_stock = st.number_input(
                "Opening Stock (m)",
                value=float(
                    pd.to_numeric(
                        current["Opening_Stock_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            produced_qty = st.number_input(
                "Produced Quantity (m)",
                value=float(
                    pd.to_numeric(
                        current["Produced_Qty_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            dispatched_qty = st.number_input(
                "Dispatched Quantity (m)",
                value=float(
                    pd.to_numeric(
                        current["Dispatched_Qty_m"],
                        errors="coerce"
                    ) or 0
                )
            )

            closing_stock = (
                opening_stock
                + produced_qty
                - dispatched_qty
            )

            st.info(
                f"Calculated Closing Stock: "
                f"{closing_stock:,.2f} m"
            )

            status_options = [
                "Available",
                "Low Stock",
                "Out of Stock",
                "Reserved"
            ]

            current_status = current[
                "Stock_Status"
            ]

            status_index = (
                status_options.index(
                    current_status
                )
                if current_status in status_options
                else 0
            )

            stock_status = st.selectbox(
                "Stock Status",
                status_options,
                index=status_index
            )

            if st.button(
                "💾 Update Stock"
            ):

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

                update_record(
                    TABLES["Stock"],
                    "Stock_ID",
                    selected_stock,
                    record
                )


    # -----------------------------------------------------
    # DELETE STOCK
    # -----------------------------------------------------

    with tab3:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            delete_stock = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist(),
                key="delete_stock"
            )

            confirm = st.checkbox(
                "I understand that this stock record will be deleted."
            )

            if st.button(
                "🗑️ Delete Stock"
            ):

                if confirm:

                    delete_record(
                        TABLES["Stock"],
                        "Stock_ID",
                        delete_stock
                    )

                else:

                    st.warning(
                        "Please confirm deletion first."
                    )


    st.divider()

    st.subheader("Stock Records")

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CUSTOM DASHBOARD
# =========================================================

elif page == "Custom Dashboard":

    st.title("📊 Custom Dashboard")

    st.write(
        "Build quick views from your ERP data."
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

        st.warning(
            "No data available."
        )

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader(
            "Quick Statistics"
        )

        st.write(
            df.describe(
                include="all"
            )
        )


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":

    st.title("📈 Analytics")

    st.write(
        "Manufacturing and inventory analytics."
    )


    # -----------------------------------------------------
    # PRODUCTION ANALYTICS
    # -----------------------------------------------------

    if not production.empty:

        st.subheader(
            "Production Analysis"
        )

        c1, c2 = st.columns(2)

        with c1:

            line_data = (
                production
                .groupby("Production_Line")[
                    [
                        "Planned_Qty_m",
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ]
                ]
                .sum()
                .reset_index()
            )

            fig = px.bar(
                line_data,
                x="Production_Line",
                y=[
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                barmode="group",
                title="Production by Line"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with c2:

            status = (
                production[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .value_counts()
                .reset_index()
            )

            status.columns = [
                "Status",
                "Count"
            ]

            fig = px.pie(
                status,
                names="Status",
                values="Count",
                title="Production Status"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # -----------------------------------------------------
    # STOCK ANALYTICS
    # -----------------------------------------------------

    if not stock.empty:

        st.subheader(
            "Stock Analysis"
        )

        stock_status = (
            stock[
                "Stock_Status"
            ]
            .fillna("Unknown")
            .value_counts()
            .reset_index()
        )

        stock_status.columns = [
            "Stock_Status",
            "Count"
        ]

        fig = px.pie(
            stock_status,
            names="Stock_Status",
            values="Count",
            hole=0.4,
            title="Stock Status"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# DATA MANAGEMENT
# =========================================================

elif page == "Data Management":

    st.title("🗄️ Data Management")

    st.write(
        "Supabase live database information."
    )


    st.success(
        "✅ Supabase connection initialized."
    )


    # -----------------------------------------------------
    # TABLE COUNTS
    # -----------------------------------------------------

    st.subheader(
        "Live Table Records"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Item Registration",
        len(items)
    )

    c2.metric(
        "Production",
        len(production)
    )

    c3.metric(
        "Stock Control",
        len(stock)
    )


    # -----------------------------------------------------
    # TABLE SELECTOR
    # -----------------------------------------------------

    selected_table = st.selectbox(
        "Select Table",
        [
            "Item Registration",
            "Production",
            "Stock Control"
        ]
    )

    if selected_table == "Item Registration":

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )

        st.write(
            "Columns:",
            list(items.columns)
        )


    elif selected_table == "Production":

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )

        st.write(
            "Columns:",
            list(production.columns)
        )


    else:

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )

        st.write(
            "Columns:",
            list(stock.columns)
        )


    # -----------------------------------------------------
    # DEBUG INFORMATION
    # -----------------------------------------------------

    st.divider()

    with st.expander(
        "🔧 Database Debug Information"
    ):

        st.write(
            "Item Registration Rows:",
            len(items)
        )

        st.write(
            "Production Rows:",
            len(production)
        )

        st.write(
            "Stock Control Rows:",
            len(stock)
        )

        st.write(
            "Item Registration Columns:",
            list(items.columns)
        )

        st.write(
            "Production Columns:",
            list(production.columns)
        )

        st.write(
            "Stock Control Columns:",
            list(stock.columns)
        )

        st.write(
            "Expected Item Columns:",
            ITEM_COLUMNS
        )

        st.write(
            "Expected Production Columns:",
            PRODUCTION_COLUMNS
        )

        st.write(
            "Expected Stock Columns:",
            STOCK_COLUMNS
        )

        st.divider()

        st.write(
            "Raw Item Data:"
        )

        st.dataframe(
            items,
            use_container_width=True
        )

        st.write(
            "Raw Production Data:"
        )

        st.dataframe(
            production,
            use_container_width=True
        )

        st.write(
            "Raw Stock Data:"
        )

        st.dataframe(
            stock,
            use_container_width=True
        )


# =========================================================
# FOOTER
# =========================================================

st.sidebar.divider()

st.sidebar.caption(
    "Flex Head Industries Pvt Ltd"
)

st.sidebar.caption(
    "ERP System • Supabase • Streamlit"
)
```
