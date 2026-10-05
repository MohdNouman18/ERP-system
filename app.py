import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date
from supabase import create_client, Client


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
# CONSTANTS
# =========================================================

ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
OPENING_TABLE = "Opening_Stock"
PRODUCTION_QTY_TABLE = "Production_Qty"
DISPATCH_TABLE = "Dispatch_Qty"
RETURN_TABLE = "Return_Qty"
CLOSING_TABLE = "Closing_Stock"

ITEM_COLUMNS = (
    "Item_ID", "Item_Code", "Material_Grade", "Application",
    "Nominal_Diameter_mm", "Wall_Thickness_mm", "SDR",
    "Color", "Standard_Length", "Unit"
)
PRODUCTION_COLUMNS = (
    "Production_ID", "Item_ID", "Production_Date", "Batch_No",
    "Production_Line", "Planned_Qty_m", "Good_Qty_m",
    "Rejected_Qty_m", "Production_Status"
)
OPENING_COLUMNS = ("Opening_Stock_ID", "Item_ID", "Qty")
PRODUCTION_QTY_COLUMNS = ("Production_ID", "Item_ID", "Qty")
DISPATCH_COLUMNS = ("Dispatch_ID", "Item_ID", "Qty")
RETURN_COLUMNS = ("Return_ID", "Item_ID", "Qty")
CLOSING_COLUMNS = ("Closing_Stock_ID", "Item_ID", "Qty")

CACHE_TTL = 300


# =========================================================
# CSS (cached read)
# =========================================================

@st.cache_data(show_spinner=False)
def _read_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


_css = _read_css()
if _css is None:
    st.warning("style.css not found. app.py and style.css must be in the same folder.")
else:
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)


# =========================================================
# SUPABASE CLIENT
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
# FAST DATAFRAME HELPERS
# =========================================================

def _normalize_columns(df: pd.DataFrame, expected: tuple) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    exp_set = set(expected)
    df_cols = set(df.columns)
    if exp_set.issubset(df_cols):
        return df
    lower_map = {c.lower(): c for c in df.columns}
    rename = {
        lower_map[c.lower()]: c
        for c in expected
        if c not in df_cols and c.lower() in lower_map
    }
    return df.rename(columns=rename) if rename else df


def make_df(data, columns: tuple) -> pd.DataFrame:
    if not data:
        return pd.DataFrame(columns=list(columns))
    df = pd.DataFrame(data)
    df = _normalize_columns(df, columns)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        df = df.reindex(columns=list(df.columns) + missing)
    return df[list(columns)]


def convert_numeric(df: pd.DataFrame, columns) -> pd.DataFrame:
    present = [c for c in columns if c in df.columns]
    if present:
        df[present] = df[present].apply(pd.to_numeric, errors="coerce").fillna(0)
    return df


# =========================================================
# PARALLEL DATA LOADING
# =========================================================

def _fetch_raw(table_name: str):
    try:
        resp = supabase.table(table_name).select("*").execute()
        return resp.data or [], None
    except Exception as e:
        return [], str(e)


