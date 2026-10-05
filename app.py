import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date
from supabase import create_client, Client


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
ADJUSTMENT_TABLE = "Stock_Adjustment"

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
ADJUSTMENT_COLUMNS = (
    "Adjustment_ID", "Item_ID", "Adjustment_Date",
    "Qty", "Reason", "Remarks"
)

# ID prefixes per table
ID_PREFIX = {
    ITEM_TABLE:          ("Item_ID",          "ITM"),
    PRODUCTION_TABLE:    ("Production_ID",    "PRD"),
    OPENING_TABLE:       ("Opening_Stock_ID", "OPN"),
    PRODUCTION_QTY_TABLE:("Production_ID",    "PQT"),
    DISPATCH_TABLE:      ("Dispatch_ID",      "DSP"),
    RETURN_TABLE:        ("Return_ID",        "RET"),
    CLOSING_TABLE:       ("Closing_Stock_ID", "CLS"),
    ADJUSTMENT_TABLE:    ("Adjustment_ID",    "ADJ"),
}

CACHE_TTL = 300


# =========================================================
# CSS
# =========================================================

@st.cache_data(show_spinner=False)
def _read_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


_css = _read_css()
if _css:
    st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)
else:
    st.warning("style.css not found.")


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
    st.stop()

try:
    supabase: Client = get_supabase_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Supabase connection failed.")
    st.code(str(e))
    st.stop()


# =========================================================
# DATAFRAME HELPERS
# =========================================================

def _normalize_columns(df, expected):
    if df is None or df.empty:
        return df
    exp_set = set(expected)
    if exp_set.issubset(set(df.columns)):
        return df
    lower_map = {c.lower(): c for c in df.columns}
    rename = {lower_map[c.lower()]: c for c in expected
              if c not in df.columns and c.lower() in lower_map}
    return df.rename(columns=rename) if rename else df


def make_df(data, columns):
    if not data:
        return pd.DataFrame(columns=list(columns))
    df = pd.DataFrame(data)
    df = _normalize_columns(df, columns)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        df = df.reindex(columns=list(df.columns) + missing)
    return df[list(columns)]


def convert_numeric(df, columns):
    present = [c for c in columns if c in df.columns]
    if present:
        df[present] = df[present].apply(pd.to_numeric, errors="coerce").fillna(0)
    return df


# =========================================================
# DATA LOADING
# =========================================================

def _fetch_raw(table_name):
    try:
        resp = supabase.table(table_name).select("*").execute()
        return resp.data or [], None
    except Exception as e:
        return [], str(e)


def _process(cols, num_cols, records, err):
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
        (ADJUSTMENT_TABLE, ADJUSTMENT_COLUMNS, ("Qty",)),
    ]

    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futures = [pool.submit(_fetch_raw, s[0]) for s in specs]
        raw_results = [f.result() for f in futures]

    results = [
        _process(specs[i][1], specs[i][2], raw_results[i][0], raw_results[i][1])
        for i in range(len(specs))
    ]

    items, items_err = results[0]
    production, production_err = results[1]
    opening, opening_err = results[2]
    prod_qty, prod_qty_err = results[3]
    dispatch, dispatch_err = results[4]
    return_qty, return_err = results[5]
    closing, closing_err = results[6]
    adjustment, adjustment_err = results[7]

    return (
        items, production,
        opening, prod_qty, dispatch, return_qty, closing, adjustment,
        items_err, production_err,
        opening_err, prod_qty_err, dispatch_err, return_err,
        closing_err, adjustment_err
    )


(
    items, production,
    opening, prod_qty, dispatch, return_qty, closing, adjustment,
    items_err, production_err,
    opening_err, prod_qty_err, dispatch_err, return_err,
    closing_err, adjustment_err
) = load_all_data()


# =========================================================
# AUTO-ID GENERATION
# =========================================================

def get_next_id(df: pd.DataFrame, id_col: str, prefix: str) -> str:
    """Generate next ID like ITM-001, ITM-002 ...
    Works with legacy numeric IDs too."""
    if df.empty or id_col not in df.columns:
        return f"{prefix}-001"

    nums = []
    for v in df[id_col].dropna().astype(str):
        # Extract numeric part
        if prefix and v.startswith(f"{prefix}-"):
            tail = v[len(prefix) + 1:]
        else:
            tail = v
        try:
            nums.append(int(float(tail)))
        except (ValueError, TypeError):
            continue

    if not nums:
        return f"{prefix}-001"

    return f"{prefix}-{max(nums) + 1:03d}"


