import os
import base64
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


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
# LOAD CSS
# =========================================================

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "style.css")

    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )


load_css()


# =========================================================
# COMPANY
# =========================================================

COMPANY = "Flex Head Industry Pvt Ltd"


# =========================================================
# TABLE CONFIG
# =========================================================

TABLES = {
    "Items": "item_registration",
    "Production": "production",
    "Stock Control": "stock_control"
}


CSV_FILES = {
    "Items": "Item_Registration.csv",
    "Production": "Production.csv",
    "Stock Control": "Stock_Control.csv"
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
# DATA HELPERS
# =========================================================

def ensure_columns(df, columns):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in columns:
        if col not in df.columns:
            df[col] = None

    return df


def ensure_numeric(df, columns):

    df = df.copy()

    for col in columns:

        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def ensure_text(df, columns):

    df = df.copy()

    for col in columns:

        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
            )

    return df


# =========================================================
# FETCH TABLE
# =========================================================

def fetch_table(name):

    table_name = TABLES[name]

    # ---------- SUPABASE ----------
    if supabase is not None:

        try:

            response = (
                supabase
                .table(table_name)
                .select("*")
                .execute()
            )

            data = response.data

            if data:
                return pd.DataFrame(data)

        except Exception as e:

            st.warning(
                f"Could not load {name} from Supabase: {e}"
            )

    # ---------- CSV FALLBACK ----------

    csv_file = CSV_FILES[name]

    if os.path.exists(csv_file):

        try:
            return pd.read_csv(csv_file)
        except Exception:
            pass

    return pd.DataFrame()


# =========================================================
# CRUD FUNCTIONS
# =========================================================

def insert_row(table_name, data):

    if supabase is not None:

        try:

            response = (
                supabase
                .table(TABLES[table_name])
                .insert(data)
                .execute()
            )

            return True, "Record added successfully."

        except Exception as e:

            return False, str(e)

    return False, "Supabase is not connected."


def update_row(table_name, record_id, id_column, data):

    if supabase is not None:

        try:

            response = (
                supabase
                .table(TABLES[table_name])
                .update(data)
                .eq(id_column, record_id)
                .execute()
            )

            return True, "Record updated successfully."

        except Exception as e:

            return False, str(e)

    return False, "Supabase is not connected."


def delete_row(table_name, record_id, id_column):

    if supabase is not None:

        try:

            response = (
                supabase
                .table(TABLES[table_name])
                .delete()
                .eq(id_column, record_id)
                .execute()
            )

            return True, "Record deleted successfully."

        except Exception as e:

            return False, str(e)

    return False, "Supabase is not connected."


# =========================================================
# LOAD DATA
# =========================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


items = ensure_columns(items, ITEM_COLUMNS)
production = ensure_columns(production, PRODUCTION_COLUMNS)
stock = ensure_columns(stock, STOCK_COLUMNS)


items = ensure_text(
    items,
    ["Item_ID", "Item_Code", "Material_Grade",
     "Application", "Color", "Unit"]
)

production = ensure_text(
    production,
    ["Production_ID", "Item_ID", "Batch_No",
     "Production_Line", "Production_Status"]
)

stock = ensure_text(
    stock,
    ["Stock_ID", "Item_ID", "Production_ID",
     "Batch_No", "Stock_Status"]
)


production = ensure_numeric(
    production,
    [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]
)


stock = ensure_numeric(
    stock,
    [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]
)


# =========================================================
# SIDEBAR BRAND / LOGO
# =========================================================

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
        <div class="brand-mark">FH</div>
        """

else:

    logo_html = """
    <div class="brand-mark">FH</div>
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


st.sidebar.markdown("---")


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

page = st.sidebar.radio(
    "ERP MODULES",
    [
        "Executive Dashboard",
        "Item Registration",
        "Production",
        "Stock Control",
        "Analytics",
        "Data Management"
    ]
)


st.sidebar.markdown("---")

if supabase is not None:

    st.sidebar.success(
        "● Supabase Connected"
    )