def _process(cols: tuple, num_cols: tuple, records, err):
    if err:
        return pd.DataFrame(columns=list(cols)), err
    df = make_df(records, cols)
    df = convert_numeric(df, num_cols)
    return df, None


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_all_data():
    specs = [
        (ITEM_TABLE, ITEM_COLUMNS,
         ("Nominal_Diameter_mm", "Wall_Thickness_mm", "Standard_Length")),
        (PRODUCTION_TABLE, PRODUCTION_COLUMNS,
         ("Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m")),
        (OPENING_TABLE, OPENING_COLUMNS, ("Qty",)),
        (PRODUCTION_QTY_TABLE, PRODUCTION_QTY_COLUMNS, ("Qty",)),
        (DISPATCH_TABLE, DISPATCH_COLUMNS, ("Qty",)),
        (RETURN_TABLE, RETURN_COLUMNS, ("Qty",)),
        (CLOSING_TABLE, CLOSING_COLUMNS, ("Qty",)),
    ]

    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        raw_results = [f.result() for f in
                       [pool.submit(_fetch_raw, s[0]) for s in specs]]

    results = [
        _process(specs[i][1], specs[i][2], raw_results[i][0], raw_results[i][1])
        for i in range(len(specs))
    ]

    (items, items_err) = results[0]
    (production, production_err) = results[1]
    (opening, opening_err) = results[2]
    (prod_qty, prod_qty_err) = results[3]
    (dispatch, dispatch_err) = results[4]
    (return_qty, return_err) = results[5]
    (closing, closing_err) = results[6]

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
# DERIVED HELPERS
# =========================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_item_options(items_df: pd.DataFrame) -> list:
    if items_df.empty:
        return []
    return items_df["Item_ID"].astype(str).tolist()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def compute_totals(production, opening, prod_qty, dispatch, return_qty, closing) -> dict:
    good = float(production["Good_Qty_m"].sum()) if not production.empty else 0.0
    rejected = float(production["Rejected_Qty_m"].sum()) if not production.empty else 0.0
    planned = float(production["Planned_Qty_m"].sum()) if not production.empty else 0.0

    total_output = good + rejected
    yield_pct = (good / total_output * 100) if total_output > 0 else 0.0

    return {
        "planned": planned,
        "good": good,
        "rejected": rejected,
        "yield_pct": yield_pct,
        "opening": float(opening["Qty"].sum()) if not opening.empty else 0.0,
        "prod_qty": float(prod_qty["Qty"].sum()) if not prod_qty.empty else 0.0,
        "dispatched": float(dispatch["Qty"].sum()) if not dispatch.empty else 0.0,
        "returned": float(return_qty["Qty"].sum()) if not return_qty.empty else 0.0,
        "closing": float(closing["Qty"].sum()) if not closing.empty else 0.0,
    }


TOTALS = compute_totals(production, opening, prod_qty, dispatch, return_qty, closing)


def get_next_id(df: pd.DataFrame, column: str) -> str:
    if df.empty or column not in df.columns:
        return "1"
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return "1"
    return str(int(values.max()) + 1)


def refresh_all():
    load_all_data.clear()
    get_item_options.clear()
    compute_totals.clear()
    st.rerun()


def filter_df(df: pd.DataFrame, search: str) -> pd.DataFrame:
    if not search or df.empty:
        return df
    search_lower = search.lower()
    mask = df.astype(str).apply(
        lambda row: search_lower in " ".join(row.values).lower(),
        axis=1
    )
    return df[mask]


# =========================================================
# ERROR HINTS + EMPTY STATE
# =========================================================

def rls_hint(err: str, table: str, action: str = "insert"):
    e = err.lower()
    if "row-level security" in e or "rls" in e or "policy" in e:
        return (f"Supabase -> Authentication -> Policies -> {table} -> "
                f"New Policy -> allow {action.upper()} for anon and authenticated.")
    if "relation" in e and "does not exist" in e:
        return f"Table {table} does not exist in Supabase. Create it first."
    if "column" in e and "does not exist" in e:
        return f"Column name mismatch on {table}. Postgres columns are case-sensitive."
    if "permission denied" in e:
        return f"Permission denied on {table}. Check RLS policies."
    if "duplicate key" in e or "unique constraint" in e:
        return f"Duplicate ID in {table}. Refresh and try again."
    return None


def empty_state(msg: str, cta: str = None):
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
# GENERIC CRUD
# =========================================================