def next_id_for(table_name: str, df: pd.DataFrame) -> str:
    id_col, prefix = ID_PREFIX[table_name]
    return get_next_id(df, id_col, prefix)


# =========================================================
# AUTO-CLOSING STOCK COMPUTATION
# =========================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def compute_stock_ledger(
    items_df, opening_df, prod_qty_df,
    dispatch_df, return_df, adjustment_df
) -> pd.DataFrame:
    """
    Item-wise stock ledger.
    Formula: Closing = Opening + Produced - Dispatched + Returned + Adjusted
    """
    if items_df.empty:
        return pd.DataFrame(columns=[
            "Item_ID", "Item_Code", "Opening", "Produced",
            "Dispatched", "Returned", "Adjusted", "Computed_Closing"
        ])

    def _grp(df, col_name):
        if df is None or df.empty:
            return pd.DataFrame(columns=["Item_ID", col_name])
        return (df.groupby("Item_ID", as_index=False)["Qty"]
                  .sum()
                  .rename(columns={"Qty": col_name}))

    base = items_df[["Item_ID", "Item_Code"]].copy()

    for df, name in [
        (opening_df,   "Opening"),
        (prod_qty_df,  "Produced"),
        (dispatch_df,  "Dispatched"),
        (return_df,    "Returned"),
        (adjustment_df,"Adjusted"),
    ]:
        base = base.merge(_grp(df, name), on="Item_ID", how="left")

    base = base.fillna(0)
    base["Computed_Closing"] = (
        base["Opening"]
        + base["Produced"]
        - base["Dispatched"]
        + base["Returned"]
        + base["Adjusted"]
    )
    return base


STOCK_LEDGER = compute_stock_ledger(
    items, opening, prod_qty, dispatch, return_qty, adjustment
)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def compute_totals(production, opening, prod_qty, dispatch,
                   return_qty, adjustment, stock_ledger) -> dict:
    good = float(production["Good_Qty_m"].sum()) if not production.empty else 0.0
    rejected = float(production["Rejected_Qty_m"].sum()) if not production.empty else 0.0
    planned = float(production["Planned_Qty_m"].sum()) if not production.empty else 0.0

    total_output = good + rejected
    yield_pct = (good / total_output * 100) if total_output > 0 else 0.0

    closing_total = (float(stock_ledger["Computed_Closing"].sum())
                     if not stock_ledger.empty else 0.0)

    return {
        "planned": planned,
        "good": good,
        "rejected": rejected,
        "yield_pct": yield_pct,
        "opening": float(opening["Qty"].sum()) if not opening.empty else 0.0,
        "prod_qty": float(prod_qty["Qty"].sum()) if not prod_qty.empty else 0.0,
        "dispatched": float(dispatch["Qty"].sum()) if not dispatch.empty else 0.0,
        "returned": float(return_qty["Qty"].sum()) if not return_qty.empty else 0.0,
        "adjusted": float(adjustment["Qty"].sum()) if not adjustment.empty else 0.0,
        "closing": closing_total,
    }


TOTALS = compute_totals(
    production, opening, prod_qty, dispatch,
    return_qty, adjustment, STOCK_LEDGER
)


# =========================================================
# UI HELPERS
# =========================================================

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_item_options(items_df: pd.DataFrame) -> list:
    if items_df.empty:
        return []
    return items_df["Item_ID"].astype(str).tolist()


def refresh_all():
    load_all_data.clear()
    get_item_options.clear()
    compute_stock_ledger.clear()
    compute_totals.clear()
    st.rerun()


def filter_df(df, search):
    if not search or df.empty:
        return df
    s = search.lower()
    mask = df.astype(str).apply(
        lambda row: s in " ".join(row.values).lower(), axis=1
    )
    return df[mask]


def rls_hint(err, table, action="insert"):
    e = err.lower()
    if "row-level security" in e or "rls" in e or "policy" in e:
        return (f"Supabase -> Authentication -> Policies -> {table} -> "
                f"New Policy -> allow {action.upper()} for anon and authenticated.")
    if "relation" in e and "does not exist" in e:
        return f"Table {table} does not exist in Supabase."
    if "column" in e and "does not exist" in e:
        return f"Column name mismatch on {table}."
    if "permission denied" in e:
        return f"Permission denied on {table}."
    if "duplicate key" in e or "unique constraint" in e:
        return f"Duplicate ID in {table}."
    if "foreign key" in e or "violates foreign key" in e:
        return f"Foreign key violation — Item_ID {table} mein maujood nahi."
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


