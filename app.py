import os
import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import date
from concurrent.futures import ThreadPoolExecutor


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
# LOAD EXTERNAL CSS (cached to avoid disk IO on every rerun)
# =========================================================

@st.cache_data(show_spinner=False)
def _read_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def load_css():
    css = _read_css()
    if css is None:
        st.warning("style.css not found. app.py and style.css must be in the same folder.")
    else:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_css()


# =========================================================
# SUPABASE CONNECTION (cached singleton)
# =========================================================

@st.cache_resource(show_spinner=False)
def get_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)


try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    st.error("Supabase secrets missing.")
    st.info("Streamlit Cloud -> Settings -> Secrets: add SUPABASE_URL and SUPABASE_KEY.")
    st.stop()

try:
    supabase: Client = get_supabase_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Supabase connection failed.")
    st.code(str(e))
    st.stop()


# =========================================================
# TABLE + COLUMN DEFINITIONS
# =========================================================

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"

OPENING_TABLE = "Opening_Stock"
PRODUCTION_QTY_TABLE = "Production_Qty"
DISPATCH_TABLE = "Dispatch_Qty"
RETURN_TABLE = "Return_Qty"
CLOSING_TABLE = "Closing_Stock"

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

OPENING_COLUMNS = ["Opening_Stock_ID", "Item_ID", "Qty"]
PRODUCTION_QTY_COLUMNS = ["Production_ID", "Item_ID", "Qty"]
DISPATCH_COLUMNS = ["Dispatch_ID", "Item_ID", "Qty"]
RETURN_COLUMNS = ["Return_ID", "Item_ID", "Qty"]
CLOSING_COLUMNS = ["Closing_Stock_ID", "Item_ID", "Qty"]


# =========================================================
# HELPERS  (fast, vectorized)
# =========================================================

def _normalize_columns(df: pd.DataFrame, expected: list) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    lower_map = {c.lower(): c for c in df.columns}
    rename = {lower_map[c.lower()]: c for c in expected
              if c not in df.columns and c.lower() in lower_map}
    return df.rename(columns=rename) if rename else df


def make_df(data, columns):
    if not data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(data)
    df = _normalize_columns(df, columns)
    # Add missing columns in one shot
    missing = [c for c in columns if c not in df.columns]
    if missing:
        df = df.reindex(columns=list(df.columns) + missing)
    return df[columns]


