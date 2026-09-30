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
    page_title="Flex Head Industries ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# COMPANY
# =========================================================

COMPANY = "Flex Head Industries Pvt Ltd"


# =========================================================
# EXACT SUPABASE TABLE NAMES
# =========================================================

TABLES = {
    "Items": "Item_Registration",
    "Production": "Production",
    "Stock Control": "Stock_Control"
}


# =========================================================
# CSV FILES
# =========================================================

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
# CSS
# =========================================================

def load_css():

    css_file = "style.css"

    if os.path.exists(css_file):

        with open(css_file, "r", encoding="utf-8") as f:
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

    try:
        return create_client(url, key)
    except Exception:
        return None


supabase = get_supabase()


# =========================================================
# COLUMN HELPERS
# =========================================================

def ensure_columns(df, columns):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in columns:

        if col not in df.columns:
            df[col] = None

    return df


def clean_text_columns(df):

    if df is None or df.empty:
        return df

    df = df.copy()

    for col in df.columns:

        if df[col].dtype == "object":

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    return df


def safe_numeric(df, columns):

    if df is None or df.empty:
        return df

    df = df.copy()

    for col in columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def prepare_dataframe(name, df):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    if name == "Items":

        df = ensure_columns(
            df,
            ITEM_COLUMNS
        )

        df = safe_numeric(
            df,
            [
                "Nominal_Diameter_mm",
                "Wall_Thickness_mm",
                "Standard_Length"
            ]
        )

    elif name == "Production":

        df = ensure_columns(
            df,
            PRODUCTION_COLUMNS
        )

        df = safe_numeric(
            df,
            [
                "Planned_Qty_m",
                "Good_Qty_m",
                "Rejected_Qty_m"
            ]
        )

        if "Production_Date" in df.columns:

            df["Production_Date"] = pd.to_datetime(
                df["Production_Date"],
                errors="coerce"
            )

    elif name == "Stock Control":

        df = ensure_columns(
            df,
            STOCK_COLUMNS
        )

        df = safe_numeric(
            df,
            [
                "Opening_Stock_m",
                "Produced_Qty_m",
                "Dispatched_Qty_m",
                "Closing_Stock_m"
            ]
        )

        if "Stock_Date" in df.columns:

            df["Stock_Date"] = pd.to_datetime(
                df["Stock_Date"],
                errors="coerce"
            )

    return clean_text_columns(df)


# =========================================================
# LOAD TABLE
# =========================================================

def fetch_table(name):

    table_name = TABLES[name]

    # -----------------------------
    # SUPABASE
    # -----------------------------

    if supabase is not None:

        try:

            response = (
                supabase
                .table(table_name)
                .select("*")
                .execute()
            )

            data = response.data

            if data is not None:

                return prepare_dataframe(
                    name,
                    pd.DataFrame(data)
                )

        except Exception as e:

            st.warning(
                f"Supabase could not load {name}: {str(e)}"
            )

    # -----------------------------
    # CSV FALLBACK
    # -----------------------------

    csv_file = CSV_FILES[name]

    if os.path.exists(csv_file):

        try:

            df = pd.read_csv(csv_file)

            return prepare_dataframe(
                name,
                df
            )

        except Exception as e:

            st.warning(
                f"Could not read {csv_file}: {str(e)}"
            )

    return prepare_dataframe(
        name,
        pd.DataFrame()
    )


# =========================================================
# CRUD HELPERS
# =========================================================

def insert_record(name, data):

    table_name = TABLES[name]

    try:

        if supabase is not None:

            response = (
                supabase
                .table(table_name)
                .insert(data)
                .execute()
            )

            return True, "Record added successfully."

        # CSV fallback
        csv_file = CSV_FILES[name]

        df = fetch_table(name)

        new_row = pd.DataFrame([data])

        df = pd.concat(
            [df, new_row],
            ignore_index=True
        )

        df.to_csv(
            csv_file,
            index=False
        )

        return True, "Record added to CSV."

    except Exception as e:

        return False, str(e)


def update_record(name, primary_key, primary_value, data):

    table_name = TABLES[name]

    try:

        if supabase is not None:

            (
                supabase
                .table(table_name)
                .update(data)
                .eq(primary_key, primary_value)
                .execute()
            )

            return True, "Record updated successfully."

        # CSV fallback
        csv_file = CSV_FILES[name]

        df = fetch_table(name)

        if primary_key not in df.columns:
            return False, f"{primary_key} column not found."

        mask = (
            df[primary_key]
            .astype(str)
            .str.strip()
            ==
            str(primary_value).strip()
        )

        if not mask.any():
            return False, "Record not found."

        for key, value in data.items():

            if key in df.columns:
                df.loc[mask, key] = value

        df.to_csv(
            csv_file,
            index=False
        )

        return True, "Record updated in CSV."

    except Exception as e:

        return False, str(e)


