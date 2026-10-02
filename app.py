import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import date

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Flex Head Industries | ERP",
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
            css = f.read()

        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )

    except FileNotFoundError:
        st.warning(
            "style.css nahi mili. app.py aur style.css same folder mein honi chahiye."
        )


load_css()

# =========================================================
# SUPABASE CONNECTION
# =========================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

except Exception:
    st.error("❌ Supabase Secrets missing.")
    st.info(
        "Streamlit Cloud → Settings → Secrets mein "
        "SUPABASE_URL aur SUPABASE_KEY add karo."
    )
    st.stop()


try:
    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

except Exception as e:
    st.error("❌ Supabase connection failed.")
    st.code(str(e))
    st.stop()


# =========================================================
# EXACT SUPABASE TABLE NAMES
# =========================================================

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
STOCK_TABLE = "Stock_Control"


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
# HELPER FUNCTIONS
# =========================================================

def empty_df(columns):
    return pd.DataFrame(columns=columns)


def safe_dataframe(response, columns):
    """
    Convert Supabase response into DataFrame.
    """
    if response is None:
        return empty_df(columns)

    data = response.data

    if not data:
        return empty_df(columns)

    df = pd.DataFrame(data)

    # Make sure expected columns exist
    for col in columns:
        if col not in df.columns:
            df[col] = None

    return df[columns]