def data_banner():
    empty = []
    if opening.empty and not opening_err: empty.append("Opening Stock")
    if prod_qty.empty and not prod_qty_err: empty.append("Production Qty")
    if dispatch.empty and not dispatch_err: empty.append("Dispatch Qty")
    if return_qty.empty and not return_err: empty.append("Return Qty")
    if adjustment.empty and not adjustment_err: empty.append("Stock Adjustment")

    if empty:
        st.warning(
            f"The following table(s) have no records yet: **{', '.join(empty)}**.\n\n"
            f"Open the Stock Control or Stock Adjustment module to add records."
        )


# =========================================================
# GENERIC CRUD FOR SIMPLE STOCK TABLES
# =========================================================

def crud_simple_table(table_name, df, id_col, label, items_df, load_error=None):
    if load_error:
        st.error(f"Failed to load {label}: {load_error}")
        h = rls_hint(load_error, table_name, "select")
        if h: st.info(h)
    elif df.empty:
        st.info(f"{label} table is empty. Add the first record below.")

    tab1, tab2, tab3 = st.tabs([f"View {label}", f"Add {label}", "Update / Delete"])

    with tab1:
        search = st.text_input(f"Search {label}", key=f"s_{table_name}",
                               placeholder=f"{id_col}, Item ID...")
        display = filter_df(df, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_id = next_id_for(table_name, df)
        st.info(f"Next {id_col}: {next_id}")

        if items_df.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            options = get_item_options(items_df)
            with st.form(f"add_{table_name}_form"):
                c1, c2 = st.columns(2)
                with c1:
                    selected_item = st.selectbox("Item ID", options,
                                                 key=f"ai_{table_name}")
                with c2:
                    qty = st.number_input("Quantity", min_value=0.0, value=0.0,
                                          step=1.0, key=f"aq_{table_name}")
                submit = st.form_submit_button(f"Add {label}", type="primary")

            if submit:
                try:
                    supabase.table(table_name).insert({
                        id_col: next_id,
                        "Item_ID": selected_item,
                        "Qty": qty
                    }).execute()
                    st.success(f"{label} {next_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error(f"{label} add failed.")
                    st.code(str(e))
                    h = rls_hint(str(e), table_name, "insert")
                    if h: st.info(h)

    with tab3:
        if df.empty:
            st.info(f"No {label} records.")
            return

        selected_id = st.selectbox(f"Select {id_col}",
                                   df[id_col].astype(str).tolist(),
                                   key=f"sel_{table_name}")
        selected = df.loc[df[id_col].astype(str) == selected_id].iloc[0]

        options = get_item_options(items_df)
        current_item = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
        default_idx = options.index(current_item) if current_item in options else 0

        with st.form(f"upd_{table_name}_form"):
            c1, c2 = st.columns(2)
            with c1:
                if options:
                    edit_item = st.selectbox("Item ID", options,
                                             index=default_idx,
                                             key=f"ei_{table_name}")
                else:
                    edit_item = current_item
            with c2:
                edit_qty = st.number_input(
                    "Quantity", min_value=0.0,
                    value=float(selected["Qty"]) if pd.notna(selected["Qty"]) else 0.0,
                    step=1.0, key=f"eq_{table_name}"
                )
            update = st.form_submit_button("Update", type="primary")

        if update:
            try:
                supabase.table(table_name).update({
                    "Item_ID": edit_item, "Qty": edit_qty
                }).eq(id_col, selected_id).execute()
                st.success(f"{label} updated.")
                refresh_all()
            except Exception as e:
                st.error("Update failed.")
                st.code(str(e))
                h = rls_hint(str(e), table_name, "update")
                if h: st.info(h)

        st.markdown("---")
        if st.button(f"Delete {label}", type="secondary",
                     key=f"del_{table_name}"):
            try:
                supabase.table(table_name).delete().eq(id_col, selected_id).execute()
                st.success(f"{label} deleted.")
                refresh_all()
            except Exception as e:
                st.error("Delete failed.")
                st.code(str(e))
                h = rls_hint(str(e), table_name, "delete")
                if h: st.info(h)


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
            "Stock Adjustment",
            "Physical Check",
            "Analytics",
            "Custom Charts",
            "Data Management"
        ]
    )

    st.markdown("---")
    if st.button("Refresh Data", use_container_width=True):
        refresh_all()


