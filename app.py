import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client


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
# LOAD EXTERNAL CSS
# ============================================================

def load_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            css = f.read()

        st.markdown(
            "<style>" + css + "</style>",
            unsafe_allow_html=True
        )

    except FileNotFoundError:
        st.warning(
            "style.css not found. Keep style.css in the same folder as app.py."
        )


load_css()


# ============================================================
# CONSTANTS
# ============================================================

COMPANY_NAME = "Flex Head Industries Pvt Ltd"

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
STOCK_TABLE = "Stock_Control"


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
# SUPABASE CONNECTION
# ============================================================

@st.cache_resource
def get_supabase():

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        return create_client(url, key)

    except Exception as e:

        st.error("Supabase connection failed.")
        st.code(str(e))
        st.stop()


supabase = get_supabase()


# ============================================================
# HELPER
# ============================================================

def make_dataframe(data, columns):

    df = pd.DataFrame(data or [])

    for column in columns:
        if column not in df.columns:
            df[column] = None

    return df[columns]


def numeric_columns(df, columns):

    df = df.copy()

    for column in columns:

        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            ).fillna(0)

    return df


# ============================================================
# LOAD ITEMS
# ============================================================

@st.cache_data(ttl=5)
def load_items():

    try:

        response = (
            supabase
            .table(ITEM_TABLE)
            .select("*")
            .execute()
        )

        df = make_dataframe(
            response.data,
            ITEM_COLUMNS
        )

        df = numeric_columns(
            df,
            [
                "Nominal_Diameter_mm",
                "Wall_Thickness_mm",
                "Standard_Length"
            ]
        )

        return df

    except Exception as e:

        st.error(
            "Item Registration table load error:"
        )
        st.code(str(e))

        return pd.DataFrame(
            columns=ITEM_COLUMNS
        )


# ============================================================
# LOAD PRODUCTION
# ============================================================

@st.cache_data(ttl=5)
def load_production():

    try:

        response = (
            supabase
            .table(PRODUCTION_TABLE)
            .select("*")
            .execute()
        )

        df = make_dataframe(
            response.data,
            PRODUCTION_COLUMNS
        )

        df = numeric_columns(
            df,
            [
                "Planned_Qty_m",
                "Good_Qty_m",
                "Rejected_Qty_m"
            ]
        )

        return df

    except Exception as e:

        st.error(
            "Production table load error:"
        )
        st.code(str(e))

        return pd.DataFrame(
            columns=PRODUCTION_COLUMNS
        )


# ============================================================
# LOAD STOCK
# ============================================================

@st.cache_data(ttl=5)
def load_stock():

    try:

        response = (
            supabase
            .table(STOCK_TABLE)
            .select("*")
            .execute()
        )

        df = make_dataframe(
            response.data,
            STOCK_COLUMNS
        )

        df = numeric_columns(
            df,
            [
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m"
            ]
        )

        return df

    except Exception as e:

        st.error(
            "Stock Control table load error:"
        )
        st.code(str(e))

        return pd.DataFrame(
            columns=STOCK_COLUMNS
        )


# ============================================================
# CACHE REFRESH
# ============================================================

def refresh_data():

    load_items.clear()
    load_production.clear()
    load_stock.clear()


# ============================================================
# LOAD LIVE DATA
# ============================================================

items = load_items()
production = load_production()
stock = load_stock()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">FH</div>

            <div>
                <div class="brand-name">
                    FLEX HEAD
                </div>

                <div class="brand-sub">
                    INDUSTRIES ERP
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    page = st.radio(
        "MODULES",
        [
            "Executive Dashboard",
            "Item Registration",
            "Production",
            "Stock Control",
            "Analytics",
            "Data Management"
        ]
    )

    st.markdown("---")

    st.caption(
        "Flex Head Industries Pvt Ltd"
    )

    st.caption(
        "Pipe Manufacturing ERP"
    )


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