def crud_simple_table(table_name, df, id_col, label, items_df, load_error=None):
    if load_error:
        st.error(f"Failed to load {label}: {load_error}")
        hint = rls_hint(load_error, table_name, "select")
        if hint:
            st.info(hint)
    elif df.empty:
        st.info(f"{label} table is empty. Add the first record from the Add {label} tab below.")

    tab1, tab2, tab3 = st.tabs([f"View {label}", f"Add {label}", "Update / Delete"])

    with tab1:
        search = st.text_input(
            f"Search {label}", key=f"search_{table_name}",
            placeholder=f"{id_col}, Item ID..."
        )
        display = filter_df(df, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_id = get_next_id(df, id_col)
        st.info(f"Next {id_col}: {next_id}")

        if items_df.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            options = get_item_options(items_df)
            with st.form(f"add_{table_name}_form"):
                c1, c2 = st.columns(2)
                with c1:
                    selected_item = st.selectbox("Item ID", options,
                                                 key=f"add_item_{table_name}")
                with c2:
                    qty = st.number_input("Quantity", min_value=0.0, value=0.0,
                                          step=1.0, key=f"add_qty_{table_name}")
                submit = st.form_submit_button(f"Add {label}", type="primary")

            if submit:
                try:
                    supabase.table(table_name).insert(
                        {id_col: next_id, "Item_ID": selected_item, "Qty": qty}
                    ).execute()
                    st.success(f"{label} {next_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error(f"{label} add failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), table_name, "insert")
                    if hint:
                        st.info(hint)

    with tab3:
        if df.empty:
            st.info(f"No {label} records.")
            return

        selected_id = st.selectbox(
            f"Select {id_col}",
            df[id_col].astype(str).tolist(),
            key=f"sel_{table_name}"
        )
        selected = df.loc[df[id_col].astype(str) == selected_id].iloc[0]

        options = get_item_options(items_df)
        current_item = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
        default_idx = options.index(current_item) if current_item in options else 0

        with st.form(f"update_{table_name}_form"):
            c1, c2 = st.columns(2)
            with c1:
                if options:
                    edit_item = st.selectbox("Item ID", options, index=default_idx,
                                             key=f"edit_item_{table_name}")
                else:
                    edit_item = current_item
            with c2:
                edit_qty = st.number_input(
                    "Quantity", min_value=0.0,
                    value=float(selected["Qty"]) if pd.notna(selected["Qty"]) else 0.0,
                    step=1.0, key=f"edit_qty_{table_name}"
                )
            update = st.form_submit_button("Update", type="primary")

        if update:
            try:
                supabase.table(table_name).update(
                    {"Item_ID": edit_item, "Qty": edit_qty}
                ).eq(id_col, selected_id).execute()
                st.success(f"{label} updated.")
                refresh_all()
            except Exception as e:
                st.error("Update failed.")
                st.code(str(e))
                hint = rls_hint(str(e), table_name, "update")
                if hint:
                    st.info(hint)

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
                if hint:
                    st.info(hint)


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
# PAGE HEADER
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
    if opening.empty and not opening_err:
        empty.append("Opening Stock")
    if prod_qty.empty and not prod_qty_err:
        empty.append("Production Qty")
    if dispatch.empty and not dispatch_err:
        empty.append("Dispatch Qty")
    if return_qty.empty and not return_err:
        empty.append("Return Qty")
    if closing.empty and not closing_err:
        empty.append("Closing Stock")

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

    t = TOTALS
    registered_items = len(items)

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
                <div class="metric-value">{t['good']:,.0f} m</div>
                <div class="metric-caption">Accepted production</div>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Closing Stock</div>
                <div class="metric-value">{t['closing']:,.0f}</div>
                <div class="metric-caption">From Closing_Stock table</div>
            </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Production Yield</div>
                <div class="metric-value">{t['yield_pct']:.1f}%</div>
                <div class="metric-caption">Good output ratio</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Opening Stock", f"{t['opening']:,.0f}")
    c2.metric("Produced Qty", f"{t['prod_qty']:,.0f}")
    c3.metric("Dispatched Qty", f"{t['dispatched']:,.0f}")
    c4.metric("Return Qty", f"{t['returned']:,.0f}")
    c5.metric("Closing Stock", f"{t['closing']:,.0f}")

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.subheader("Production Status")
        if not production.empty:
            status_df = (
                production["Production_Status"]
                .fillna("Unknown")
                .value_counts()
                .rename_axis("Production_Status")
                .reset_index(name="Count")
            )
            fig = px.pie(status_df, names="Production_Status",
                         values="Count", hole=0.5)
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
    flow_total = (t["opening"] + t["prod_qty"] + t["dispatched"]
                  + t["returned"] + t["closing"])
    if flow_total > 0:
        flow_data = pd.DataFrame({
            "Stage": ["Opening", "Produced", "Dispatched", "Returned", "Closing"],
            "Qty": [t["opening"], t["prod_qty"], t["dispatched"],
                    t["returned"], t["closing"]]
        })
        fig = px.bar(flow_data, x="Stage", y="Qty", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state(
            "No stock records found yet.",
            "Open the Stock Control module to add Opening / Production / "
            "Dispatch / Return / Closing records."
        )


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.title("Item Registration")

    if items_err:
        st.error(f"Failed to load Item table: {items_err}")
        hint = rls_hint(items_err, ITEM_TABLE, "select")
        if hint:
            st.info(hint)

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Item", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Item",
                               placeholder="Item ID, Item Code, Grade...")
        display = filter_df(items, search)
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
                diameter = st.number_input("Nominal Diameter (mm)", min_value=1,
                                           value=1, step=1)
                wall = st.number_input("Wall Thickness (mm)", min_value=1,
                                       value=1, step=1)
                sdr = st.text_input("SDR")
            with c3:
                color = st.text_input("Color")
                standard_length = st.number_input("Standard Length", min_value=1,
                                                  value=1, step=1)
                unit = st.text_input("Unit", value="Meter")
            submit = st.form_submit_button("Add Item", type="primary")

        if submit:
            try:
                supabase.table(ITEM_TABLE).insert({
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
                }).execute()
                st.success(f"Item {next_item_id} added.")
                refresh_all()
            except Exception as e:
                st.error("Item add failed.")
                st.code(str(e))
                hint = rls_hint(str(e), ITEM_TABLE, "insert")
                if hint:
                    st.info(hint)

    with tab3:
        if items.empty:
            st.info("No items available.")
        else:
            selected_id = st.selectbox("Select Item ID",
                                       items["Item_ID"].astype(str).tolist())
            selected = items.loc[
                items["Item_ID"].astype(str) == selected_id
            ].iloc[0]

            with st.form("update_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_code = st.text_input(
                        "Item Code",
                        value=str(selected["Item_Code"]) if pd.notna(selected["Item_Code"]) else ""
                    )
                    new_grade = st.selectbox(
                        "Material Grade", ["PE-80", "PE-100"],
                        index=(1 if str(selected["Material_Grade"]) == "PE-100" else 0)
                    )
                    new_application = st.text_input(
                        "Application",
                        value=str(selected["Application"]) if pd.notna(selected["Application"]) else ""
                    )
                with c2:
                    new_diameter = st.number_input(
                        "Nominal Diameter (mm)", min_value=1,
                        value=max(1, int(selected["Nominal_Diameter_mm"])), step=1
                    )
                    new_wall = st.number_input(
                        "Wall Thickness (mm)", min_value=1,
                        value=max(1, int(selected["Wall_Thickness_mm"])), step=1
                    )
                    new_sdr = st.text_input(
                        "SDR",
                        value=str(selected["SDR"]) if pd.notna(selected["SDR"]) else ""
                    )
                with c3:
                    new_color = st.text_input(
                        "Color",
                        value=str(selected["Color"]) if pd.notna(selected["Color"]) else ""
                    )
                    new_length = st.number_input(
                        "Standard Length", min_value=1,
                        value=max(1, int(selected["Standard_Length"])), step=1
                    )
                    new_unit = st.text_input(
                        "Unit",
                        value=str(selected["Unit"]) if pd.notna(selected["Unit"]) else ""
                    )
                update = st.form_submit_button("Update Item", type="primary")

            if update:
                try:
                    supabase.table(ITEM_TABLE).update({
                        "Item_Code": new_code,
                        "Material_Grade": new_grade,
                        "Application": new_application,
                        "Nominal_Diameter_mm": new_diameter,
                        "Wall_Thickness_mm": new_wall,
                        "SDR": new_sdr,
                        "Color": new_color,
                        "Standard_Length": new_length,
                        "Unit": new_unit
                    }).eq("Item_ID", selected_id).execute()
                    st.success("Item updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), ITEM_TABLE, "update")
                    if hint:
                        st.info(hint)

            st.markdown("---")
            if st.button("Delete Item", type="secondary"):
                try:
                    supabase.table(ITEM_TABLE).delete().eq(
                        "Item_ID", selected_id
                    ).execute()
                    st.success("Item deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), ITEM_TABLE, "delete")
                    if hint:
                        st.info(hint)


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.title("Production")

    if production_err:
        st.error(f"Failed to load Production table: {production_err}")
        hint = rls_hint(production_err, PRODUCTION_TABLE, "select")
        if hint:
            st.info(hint)

    if production.empty and not production_err:
        st.info(
            "Production table is empty. Add the first record from the Add Production tab below."
        )

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Production", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Production",
                               placeholder="Production ID, Item ID, Batch...")
        display = filter_df(production, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_production_id = get_next_id(production, "Production_ID")
        st.info(f"Next Production ID: {next_production_id}")

        if items.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            options = get_item_options(items)
            with st.form("add_production_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    selected_item = st.selectbox("Item ID", options)
                    production_date = st.date_input("Production Date",
                                                    value=date.today())
                    batch_no = st.text_input("Batch No")
                with c2:
                    production_line = st.text_input("Production Line")
                    planned_qty = st.number_input("Planned Quantity (m)",
                                                  min_value=1, value=1, step=1)
                    good_qty = st.number_input("Good Quantity (m)",
                                               min_value=0, value=0, step=1)
                with c3:
                    rejected_qty = st.number_input("Rejected Quantity (m)",
                                                   min_value=0, value=0, step=1)
                    status = st.selectbox(
                        "Production Status",
                        ["Completed", "In Progress", "Pending", "Rejected"]
                    )
                submit = st.form_submit_button("Add Production", type="primary")

            if submit:
                try:
                    supabase.table(PRODUCTION_TABLE).insert({
                        "Production_ID": next_production_id,
                        "Item_ID": selected_item,
                        "Production_Date": str(production_date),
                        "Batch_No": batch_no.strip(),
                        "Production_Line": production_line.strip(),
                        "Planned_Qty_m": planned_qty,
                        "Good_Qty_m": good_qty,
                        "Rejected_Qty_m": rejected_qty,
                        "Production_Status": status
                    }).execute()
                    st.success(f"Production {next_production_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error("Production add failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "insert")
                    if hint:
                        st.info(hint)

    with tab3:
        if production.empty:
            st.info("No production records.")
        else:
            selected_id = st.selectbox(
                "Select Production ID",
                production["Production_ID"].astype(str).tolist()
            )
            selected = production.loc[
                production["Production_ID"].astype(str) == selected_id
            ].iloc[0]

            with st.form("update_production_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_batch = st.text_input(
                        "Batch No",
                        value=str(selected["Batch_No"]) if pd.notna(selected["Batch_No"]) else ""
                    )
                    edit_line = st.text_input(
                        "Production Line",
                        value=str(selected["Production_Line"]) if pd.notna(selected["Production_Line"]) else ""
                    )
                with c2:
                    edit_planned = st.number_input(
                        "Planned Quantity", min_value=1,
                        value=max(1, int(selected["Planned_Qty_m"])), step=1
                    )
                    edit_good = st.number_input(
                        "Good Quantity", min_value=0,
                        value=max(0, int(selected["Good_Qty_m"])), step=1
                    )
                with c3:
                    edit_rejected = st.number_input(
                        "Rejected Quantity", min_value=0,
                        value=max(0, int(selected["Rejected_Qty_m"])), step=1
                    )
                    status_options = ["Completed", "In Progress", "Pending", "Rejected"]
                    current_status = str(selected["Production_Status"])
                    edit_status = st.selectbox(
                        "Production Status", status_options,
                        index=(status_options.index(current_status)
                               if current_status in status_options else 0)
                    )
                update = st.form_submit_button("Update Production", type="primary")

            if update:
                try:
                    supabase.table(PRODUCTION_TABLE).update({
                        "Batch_No": edit_batch,
                        "Production_Line": edit_line,
                        "Planned_Qty_m": edit_planned,
                        "Good_Qty_m": edit_good,
                        "Rejected_Qty_m": edit_rejected,
                        "Production_Status": edit_status
                    }).eq("Production_ID", selected_id).execute()
                    st.success("Production updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "update")
                    if hint:
                        st.info(hint)

            if st.button("Delete Production"):
                try:
                    supabase.table(PRODUCTION_TABLE).delete().eq(
                        "Production_ID", selected_id
                    ).execute()
                    st.success("Production deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    hint = rls_hint(str(e), PRODUCTION_TABLE, "delete")
                    if hint:
                        st.info(hint)


# =========================================================
# STOCK CONTROL
# =========================================================

elif page == "Stock Control":

    st.title("Stock Control")
    st.caption("Manage stock across Opening, Production, Dispatch, Return and Closing.")

    data_banner()

    stock_tabs = st.tabs([
        "Opening Stock",
        "Production Qty",
        "Dispatch Qty",
        "Return Qty",
        "Closing Stock"
    ])

    with stock_tabs[0]:
        crud_simple_table(
            OPENING_TABLE, opening, "Opening_Stock_ID",
            "Opening Stock", items, opening_err
        )

    with stock_tabs[1]:
        crud_simple_table(
            PRODUCTION_QTY_TABLE, prod_qty, "Production_ID",
            "Production Qty", items, prod_qty_err
        )

    with stock_tabs[2]:
        crud_simple_table(
            DISPATCH_TABLE, dispatch, "Dispatch_ID",
            "Dispatch Qty",
