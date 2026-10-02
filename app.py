import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client


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
# LOAD EXTERNAL CSS
# =========================================================

def load_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        st.warning("style.css file not found. Please keep style.css in the same folder as app.py.")


load_css()


# =========================================================
# CONSTANTS
# =========================================================

COMPANY_NAME = "Flex Head Industries Pvt Ltd"

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
STOCK_TABLE = "Stock_Control"


# =========================================================
# SUPABASE CONNECTION
# =========================================================

@st.cache_resource
def get_supabase():

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        return create_client(url, key)

    except Exception as e:
        st.error("Supabase connection failed.")
        st.error(str(e))
        st.stop()


supabase = get_supabase()


# =========================================================
# DATA LOADING FUNCTIONS
# =========================================================

@st.cache_data(ttl=5)
def load_items():

    try:

        response = (
            supabase
            .table(ITEM_TABLE)
            .select("*")
            .execute()
        )

        data = response.data or []

        columns = [
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

        df = pd.DataFrame(data)

        for col in columns:
            if col not in df.columns:
                df[col] = None

        return df[columns]

    except Exception as e:

        st.error(f"Error loading Item Registration: {e}")

        return pd.DataFrame(columns=[
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
        ])


@st.cache_data(ttl=5)
def load_production():

    try:

        response = (
            supabase
            .table(PRODUCTION_TABLE)
            .select("*")
            .execute()
        )

        data = response.data or []

        columns = [
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

        df = pd.DataFrame(data)

        for col in columns:
            if col not in df.columns:
                df[col] = None

        return df[columns]

    except Exception as e:

        st.error(f"Error loading Production: {e}")

        return pd.DataFrame(columns=[
            "Production_ID",
            "Item_ID",
            "Production_Date",
            "Batch_No",
            "Production_Line",
            "Planned_Qty_m",
            "Good_Qty_m",
            "Rejected_Qty_m",
            "Production_Status"
        ])


@st.cache_data(ttl=5)
def load_stock():

    try:

        response = (
            supabase
            .table(STOCK_TABLE)
            .select("*")
            .execute()
        )

        data = response.data or []

        columns = [
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

        df = pd.DataFrame(data)

        for col in columns:
            if col not in df.columns:
                df[col] = None

        return df[columns]

    except Exception as e:

        st.error(f"Error loading Stock Control: {e}")

        return pd.DataFrame(columns=[
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
        ])


# =========================================================
# LOAD DATA
# =========================================================

items = load_items()
production = load_production()
stock = load_stock()


# =========================================================
# DATA CLEANING
# =========================================================

def clean_numeric(df, columns):

    for col in columns:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


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


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def refresh_data():

    st.cache_data.clear()


def show_success(message):

    st.success(message)
    refresh_data()


def safe_sum(df, column):

    if df.empty or column not in df.columns:
        return 0

    return pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).sum()


# =========================================================
# SIDEBAR
# =========================================================

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

    st.caption("Flex Head Industries Pvt Ltd")
    st.caption("Pipe Manufacturing ERP")


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

if page == "Executive Dashboard":

    st.markdown(
        '<div class="page-kicker">MANUFACTURING ERP</div>',
        unsafe_allow_html=True
    )

    st.title("Executive Dashboard")

    st.caption(
        "Real-time overview of manufacturing, production and inventory."
    )

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

    # -----------------------------------------------------
    # CALCULATE METRICS
    # -----------------------------------------------------

    registered_items = len(items)

    planned_production = safe_sum(
        production,
        "Planned_Qty_m"
    )

    good_production = safe_sum(
        production,
        "Good_Qty_m"
    )

    rejected_production = safe_sum(
        production,
        "Rejected_Qty_m"
    )

    produced_stock = safe_sum(
        stock,
        "Produced_Qty_m"
    )

    dispatched = safe_sum(
        stock,
        "Dispatched_Qty_m"
    )

    closing_stock = safe_sum(
        stock,
        "Closing_Stock_m"
    )

    total_produced = good_production + rejected_production

    if total_produced > 0:

        production_yield = (
            good_production / total_produced
        ) * 100

    else:

        production_yield = 0


    # -----------------------------------------------------
    # METRIC CARDS
    # -----------------------------------------------------

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
                    {good_production:,.0f} m
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

                <div class="metric-icon">◈</div>

                <div class="metric-label">
                    Current Stock
                </div>

                <div class="metric-value">
                    {closing_stock:,.0f} m
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


    # -----------------------------------------------------
    # SECOND ROW
    # -----------------------------------------------------

    c5, c6, c7, c8 = st.columns(4)

    with c5:

        st.metric(
            "Planned Production",
            f"{planned_production:,.0f} m"
        )

    with c6:

        st.metric(
            "Rejected Production",
            f"{rejected_production:,.0f} m"
        )

    with c7:

        st.metric(
            "Produced to Stock",
            f"{produced_stock:,.0f} m"
        )

    with c8:

        st.metric(
            "Dispatched",
            f"{dispatched:,.0f} m"
        )


    st.markdown("---")


    # =====================================================
    # CHARTS
    # =====================================================

    col1, col2 = st.columns(2)


    # -----------------------------------------------------
    # PRODUCTION STATUS
    # -----------------------------------------------------

    with col1:

        st.subheader("Production Status")

        if not production.empty:

            status_data = (
                production[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .reset_index()
            )

            status_data.columns = [
                "Status",
                "Count"
            ]

            fig = px.pie(
                status_data,
                names="Status",
                values="Count",
                hole=0.45
            )

            fig.update_layout(
                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10
                ),
                height=350
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No production data available.")


    # -----------------------------------------------------
    # PRODUCTION COMPARISON
    # -----------------------------------------------------

    with col2:

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
            height=350,
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


    # =====================================================
    # STOCK BY ITEM
    # =====================================================

    st.subheader("Current Stock by Item")

    if not stock.empty:

        stock_item = (
            stock
            .groupby("Item_ID", as_index=False)
            ["Closing_Stock_m"]
            .sum()
        )

        if not items.empty:

            item_names = items[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].copy()

            stock_item = stock_item.merge(
                item_names,
                on="Item_ID",
                how="left"
            )

            stock_item["Display_Item"] = (
                stock_item["Item_Code"]
                .fillna(stock_item["Item_ID"])
            )

        else:

            stock_item["Display_Item"] = (
                stock_item["Item_ID"]
            )

        fig = px.bar(
            stock_item,
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

        st.info("No stock data available.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.markdown(
        '<div class="page-kicker">MASTER DATA</div>',
        unsafe_allow_html=True
    )

    st.title("Item Registration")

    st.caption(
        "Create, search, update and delete manufacturing items."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Item",
            "Update Item",
            "Delete Item"
        ]
    )


    # =====================================================
    # ADD ITEM
    # =====================================================

    with tab1:

        st.subheader("Register New Item")

        with st.form("add_item_form"):

            col1, col2, col3 = st.columns(3)

            with col1:

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

            with col2:

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

            with col3:

                sdr = st.text_input(
                    "SDR"
                )

                color = st.text_input(
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


            submitted = st.form_submit_button(
                "Add Item",
                type="primary"
            )


        if submitted:

            if not item_id.strip():

                st.error("Item ID is required.")

            else:

                payload = {
                    "Item_ID": item_id.strip(),
                    "Item_Code": item_code.strip(),
                    "Material_Grade": material_grade,
                    "Application": application,
                    "Nominal_Diameter_mm": diameter,
                    "Wall_Thickness_mm": wall,
                    "SDR": sdr.strip(),
                    "Color": color.strip(),
                    "Standard_Length": standard_length,
                    "Unit": unit.strip()
                }

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).insert(payload).execute()

                    st.success(
                        "Item added successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add item: {e}"
                    )


    # =====================================================
    # UPDATE ITEM
    # =====================================================

    with tab2:

        st.subheader("Update Existing Item")

        if items.empty:

            st.info("No items available.")

        else:

            selected_item = st.selectbox(
                "Select Item",
                items["Item_ID"].astype(str).tolist(),
                key="update_item_select"
            )

            current = items[
                items["Item_ID"].astype(str)
                == selected_item
            ].iloc[0]


            with st.form("update_item_form"):

                col1, col2, col3 = st.columns(3)

                with col1:

                    new_code = st.text_input(
                        "Item Code",
                        value=str(
                            current["Item_Code"]
                            if pd.notna(current["Item_Code"])
                            else ""
                        )
                    )

                    new_grade = st.selectbox(
                        "Material Grade",
                        [
                            "PE-80",
                            "PE-100"
                        ],
                        index=(
                            0
                            if str(current["Material_Grade"]) == "PE-80"
                            else 1
                        )
                    )

                    new_application = st.selectbox(
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
                                str(current["Application"])
                            )
                            if str(current["Application"])
                            in [
                                "Water",
                                "Sewerage",
                                "Gas"
                            ]
                            else 0
                        )
                    )

                with col2:

                    new_diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=float(
                            current["Nominal_Diameter_mm"]
                            or 0
                        ),
                        step=1.0
                    )

                    new_wall = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=float(
                            current["Wall_Thickness_mm"]
                            or 0
                        ),
                        step=0.1
                    )

                    new_sdr = st.text_input(
                        "SDR",
                        value=str(
                            current["SDR"]
                            if pd.notna(current["SDR"])
                            else ""
                        )
                    )

                with col3:

                    new_color = st.text_input(
                        "Color",
                        value=str(
                            current["Color"]
                            if pd.notna(current["Color"])
                            else ""
                        )
                    )

                    new_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            current["Standard_Length"]
                            or 0
                        ),
                        step=1.0
                    )

                    new_unit = st.text_input(
                        "Unit",
                        value=str(
                            current["Unit"]
                            if pd.notna(current["Unit"])
                            else "m"
                        )
                    )


                update_btn = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


            if update_btn:

                payload = {
                    "Item_Code": new_code.strip(),
                    "Material_Grade": new_grade,
                    "Application": new_application,
                    "Nominal_Diameter_mm": new_diameter,
                    "Wall_Thickness_mm": new_wall,
                    "SDR": new_sdr.strip(),
                    "Color": new_color.strip(),
                    "Standard_Length": new_length,
                    "Unit": new_unit.strip()
                }

                try:

                    (
                        supabase
                        .table(ITEM_TABLE)
                        .update(payload)
                        .eq("Item_ID", selected_item)
                        .execute()
                    )

                    st.success(
                        "Item updated successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not update item: {e}"
                    )


    # =====================================================
    # DELETE ITEM
    # =====================================================

    with tab3:

        st.subheader("Delete Item")

        if items.empty:

            st.info("No items available.")

        else:

            delete_item = st.selectbox(
                "Select Item to Delete",
                items["Item_ID"].astype(str).tolist(),
                key="delete_item_select"
            )

            st.warning(
                "Deleting an item is permanent."
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
                            delete_item
                        )
                        .execute()
                    )

                    st.success(
                        "Item deleted successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not delete item: {e}"
                    )


    st.markdown("---")

    st.subheader("Registered Items")

    search_item = st.text_input(
        "Search Item",
        placeholder="Search by Item ID, Item Code or Application..."
    )

    display_items = items.copy()

    if search_item:

        mask = (
            display_items.astype(str)
            .apply(
                lambda col: col.str.contains(
                    search_item,
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


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.markdown(
        '<div class="page-kicker">MANUFACTURING</div>',
        unsafe_allow_html=True
    )

    st.title("Production Management")

    st.caption(
        "Manage production records, quantities and production status."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Production",
            "Update Production",
            "Delete Production"
        ]
    )


    # =====================================================
    # ADD PRODUCTION
    # =====================================================

    with tab1:

        st.subheader("Add Production Record")

        with st.form("add_production_form"):

            col1, col2, col3 = st.columns(3)

            with col1:

                production_id = st.text_input(
                    "Production ID *"
                )

                if not items.empty:

                    production_item = st.selectbox(
                        "Item ID",
                        items["Item_ID"].astype(str).tolist()
                    )

                else:

                    production_item = st.text_input(
                        "Item ID"
                    )

                production_date = st.date_input(
                    "Production Date"
                )

            with col2:

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

            with col3:

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


            submit_production = st.form_submit_button(
                "Add Production",
                type="primary"
            )


        if submit_production:

            if not production_id.strip():

                st.error(
                    "Production ID is required."
                )

            else:

                payload = {
                    "Production_ID": production_id.strip(),
                    "Item_ID": str(production_item),
                    "Production_Date": str(production_date),
                    "Batch_No": batch_no.strip(),
                    "Production_Line": production_line.strip(),
                    "Planned_Qty_m": planned_qty,
                    "Good_Qty_m": good_qty,
                    "Rejected_Qty_m": rejected_qty,
                    "Production_Status": production_status
                }

                try:

                    (
                        supabase
                        .table(PRODUCTION_TABLE)
                        .insert(payload)
                        .execute()
                    )

                    st.success(
                        "Production record added successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add production: {e}"
                    )


    # =====================================================
    # UPDATE PRODUCTION
    # =====================================================

    with tab2:

        st.subheader("Update Production")

        if production.empty:

            st.info("No production records available.")

        else:

            selected_production = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist()
            )

            current = production[
                production["Production_ID"].astype(str)
                == selected_production
            ].iloc[0]


            with st.form("update_production_form"):

                col1, col2, col3 = st.columns(3)

                with col1:

                    update_item = st.text_input(
                        "Item ID",
                        value=str(
                            current["Item_ID"]
                        )
                    )

                    update_date = st.text_input(
                        "Production Date",
                        value=str(
                            current["Production_Date"]
                        )
                    )

                    update_batch = st.text_input(
                        "Batch No",
                        value=str(
                            current["Batch_No"]
                            if pd.notna(current["Batch_No"])
                            else ""
                        )
                    )

                with col2:

                    update_line = st.text_input(
                        "Production Line",
                        value=str(
                            current["Production_Line"]
                            if pd.notna(current["Production_Line"])
                            else ""
                        )
                    )

                    update_planned = st.number_input(
                        "Planned Quantity (m)",
                        min_value=0,
                        value=int(
                            current["Planned_Qty_m"]
                            or 0
                        )
                    )

                    update_good = st.number_input(
                        "Good Quantity (m)",
                        min_value=0,
                        value=int(
                            current["Good_Qty_m"]
                            or 0
                        )
                    )

                with col3:

                    update_rejected = st.number_input(
                        "Rejected Quantity (m)",
                        min_value=0,
                        value=int(
                            current["Rejected_Qty_m"]
                            or 0
                        )
                    )

                    status_options = [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected"
                    ]

                    current_status = str(
                        current["Production_Status"]
                    )

                    status_index = (
                        status_options.index(
                            current_status
                        )
                        if current_status
                        in status_options
                        else 0
                    )

                    update_status = st.selectbox(
                        "Production Status",
                        status_options,
                        index=status_index
                    )


                update_production_btn = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


            if update_production_btn:

                payload = {
                    "Item_ID": update_item.strip(),
                    "Production_Date": update_date.strip(),
                    "Batch_No": update_batch.strip(),
                    "Production_Line": update_line.strip(),
                    "Planned_Qty_m": update_planned,
                    "Good_Qty_m": update_good,
                    "Rejected_Qty_m": update_rejected,
                    "Production_Status": update_status
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

                    st.success(
                        "Production updated successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not update production: {e}"
                    )


    # =====================================================
    # DELETE PRODUCTION
    # =====================================================

    with tab3:

        st.subheader("Delete Production")

        if production.empty:

            st.info("No production records available.")

        else:

            delete_production = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist(),
                key="delete_production"
            )

            st.warning(
                "Deleting this production record is permanent."
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

                    st.success(
                        "Production deleted successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not delete production: {e}"
                    )


    st.markdown("---")

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

    st.markdown(
        '<div class="page-kicker">INVENTORY</div>',
        unsafe_allow_html=True
    )

    st.title("Stock Control")

    st.caption(
        "Manage opening stock, production, dispatch and closing stock."
    )


    tab1, tab2, tab3 = st.tabs(
        [
            "Add Stock",
            "Update Stock",
            "Delete Stock"
        ]
    )


    # =====================================================
    # ADD STOCK
    # =====================================================

    with tab1:

        st.subheader("Add Stock Record")

        with st.form("add_stock_form"):

            col1, col2, col3 = st.columns(3)

            with col1:

                stock_id = st.text_input(
                    "Stock ID *"
                )

                if not items.empty:

                    stock_item = st.selectbox(
                        "Item ID",
                        items["Item_ID"].astype(str).tolist(),
                        key="stock_item"
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
                        ].astype(str).tolist()
                    )

                else:

                    stock_production = st.text_input(
                        "Production ID"
                    )

                batch_stock = st.text_input(
                    "Batch No"
                )

            with col2:

                stock_date = st.date_input(
                    "Stock Date"
                )

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0,
                    step=1
                )

                produced_stock_qty = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0,
                    step=1
                )

            with col3:

                dispatched_stock = st.number_input(
                    "Dispatched Quantity (m)",
                    min_value=0,
                    step=1
                )

                closing_stock_input = st.number_input(
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


            submit_stock = st.form_submit_button(
                "Add Stock",
                type="primary"
            )


        if submit_stock:

            if not stock_id.strip():

                st.error(
                    "Stock ID is required."
                )

            else:

                payload = {
                    "Stock_ID": stock_id.strip(),
                    "Item_ID": str(stock_item),
                    "Production_ID": str(stock_production),
                    "Batch_No": batch_stock.strip(),
                    "Stock_Date": str(stock_date),
                    "Opening_Stock_m": opening_stock,
                    "Produced_Qty_m": produced_stock_qty,
                    "Dispatched_Qty_m": dispatched_stock,
                    "Closing_Stock_m": closing_stock_input,
                    "Stock_Status": stock_status
                }

                try:

                    (
                        supabase
                        .table(STOCK_TABLE)
                        .insert(payload)
                        .execute()
                    )

                    st.success(
                        "Stock record added successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not add stock: {e}"
                    )


    # =====================================================
    # UPDATE STOCK
    # =====================================================

    with tab2:

        st.subheader("Update Stock")

        if stock.empty:

            st.info("No stock records available.")

        else:

            selected_stock = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist()
            )

            current = stock[
                stock["Stock_ID"].astype(str)
                == selected_stock
            ].iloc[0]


            with st.form("update_stock_form"):

                col1, col2, col3 = st.columns(3)

                with col1:

                    update_stock_item = st.text_input(
                        "Item ID",
                        value=str(
                            current["Item_ID"]
                        )
                    )

                    update_stock_production = st.text_input(
                        "Production ID",
                        value=str(
                            current["Production_ID"]
                        )
                    )

                    update_stock_batch = st.text_input(
                        "Batch No",
                        value=str(
                            current["Batch_No"]
                            if pd.notna(current["Batch_No"])
                            else ""
                        )
                    )

                with col2:

                    update_stock_date = st.text_input(
                        "Stock Date",
                        value=str(
                            current["Stock_Date"]
                        )
                    )

                    update_opening = st.number_input(
                        "Opening Stock (m)",
                        min_value=0,
                        value=int(
                            current["Opening_Stock_m"]
                            or 0
                        )
                    )

                    update_produced = st.number_input(
                        "Produced Quantity (m)",
                        min_value=0,
                        value=int(
                            current["Produced_Qty_m"]
                            or 0
                        )
                    )

                with col3:

                    update_dispatched = st.number_input(
                        "Dispatched Quantity (m)",
                        min_value=0,
                        value=int(
                            current["Dispatched_Qty_m"]
                            or 0
                        )
                    )

                    update_closing = st.number_input(
                        "Closing Stock (m)",
                        min_value=0,
                        value=int(
                            current["Closing_Stock_m"]
                            or 0
                        )
                    )

                    stock_status_options = [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]

                    current_stock_status = str(
                        current["Stock_Status"]
                    )

                    status_index = (
                        stock_status_options.index(
                            current_stock_status
                        )
                        if current_stock_status
                        in stock_status_options
                        else 0
                    )

                    update_stock_status = st.selectbox(
                        "Stock Status",
                        stock_status_options,
                        index=status_index
                    )


                update_stock_btn = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )


            if update_stock_btn:

                payload = {
                    "Item_ID": update_stock_item.strip(),
                    "Production_ID": update_stock_production.strip(),
                    "Batch_No": update_stock_batch.strip(),
                    "Stock_Date": update_stock_date.strip(),
                    "Opening_Stock_m": update_opening,
                    "Produced_Qty_m": update_produced,
                    "Dispatched_Qty_m": update_dispatched,
                    "Closing_Stock_m": update_closing,
                    "Stock_Status": update_stock_status
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

                    st.success(
                        "Stock updated successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not update stock: {e}"
                    )


    # =====================================================
    # DELETE STOCK
    # =====================================================

    with tab3:

        st.subheader("Delete Stock")

        if stock.empty:

            st.info("No stock records available.")

        else:

            delete_stock = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist(),
                key="delete_stock"
            )

            st.warning(
                "Deleting this stock record is permanent."
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

                    st.success(
                        "Stock deleted successfully."
                    )

                    refresh_data()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Could not delete stock: {e}"
                    )


    st.markdown("---")

    st.subheader("Stock Records")

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":

    st.markdown(
        '<div class="page-kicker">BUSINESS ANALYTICS</div>',
        unsafe_allow_html=True
    )

    st.title("Analytics")

    st.caption(
        "Production, rejection and inventory analysis."
    )


    # =====================================================
    # PRODUCTION ANALYSIS
    # =====================================================

    st.subheader("Production Analysis")

    if production.empty:

        st.info(
            "No production data available for analysis."
        )

    else:

        analysis = production.copy()

        analysis["Total_Production"] = (
            analysis["Good_Qty_m"]
            + analysis["Rejected_Qty_m"]
        )

        analysis["Yield_%"] = 0.0

        mask = (
            analysis["Total_Production"] > 0
        )

        analysis.loc[
            mask,
            "Yield_%"
        ] = (
            analysis.loc[
                mask,
                "Good_Qty_m"
            ]
            /
            analysis.loc[
                mask,
                "Total_Production"
            ]
            * 100
        )


        col1, col2 = st.columns(2)


        with col1:

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


        with col2:

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


        st.subheader("Production Analysis Table")

        st.dataframe(
            analysis,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # STOCK ANALYSIS
    # =====================================================

    st.subheader("Inventory Analysis")

    if stock.empty:

        st.info(
            "No stock data available for analysis."
        )

    else:

        stock_analysis = (
            stock
            .groupby(
                "Item_ID",
                as_index=False
            )
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
            title="Inventory Movement by Item"
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# DATA MANAGEMENT
# =========================================================

elif page == "Data Management":

    st.markdown(
        '<div class="page-kicker">DATABASE</div>',
        unsafe_allow_html=True
    )

    st.title("Data Management")

    st.caption(
        "Live Supabase database overview."
    )


    # =====================================================
    # TABLE COUNTS
    # =====================================================

    c1, c2, c3 = st.columns(3)


    with c1:

        st.metric(
            "Item Records",
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


    st.markdown("---")


    # =====================================================
    # ITEM TABLE
    # =====================================================

    with st.expander(
        "Item Registration Table",
        expanded=True
    ):

        st.dataframe(
            items,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # PRODUCTION TABLE
    # =====================================================

    with st.expander(
        "Production Table"
    ):

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # STOCK TABLE
    # =====================================================

    with st.expander(
        "Stock Control Table"
    ):

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # REFRESH
    # =====================================================

    st.markdown("---")

    if st.button(
        "Refresh Database Data"
    ):

        refresh_data()

        st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Flex Head Industries Pvt Ltd | Manufacturing ERP"
)
