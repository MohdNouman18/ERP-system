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
# LOAD CSS
# ============================================================

def load_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            css = f.read()

        st.html(f"<style>{css}</style>")

    except FileNotFoundError:
        st.warning(
            "style.css nahi mili. app.py aur style.css same folder mein honi chahiye."
        )


load_css()


# ============================================================
# DATABASE CONFIG
# ============================================================

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

    if "SUPABASE_URL" not in st.secrets:
        st.error("SUPABASE_URL Streamlit Secrets mein nahi hai.")
        st.stop()

    if "SUPABASE_KEY" not in st.secrets:
        st.error("SUPABASE_KEY Streamlit Secrets mein nahi hai.")
        st.stop()

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
# DATAFRAME HELPER
# ============================================================

def prepare_dataframe(data, columns):

    df = pd.DataFrame(data or [])

    for col in columns:

        if col not in df.columns:
            df[col] = None

    return df[columns]


# ============================================================
# LOAD ITEMS
# ============================================================

@st.cache_data(ttl=5)
def load_items():

    response = (
        supabase
        .table(ITEM_TABLE)
        .select("*")
        .execute()
    )

    df = prepare_dataframe(
        response.data,
        ITEM_COLUMNS
    )

    numeric_cols = [
        "Nominal_Diameter_mm",
        "Wall_Thickness_mm",
        "Standard_Length"
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


# ============================================================
# LOAD PRODUCTION
# ============================================================

@st.cache_data(ttl=5)
def load_production():

    response = (
        supabase
        .table(PRODUCTION_TABLE)
        .select("*")
        .execute()
    )

    df = prepare_dataframe(
        response.data,
        PRODUCTION_COLUMNS
    )

    numeric_cols = [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


# ============================================================
# LOAD STOCK
# ============================================================

@st.cache_data(ttl=5)
def load_stock():

    response = (
        supabase
        .table(STOCK_TABLE)
        .select("*")
        .execute()
    )

    df = prepare_dataframe(
        response.data,
        STOCK_COLUMNS
    )

    numeric_cols = [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


# ============================================================
# LOAD DATABASE
# ============================================================

try:

    items = load_items()
    production = load_production()
    stock = load_stock()

except Exception as e:

    st.error("❌ SUPABASE DATA LOAD ERROR")

    st.error(
        "App Supabase tables ko read nahi kar pa rahi."
    )

    st.code(str(e))

    st.info(
        "Agar Supabase mein RLS enabled hai to SELECT policies check karo."
    )

    st.stop()


# ============================================================
# REFRESH FUNCTION
# ============================================================

def refresh_database():

    load_items.clear()
    load_production.clear()
    load_stock.clear()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.html(
        """
        <div class="brand">

            <div class="brand-mark">
                FH
            </div>

            <div>

                <div class="brand-name">
                    FLEX HEAD
                </div>

                <div class="brand-sub">
                    INDUSTRIES ERP
                </div>

            </div>

        </div>
        """
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

    st.html(
        """
        <div class="page-kicker">
            MANUFACTURING ERP
        </div>
        """
    )

    st.title("Executive Dashboard")

    st.caption(
        "Real-time overview of manufacturing, production and inventory."
    )


    # ========================================================
    # METRICS
    # ========================================================

    registered_items = len(items)

    planned_production = (
        production["Planned_Qty_m"]
        .sum()
    )

    good_production = (
        production["Good_Qty_m"]
        .sum()
    )

    rejected_production = (
        production["Rejected_Qty_m"]
        .sum()
    )

    produced_to_stock = (
        stock["Produced_Qty_m"]
        .sum()
    )

    dispatched = (
        stock["Dispatched_Qty_m"]
        .sum()
    )

    current_stock = (
        stock["Closing_Stock_m"]
        .sum()
    )

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
    # MAIN CARDS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.html(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ▣
                </div>

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
            """
        )


    with c2:

        st.html(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ✓
                </div>

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
            """
        )


    with c3:

        st.html(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    ◈
                </div>

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
            """
        )


    with c4:

        st.html(
            f"""
            <div class="metric-card">

                <div class="metric-icon">
                    %
                </div>

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
            """
        )


    st.markdown("")


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
    # PRODUCTION STATUS
    # ========================================================

    chart1, chart2 = st.columns(2)


    with chart1:

        st.subheader("Production Status")

        if production.empty:

            st.info(
                "No production records found."
            )

        else:

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
                height=360
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


    # ========================================================
    # PRODUCTION OVERVIEW
    # ========================================================

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
            height=360
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


    # ========================================================
    # STOCK
    # ========================================================

    st.subheader("Current Stock by Item")

    if stock.empty:

        st.info(
            "No stock records found."
        )

    else:

        stock_chart = (
            stock
            .groupby(
                "Item_ID",
                as_index=False
            )["Closing_Stock_m"]
            .sum()
        )

        if not items.empty:

            lookup = items[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].copy()

            stock_chart = stock_chart.merge(
                lookup,
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
            text_auto=True
        )

        fig.update_layout(
            height=400,
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# ITEM REGISTRATION
# ============================================================

elif page == "Item Registration":

    st.html(
        """
        <div class="page-kicker">
            MASTER DATA
        </div>
        """
    )

    st.title("Item Registration")

    st.caption(
        "Manage pipe manufacturing items."
    )


    add_tab, update_tab, delete_tab = st.tabs(
        [
            "Add Item",
            "Update Item",
            "Delete Item"
        ]
    )


    # ========================================================
    # ADD
    # ========================================================

    with add_tab:

        st.subheader("Register New Item")

        with st.form("add_item_form"):

            a, b, c = st.columns(3)

            with a:

                item_id = st.text_input(
                    "Item ID *"
                )

                item_code = st.text_input(
                    "Item Code"
                )

                grade = st.selectbox(
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

                color = st.text_input(
                    "Color"
                )

                length = st.number_input(
                    "Standard Length",
                    min_value=0.0,
                    step=1.0
                )

                unit = st.text_input(
                    "Unit",
                    value="m"
                )


            save = st.form_submit_button(
                "Add Item",
                type="primary"
            )


        if save:

            if not item_id.strip():

                st.error(
                    "Item ID required."
                )

            else:

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).insert(
                        {
                            "Item_ID":
                                item_id.strip(),
                            "Item_Code":
                                item_code.strip(),
                            "Material_Grade":
                                grade,
                            "Application":
                                application,
                            "Nominal_Diameter_mm":
                                diameter,
                            "Wall_Thickness_mm":
                                wall,
                            "SDR":
                                sdr.strip(),
                            "Color":
                                color.strip(),
                            "Standard_Length":
                                length,
                            "Unit":
                                unit.strip()
                        }
                    ).execute()

                    refresh_database()

                    st.success(
                        "Item added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Supabase insert failed."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE
    # ========================================================

    with update_tab:

        st.subheader("Update Item")

        if items.empty:

            st.info(
                "No item records available."
            )

        else:

            selected = st.selectbox(
                "Select Item",
                items["Item_ID"]
                .astype(str)
                .tolist()
            )

            row = items[
                items["Item_ID"].astype(str)
                == selected
            ].iloc[0]


            with st.form("update_item_form"):

                new_code = st.text_input(
                    "Item Code",
                    value=str(
                        row["Item_Code"]
                        if pd.notna(
                            row["Item_Code"]
                        )
                        else ""
                    )
                )

                new_grade = st.selectbox(
                    "Material Grade",
                    [
                        "PE-80",
                        "PE-100"
                    ]
                )

                new_application = st.selectbox(
                    "Application",
                    [
                        "Water",
                        "Sewerage",
                        "Gas"
                    ]
                )

                new_diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    value=float(
                        row[
                            "Nominal_Diameter_mm"
                        ]
                    )
                )

                new_wall = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0,
                    value=float(
                        row[
                            "Wall_Thickness_mm"
                        ]
                    )
                )

                new_sdr = st.text_input(
                    "SDR",
                    value=str(
                        row["SDR"]
                        if pd.notna(row["SDR"])
                        else ""
                    )
                )

                new_color = st.text_input(
                    "Color",
                    value=str(
                        row["Color"]
                        if pd.notna(row["Color"])
                        else ""
                    )
                )

                new_length = st.number_input(
                    "Standard Length",
                    min_value=0.0,
                    value=float(
                        row[
                            "Standard_Length"
                        ]
                    )
                )

                new_unit = st.text_input(
                    "Unit",
                    value=str(
                        row["Unit"]
                        if pd.notna(row["Unit"])
                        else "m"
                    )
                )

                update = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )


            if update:

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).update(
                        {
                            "Item_Code":
                                new_code.strip(),
                            "Material_Grade":
                                new_grade,
                            "Application":
                                new_application,
                            "Nominal_Diameter_mm":
                                new_diameter,
                            "Wall_Thickness_mm":
                                new_wall,
                            "SDR":
                                new_sdr.strip(),
                            "Color":
                                new_color.strip(),
                            "Standard_Length":
                                new_length,
                            "Unit":
                                new_unit.strip()
                        }
                    ).eq(
                        "Item_ID",
                        selected
                    ).execute()

                    refresh_database()

                    st.success(
                        "Item updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Update failed."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE
    # ========================================================

    with delete_tab:

        st.subheader("Delete Item")

        if items.empty:

            st.info(
                "No item records available."
            )

        else:

            delete_id = st.selectbox(
                "Select Item",
                items["Item_ID"]
                .astype(str)
                .tolist(),
                key="delete_item"
            )

            if st.button(
                "Delete Item",
                type="primary"
            ):

                try:

                    supabase.table(
                        ITEM_TABLE
                    ).delete().eq(
                        "Item_ID",
                        delete_id
                    ).execute()

                    refresh_database()

                    st.success(
                        "Item deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Delete failed."
                    )

                    st.code(str(e))


    st.markdown("---")

    st.subheader("Item Registration Records")

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PRODUCTION
# ============================================================

elif page == "Production":

    st.html(
        """
        <div class="page-kicker">
            MANUFACTURING
        </div>
        """
    )

    st.title("Production")

    st.caption(
        "Production records from Supabase."
    )


    add_tab, update_tab, delete_tab = st.tabs(
        [
            "Add Production",
            "Update Production",
            "Delete Production"
        ]
    )


    # ========================================================
    # ADD PRODUCTION
    # ========================================================

    with add_tab:

        with st.form("add_production_form"):

            production_id = st.text_input(
                "Production ID *"
            )

            if not items.empty:

                item_id = st.selectbox(
                    "Item ID",
                    items["Item_ID"]
                    .astype(str)
                    .tolist()
                )

            else:

                item_id = st.text_input(
                    "Item ID"
                )

            production_date = st.date_input(
                "Production Date"
            )

            batch_no = st.text_input(
                "Batch No"
            )

            production_line = st.text_input(
                "Production Line"
            )

            planned = st.number_input(
                "Planned Quantity (m)",
                min_value=0,
                step=1
            )

            good = st.number_input(
                "Good Quantity (m)",
                min_value=0,
                step=1
            )

            rejected = st.number_input(
                "Rejected Quantity (m)",
                min_value=0,
                step=1
            )

            status = st.selectbox(
                "Production Status",
                [
                    "Planned",
                    "In Progress",
                    "Completed",
                    "Rejected"
                ]
            )

            save = st.form_submit_button(
                "Add Production",
                type="primary"
            )


        if save:

            if not production_id.strip():

                st.error(
                    "Production ID required."
                )

            else:

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).insert(
                        {
                            "Production_ID":
                                production_id.strip(),
                            "Item_ID":
                                str(item_id),
                            "Production_Date":
                                str(production_date),
                            "Batch_No":
                                batch_no.strip(),
                            "Production_Line":
                                production_line.strip(),
                            "Planned_Qty_m":
                                planned,
                            "Good_Qty_m":
                                good,
                            "Rejected_Qty_m":
                                rejected,
                            "Production_Status":
                                status
                        }
                    ).execute()

                    refresh_database()

                    st.success(
                        "Production added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production insert failed."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE PRODUCTION
    # ========================================================

    with update_tab:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            selected = st.selectbox(
                "Production ID",
                production[
                    "Production_ID"
                ]
                .astype(str)
                .tolist(),
                key="update_production"
            )

            row = production[
                production[
                    "Production_ID"
                ].astype(str)
                == selected
            ].iloc[0]


            with st.form("update_production_form"):

                update_item = st.text_input(
                    "Item ID",
                    value=str(
                        row["Item_ID"]
                    )
                )

                update_date = st.text_input(
                    "Production Date",
                    value=str(
                        row["Production_Date"]
                    )
                )

                update_batch = st.text_input(
                    "Batch No",
                    value=str(
                        row["Batch_No"]
                        if pd.notna(
                            row["Batch_No"]
                        )
                        else ""
                    )
                )

                update_line = st.text_input(
                    "Production Line",
                    value=str(
                        row["Production_Line"]
                        if pd.notna(
                            row["Production_Line"]
                        )
                        else ""
                    )
                )

                update_planned = st.number_input(
                    "Planned Quantity",
                    min_value=0,
                    value=int(
                        row["Planned_Qty_m"]
                    )
                )

                update_good = st.number_input(
                    "Good Quantity",
                    min_value=0,
                    value=int(
                        row["Good_Qty_m"]
                    )
                )

                update_rejected = st.number_input(
                    "Rejected Quantity",
                    min_value=0,
                    value=int(
                        row["Rejected_Qty_m"]
                    )
                )

                update_status = st.selectbox(
                    "Status",
                    [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "Rejected"
                    ]
                )

                update = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )


            if update:

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).update(
                        {
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
                    ).eq(
                        "Production_ID",
                        selected
                    ).execute()

                    refresh_database()

                    st.success(
                        "Production updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production update failed."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE PRODUCTION
    # ========================================================

    with delete_tab:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            delete_id = st.selectbox(
                "Production ID",
                production[
                    "Production_ID"
                ]
                .astype(str)
                .tolist(),
                key="delete_production"
            )

            if st.button(
                "Delete Production",
                type="primary"
            ):

                try:

                    supabase.table(
                        PRODUCTION_TABLE
                    ).delete().eq(
                        "Production_ID",
                        delete_id
                    ).execute()

                    refresh_database()

                    st.success(
                        "Production deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Production delete failed."
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

    st.html(
        """
        <div class="page-kicker">
            INVENTORY
        </div>
        """
    )

    st.title("Stock Control")

    st.caption(
        "Live stock records from Supabase."
    )


    add_tab, update_tab, delete_tab = st.tabs(
        [
            "Add Stock",
            "Update Stock",
            "Delete Stock"
        ]
    )


    # ========================================================
    # ADD STOCK
    # ========================================================

    with add_tab:

        with st.form("add_stock_form"):

            stock_id = st.text_input(
                "Stock ID *"
            )

            if not items.empty:

                item_id = st.selectbox(
                    "Item ID",
                    items["Item_ID"]
                    .astype(str)
                    .tolist(),
                    key="stock_add_item"
                )

            else:

                item_id = st.text_input(
                    "Item ID"
                )

            if not production.empty:

                production_id = st.selectbox(
                    "Production ID",
                    production[
                        "Production_ID"
                    ]
                    .astype(str)
                    .tolist()
                )

            else:

                production_id = st.text_input(
                    "Production ID"
                )

            batch_no = st.text_input(
                "Batch No"
            )

            stock_date = st.date_input(
                "Stock Date"
            )

            opening = st.number_input(
                "Opening Stock (m)",
                min_value=0,
                step=1
            )

            produced = st.number_input(
                "Produced Quantity (m)",
                min_value=0,
                step=1
            )

            dispatched_qty = st.number_input(
                "Dispatched Quantity (m)",
                min_value=0,
                step=1
            )

            closing = st.number_input(
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

            save = st.form_submit_button(
                "Add Stock",
                type="primary"
            )


        if save:

            if not stock_id.strip():

                st.error(
                    "Stock ID required."
                )

            else:

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).insert(
                        {
                            "Stock_ID":
                                stock_id.strip(),
                            "Item_ID":
                                str(item_id),
                            "Production_ID":
                                str(production_id),
                            "Batch_No":
                                batch_no.strip(),
                            "Stock_Date":
                                str(stock_date),
                            "Opening_Stock_m":
                                opening,
                            "Produced_Qty_m":
                                produced,
                            "Dispatched_Qty_m":
                                dispatched_qty,
                            "Closing_Stock_m":
                                closing,
                            "Stock_Status":
                                stock_status
                        }
                    ).execute()

                    refresh_database()

                    st.success(
                        "Stock added successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock insert failed."
                    )

                    st.code(str(e))


    # ========================================================
    # UPDATE STOCK
    # ========================================================

    with update_tab:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            selected = st.selectbox(
                "Stock ID",
                stock[
                    "Stock_ID"
                ]
                .astype(str)
                .tolist(),
                key="update_stock"
            )

            row = stock[
                stock["Stock_ID"].astype(str)
                == selected
            ].iloc[0]


            with st.form("update_stock_form"):

                update_item = st.text_input(
                    "Item ID",
                    value=str(
                        row["Item_ID"]
                    )
                )

                update_production = st.text_input(
                    "Production ID",
                    value=str(
                        row["Production_ID"]
                    )
                )

                update_batch = st.text_input(
                    "Batch No",
                    value=str(
                        row["Batch_No"]
                        if pd.notna(
                            row["Batch_No"]
                        )
                        else ""
                    )
                )

                update_date = st.text_input(
                    "Stock Date",
                    value=str(
                        row["Stock_Date"]
                    )
                )

                update_opening = st.number_input(
                    "Opening Stock",
                    min_value=0,
                    value=int(
                        row["Opening_Stock_m"]
                    )
                )

                update_produced = st.number_input(
                    "Produced Quantity",
                    min_value=0,
                    value=int(
                        row["Produced_Qty_m"]
                    )
                )

                update_dispatched = st.number_input(
                    "Dispatched Quantity",
                    min_value=0,
                    value=int(
                        row["Dispatched_Qty_m"]
                    )
                )

                update_closing = st.number_input(
                    "Closing Stock",
                    min_value=0,
                    value=int(
                        row["Closing_Stock_m"]
                    )
                )

                update_status = st.selectbox(
                    "Stock Status",
                    [
                        "Available",
                        "Low Stock",
                        "Out of Stock"
                    ]
                )

                update = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )


            if update:

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).update(
                        {
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
                    ).eq(
                        "Stock_ID",
                        selected
                    ).execute()

                    refresh_database()

                    st.success(
                        "Stock updated successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock update failed."
                    )

                    st.code(str(e))


    # ========================================================
    # DELETE STOCK
    # ========================================================

    with delete_tab:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            delete_id = st.selectbox(
                "Stock ID",
                stock[
                    "Stock_ID"
                ]
                .astype(str)
                .tolist(),
                key="delete_stock"
            )

            if st.button(
                "Delete Stock",
                type="primary"
            ):

                try:

                    supabase.table(
                        STOCK_TABLE
                    ).delete().eq(
                        "Stock_ID",
                        delete_id
                    ).execute()

                    refresh_database()

                    st.success(
                        "Stock deleted successfully."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Stock delete failed."
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

    st.html(
        """
        <div class="page-kicker">
            BUSINESS ANALYTICS
        </div>
        """
    )

    st.title("Analytics")


    # ========================================================
    # PRODUCTION
    # ========================================================

    if production.empty:

        st.info(
            "No production records available."
        )

    else:

        analysis = production.copy()

        analysis["Total_Production"] = (
            analysis["Good_Qty_m"]
            +
            analysis["Rejected_Qty_m"]
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
            *
            100
        )


        c1, c2 = st.columns(2)


        with c1:

            fig = px.bar(
                analysis,
                x="Production_ID",
                y=[
                    "Good_Qty_m",
                    "Rejected_Qty_m"
                ],
                barmode="group",
                title="Good vs Rejected"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


        with c2:

            fig = px.bar(
                analysis,
                x="Production_ID",
                y="Yield_%",
                title="Production Yield"
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
    # STOCK
    # ========================================================

    if not stock.empty:

        st.subheader(
            "Inventory Movement"
        )

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
            barmode="group"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# DATA MANAGEMENT
# ============================================================

elif page == "Data Management":

    st.html(
        """
        <div class="page-kicker">
            DATABASE
        </div>
        """
    )

    st.title("Data Management")

    st.caption(
        "Live Supabase database records."
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


    st.subheader(
        "Item Registration"
    )

    st.dataframe(
        items,
        use_container_width=True,
        hide_index=True
    )


    st.subheader(
        "Production"
    )

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )


    st.subheader(
        "Stock Control"
    )

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )


    st.markdown("---")


    if st.button(
        "Refresh Live Database"
    ):

        refresh_database()

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Flex Head Industries Pvt Ltd | Manufacturing ERP"
)
