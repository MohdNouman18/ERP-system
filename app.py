import os
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
    page_icon="logo.png" if os.path.exists("logo.png") else None,
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
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css not found. app.py and style.css must be in the same folder.")


load_css()


# =========================================================
# SUPABASE CONNECTION
# =========================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("Supabase secrets missing.")
    st.info("Streamlit Cloud -> Settings -> Secrets: add SUPABASE_URL and SUPABASE_KEY.")
    st.stop()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Supabase connection failed.")
    st.code(str(e))
    st.stop()


# =========================================================
# TABLE + COLUMN DEFINITIONS
# =========================================================

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
STOCK_TABLE = "Stock_Control"

ITEM_COLUMNS = [
    "Item_ID", "Item_Code", "Material_Grade", "Application",
    "Nominal_Diameter_mm", "Wall_Thickness_mm", "SDR",
    "Color", "Standard_Length", "Unit"
]

PRODUCTION_COLUMNS = [
    "Production_ID", "Item_ID", "Production_Date", "Batch_No",
    "Production_Line", "Planned_Qty_m", "Good_Qty_m",
    "Rejected_Qty_m", "Production_Status"
]

STOCK_COLUMNS = [
    "Stock_ID", "Item_ID", "Production_ID", "Batch_No",
    "Stock_Date", "Opening_Stock_m", "Produced_Qty_m",
    "Dispatched_Qty_m", "Closing_Stock_m", "Stock_Status"
]


# =========================================================
# HELPERS
# =========================================================

def normalize_columns(df, expected):
    if df is None or df.empty:
        return df
    lower_map = {c.lower(): c for c in df.columns}
    rename = {}
    for col in expected:
        if col not in df.columns and col.lower() in lower_map:
            rename[lower_map[col.lower()]] = col
    return df.rename(columns=rename) if rename else df


def make_df(data, columns):
    if not data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(data)
    df = normalize_columns(df, columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[columns]


def convert_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_table(table_name, columns, numeric_cols):
    try:
        response = supabase.table(table_name).select("*").execute()
        df = make_df(response.data or [], columns)
        df = convert_numeric(df, numeric_cols)
        return df, None
    except Exception as e:
        return pd.DataFrame(columns=columns), str(e)


@st.cache_data(ttl=5, show_spinner=False)
def load_all_data():
    items, items_err = load_table(
        ITEM_TABLE, ITEM_COLUMNS,
        ["Nominal_Diameter_mm", "Wall_Thickness_mm", "Standard_Length"]
    )
    production, prod_err = load_table(
        PRODUCTION_TABLE, PRODUCTION_COLUMNS,
        ["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"]
    )
    stock, stock_err = load_table(
        STOCK_TABLE, STOCK_COLUMNS,
        ["Opening_Stock_m", "Produced_Qty_m",
         "Dispatched_Qty_m", "Closing_Stock_m"]
    )
    return items, production, stock, items_err, prod_err, stock_err


items, production, stock, items_err, production_err, stock_err = load_all_data()


def get_next_id(df, column):
    if df.empty or column not in df.columns:
        return "1"
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return "1"
    return str(int(values.max()) + 1)


def refresh_all():
    st.cache_data.clear()
    st.rerun()


def rls_hint(err, table, action="insert"):
    err_low = err.lower()
    if "row-level security" in err_low or "rls" in err_low or "policy" in err_low:
        return (
            f"Supabase -> Authentication -> Policies -> {table} -> "
            f"New Policy -> allow {action.upper()} for anon and authenticated."
        )
    if "does not exist" in err_low and "relation" in err_low:
        return f"Table {table} does not exist in Supabase. Create it first."
    if "column" in err_low and "does not exist" in err_low:
        return f"Column name mismatch on {table}. Postgres columns are case-sensitive."
    if "permission denied" in err_low:
        return f"Permission denied on {table}. Check RLS policies."
    if "duplicate key" in err_low or "unique constraint" in err_low:
        return f"Duplicate ID in {table}. Refresh and try again."
    return None


def empty_state(msg, cta=None):
    st.markdown(
        f"""
        <div style="padding: 28px; border-radius: 12px;
                    background: rgba(255,193,7,0.08);
                    border: 1px solid rgba(255,193,7,0.35);
                    color: #f5c542; text-align: center; margin: 12px 0;">
            <div style="font-size: 15px; font-weight: 600;">{msg}</div>
            {f'<div style="margin-top:8px; font-size:13px; opacity:0.85;">{cta}</div>' if cta else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    # -------- BRAND + LOGO --------
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", use_container_width=True)

    st.markdown(
        """
        <div style="text-align: center; padding: 4px 0 12px 0;">
            <div style="font-size: 15px; font-weight: 700; letter-spacing: 0.5px;">
                Flex Head Industries
            </div>
            <div style="font-size: 10px; letter-spacing: 2px; opacity: 0.6; margin-top: 2px;">
                ERP MANAGEMENT SYSTEM
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
            "Custom Charts",
            "Data Management"
        ]
    )

    st.markdown("---")

    if st.button("Refresh Data", use_container_width=True):
        refresh_all()


