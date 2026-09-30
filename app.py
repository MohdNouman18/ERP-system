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
# CSS
# =========================================================

def load_css():

    css_path = os.path.join(
        os.path.dirname(__file__),
        "style.css"
    )

    if os.path.exists(css_path):

        with open(
            css_path,
            "r",
            encoding="utf-8"
        ) as f:

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
# SUPABASE
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
# HELPERS
# =========================================================

def ensure_columns(df, columns):

    if df is None:
        df = pd.DataFrame()

    df = df.copy()

    for col in columns:

        if col not in df.columns:
            df[col] = None

    return df


def clean_text_columns(df, columns):

    df = df.copy()

    for col in columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
            )

    return df


def clean_numeric_columns(df, columns):

    df = df.copy()

    for col in columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df


def get_id_columns():

    return {
        "Items": "Item_ID",
        "Production": "Production_ID",
        "Stock Control": "Stock_ID"
    }


# =========================================================
# FETCH DATA
# =========================================================

def fetch_table(module):

    table_name = TABLES[module]

    if supabase is not None:

        try:

            response = (
                supabase
                .table(table_name)
                .select("*")
                .execute()
            )

            if response.data:

                return pd.DataFrame(
                    response.data
                )

        except Exception as e:

            st.warning(
                f"Supabase error in {module}: {e}"
            )

    return pd.DataFrame()


# =========================================================
# CRUD
# =========================================================

def insert_record(module, data):

    if supabase is None:

        return False, "Supabase is not connected."

    try:

        supabase.table(
            TABLES[module]
        ).insert(data).execute()

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

        supabase.table(
            TABLES[module]
        ).update(data).eq(
            id_column,
            record_id
        ).execute()

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

        supabase.table(
            TABLES[module]
        ).delete().eq(
            id_column,
            record_id
        ).execute()

        return True, "Record deleted successfully."

    except Exception as e:

        return False, str(e)


# =========================================================
# LOAD ALL DATA
# =========================================================

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")


items = ensure_columns(
    items,
    ITEM_COLUMNS
)

production = ensure_columns(
    production,
    PRODUCTION_COLUMNS
)

stock = ensure_columns(
    stock,
    STOCK_COLUMNS
)


# IMPORTANT:
# Item_ID is TEXT because values are ITM-001 etc.

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


production = clean_numeric_columns(
    production,
    [
        "Planned_Qty_m",
        "Good_Qty_m",
        "Rejected_Qty_m"
    ]
)

stock = clean_numeric_columns(
    stock,
    [
        "Opening_Stock_m",
        "Produced_Qty_m",
        "Dispatched_Qty_m",
        "Closing_Stock_m"
    ]
)


# =========================================================
# SIDEBAR LOGO
# =========================================================

logo_path = os.path.join(
    os.path.dirname(__file__),
    "logo.png"
)


if os.path.exists(logo_path):

    try:

        with open(
            logo_path,
            "rb"
        ) as image_file:

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
# NAVIGATION
# =========================================================