def numeric_columns(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


# =========================================================
# LOAD FUNCTIONS
# =========================================================

@st.cache_data(ttl=5)
def load_items():

    response = (
        supabase
        .table(ITEM_TABLE)
        .select("*")
        .execute()
    )

    df = safe_dataframe(
        response,
        ITEM_COLUMNS
    )

    return numeric_columns(
        df,
        [
            "Nominal_Diameter_mm",
            "Wall_Thickness_mm",
            "Standard_Length"
        ]
    )


@st.cache_data(ttl=5)
def load_production():

    response = (
        supabase
        .table(PRODUCTION_TABLE)
        .select("*")
        .execute()
    )

    df = safe_dataframe(
        response,
        PRODUCTION_COLUMNS
    )

    return numeric_columns(
        df,
        [
            "Planned_Qty_m",
            "Good_Qty_m",
            "Rejected_Qty_m"
        ]
    )


@st.cache_data(ttl=5)
def load_stock():

    response = (
        supabase
        .table(STOCK_TABLE)
        .select("*")
        .execute()
    )

    df = safe_dataframe(
        response,
        STOCK_COLUMNS
    )

    return numeric_columns(
        df,
        [
            "Opening_Stock_m",
            "Produced_Qty_m",
            "Dispatched_Qty_m",
            "Closing_Stock_m"
        ]
    )


# =========================================================
# LOAD ALL LIVE DATA
# =========================================================

try:

    items = load_items()
    production = load_production()
    stock = load_stock()

except Exception as e:

    st.error("❌ SUPABASE DATA LOAD ERROR")

    st.markdown(
        """
        <div style="
            background:#fff3f3;
            border:1px solid #ffcccc;
            padding:18px;
            border-radius:12px;
            margin:10px 0;
        ">
        <b>Supabase se data read nahi ho raha.</b><br>
        Neeche actual error diya gaya hai.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.code(str(e))

    st.info(
        "Agar RLS enabled hai to existing SELECT policies "
        "anon/authenticated ke liye read allow karni chahiye."
    )

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">FH</div>
            <div>
                <div class="brand-name">Flex Head Industries</div>
                <div class="brand-sub">ERP MANAGEMENT SYSTEM</div>
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

    st.caption("Live Database")
    st.success("Supabase Connected")


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="page-kicker">FLEX HEAD INDUSTRIES PVT LTD</div>',
    unsafe_allow_html=True
)


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

if page == "Executive Dashboard":

    st.title("Executive Dashboard")

    st.caption(
        "Real-time overview of manufacturing, production and inventory."
    )

    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    registered_items = len(items)

    planned_production = production["Planned_Qty_m"].sum()

    good_production = production["Good_Qty_m"].sum()

    rejected_production = production["Rejected_Qty_m"].sum()

    produced_stock = stock["Produced_Qty_m"].sum()

    dispatched_stock = stock["Dispatched_Qty_m"].sum()

    current_stock = stock["Closing_Stock_m"].sum()

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
                <div class="metric-icon">▤</div>
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
                    Good output ratio
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


    st.markdown("<div class='section-gap'></div>",
                unsafe_allow_html=True)


    # -----------------------------------------------------
    # SECOND ROW
    # -----------------------------------------------------

    c5, c6, c7 = st.columns(3)

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
            "Dispatched",
            f"{dispatched_stock:,.0f} m"
        )


    st.markdown("---")


    # -----------------------------------------------------
    # CHARTS
    # -----------------------------------------------------

    left, right = st.columns(2)


    # Production Status

    with left:

        st.subheader("Production Status")

        if not production.empty:

            status_data = (
                production
                .fillna({"Production_Status": "Unknown"})
                ["Production_Status"]
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
                hole=0.55
            )

            fig.update_layout(
                margin=dict(
                    l=20,
                    r=20,
                    t=30,
                    b=20
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No production records found.")


    # Production Overview

    with right:

        st.subheader("Production Overview")

        if not production.empty:

            chart_data = production[
                [
                    "Production_ID",
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ]
            ].copy()

            chart_data = chart_data.head(20)

            fig = px.bar(
                chart_data,
                x="Production_ID",
                y=[
                    "Planned_Qty_m",
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                barmode="group"
            )

            fig.update_layout(
                margin=dict(
                    l=20,
                    r=20,
                    t=30,
                    b=50
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No production records found.")


    # -----------------------------------------------------
    # STOCK BY ITEM
    # -----------------------------------------------------

    st.subheader("Current Stock by Item")

    if not stock.empty:

        stock_chart = (
            stock
            .groupby("Item_ID", as_index=False)
            ["Closing_Stock_m"]
            .sum()
        )

        # Add Item Code safely
        if not items.empty:

            item_lookup = items[
                ["Item_ID", "Item_Code"]
            ].drop_duplicates(
                subset=["Item_ID"]
            )

            stock_chart = stock_chart.merge(
                item_lookup,
                on="Item_ID",
                how="left"
            )

        else:

            stock_chart["Item_Code"] = ""

        stock_chart["Display_Item"] = (
            stock_chart["Item_Code"]
            .fillna("")
            .astype(str)
            .replace("", None)
        )

        stock_chart["Display_Item"] = (
            stock_chart["Display_Item"]
            .fillna(stock_chart["Item_ID"])
        )

        fig = px.bar(
            stock_chart,
            x="Display_Item",
            y="Closing_Stock_m",
            text_auto=True
        )

        fig.update_layout(
            xaxis_title="Item",
            yaxis_title="Closing Stock (m)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:

        st.info("No stock records found.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.title("Item Registration")

    st.caption(
        "Manage pipe products and specifications."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "View Records",
            "Add Item",
            "Update / Delete"
        ]
    )


    # -----------------------------------------------------
    # VIEW
    # -----------------------------------------------------

    with tab1:

        search = st.text_input(
            "Search Item",
            placeholder="Search by Item ID, Item Code, Grade..."
        )

        display_items = items.copy()

        if search:

            mask = (
                display_items
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

            display_items = display_items[mask]

        st.dataframe(
            display_items,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"{len(display_items)} record(s)"
        )


    # -----------------------------------------------------
    # ADD
    # -----------------------------------------------------

    with tab2:

        with st.form("add_item_form"):

            c1, c2, c3 = st.columns(3)

            with c1:
                item_id = st.text_input("Item ID *")
                item_code = st.text_input("Item Code")
                material_grade = st.selectbox(
                    "Material Grade",
                    ["PE-80", "PE-100"]
                )
                application = st.text_input("Application")

            with c2:

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0
                )

                wall = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0
                )

                sdr = st.text_input("SDR")
                color = st.text_input("Color")

            with c3:

                standard_length = st.number_input(
                    "Standard Length",
                    min_value=0.0
                )

                unit = st.text_input(
                    "Unit",
                    value="Meter"
                )

            submit = st.form_submit_button(
                "Add Item",
                type="primary"
            )


        if submit:

            if not item_id.strip():

                st.error("Item ID required.")

            else:

                payload = {
                    "Item_ID": item_id.strip(),
                    "Item_Code": item_code.strip(),
                    "Material_Grade": material_grade,
                    "Application": application.strip(),
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
                    ).insert(
                        payload
                    ).execute()

                    st.success(
                        "✅ Item added successfully."
                    )

                    st.cache_data.clear()

                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Item add failed."
                    )

                    st.code(str(e))


    # -----------------------------------------------------
    # UPDATE / DELETE
    # -----------------------------------------------------

    with tab3:

        if items.empty:

            st.info("No items available.")

        else:

            selected_item = st.selectbox(
                "Select Item",
                items["Item_ID"].astype(str).tolist()
            )

            selected = items[
                items["Item_ID"].astype(str)
                == selected_item
            ].iloc[0]

            with st.form("update_item_form"):

                c1, c2 = st.columns(2)

                with c1:

                    new_code = st.text_input(
                        "Item Code",
                        value=str(
                            selected["Item_Code"]
                            if pd.notna(selected["Item_Code"])
                            else ""
                        )
                    )

                    new_grade = st.selectbox(
                        "Material Grade",
                        ["PE-80", "PE-100"],
                        index=(
                            1
                            if str(selected["Material_Grade"]) == "PE-100"
                            else 0
                        )
                    )

                    new_application = st.text_input(
                        "Application",
                        value=str(
                            selected["Application"]
                            if pd.notna(selected["Application"])
                            else ""
                        )
                    )

                    new_color = st.text_input(
                        "Color",
                        value=str(
                            selected["Color"]
                            if pd.notna(selected["Color"])
                            else ""
                        )
                    )

                with c2:

                    new_diameter = st.number_input(
                        "Nominal Diameter",
                        min_value=0.0,
                        value=float(
                            selected["Nominal_Diameter_mm"]
                            or 0
                        )
                    )

                    new_wall = st.number_input(
                        "Wall Thickness",
                        min_value=0.0,
                        value=float(
                            selected["Wall_Thickness_mm"]
                            or 0
                        )
                    )

                    new_sdr = st.text_input(
                        "SDR",
                        value=str(
                            selected["SDR"]
                            if pd.notna(selected["SDR"])
                            else ""
                        )
                    )

                    new_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            selected["Standard_Length"]
                            or 0
                        )
                    )

                    new_unit = st.text_input(
                        "Unit",
                        value=str(
                            selected["Unit"]
                            if pd.notna(selected["Unit"])
                            else ""
                        )
                    )

                update_button = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


            if update_button:

                payload = {
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

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).update(
                        payload
                    ).eq(
                        "Item_ID",
                        selected_item
                    ).execute()

                    st.success(
                        "✅ Item updated successfully."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Update failed."
                    )

                    st.code(str(e))


            st.markdown("---")

            if st.button(
                "🗑️ Delete Selected Item",
                type="secondary"
            ):

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).delete().eq(
                        "Item_ID",
                        selected_item
                    ).execute()

                    st.success(
                        "✅ Item deleted successfully."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Delete failed."
                    )

                    st.code(str(e))


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.title("Production")

    st.caption(
        "Manage daily pipe manufacturing production."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "View Records",
            "Add Production",
            "Update / Delete"
        ]
    )


    with tab1:

        search = st.text_input(
            "Search Production",
            placeholder="Production ID, Item ID, Batch..."
        )

        display = production.copy()

        if search:

            mask = (
                display
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

            display = display[mask]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )


    with tab2:

        with st.form("add_production"):

            c1, c2, c3 = st.columns(3)

            with c1:

                production_id = st.text_input(
                    "Production ID *"
                )

                item_id = st.selectbox(
                    "Item ID",
                    items["Item_ID"].astype(str).tolist()
                    if not items.empty
                    else [""]
                )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

            with c2:

                batch_no = st.text_input(
                    "Batch No"
                )

                production_line = st.text_input(
                    "Production Line"
                )

                planned_qty = st.number_input(
                    "Planned Quantity (m)",
                    min_value=0
                )

            with c3:

                good_qty = st.number_input(
                    "Good Quantity (m)",
                    min_value=0
                )

                rejected_qty = st.number_input(
                    "Rejected Quantity (m)",
                    min_value=0
                )

                status = st.selectbox(
                    "Production Status",
                    [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Rejected"
                    ]
                )

            submit = st.form_submit_button(
                "Add Production",
                type="primary"
            )


        if submit:

            if not production_id.strip():

                st.error(
                    "Production ID required."
                )

            else:

                payload = {
                    "Production_ID": production_id.strip(),
                    "Item_ID": item_id,
                    "Production_Date": str(production_date),
                    "Batch_No": batch_no,
                    "Production_Line": production_line,
                    "Planned_Qty_m": planned_qty,
                    "Good_Qty_m": good_qty,
                    "Rejected_Qty_m": rejected_qty,
                    "Production_Status": status
                }

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).insert(
                        payload
                    ).execute()

                    st.success(
                        "✅ Production record added."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Production add failed."
                    )

                    st.code(str(e))


    with tab3:

        if production.empty:

            st.info(
                "No production records."
            )

        else:

            selected_id = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].astype(str).tolist()
            )

            selected = production[
                production["Production_ID"].astype(str)
                == selected_id
            ].iloc[0]

            with st.form("update_production"):

                c1, c2 = st.columns(2)

                with c1:

                    edit_batch = st.text_input(
                        "Batch No",
                        value=str(
                            selected["Batch_No"]
                            if pd.notna(selected["Batch_No"])
                            else ""
                        )
                    )

                    edit_line = st.text_input(
                        "Production Line",
                        value=str(
                            selected["Production_Line"]
                            if pd.notna(selected["Production_Line"])
                            else ""
                        )
                    )

                    edit_planned = st.number_input(
                        "Planned Qty",
                        min_value=0,
                        value=int(
                            selected["Planned_Qty_m"]
                        )
                    )

                with c2:

                    edit_good = st.number_input(
                        "Good Qty",
                        min_value=0,
                        value=int(
                            selected["Good_Qty_m"]
                        )
                    )

                    edit_rejected = st.number_input(
                        "Rejected Qty",
                        min_value=0,
                        value=int(
                            selected["Rejected_Qty_m"]
                        )
                    )

                    edit_status = st.selectbox(
                        "Status",
                        [
                            "Completed",
                            "In Progress",
                            "Pending",
                            "Rejected"
                        ],
                        index=(
                            [
                                "Completed",
                                "In Progress",
                                "Pending",
                                "Rejected"
                            ].index(
                                str(
                                    selected["Production_Status"]
                                )
                            )
                            if str(
                                selected["Production_Status"]
                            ) in [
                                "Completed",
                                "In Progress",
                                "Pending",
                                "Rejected"
                            ]
                            else 0
                        )
                    )

                update = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


            if update:

                payload = {
                    "Batch_No": edit_batch,
                    "Production_Line": edit_line,
                    "Planned_Qty_m": edit_planned,
                    "Good_Qty_m": edit_good,
                    "Rejected_Qty_m": edit_rejected,
                    "Production_Status": edit_status
                }

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).update(
                        payload
                    ).eq(
                        "Production_ID",
                        selected_id
                    ).execute()

                    st.success(
                        "✅ Production updated."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Update failed."
                    )

                    st.code(str(e))


            if st.button(
                "🗑️ Delete Production"
            ):

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).delete().eq(
                        "Production_ID",
                        selected_id
                    ).execute()

                    st.success(
                        "✅ Production deleted."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Delete failed."
                    )

                    st.code(str(e))


# =========================================================
# STOCK CONTROL
# =========================================================

elif page == "Stock Control":

    st.title("Stock Control")

    st.caption(
        "Monitor opening stock, production, dispatch and closing inventory."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "View Records",
            "Add Stock",
            "Update / Delete"
        ]
    )


    with tab1:

        search = st.text_input(
            "Search Stock",
            placeholder="Stock ID, Item ID, Production ID..."
        )

        display = stock.copy()

        if search:

            mask = (
                display
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

            display = display[mask]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )


    with tab2:

        with st.form("add_stock"):

            c1, c2, c3 = st.columns(3)

            with c1:

                stock_id = st.text_input(
                    "Stock ID *"
                )

                item_id = st.selectbox(
                    "Item ID",
                    items["Item_ID"].astype(str).tolist()
                    if not items.empty
                    else [""]
                )

                production_id = st.selectbox(
                    "Production ID",
                    production[
                        "Production_ID"
                    ].astype(str).tolist()
                    if not production.empty
                    else [""]
                )

            with c2:

                batch_no = st.text_input(
                    "Batch No"
                )

                stock_date = st.date_input(
                    "Stock Date",
                    value=date.today()
                )

                opening_stock = st.number_input(
                    "Opening Stock (m)",
                    min_value=0
                )

            with c3:

                produced_qty = st.number_input(
                    "Produced Qty (m)",
                    min_value=0
                )

                dispatched_qty = st.number_input(
                    "Dispatched Qty (m)",
                    min_value=0
                )

                closing_stock = st.number_input(
                    "Closing Stock (m)",
                    min_value=0
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
                    "Stock ID required."
                )

            else:

                payload = {
                    "Stock_ID": stock_id.strip(),
                    "Item_ID": item_id,
                    "Production_ID": production_id,
                    "Batch_No": batch_no,
                    "Stock_Date": str(stock_date),
                    "Opening_Stock_m": opening_stock,
                    "Produced_Qty_m": produced_qty,
                    "Dispatched_Qty_m": dispatched_qty,
                    "Closing_Stock_m": closing_stock,
                    "Stock_Status": stock_status
                }

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).insert(
                        payload
                    ).execute()

                    st.success(
                        "✅ Stock record added."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Stock add failed."
                    )

                    st.code(str(e))


    with tab3:

        if stock.empty:

            st.info(
                "No stock records."
            )

        else:

            selected_id = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].astype(str).tolist()
            )

            selected = stock[
                stock["Stock_ID"].astype(str)
                == selected_id
            ].iloc[0]

            with st.form("update_stock"):

                c1, c2 = st.columns(2)

                with c1:

                    edit_batch = st.text_input(
                        "Batch No",
                        value=str(
                            selected["Batch_No"]
                            if pd.notna(selected["Batch_No"])
                            else ""
                        )
                    )

                    edit_opening = st.number_input(
                        "Opening Stock",
                        min_value=0,
                        value=int(
                            selected["Opening_Stock_m"]
                        )
                    )

                    edit_produced = st.number_input(
                        "Produced Qty",
                        min_value=0,
                        value=int(
                            selected["Produced_Qty_m"]
                        )
                    )

                with c2:

                    edit_dispatched = st.number_input(
                        "Dispatched Qty",
                        min_value=0,
                        value=int(
                            selected["Dispatched_Qty_m"]
                        )
                    )

                    edit_closing = st.number_input(
                        "Closing Stock",
                        min_value=0,
                        value=int(
                            selected["Closing_Stock_m"]
                        )
                    )

                    status_options = [
                        "Available",
                        "Low Stock",
                        "Out of Stock",
                        "Reserved"
                    ]

                    current_status = str(
                        selected["Stock_Status"]
                    )

                    edit_status = st.selectbox(
                        "Stock Status",
                        status_options,
                        index=(
                            status_options.index(
                                current_status
                            )
                            if current_status in status_options
                            else 0
                        )
                    )

                update = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )


            if update:

                payload = {
                    "Batch_No": edit_batch,
                    "Opening_Stock_m": edit_opening,
                    "Produced_Qty_m": edit_produced,
                    "Dispatched_Qty_m": edit_dispatched,
                    "Closing_Stock_m": edit_closing,
                    "Stock_Status": edit_status
                }

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).update(
                        payload
                    ).eq(
                        "Stock_ID",
                        selected_id
                    ).execute()

                    st.success(
                        "✅ Stock updated."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Update failed."
                    )

                    st.code(str(e))


            if st.button(
                "🗑️ Delete Stock"
            ):

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).delete().eq(
                        "Stock_ID",
                        selected_id
                    ).execute()

                    st.success(
                        "✅ Stock deleted."
                    )

                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:

                    st.error(
                        "❌ Delete failed."
                    )

                    st.code(str(e))


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":

    st.title("Analytics")

    st.caption(
        "Manufacturing and inventory performance analysis."
    )

    # -----------------------------------------------------
    # PRODUCTION ANALYTICS
    # -----------------------------------------------------

    if not production.empty:

        st.subheader("Production Performance")

        total_planned = production["Planned_Qty_m"].sum()
        total_good = production["Good_Qty_m"].sum()
        total_rejected = production["Rejected_Qty_m"].sum()

        a, b, c = st.columns(3)

        a.metric(
            "Planned",
            f"{total_planned:,.0f} m"
        )

        b.metric(
            "Good",
            f"{total_good:,.0f} m"
        )

        c.metric(
            "Rejected",
            f"{total_rejected:,.0f} m"
        )

        analysis = pd.DataFrame(
            {
                "Type": [
                    "Good Production",
                    "Rejected Production"
                ],
                "Quantity": [
                    total_good,
                    total_rejected
                ]
            }
        )

        fig = px.bar(
            analysis,
            x="Type",
            y="Quantity",
            text_auto=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    st.markdown("---")


    # -----------------------------------------------------
    # STOCK ANALYTICS
    # -----------------------------------------------------

    if not stock.empty:

        st.subheader("Inventory Analysis")

        stock_analysis = (
            stock
            .groupby("Item_ID", as_index=False)
            .agg(
                Opening_Stock=(
                    "Opening_Stock_m",
                    "sum"
                ),
                Produced=(
                    "Produced_Qty_m",
                    "sum"
                ),
                Dispatched=(
                    "Dispatched_Qty_m",
                    "sum"
                ),
                Closing_Stock=(
                    "Closing_Stock_m",
                    "sum"
                )
            )
        )

        st.dataframe(
            stock_analysis,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            stock_analysis,
            x="Item_ID",
            y=[
                "Opening_Stock",
                "Produced",
                "Dispatched",
                "Closing_Stock"
            ],
            barmode="group"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =========================================================
# DATA MANAGEMENT
# =========================================================

elif page == "Data Management":

    st.title("Data Management")

    st.caption(
        "Live Supabase database overview."
    )

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


    st.subheader("Item Registration")

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("Production")

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )


    st.subheader("Stock Control")

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Flex Head Industries Pvt Ltd • ERP Management System • Supabase Live Database"
)
