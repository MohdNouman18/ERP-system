import os
from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

st.set_page_config(
    page_title="Flex Head Industry | ERP",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Styling
# -----------------------------
with open(os.path.join(os.path.dirname(__file__), "style.css"), "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

COMPANY = "Flex Head Industry Pvt Ltd"
TABLES = {
    "Items": "item_registration",
    "Production": "production",
    "Stock Control": "stock_control",
}

CSV_FILES = {
    "Items": "Item_Registration.csv",
    "Production": "Production.csv",
    "Stock Control": "Stock_Control.csv",
}

# -----------------------------
# Supabase / local data layer
# -----------------------------
@st.cache_resource
def get_supabase():
    url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")
    if not url or not key or create_client is None:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

supabase = get_supabase()

def load_csv(name):
    path = os.path.join(os.path.dirname(__file__), CSV_FILES[name])
    if os.path.exists(path):
        df = pd.read_csv(path)
        return clean_df(df)
    return pd.DataFrame()

def clean_df(df):
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    for col in df.columns:
        if "Date" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

@st.cache_data(ttl=60)
def fetch_table(name):
    if supabase:
        try:
            response = supabase.table(TABLES[name]).select("*").execute()
            return clean_df(pd.DataFrame(response.data or []))
        except Exception:
            pass
    return load_csv(name)

def refresh():
    st.cache_data.clear()
    st.rerun()

def insert_row(name, data):
    if supabase:
        try:
            supabase.table(TABLES[name]).insert(data).execute()
            refresh()
            return True, "Record created successfully."
        except Exception as e:
            return False, str(e)
    return False, "Supabase is not connected. Add SUPABASE_URL and SUPABASE_KEY to use live CRUD."

def update_row(name, primary_key, pk_value, data):
    if supabase:
        try:
            supabase.table(TABLES[name]).update(data).eq(primary_key, pk_value).execute()
            refresh()
            return True, "Record updated successfully."
        except Exception as e:
            return False, str(e)
    return False, "Supabase is not connected. Add SUPABASE_URL and SUPABASE_KEY to use live CRUD."

def delete_row(name, primary_key, pk_value):
    if supabase:
        try:
            supabase.table(TABLES[name]).delete().eq(primary_key, pk_value).execute()
            refresh()
            return True, "Record deleted successfully."
        except Exception as e:
            return False, str(e)
    return False, "Supabase is not connected. Add SUPABASE_URL and SUPABASE_KEY to use live CRUD."

items = fetch_table("Items")
production = fetch_table("Production")
stock = fetch_table("Stock Control")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown(
    """
    <div class="brand">
        <div class="brand-mark">FH</div>
        <div>
            <div class="brand-name">FLEX HEAD</div>
            <div class="brand-sub">INDUSTRY PVT LTD</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "ERP MODULES",
    ["Executive Dashboard", "Item Registration", "Production", "Stock Control", "Analytics", "Data Management"],
)

st.sidebar.markdown("---")
if supabase:
    st.sidebar.success("● Supabase connected")
else:
    st.sidebar.warning("● Demo / CSV mode")
    st.sidebar.caption("CRUD becomes live after Supabase credentials are configured.")

if st.sidebar.button("↻ Refresh Data", use_container_width=True):
    refresh()

# -----------------------------
# Helpers
# -----------------------------
def metric_card(label, value, caption="", icon=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def pct(a, b):
    return 0 if not b else (a / b) * 100

def safe_sum(df, col):
    return pd.to_numeric(df[col], errors="coerce").fillna(0).sum() if col in df.columns else 0

def show_table(df, height=360):
    if df.empty:
        st.info("No records available.")
    else:
        st.dataframe(df, use_container_width=True, height=height, hide_index=True)

# -----------------------------
# Dashboard
# -----------------------------
def dashboard():
    st.markdown('<div class="page-kicker">ERP CONTROL CENTER</div>', unsafe_allow_html=True)
    st.title("Executive Dashboard")
    st.caption("Manufacturing, production and inventory overview for Flex Head Industry Pvt Ltd.")

    planned = safe_sum(production, "Planned_Qty_m")
    good = safe_sum(production, "Good_Qty_m")
    rejected = safe_sum(production, "Rejected_Qty_m")
    dispatched = safe_sum(stock, "Dispatched_Qty_m")
    closing = safe_sum(stock, "Closing_Stock_m")
    production_eff = pct(good, planned)
    rejection_rate = pct(rejected, good + rejected)

    cols = st.columns(5)
    with cols[0]: metric_card("Registered Items", f"{len(items):,}", "Product master records", "◈")
    with cols[1]: metric_card("Good Production", f"{good:,.0f} m", f"{production_eff:.1f}% yield", "▣")
    with cols[2]: metric_card("Rejected Quantity", f"{rejected:,.0f} m", f"{rejection_rate:.1f}% rejection rate", "△")
    with cols[3]: metric_card("Dispatched", f"{dispatched:,.0f} m", "Total dispatch quantity", "↗")
    with cols[4]: metric_card("Closing Stock", f"{closing:,.0f} m", "Current recorded closing stock", "▤")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.subheader("Production Performance")
        if not production.empty:
            p = production.copy()
            p["Production_Date"] = pd.to_datetime(p["Production_Date"], errors="coerce")
            daily = p.groupby("Production_Date", as_index=False)[["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"]].sum()
            long = daily.melt("Production_Date", var_name="Metric", value_name="Quantity")
            fig = px.line(long, x="Production_Date", y="Quantity", color="Metric", markers=True,
                          template="plotly_white")
            fig.update_layout(height=360, margin=dict(l=10,r=10,t=20,b=10), legend_title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No production data.")

    with c2:
        st.subheader("Production Status")
        if not production.empty and "Production_Status" in production:
            status = production["Production_Status"].value_counts().reset_index()
            status.columns = ["Status", "Count"]
            fig = px.pie(status, names="Status", values="Count", hole=.62, template="plotly_white")
            fig.update_layout(height=360, margin=dict(l=5,r=5,t=20,b=5), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Stock by Item")
        if not stock.empty:
            s = stock.merge(items[["Item_ID","Item_Code"]] if "Item_Code" in items else items[["Item_ID"]],
                            on="Item_ID", how="left")
            label = "Item_Code" if "Item_Code" in s else "Item_ID"
            agg = s.groupby(label, as_index=False)["Closing_Stock_m"].sum().sort_values("Closing_Stock_m", ascending=False)
            fig = px.bar(agg, x=label, y="Closing_Stock_m", template="plotly_white")
            fig.update_layout(height=330, margin=dict(l=10,r=10,t=20,b=10), xaxis_title="", yaxis_title="Closing stock (m)")
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.subheader("Recent Production")
        if not production.empty:
            recent = production.sort_values("Production_Date", ascending=False).head(7)
            show_table(recent[["Production_ID","Item_ID","Production_Date","Good_Qty_m","Rejected_Qty_m","Production_Status"]], 330)

# -----------------------------
# Item Registration
# -----------------------------
def item_page():
    st.markdown('<div class="page-kicker">MASTER DATA</div>', unsafe_allow_html=True)
    st.title("Item Registration")
    st.caption("Maintain the product and material specification master.")

    tab1, tab2 = st.tabs(["Item List", "Add / Edit Item"])
    with tab1:
        q = st.text_input("Search items", placeholder="Search by item code, grade, application or color...")
        view = items.copy()
        if q:
            mask = view.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
            view = view[mask]
        show_table(view)

    with tab2:
        existing = items["Item_ID"].tolist() if not items.empty else []
        mode = st.radio("Action", ["Create", "Edit", "Delete"], horizontal=True)
        if mode == "Create":
            with st.form("create_item"):
                c1,c2,c3 = st.columns(3)
                item_id = c1.text_input("Item ID *", placeholder="ITM-016")
                code = c2.text_input("Item Code *")
                grade = c3.text_input("Material Grade", value="PE-80")
                c4,c5,c6 = st.columns(3)
                app = c4.text_input("Application")
                dia = c5.number_input("Nominal Diameter (mm)", min_value=0.0, step=1.0)
                wall = c6.number_input("Wall Thickness (mm)", min_value=0.0, step=0.1)
                c7,c8,c9,c10 = st.columns(4)
                sdr = c7.text_input("SDR")
                color = c8.text_input("Color")
                length = c9.number_input("Standard Length", min_value=0.0, step=1.0)
                unit = c10.text_input("Unit", value="m")
                submitted = st.form_submit_button("Create Item", use_container_width=True)
            if submitted:
                ok,msg = insert_row("Items", {
                    "Item_ID": item_id, "Item_Code": code, "Material_Grade": grade,
                    "Application": app, "Nominal_Diameter_mm": dia, "Wall_Thickness_mm": wall,
                    "SDR": sdr, "Color": color, "Standard_Length": length, "Unit": unit
                })
                st.success(msg) if ok else st.error(msg)

        elif mode == "Edit" and existing:
            selected = st.selectbox("Select Item", existing)
            row = items[items["Item_ID"] == selected].iloc[0]
            with st.form("edit_item"):
                c1,c2,c3 = st.columns(3)
                code = c1.text_input("Item Code", value=str(row.get("Item_Code","")))
                grade = c2.text_input("Material Grade", value=str(row.get("Material_Grade","")))
                app = c3.text_input("Application", value=str(row.get("Application","")))
                c4,c5,c6 = st.columns(3)
                dia = c4.number_input("Nominal Diameter (mm)", value=float(row.get("Nominal_Diameter_mm",0)))
                wall = c5.number_input("Wall Thickness (mm)", value=float(row.get("Wall_Thickness_mm",0)))
                sdr = c6.text_input("SDR", value=str(row.get("SDR","")))
                c7,c8,c9 = st.columns(3)
                color = c7.text_input("Color", value=str(row.get("Color","")))
                length = c8.number_input("Standard Length", value=float(row.get("Standard_Length",0)))
                unit = c9.text_input("Unit", value=str(row.get("Unit","m")))
                submitted = st.form_submit_button("Save Changes", use_container_width=True)
            if submitted:
                ok,msg = update_row("Items", "Item_ID", selected, {
                    "Item_Code": code, "Material_Grade": grade, "Application": app,
                    "Nominal_Diameter_mm": dia, "Wall_Thickness_mm": wall, "SDR": sdr,
                    "Color": color, "Standard_Length": length, "Unit": unit
                })
                st.success(msg) if ok else st.error(msg)
        elif mode == "Delete" and existing:
            selected = st.selectbox("Select Item to Delete", existing)
            st.warning("Deleting an item can break related production and stock records.")
            if st.button("Delete Item", type="primary"):
                ok,msg = delete_row("Items", "Item_ID", selected)
                st.success(msg) if ok else st.error(msg)
        else:
            st.info("No item records available.")

# -----------------------------
# Production
# -----------------------------
def production_page():
    st.markdown('<div class="page-kicker">MANUFACTURING</div>', unsafe_allow_html=True)
    st.title("Production Management")
    st.caption("Track batches, production lines, planned quantities, good output and rejects.")

    k1,k2,k3,k4 = st.columns(4)
    planned = safe_sum(production,"Planned_Qty_m")
    good = safe_sum(production,"Good_Qty_m")
    rejected = safe_sum(production,"Rejected_Qty_m")
    with k1: metric_card("Planned", f"{planned:,.0f} m", "Scheduled quantity", "◎")
    with k2: metric_card("Good", f"{good:,.0f} m", f"{pct(good,planned):.1f}% of plan", "✓")
    with k3: metric_card("Rejected", f"{rejected:,.0f} m", f"{pct(rejected,good+rejected):.1f}% of output", "!")
    with k4: metric_card("Batches", f"{len(production):,}", "Production records", "#")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    q = st.text_input("Filter production", placeholder="Search batch, production line, item or status...")
    view = production.copy()
    if q and not view.empty:
        mask = view.astype(str).apply(lambda x: x.str.contains(q, case=False, na=False)).any(axis=1)
        view = view[mask]
    show_table(view)

    with st.expander("Add Production Record"):
        item_ids = items["Item_ID"].tolist() if not items.empty else []
        with st.form("create_production"):
            c1,c2,c3 = st.columns(3)
            pid = c1.text_input("Production ID *", placeholder="PRD-016")
            item_id = c2.selectbox("Item ID", item_ids) if item_ids else c2.text_input("Item ID")
            pdate = c3.date_input("Production Date", value=date.today())
            c4,c5,c6 = st.columns(3)
            batch = c4.text_input("Batch No.")
            line = c5.text_input("Production Line")
            status = c6.selectbox("Production Status", ["Planned","In Progress","Completed","Hold","Cancelled"])
            c7,c8,c9 = st.columns(3)
            planned_qty = c7.number_input("Planned Qty (m)", min_value=0.0, step=1.0)
            good_qty = c8.number_input("Good Qty (m)", min_value=0.0, step=1.0)
            reject_qty = c9.number_input("Rejected Qty (m)", min_value=0.0, step=1.0)
            submitted = st.form_submit_button("Create Production Record", use_container_width=True)
        if submitted:
            ok,msg = insert_row("Production", {
                "Production_ID": pid, "Item_ID": item_id, "Production_Date": str(pdate),
                "Batch_No": batch, "Production_Line": line, "Planned_Qty_m": planned_qty,
                "Good_Qty_m": good_qty, "Rejected_Qty_m": reject_qty, "Production_Status": status
            })
            st.success(msg) if ok else st.error(msg)

# -----------------------------
# Stock Control
# -----------------------------
def stock_page():
    st.markdown('<div class="page-kicker">INVENTORY</div>', unsafe_allow_html=True)
    st.title("Stock Control")
    st.caption("Monitor opening stock, production inflow, dispatches and closing stock.")

    opening = safe_sum(stock,"Opening_Stock_m")
    produced = safe_sum(stock,"Produced_Qty_m")
    dispatched = safe_sum(stock,"Dispatched_Qty_m")
    closing = safe_sum(stock,"Closing_Stock_m")

    cols = st.columns(4)
    with cols[0]: metric_card("Opening Stock", f"{opening:,.0f} m", "Recorded opening balance", "□")
    with cols[1]: metric_card("Produced", f"{produced:,.0f} m", "Stock inflow", "＋")
    with cols[2]: metric_card("Dispatched", f"{dispatched:,.0f} m", "Outbound quantity", "↗")
    with cols[3]: metric_card("Closing Stock", f"{closing:,.0f} m", "Recorded balance", "▤")

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    show_table(stock)

    with st.expander("Add Stock Record"):
        item_ids = items["Item_ID"].tolist() if not items.empty else []
        prod_ids = production["Production_ID"].tolist() if not production.empty else []
        with st.form("create_stock"):
            c1,c2,c3 = st.columns(3)
            sid = c1.text_input("Stock ID *", placeholder="STK-016")
            item_id = c2.selectbox("Item ID", item_ids) if item_ids else c2.text_input("Item ID")
            prod_id = c3.selectbox("Production ID", prod_ids) if prod_ids else c3.text_input("Production ID")
            c4,c5,c6 = st.columns(3)
            batch = c4.text_input("Batch No.")
            sdate = c5.date_input("Stock Date", value=date.today())
            status = c6.selectbox("Stock Status", ["Available","Low Stock","Reserved","Hold","Out of Stock"])
            c7,c8,c9,c10 = st.columns(4)
            opening_qty = c7.number_input("Opening Stock (m)", min_value=0.0, step=1.0)
            produced_qty = c8.number_input("Produced Qty (m)", min_value=0.0, step=1.0)
            dispatched_qty = c9.number_input("Dispatched Qty (m)", min_value=0.0, step=1.0)
            closing_qty = c10.number_input("Closing Stock (m)", min_value=0.0, step=1.0)
            submitted = st.form_submit_button("Create Stock Record", use_container_width=True)
        if submitted:
            ok,msg = insert_row("Stock Control", {
                "Stock_ID": sid, "Item_ID": item_id, "Production_ID": prod_id, "Batch_No": batch,
                "Stock_Date": str(sdate), "Opening_Stock_m": opening_qty,
                "Produced_Qty_m": produced_qty, "Dispatched_Qty_m": dispatched_qty,
                "Closing_Stock_m": closing_qty, "Stock_Status": status
            })
            st.success(msg) if ok else st.error(msg)

# -----------------------------
# Analytics
# -----------------------------
def analytics_page():
    st.markdown('<div class="page-kicker">BUSINESS INTELLIGENCE</div>', unsafe_allow_html=True)
    st.title("Analytics & Insights")
    st.caption("Use operational data to identify output trends, rejection patterns and inventory movement.")

    if production.empty:
        st.info("Production data is required for analytics.")
        return

    p = production.copy()
    p["Production_Date"] = pd.to_datetime(p["Production_Date"], errors="coerce")
    p["Yield_%"] = (pd.to_numeric(p["Good_Qty_m"], errors="coerce") /
                    (pd.to_numeric(p["Good_Qty_m"], errors="coerce") + pd.to_numeric(p["Rejected_Qty_m"], errors="coerce")).replace(0,pd.NA))*100

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Yield by Production Line")
        line = p.groupby("Production_Line", as_index=False).agg(
            Good=("Good_Qty_m","sum"), Rejected=("Rejected_Qty_m","sum")
        )
        line["Yield_%"] = line["Good"]/(line["Good"]+line["Rejected"])*100
        fig = px.bar(line.sort_values("Yield_%"), x="Yield_%", y="Production_Line",
                     orientation="h", template="plotly_white", text_auto=".1f")
        fig.update_layout(height=350, margin=dict(l=10,r=10,t=20,b=10), xaxis_title="Yield %", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Good vs Rejected Output")
        long = p.groupby("Production_Status", as_index=False)[["Good_Qty_m","Rejected_Qty_m"]].sum()
        long = long.melt("Production_Status", var_name="Metric", value_name="Quantity")
        fig = px.bar(long, x="Production_Status", y="Quantity", color="Metric",
                     barmode="group", template="plotly_white")
        fig.update_layout(height=350, margin=dict(l=10,r=10,t=20,b=10), xaxis_title="", yaxis_title="Quantity (m)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Item-Level Production Analysis")
    merged = p.merge(items[["Item_ID","Item_Code","Material_Grade","Application"]] if not items.empty else pd.DataFrame(),
                      on="Item_ID", how="left")
    if not merged.empty:
        analysis = merged.groupby(["Item_ID","Item_Code"], dropna=False).agg(
            Planned_m=("Planned_Qty_m","sum"),
            Good_m=("Good_Qty_m","sum"),
            Rejected_m=("Rejected_Qty_m","sum"),
        ).reset_index()
        analysis["Yield_%"] = analysis["Good_m"]/(analysis["Good_m"]+analysis["Rejected_m"]).replace(0,pd.NA)*100
        analysis["Reject_%"] = analysis["Rejected_m"]/(analysis["Good_m"]+analysis["Rejected_m"]).replace(0,pd.NA)*100
        show_table(analysis.round(2), 420)

# -----------------------------
# Data Management
# -----------------------------
def data_management():
    st.markdown('<div class="page-kicker">DATABASE ADMINISTRATION</div>', unsafe_allow_html=True)
    st.title("Data Management")
    st.caption("Review table health and configure the production database connection.")

    st.subheader("Database Status")
    if supabase:
        st.success("Supabase connection is active.")
    else:
        st.info("The app is currently using the uploaded CSV files as a local fallback.")

    stats = pd.DataFrame([
        {"Module":"Item Registration","Records":len(items),"Columns":len(items.columns)},
        {"Module":"Production","Records":len(production),"Columns":len(production.columns)},
        {"Module":"Stock Control","Records":len(stock),"Columns":len(stock.columns)},
    ])
    show_table(stats, 220)

    st.subheader("Supabase Configuration")
    st.code(
        """SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SUPABASE-ANON-KEY"

# Streamlit Cloud:
# App → Settings → Secrets""",
        language="toml",
    )
    st.caption("For production, keep the Supabase key in Streamlit Secrets or environment variables. Do not hard-code credentials in app.py.")

    st.subheader("Expected Supabase Tables")
    schema = pd.DataFrame([
        {"Table":"item_registration","Primary Key":"Item_ID","Source":"Item_Registration.csv"},
        {"Table":"production","Primary Key":"Production_ID","Source":"Production.csv"},
        {"Table":"stock_control","Primary Key":"Stock_ID","Source":"Stock_Control.csv"},
    ])
    show_table(schema, 220)

# -----------------------------
# Router
# -----------------------------
if page == "Executive Dashboard":
    dashboard()
elif page == "Item Registration":
    item_page()
elif page == "Production":
    production_page()
elif page == "Stock Control":
    stock_page()
elif page == "Analytics":
    analytics_page()
else:
    data_management()