else:

    st.sidebar.warning(
        "● Supabase Not Connected"
    )


# =========================================================
# PAGE HEADER
# =========================================================

def page_header(kicker, title, description):

    st.markdown(
        f'<div class="page-kicker">{kicker}</div>',
        unsafe_allow_html=True
    )

    st.title(title)

    st.caption(description)


# =========================================================
# METRIC CARD
# =========================================================

def metric_card(label, value, icon="●", caption=""):

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


# =========================================================
# DASHBOARD
# =========================================================

def dashboard():

    page_header(
        "ERP / EXECUTIVE",
        "Executive Dashboard",
        "Real-time overview of Flex Head Industry operations."
    )

    good_qty = production["Good_Qty_m"].sum()
    rejected_qty = production["Rejected_Qty_m"].sum()
    dispatched = stock["Dispatched_Qty_m"].sum()
    closing_stock = stock["Closing_Stock_m"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        metric_card(
            "REGISTERED ITEMS",
            f"{len(items):,}",
            "▣",
            "Total item master records"
        )

    with c2:
        metric_card(
            "GOOD PRODUCTION",
            f"{good_qty:,.0f} m",
            "✓",
            "Accepted production"
        )

    with c3:
        metric_card(
            "REJECTED",
            f"{rejected_qty:,.0f} m",
            "!",
            "Rejected production"
        )

    with c4:
        metric_card(
            "DISPATCHED",
            f"{dispatched:,.0f} m",
            "→",
            "Total dispatched quantity"
        )

    with c5:
        metric_card(
            "CLOSING STOCK",
            f"{closing_stock:,.0f} m",
            "□",
            "Current stock"
        )

    st.markdown(
        '<div class="section-gap"></div>',
        unsafe_allow_html=True
    )

    # =====================================================
    # PRODUCTION PERFORMANCE
    # =====================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Production Performance")

        if not production.empty:

            p = production.copy()

            p["Production_Date"] = pd.to_datetime(
                p["Production_Date"],
                errors="coerce"
            )

            p = p.dropna(
                subset=["Production_Date"]
            )

            if not p.empty:

                daily = (
                    p.groupby(
                        "Production_Date",
                        as_index=False
                    )[
                        [
                            "Good_Qty_m",
                            "Rejected_Qty_m"
                        ]
                    ]
                    .sum()
                )

                fig = px.line(
                    daily,
                    x="Production_Date",
                    y=[
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ],
                    markers=True,
                    template="plotly_white"
                )

                fig.update_layout(
                    height=350,
                    margin=dict(
                        l=10,
                        r=10,
                        t=20,
                        b=10
                    ),
                    legend_title=""
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info("No valid production dates found.")

        else:

            st.info("No production data available.")

    # =====================================================
    # PRODUCTION STATUS
    # =====================================================

    with col2:

        st.subheader("Production Status")

        if not production.empty:

            status = (
                production[
                    "Production_Status"
                ]
                .fillna("Unknown")
                .replace("", "Unknown")
                .value_counts()
                .reset_index()
            )

            status.columns = [
                "Status",
                "Count"
            ]

            if not status.empty:

                fig = px.pie(
                    status,
                    names="Status",
                    values="Count",
                    hole=0.55,
                    template="plotly_white"
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

            else:

                st.info("No status data available.")

        else:

            st.info("No production data available.")

    # =====================================================
    # STOCK BY ITEM
    # =====================================================

    st.subheader("Stock by Item")

    if not stock.empty:

        s = stock.copy()
        i = items.copy()

        s = ensure_columns(
            s,
            [
                "Item_ID",
                "Closing_Stock_m"
            ]
        )

        i = ensure_columns(
            i,
            [
                "Item_ID",
                "Item_Code"
            ]
        )

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

        i["Item_Code"] = (
            i["Item_Code"]
            .fillna("")
            .astype(str)
        )

        s["Closing_Stock_m"] = pd.to_numeric(
            s["Closing_Stock_m"],
            errors="coerce"
        ).fillna(0)

        item_lookup = (
            i[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ]
            .drop_duplicates(
                subset=["Item_ID"]
            )
        )

        s = s.merge(
            item_lookup,
            on="Item_ID",
            how="left"
        )

        s["Item_Display"] = s["Item_Code"]

        s.loc[
            s["Item_Display"].eq(""),
            "Item_Display"
        ] = s["Item_ID"]

        stock_summary = (
            s.groupby(
                "Item_Display",
                as_index=False
            )["Closing_Stock_m"]
            .sum()
        )

        stock_summary = stock_summary.sort_values(
            "Closing_Stock_m",
            ascending=False
        )

        if not stock_summary.empty:

            fig = px.bar(
                stock_summary,
                x="Item_Display",
                y="Closing_Stock_m",
                template="plotly_white",
                text_auto=".0f"
            )

            fig.update_layout(
                height=350,
                margin=dict(
                    l=10,
                    r=10,
                    t=20,
                    b=10
                ),
                xaxis_title="Item",
                yaxis_title="Closing Stock (m)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        else:

            st.info("No stock records available.")

    else:

        st.info("No stock data available.")

    # =====================================================
    # RECENT PRODUCTION
    # =====================================================

    st.subheader("Recent Production")

    if not production.empty:

        recent_cols = [
            "Production_ID",
            "Item_ID",
            "Production_Date",
            "Batch_No",
            "Production_Line",
            "Good_Qty_m",
            "Rejected_Qty_m",
            "Production_Status"
        ]

        recent_cols = [
            c for c in recent_cols
            if c in production.columns
        ]

        recent = production[
            recent_cols
        ].copy()

        if "Production_Date" in recent.columns:

            recent["Production_Date"] = pd.to_datetime(
                recent["Production_Date"],
                errors="coerce"
            )

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

        st.info("No production records.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

def item_registration():

    page_header(
        "MASTER DATA",
        "Item Registration",
        "Register and manage pipe products."
    )

    search = st.text_input(
        "Search Item",
        placeholder="Search by Item ID, code, grade or application..."
    )

    display_items = items.copy()

    if search:

        search = search.lower()

        mask = display_items.astype(
            str
        ).apply(
            lambda col: col.str.lower().str.contains(
                search,
                na=False
            )
        ).any(axis=1)

        display_items = display_items[mask]

    st.dataframe(
        display_items,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Item",
            "✏️ Edit Item",
            "🗑️ Delete Item"
        ]
    )

    # =====================================================
    # ADD
    # =====================================================

    with tab1:

        with st.form("add_item"):

            c1, c2, c3 = st.columns(3)

            with c1:

                item_id = st.text_input(
                    "Item ID *"
                )

                item_code = st.text_input(
                    "Item Code *"
                )

                grade = st.text_input(
                    "Material Grade"
                )

            with c2:

                application = st.text_input(
                    "Application"
                )

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0
                )

                thickness = st.number_input(
                    "Wall Thickness (mm)",
                    min_value=0.0
                )

            with c3:

                sdr = st.number_input(
                    "SDR",
                    min_value=0.0
                )

                color = st.text_input(
                    "Color"
                )

                length = st.number_input(
                    "Standard Length",
                    min_value=0.0
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

                if not item_id or not item_code:

                    st.error(
                        "Item ID and Item Code are required."
                    )

                else:

                    data = {
                        "Item_ID": item_id,
                        "Item_Code": item_code,
                        "Material_Grade": grade,
                        "Application": application,
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": thickness,
                        "SDR": sdr,
                        "Color": color,
                        "Standard_Length": length,
                        "Unit": unit
                    }

                    ok, message = insert_row(
                        "Items",
                        data
                    )

                    if ok:

                        st.success(message)
                        st.rerun()

                    else:

                        st.error(message)

    # =====================================================
    # EDIT
    # =====================================================

    with tab2:

        if items.empty:

            st.info("No items available.")

        else:

            selected_id = st.selectbox(
                "Select Item",
                items["Item_ID"].astype(str).tolist()
            )

            selected = items[
                items["Item_ID"].astype(str)
                == str(selected_id)
            ]

            if not selected.empty:

                row = selected.iloc[0]

                with st.form("edit_item"):

                    item_code = st.text_input(
                        "Item Code",
                        value=str(
                            row.get(
                                "Item_Code",
                                ""
                            )
                        )
                    )

                    grade = st.text_input(
                        "Material Grade",
                        value=str(
                            row.get(
                                "Material_Grade",
                                ""
                            )
                        )
                    )

                    application = st.text_input(
                        "Application",
                        value=str(
                            row.get(
                                "Application",
                                ""
                            )
                        )
                    )

                    diameter = st.number_input(
                        "Nominal Diameter (mm)",
                        min_value=0.0,
                        value=float(
                            pd.to_numeric(
                                row.get(
                                    "Nominal_Diameter_mm",
                                    0
                                ),
                                errors="coerce"
                            ) or 0
                        )
                    )

                    thickness = st.number_input(
                        "Wall Thickness (mm)",
                        min_value=0.0,
                        value=float(
                            pd.to_numeric(
                                row.get(
                                    "Wall_Thickness_mm",
                                    0
                                ),
                                errors="coerce"
                            ) or 0
                        )
                    )

                    color = st.text_input(
                        "Color",
                        value=str(
                            row.get(
                                "Color",
                                ""
                            )
                        )
                    )

                    unit = st.text_input(
                        "Unit",
                        value=str(
                            row.get(
                                "Unit",
                                "m"
                            )
                        )
                    )

                    submitted = st.form_submit_button(
                        "Update Item",
                        type="primary"
                    )

                    if submitted:

                        data = {
                            "Item_Code": item_code,
                            "Material_Grade": grade,
                            "Application": application,
                            "Nominal_Diameter_mm": diameter,
                            "Wall_Thickness_mm": thickness,
                            "Color": color,
                            "Unit": unit
                        }

                        ok, message = update_row(
                            "Items",
                            selected_id,
                            "Item_ID",
                            data
                        )

                        if ok:

                            st.success(message)
                            st.rerun()

                        else:

                            st.error(message)

    # =====================================================
    # DELETE
    # =====================================================

    with tab3:

        if items.empty:

            st.info("No items available.")

        else:

            delete_id = st.selectbox(
                "Select Item to Delete",
                items["Item_ID"].astype(str).tolist(),
                key="delete_item"
            )

            if st.button(
                "Delete Item",
                type="primary"
            ):

                ok, message = delete_row(
                    "Items",
                    delete_id,
                    "Item_ID"
                )

                if ok:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# PRODUCTION
# =========================================================

def production_page():

    page_header(
        "OPERATIONS",
        "Production",
        "Track daily pipe manufacturing and production output."
    )

    st.dataframe(
        production,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    with st.form("add_production"):

        st.subheader("Add Production Record")

        c1, c2, c3 = st.columns(3)

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

        with c2:

            batch_no = st.text_input(
                "Batch No"
            )

            production_line = st.text_input(
                "Production Line"
            )

            planned = st.number_input(
                "Planned Quantity (m)",
                min_value=0.0
            )

        with c3:

            good = st.number_input(
                "Good Quantity (m)",
                min_value=0.0
            )

            rejected = st.number_input(
                "Rejected Quantity (m)",
                min_value=0.0
            )

            status = st.selectbox(
                "Production Status",
                [
                    "Completed",
                    "In Progress",
                    "Pending",
                    "Hold"
                ]
            )

        submitted = st.form_submit_button(
            "Add Production",
            type="primary"
        )

        if submitted:

            if not production_id or not item_id:

                st.error(
                    "Production ID and Item ID are required."
                )

            else:

                data = {
                    "Production_ID": production_id,
                    "Item_ID": item_id,
                    "Production_Date": str(
                        production_date
                    ),
                    "Batch_No": batch_no,
                    "Production_Line": production_line,
                    "Planned_Qty_m": planned,
                    "Good_Qty_m": good,
                    "Rejected_Qty_m": rejected,
                    "Production_Status": status
                }

                ok, message = insert_row(
                    "Production",
                    data
                )

                if ok:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# STOCK CONTROL
# =========================================================

def stock_control():

    page_header(
        "INVENTORY",
        "Stock Control",
        "Monitor opening, produced, dispatched and closing stock."
    )

    st.dataframe(
        stock,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    with st.form("add_stock"):

        st.subheader("Add Stock Record")

        c1, c2, c3 = st.columns(3)

        with c1:

            stock_id = st.text_input(
                "Stock ID *"
            )

            item_id = st.text_input(
                "Item ID *"
            )

            production_id = st.text_input(
                "Production ID"
            )

            batch_no = st.text_input(
                "Batch No"
            )

        with c2:

            stock_date = st.date_input(
                "Stock Date",
                value=date.today()
            )

            opening = st.number_input(
                "Opening Stock (m)",
                min_value=0.0
            )

            produced = st.number_input(
                "Produced Quantity (m)",
                min_value=0.0
            )

        with c3:

            dispatched = st.number_input(
                "Dispatched Quantity (m)",
                min_value=0.0
            )

            closing = max(
                0,
                opening + produced - dispatched
            )

            st.metric(
                "Calculated Closing Stock",
                f"{closing:,.2f} m"
            )

            status = st.selectbox(
                "Stock Status",
                [
                    "Available",
                    "Low Stock",
                    "Out of Stock"
                ]
            )

        submitted = st.form_submit_button(
            "Add Stock",
            type="primary"
        )

        if submitted:

            if not stock_id or not item_id:

                st.error(
                    "Stock ID and Item ID are required."
                )

            else:

                data = {
                    "Stock_ID": stock_id,
                    "Item_ID": item_id,
                    "Production_ID": production_id,
                    "Batch_No": batch_no,
                    "Stock_Date": str(
                        stock_date
                    ),
                    "Opening_Stock_m": opening,
                    "Produced_Qty_m": produced,
                    "Dispatched_Qty_m": dispatched,
                    "Closing_Stock_m": closing,
                    "Stock_Status": status
                }

                ok, message = insert_row(
                    "Stock Control",
                    data
                )

                if ok:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# ANALYTICS
# =========================================================

def analytics():

    page_header(
        "BUSINESS INTELLIGENCE",
        "Analytics",
        "Production, yield and item-level performance analysis."
    )

    if production.empty:

        st.info(
            "No production data available for analytics."
        )

        return

    p = production.copy()

    p = ensure_columns(
        p,
        PRODUCTION_COLUMNS
    )

    p = ensure_numeric(
        p,
        [
            "Planned_Qty_m",
            "Good_Qty_m",
            "Rejected_Qty_m"
        ]
    )

    # =====================================================
    # OVERALL YIELD
    # =====================================================

    total_good = p["Good_Qty_m"].sum()
    total_rejected = p["Rejected_Qty_m"].sum()

    total_output = (
        total_good +
        total_rejected
    )

    if total_output > 0:

        overall_yield = (
            total_good /
            total_output *
            100
        )

    else:

        overall_yield = 0

    c1, c2, c3 = st.columns(3)

    with c1:

        metric_card(
            "TOTAL GOOD",
            f"{total_good:,.0f} m",
            "✓",
            "Accepted output"
        )

    with c2:

        metric_card(
            "TOTAL REJECTED",
            f"{total_rejected:,.0f} m",
            "!",
            "Rejected output"
        )

    with c3:

        metric_card(
            "OVERALL YIELD",
            f"{overall_yield:.1f}%",
            "%",
            "Good output / total output"
        )

    st.markdown("---")

    # =====================================================
    # YIELD BY PRODUCTION LINE
    # =====================================================

    st.subheader("Yield by Production Line")

    line = (
        p.groupby(
            "Production_Line",
            as_index=False
        )
        .agg(
            Good=("Good_Qty_m", "sum"),
            Rejected=("Rejected_Qty_m", "sum")
        )
    )

    line["Total"] = (
        line["Good"] +
        line["Rejected"]
    )

    line["Yield_%"] = 0.0

    valid_line = line["Total"] > 0

    line.loc[
        valid_line,
        "Yield_%"
    ] = (
        line.loc[
            valid_line,
            "Good"
        ]
        /
        line.loc[
            valid_line,
            "Total"
        ]
        *
        100
    )

    fig = px.bar(
        line.sort_values("Yield_%"),
        x="Yield_%",
        y="Production_Line",
        orientation="h",
        template="plotly_white",
        text_auto=".1f"
    )

    fig.update_layout(
        height=350,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),
        xaxis_title="Yield %",
        yaxis_title=""
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # GOOD VS REJECTED
    # =====================================================

    st.subheader("Good vs Rejected Output")

    output = pd.DataFrame(
        {
            "Type": [
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
        output,
        x="Type",
        y="Quantity",
        template="plotly_white",
        text_auto=".0f"
    )

    fig.update_layout(
        height=350,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),
        yaxis_title="Quantity (m)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # ITEM LEVEL ANALYSIS
    # =====================================================

    st.subheader("Item-Level Production Analysis")

    item_analysis = (
        p.groupby(
            "Item_ID",
            as_index=False
        )
        .agg(
            Planned=("Planned_Qty_m", "sum"),
            Good=("Good_Qty_m", "sum"),
            Rejected=("Rejected_Qty_m", "sum")
        )
    )

    item_analysis["Total_Output"] = (
        item_analysis["Good"] +
        item_analysis["Rejected"]
    )

    item_analysis["Yield_%"] = 0.0

    valid_items = (
        item_analysis["Total_Output"] > 0
    )

    item_analysis.loc[
        valid_items,
        "Yield_%"
    ] = (
        item_analysis.loc[
            valid_items,
            "Good"
        ]
        /
        item_analysis.loc[
            valid_items,
            "Total_Output"
        ]
        *
        100
    )

    st.dataframe(
        item_analysis,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# DATA MANAGEMENT
# =========================================================

def data_management():

    page_header(
        "SYSTEM",
        "Data Management",
        "Database connection and ERP table information."
    )

    c1, c2 = st.columns(2)

    with c1:

        st.subheader("Database Status")

        if supabase is not None:

            st.success(
                "Supabase is connected."
            )

        else:

            st.warning(
                "Supabase is not connected."
            )

    with c2:

        st.subheader("ERP Tables")

        table_info = pd.DataFrame(
            {
                "Module": [
                    "Items",
                    "Production",
                    "Stock Control"
                ],
                "Supabase Table": [
                    "item_registration",
                    "production",
                    "stock_control"
                ],
                "Records": [
                    len(items),
                    len(production),
                    len(stock)
                ]
            }
        )

        st.dataframe(
            table_info,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    st.subheader("Expected Database Structure")

    st.code(
        """
item_registration
-----------------
Item_ID
Item_Code
Material_Grade
Application
Nominal_Diameter_mm
Wall_Thickness_mm
SDR
Color
Standard_Length
Unit


production
----------
Production_ID
Item_ID
Production_Date
Batch_No
Production_Line
Planned_Qty_m
Good_Qty_m
Rejected_Qty_m
Production_Status


stock_control
-------------
Stock_ID
Item_ID
Production_ID
Batch_No
Stock_Date
Opening_Stock_m
Produced_Qty_m
Dispatched_Qty_m
Closing_Stock_m
Stock_Status
        """,
        language="text"
    )


# =========================================================
# ROUTING
# =========================================================

if page == "Executive Dashboard":

    dashboard()

elif page == "Item Registration":

    item_registration()

elif page == "Production":

    production_page()

elif page == "Stock Control":

    stock_control()

elif page == "Analytics":

    analytics()

elif page == "Data Management":

    data_management()