def delete_record(name, primary_key, primary_value):

    table_name = TABLES[name]

    try:

        if supabase is not None:

            (
                supabase
                .table(table_name)
                .delete()
                .eq(primary_key, primary_value)
                .execute()
            )

            return True, "Record deleted successfully."

        # CSV fallback
        csv_file = CSV_FILES[name]

        df = fetch_table(name)

        if primary_key not in df.columns:
            return False, f"{primary_key} column not found."

        mask = (
            df[primary_key]
            .astype(str)
            .str.strip()
            ==
            str(primary_value).strip()
        )

        df = df.loc[~mask].copy()

        df.to_csv(
            csv_file,
            index=False
        )

        return True, "Record deleted from CSV."

    except Exception as e:

        return False, str(e)


# =========================================================
# LOAD ALL DATA
# =========================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


# =========================================================
# GENERAL UI HELPERS
# =========================================================

def page_header(title, subtitle=""):

    st.markdown(
        f"""
        <div class="page-kicker">FLEX HEAD INDUSTRIES ERP</div>
        <h1>{title}</h1>
        <p style="color:#71808c;">{subtitle}</p>
        """,
        unsafe_allow_html=True
    )


def metric_card(label, value, caption="", icon="●"):

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def format_number(value):

    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    if os.path.exists("logo.png"):

        try:

            with open("logo.png", "rb") as f:

                encoded = base64.b64encode(
                    f.read()
                ).decode()

            st.markdown(
                f"""
                <div class="brand">
                    <img
                        src="data:image/png;base64,{encoded}"
                        class="company-logo"
                    >
                    <div>
                        <div class="brand-name">
                            Flex Head Industries
                        </div>
                        <div class="brand-sub">
                            ERP SYSTEM
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        except Exception:

            st.markdown(
                """
                <div class="brand">
                    <div class="brand-mark">FH</div>
                    <div>
                        <div class="brand-name">
                            Flex Head Industries
                        </div>
                        <div class="brand-sub">
                            ERP SYSTEM
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.markdown(
            """
            <div class="brand">
                <div class="brand-mark">FH</div>
                <div>
                    <div class="brand-name">
                        Flex Head Industries
                    </div>
                    <div class="brand-sub">
                        ERP SYSTEM
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

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

    st.markdown("---")

    if supabase is not None:

        st.success(
            "🟢 Supabase Connected"
        )

    else:

        st.warning(
            "🟡 CSV / Local Mode"
        )

    st.caption(
        "ERP Management System"
    )


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

def dashboard():

    page_header(
        "Executive Dashboard",
        "Production, inventory and operational performance overview."
    )

    items_df = items.copy()
    production_df = production.copy()
    stock_df = stock.copy()

    # -----------------------------
    # KPIs
    # -----------------------------

    total_items = len(items_df)

    total_good = (
        production_df["Good_Qty_m"].sum()
        if "Good_Qty_m" in production_df.columns
        else 0
    )

    current_stock = (
        stock_df["Closing_Stock_m"].sum()
        if "Closing_Stock_m" in stock_df.columns
        else 0
    )

    planned = (
        production_df["Planned_Qty_m"].sum()
        if "Planned_Qty_m" in production_df.columns
        else 0
    )

    rejected = (
        production_df["Rejected_Qty_m"].sum()
        if "Rejected_Qty_m" in production_df.columns
        else 0
    )

    total_output = total_good + rejected

    if total_output > 0:
        yield_rate = (
            total_good /
            total_output
            * 100
        )
    else:
        yield_rate = 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "REGISTERED ITEMS",
            format_number(total_items),
            "Product master records",
            "▣"
        )

    with c2:
        metric_card(
            "GOOD PRODUCTION",
            f"{format_number(total_good)} m",
            "Accepted production",
            "↗"
        )

    with c3:
        metric_card(
            "CURRENT STOCK",
            f"{format_number(current_stock)} m",
            "Closing inventory",
            "◫"
        )

    with c4:
        metric_card(
            "PRODUCTION YIELD",
            f"{yield_rate:.1f}%",
            "Good output ratio",
            "%"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------
    # FILTERS
    # -----------------------------

    if not production_df.empty:

        st.subheader("Dashboard Filters")

        f1, f2 = st.columns(2)

        with f1:

            lines = ["All"]

            if "Production_Line" in production_df.columns:

                values = (
                    production_df["Production_Line"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                lines += sorted(values)

            selected_line = st.selectbox(
                "Production Line",
                lines
            )

        with f2:

            statuses = ["All"]

            if "Production_Status" in production_df.columns:

                values = (
                    production_df["Production_Status"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                statuses += sorted(values)

            selected_status = st.selectbox(
                "Production Status",
                statuses
            )

        filtered = production_df.copy()

        if selected_line != "All":

            filtered = filtered[
                filtered["Production_Line"].astype(str)
                == selected_line
            ]

        if selected_status != "All":

            filtered = filtered[
                filtered["Production_Status"].astype(str)
                == selected_status
            ]

    else:

        filtered = production_df.copy()

    # -----------------------------
    # PRODUCTION TREND
    # -----------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Production Trend")

        if (
            not filtered.empty
            and "Production_Date" in filtered.columns
        ):

            chart_df = filtered.copy()

            chart_df["Production_Date"] = pd.to_datetime(
                chart_df["Production_Date"],
                errors="coerce"
            )

            chart_df = chart_df.dropna(
                subset=["Production_Date"]
            )

            if not chart_df.empty:

                trend = (
                    chart_df
                    .groupby("Production_Date", as_index=False)[
                        ["Good_Qty_m", "Rejected_Qty_m"]
                    ]
                    .sum()
                )

                fig = px.line(
                    trend,
                    x="Production_Date",
                    y=[
                        "Good_Qty_m",
                        "Rejected_Qty_m"
                    ],
                    markers=True,
                    labels={
                        "value": "Quantity (m)",
                        "Production_Date": "Production Date",
                        "variable": "Production Type"
                    }
                )

                fig.update_layout(
                    height=380,
                    margin=dict(
                        l=10,
                        r=10,
                        t=30,
                        b=10
                    ),
                    legend_title=""
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "No valid production dates available."
                )

        else:

            st.info(
                "No production data available."
            )

    # -----------------------------
    # STATUS
    # -----------------------------

    with col2:

        st.subheader("Production Status")

        if (
            not filtered.empty
            and "Production_Status" in filtered.columns
        ):

            status_df = (
                filtered["Production_Status"]
                .value_counts()
                .reset_index()
            )

            status_df.columns = [
                "Status",
                "Count"
            ]

            if not status_df.empty:

                fig = px.pie(
                    status_df,
                    names="Status",
                    values="Count",
                    hole=0.55
                )

                fig.update_layout(
                    height=380,
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
                "No production status data available."
            )

    # -----------------------------
    # STOCK BY ITEM
    # -----------------------------

    st.subheader("Stock by Item")

    if (
        not stock_df.empty
        and "Item_ID" in stock_df.columns
        and "Closing_Stock_m" in stock_df.columns
    ):

        stock_chart = (
            stock_df
            .groupby("Item_ID", as_index=False)[
                "Closing_Stock_m"
            ]
            .sum()
        )

        if not items_df.empty and "Item_ID" in items_df.columns:

            lookup = items_df[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].drop_duplicates()

            stock_chart = stock_chart.merge(
                lookup,
                on="Item_ID",
                how="left"
            )

            stock_chart["Display"] = (
                stock_chart["Item_Code"]
                .fillna(stock_chart["Item_ID"])
            )

        else:

            stock_chart["Display"] = (
                stock_chart["Item_ID"]
            )

        fig = px.bar(
            stock_chart,
            x="Display",
            y="Closing_Stock_m",
            labels={
                "Display": "Item",
                "Closing_Stock_m": "Closing Stock (m)"
            }
        )

        fig.update_layout(
            height=400,
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
            "No stock data available."
        )

    # -----------------------------
    # OPERATIONAL SUMMARY
    # -----------------------------

    st.subheader("Operational Summary")

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "Planned Production",
            f"{format_number(planned)} m"
        )

    with b:
        st.metric(
            "Good Production",
            f"{format_number(total_good)} m"
        )

    with c:
        st.metric(
            "Rejected",
            f"{format_number(rejected)} m"
        )

    with d:
        dispatched = (
            stock_df["Dispatched_Qty_m"].sum()
            if "Dispatched_Qty_m" in stock_df.columns
            else 0
        )

        st.metric(
            "Dispatched",
            f"{format_number(dispatched)} m"
        )

    # -----------------------------
    # RECENT PRODUCTION
    # -----------------------------

    st.subheader("Recent Production")

    if not production_df.empty:

        recent = production_df.copy()

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

        st.info(
            "No production records available."
        )


# =========================================================
# ITEM REGISTRATION CRUD
# =========================================================

def item_registration():

    page_header(
        "Item Registration",
        "Manage pipe products, material grades and specifications."
    )

    df = items.copy()

    # -----------------------------
    # SEARCH
    # -----------------------------

    search = st.text_input(
        "🔎 Search Items",
        placeholder="Search by Item ID, Item Code, Material or Application..."
    )

    if search:

        search_lower = search.lower()

        mask = df.astype(str).apply(
            lambda row:
            row.str.lower().str.contains(
                search_lower,
                na=False
            ).any(),
            axis=1
        )

        df = df[mask]

    st.subheader(
        f"Item Records: {len(df)}"
    )

    st.dataframe(
        df,
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

        with st.form("add_item_form"):

            c1, c2, c3 = st.columns(3)

            with c1:

                item_id = st.text_input(
                    "Item ID *",
                    placeholder="ITM-008"
                )

                item_code = st.text_input(
                    "Item Code *"
                )

                material = st.text_input(
                    "Material Grade",
                    placeholder="PE-100"
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

                diameter = st.number_input(
                    "Nominal Diameter (mm)",
                    min_value=0.0,
                    step=0.1
                )

                wall = st.number_input(
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
                    step=1.0,
                    value=100.0
                )

                unit = st.text_input(
                    "Unit",
                    value="m"
                )

            submit = st.form_submit_button(
                "Add Item",
                type="primary"
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
                        "Material_Grade": material.strip(),
                        "Application": application,
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": wall,
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

    # =====================================================
    # EDIT
    # =====================================================

    with tab2:

        if items.empty:

            st.info(
                "No items available for editing."
            )

        else:

            ids = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
                if "Item_ID" in items.columns
                else []
            )

            if ids:

                selected_id = st.selectbox(
                    "Select Item",
                    ids
                )

                selected = items[
                    items["Item_ID"].astype(str)
                    == selected_id
                ]

                if not selected.empty:

                    row = selected.iloc[0]

                    with st.form("edit_item_form"):

                        c1, c2, c3 = st.columns(3)

                        with c1:

                            st.text_input(
                                "Item ID",
                                value=selected_id,
                                disabled=True
                            )

                            item_code = st.text_input(
                                "Item Code",
                                value=str(
                                    row.get(
                                        "Item_Code",
                                        ""
                                    )
                                )
                            )

                            material = st.text_input(
                                "Material Grade",
                                value=str(
                                    row.get(
                                        "Material_Grade",
                                        ""
                                    )
                                )
                            )

                        with c2:

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
                                    row.get(
                                        "Nominal_Diameter_mm",
                                        0
                                    ) or 0
                                ),
                                step=0.1
                            )

                            wall = st.number_input(
                                "Wall Thickness (mm)",
                                min_value=0.0,
                                value=float(
                                    row.get(
                                        "Wall_Thickness_mm",
                                        0
                                    ) or 0
                                ),
                                step=0.1
                            )

                        with c3:

                            sdr = st.text_input(
                                "SDR",
                                value=str(
                                    row.get(
                                        "SDR",
                                        ""
                                    )
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

                            standard_length = st.number_input(
                                "Standard Length",
                                min_value=0.0,
                                value=float(
                                    row.get(
                                        "Standard_Length",
                                        0
                                    ) or 0
                                ),
                                step=1.0
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

                        update_btn = st.form_submit_button(
                            "Update Item",
                            type="primary"
                        )

                        if update_btn:

                            data = {
                                "Item_Code": item_code.strip(),
                                "Material_Grade": material.strip(),
                                "Application": application.strip(),
                                "Nominal_Diameter_mm": diameter,
                                "Wall_Thickness_mm": wall,
                                "SDR": sdr.strip(),
                                "Color": color.strip(),
                                "Standard_Length": standard_length,
                                "Unit": unit.strip()
                            }

                            success, message = update_record(
                                "Items",
                                "Item_ID",
                                selected_id,
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

    with tab3:

        if items.empty:

            st.info(
                "No items available for deletion."
            )

        else:

            ids = (
                items["Item_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Item to Delete",
                ids,
                key="delete_item_id"
            )

            st.warning(
                f"You are about to delete Item: {selected_id}"
            )

            confirm = st.checkbox(
                "I confirm that I want to delete this record."
            )

            if st.button(
                "Delete Item",
                type="primary",
                disabled=not confirm
            ):

                success, message = delete_record(
                    "Items",
                    "Item_ID",
                    selected_id
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# PRODUCTION CRUD
# =========================================================

def production_page():

    page_header(
        "Production Management",
        "Manage production batches, quantities, lines and quality status."
    )

    df = production.copy()

    st.subheader(
        f"Production Records: {len(df)}"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Production",
            "✏️ Edit Production",
            "🗑️ Delete Production"
        ]
    )

    item_ids = []

    if not items.empty and "Item_ID" in items.columns:

        item_ids = (
            items["Item_ID"]
            .dropna()
            .astype(str)
            .tolist()
        )

    # =====================================================
    # ADD
    # =====================================================

    with tab1:

        with st.form("add_production_form"):

            c1, c2 = st.columns(2)

            with c1:

                production_id = st.text_input(
                    "Production ID *",
                    placeholder="PRD-001"
                )

                item_id = st.selectbox(
                    "Item ID",
                    item_ids if item_ids else [""]
                )

                production_date = st.date_input(
                    "Production Date",
                    value=date.today()
                )

                batch_no = st.text_input(
                    "Batch No.",
                    placeholder="BATCH-001"
                )

                production_line = st.text_input(
                    "Production Line",
                    placeholder="Line 01"
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

                status = st.selectbox(
                    "Production Status",
                    [
                        "Planned",
                        "In Progress",
                        "Completed",
                        "On Hold",
                        "Cancelled"
                    ]
                )

            submit = st.form_submit_button(
                "Add Production",
                type="primary"
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
                            status
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

    with tab2:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            ids = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Production Record",
                ids,
                key="edit_production_id"
            )

            selected = production[
                production["Production_ID"].astype(str)
                == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                with st.form("edit_production_form"):

                    c1, c2 = st.columns(2)

                    with c1:

                        st.text_input(
                            "Production ID",
                            value=selected_id,
                            disabled=True
                        )

                        current_item = str(
                            row.get(
                                "Item_ID",
                                ""
                            )
                        )

                        edit_items = item_ids.copy()

                        if (
                            current_item
                            and current_item not in edit_items
                        ):

                            edit_items.insert(
                                0,
                                current_item
                            )

                        item_id = st.selectbox(
                            "Item ID",
                            edit_items
                            if edit_items
                            else [""],
                            index=(
                                edit_items.index(
                                    current_item
                                )
                                if current_item
                                in edit_items
                                else 0
                            )
                        )

                        current_date = pd.to_datetime(
                            row.get(
                                "Production_Date"
                            ),
                            errors="coerce"
                        )

                        if pd.isna(current_date):

                            current_date = pd.Timestamp.today()

                        production_date = st.date_input(
                            "Production Date",
                            value=current_date.date()
                        )

                        batch_no = st.text_input(
                            "Batch No.",
                            value=str(
                                row.get(
                                    "Batch_No",
                                    ""
                                )
                            )
                        )

                        production_line = st.text_input(
                            "Production Line",
                            value=str(
                                row.get(
                                    "Production_Line",
                                    ""
                                )
                            )
                        )

                    with c2:

                        planned_qty = st.number_input(
                            "Planned Quantity (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Planned_Qty_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        good_qty = st.number_input(
                            "Good Quantity (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Good_Qty_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        rejected_qty = st.number_input(
                            "Rejected Quantity (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Rejected_Qty_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        current_status = str(
                            row.get(
                                "Production_Status",
                                "Planned"
                            )
                        )

                        status_options = [
                            "Planned",
                            "In Progress",
                            "Completed",
                            "On Hold",
                            "Cancelled"
                        ]

                        if (
                            current_status
                            not in status_options
                        ):

                            status_options.insert(
                                0,
                                current_status
                            )

                        status = st.selectbox(
                            "Production Status",
                            status_options,
                            index=status_options.index(
                                current_status
                            )
                        )

                    update_btn = st.form_submit_button(
                        "Update Production",
                        type="primary"
                    )

                    if update_btn:

                        data = {
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
                                status
                        }

                        success, message = update_record(
                            "Production",
                            "Production_ID",
                            selected_id,
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

    with tab3:

        if production.empty:

            st.info(
                "No production records available."
            )

        else:

            ids = (
                production["Production_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Production Record",
                ids,
                key="delete_production_id"
            )

            confirm = st.checkbox(
                "I confirm that I want to delete this production record."
            )

            if st.button(
                "Delete Production",
                type="primary",
                disabled=not confirm
            ):

                success, message = delete_record(
                    "Production",
                    "Production_ID",
                    selected_id
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# STOCK CRUD
# =========================================================

def stock_control():

    page_header(
        "Stock Control",
        "Manage opening stock, production, dispatch and closing inventory."
    )

    df = stock.copy()

    st.subheader(
        f"Stock Records: {len(df)}"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        [
            "➕ Add Stock",
            "✏️ Edit Stock",
            "🗑️ Delete Stock"
        ]
    )

    item_ids = []

    if not items.empty and "Item_ID" in items.columns:

        item_ids = (
            items["Item_ID"]
            .dropna()
            .astype(str)
            .tolist()
        )

    production_ids = []

    if (
        not production.empty
        and "Production_ID"
        in production.columns
    ):

        production_ids = (
            production["Production_ID"]
            .dropna()
            .astype(str)
            .tolist()
        )

    # =====================================================
    # ADD
    # =====================================================

    with tab1:

        with st.form("add_stock_form"):

            c1, c2 = st.columns(2)

            with c1:

                stock_id = st.text_input(
                    "Stock ID *",
                    placeholder="STK-001"
                )

                item_id = st.selectbox(
                    "Item ID",
                    item_ids if item_ids else [""]
                )

                production_id = st.selectbox(
                    "Production ID",
                    production_ids
                    if production_ids
                    else [""]
                )

                batch_no = st.text_input(
                    "Batch No."
                )

                stock_date = st.date_input(
                    "Stock Date",
                    value=date.today()
                )

            with c2:

                opening = st.number_input(
                    "Opening Stock (m)",
                    min_value=0.0,
                    step=1.0
                )

                produced = st.number_input(
                    "Produced Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                dispatched = st.number_input(
                    "Dispatched Quantity (m)",
                    min_value=0.0,
                    step=1.0
                )

                closing = (
                    opening
                    + produced
                    - dispatched
                )

                st.metric(
                    "Calculated Closing Stock",
                    f"{closing:,.2f} m"
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
                        "Stock ID is required."
                    )

                else:

                    data = {
                        "Stock_ID":
                            stock_id.strip(),

                        "Item_ID":
                            item_id,

                        "Production_ID":
                            production_id,

                        "Batch_No":
                            batch_no.strip(),

                        "Stock_Date":
                            stock_date.isoformat(),

                        "Opening_Stock_m":
                            opening,

                        "Produced_Qty_m":
                            produced,

                        "Dispatched_Qty_m":
                            dispatched,

                        "Closing_Stock_m":
                            closing,

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

    with tab2:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            ids = (
                stock["Stock_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Stock Record",
                ids,
                key="edit_stock_id"
            )

            selected = stock[
                stock["Stock_ID"].astype(str)
                == selected_id
            ]

            if not selected.empty:

                row = selected.iloc[0]

                with st.form("edit_stock_form"):

                    c1, c2 = st.columns(2)

                    with c1:

                        st.text_input(
                            "Stock ID",
                            value=selected_id,
                            disabled=True
                        )

                        current_item = str(
                            row.get(
                                "Item_ID",
                                ""
                            )
                        )

                        edit_items = item_ids.copy()

                        if (
                            current_item
                            and current_item not in edit_items
                        ):

                            edit_items.insert(
                                0,
                                current_item
                            )

                        item_id = st.selectbox(
                            "Item ID",
                            edit_items
                            if edit_items
                            else [""],
                            index=(
                                edit_items.index(
                                    current_item
                                )
                                if current_item
                                in edit_items
                                else 0
                            ),
                            key="edit_stock_item"
                        )

                        current_production = str(
                            row.get(
                                "Production_ID",
                                ""
                            )
                        )

                        edit_production = production_ids.copy()

                        if (
                            current_production
                            and current_production
                            not in edit_production
                        ):

                            edit_production.insert(
                                0,
                                current_production
                            )

                        production_id = st.selectbox(
                            "Production ID",
                            edit_production
                            if edit_production
                            else [""],
                            index=(
                                edit_production.index(
                                    current_production
                                )
                                if current_production
                                in edit_production
                                else 0
                            ),
                            key="edit_stock_production"
                        )

                        batch_no = st.text_input(
                            "Batch No.",
                            value=str(
                                row.get(
                                    "Batch_No",
                                    ""
                                )
                            )
                        )

                        current_date = pd.to_datetime(
                            row.get(
                                "Stock_Date"
                            ),
                            errors="coerce"
                        )

                        if pd.isna(current_date):

                            current_date = pd.Timestamp.today()

                        stock_date = st.date_input(
                            "Stock Date",
                            value=current_date.date()
                        )

                    with c2:

                        opening = st.number_input(
                            "Opening Stock (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Opening_Stock_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        produced = st.number_input(
                            "Produced Quantity (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Produced_Qty_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        dispatched = st.number_input(
                            "Dispatched Quantity (m)",
                            min_value=0.0,
                            value=float(
                                row.get(
                                    "Dispatched_Qty_m",
                                    0
                                ) or 0
                            ),
                            step=1.0
                        )

                        closing = (
                            opening
                            + produced
                            - dispatched
                        )

                        st.metric(
                            "Calculated Closing Stock",
                            f"{closing:,.2f} m"
                        )

                        current_status = str(
                            row.get(
                                "Stock_Status",
                                "Available"
                            )
                        )

                        stock_options = [
                            "Available",
                            "Low Stock",
                            "Out of Stock",
                            "Reserved"
                        ]

                        if (
                            current_status
                            not in stock_options
                        ):

                            stock_options.insert(
                                0,
                                current_status
                            )

                        stock_status = st.selectbox(
                            "Stock Status",
                            stock_options,
                            index=stock_options.index(
                                current_status
                            )
                        )

                    update_btn = st.form_submit_button(
                        "Update Stock",
                        type="primary"
                    )

                    if update_btn:

                        data = {
                            "Item_ID":
                                item_id,

                            "Production_ID":
                                production_id,

                            "Batch_No":
                                batch_no.strip(),

                            "Stock_Date":
                                stock_date.isoformat(),

                            "Opening_Stock_m":
                                opening,

                            "Produced_Qty_m":
                                produced,

                            "Dispatched_Qty_m":
                                dispatched,

                            "Closing_Stock_m":
                                closing,

                            "Stock_Status":
                                stock_status
                        }

                        success, message = update_record(
                            "Stock Control",
                            "Stock_ID",
                            selected_id,
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

    with tab3:

        if stock.empty:

            st.info(
                "No stock records available."
            )

        else:

            ids = (
                stock["Stock_ID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            selected_id = st.selectbox(
                "Select Stock Record",
                ids,
                key="delete_stock_id"
            )

            confirm = st.checkbox(
                "I confirm that I want to delete this stock record."
            )

            if st.button(
                "Delete Stock",
                type="primary",
                disabled=not confirm
            ):

                success, message = delete_record(
                    "Stock Control",
                    "Stock_ID",
                    selected_id
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)


# =========================================================
# CUSTOM DASHBOARD
# =========================================================

def custom_dashboard():

    page_header(
        "Custom Dashboard Builder",
        "Create your own charts directly from ERP data."
    )

    dataset_name = st.selectbox(
        "Select Dataset",
        [
            "Items",
            "Production",
            "Stock Control"
        ]
    )

    data_map = {
        "Items": items.copy(),
        "Production": production.copy(),
        "Stock Control": stock.copy()
    }

    df = data_map[dataset_name]

    if df.empty:

        st.warning(
            f"No data available in {dataset_name}."
        )

        return

    st.subheader(
        f"{dataset_name} Data"
    )

    # -----------------------------
    # SEARCH
    # -----------------------------

    search = st.text_input(
        "Search Dataset"
    )

    filtered = df.copy()

    if search:

        mask = filtered.astype(str).apply(
            lambda row:
            row.str.lower()
            .str.contains(
                search.lower(),
                na=False
            ).any(),
            axis=1
        )

        filtered = filtered[mask]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader(
        "Build Your Chart"
    )

    numeric_columns = (
        filtered.select_dtypes(
            include="number"
        ).columns.tolist()
    )

    all_columns = filtered.columns.tolist()

    if not all_columns:

        st.warning(
            "No columns available."
        )

        return

    c1, c2, c3 = st.columns(3)

    with c1:

        chart_type = st.selectbox(
            "Chart Type",
            [
                "Bar",
                "Line",
                "Pie",
                "Scatter"
            ]
        )

    with c2:

        x_column = st.selectbox(
            "X Axis / Category",
            all_columns
        )

    with c3:

        if numeric_columns:

            default_y = numeric_columns[0]

            y_column = st.selectbox(
                "Y Axis / Value",
                numeric_columns,
                index=numeric_columns.index(
                    default_y
                )
            )

        else:

            y_column = None

    # -----------------------------
    # CREATE CHART
    # -----------------------------

    if y_column is None:

        st.info(
            "This dataset does not contain a numeric column for the Y-axis."
        )

        return

    chart_data = filtered[
        [x_column, y_column]
    ].copy()

    chart_data[y_column] = pd.to_numeric(
        chart_data[y_column],
        errors="coerce"
    )

    chart_data = chart_data.dropna(
        subset=[y_column]
    )

    if chart_data.empty:

        st.warning(
            "No valid numeric data available for this chart."
        )

        return

    try:

        if chart_type == "Bar":

            grouped = (
                chart_data
                .groupby(x_column, as_index=False)[
                    y_column
                ]
                .sum()
            )

            fig = px.bar(
                grouped,
                x=x_column,
                y=y_column,
                title=f"{y_column} by {x_column}"
            )

        elif chart_type == "Line":

            if pd.api.types.is_numeric_dtype(
                chart_data[x_column]
            ):

                line_data = chart_data.sort_values(
                    x_column
                )

            else:

                line_data = chart_data

            fig = px.line(
                line_data,
                x=x_column,
                y=y_column,
                markers=True,
                title=f"{y_column} Trend"
            )

        elif chart_type == "Pie":

            grouped = (
                chart_data
                .groupby(x_column, as_index=False)[
                    y_column
                ]
                .sum()
            )

            fig = px.pie(
                grouped,
                names=x_column,
                values=y_column,
                hole=0.45,
                title=f"{y_column} Distribution"
            )

        else:

            if not pd.api.types.is_numeric_dtype(
                chart_data[x_column]
            ):

                st.warning(
                    "Scatter chart requires a numeric X-axis."
                )

                return

            fig = px.scatter(
                chart_data,
                x=x_column,
                y=y_column,
                title=f"{y_column} vs {x_column}"
            )

        fig.update_layout(
            height=520,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception as e:

        st.error(
            f"Could not create chart: {str(e)}"
        )


# =========================================================
# ANALYTICS
# =========================================================

def analytics():

    page_header(
        "Analytics",
        "Production efficiency, quality and item-level performance."
    )

    production_df = production.copy()
    items_df = items.copy()

    if production_df.empty:

        st.info(
            "No production data available for analytics."
        )

        return

    # -----------------------------
    # OVERALL YIELD
    # -----------------------------

    good = (
        pd.to_numeric(
            production_df["Good_Qty_m"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    rejected = (
        pd.to_numeric(
            production_df["Rejected_Qty_m"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    total = good + rejected

    if total > 0:

        yield_rate = (
            good / total * 100
        )

    else:

        yield_rate = 0

    a, b, c = st.columns(3)

    with a:

        st.metric(
            "Good Production",
            f"{good:,.0f} m"
        )

    with b:

        st.metric(
            "Rejected Production",
            f"{rejected:,.0f} m"
        )

    with c:

        st.metric(
            "Overall Yield",
            f"{yield_rate:.2f}%"
        )

    st.markdown("---")

    # -----------------------------
    # LINE ANALYSIS
    # -----------------------------

    if "Production_Line" in production_df.columns:

        line = (
            production_df
            .groupby("Production_Line")
            .agg(
                Good=("Good_Qty_m", "sum"),
                Rejected=("Rejected_Qty_m", "sum"),
                Planned=("Planned_Qty_m", "sum")
            )
            .reset_index()
        )

        line["Total"] = (
            line["Good"]
            + line["Rejected"]
        )

        line["Yield_%"] = 0.0

        valid = line["Total"] > 0

        line.loc[valid, "Yield_%"] = (
            line.loc[valid, "Good"]
            /
            line.loc[valid, "Total"]
            * 100
        )

        st.subheader(
            "Production Line Performance"
        )

        fig = px.bar(
            line,
            x="Production_Line",
            y="Yield_%",
            text="Yield_%",
            title="Yield by Production Line"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        fig.update_layout(
            height=430,
            yaxis_title="Yield (%)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.dataframe(
            line,
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------
    # GOOD VS REJECTED
    # -----------------------------

    st.subheader(
        "Good vs Rejected Production"
    )

    quality_df = pd.DataFrame(
        {
            "Category": [
                "Good",
                "Rejected"
            ],
            "Quantity": [
                good,
                rejected
            ]
        }
    )

    fig = px.pie(
        quality_df,
        names="Category",
        values="Quantity",
        hole=0.55
    )

    fig.update_layout(
        height=400
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # -----------------------------
    # ITEM ANALYSIS
    # -----------------------------

    st.subheader(
        "Item-Level Production Analysis"
    )

    if "Item_ID" in production_df.columns:

        item_analysis = (
            production_df
            .groupby("Item_ID")
            .agg(
                Planned=("Planned_Qty_m", "sum"),
                Good=("Good_Qty_m", "sum"),
                Rejected=("Rejected_Qty_m", "sum")
            )
            .reset_index()
        )

        item_analysis["Total"] = (
            item_analysis["Good"]
            +
            item_analysis["Rejected"]
        )

        item_analysis["Yield_%"] = 0.0

        valid = item_analysis["Total"] > 0

        item_analysis.loc[valid, "Yield_%"] = (
            item_analysis.loc[valid, "Good"]
            /
            item_analysis.loc[valid, "Total"]
            * 100
        )

        if (
            not items_df.empty
            and "Item_ID" in items_df.columns
            and "Item_Code" in items_df.columns
        ):

            lookup = items_df[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ].drop_duplicates()

            item_analysis = item_analysis.merge(
                lookup,
                on="Item_ID",
                how="left"
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
        "Data Management",
        "ERP database status, table structure and data overview."
    )

    # -----------------------------
    # CONNECTION
    # -----------------------------

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Database",
            "Supabase"
            if supabase is not None
            else "CSV Mode"
        )

    with c2:

        st.metric(
            "Items",
            len(items)
        )

    with c3:

        st.metric(
            "Production",
            len(production)
        )

    st.markdown("---")

    # -----------------------------
    # TABLE INFORMATION
    # -----------------------------

    st.subheader(
        "ERP Database Tables"
    )

    table_info = pd.DataFrame(
        {
            "Module": [
                "Items",
                "Production",
                "Stock Control"
            ],

            "Supabase Table": [
                "Item_Registration",
                "Production",
                "Stock_Control"
            ],

            "Primary Key": [
                "Item_ID",
                "Production_ID",
                "Stock_ID"
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

    # -----------------------------
    # COLUMN STRUCTURE
    # -----------------------------

    st.subheader(
        "Expected Database Structure"
    )

    structure = pd.DataFrame(
        {
            "Table": [
                "Item_Registration",
                "Item_Registration",
                "Item_Registration",
                "Production",
                "Production",
                "Production",
                "Stock_Control",
                "Stock_Control",
                "Stock_Control"
            ],

            "Important Column": [
                "Item_ID",
                "Item_Code",
                "Material_Grade",
                "Production_ID",
                "Item_ID",
                "Good_Qty_m",
                "Stock_ID",
                "Item_ID",
                "Closing_Stock_m"
            ]
        }
    )

    st.dataframe(
        structure,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------
    # DOWNLOAD DATA
    # -----------------------------

    st.subheader(
        "Export Data"
    )

    d1, d2, d3 = st.columns(3)

    with d1:

        st.download_button(
            "Download Items CSV",
            data=items.to_csv(
                index=False
            ),
            file_name="Item_Registration.csv",
            mime="text/csv"
        )

    with d2:

        st.download_button(
            "Download Production CSV",
            data=production.to_csv(
                index=False
            ),
            file_name="Production.csv",
            mime="text/csv"
        )

    with d3:

        st.download_button(
            "Download Stock CSV",
            data=stock.to_csv(
                index=False
            ),
            file_name="Stock_Control.csv",
            mime="text/csv"
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

    stock_control()

elif page == "Custom Dashboard":

    custom_dashboard()

elif page == "Analytics":

    analytics()

elif page == "Data Management":

    data_management()