if page == "Executive Dashboard":

    st.markdown(
        '<div class="page-kicker">MANUFACTURING ERP</div>',
        unsafe_allow_html=True
    )

    st.title("Executive Dashboard")

    st.caption(
        "Real-time overview of manufacturing, production and inventory."
    )

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    registered_items = len(items)

    planned_production = pd.to_numeric(
        production["Planned_Qty_m"],
        errors="coerce"
    ).fillna(0).sum()

    good_production = pd.to_numeric(
        production["Good_Qty_m"],
        errors="coerce"
    ).fillna(0).sum()

    rejected_production = pd.to_numeric(
        production["Rejected_Qty_m"],
        errors="coerce"
    ).fillna(0).sum()

    produced_to_stock = pd.to_numeric(
        stock["Produced_Qty_m"],
        errors="coerce"
    ).fillna(0).sum()

    dispatched = pd.to_numeric(
        stock["Dispatched_Qty_m"],
        errors="coerce"
    ).fillna(0).sum()

    current_stock = pd.to_numeric(
        stock["Closing_Stock_m"],
        errors="coerce"
    ).fillna(0).sum()

    total_production = (
        good_production +
        rejected_production
    )

    if total_production > 0:

        production_yield = (
            good_production /
            total_production
        ) * 100

    else:

        production_yield = 0


    # ========================================================
    # FOUR MAIN CARDS
    # ========================================================

    col1, col2, col3, col4 = st.columns(4)


    # --------------------------------------------------------
    # REGISTERED ITEMS
    # --------------------------------------------------------

    with col1:

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


    # --------------------------------------------------------
    # GOOD PRODUCTION
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # CURRENT STOCK
    # --------------------------------------------------------

    with col3:

        st.markdown(
            f"""
<div class="metric-card">
    <div class="metric-icon">◈</div>

    <div class="metric-label">
        Current Stock
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


    # --------------------------------------------------------
    # PRODUCTION YIELD
    # --------------------------------------------------------

    with col4:

        st.markdown(
            f"""
<div class="metric-card">
    <div class="metric-icon">%</div>

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
            f"{planned_production:,.0f} m"
        )

    with c2:

        st.metric(
            "Rejected Production",
            f"{rejected_production:,.0f} m"
        )

    with c3:

        st.metric(
            "Produced to Stock",
            f"{produced_to_stock:,.0f} m"
        )

    with c4:

        st.metric(
            "Dispatched",
            f"{dispatched:,.0f} m"
        )


    st.markdown("---")


    # ========================================================
    # CHARTS
    # ========================================================

    chart1, chart2 = st.columns(2)


    # --------------------------------------------------------
    # PRODUCTION STATUS
    # --------------------------------------------------------

    with chart1:

        st.subheader("Production Status")

        if not production.empty:

            status_df = (
                production[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .reset_index()
            )

            status_df.columns = [
                "Status",
                "Count"
            ]

            fig = px.pie(
                status_df,
                names="Status",
                values="Count",
                hole=0.45
            )

            fig.update_layout(
                height=360,
                margin=dict(
                    l=10,
                    r=10,
                    t=30,
                    b=10
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info(
                "No production records found."
            )


    # --------------------------------------------------------
    # PRODUCTION QUANTITY
    # --------------------------------------------------------

    with chart2:

        st.subheader("Production Overview")

        overview = pd.DataFrame(
            {
                "Category": [
                    "Planned",
                    "Good",
                    "Rejected"
                ],
                "Quantity": [
                    planned_production,
                    good_production,
                    rejected_production
                ]
            }
        )

        fig = px.bar(
            overview,
            x="Category",
            y="Quantity",
            text_auto=True
        )

        fig.update_layout(
            height=360,
            margin=dict(
                l=10,
                r=10,
                t=30,
                b=10
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # ========================================================
    # STOCK CHART
    # ========================================================

    st.subheader("Current Stock by Item")

    if not stock.empty:

        stock_chart = (
            stock
            .groupby(
                "Item_ID",
                as_index=False
            )["Closing_Stock_m"]
            .sum()
        )

        if not items.empty:

            item_lookup = items[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].copy()

            stock_chart = stock_chart.merge(
                item_lookup,
                on="Item_ID",
                how="left"
            )

            stock_chart["Display_Item"] = (
                stock_chart["Item_Code"]
                .fillna(
                    stock_chart["Item_ID"]
                )
            )

        else:

            stock_chart["Display_Item"] = (
                stock_chart["Item_ID"]
            )

        fig = px.bar(
            stock_chart,
            x="Display_Item",
            y="Closing_Stock_m",
            text_auto=True,
            labels={
                "Display_Item": "Item",
                "Closing_Stock_m": "Closing Stock (m)"
            }
        )

        fig.update_layout(
            height=400,
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info(
            "No stock records found."
        )


# ============================================================
# ITEM REGISTRATION
# ============================================================

elif page == "Item Registration":

    st.markdown(
        '<div class="page-kicker">MASTER DATA</div>',
        unsafe_allow_html=True
    )

    st.title("Item Registration")

    st.caption(
        "Manage manufacturing product items."
    )


    tab_add, tab_update, tab_delete = st.tabs(
        [
            "Add Item",
            "Update Item",
            "Delete Item"
        ]
    )


    # ========================================================
    # ADD ITEM
    # ========================================================

    with tab_add:

        st.subheader("Register New Item")

        with st.form("add_item"):

            a, b, c = st.columns(3)

            with a:

                item_id = st.text_input(
                    "Item ID *"
                )

                item_code = st.text_input(
                    "Item Code"
                )

                material_grade = st.selectbox(
                    "Material Grade",
                    [
                        "PE-80",
                        "PE-100"
                    ]
                )

            with b:

                application = st.selectbox(
                    "Application",
                    [
                        "Water",
                        "Sewerage",
                        "Gas"
                    ]
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

            with c:

                sdr = st.text_input(
                    "SDR"
                )

                item_color = st.text_input(
                    "Color"
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


            add_item = st.form_submit_button(
                "Add Item",
                type="primary"
            )


        if add_item:

            if not item_id.strip():

                st.error(
                    "Item ID is required."
                )

            else:

                payload = {
                    "Item_ID": item_id.strip(),
                    "Item_Code": item_code.strip(),
                    "Material_Grade": material_grade,
                    "Application": application,
                    "Nominal_Diameter_mm": diameter,
                    "Wall_Thickness_mm": wall,
                    "SDR": sdr.strip(),
                    "Color": item_color.strip(),
                    "Standard_Length": standard_length,
                    "Unit": unit.strip()
                }

                try:

                    (
                        supabase
                        .table(ITEM_TABLE)
                        .insert(payload)
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Item added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Item could not be added."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE ITEM
    # ========================================================

    with tab_update:

        st.subheader("Update Item")

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            selected_id = st.selectbox(
                "Select Item",
                items["Item_ID"]
                .astype(str)
                .tolist(),
                key="update_item_id"
            )

            current = items[
                items["Item_ID"].astype(str)
                == selected_id
            ].iloc[0]


            with st.form("update_item"):

                a, b, c = st.columns(3)

                with a:

                    update_code = st.text_input(
                        "Item Code",
                        value=str(
                            current["Item_Code"]
                            if pd.notna(
                                current["Item_Code"]
                            )
                            else ""
                        )
                    )

                    update_grade = st.selectbox(
                        "Material Grade",
                        [
                            "PE-80",
                            "PE-100"
                        ],
                        index=(
                            1
                            if str(
                                current["Material_Grade"]
                            ) == "PE-100"
                            else 0
                        )
                    )

                    update_application = st.selectbox(
                        "Application",
                        [
                            "Water",
                            "Sewerage",
                            "Gas"
                        ],
                        index=(
                            [
                                "Water",
                                "Sewerage",
                                "Gas"
                            ].index(
                                str(
                                    current["Application"]
                                )
                            )
                            if str(
                                current["Application"]
                            ) in [
                                "Water",
                                "Sewerage",
                                "Gas"
                            ]
                            else 0
                        )
                    )

                with b:

                    update_diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=float(
                            current[
                                "Nominal_Diameter_mm"
                            ] or 0
                        ),
                        step=1.0
                    )

                    update_wall = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=float(
                            current[
                                "Wall_Thickness_mm"
                            ] or 0
                        ),
                        step=0.1
                    )

                    update_sdr = st.text_input(
                        "SDR",
                        value=str(
                            current["SDR"]
                            if pd.notna(
                                current["SDR"]
                            )
                            else ""
                        )
                    )

                with c:

                    update_color = st.text_input(
                        "Color",
                        value=str(
                            current["Color"]
                            if pd.notna(
                                current["Color"]
                            )
                            else ""
                        )
                    )

                    update_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            current[
                                "Standard_Length"
                            ] or 0
                        ),
                        step=1.0
                    )

                    update_unit = st.text_input(
                        "Unit",
                        value=str(
                            current["Unit"]
                            if pd.notna(
                                current["Unit"]
                            )
                            else "m"
                        )
                    )


                update_item = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


            if update_item:

                payload = {
                    "Item_Code": update_code.strip(),
                    "Material_Grade": update_grade,
                    "Application": update_application,
                    "Nominal_Diameter_mm": update_diameter,
                    "Wall_Thickness_mm": update_wall,
                    "SDR": update_sdr.strip(),
                    "Color": update_color.strip(),
                    "Standard_Length": update_length,
                    "Unit": update_unit.strip()
                }

                try:

                    (
                        supabase
                        .table(ITEM_TABLE)
                        .update(payload)
                        .eq(
                            "Item_ID",
                            selected_id
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Item updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Item could not be updated."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE ITEM
    # ========================================================

    with tab_delete:

        st.subheader("Delete Item")

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            delete_id = st.selectbox(
                "Select Item",
                items["Item_ID"]
                .astype(str)
                .tolist(),
                key="delete_item_id"
            )

            if st.button(
                "Delete Item",
                type="primary"
            ):

                try:

                    (
                        supabase
                        .table(ITEM_TABLE)
                        .delete()
                        .eq(
                            "Item_ID",
                            delete_id
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Item deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Item could not be deleted."
                    )

                    st.code(str(e))


    # ========================================================
    # ITEM TABLE
    # ========================================================

    st.markdown("---")

    st.subheader("Registered Items")

    search = st.text_input(
        "Search",
        placeholder="Search Item ID, Item Code, Grade..."
    )

    display_items = items.copy()

    if search:

        mask = (
            display_items
            .astype(str)
            .apply(
                lambda x:
                x.str.contains(
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


# ============================================================
# PRODUCTION
# ============================================================

elif page == "Production":

    st.markdown(
        '<div class="page-kicker">MANUFACTURING</div>',
        unsafe_allow_html=True
    )

    st.title("Production Management")

    st.caption(
        "Manage production records and quantities."
    )


    tab_add, tab_update, tab_delete = st.tabs(
        [
            "Add Production",
            "Update Production",
            "Delete Production"
        ]
    )


    # ========================================================
    # ADD PRODUCTION
    # ========================================================

    with tab_add:

        st.subheader("Add Production")

        with st.form("add_production"):

            a, b, c = st.columns(3)

            with a:

                production_id = st.text_input(
                    "Production ID *"
                )

                if not items.empty:

                    production_item = st.selectbox(
                        "Item ID",
                        items["Item_ID"]
                        .astype(str)
                        .tolist()
                    )

                else:

                    production_item = st.text_input(
                        "Item ID"
                    )

                production_date = st.date_input(
                    "Production Date"
                )

            with b:

                batch_no = st.text_input(
                    "Batch No"
                )

                production_line = st.text_input(
                    "Production Line"
                )

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0,
                    step=1
                )

            with c:

                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0,
                    step=1
                )

                rejected_qty = st.number_input(
                    "Rejected Quantity (m)",
                    min_value=0,
                    step=1
                )

                production_status = st.selectbox(
                    "Production Status",
                    [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected"
                    ]
                )


            add_production = st.form_submit_button(
                "Add Production",
                type="primary"
            )


        if add_production:

            if not production_id.strip():

                st.error(
                    "Production ID is required."
                )

            else:

                payload = {
                    "Production_ID": production_id.strip(),
                    "Item_ID": str(
                        production_item
                    ),
                    "Production_Date": str(
                        production_date
                    ),
                    "Batch_No": batch_no.strip(),
                    "Production_Line":
                        production_line.strip(),
                    "Planned_Qty_m": planned_qty,
                    "Good_Qty_m": good_qty,
                    "Rejected_Qty_m":
                        rejected_qty,
                    "Production_Status":
                        production_status
                }

                try:

                    (
                        supabase
                        .table(PRODUCTION_TABLE)
                        .insert(payload)
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Production added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production could not be added."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE PRODUCTION
    # ========================================================

    with tab_update:

        st.subheader("Update Production")

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            selected_production = st.selectbox(
                "Production ID",
                production[
                    "Production_ID"
                ]
                .astype(str)
                .tolist(),
                key="update_production_id"
            )

            current = production[
                production[
                    "Production_ID"
                ].astype(str)
                == selected_production
            ].iloc[0]


            with st.form("update_production"):

                a, b, c = st.columns(3)

                with a:

                    update_item = st.text_input(
                        "Item ID",
                        value=str(
                            current["Item_ID"]
                        )
                    )

                    update_date = st.text_input(
                        "Production Date",
                        value=str(
                            current[
                                "Production_Date"
                            ]
                        )
                    )

                    update_batch = st.text_input(
                        "Batch No",
                        value=str(
                            current["Batch_No"]
                            if pd.notna(
                                current["Batch_No"]
                            )
                            else ""
                        )
                    )

                with b:

                    update_line = st.text_input(
                        "Production Line",
                        value=str(
                            current[
                                "Production_Line"
                            ]
                            if pd.notna(
                                current[
                                    "Production_Line"
                                ]
                            )
                            else ""
                        )
                    )

                    update_planned = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Planned_Qty_m"
                            ] or 0
                        )
                    )

                    update_good = st.number_input(
                        "Good Quantity (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Good_Qty_m"
                            ] or 0
                        )
                    )

                with c:

                    update_rejected = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Rejected_Qty_m"
                            ] or 0
                        )
                    )

                    statuses = [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected"
                    ]

                    current_status = str(
                        current[
                            "Production_Status"
                        ]
                    )

                    status_index = (
                        statuses.index(
                            current_status
                        )
                        if current_status in statuses
                        else 0
                    )

                    update_status = st.selectbox(
                        "Production Status",
                        statuses,
                        index=status_index
                    )


                update_production = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


            if update_production:

                payload = {
                    "Item_ID":
                        update_item.strip(),
                    "Production_Date":
                        update_date.strip(),
                    "Batch_No":
                        update_batch.strip(),
                    "Production_Line":
                        update_line.strip(),
                    "Planned_Qty_m":
                        update_planned,
                    "Good_Qty_m":
                        update_good,
                    "Rejected_Qty_m":
                        update_rejected,
                    "Production_Status":
                        update_status
                }

                try:

                    (
                        supabase
                        .table(PRODUCTION_TABLE)
                        .update(payload)
                        .eq(
                            "Production_ID",
                            selected_production
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Production updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production could not be updated."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE PRODUCTION
    # ========================================================

    with tab_delete:

        st.subheader("Delete Production")

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            delete_production = st.selectbox(
                "Production ID",
                production[
                    "Production_ID"
                ]
                .astype(str)
                .tolist(),
                key="delete_production_id"
            )

            if st.button(
                "Delete Production",
                type="primary"
            ):

                try:

                    (
                        supabase
                        .table(PRODUCTION_TABLE)
                        .delete()
                        .eq(
                            "Production_ID",
                            delete_production
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Production deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production could not be deleted."
                    )

                    st.code(str(e))


    st.markdown("---")

    st.subheader("Production Records")

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# STOCK CONTROL
# ============================================================

elif page == "Stock Control":

    st.markdown(
        '<div class="page-kicker">INVENTORY</div>',
        unsafe_allow_html=True
    )

    st.title("Stock Control")

    st.caption(
        "Manage opening stock, production, dispatch and closing stock."
    )


    tab_add, tab_update, tab_delete = st.tabs(
        [
            "Add Stock",
            "Update Stock",
            "Delete Stock"
        ]
    )


    # ========================================================
    # ADD STOCK
    # ========================================================

    with tab_add:

        st.subheader("Add Stock")

        with st.form("add_stock"):

            a, b, c = st.columns(3)

            with a:

                stock_id = st.text_input(
                    "Stock ID *"
                )

                if not items.empty:

                    stock_item = st.selectbox(
                        "Item ID",
                        items["Item_ID"]
                        .astype(str)
                        .tolist(),
                        key="add_stock_item"
                    )

                else:

                    stock_item = st.text_input(
                        "Item ID"
                    )

                if not production.empty:

                    stock_production = st.selectbox(
                        "Production ID",
                        production[
                            "Production_ID"
                        ]
                        .astype(str)
                        .tolist()
                    )

                else:

                    stock_production = st.text_input(
                        "Production ID"
                    )

                stock_batch = st.text_input(
                    "Batch No"
                )

            with b:

                stock_date = st.date_input(
                    "Stock Date"
                )

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0,
                    step=1
                )

                produced_stock = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0,
                    step=1
                )

            with c:

                dispatched_stock = st.number_input(
                    "Dispatched Quantity (m)",
                    min_value=0,
                    step=1
                )

                closing_stock = st.number_input(
                    "Closing Stock (m)",
                    min_value=0,
                    step=1
                )

                stock_status = st.selectbox(
                    "Stock Status",
                    [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]
                )


            add_stock = st.form_submit_button(
                "Add Stock",
                type="primary"
            )


        if add_stock:

            if not stock_id.strip():

                st.error(
                    "Stock ID is required."
                )

            else:

                payload = {
                    "Stock_ID":
                        stock_id.strip(),
                    "Item_ID":
                        str(stock_item),
                    "Production_ID":
                        str(stock_production),
                    "Batch_No":
                        stock_batch.strip(),
                    "Stock_Date":
                        str(stock_date),
                    "Opening_Stock_m":
                        opening_stock,
                    "Produced_Qty_m":
                        produced_stock,
                    "Dispatched_Qty_m":
                        dispatched_stock,
                    "Closing_Stock_m":
                        closing_stock,
                    "Stock_Status":
                        stock_status
                }

                try:

                    (
                        supabase
                        .table(STOCK_TABLE)
                        .insert(payload)
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Stock added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock could not be added."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE STOCK
    # ========================================================

    with tab_update:

        st.subheader("Update Stock")

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            selected_stock = st.selectbox(
                "Stock ID",
                stock[
                    "Stock_ID"
                ]
                .astype(str)
                .tolist(),
                key="update_stock_id"
            )

            current = stock[
                stock[
                    "Stock_ID"
                ].astype(str)
                == selected_stock
            ].iloc[0]


            with st.form("update_stock"):

                a, b, c = st.columns(3)

                with a:

                    update_item = st.text_input(
                        "Item ID",
                        value=str(
                            current["Item_ID"]
                        )
                    )

                    update_production = st.text_input(
                        "Production ID",
                        value=str(
                            current["Production_ID"]
                        )
                    )

                    update_batch = st.text_input(
                        "Batch No",
                        value=str(
                            current["Batch_No"]
                            if pd.notna(
                                current["Batch_No"]
                            )
                            else ""
                        )
                    )

                with b:

                    update_date = st.text_input(
                        "Stock Date",
                        value=str(
                            current["Stock_Date"]
                        )
                    )

                    update_opening = st.number_input(
                        "Opening Stock (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Opening_Stock_m"
                            ] or 0
                        )
                    )

                    update_produced = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Produced_Qty_m"
                            ] or 0
                        )
                    )

                with c:

                    update_dispatched = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Dispatched_Qty_m"
                            ] or 0
                        )
                    )

                    update_closing = st.number_input(
                        "Closing Stock (m)",
                        min_value=0,
                        value=int(
                            current[
                                "Closing_Stock_m"
                            ] or 0
                        )
                    )

                    stock_statuses = [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]

                    current_stock_status = str(
                        current[
                            "Stock_Status"
                        ]
                    )

                    stock_status_index = (
                        stock_statuses.index(
                            current_stock_status
                        )
                        if current_stock_status
                        in stock_statuses
                        else 0
                    )

                    update_status = st.selectbox(
                        "Stock Status",
                        stock_statuses,
                        index=stock_status_index
                    )


                update_stock = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )


            if update_stock:

                payload = {
                    "Item_ID":
                        update_item.strip(),
                    "Production_ID":
                        update_production.strip(),
                    "Batch_No":
                        update_batch.strip(),
                    "Stock_Date":
                        update_date.strip(),
                    "Opening_Stock_m":
                        update_opening,
                    "Produced_Qty_m":
                        update_produced,
                    "Dispatched_Qty_m":
                        update_dispatched,
                    "Closing_Stock_m":
                        update_closing,
                    "Stock_Status":
                        update_status
                }

                try:

                    (
                        supabase
                        .table(STOCK_TABLE)
                        .update(payload)
                        .eq(
                            "Stock_ID",
                            selected_stock
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Stock updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock could not be updated."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE STOCK
    # ========================================================

    with tab_delete:

        st.subheader("Delete Stock")

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            delete_stock = st.selectbox(
                "Stock ID",
                stock[
                    "Stock_ID"
                ]
                .astype(str)
                .tolist(),
                key="delete_stock_id"
            )

            if st.button(
                "Delete Stock",
                type="primary"
            ):

                try:

                    (
                        supabase
                        .table(STOCK_TABLE)
                        .delete()
                        .eq(
                            "Stock_ID",
                            delete_stock
                        )
                        .execute()
                    )

                    refresh_data()

                    st.success(
                        "Stock deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock could not be deleted."
                    )

                    st.code(str(e))


    st.markdown("---")

    st.subheader("Stock Records")

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# ANALYTICS
# ============================================================

elif page == "Analytics":

    st.markdown(
        '<div class="page-kicker">BUSINESS ANALYTICS</div>',
        unsafe_allow_html=True
    )

    st.title("Analytics")

    st.caption(
        "Production and inventory analysis."
    )


    # ========================================================
    # PRODUCTION ANALYSIS
    # ========================================================

    st.subheader("Production Analysis")

    if production.empty:

        st.info(
            "No production data available."
        )

    else:

        analysis = production.copy()

        analysis["Total_Production"] = (
            analysis["Good_Qty_m"]
            +
            analysis["Rejected_Qty_m"]
        )

        analysis["Yield_%"] = 0.0

        valid = (
            analysis["Total_Production"] > 0
        )

        analysis.loc[
            valid,
            "Yield_%"
        ] = (
            analysis.loc[
                valid,
                "Good_Qty_m"
            ]
            /
            analysis.loc[
                valid,
                "Total_Production"
            ]
            * 100
        )


        a, b = st.columns(2)


        with a:

            fig = px.bar(
                analysis,
                x="Production_ID",
                y=[
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                barmode="group",
                title="Good vs Rejected Production"
            )

            fig.update_layout(
                height=400
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with b:

            fig = px.bar(
                analysis,
                x="Production_ID",
                y="Yield_%",
                title="Production Yield"
            )

            fig.update_layout(
                height=400
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        st.dataframe(
            analysis,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # STOCK ANALYSIS
    # ========================================================

    st.subheader("Inventory Analysis")

    if stock.empty:

        st.info(
            "No stock data available."
        )

    else:

        stock_analysis = (
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

        fig = px.bar(
            stock_analysis,
            x="Item_ID",
            y=[
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m"
            ],
            barmode="group",
            title="Inventory Movement"
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

elif page == "Data Management":

    st.markdown(
        '<div class="page-kicker">DATABASE</div>',
        unsafe_allow_html=True
    )

    st.title("Data Management")

    st.caption(
        "Live data loaded directly from Supabase."
    )


    # ========================================================
    # DATABASE COUNTS
    # ========================================================

    a, b, c = st.columns(3)

    with a:

        st.metric(
            "Item Records",
            len(items)
        )

    with b:

        st.metric(
            "Production Records",
            len(production)
        )

    with c:

        st.metric(
            "Stock Records",
            len(stock)
        )


    st.markdown("---")


    # ========================================================
    # ITEM DATA
    # ========================================================

    with st.expander(
        "Item Registration",
        expanded=True
    ):

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # PRODUCTION DATA
    # ========================================================

    with st.expander(
        "Production"
    ):

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # STOCK DATA
    # ========================================================

    with st.expander(
        "Stock Control"
    ):

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )


    st.markdown("---")


    if st.button(
        "Refresh Live Data"
    ):

        refresh_data()

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Flex Head Industries Pvt Ltd | Manufacturing ERP"
)