page = st.sidebar.radio(
    "ERP MODULES",
    [
        "Executive Dashboard",
        "Item Registration",
        "Production",
        "Stock Control",
        "Custom Analytics",
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
# HEADER
# =========================================================

def page_header(
    kicker,
    title,
    description
):

    st.markdown(
        f'<div class="page-kicker">{kicker}</div>',
        unsafe_allow_html=True
    )

    st.title(title)

    st.caption(description)


# =========================================================
# METRIC CARD
# =========================================================

def metric_card(
    label,
    value,
    icon,
    caption
):

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
        "Overview of manufacturing, inventory and item master."
    )

    good = production[
        "Good_Qty_m"
    ].sum()

    rejected = production[
        "Rejected_Qty_m"
    ].sum()

    dispatched = stock[
        "Dispatched_Qty_m"
    ].sum()

    closing = stock[
        "Closing_Stock_m"
    ].sum()

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        metric_card(
            "REGISTERED ITEMS",
            f"{len(items):,}",
            "▣",
            "Product master"
        )

    with c2:

        metric_card(
            "GOOD PRODUCTION",
            f"{good:,.0f} m",
            "✓",
            "Accepted output"
        )

    with c3:

        metric_card(
            "REJECTED",
            f"{rejected:,.0f} m",
            "!",
            "Rejected output"
        )

    with c4:

        metric_card(
            "DISPATCHED",
            f"{dispatched:,.0f} m",
            "→",
            "Dispatched quantity"
        )

    with c5:

        metric_card(
            "CLOSING STOCK",
            f"{closing:,.0f} m",
            "□",
            "Current stock"
        )

    st.markdown("---")

    # =====================================================
    # PRODUCTION TREND
    # =====================================================

    c1, c2 = st.columns(2)

    with c1:

        st.subheader(
            "Production Trend"
        )

        if not production.empty:

            p = production.copy()

            p[
                "Production_Date"
            ] = pd.to_datetime(
                p["Production_Date"],
                errors="coerce"
            )

            p = p.dropna(
                subset=[
                    "Production_Date"
                ]
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
                    )
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "No production date available."
                )

        else:

            st.info(
                "No production data."
            )

    # =====================================================
    # PRODUCTION STATUS
    # =====================================================

    with c2:

        st.subheader(
            "Production Status"
        )

        if not production.empty:

            status = (
                production[
                    "Production_Status"
                ]
                .replace("", "Unknown")
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
                hole=0.5,
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

    # =====================================================
    # STOCK BY ITEM
    # =====================================================

    st.subheader(
        "Closing Stock by Item"
    )

    if not stock.empty:

        s = stock.copy()

        s = s.merge(
            items[
                [
                    "Item_ID",
                    "Item_Code"
                ]
            ],
            on="Item_ID",
            how="left"
        )

        s["Item_Display"] = (
            s["Item_Code"]
            .replace("", None)
            .fillna(s["Item_ID"])
        )

        summary = (
            s.groupby(
                "Item_Display",
                as_index=False
            )[
                "Closing_Stock_m"
            ]
            .sum()
            .sort_values(
                "Closing_Stock_m",
                ascending=False
            )
        )

        if not summary.empty:

            fig = px.bar(
                summary,
                x="Item_Display",
                y="Closing_Stock_m",
                text_auto=".0f",
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

    # =====================================================
    # RECENT PRODUCTION
    # =====================================================

    st.subheader(
        "Recent Production"
    )

    if not production.empty:

        st.dataframe(
            production.head(10),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# ITEM REGISTRATION CRUD
# =========================================================

def item_registration():

    page_header(
        "MASTER DATA",
        "Item Registration",
        "Create, view, edit and delete product specifications."
    )

    tabs = st.tabs(
        [
            "Item List",
            "Add Item",
            "Edit Item",
            "Delete Item"
        ]
    )

    # =====================================================
    # LIST
    # =====================================================

    with tabs[0]:

        search = st.text_input(
            "Search Item",
            placeholder="ITM-001, PE80, Water..."
        )

        display = items.copy()

        if search:

            mask = display.astype(
                str
            ).apply(
                lambda x:
                x.str.contains(
                    search,
                    case=False,
                    na=False
                )
            ).any(axis=1)

            display = display[mask]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # ADD
    # =====================================================

    with tabs[1]:

        with st.form(
            "add_item_form"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                item_id = st.text_input(
                    "Item ID *",
                    placeholder="ITM-008"
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
                    min_value=0.0,
                    step=0.1
                )

                thickness = st.number_input(
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

            submit = st.form_submit_button(
                "Create Item",
                type="primary"
            )

            if submit:

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
                        "Nominal_Diameter_mm": float(diameter),
                        "Wall_Thickness_mm": float(thickness),
                        "SDR": sdr,
                        "Color": color,
                        "Standard_Length": float(
                            standard_length
                        ),
                        "Unit": unit
                    }

                    ok, msg = insert_record(
                        "Items",
                        data
                    )

                    if ok:

                        st.success(msg)

                        st.cache_data.clear()

                        st.rerun()

                    else:

                        st.error(msg)

    # =====================================================
    # EDIT
    # =====================================================

    with tabs[2]:

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            selected = st.selectbox(
                "Select Item",
                items["Item_ID"].tolist(),
                key="edit_item"
            )

            row = items[
                items["Item_ID"] == selected
            ].iloc[0]

            with st.form(
                "edit_item_form"
            ):

                c1, c2 = st.columns(2)

                with c1:

                    item_code = st.text_input(
                        "Item Code",
                        value=str(
                            row["Item_Code"]
                        )
                    )

                    grade = st.text_input(
                        "Material Grade",
                        value=str(
                            row["Material_Grade"]
                        )
                    )

                    application = st.text_input(
                        "Application",
                        value=str(
                            row["Application"]
                        )
                    )

                    sdr = st.text_input(
                        "SDR",
                        value=str(
                            row["SDR"]
                        )
                    )

                    color = st.text_input(
                        "Color",
                        value=str(
                            row["Color"]
                        )
                    )

                with c2:

                    diameter = st.number_input(
                        "Nominal Diameter",
                        min_value=0.0,
                        value=float(
                            pd.to_numeric(
                                row[
                                    "Nominal_Diameter_mm"
                                ],
                                errors="coerce"
                            ) or 0
                        )
                    )

                    thickness = st.number_input(
                        "Wall Thickness",
                        min_value=0.0,
                        value=float(
                            pd.to_numeric(
                                row[
                                    "Wall_Thickness_mm"
                                ],
                                errors="coerce"
                            ) or 0
                        )
                    )

                    standard_length = st.number_input(
                        "Standard Length",
                        min_value=0.0,
                        value=float(
                            pd.to_numeric(
                                row[
                                    "Standard_Length"
                                ],
                                errors="coerce"
                            ) or 0
                        )
                    )

                    unit = st.text_input(
                        "Unit",
                        value=str(
                            row["Unit"]
                        )
                    )

                submit = st.form_submit_button(
                    "Update Item",
                    type="primary"
                )

                if submit:

                    data = {
                        "Item_Code": item_code,
                        "Material_Grade": grade,
                        "Application": application,
                        "Nominal_Diameter_mm": diameter,
                        "Wall_Thickness_mm": thickness,
                        "SDR": sdr,
                        "Color": color,
                        "Standard_Length": standard_length,
                        "Unit": unit
                    }

                    ok, msg = update_record(
                        "Items",
                        selected,
                        "Item_ID",
                        data
                    )

                    if ok:

                        st.success(msg)
                        st.rerun()

                    else:

                        st.error(msg)

    # =====================================================
    # DELETE
    # =====================================================

    with tabs[3]:

        if items.empty:

            st.info(
                "No items available."
            )

        else:

            selected = st.selectbox(
                "Select Item",
                items["Item_ID"].tolist(),
                key="delete_item"
            )

            st.warning(
                f"You are about to delete: {selected}"
            )

            if st.button(
                "Delete Item",
                type="primary"
            ):

                ok, msg = delete_record(
                    "Items",
                    selected,
                    "Item_ID"
                )

                if ok:

                    st.success(msg)
                    st.rerun()

                else:

                    st.error(msg)


# =========================================================
# PRODUCTION CRUD
# =========================================================

def production_page():

    page_header(
        "OPERATIONS",
        "Production",
        "Manage manufacturing production records."
    )

    tabs = st.tabs(
        [
            "Production List",
            "Create",
            "Edit",
            "Delete"
        ]
    )

    # =====================================================
    # LIST
    # =====================================================

    with tabs[0]:

        st.dataframe(
            production,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # CREATE
    # =====================================================

    with tabs[1]:

        with st.form(
            "create_production"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                production_id = st.text_input(
                    "Production ID *",
                    placeholder="PRD-001"
                )

                item_id = st.text_input(
                    "Item ID *",
                    placeholder="ITM-001"
                )

                production_date = st.date_input(
                    "Production Date",
                    date.today()
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
                    "Status",
                    [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Hold"
                    ]
                )

            submit = st.form_submit_button(
                "Create Production",
                type="primary"
            )

            if submit:

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

                ok, msg = insert_record(
                    "Production",
                    data
                )

                if ok:

                    st.success(msg)
                    st.rerun()

                else:

                    st.error(msg)

    # =====================================================
    # EDIT
    # =====================================================

    with tabs[2]:

        if production.empty:

            st.info(
                "No production records."
            )

        else:

            selected = st.selectbox(
                "Select Production ID",
                production[
                    "Production_ID"
                ].tolist(),
                key="edit_production"
            )

            row = production[
                production[
                    "Production_ID"
                ] == selected
            ].iloc[0]

            with st.form(
                "edit_production_form"
            ):

                item_id = st.text_input(
                    "Item ID",
                    value=str(
                        row["Item_ID"]
                    )
                )

                batch_no = st.text_input(
                    "Batch No",
                    value=str(
                        row["Batch_No"]
                    )
                )

                production_line = st.text_input(
                    "Production Line",
                    value=str(
                        row["Production_Line"]
                    )
                )

                production_date = st.date_input(
                    "Production Date",
                    value=pd.to_datetime(
                        row["Production_Date"],
                        errors="coerce"
                    ).date()
                    if pd.notna(
                        pd.to_datetime(
                            row["Production_Date"],
                            errors="coerce"
                        )
                    )
                    else date.today()
                )

                planned = st.number_input(
                    "Planned Quantity",
                    min_value=0.0,
                    value=float(
                        row["Planned_Qty_m"]
                    )
                )

                good = st.number_input(
                    "Good Quantity",
                    min_value=0.0,
                    value=float(
                        row["Good_Qty_m"]
                    )
                )

                rejected = st.number_input(
                    "Rejected Quantity",
                    min_value=0.0,
                    value=float(
                        row["Rejected_Qty_m"]
                    )
                )

                status = st.selectbox(
                    "Status",
                    [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Hold"
                    ],
                    index=[
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Hold"
                    ].index(
                        row["Production_Status"]
                    )
                    if row["Production_Status"]
                    in [
                        "Completed",
                        "In Progress",
                        "Pending",
                        "Hold"
                    ]
                    else 0
                )

                submit = st.form_submit_button(
                    "Update Production",
                    type="primary"
                )

                if submit:

                    data = {
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

                    ok, msg = update_record(
                        "Production",
                        selected,
                        "Production_ID",
                        data
                    )

                    if ok:

                        st.success(msg)
                        st.rerun()

                    else:

                        st.error(msg)

    # =====================================================
    # DELETE
    # =====================================================

    with tabs[3]:

        if production.empty:

            st.info(
                "No production records."
            )

        else:

            selected = st.selectbox(
                "Select Production",
                production[
                    "Production_ID"
                ].tolist(),
                key="delete_production"
            )

            if st.button(
                "Delete Production",
                type="primary"
            ):

                ok, msg = delete_record(
                    "Production",
                    selected,
                    "Production_ID"
                )

                if ok:

                    st.success(msg)
                    st.rerun()

                else:

                    st.error(msg)


# =========================================================
# STOCK CRUD
# =========================================================

def stock_control():

    page_header(
        "INVENTORY",
        "Stock Control",
        "Manage inventory, dispatches and closing stock."
    )

    tabs = st.tabs(
        [
            "Stock List",
            "Create",
            "Edit",
            "Delete"
        ]
    )

    # =====================================================
    # LIST
    # =====================================================

    with tabs[0]:

        st.dataframe(
            stock,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # CREATE
    # =====================================================

    with tabs[1]:

        with st.form(
            "create_stock"
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                stock_id = st.text_input(
                    "Stock ID *",
                    placeholder="STK-001"
                )

                item_id = st.text_input(
                    "Item ID *",
                    placeholder="ITM-001"
                )

                production_id = st.text_input(
                    "Production ID",
                    placeholder="PRD-001"
                )

                batch_no = st.text_input(
                    "Batch No"
                )

            with c2:

                stock_date = st.date_input(
                    "Stock Date",
                    date.today()
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

                closing = (
                    opening +
                    produced -
                    dispatched
                )

                st.metric(
                    "Closing Stock",
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

            submit = st.form_submit_button(
                "Create Stock Record",
                type="primary"
            )

            if submit:

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

                ok, msg = insert_record(
                    "Stock Control",
                    data
                )

                if ok:

                    st.success(msg)
                    st.rerun()

                else:

                    st.error(msg)

    # =====================================================
    # EDIT
    # =====================================================

    with tabs[2]:

        if stock.empty:

            st.info(
                "No stock records."
            )

        else:

            selected = st.selectbox(
                "Select Stock ID",
                stock[
                    "Stock_ID"
                ].tolist(),
                key="edit_stock"
            )

            row = stock[
                stock["Stock_ID"] == selected
            ].iloc[0]

            with st.form(
                "edit_stock_form"
            ):

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
                    )
                )

                batch_no = st.text_input(
                    "Batch No",
                    value=str(
                        row["Batch_No"]
                    )
                )

                stock_date = st.date_input(
                    "Stock Date",
                    value=pd.to_datetime(
                        row["Stock_Date"],
                        errors="coerce"
                    ).date()
                    if pd.notna(
                        pd.to_datetime(
                            row["Stock_Date"],
                            errors="coerce"
                        )
                    )
                    else date.today()
                )

                opening = st.number_input(
                    "Opening Stock",
                    min_value=0.0,
                    value=float(
                        row["Opening_Stock_m"]
                    )
                )

                produced = st.number_input(
                    "Produced Quantity",
                    min_value=0.0,
                    value=float(
                        row["Produced_Qty_m"]
                    )
                )

                dispatched = st.number_input(
                    "Dispatched Quantity",
                    min_value=0.0,
                    value=float(
                        row["Dispatched_Qty_m"]
                    )
                )

                closing = (
                    opening +
                    produced -
                    dispatched
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

                submit = st.form_submit_button(
                    "Update Stock",
                    type="primary"
                )

                if submit:

                    data = {
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

                    ok, msg = update_record(
                        "Stock Control",
                        selected,
                        "Stock_ID",
                        data
                    )

                    if ok:

                        st.success(msg)
                        st.rerun()

                    else:

                        st.error(msg)

    # =====================================================
    # DELETE
    # =====================================================

    with tabs[3]:

        if stock.empty:

            st.info(
                "No stock records."
            )

        else:

            selected = st.selectbox(
                "Select Stock",
                stock[
                    "Stock_ID"
                ].tolist(),
                key="delete_stock"
            )

            if st.button(
                "Delete Stock Record",
                type="primary"
            ):

                ok, msg = delete_record(
                    "Stock Control",
                    selected,
                    "Stock_ID"
                )

                if ok:

                    st.success(msg)
                    st.rerun()

                else:

                    st.error(msg)


# =========================================================
# CUSTOM ANALYTICS
# =========================================================

def custom_analytics():

    page_header(
        "BUSINESS INTELLIGENCE",
        "Custom Analytics Dashboard",
        "Build your own charts by selecting table, attributes and aggregation."
    )

    st.info(
        "Select the table and attributes below. "
        "The chart will be generated automatically."
    )

    # =====================================================
    # DATASET
    # =====================================================

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

    # =====================================================
    # PREPARE COLUMNS
    # =====================================================

    all_columns = df.columns.tolist()

    numeric_columns = (
        df.select_dtypes(
            include=["number"]
        )
        .columns
        .tolist()
    )

    categorical_columns = [
        c for c in all_columns
        if c not in numeric_columns
    ]

    # =====================================================
    # CHART SETTINGS
    # =====================================================

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:

        chart_type = st.selectbox(
            "2. Chart Type",
            [
                "Bar",
                "Line",
                "Pie",
                "Scatter"
            ]
        )

    with c2:

        if chart_type == "Scatter":

            st.write(
                "Scatter requires numeric X and Y."
            )

    # =====================================================
    # BAR / LINE / PIE
    # =====================================================

    if chart_type in [
        "Bar",
        "Line",
        "Pie"
    ]:

        c1, c2, c3 = st.columns(3)

        with c1:

            x_column = st.selectbox(
                "3. X / Category",
                all_columns
            )

        with c2:

            if numeric_columns:

                y_column = st.selectbox(
                    "4. Numeric Attribute",
                    numeric_columns
                )

            else:

                y_column = None

                st.warning(
                    "No numeric column available."
                )

        with c3:

            aggregation = st.selectbox(
                "5. Aggregation",
                [
                    "Sum",
                    "Average",
                    "Count",
                    "Minimum",
                    "Maximum"
                ]
            )

        if y_column:

            if aggregation == "Sum":

                grouped = (
                    df.groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .sum()
                )

            elif aggregation == "Average":

                grouped = (
                    df.groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .mean()
                )

            elif aggregation == "Count":

                grouped = (
                    df.groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .count()
                )

            elif aggregation == "Minimum":

                grouped = (
                    df.groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .min()
                )

            else:

                grouped = (
                    df.groupby(
                        x_column,
                        as_index=False
                    )[y_column]
                    .max()
                )

            grouped = grouped.sort_values(
                y_column,
                ascending=False
            )

            st.markdown("---")

            st.subheader(
                "Generated Chart"
            )

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
                height=500,
                margin=dict(
                    l=20,
                    r=20,
                    t=50,
                    b=20
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            with st.expander(
                "View Chart Data"
            ):

                st.dataframe(
                    grouped,
                    use_container_width=True,
                    hide_index=True
                )

    # =====================================================
    # SCATTER
    # =====================================================

    else:

        if len(numeric_columns) < 2:

            st.warning(
                "Scatter chart requires at least "
                "two numeric attributes."
            )

        else:

            c1, c2 = st.columns(2)

            with c1:

                x_column = st.selectbox(
                    "X Axis",
                    numeric_columns,
                    key="scatter_x"
                )

            with c2:

                y_column = st.selectbox(
                    "Y Axis",
                    numeric_columns,
                    index=1 if len(
                        numeric_columns
                    ) > 1 else 0,
                    key="scatter_y"
                )

            fig = px.scatter(
                df,
                x=x_column,
                y=y_column,
                template="plotly_white"
            )

            fig.update_layout(
                height=500,
                margin=dict(
                    l=20,
                    r=20,
                    t=50,
                    b=20
                )
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )


# =========================================================
# DATA MANAGEMENT
# =========================================================

def data_management():

    page_header(
        "SYSTEM",
        "Data Management",
        "ERP database status and table structure."
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        metric_card(
            "ITEM RECORDS",
            len(items),
            "▣",
            "Item master"
        )

    with c2:

        metric_card(
            "PRODUCTION RECORDS",
            len(production),
            "⚙",
            "Production"
        )

    with c3:

        metric_card(
            "STOCK RECORDS",
            len(stock),
            "□",
            "Inventory"
        )

    st.markdown("---")

    st.subheader(
        "Supabase Tables"
    )

    table_info = pd.DataFrame(
        {
            "Module": [
                "Items",
                "Production",
                "Stock Control"
            ],
            "Table": [
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

    st.subheader(
        "Database Connection"
    )

    if supabase is not None:

        st.success(
            "Supabase connection is active."
        )

    else:

        st.error(
            "Supabase connection is not active."
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

elif page == "Custom Analytics":

    custom_analytics()

elif page == "Data Management":

    data_management()