def convert_numeric(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    present = [c for c in columns if c in df.columns]
    if present:
        df[present] = df[present].apply(pd.to_numeric, errors="coerce").fillna(0)
    return df


# =========================================================
# DATA LOADING — cached + parallel
# =========================================================

@st.cache_data(ttl=60, show_spinner=False)
def _load_one_table(table_name: str, columns: tuple, numeric_cols: tuple):
    """Load a single table with caching. Returns (records, error)."""
    try:
        response = supabase.table(table_name).select("*").execute()
        return response.data or [], None
    except Exception as e:
        return [], str(e)


def _build_df(table_name, columns, numeric_cols):
    records, err = _load_one_table(table_name, tuple(columns), tuple(numeric_cols))
    if err:
        return pd.DataFrame(columns=columns), err
    df = make_df(records, columns)
    df = convert_numeric(df, list(numeric_cols))
    return df, None


@st.cache_data(ttl=60, show_spinner=False)
def load_all_data():
    """
    Load all 7 tables in parallel using a thread pool.
    Cache TTL = 60s. Manual refresh clears the cache.
    Returns the same 14-tuple as before (backwards compatible).
    """
    tasks = [
        (ITEM_TABLE, tuple(ITEM_COLUMNS),
         ("Nominal_Diameter_mm", "Wall_Thickness_mm", "Standard_Length")),
        (PRODUCTION_TABLE, tuple(PRODUCTION_COLUMNS),
         ("Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m")),
        (OPENING_TABLE, tuple(OPENING_COLUMNS), ("Qty",)),
        (PRODUCTION_QTY_TABLE, tuple(PRODUCTION_QTY_COLUMNS), ("Qty",)),
        (DISPATCH_TABLE, tuple(DISPATCH_COLUMNS), ("Qty",)),
        (RETURN_TABLE, tuple(RETURN_COLUMNS), ("Qty",)),
        (CLOSING_TABLE, tuple(CLOSING_COLUMNS), ("Qty",)),
    ]

    results = [None] * len(tasks)

    def _run(idx, tname, cols, nums):
        try:
            resp = supabase.table(tname).select("*").execute()
            records = resp.data or []
            df = make_df(records, list(cols))
            df = convert_numeric(df, list(nums))
            results[idx] = (df, None)
        except Exception as e:
            results[idx] = (pd.DataFrame(columns=list(cols)), str(e))

    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = [
            pool.submit(_run, i, t, c, n)
            for i, (t, c, n) in enumerate(tasks)
        ]
        for f in futures:
            f.result()  # propagate exceptions (already handled)

    # Unpack: each is (df, err)
    (items, items_err)                 = results[0]
    (production, production_err)       = results[1]
    (opening, opening_err)             = results[2]
    (prod_qty, prod_qty_err)           = results[3]
    (dispatch, dispatch_err)           = results[4]
    (return_qty, return_err)           = results[5]
    (closing, closing_err)             = results[6]

    return (
        items, production,
        opening, prod_qty, dispatch, return_qty, closing,
        items_err, production_err,
        opening_err, prod_qty_err, dispatch_err, return_err, closing_err
    )


(
    items, production,
    opening, prod_qty, dispatch, return_qty, closing,
    items_err, production_err,
    opening_err, prod_qty_err, dispatch_err, return_err, closing_err
) = load_all_data()


# =========================================================
# ID + CACHE UTILITIES
# =========================================================

def get_next_id(df, column):
    if df.empty or column not in df.columns:
        return "1"
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return "1"
    return str(int(values.max()) + 1)


def refresh_all():
    """Clear only the cached data (keep CSS + client cached)."""
    load_all_data.clear()
    st.rerun()


# =========================================================
# ERROR HINTS + EMPTY STATE
# =========================================================

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
# REUSABLE CRUD BLOCK
# =========================================================

def crud_simple_table(table_name, df, id_col, label, items_df, load_error=None):
    if load_error:
        st.error(f"Failed to load {label}: {load_error}")
        hint = rls_hint(load_error, table_name, "select")
        if hint: st.info(hint)

    if len(df) == 0 and not load_error:
        st.info(f"{label} table is empty. Add the first record from the Add {label} tab below.")

    tab1, tab2, tab3 = st.tabs([f"View {label}", f"Add {label}", "Update / Delete"])

    with tab1:
        search = st.text_input(f"Search {label}", key=f"search_{table_name}",
                               placeholder=f"{id_col}, Item ID...")
        display = df
        if search and not display.empty:
            mask = display.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
            )
            display = display[mask]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_id = get_next_id(df, id_col)
        st.info(f"Next {id_col}: {next_id}")

        if items_df.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            with st.form(f"add_{table_name}_form"):
                c1, c2 = st.columns(2)
                with c1:
                    item_options = items_df["Item_ID"].astype(str).tolist()
                    selected_item = st.selectbox("Item ID", item_options, key=f"add_item_{table_name}")
                with c2:
                    qty = st.number_input("Quantity", min_value=0.0, value=0.0, step=1.0,
                                          key=f"add_qty_{table_name}")
                submit = st.form_submit_button(f"Add {label}", type="primary")

            if submit:
                payload = {id_col: next_id, "Item_ID": selected_item, "Qty": qty}
                try:
                    supabase.table(table_name).insert(payload).execute()
                    st.success(f"{label} {next_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error(f"{label} add failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), table_name, "insert")
                    if hint: st.info(hint)

    with tab3:
        if df.empty:
            st.info(f"No {label} records.")
        else:
            selected_id = st.selectbox(
                f"Select {id_col}",
                df[id_col].astype(str).tolist(),
                key=f"sel_{table_name}"
            )
            selected = df[df[id_col].astype(str) == selected_id].iloc[0]

            with st.form(f"update_{table_name}_form"):
                c1, c2 = st.columns(2)
                with c1:
                    if not items_df.empty:
                        item_options = items_df["Item_ID"].astype(str).tolist()
                        current_item = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
                        default_idx = item_options.index(current_item) if current_item in item_options else 0
                        edit_item = st.selectbox("Item ID", item_options, index=default_idx,
                                                 key=f"edit_item_{table_name}")
                    else:
                        edit_item = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
                with c2:
                    edit_qty = st.number_input(
                        "Quantity", min_value=0.0,
                        value=float(selected["Qty"]) if pd.notna(selected["Qty"]) else 0.0,
                        step=1.0, key=f"edit_qty_{table_name}"
                    )
                update = st.form_submit_button("Update", type="primary")

            if update:
                payload = {"Item_ID": edit_item, "Qty": edit_qty}
                try:
                    supabase.table(table_name).update(payload).eq(id_col, selected_id).execute()
                    st.success(f"{label} updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), table_name, "update")
                    if hint: st.info(hint)

            st.markdown("---")
            if st.button(f"Delete {label}", type="secondary", key=f"del_{table_name}"):
                try:
                    supabase.table(table_name).delete().eq(id_col, selected_id).execute()
                    st.success(f"{label} deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), table_name, "delete")
                    if hint: st.info(hint)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

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
    empty = []
    if len(opening) == 0 and not opening_err: empty.append("Opening Stock")
    if len(prod_qty) == 0 and not prod_qty_err: empty.append("Production Qty")
    if len(dispatch) == 0 and not dispatch_err: empty.append("Dispatch Qty")
    if len(return_qty) == 0 and not return_err: empty.append("Return Qty")
    if len(closing) == 0 and not closing_err: empty.append("Closing Stock")

    if empty:
        st.warning(
            f"The following stock table(s) have no records yet: **{', '.join(empty)}**.\n\n"
            f"Open the Stock Control module from the sidebar and use the tabs to add records."
        )


# =========================================================
# EXECUTIVE DASHBOARD
# =========================================================

if page == "Executive Dashboard":

    st.title("Executive Dashboard")
    st.caption("Real-time overview of manufacturing, production and inventory.")

    registered_items = len(items)
    planned_production = production["Planned_Qty_m"].sum() if not production.empty else 0
    good_production = production["Good_Qty_m"].sum() if not production.empty else 0
    rejected_production = production["Rejected_Qty_m"].sum() if not production.empty else 0

    total_opening = opening["Qty"].sum() if not opening.empty else 0
    total_produced_qty = prod_qty["Qty"].sum() if not prod_qty.empty else 0
    total_dispatched = dispatch["Qty"].sum() if not dispatch.empty else 0
    total_returned = return_qty["Qty"].sum() if not return_qty.empty else 0
    total_closing = closing["Qty"].sum() if not closing.empty else 0

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
                <div class="metric-label">Closing Stock</div>
                <div class="metric-value">{total_closing:,.0f}</div>
                <div class="metric-caption">From Closing_Stock table</div>
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

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Opening Stock", f"{total_opening:,.0f}")
    c2.metric("Produced Qty", f"{total_produced_qty:,.0f}")
    c3.metric("Dispatched Qty", f"{total_dispatched:,.0f}")
    c4.metric("Return Qty", f"{total_returned:,.0f}")
    c5.metric("Closing Stock", f"{total_closing:,.0f}")

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

    st.subheader("Stock Flow Overview")

    flow_data = pd.DataFrame({
        "Stage": ["Opening", "Produced", "Dispatched", "Returned", "Closing"],
        "Qty": [total_opening, total_produced_qty, total_dispatched, total_returned, total_closing]
    })

    if flow_data["Qty"].sum() > 0:
        fig = px.bar(flow_data, x="Stage", y="Qty", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No stock records found yet.",
                    "Open the Stock Control module to add Opening / Production / Dispatch / Return / Closing records.")


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
        display = items
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
            "Production table is empty. Add the first record from the Add Production tab below."
        )

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Production", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Production", placeholder="Production ID, Item ID, Batch...")
        display = production
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


# =================================