# =========================================================
# TOP HEADER
# =========================================================

st.markdown(
    "<div class='page-kicker'>FLEX HEAD INDUSTRIES PVT LTD</div>",
    unsafe_allow_html=True
)


# =========================================================
# DATA BANNER
# =========================================================

def data_banner():
    no_prod = len(production) == 0 and not production_err
    no_stock = len(stock) == 0 and not stock_err

    if no_prod or no_stock:
        missing = []
        if no_prod:
            missing.append("Production")
        if no_stock:
            missing.append("Stock")
        st.warning(
            f"{' and '.join(missing)} table(s) have no records yet, "
            f"so the charts, dashboard and analytics below appear empty.\n\n"
            f"Solution: open the Production or Stock Control module from the sidebar "
            f"to add records, or use Data Management -> Demo Data (for testing)."
        )


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

if page == "Executive Dashboard":

    st.title("Executive Dashboard")
    st.caption("Real-time overview of manufacturing, production and inventory.")

    data_banner()

    registered_items = len(items)
    planned_production = production["Planned_Qty_m"].sum() if not production.empty else 0
    good_production = production["Good_Qty_m"].sum() if not production.empty else 0
    rejected_production = production["Rejected_Qty_m"].sum() if not production.empty else 0
    dispatched = stock["Dispatched_Qty_m"].sum() if not stock.empty else 0
    current_stock = stock["Closing_Stock_m"].sum() if not stock.empty else 0

    total_output = good_production + rejected_production
    yield_percentage = (good_production / total_output * 100) if total_output > 0 else 0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Registered Items</div>
                <div class="metric-value">{registered_items:,}</div>
                <div class="metric-caption">Total product items</div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Good Production</div>
                <div class="metric-value">{good_production:,.0f} m</div>
                <div class="metric-caption">Accepted production</div>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Current Stock</div>
                <div class="metric-value">{current_stock:,.0f} m</div>
                <div class="metric-caption">Available inventory</div>
            </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Production Yield</div>
                <div class="metric-value">{yield_percentage:.1f}%</div>
                <div class="metric-caption">Good output ratio</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Planned Production", f"{planned_production:,.0f} m")
    c2.metric("Rejected Production", f"{rejected_production:,.0f} m")
    c3.metric("Dispatched", f"{dispatched:,.0f} m")

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.subheader("Production Status")
        if not production.empty:
            status_df = production["Production_Status"].fillna("Unknown").value_counts().reset_index()
            status_df.columns = ["Production_Status", "Count"]
            fig = px.pie(status_df, names="Production_Status", values="Count", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state("No production records found.",
                        "Open the Production module from the sidebar to add records.")

    with right:
        st.subheader("Production Overview")
        if not production.empty:
            chart_df = production[
                ["Production_ID", "Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"]
            ].head(20)
            fig = px.bar(
                chart_df, x="Production_ID",
                y=["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"],
                barmode="group"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            empty_state("No production records found.")

    st.subheader("Current Stock by Item")
    if not stock.empty:
        stock_chart = stock.groupby("Item_ID", as_index=False)["Closing_Stock_m"].sum()
        if not items.empty:
            lookup = items[["Item_ID", "Item_Code"]].drop_duplicates(subset=["Item_ID"])
            stock_chart = stock_chart.merge(lookup, on="Item_ID", how="left")
        else:
            stock_chart["Item_Code"] = ""
        stock_chart["Display_Item"] = stock_chart["Item_Code"].fillna("").astype(str)
        stock_chart.loc[stock_chart["Display_Item"] == "", "Display_Item"] = stock_chart["Item_ID"].astype(str)
        fig = px.bar(stock_chart, x="Display_Item", y="Closing_Stock_m", text_auto=True)
        fig.update_layout(xaxis_title="Item", yaxis_title="Closing Stock (m)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No stock records found.",
                    "Open the Stock Control module from the sidebar to add records.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.title("Item Registration")

    if items_err:
        st.error(f"Failed to load Item table: {items_err}")
        hint = rls_hint(items_err, ITEM_TABLE, "select")
        if hint: st.info(hint)

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Item", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Item", placeholder="Item ID, Item Code, Grade...")
        display = items.copy()
        if search and not display.empty:
            mask = display.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
            )
            display = display[mask]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_item_id = get_next_id(items, "Item_ID")
        st.info(f"Next Item ID: {next_item_id}")

        with st.form("add_item_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                item_code = st.text_input("Item Code")
                material_grade = st.selectbox("Material Grade", ["PE-80", "PE-100"])
                application = st.text_input("Application")
            with c2:
                diameter = st.number_input("Nominal Diameter (mm)", min_value=1, value=1, step=1)
                wall = st.number_input("Wall Thickness (mm)", min_value=1, value=1, step=1)
                sdr = st.text_input("SDR")
            with c3:
                color = st.text_input("Color")
                standard_length = st.number_input("Standard Length", min_value=1, value=1, step=1)
                unit = st.text_input("Unit", value="Meter")
            submit = st.form_submit_button("Add Item", type="primary")

        if submit:
            payload = {
                "Item_ID": next_item_id,
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
                supabase.table(ITEM_TABLE).insert(payload).execute()
                st.success(f"Item {next_item_id} added.")
                refresh_all()
            except Exception as e:
                st.error("Item add failed.")
                st.code(str(e))
                hint = rls_hint(str(e), ITEM_TABLE, "insert")
                if hint: st.info(hint)

    with tab3:
        if items.empty:
            st.info("No items available.")
        else:
            selected_id = st.selectbox("Select Item ID", items["Item_ID"].astype(str).tolist())
            selected = items[items["Item_ID"].astype(str) == selected_id].iloc[0]

            with st.form("update_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_code = st.text_input("Item Code", value=str(selected["Item_Code"]) if pd.notna(selected["Item_Code"]) else "")
                    new_grade = st.selectbox("Material Grade", ["PE-80", "PE-100"],
                                             index=(1 if str(selected["Material_Grade"]) == "PE-100" else 0))
                    new_application = st.text_input("Application", value=str(selected["Application"]) if pd.notna(selected["Application"]) else "")
                with c2:
                    new_diameter = st.number_input("Nominal Diameter (mm)", min_value=1,
                                                   value=max(1, int(selected["Nominal_Diameter_mm"])), step=1)
                    new_wall = st.number_input("Wall Thickness (mm)", min_value=1,
                                               value=max(1, int(selected["Wall_Thickness_mm"])), step=1)
                    new_sdr = st.text_input("SDR", value=str(selected["SDR"]) if pd.notna(selected["SDR"]) else "")
                with c3:
                    new_color = st.text_input("Color", value=str(selected["Color"]) if pd.notna(selected["Color"]) else "")
                    new_length = st.number_input("Standard Length", min_value=1,
                                                 value=max(1, int(selected["Standard_Length"])), step=1)
                    new_unit = st.text_input("Unit", value=str(selected["Unit"]) if pd.notna(selected["Unit"]) else "")
                update = st.form_submit_button("Update Item", type="primary")

            if update:
                payload = {
                    "Item_Code": new_code, "Material_Grade": new_grade,
                    "Application": new_application, "Nominal_Diameter_mm": new_diameter,
                    "Wall_Thickness_mm": new_wall, "SDR": new_sdr,
                    "Color": new_color, "Standard_Length": new_length, "Unit": new_unit
                }
                try:
                    supabase.table(ITEM_TABLE).update(payload).eq("Item_ID", selected_id).execute()
                    st.success("Item updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), ITEM_TABLE, "update")
                    if hint: st.info(hint)

            st.markdown("---")
            if st.button("Delete Item", type="secondary"):
                try:
                    supabase.table(ITEM_TABLE).delete().eq("Item_ID", selected_id).execute()
                    st.success("Item deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), ITEM_TABLE, "delete")
                    if hint: st.info(hint)


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.title("Production")

    if production_err:
        st.error(f"Failed to load Production table: {production_err}")
        hint = rls_hint(production_err, PRODUCTION_TABLE, "select")
        if hint: st.info(hint)

    if len(production) == 0 and not production_err:
        st.info(
            "Production table is empty. Add the first record from the Add Production tab below. "
            "If an error appears while adding, it is an RLS policy issue — see Data Management -> Diagnostics."
        )

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Production", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Production", placeholder="Production ID, Item ID, Batch...")
        display = production.copy()
        if search and not display.empty:
            mask = display.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
            )
            display = display[mask]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_production_id = get_next_id(production, "Production_ID")
        st.info(f"Next Production ID: {next_production_id}")

        if items.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            with st.form("add_production_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    item_options = items["Item_ID"].astype(str).tolist()
                    selected_item = st.selectbox("Item ID", item_options)
                    production_date = st.date_input("Production Date", value=date.today())
                    batch_no = st.text_input("Batch No")
                with c2:
                    production_line = st.text_input("Production Line")
                    planned_qty = st.number_input("Planned Quantity (m)", min_value=1, value=1, step=1)
                    good_qty = st.number_input("Good Quantity (m)", min_value=0, value=0, step=1)
                with c3:
                    rejected_qty = st.number_input("Rejected Quantity (m)", min_value=0, value=0, step=1)
                    status = st.selectbox("Production Status",
                                          ["Completed", "In Progress", "Pending", "Rejected"])
                submit = st.form_submit_button("Add Production", type="primary")

            if submit:
                payload = {
                    "Production_ID": next_production_id,
                    "Item_ID": selected_item,
                    "Production_Date": str(production_date),
                    "Batch_No": batch_no.strip(),
                    "Production_Line": production_line.strip(),
                    "Planned_Qty_m": planned_qty,
                    "Good_Qty_m": good_qty,
                    "Rejected_Qty_m": rejected_qty,
                    "Production_Status": status
                }
                try:
                    supabase.table(PRODUCTION_TABLE).insert(payload).execute()
                    st.success(f"Production {next_production_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error("Production add failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "insert")
                    if hint: st.info(hint)

    with tab3:
        if production.empty:
            st.info("No production records.")
        else:
            selected_id = st.selectbox("Select Production ID",
                                       production["Production_ID"].astype(str).tolist())
            selected = production[production["Production_ID"].astype(str) == selected_id].iloc[0]

            with st.form("update_production_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_batch = st.text_input("Batch No",
                                               value=str(selected["Batch_No"]) if pd.notna(selected["Batch_No"]) else "")
                    edit_line = st.text_input("Production Line",
                                              value=str(selected["Production_Line"]) if pd.notna(selected["Production_Line"]) else "")
                with c2:
                    edit_planned = st.number_input("Planned Quantity", min_value=1,
                                                   value=max(1, int(selected["Planned_Qty_m"])), step=1)
                    edit_good = st.number_input("Good Quantity", min_value=0,
                                                value=max(0, int(selected["Good_Qty_m"])), step=1)
                with c3:
                    edit_rejected = st.number_input("Rejected Quantity", min_value=0,
                                                    value=max(0, int(selected["Rejected_Qty_m"])), step=1)
                    status_options = ["Completed", "In Progress", "Pending", "Rejected"]
                    current_status = str(selected["Production_Status"])
                    edit_status = st.selectbox(
                        "Production Status", status_options,
                        index=(status_options.index(current_status) if current_status in status_options else 0)
                    )
                update = st.form_submit_button("Update Production", type="primary")

            if update:
                payload = {
                    "Batch_No": edit_batch, "Production_Line": edit_line,
                    "Planned_Qty_m": edit_planned, "Good_Qty_m": edit_good,
                    "Rejected_Qty_m": edit_rejected, "Production_Status": edit_status
                }
                try:
                    supabase.table(PRODUCTION_TABLE).update(payload).eq("Production_ID", selected_id).execute()
                    st.success("Production updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "update")
                    if hint: st.info(hint)

            if st.button("Delete Production"):
                try:
                    supabase.table(PRODUCTION_TABLE).delete().eq("Production_ID", selected_id).execute()
                    st.success("Production deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "delete")
                    if hint: st.info(hint)


# =========================================================
# STOCK CONTROL
# =========================================================

elif page == "Stock Control":

    st.title("Stock Control")

    if stock_err:
        st.error(f"Failed to load Stock table: {stock_err}")
        hint = rls_hint(stock_err, STOCK_TABLE, "select")
        if hint: st.info(hint)

    if len(stock) == 0 and not stock_err:
        st.info(
            "Stock table is empty. Add the first record from the Add Stock tab below. "
            "If an error appears while adding, it is an RLS policy issue — see Data Management -> Diagnostics."
        )

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Stock", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Stock", placeholder="Stock ID, Item ID, Production ID...")
        display = stock.copy()
        if search and not display.empty:
            mask = display.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
            )
            display = display[mask]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_stock_id = get_next_id(stock, "Stock_ID")
        st.info(f"Next Stock ID: {next_stock_id}")

        if items.empty:
            st.warning("Add an item in Item Registration first.")
        elif production.empty:
            st.warning("Add a production record first.")
        else:
            with st.form("add_stock_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    item_options = items["Item_ID"].astype(str).tolist()
                    selected_item = st.selectbox("Item ID", item_options)
                    production_options = production["Production_ID"].astype(str).tolist()
                    selected_production = st.selectbox("Production ID", production_options)
                    batch_no = st.text_input("Batch No")
                with c2:
                    stock_date = st.date_input("Stock Date", value=date.today())
                    opening_stock = st.number_input("Opening Stock (m)", min_value=0, value=0, step=1)
                    produced_qty = st.number_input("Produced Qty (m)", min_value=0, value=0, step=1)
                with c3:
                    dispatched_qty = st.number_input("Dispatched Qty (m)", min_value=0, value=0, step=1)
                    closing_stock = st.number_input("Closing Stock (m)", min_value=0, value=0, step=1)
                    stock_status = st.selectbox("Stock Status",
                                                ["Available", "Low Stock", "Out of Stock", "Reserved"])
                submit = st.form_submit_button("Add Stock", type="primary")

            if submit:
                payload = {
                    "Stock_ID": next_stock_id,
                    "Item_ID": selected_item,
                    "Production_ID": selected_production,
                    "Batch_No": batch_no.strip(),
                    "Stock_Date": str(stock_date),
                    "Opening_Stock_m": opening_stock,
                    "Produced_Qty_m": produced_qty,
                    "Dispatched_Qty_m": dispatched_qty,
                    "Closing_Stock_m": closing_stock,
                    "Stock_Status": stock_status
                }
                try:
                    supabase.table(STOCK_TABLE).insert(payload).execute()
                    st.success(f"Stock {next_stock_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error("Stock add failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), STOCK_TABLE, "insert")
                    if hint: st.info(hint)

    with tab3:
        if stock.empty:
            st.info("No stock records.")
        else:
            selected_id = st.selectbox("Select Stock ID",
                                       stock["Stock_ID"].astype(str).tolist())
            selected = stock[stock["Stock_ID"].astype(str) == selected_id].iloc[0]

            with st.form("update_stock_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_batch = st.text_input("Batch No",
                                               value=str(selected["Batch_No"]) if pd.notna(selected["Batch_No"]) else "")
                    edit_opening = st.number_input("Opening Stock", min_value=0,
                                                   value=max(0, int(selected["Opening_Stock_m"])), step=1)
                with c2:
                    edit_produced = st.number_input("Produced Qty", min_value=0,
                                                    value=max(0, int(selected["Produced_Qty_m"])), step=1)
                    edit_dispatched = st.number_input("Dispatched Qty", min_value=0,
                                                      value=max(0, int(selected["Dispatched_Qty_m"])), step=1)
                with c3:
                    edit_closing = st.number_input("Closing Stock", min_value=0,
                                                   value=max(0, int(selected["Closing_Stock_m"])), step=1)
                    status_options = ["Available", "Low Stock", "Out of Stock", "Reserved"]
                    current_status = str(selected["Stock_Status"])
                    edit_status = st.selectbox(
                        "Stock Status", status_options,
                        index=(status_options.index(current_status) if current_status in status_options else 0)
                    )
                update = st.form_submit_button("Update Stock", type="primary")

            if update:
                payload = {
                    "Batch_No": edit_batch, "Opening_Stock_m": edit_opening,
                    "Produced_Qty_m": edit_produced, "Dispatched_Qty_m": edit_dispatched,
                    "Closing_Stock_m": edit_closing, "Stock_Status": edit_status
                }
                try:
                    supabase.table(STOCK_TABLE).update(payload).eq("Stock_ID", selected_id).execute()
                    st.success("Stock updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), STOCK_TABLE, "update")
                    if hint: st.info(hint)

            if st.button("Delete Stock"):
                try:
                    supabase.table(STOCK_TABLE).delete().eq("Stock_ID", selected_id).execute()
                    st.success("Stock deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), STOCK_TABLE, "delete")
                    if hint: st.info(hint)


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":

    st.title("Analytics")
    st.caption("Production and inventory performance.")

    data_banner()

    st.subheader("Production Performance")
    if not production.empty:
        total_planned = production["Planned_Qty_m"].sum()
        total_good = production["Good_Qty_m"].sum()
        total_rejected = production["Rejected_Qty_m"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Planned", f"{total_planned:,.0f} m")
        c2.metric("Good", f"{total_good:,.0f} m")
        c3.metric("Rejected", f"{total_rejected:,.0f} m")
        analysis = pd.DataFrame({
            "Type": ["Good Production", "Rejected Production"],
            "Quantity": [total_good, total_rejected]
        })
        fig = px.bar(analysis, x="Type", y="Quantity", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No production data available.",
                    "Open the Production module from the sidebar to add records.")

    st.markdown("---")

    st.subheader("Inventory Analysis")
    if not stock.empty:
        stock_analysis = stock.groupby("Item_ID", as_index=False).agg(
            Opening_Stock=("Opening_Stock_m", "sum"),
            Produced=("Produced_Qty_m", "sum"),
            Dispatched=("Dispatched_Qty_m", "sum"),
            Closing_Stock=("Closing_Stock_m", "sum")
        )
        st.dataframe(stock_analysis, use_container_width=True, hide_index=True)
        fig = px.bar(stock_analysis, x="Item_ID",
                     y=["Opening_Stock", "Produced", "Dispatched", "Closing_Stock"],
                     barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No stock data available.",
                    "Open the Stock Control module from the sidebar to add records.")


# =========================================================
# CUSTOM CHARTS
# =========================================================

elif page == "Custom Charts":

    st.title("Custom Charts")
    st.caption("Build your own charts — choose data source, chart type, axes and aggregation.")

    st.markdown("### 1. Data Source")

    source_options = {
        "Production": production,
        "Stock Control": stock,
        "Item Registration": items,
    }

    source_name = st.selectbox(
        "Select a dataset",
        list(source_options.keys())
    )

    df = source_options[source_name].copy()

    if df.empty:
        empty_state(
            f"{source_name} has no records.",
            "Add records in that module first, then come back here."
        )
        st.stop()

    st.markdown("### 2. Filters (optional)")

    with st.expander("Apply filters", expanded=False):
        filter_cols = st.multiselect(
            "Filter by column",
            options=[c for c in df.columns if df[c].dtype == "object" or df[c].nunique() < 30],
            default=[]
        )

        filtered_df = df.copy()

        for col in filter_cols:
            unique_vals = df[col].dropna().astype(str).unique().tolist()
            if not unique_vals:
                continue
            picked = st.multiselect(f"Values for {col}", unique_vals,
                                    default=unique_vals, key=f"filter_{col}")
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(picked)]

    df = filtered_df

    if df.empty:
        st.warning("No data left after filters. Change the filters.")
        st.stop()

    st.markdown("### 3. Chart Configuration")

    numeric_cols = [c for c in df.columns
                    if pd.api.types.is_numeric_dtype(df[c])]
    all_cols = df.columns.tolist()

    chart_type = st.selectbox(
        "Chart Type",
        [
            "Bar Chart",
            "Grouped Bar Chart",
            "Stacked Bar Chart",
            "Line Chart",
            "Area Chart",
            "Pie Chart",
            "Donut Chart",
            "Scatter Plot",
            "Histogram",
            "Box Plot",
        ]
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        x_axis = st.selectbox("X-axis (category / group)", all_cols,
                              index=(all_cols.index("Item_ID") if "Item_ID" in all_cols else 0))

    with c2:
        y_axis = st.selectbox("Y-axis (numeric)",
                              numeric_cols if numeric_cols else ["(no numeric column)"])

    with c3:
        color_by = st.selectbox(
            "Color / Group by (optional)",
            ["(none)"] + all_cols,
            index=0
        )

    agg_choice = "None"
    if chart_type not in ["Histogram", "Scatter Plot", "Box Plot"]:
        agg_choice = st.selectbox(
            "Aggregation (when X has multiple rows)",
            ["sum", "mean", "count", "max", "min"],
            index=0
        )

    top_n = st.slider("Show top N categories (0 = all)", 0, 50, 0)

    sort_order = st.radio("Sort order", ["Descending", "Ascending", "None"], horizontal=True)

    st.markdown("### 4. Chart")

    plot_df = df.copy()

    try:
        if agg_choice != "None" and chart_type not in ["Histogram", "Scatter Plot", "Box Plot"]:
            group_cols = [x_axis]
            if color_by != "(none)" and color_by != x_axis:
                group_cols.append(color_by)

            if agg_choice == "count":
                plot_df = (
                    plot_df.groupby(group_cols)[y_axis]
                    .count().reset_index()
                    .rename(columns={y_axis: "count"})
                )
                y_plot = "count"
            else:
                plot_df = (
                    plot_df.groupby(group_cols)[y_axis]
                    .agg(agg_choice).reset_index()
                )
                y_plot = y_axis
        else:
            y_plot = y_axis

        if agg_choice != "None" and y_plot in plot_df.columns and sort_order != "None":
            plot_df = plot_df.sort_values(
                y_plot, ascending=(sort_order == "Ascending")
            )

        if top_n > 0 and y_plot in plot_df.columns:
            plot_df = plot_df.head(top_n)

        if chart_type == "Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot,
                         color=(color_by if color_by != "(none)" else None),
                         text_auto=True)

        elif chart_type == "Grouped Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot,
                         color=(color_by if color_by != "(none)" else None),
                         barmode="group")

        elif chart_type == "Stacked Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot,
                         color=(color_by if color_by != "(none)" else None),
                         barmode="stack")

        elif chart_type == "Line Chart":
            fig = px.line(plot_df, x=x_axis, y=y_plot,
                          color=(color_by if color_by != "(none)" else None),
                          markers=True)

        elif chart_type == "Area Chart":
            fig = px.area(plot_df, x=x_axis, y=y_plot,
                          color=(color_by if color_by != "(none)" else None))

        elif chart_type == "Pie Chart":
            fig = px.pie(plot_df, names=x_axis, values=y_plot)

        elif chart_type == "Donut Chart":
            fig = px.pie(plot_df, names=x_axis, values=y_plot, hole=0.5)

        elif chart_type == "Scatter Plot":
            fig = px.scatter(plot_df, x=x_axis, y=y_plot,
                             color=(color_by if color_by != "(none)" else None))

        elif chart_type == "Histogram":
            fig = px.histogram(plot_df, x=x_axis,
                               color=(color_by if color_by != "(none)" else None))

        elif chart_type == "Box Plot":
            fig = px.box(plot_df, x=x_axis, y=y_plot,
                         color=(color_by if color_by != "(none)" else None))
        else:
            fig = None

        if fig is not None:
            fig.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                height=520,
                legend_title_text=(color_by if color_by != "(none)" else "")
            )
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("View underlying chart data"):
            st.dataframe(plot_df, use_container_width=True, hide_index=True)
            st.caption(f"{len(plot_df)} row(s)")

        csv = plot_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download chart data as CSV",
            data=csv,
            file_name=f"custom_chart_{source_name.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error("Error while building the chart.")
        st.code(str(e))
        st.info("Try a different X / Y combination, or clear Color / Group by.")


# =========================================================
# DATA MANAGEMENT
# =========================================================

elif page == "Data Management":

    st.title("Data Management")
    st.caption("Live database records and diagnostics.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Item Records", len(items))
    c2.metric("Production Records", len(production))
    c3.metric("Stock Records", len(stock))

    st.markdown("---")

    st.subheader("Test Connection (Demo Data)")
    st.caption(
        "This button inserts one test production and one test stock record. "
        "If the insert succeeds, the RLS policies are correct and you can add records manually."
    )

    if items.empty:
        st.warning("Add at least one item in Item Registration first.")
    else:
        if st.button("Insert 1 Demo Production + 1 Demo Stock Record"):
            try:
                pid = get_next_id(production, "Production_ID")
                first_item_id = str(items["Item_ID"].iloc[0])
                today = date.today()

                prod_payload = {
                    "Production_ID": pid,
                    "Item_ID": first_item_id,
                    "Production_Date": str(today),
                    "Batch_No": f"DEMO-{pid}",
                    "Production_Line": "Line-1",
                    "Planned_Qty_m": 1000,
                    "Good_Qty_m": 950,
                    "Rejected_Qty_m": 50,
                    "Production_Status": "Completed"
                }
                supabase.table(PRODUCTION_TABLE).insert(prod_payload).execute()
                st.success(f"Demo Production {pid} inserted.")

                sid = get_next_id(stock, "Stock_ID")
                stock_payload = {
                    "Stock_ID": sid,
                    "Item_ID": first_item_id,
                    "Production_ID": pid,
                    "Batch_No": f"DEMO-{pid}",
                    "Stock_Date": str(today),
                    "Opening_Stock_m": 0,
                    "Produced_Qty_m": 950,
                    "Dispatched_Qty_m": 100,
                    "Closing_Stock_m": 850,
                    "Stock_Status": "Available"
                }
                supabase.table(STOCK_TABLE).insert(stock_payload).execute()
                st.success(f"Demo Stock {sid} inserted.")

                st.balloons()
                refresh_all()

            except Exception as e:
                st.error("Demo insert failed.")
                st.code(str(e))
                hint = rls_hint(str(e), "Production/Stock", "insert")
                if hint:
                    st.warning(hint)

    st.markdown("---")

    with st.expander("Table Diagnostics", expanded=False):
        diag = pd.DataFrame({
            "Table": [ITEM_TABLE, PRODUCTION_TABLE, STOCK_TABLE],
            "Rows Loaded": [len(items), len(production), len(stock)],
            "Status": [
                "Error" if items_err else "OK",
                "Error" if production_err else ("Empty" if len(production) == 0 else "OK"),
                "Error" if stock_err else ("Empty" if len(stock) == 0 else "OK"),
            ],
            "Error": [items_err or "-", production_err or "-", stock_err or "-"]
        })
        st.dataframe(diag, use_container_width=True, hide_index=True)

        if st.button("Force Reload All Data"):
            refresh_all()

    st.markdown("---")

    st.subheader("Item Registration")
    st.dataframe(items, use_container_width=True, hide_index=True)

    st.subheader("Production")
    st.dataframe(production, use_container_width=True, hide_index=True)

    st.subheader("Stock Control")
    st.dataframe(stock, use_container_width=True, hide_index=True)


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")
st.caption("Flex Head Industries Pvt Ltd | ERP Management System")