st.markdown(
    "<div class='page-kicker'>FLEX HEAD INDUSTRIES PVT LTD</div>",
    unsafe_allow_html=True
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
                <div class="metric-label">Current Closing Stock</div>
                <div class="metric-value">{t['closing']:,.0f}</div>
                <div class="metric-caption">Auto-computed from ledger</div>
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
    c5.metric("Adjusted", f"{t['adjusted']:,.0f}")

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
            empty_state("No production records found.")

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
    flow_total = t["opening"] + t["prod_qty"] + t["dispatched"] + t["returned"]
    if flow_total > 0 or t["closing"] > 0:
        flow_data = pd.DataFrame({
            "Stage": ["Opening", "Produced", "Dispatched", "Returned", "Closing"],
            "Qty": [t["opening"], t["prod_qty"], t["dispatched"],
                    t["returned"], t["closing"]]
        })
        fig = px.bar(flow_data, x="Stage", y="Qty", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No stock records found yet.")

    st.subheader("Auto-Computed Stock Ledger")
    if not STOCK_LEDGER.empty:
        st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)
    else:
        empty_state("No ledger data available.")


# =========================================================
# ITEM REGISTRATION
# =========================================================

elif page == "Item Registration":

    st.title("Item Registration")

    if items_err:
        st.error(f"Failed to load Item table: {items_err}")
        h = rls_hint(items_err, ITEM_TABLE, "select")
        if h: st.info(h)

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Item", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Item",
                               placeholder="Item ID, Item Code, Grade...")
        display = filter_df(items, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_item_id = next_id_for(ITEM_TABLE, items)
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
                h = rls_hint(str(e), ITEM_TABLE, "insert")
                if h: st.info(h)

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
                    h = rls_hint(str(e), ITEM_TABLE, "update")
                    if h: st.info(h)

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
                    h = rls_hint(str(e), ITEM_TABLE, "delete")
                    if h: st.info(h)


# =========================================================
# PRODUCTION
# =========================================================

elif page == "Production":

    st.title("Production")

    if production_err:
        st.error(f"Failed to load Production table: {production_err}")
        h = rls_hint(production_err, PRODUCTION_TABLE, "select")
        if h: st.info(h)

    if production.empty and not production_err:
        st.info("Production table is empty. Add the first record below.")

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Production", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Production",
                               placeholder="Production ID, Item ID, Batch...")
        display = filter_df(production, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_production_id = next_id_for(PRODUCTION_TABLE, production)
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
                    h = rls_hint(str(e), PRODUCTION_TABLE, "insert")
                    if h: st.info(h)

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
                    h = rls_hint(str(e), PRODUCTION_TABLE, "update")
                    if h: st.info(h)

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
                    h = rls_hint(str(e), PRODUCTION_TABLE, "delete")
                    if h: st.info(h)


# =========================================================
# STOCK CONTROL
# =========================================================

elif page == "Stock Control":

    st.title("Stock Control")
    st.caption("Opening, Production, Dispatch, Return, and auto-computed Closing stock.")

    data_banner()

    stock_tabs = st.tabs([
        "Opening Stock",
        "Production Qty",
        "Dispatch Qty",
        "Return Qty",
        "Closing Stock (Auto)"
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
            "Dispatch Qty", items, dispatch_err
        )

    with stock_tabs[3]:
        crud_simple_table(
            RETURN_TABLE, return_qty, "Return_ID",
            "Return Qty", items, return_err
        )

    with stock_tabs[4]:
        st.markdown("### Auto-Computed Closing Stock")
        st.caption(
            "Closing = Opening + Produced − Dispatched + Returned + Adjusted. "
            "Ye values har entry pe automatically recalculate hoti hain."
        )
        if not STOCK_LEDGER.empty:
            st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)
        else:
            empty_state("No stock data available yet.")


# =========================================================
# STOCK ADJUSTMENT
# =========================================================

elif page == "Stock Adjustment":

    st.title("Stock Adjustment")
    st.caption("Record stock corrections: damage, loss, found, physical-check discrepancies.")

    if adjustment_err:
        st.error(f"Failed to load Stock_Adjustment table: {adjustment_err}")
        h = rls_hint(adjustment_err, ADJUSTMENT_TABLE, "select")
        if h: st.info(h)

    if adjustment.empty and not adjustment_err:
        st.info("Stock_Adjustment table is empty. Add the first record below.")

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Adjustment", "Update / Delete"])

    reasons = ["Physical Check", "Damage", "Loss", "Found", "Other"]

    # ---- VIEW ----
    with tab1:
        search = st.text_input("Search Adjustment",
                               placeholder="Adjustment ID, Item ID, Reason...")
        display = filter_df(adjustment, search)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    # ---- ADD ----
    with tab2:
        next_adj_id = next_id_for(ADJUSTMENT_TABLE, adjustment)
        st.info(f"Next Adjustment ID: {next_adj_id}")

        if items.empty:
            st.warning("Add an item in Item Registration first.")
        else:
            options = get_item_options(items)
            with st.form("add_adjustment_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    selected_item = st.selectbox("Item ID", options)
                    adj_date = st.date_input("Adjustment Date", value=date.today())
                with c2:
                    qty = st.number_input(
                        "Quantity (+ve to add, -ve to subtract)",
                        value=0.0, step=1.0
                    )
                    reason = st.selectbox("Reason", reasons)
                with c3:
                    remarks = st.text_area("Remarks", height=100)

                submit = st.form_submit_button("Add Adjustment", type="primary")

            if submit:
                try:
                    supabase.table(ADJUSTMENT_TABLE).insert({
                        "Adjustment_ID": next_adj_id,
                        "Item_ID": selected_item,
                        "Adjustment_Date": str(adj_date),
                        "Qty": qty,
                        "Reason": reason,
                        "Remarks": remarks.strip()
                    }).execute()
                    st.success(f"Adjustment {next_adj_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error("Adjustment add failed.")
                    st.code(str(e))
                    h = rls_hint(str(e), ADJUSTMENT_TABLE, "insert")
                    if h: st.info(h)

    # ---- UPDATE / DELETE ----
    with tab3:
        if adjustment.empty:
            st.info("No adjustment records.")
        else:
            selected_id = st.selectbox(
                "Select Adjustment ID",
                adjustment["Adjustment_ID"].astype(str).tolist()
            )
            selected = adjustment.loc[
                adjustment["Adjustment_ID"].astype(str) == selected_id
            ].iloc[0]

            options = get_item_options(items)
            current_item = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
            default_idx = options.index(current_item) if current_item in options else 0
            current_reason = str(selected["Reason"]) if pd.notna(selected["Reason"]) else "Other"
            reason_idx = reasons.index(current_reason) if current_reason in reasons else 4

            with st.form("update_adjustment_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_item = (st.selectbox("Item ID", options, index=default_idx)
                                 if options else current_item)
                    edit_date = st.date_input(
                        "Adjustment Date",
                        value=pd.to_datetime(
                            selected["Adjustment_Date"]
                        ).date() if pd.notna(selected["Adjustment_Date"]) else date.today()
                    )
                with c2:
                    edit_qty = st.number_input(
                        "Quantity", value=float(selected["Qty"]) if pd.notna(selected["Qty"]) else 0.0,
                        step=1.0
                    )
                    edit_reason = st.selectbox("Reason", reasons, index=reason_idx)
                with c3:
                    edit_remarks = st.text_area(
                        "Remarks",
                        value=str(selected["Remarks"]) if pd.notna(selected["Remarks"]) else "",
                        height=100
                    )
                update = st.form_submit_button("Update Adjustment", type="primary")

            if update:
                try:
                    supabase.table(ADJUSTMENT_TABLE).update({
                        "Item_ID": edit_item,
                        "Adjustment_Date": str(edit_date),
                        "Qty": edit_qty,
                        "Reason": edit_reason,
                        "Remarks": edit_remarks.strip()
                    }).eq("Adjustment_ID", selected_id).execute()
                    st.success("Adjustment updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))
                    h = rls_hint(str(e), ADJUSTMENT_TABLE, "update")
                    if h: st.info(h)

            st.markdown("---")
            if st.button("Delete Adjustment", type="secondary"):
                try:
                    supabase.table(ADJUSTMENT_TABLE).delete().eq(
                        "Adjustment_ID", selected_id
                    ).execute()
                    st.success("Adjustment deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))
                    h = rls_hint(str(e), ADJUSTMENT_TABLE, "delete")
                    if h: st.info(h)

    st.markdown("---")
    st.subheader("Item-wise Adjustment Summary")
    if not adjustment.empty:
        summary = (adjustment.groupby("Item_ID", as_index=False)["Qty"]
                   .sum().rename(columns={"Qty": "Net_Adjustment"}))
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        empty_state("No adjustments yet.")


# =========================================================
# PHYSICAL CHECK
# =========================================================

elif page == "Physical Check":

    st.title("Physical Check")
    st.caption(
        "Compare system closing stock with physical count. "
        "Differences automatically create Stock_Adjustment entries."
    )

    if STOCK_LEDGER.empty:
        empty_state("No stock data available yet.")
        st.stop()

    ledger = STOCK_LEDGER.copy()
    ledger = ledger.rename(columns={
        "Opening": "System_Opening",
        "Produced": "System_Produced",
        "Dispatched": "System_Dispatched",
        "Returned": "System_Returned",
        "Adjusted": "System_Adjusted",
        "Computed_Closing": "System_Closing",
    })

    st.subheader("Enter Physical Counts")

    # Build a form with input per item
    with st.form("physical_check_form"):
        counts = {}
        for _, row in ledger.iterrows():
            item_id = row["Item_ID"]
            item_code = row["Item_Code"] if pd.notna(row["Item_Code"]) else ""
            system_closing = float(row["System_Closing"])

            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                st.markdown(f"**{item_id}**")
                st.caption(item_code)
            with c2:
                st.metric("System Closing", f"{system_closing:,.0f}")
            with c3:
                counts[item_id] = st.number_input(
                    "Physical Count",
                    min_value=0.0,
                    value=system_closing,
                    step=1.0,
                    key=f"physical_{item_id}"
                )
            st.markdown("---")

        submit = st.form_submit_button(
            "Save All Differences as Adjustments",
            type="primary"
        )

    if submit:
        today = date.today()
        inserted = 0
        skipped = 0
        errors = []

        # Reload adjustment to get next ID
        try:
            adj_resp = supabase.table(ADJUSTMENT_TABLE).select("*").execute()
            current_adj_df = make_df(adj_resp.data or [], ADJUSTMENT_COLUMNS)
        except Exception:
            current_adj_df = adjustment.copy()

        for _, row in ledger.iterrows():
            item_id = row["Item_ID"]
            system_closing = float(row["System_Closing"])
            physical = float(counts.get(item_id, system_closing))
            diff = physical - system_closing

            if abs(diff) < 0.0001:
                skipped += 1
                continue

            new_id = next_id_for(ADJUSTMENT_TABLE, current_adj_df)
            payload = {
                "Adjustment_ID": new_id,
                "Item_ID": item_id,
                "Adjustment_Date": str(today),
                "Qty": diff,
                "Reason": "Physical Check",
                "Remarks": f"System {system_closing:.0f} vs Physical {physical:.0f}"
            }

            try:
                supabase.table(ADJUSTMENT_TABLE).insert(payload).execute()
                # Append to local DF so next ID generation stays correct
                current_adj_df = pd.concat(
                    [current_adj_df, pd.DataFrame([payload])],
                    ignore_index=True
                )
                inserted += 1
            except Exception as e:
                errors.append(f"{item_id}: {e}")

        if inserted:
            st.success(f"{inserted} adjustment(s) created.")
        if skipped:
            st.info(f"{skipped} item(s) matched — no adjustment needed.")
        if errors:
            st.error("Some entries failed:")
            for e in errors:
                st.code(e)

        if inserted or skipped:
            st.balloons()
            refresh_all()

    st.markdown("---")
    st.subheader("Latest Physical Check Adjustments")
    if not adjustment.empty:
        pc = adjustment[adjustment["Reason"].astype(str) == "Physical Check"]
        if not pc.empty:
            st.dataframe(pc.tail(20), use_container_width=True, hide_index=True)
        else:
            st.info("No physical-check adjustments yet.")
    else:
        st.info("No adjustment records yet.")


# =========================================================
# ANALYTICS
# =========================================================

elif page == "Analytics":

    st.title("Analytics")
    st.caption("Production and inventory performance.")

    data_banner()

    st.subheader("Production Performance")
    if not production.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Planned", f"{TOTALS['planned']:,.0f} m")
        c2.metric("Good", f"{TOTALS['good']:,.0f} m")
        c3.metric("Rejected", f"{TOTALS['rejected']:,.0f} m")

        analysis = pd.DataFrame({
            "Type": ["Good Production", "Rejected Production"],
            "Quantity": [TOTALS["good"], TOTALS["rejected"]]
        })
        fig = px.bar(analysis, x="Type", y="Quantity", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No production data available.")

    st.markdown("---")

    st.subheader("Stock Ledger")
    if not STOCK_LEDGER.empty:
        st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)

        chart_cols = ["Opening", "Produced", "Dispatched",
                      "Returned", "Adjusted", "Computed_Closing"]
        fig = px.bar(STOCK_LEDGER, x="Item_ID",
                     y=chart_cols, barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    else:
        empty_state("No stock data available.")


# =========================================================
# CUSTOM CHARTS
# =========================================================

elif page == "Custom Charts":

    st.title("Custom Charts")
    st.caption("Build your own charts — pick data source, chart type, axes.")

    source_options = {
        "Production": production,
        "Item Registration": items,
        "Opening Stock": opening,
        "Production Qty": prod_qty,
        "Dispatch Qty": dispatch,
        "Return Qty": return_qty,
        "Stock Adjustment": adjustment,
        "Stock Ledger (computed)": STOCK_LEDGER,
    }

    source_name = st.selectbox("Select a dataset", list(source_options.keys()))
    df = source_options[source_name].copy()

    if df.empty:
        empty_state(f"{source_name} has no records.")
        st.stop()

    with st.expander("Apply filters", expanded=False):
        filter_cols = st.multiselect(
            "Filter by column",
            options=[c for c in df.columns
                     if df[c].dtype == "object" or df[c].nunique() < 30],
            default=[]
        )
        filtered_df = df.copy()
        for col in filter_cols:
            unique_vals = df[col].dropna().astype(str).unique().tolist()
            if not unique_vals:
                continue
            picked = st.multiselect(f"Values for {col}", unique_vals,
                                    default=unique_vals, key=f"f_{col}")
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(picked)]
        df = filtered_df

    if df.empty:
        st.warning("No data left after filters.")
        st.stop()

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    all_cols = df.columns.tolist()

    chart_type = st.selectbox(
        "Chart Type",
        ["Bar Chart", "Grouped Bar Chart", "Stacked Bar Chart",
         "Line Chart", "Area Chart", "Pie Chart", "Donut Chart",
         "Scatter Plot", "Histogram", "Box Plot"]
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        x_axis = st.selectbox("X-axis", all_cols,
                              index=(all_cols.index("Item_ID")
                                     if "Item_ID" in all_cols else 0))
    with c2:
        y_axis = st.selectbox("Y-axis",
                              numeric_cols if numeric_cols else ["(no numeric)"])
    with c3:
        color_by = st.selectbox("Color / Group by", ["(none)"] + all_cols)

    agg_choice = "None"
    if chart_type not in ["Histogram", "Scatter Plot", "Box Plot"]:
        agg_choice = st.selectbox(
            "Aggregation",
            ["sum", "mean", "count", "max", "min"]
        )

    top_n = st.slider("Top N (0 = all)", 0, 50, 0)
    sort_order = st.radio("Sort order", ["Descending", "Ascending", "None"],
                          horizontal=True)

    plot_df = df.copy()
    try:
        if agg_choice != "None" and chart_type not in ["Histogram", "Scatter Plot", "Box Plot"]:
            group_cols = [x_axis]
            if color_by != "(none)" and color_by != x_axis:
                group_cols.append(color_by)
            if agg_choice == "count":
                plot_df = (plot_df.groupby(group_cols)[y_axis]
                           .count().reset_index()
                           .rename(columns={y_axis: "count"}))
                y_plot = "count"
            else:
                plot_df = (plot_df.groupby(group_cols)[y_axis]
                           .agg(agg_choice).reset_index())
                y_plot = y_axis
        else:
            y_plot = y_axis

        if agg_choice != "None" and y_plot in plot_df.columns and sort_order != "None":
            plot_df = plot_df.sort_values(
                y_plot, ascending=(sort_order == "Ascending")
            )
        if top_n > 0 and y_plot in plot_df.columns:
            plot_df = plot_df.head(top_n)

        color_arg = color_by if color_by != "(none)" else None

        if chart_type == "Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot, color=color_arg, text_auto=True)
        elif chart_type == "Grouped Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot, color=color_arg, barmode="group")
        elif chart_type == "Stacked Bar Chart":
            fig = px.bar(plot_df, x=x_axis, y=y_plot, color=color_arg, barmode="stack")
        elif chart_type == "Line Chart":
            fig = px.line(plot_df, x=x_axis, y=y_plot, color=color_arg, markers=True)
        elif chart_type == "Area Chart":
            fig = px.area(plot_df, x=x_axis, y=y_plot, color=color_arg)
        elif chart_type == "Pie Chart":
            fig = px.pie(plot_df, names=x_axis, values=y_plot)
        elif chart_type == "Donut Chart":
            fig = px.pie(plot_df, names=x_axis, values=y_plot, hole=0.5)
        elif chart_type == "Scatter Plot":
            fig = px.scatter(plot_df, x=x_axis, y=y_plot, color=color_arg)
        elif chart_type == "Histogram":
            fig = px.histogram(plot_df, x=x_axis, color=color_arg)
        elif chart_type == "Box Plot":
            fig = px.box(plot_df, x=x_axis, y=y_plot, color=color_arg)
        else:
            fig = None

        if fig is not None:
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=520)
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("View underlying data"):
            st.dataframe(plot_df, use_container_width=True, hide_index=True)

        csv = plot_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv,
                           file_name=f"chart_{source_name.lower().replace(' ', '_')}.csv",
                           mime="text/csv")

    except Exception as e:
        st.error("Chart build error.")
        st.code(str(e))


# =========================================================
# DATA MANAGEMENT
# =========================================================

elif page == "Data Management":

    st.title("Data Management")
    st.caption("Live database records and diagnostics.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items", len(items))
    c2.metric("Production", len(production))
    c3.metric("Adjustments", len(adjustment))
    c4.metric("Stock Ledger Rows", len(STOCK_LEDGER))

    st.markdown("---")

    with st.expander("Table Diagnostics", expanded=False):
        diag = pd.DataFrame({
            "Table": [
                ITEM_TABLE, PRODUCTION_TABLE,
                OPENING_TABLE, PRODUCTION_QTY_TABLE,
                DISPATCH_TABLE, RETURN_TABLE,
                CLOSING_TABLE, ADJUSTMENT_TABLE
            ],
            "Rows Loaded": [
                len(items), len(production),
                len(opening), len(prod_qty),
                len(dispatch), len(return_qty),
                len(closing), len(adjustment)
            ],
            "Status": [
                "Error" if items_err else "OK",
                "Error" if production_err else ("Empty" if production.empty else "OK"),
                "Error" if opening_err else ("Empty" if opening.empty else "OK"),
                "Error" if prod_qty_err else ("Empty" if prod_qty.empty else "OK"),
                "Error" if dispatch_err else ("Empty" if dispatch.empty else "OK"),
                "Error" if return_err else ("Empty" if return_qty.empty else "OK"),
                "Error" if closing_err else ("Empty" if closing.empty else "OK"),
                "Error" if adjustment_err else ("Empty" if adjustment.empty else "OK"),
            ],
            "Error": [
                items_err or "-",
                production_err or "-",
                opening_err or "-",
                prod_qty_err or "-",
                dispatch_err or "-",
                return_err or "-",
                closing_err or "-",
                adjustment_err or "-",
            ]
        })
        st.dataframe(diag, use_container_width=True, hide_index=True)

        if st.button("Force Reload All Data"):
            refresh_all()

    st.markdown("---")

    for label, frame in [
        ("Item Registration", items),
        ("Production", production),
        ("Opening Stock", opening),
        ("Production Qty", prod_qty),
        ("Dispatch Qty", dispatch),
        ("Return Qty", return_qty),
        ("Closing Stock", closing),
        ("Stock Adjustment", adjustment),
    ]:
        st.subheader(label)
        st.dataframe(frame, use_container_width=True, hide_index=True)


st.markdown("---")
st.caption("Flex Head Industries Pvt Ltd | ERP Management System")
