import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client, Client


st.set_page_config(
    page_title="Flex Head Industries | ERP",
    page_icon="logo.png" if os.path.exists("logo.png") else None,
    layout="wide",
    initial_sidebar_state="expanded"
)


ITEM_TABLE = "Item_Registration"
PRODUCTION_TABLE = "Production"
OPENING_TABLE = "Opening_Stock"
PRODUCTION_QTY_TABLE = "Production_Qty"
DISPATCH_TABLE = "Dispatch_Qty"
RETURN_TABLE = "Return_Qty"
CLOSING_TABLE = "Closing_Stock"
ADJUSTMENT_TABLE = "Stock_Adjustment"
CHALLAN_TABLE = "Delivery_Challan"
CHALLAN_ITEMS_TABLE = "Delivery_Challan_Items"
RETURN_CHALLAN_TABLE = "Return_Challan"
RETURN_CHALLAN_ITEMS_TABLE = "Return_Challan_Items"

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
OPENING_COLUMNS = ("Opening_Stock_ID", "Item_ID", "Qty", "Entry_Date")
PRODUCTION_QTY_COLUMNS = ("Production_ID", "Item_ID", "Qty", "Entry_Date")
DISPATCH_COLUMNS = ("Dispatch_ID", "Item_ID", "Qty", "Entry_Date")
RETURN_COLUMNS = ("Return_ID", "Item_ID", "Qty", "Entry_Date")
CLOSING_COLUMNS = ("Closing_Stock_ID", "Item_ID", "Qty", "Entry_Date")
ADJUSTMENT_COLUMNS = (
    "Adjustment_ID", "Item_ID", "Adjustment_Date",
    "Qty", "Reason", "Remarks"
)
CHALLAN_COLUMNS = (
    "challan_id", "challan_no", "challan_date",
    "vehicle_no", "received_by", "sent_by",
    "customer_name", "contact_detail", "project",
    "location", "sales_head", "payment_terms", "created_at"
)
CHALLAN_ITEMS_COLUMNS = (
    "challan_item_id", "challan_id", "sr_no",
    "item_id", "description", "quantity", "unit", "created_at"
)
RETURN_CHALLAN_COLUMNS = (
    "challan_id", "challan_no", "challan_date",
    "vehicle_no", "received_by", "sent_by",
    "customer_name", "contact_detail", "project",
    "location", "sales_head", "payment_terms", "created_at"
)
RETURN_CHALLAN_ITEMS_COLUMNS = (
    "challan_item_id", "challan_id", "sr_no",
    "item_id", "description", "quantity", "unit", "created_at"
)

ID_PREFIX = {
    ITEM_TABLE:           ("Item_ID",          "ITM"),
    PRODUCTION_TABLE:     ("Production_ID",    "PRD"),
    OPENING_TABLE:        ("Opening_Stock_ID", "OPN"),
    PRODUCTION_QTY_TABLE: ("Production_ID",    "PQT"),
    DISPATCH_TABLE:       ("Dispatch_ID",      "DSP"),
    RETURN_TABLE:         ("Return_ID",        "RET"),
    CLOSING_TABLE:        ("Closing_Stock_ID", "CLS"),
    ADJUSTMENT_TABLE:     ("Adjustment_ID",    "ADJ"),
}

CACHE_TTL = 300
PRODUCTION_LINES = ["Machine 01", "Machine 02", "Machine 03"]
PRODUCTION_STATUSES = ["Completed", "In Progress", "Pending", "Rejected"]
ADJUSTMENT_REASONS = ["Physical Check", "Damage", "Loss", "Found", "Other"]

COMPANY_NAME = "FLEX HEAD INDUSTRIES PVT LTD"
COMPANY_ADDR_LINE1 = (
    "M-308/2, KCHS, 4th Floor, Plot No. 01, Main Korangi Road, "
    "Korangi Industrial Area, Karachi - 74900, Pakistan"
)
COMPANY_ADDR_LINE2 = (
    "HEAD OFFICE: 4.5 KM, F.E.H.S., Block-4, Karachi. "
    "PH: 021-35090651-52, 021-35000653-54"
)
COMPANY_ADDR_LINE3 = (
    "TEL: 021-35162930, 021-35162931, 0335-1279370, 0316-1239770"
)


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


def fmt_date_only(val):
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except Exception:
        pass
    if isinstance(val, date) and not isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return ""
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return s[:10]
        try:
            return pd.to_datetime(s).strftime("%Y-%m-%d")
        except Exception:
            return s
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return str(val)


def date_str(d):
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    return fmt_date_only(d)


def today_str():
    return date.today().strftime("%Y-%m-%d")


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
    if num_cols:
        df = convert_numeric(df, num_cols)
    return df, None


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_all_data():
    specs = [
        (ITEM_TABLE, ITEM_COLUMNS, ()),
        (PRODUCTION_TABLE, PRODUCTION_COLUMNS,
         ("Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m")),
        (OPENING_TABLE, OPENING_COLUMNS, ("Qty",)),
        (PRODUCTION_QTY_TABLE, PRODUCTION_QTY_COLUMNS, ("Qty",)),
        (DISPATCH_TABLE, DISPATCH_COLUMNS, ("Qty",)),
        (RETURN_TABLE, RETURN_COLUMNS, ("Qty",)),
        (CLOSING_TABLE, CLOSING_COLUMNS, ("Qty",)),
        (ADJUSTMENT_TABLE, ADJUSTMENT_COLUMNS, ("Qty",)),
        (CHALLAN_TABLE, CHALLAN_COLUMNS, ()),
        (CHALLAN_ITEMS_TABLE, CHALLAN_ITEMS_COLUMNS, ("quantity", "sr_no")),
        (RETURN_CHALLAN_TABLE, RETURN_CHALLAN_COLUMNS, ()),
        (RETURN_CHALLAN_ITEMS_TABLE, RETURN_CHALLAN_ITEMS_COLUMNS,
         ("quantity", "sr_no")),
    ]

    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futures = [pool.submit(_fetch_raw, s[0]) for s in specs]
        raw_results = [f.result() for f in futures]

    results = [
        _process(specs[i][1], specs[i][2], raw_results[i][0], raw_results[i][1])
        for i in range(len(specs))
    ]

    return tuple([r[0] for r in results] + [r[1] for r in results])


(
    items, production,
    opening, prod_qty, dispatch, return_qty, closing, adjustment,
    challans, challan_items, return_challans, return_challan_items,
    items_err, production_err,
    opening_err, prod_qty_err, dispatch_err, return_err,
    closing_err, adjustment_err,
    challans_err, challan_items_err,
    return_challans_err, return_challan_items_err
) = load_all_data()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def build_item_lookup(items_df):
    if items_df.empty:
        return {}
    lookup = {}
    for _, row in items_df.iterrows():
        iid = str(row.get("Item_ID", "") or "").strip()
        if not iid:
            continue
        parts = []

        def _add(val, prefix=""):
            if val is None:
                return
            try:
                if pd.isna(val):
                    return
            except Exception:
                pass
            s = str(val).strip()
            if not s or s in ("-", "nan", "None", "null"):
                return
            parts.append(f"{prefix}{s}" if prefix else s)

        _add(row.get("Material_Grade"))
        _add(row.get("Application"))
        _add(row.get("Nominal_Diameter_mm"))
        _add(row.get("Wall_Thickness_mm"), "WT ")
        _add(row.get("SDR"), "SDR ")
        _add(row.get("Color"))
        _add(row.get("Unit"))

        lookup[iid] = " | ".join(parts)
    return lookup


ITEM_LOOKUP = build_item_lookup(items)


def auto_description(item_id):
    if not item_id or item_id == "(none)":
        return ""
    return ITEM_LOOKUP.get(str(item_id), "")


def get_next_id(df, id_col, prefix):
    if df.empty or id_col not in df.columns:
        return f"{prefix}-001"
    nums = []
    for v in df[id_col].dropna().astype(str):
        tail = v[len(prefix) + 1:] if prefix and v.startswith(f"{prefix}-") else v
        try:
            nums.append(int(float(tail)))
        except (ValueError, TypeError):
            continue
    if not nums:
        return f"{prefix}-001"
    return f"{prefix}-{max(nums) + 1:03d}"


def next_id_for(table_name, df):
    id_col, prefix = ID_PREFIX[table_name]
    return get_next_id(df, id_col, prefix)


def next_challan_no(df, kind="DC"):
    today = date.today()
    prefix = f"{kind}-{today.year}-"
    if df.empty or "challan_no" not in df.columns:
        return f"{prefix}001"
    nums = []
    for v in df["challan_no"].dropna().astype(str):
        if v.startswith(prefix):
            try:
                nums.append(int(v[len(prefix):]))
            except ValueError:
                continue
    if not nums:
        return f"{prefix}001"
    return f"{prefix}{max(nums) + 1:03d}"


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def compute_stock_ledger(items_df, opening_df, prod_qty_df,
                         dispatch_df, return_df, adjustment_df):
    if items_df.empty:
        return pd.DataFrame(columns=[
            "Item_ID", "Item_Code", "Opening", "Produced",
            "Dispatched", "Returned", "Adjusted", "Closing"
        ])

    def _grp(df, name):
        if df is None or df.empty:
            return pd.DataFrame(columns=["Item_ID", name])
        return (df.groupby("Item_ID", as_index=False)["Qty"]
                  .sum().rename(columns={"Qty": name}))

    base = items_df[["Item_ID", "Item_Code"]].copy()
    for df, name in [
        (opening_df, "Opening"),
        (prod_qty_df, "Produced"),
        (dispatch_df, "Dispatched"),
        (return_df, "Returned"),
        (adjustment_df, "Adjusted"),
    ]:
        base = base.merge(_grp(df, name), on="Item_ID", how="left")

    base = base.fillna(0)
    base["Closing"] = (base["Opening"] + base["Produced"]
                       - base["Dispatched"] + base["Returned"]
                       + base["Adjusted"])
    return base


STOCK_LEDGER = compute_stock_ledger(
    items, opening, prod_qty, dispatch, return_qty, adjustment
)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def compute_totals(production, opening, prod_qty, dispatch,
                   return_qty, adjustment, stock_ledger):
    good = float(production["Good_Qty_m"].sum()) if not production.empty else 0.0
    rejected = float(production["Rejected_Qty_m"].sum()) if not production.empty else 0.0
    planned = float(production["Planned_Qty_m"].sum()) if not production.empty else 0.0
    total_out = good + rejected
    yield_pct = (good / total_out * 100) if total_out > 0 else 0.0

    return {
        "planned": planned, "good": good, "rejected": rejected,
        "yield_pct": yield_pct,
        "opening": float(opening["Qty"].sum()) if not opening.empty else 0.0,
        "prod_qty": float(prod_qty["Qty"].sum()) if not prod_qty.empty else 0.0,
        "dispatched": float(dispatch["Qty"].sum()) if not dispatch.empty else 0.0,
        "returned": float(return_qty["Qty"].sum()) if not return_qty.empty else 0.0,
        "adjusted": float(adjustment["Qty"].sum()) if not adjustment.empty else 0.0,
        "closing": float(stock_ledger["Closing"].sum()) if not stock_ledger.empty else 0.0,
    }


TOTALS = compute_totals(production, opening, prod_qty, dispatch,
                        return_qty, adjustment, STOCK_LEDGER)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_item_options(items_df):
    if items_df.empty:
        return []
    return items_df["Item_ID"].astype(str).tolist()


def refresh_all():
    load_all_data.clear()
    get_item_options.clear()
    compute_stock_ledger.clear()
    compute_totals.clear()
    build_item_lookup.clear()
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
        return f"Enable RLS policy for {action.upper()} on {table}."
    if "relation" in e and "does not exist" in e:
        return f"Table {table} missing in Supabase."
    if "column" in e and "does not exist" in e:
        return f"Column mismatch on {table}."
    if "duplicate key" in e or "unique constraint" in e:
        return f"Duplicate ID in {table}. Refresh and try again."
    if "foreign key" in e:
        return f"Foreign key violation on {table}."
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


@st.cache_data(show_spinner=False)
def get_logo_base64():
    for path in ["logo.png", "logo.jpg", "logo.jpeg"]:
        if os.path.exists(path):
            try:
                import base64
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                ext = path.split(".")[-1].lower().replace("jpg", "jpeg")
                return f"data:image/{ext};base64,{data}"
            except Exception:
                return None
    return None


LOGO_B64 = get_logo_base64()


def logo_html():
    if LOGO_B64:
        return f'<img src="{LOGO_B64}" style="width:130px;height:auto;display:block;margin:0 auto;" alt="Logo"/>'
    return """<svg viewBox="0 0 100 80" xmlns="http://www.w3.org/2000/svg"
                style="width:130px;height:auto;display:block;margin:0 auto;">
        <g fill="#000">
            <path d="M5 55 L25 25 L40 25 L20 55 Z"/>
            <path d="M30 60 L50 20 L65 20 L45 60 Z"/>
            <path d="M55 60 L75 25 L90 25 L70 60 Z"/>
        </g>
    </svg>"""


def build_challan_html(header_row, items_df, challan_title="DELIVERY CHALLAN"):
    challan_no = header_row.get("challan_no", "") or ""
    challan_date = fmt_date_only(header_row.get("challan_date", ""))

    def _clean(v):
        if v is None:
            return ""
        s = str(v).strip()
        if s.lower() in ("nan", "none", "null"):
            return ""
        return s

    customer_name = _clean(header_row.get("customer_name", ""))
    contact_detail = _clean(header_row.get("contact_detail", ""))
    project = _clean(header_row.get("project", ""))
    location = _clean(header_row.get("location", ""))
    sales_head = _clean(header_row.get("sales_head", ""))
    payment_terms = _clean(header_row.get("payment_terms", ""))
    vehicle_no_val = _clean(header_row.get("vehicle_no", ""))
    received_by_val = _clean(header_row.get("received_by", ""))
    sent_by_val = _clean(header_row.get("sent_by", ""))

    rows_html = ""
    MIN_ROWS = 15
    count = 0

    if items_df is not None and not items_df.empty:
        for _, r in items_df.iterrows():
            sr = r.get("sr_no", "")
            desc = r.get("description", "") or ""
            qty = r.get("quantity", "")
            unit = r.get("unit", "") or ""
            try:
                qty_str = f"{float(qty):,.2f}".rstrip("0").rstrip(".")
            except Exception:
                qty_str = str(qty)
            rows_html += f"""<tr>
                <td class="c">{sr}</td>
                <td>{desc}</td>
                <td class="c">{qty_str}</td>
                <td class="c">{unit}</td>
            </tr>"""
            count += 1

    for _ in range(max(0, MIN_ROWS - count)):
        rows_html += """<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>"""

    logo_markup = logo_html()

    def _sig_block(label, value):
        val_display = value if value else "&nbsp;"
        return f"""
        <div class="sig">
          <div class="sig-value">{val_display}</div>
          <div class="sig-line"></div>
          <div class="sig-label">{label}</div>
        </div>
        """

    def _cust_row(label, value):
        if not value:
            return ""
        return f'<div class="cust-item"><b>{label}:</b> <span>{value}</span></div>'

    customer_block = ""
    for lbl, val in [
        ("Customer Name", customer_name),
        ("Contact Detail", contact_detail),
        ("Project", project),
        ("Location", location),
        ("Sales Head", sales_head),
        ("Payment Terms", payment_terms),
    ]:
        customer_block += _cust_row(lbl, val)

    return f"""
<div id="challan-print" class="challan-page">
<style>
.challan-page{{font-family:Arial,Helvetica,sans-serif;color:#000;background:#fff;
padding:20px 25px;max-width:920px;margin:0 auto;font-size:12px;}}
.challan-page .hdr-center{{text-align:center;margin-bottom:10px;
padding-bottom:12px;border-bottom:2px solid #000;}}
.challan-page .logo-center{{text-align:center;margin-bottom:8px;}}
.challan-page .cname{{font-size:24px;font-weight:900;letter-spacing:1px;
margin:6px 0 6px 0;color:#000;}}
.challan-page .caddr{{font-size:10px;line-height:1.55;color:#000;}}
.challan-page .caddr-line{{margin:1px 0;}}
.challan-page .meta-row{{display:flex;justify-content:space-between;
font-size:12px;margin:12px 0 8px 0;gap:20px;padding:6px 0;}}
.challan-page .meta-row b{{font-weight:900;}}
.challan-page .meta-row span{{font-weight:400;}}
.challan-page .cust-box{{border:1px solid #000;padding:8px 12px;
margin:8px 0 12px 0;background:#f9f9f9;}}
.challan-page .cust-grid{{display:grid;
grid-template-columns:1fr 1fr 1fr;gap:6px 20px;font-size:11px;}}
.challan-page .cust-item{{line-height:1.5;}}
.challan-page .cust-item b{{font-weight:900;}}
.challan-page .bar{{background:#000;color:#fff;text-align:center;
font-weight:900;font-size:18px;letter-spacing:3px;padding:10px 0;
margin:10px 0 12px 0;}}
.challan-page table{{width:100%;border-collapse:collapse;font-size:11px;}}
.challan-page th,.challan-page td{{border:1px solid #000;padding:6px 8px;
vertical-align:middle;height:22px;}}
.challan-page th{{background:#f2f2f2;font-weight:900;text-transform:uppercase;
font-size:12px;padding:8px;text-align:center;}}
.challan-page td.c{{text-align:center;}}
.challan-page .ftr{{display:flex;justify-content:space-between;
margin-top:60px;font-size:11px;font-weight:900;gap:20px;}}
.challan-page .sig{{width:30%;text-align:center;}}
.challan-page .sig-value{{min-height:22px;font-size:12px;
font-weight:700;margin-bottom:6px;color:#000;padding-top:6px;}}
.challan-page .sig-line{{border-top:1.5px solid #000;margin:0 auto;width:100%;}}
.challan-page .sig-label{{text-transform:uppercase;letter-spacing:0.5px;
padding-top:5px;font-weight:900;}}
.challan-page .stamp-area{{margin-top:40px;display:flex;
justify-content:flex-end;}}
.challan-page .stamp-box{{width:180px;height:90px;border:1.5px dashed #555;
display:flex;align-items:center;justify-content:center;
color:#888;font-size:11px;font-weight:700;letter-spacing:1px;}}
@media print{{
  body *{{visibility:hidden;}}
  #challan-print, #challan-print *{{visibility:visible;}}
  #challan-print{{position:absolute;left:0;top:0;width:100%;padding:0;}}
  @page{{margin:12mm;}}
}}
</style>

<div class="hdr-center">
  <div class="logo-center">{logo_markup}</div>
  <div class="cname">{COMPANY_NAME}</div>
  <div class="caddr">
    <div class="caddr-line">{COMPANY_ADDR_LINE1}</div>
    <div class="caddr-line">{COMPANY_ADDR_LINE2}</div>
    <div class="caddr-line">{COMPANY_ADDR_LINE3}</div>
  </div>
</div>

<div class="meta-row">
  <div><b>Challan No:</b> <span>{challan_no}</span></div>
  <div><b>Date:</b> <span>{challan_date}</span></div>
</div>

<div class="cust-box">
  <div class="cust-grid">
    {customer_block if customer_block else '<div class="cust-item"><i>No customer details</i></div>'}
  </div>
</div>

<div class="bar">{challan_title}</div>

<table>
  <thead>
    <tr>
      <th style="width:12%;">SR NO</th>
      <th style="width:58%;">DESCRIPTION</th>
      <th style="width:15%;">QUANTITY</th>
      <th style="width:15%;">UNIT</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>

<div class="ftr">
  {_sig_block("Vehicle No", vehicle_no_val)}
  {_sig_block("Received By", received_by_val)}
  {_sig_block("Sent By", sent_by_val)}
</div>

<div class="stamp-area">
  <div class="stamp-box">STAMP</div>
</div>
</div>
"""


def build_printable_html_page(challan_html):
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Challan</title></head>
<body style="margin:0;background:#f5f5f5;">
<div style="text-align:center;padding:14px;background:#222;">
  <button onclick="window.print()"
    style="padding:12px 30px;font-size:16px;font-weight:bold;
           background:#ff4b4b;color:#fff;border:none;border-radius:6px;
           cursor:pointer;">
    Print / Save as PDF
  </button>
</div>
<div style="padding:20px;">
{challan_html}
</div>
</body>
</html>"""


def crud_stock_table(table_name, df, id_col, label, items_df, load_error=None):
    if load_error:
        st.error(f"Failed to load {label}: {load_error}")

    tab1, tab2, tab3 = st.tabs([f"View {label}", f"Add {label}", "Update / Delete"])

    with tab1:
        search = st.text_input(f"Search {label}", key=f"s_{table_name}",
                               placeholder=f"{id_col}, Item ID...")
        display = filter_df(df, search)
        if "Entry_Date" in display.columns:
            display = display.copy()
            display["Entry_Date"] = display["Entry_Date"].apply(fmt_date_only)
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
                c1, c2, c3 = st.columns(3)
                with c1:
                    selected_item = st.selectbox("Item ID", options,
                                                 key=f"ai_{table_name}")
                with c2:
                    qty = st.number_input("Quantity", min_value=0.0, value=0.0,
                                          step=1.0, key=f"aq_{table_name}")
                with c3:
                    entry_date = st.date_input("Entry Date", value=date.today(),
                                               key=f"ad_{table_name}")
                submit = st.form_submit_button(f"Add {label}", type="primary")

            if submit:
                try:
                    supabase.table(table_name).insert({
                        id_col: next_id,
                        "Item_ID": selected_item,
                        "Qty": qty,
                        "Entry_Date": date_str(entry_date)
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

        current_date = date.today()
        if "Entry_Date" in selected and pd.notna(selected["Entry_Date"]):
            try:
                current_date = pd.to_datetime(selected["Entry_Date"]).date()
            except Exception:
                pass

        with st.form(f"upd_{table_name}_form"):
            c1, c2, c3 = st.columns(3)
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
            with c3:
                edit_date = st.date_input("Entry Date", value=current_date,
                                          key=f"ed_{table_name}")
            update = st.form_submit_button("Update", type="primary")

        if update:
            try:
                supabase.table(table_name).update({
                    "Item_ID": edit_item, "Qty": edit_qty,
                    "Entry_Date": date_str(edit_date)
                }).eq(id_col, selected_id).execute()
                st.success(f"{label} updated.")
                refresh_all()
            except Exception as e:
                st.error("Update failed.")
                st.code(str(e))

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


def challan_items_editor(key_prefix):
    state_key = f"{key_prefix}_rows"
    counter_key = f"{key_prefix}_counter"

    if state_key not in st.session_state:
        st.session_state[state_key] = [
            {"id": 1, "item_id": "(none)", "description": "",
             "quantity": 0.0, "unit": "Meter"}
        ]
        st.session_state[counter_key] = 1

    item_options = get_item_options(items)
    rows = st.session_state[state_key]

    hc1, hc2, hc3, hc4, hc5 = st.columns([0.5, 2, 4, 2, 2])
    with hc1: st.markdown("**#**")
    with hc2: st.markdown("**Item ID**")
    with hc3: st.markdown("**Description (auto)**")
    with hc4: st.markdown("**Qty**")
    with hc5: st.markdown("**Unit**")

    to_remove = None

    for idx, row in enumerate(rows):
        rid = row["id"]
        c1, c2, c3, c4, c5 = st.columns([0.5, 2, 4, 2, 2])

        with c1:
            st.markdown(f"**{idx + 1}**")

        with c2:
            if item_options:
                opts = ["(none)"] + item_options
                cur = row.get("item_id", "(none)")
                pos = opts.index(cur) if cur in opts else 0
                new_val = st.selectbox(
                    "Item ID", opts, index=pos,
                    key=f"{key_prefix}_item_{rid}",
                    label_visibility="collapsed"
                )
                if new_val != cur:
                    row["item_id"] = new_val
                    row["description"] = auto_description(new_val)
                    st.rerun()
                else:
                    row["item_id"] = new_val
            else:
                row["item_id"] = st.text_input(
                    "Item ID", value=row.get("item_id", ""),
                    key=f"{key_prefix}_itemtxt_{rid}",
                    label_visibility="collapsed"
                )

        with c3:
            row["description"] = st.text_input(
                "Description", value=row.get("description", ""),
                key=f"{key_prefix}_desc_{rid}",
                label_visibility="collapsed"
            )

        with c4:
            row["quantity"] = st.number_input(
                "Qty", min_value=0.0,
                value=float(row.get("quantity", 0.0)),
                step=1.0,
                key=f"{key_prefix}_qty_{rid}",
                label_visibility="collapsed"
            )

        with c5:
            c5a, c5b = st.columns([3, 1])
            with c5a:
                row["unit"] = st.text_input(
                    "Unit", value=row.get("unit", "Meter"),
                    key=f"{key_prefix}_unit_{rid}",
                    label_visibility="collapsed"
                )
            with c5b:
                if st.button("✖", key=f"{key_prefix}_rm_{rid}",
                             help="Remove row"):
                    to_remove = idx

    if to_remove is not None:
        st.session_state[state_key].pop(to_remove)
        st.rerun()

    bc1, bc2 = st.columns([1, 5])
    with bc1:
        if st.button("+ Add Row", key=f"{key_prefix}_add"):
            st.session_state[counter_key] += 1
            st.session_state[state_key].append({
                "id": st.session_state[counter_key],
                "item_id": "(none)",
                "description": "",
                "quantity": 0.0,
                "unit": "Meter"
            })
            st.rerun()

    return st.session_state[state_key]


def reset_challan_rows(key_prefix):
    state_key = f"{key_prefix}_rows"
    counter_key = f"{key_prefix}_counter"
    st.session_state[state_key] = [
        {"id": 1, "item_id": "(none)", "description": "",
         "quantity": 0.0, "unit": "Meter"}
    ]
    st.session_state[counter_key] = 1


# =========================================================
# UNIVERSAL BULK IMPORT
# =========================================================

IMPORT_TARGETS = {
    "Item Registration": {
        "table": ITEM_TABLE,
        "columns": list(ITEM_COLUMNS),
        "auto_id_col": "Item_ID",
        "auto_id_prefix": "ITM",
        "has_auto_id": True,
    },
    "Production": {
        "table": PRODUCTION_TABLE,
        "columns": list(PRODUCTION_COLUMNS),
        "auto_id_col": "Production_ID",
        "auto_id_prefix": "PRD",
        "has_auto_id": True,
    },
    "Opening Stock": {
        "table": OPENING_TABLE,
        "columns": list(OPENING_COLUMNS),
        "auto_id_col": "Opening_Stock_ID",
        "auto_id_prefix": "OPN",
        "has_auto_id": True,
    },
    "Production Qty": {
        "table": PRODUCTION_QTY_TABLE,
        "columns": list(PRODUCTION_QTY_COLUMNS),
        "auto_id_col": "Production_ID",
        "auto_id_prefix": "PQT",
        "has_auto_id": True,
    },
    "Dispatch Qty": {
        "table": DISPATCH_TABLE,
        "columns": list(DISPATCH_COLUMNS),
        "auto_id_col": "Dispatch_ID",
        "auto_id_prefix": "DSP",
        "has_auto_id": True,
    },
    "Return Qty": {
        "table": RETURN_TABLE,
        "columns": list(RETURN_COLUMNS),
        "auto_id_col": "Return_ID",
        "auto_id_prefix": "RET",
        "has_auto_id": True,
    },
    "Closing Stock": {
        "table": CLOSING_TABLE,
        "columns": list(CLOSING_COLUMNS),
        "auto_id_col": "Closing_Stock_ID",
        "auto_id_prefix": "CLS",
        "has_auto_id": True,
    },
    "Stock Adjustment": {
        "table": ADJUSTMENT_TABLE,
        "columns": list(ADJUSTMENT_COLUMNS),
        "auto_id_col": "Adjustment_ID",
        "auto_id_prefix": "ADJ",
        "has_auto_id": True,
    },
    "Delivery Challan": {
        "table": CHALLAN_TABLE,
        "columns": list(CHALLAN_COLUMNS),
        "auto_id_col": "challan_id",
        "auto_id_prefix": "",
        "has_auto_id": False,
    },
    "Delivery Challan Items": {
        "table": CHALLAN_ITEMS_TABLE,
        "columns": list(CHALLAN_ITEMS_COLUMNS),
        "auto_id_col": "challan_item_id",
        "auto_id_prefix": "",
        "has_auto_id": False,
    },
    "Return Challan": {
        "table": RETURN_CHALLAN_TABLE,
        "columns": list(RETURN_CHALLAN_COLUMNS),
        "auto_id_col": "challan_id",
        "auto_id_prefix": "",
        "has_auto_id": False,
    },
    "Return Challan Items": {
        "table": RETURN_CHALLAN_ITEMS_TABLE,
        "columns": list(RETURN_CHALLAN_ITEMS_COLUMNS),
        "auto_id_col": "challan_item_id",
        "auto_id_prefix": "",
        "has_auto_id": False,
    },
}

NUMERIC_TARGETS = {
    "Production": ["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"],
    "Opening Stock": ["Qty"],
    "Production Qty": ["Qty"],
    "Dispatch Qty": ["Qty"],
    "Return Qty": ["Qty"],
    "Closing Stock": ["Qty"],
    "Stock Adjustment": ["Qty"],
    "Delivery Challan Items": ["quantity", "sr_no"],
    "Return Challan Items": ["quantity", "sr_no"],
}


def bulk_import_page():
    st.title("Bulk Import")
    st.caption("Upload CSV to import data into any ERP table.")

    st.markdown("---")
    st.markdown("#### 1. Select Target Table")
    target_name = st.selectbox("Which table do you want to import to?",
                                list(IMPORT_TARGETS.keys()),
                                key="bulk_target_select")

    cfg = IMPORT_TARGETS[target_name]
    target_table = cfg["table"]
    target_cols = cfg["columns"]
    auto_id_col = cfg["auto_id_col"]
    auto_id_prefix = cfg["auto_id_prefix"]
    has_auto_id = cfg["has_auto_id"]

    st.caption(f"**Target:** `{target_table}`")
    with st.expander("Expected CSV columns", expanded=False):
        st.code(", ".join(target_cols))

    st.markdown("---")
    st.markdown("#### 2. Upload CSV")
    uploaded = st.file_uploader("Choose CSV file", type=["csv"],
                                 key=f"csv_{target_name}")

    if uploaded is None:
        st.info("Please upload a CSV file to continue.")
        return

    try:
        df = pd.read_csv(uploaded, dtype=str).fillna("")
    except Exception as e:
        st.error(f"Failed to read CSV: {e}")
        return

    st.success(f"CSV loaded: **{len(df)} rows**")

    st.markdown("#### 3. Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.markdown("#### 4. Options")

    start_num = 1
    if has_auto_id:
        c1, c2 = st.columns(2)
        with c1:
            start_num = st.number_input(
                f"Start numbering for {auto_id_col} from",
                min_value=1, value=1, step=1,
                help=f"e.g. 1 → {auto_id_prefix}-001, 100 → {auto_id_prefix}-100"
            )
        with c2:
            st.info(f"New IDs: `{auto_id_prefix}-{int(start_num):03d}`, "
                    f"`{auto_id_prefix}-{int(start_num) + 1:03d}`, ...")

    def _clean(v):
        if v is None:
            return ""
        s = str(v).strip()
        if s.lower() in ("nan", "none", "null"):
            return ""
        return s

    payloads = []
    for idx, row in df.reset_index(drop=True).iterrows():
        record = {}

        if has_auto_id:
            record[auto_id_col] = f"{auto_id_prefix}-{int(start_num) + idx:03d}"

        for col in target_cols:
            if col == auto_id_col and has_auto_id:
                continue
            if col in df.columns:
                val = _clean(row.get(col, ""))
                if col in NUMERIC_TARGETS.get(target_name, []):
                    try:
                        val = float(val) if val != "" else 0.0
                    except Exception:
                        val = 0.0
                record[col] = val if val != "" else None

        payloads.append(record)

    st.markdown("#### 5. Preview (First 20 Rows)")
    preview_df = pd.DataFrame(payloads)
    st.dataframe(preview_df.head(20), use_container_width=True)
    st.caption(f"Total: {len(payloads)} records ready to insert.")

    st.markdown("---")
    st.markdown("#### 6. Insert")

    if st.button(f"Insert All Records into `{target_table}`",
                 type="primary",
                 key=f"bulk_insert_{target_name}"):
        progress = st.progress(0)
        status = st.empty()

        total = len(payloads)
        inserted = 0
        failed = 0
        errors_list = []

        BATCH = 50
        for i in range(0, total, BATCH):
            batch = payloads[i:i + BATCH]
            try:
                supabase.table(target_table).insert(batch).execute()
                inserted += len(batch)
                status.text(f"Inserted {inserted}/{total}")
                progress.progress(min(inserted / total, 1.0))
            except Exception as e:
                for p in batch:
                    try:
                        supabase.table(target_table).insert(p).execute()
                        inserted += 1
                    except Exception as ee:
                        failed += 1
                        id_val = p.get(auto_id_col, "?")
                        errors_list.append(f"{id_val}: {str(ee)[:120]}")
                status.text(f"Inserted {inserted}/{total} (some failed)")
                progress.progress(min((i + len(batch)) / total, 1.0))

        progress.progress(1.0)

        st.markdown("---")
        if failed == 0:
            st.success(f"✅ Successfully inserted **{inserted}** records "
                       f"into `{target_table}`.")
        else:
            st.warning(f"⚠️ Inserted: **{inserted}** | Failed: **{failed}**")

        if errors_list:
            with st.expander(f"Show {len(errors_list)} error(s)"):
                for e in errors_list[:50]:
                    st.code(e)

        refresh_all()



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
            "Bulk Import",
            "Production",
            "Stock Control",
            "Stock Adjustment",
            "Physical Check",
            "Delivery Challan",
            "Return Challan",
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
# PAGE ROUTING
# =========================================================

if page == "Executive Dashboard":
    st.title("Executive Dashboard")
    t = TOTALS

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Registered Items</div>
                <div class="metric-value">{len(items):,}</div>
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
                <div class="metric-caption">Available inventory</div>
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

    st.markdown("---")
    st.subheader("Stock Ledger")
    if not STOCK_LEDGER.empty:
        st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)
    else:
        empty_state("No ledger data available.")


elif page == "Bulk Import":
    bulk_import_page()


elif page == "Item Registration":
    st.title("Item Registration")

    if items_err:
        st.error(f"Failed to load Item table: {items_err}")

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Item", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Item",
                               placeholder="Item ID, Item Code, Material Grade...")
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
                material_grade = st.text_input("Material Grade")
                application = st.text_input("Application")
            with c2:
                diameter = st.text_input("Nominal Diameter (mm)")
                wall = st.text_input("Wall Thickness (mm)")
                sdr = st.text_input("SDR")
            with c3:
                color = st.text_input("Color")
                standard_length = st.text_input("Standard Length")
                unit = st.text_input("Unit", value="Meter")
            submit = st.form_submit_button("Add Item", type="primary")

        if submit:
            try:
                supabase.table(ITEM_TABLE).insert({
                    "Item_ID": next_item_id,
                    "Item_Code": item_code.strip(),
                    "Material_Grade": material_grade.strip(),
                    "Application": application.strip(),
                    "Nominal_Diameter_mm": diameter.strip(),
                    "Wall_Thickness_mm": wall.strip(),
                    "SDR": sdr.strip(),
                    "Color": color.strip(),
                    "Standard_Length": standard_length.strip(),
                    "Unit": unit.strip()
                }).execute()
                st.success(f"Item {next_item_id} added.")
                refresh_all()
            except Exception as e:
                st.error("Item add failed.")
                st.code(str(e))

    with tab3:
        if items.empty:
            st.info("No items available.")
        else:
            selected_id = st.selectbox("Select Item ID",
                                       items["Item_ID"].astype(str).tolist())
            selected = items.loc[items["Item_ID"].astype(str) == selected_id].iloc[0]

            def _v(col):
                v = selected.get(col)
                return str(v) if pd.notna(v) else ""

            with st.form("update_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_code = st.text_input("Item Code", value=_v("Item_Code"))
                    new_grade = st.text_input("Material Grade", value=_v("Material_Grade"))
                    new_application = st.text_input("Application", value=_v("Application"))
                with c2:
                    new_diameter = st.text_input("Nominal Diameter (mm)", value=_v("Nominal_Diameter_mm"))
                    new_wall = st.text_input("Wall Thickness (mm)", value=_v("Wall_Thickness_mm"))
                    new_sdr = st.text_input("SDR", value=_v("SDR"))
                with c3:
                    new_color = st.text_input("Color", value=_v("Color"))
                    new_length = st.text_input("Standard Length", value=_v("Standard_Length"))
                    new_unit = st.text_input("Unit", value=_v("Unit"))
                update = st.form_submit_button("Update Item", type="primary")

            if update:
                try:
                    supabase.table(ITEM_TABLE).update({
                        "Item_Code": new_code.strip(),
                        "Material_Grade": new_grade.strip(),
                        "Application": new_application.strip(),
                        "Nominal_Diameter_mm": new_diameter.strip(),
                        "Wall_Thickness_mm": new_wall.strip(),
                        "SDR": new_sdr.strip(),
                        "Color": new_color.strip(),
                        "Standard_Length": new_length.strip(),
                        "Unit": new_unit.strip()
                    }).eq("Item_ID", selected_id).execute()
                    st.success("Item updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))

            st.markdown("---")
            if st.button("Delete Item", type="secondary"):
                try:
                    supabase.table(ITEM_TABLE).delete().eq("Item_ID", selected_id).execute()
                    st.success("Item deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))


elif page == "Production":
    st.title("Production")

    if production_err:
        st.error(f"Failed to load Production: {production_err}")

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Production", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Production",
                               placeholder="Production ID, Item ID, Batch...")
        display = filter_df(production, search)
        if "Production_Date" in display.columns:
            display = display.copy()
            display["Production_Date"] = display["Production_Date"].apply(fmt_date_only)
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
                    production_line = st.selectbox("Production Line",
                                                   PRODUCTION_LINES)
                    planned_qty = st.number_input("Planned Quantity (m)",
                                                  min_value=1, value=1, step=1)
                    good_qty = st.number_input("Good Quantity (m)",
                                               min_value=0, value=0, step=1)
                with c3:
                    rejected_qty = st.number_input("Rejected Quantity (m)",
                                                   min_value=0, value=0, step=1)
                    status = st.selectbox("Production Status", PRODUCTION_STATUSES)
                submit = st.form_submit_button("Add Production", type="primary")

            if submit:
                try:
                    supabase.table(PRODUCTION_TABLE).insert({
                        "Production_ID": next_production_id,
                        "Item_ID": selected_item,
                        "Production_Date": date_str(production_date),
                        "Batch_No": batch_no.strip(),
                        "Production_Line": production_line,
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

    with tab3:
        if production.empty:
            st.info("No production records.")
        else:
            selected_id = st.selectbox("Select Production ID",
                production["Production_ID"].astype(str).tolist())
            selected = production.loc[
                production["Production_ID"].astype(str) == selected_id
            ].iloc[0]

            current_line = str(selected["Production_Line"]) if pd.notna(selected["Production_Line"]) else PRODUCTION_LINES[0]
            line_idx = PRODUCTION_LINES.index(current_line) if current_line in PRODUCTION_LINES else 0

            with st.form("update_production_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    edit_batch = st.text_input("Batch No",
                        value=str(selected["Batch_No"]) if pd.notna(selected["Batch_No"]) else "")
                    edit_line = st.selectbox("Production Line", PRODUCTION_LINES,
                                             index=line_idx)
                with c2:
                    edit_planned = st.number_input("Planned Quantity", min_value=1,
                        value=max(1, int(selected["Planned_Qty_m"])), step=1)
                    edit_good = st.number_input("Good Quantity", min_value=0,
                        value=max(0, int(selected["Good_Qty_m"])), step=1)
                with c3:
                    edit_rejected = st.number_input("Rejected Quantity", min_value=0,
                        value=max(0, int(selected["Rejected_Qty_m"])), step=1)
                    cs = str(selected["Production_Status"])
                    si = PRODUCTION_STATUSES.index(cs) if cs in PRODUCTION_STATUSES else 0
                    edit_status = st.selectbox("Production Status",
                                               PRODUCTION_STATUSES, index=si)
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

            if st.button("Delete Production"):
                try:
                    supabase.table(PRODUCTION_TABLE).delete().eq(
                        "Production_ID", selected_id).execute()
                    st.success("Production deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))


elif page == "Stock Control":
    st.title("Stock Control")

    stock_tabs = st.tabs([
        "Opening Stock", "Production Qty", "Dispatch Qty",
        "Return Qty", "Closing Stock"
    ])

    with stock_tabs[0]:
        crud_stock_table(OPENING_TABLE, opening, "Opening_Stock_ID",
                         "Opening Stock", items, opening_err)

    with stock_tabs[1]:
        crud_stock_table(PRODUCTION_QTY_TABLE, prod_qty, "Production_ID",
                         "Production Qty", items, prod_qty_err)

    with stock_tabs[2]:
        crud_stock_table(DISPATCH_TABLE, dispatch, "Dispatch_ID",
                         "Dispatch Qty", items, dispatch_err)

    with stock_tabs[3]:
        crud_stock_table(RETURN_TABLE, return_qty, "Return_ID",
                         "Return Qty", items, return_err)

    with stock_tabs[4]:
        st.markdown("### Closing Stock")
        if not STOCK_LEDGER.empty:
            ledger_view = STOCK_LEDGER.copy()
            ledger_view["Auto_Date"] = today_str()
            st.dataframe(ledger_view, use_container_width=True, hide_index=True)
        else:
            empty_state("No stock data available yet.")


elif page == "Stock Adjustment":
    st.title("Stock Adjustment")

    if adjustment_err:
        st.error(f"Failed to load Stock_Adjustment: {adjustment_err}")

    tab1, tab2, tab3 = st.tabs(["View Records", "Add Adjustment", "Update / Delete"])

    with tab1:
        search = st.text_input("Search Adjustment",
                               placeholder="Adjustment ID, Item ID, Reason...")
        display = filter_df(adjustment, search)
        if "Adjustment_Date" in display.columns:
            display = display.copy()
            display["Adjustment_Date"] = display["Adjustment_Date"].apply(fmt_date_only)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption(f"{len(display)} record(s)")

    with tab2:
        next_adj_id = next_id_for(ADJUSTMENT_TABLE, adjustment)
        st.info(f"Next Adjustment ID: {next_adj_id}")

        if items.empty:
            st.warning("Add an item first.")
        else:
            options = get_item_options(items)
            with st.form("add_adjustment_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    selected_item = st.selectbox("Item ID", options)
                    adj_date = st.date_input("Adjustment Date", value=date.today())
                with c2:
                    qty = st.number_input("Quantity (+/-)", value=0.0, step=1.0)
                    reason = st.selectbox("Reason", ADJUSTMENT_REASONS)
                with c3:
                    remarks = st.text_area("Remarks", height=100)
                submit = st.form_submit_button("Add Adjustment", type="primary")

            if submit:
                try:
                    supabase.table(ADJUSTMENT_TABLE).insert({
                        "Adjustment_ID": next_adj_id,
                        "Item_ID": selected_item,
                        "Adjustment_Date": date_str(adj_date),
                        "Qty": qty,
                        "Reason": reason,
                        "Remarks": remarks.strip()
                    }).execute()
                    st.success(f"Adjustment {next_adj_id} added.")
                    refresh_all()
                except Exception as e:
                    st.error("Failed.")
                    st.code(str(e))

    with tab3:
        if adjustment.empty:
            st.info("No adjustments.")
        else:
            selected_id = st.selectbox("Select Adjustment ID",
                adjustment["Adjustment_ID"].astype(str).tolist())
            selected = adjustment.loc[
                adjustment["Adjustment_ID"].astype(str) == selected_id
            ].iloc[0]

            options = get_item_options(items)
            ci = str(selected["Item_ID"]) if pd.notna(selected["Item_ID"]) else ""
            di = options.index(ci) if ci in options else 0

            current_adj_date = date.today()
            if pd.notna(selected["Adjustment_Date"]):
                try:
                    current_adj_date = pd.to_datetime(selected["Adjustment_Date"]).date()
                except Exception:
                    pass

            with st.form("update_adjustment_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    ei = st.selectbox("Item ID", options, index=di) if options else ci
                    ed = st.date_input("Adjustment Date", value=current_adj_date)
                with c2:
                    eq = st.number_input("Quantity",
                        value=float(selected["Qty"]) if pd.notna(selected["Qty"]) else 0.0,
                        step=1.0)
                    cr = str(selected["Reason"]) if pd.notna(selected["Reason"]) else "Other"
                    ri = ADJUSTMENT_REASONS.index(cr) if cr in ADJUSTMENT_REASONS else 4
                    er = st.selectbox("Reason", ADJUSTMENT_REASONS, index=ri)
                with c3:
                    em = st.text_area("Remarks",
                        value=str(selected["Remarks"]) if pd.notna(selected["Remarks"]) else "",
                        height=100)
                update = st.form_submit_button("Update", type="primary")

            if update:
                try:
                    supabase.table(ADJUSTMENT_TABLE).update({
                        "Item_ID": ei, "Adjustment_Date": date_str(ed),
                        "Qty": eq, "Reason": er, "Remarks": em.strip()
                    }).eq("Adjustment_ID", selected_id).execute()
                    st.success("Updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))

            if st.button("Delete Adjustment", type="secondary"):
                try:
                    supabase.table(ADJUSTMENT_TABLE).delete().eq(
                        "Adjustment_ID", selected_id).execute()
                    st.success("Deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))


elif page == "Physical Check":
    st.title("Physical Check")

    if STOCK_LEDGER.empty:
        empty_state("No stock data available yet.")
        st.stop()

    ledger = STOCK_LEDGER.copy()
    ledger = ledger.rename(columns={
        "Opening": "System_Opening", "Produced": "System_Produced",
        "Dispatched": "System_Dispatched", "Returned": "System_Returned",
        "Adjusted": "System_Adjusted", "Closing": "System_Closing",
    })

    st.subheader("Enter Physical Counts")

    with st.form("physical_check_form"):
        counts = {}
        for _, row in ledger.iterrows():
            iid = row["Item_ID"]
            icode = row["Item_Code"] if pd.notna(row["Item_Code"]) else ""
            sc = float(row["System_Closing"])

            c1, c2, c3 = st.columns([2, 2, 3])
            with c1:
                st.markdown(f"**{iid}**")
                st.caption(icode)
            with c2:
                st.metric("System Closing", f"{sc:,.0f}")
            with c3:
                counts[iid] = st.number_input("Physical Count", min_value=0.0,
                                              value=sc, step=1.0,
                                              key=f"pc_{iid}")
            st.markdown("---")

        submit = st.form_submit_button("Save Differences as Adjustments",
                                       type="primary")

    if submit:
        today = date.today()
        inserted = skipped = 0
        errors = []

        try:
            adj_resp = supabase.table(ADJUSTMENT_TABLE).select("*").execute()
            current_adj_df = make_df(adj_resp.data or [], ADJUSTMENT_COLUMNS)
        except Exception:
            current_adj_df = adjustment.copy()

        for _, row in ledger.iterrows():
            iid = row["Item_ID"]
            sc = float(row["System_Closing"])
            ph = float(counts.get(iid, sc))
            diff = ph - sc

            if abs(diff) < 0.0001:
                skipped += 1
                continue

            new_id = next_id_for(ADJUSTMENT_TABLE, current_adj_df)
            payload = {
                "Adjustment_ID": new_id, "Item_ID": iid,
                "Adjustment_Date": date_str(today), "Qty": diff,
                "Reason": "Physical Check",
                "Remarks": f"System {sc:.0f} vs Physical {ph:.0f}"
            }
            try:
                supabase.table(ADJUSTMENT_TABLE).insert(payload).execute()
                current_adj_df = pd.concat(
                    [current_adj_df, pd.DataFrame([payload])], ignore_index=True
                )
                inserted += 1
            except Exception as e:
                errors.append(f"{iid}: {e}")

        if inserted: st.success(f"{inserted} adjustment(s) created.")
        if skipped: st.info(f"{skipped} item(s) matched.")
        if errors:
            st.error("Some failed:")
            for e in errors: st.code(e)
        if inserted or skipped:
            st.balloons()
            refresh_all()


elif page == "Delivery Challan":
    st.title("Delivery Challan")

    if challans_err:
        st.error(f"Failed to load Delivery_Challan: {challans_err}")
    if challan_items_err:
        st.error(f"Failed to load Delivery_Challan_Items: {challan_items_err}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "View / Print", "Create", "Update / Delete", "Manage Items"
    ])

    with tab1:
        if challans.empty:
            st.info("No delivery challans yet.")
        else:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                search_dc = st.text_input("Search",
                    placeholder="Challan No, Customer, Location...",
                    key="search_dc")
            with c2:
                sort_by_dc = st.selectbox("Sort by",
                    ["Challan Date", "Challan ID", "Challan No"],
                    key="sortby_dc")
            with c3:
                sort_ord_dc = st.selectbox("Order",
                    ["Newest first", "Oldest first"],
                    key="sortorder_dc")

            display_dc = challans.copy()
            if search_dc:
                display_dc = filter_df(display_dc, search_dc)

            sort_col = None
            if sort_by_dc == "Challan Date":
                sort_col = "challan_date"
            elif sort_by_dc == "Challan ID":
                sort_col = "challan_id"
            elif sort_by_dc == "Challan No":
                sort_col = "challan_no"

            if sort_col and sort_col in display_dc.columns:
                try:
                    if sort_col == "challan_date":
                        display_dc[sort_col] = pd.to_datetime(
                            display_dc[sort_col], errors="coerce")
                    display_dc = display_dc.sort_values(
                        by=sort_col,
                        ascending=(sort_ord_dc == "Oldest first"),
                        na_position="last")
                except Exception:
                    pass

            if display_dc.empty:
                st.warning("No challans match the search.")
            else:
                left_col, right_col = st.columns([1, 1.6])

                with left_col:
                    st.markdown(f"#### {len(display_dc)} Challan(s)")

                    options_display = []
                    id_map = {}
                    for _, row in display_dc.iterrows():
                        no = str(row.get("challan_no", ""))
                        d = fmt_date_only(row.get("challan_date", ""))
                        cid = row.get("challan_id")
                        label = f"{no}  •  {d}"
                        options_display.append(label)
                        id_map[label] = cid

                    picked_label = st.radio("Challans",
                        options_display, key="pick_dc",
                        label_visibility="collapsed")
                    picked_id = id_map.get(picked_label)

                    picked_row = display_dc.loc[
                        display_dc["challan_id"] == picked_id
                    ].iloc[0]

                    items_for = challan_items[
                        challan_items["challan_id"] == picked_id
                    ].sort_values("sr_no")

                    st.markdown("---")
                    st.markdown(
                        f"**Challan No:** {picked_row.get('challan_no', '')}  \n"
                        f"**Date:** {fmt_date_only(picked_row.get('challan_date', ''))}  \n"
                        f"**Customer:** {picked_row.get('customer_name', '')}  \n"
                        f"**Contact:** {picked_row.get('contact_detail', '')}  \n"
                        f"**Project:** {picked_row.get('project', '')}  \n"
                        f"**Location:** {picked_row.get('location', '')}  \n"
                        f"**Sales Head:** {picked_row.get('sales_head', '')}  \n"
                        f"**Payment Terms:** {picked_row.get('payment_terms', '')}  \n"
                        f"**Items:** {len(items_for)}"
                    )

                with right_col:
                    st.markdown("#### Print / Download")
                    html = build_challan_html(picked_row, items_for,
                                              "DELIVERY CHALLAN")
                    c1, c2 = st.columns(2)
                    with c1:
                        printable = build_printable_html_page(html)
                        st.download_button("PDF (Print)",
                            data=printable.encode("utf-8"),
                            file_name=f"{picked_row.get('challan_no', 'dc')}_print.html",
                            mime="text/html",
                            use_container_width=True, key="pdf_dc")
                    with c2:
                        st.download_button("HTML",
                            data=html.encode("utf-8"),
                            file_name=f"{picked_row.get('challan_no', 'dc')}.html",
                            mime="text/html",
                            use_container_width=True, key="html_dc")

                    if not items_for.empty:
                        st.download_button("CSV (Items)",
                            data=items_for.to_csv(index=False).encode("utf-8"),
                            file_name=f"{picked_row.get('challan_no', 'dc')}_items.csv",
                            mime="text/csv",
                            use_container_width=True, key="csv_dc")
                        st.markdown("#### Items")
                        st.dataframe(items_for[
                            ["sr_no", "item_id", "description", "quantity", "unit"]
                        ], use_container_width=True, hide_index=True)

    with tab2:
        next_no_dc = next_challan_no(challans, "DC")
        st.info(f"Next Challan No: {next_no_dc}")

        st.markdown("#### Customer Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            cd_dc = st.date_input("Challan Date", value=date.today(), key="cd_dc")
            cn_dc = st.text_input("Customer Name", key="cn_dc")
            cdt_dc = st.text_input("Contact Detail", key="cdt_dc")
        with c2:
            pj_dc = st.text_input("Project", key="pj_dc")
            lc_dc = st.text_input("Location", key="lc_dc")
            sh_dc = st.text_input("Sales Head", key="sh_dc")
        with c3:
            pt_dc = st.text_input("Payment Terms", key="pt_dc")
            vn_dc = st.text_input("Vehicle No", key="vn_dc")
            rb_dc = st.text_input("Received By", key="rb_dc")
            sb_dc = st.text_input("Sent By", key="sb_dc")

        st.markdown("---")
        st.markdown("#### Items")
        item_rows_dc = challan_items_editor("create_dc")

        st.markdown("---")
        if st.button("Create Challan", type="primary", key="create_btn_dc"):
            if not cn_dc.strip():
                st.error("Customer Name required.")
            else:
                valid_dc = [r for r in item_rows_dc
                            if r["description"].strip() and r["quantity"] > 0]
                if not valid_dc:
                    st.error("At least one valid item row required.")
                else:
                    try:
                        hdr_dc = {
                            "challan_no": next_no_dc,
                            "challan_date": date_str(cd_dc),
                            "customer_name": cn_dc.strip(),
                            "contact_detail": cdt_dc.strip() or None,
                            "project": pj_dc.strip() or None,
                            "location": lc_dc.strip() or None,
                            "sales_head": sh_dc.strip() or None,
                            "payment_terms": pt_dc.strip() or None,
                            "vehicle_no": vn_dc.strip() or None,
                            "received_by": rb_dc.strip() or None,
                            "sent_by": sb_dc.strip() or None,
                        }
                        resp_dc = supabase.table(CHALLAN_TABLE).insert(hdr_dc).execute()
                        if resp_dc.data:
                            cid_dc = resp_dc.data[0]["challan_id"]
                            payloads_dc = []
                            for idx, r in enumerate(valid_dc, 1):
                                payloads_dc.append({
                                    "challan_id": cid_dc, "sr_no": idx,
                                    "item_id": r["item_id"] if r["item_id"] != "(none)" else None,
                                    "description": r["description"].strip(),
                                    "quantity": r["quantity"],
                                    "unit": (r["unit"] or "Meter").strip()
                                })
                            supabase.table(CHALLAN_ITEMS_TABLE).insert(payloads_dc).execute()
                            st.success(f"Challan {next_no_dc} created with {len(valid_dc)} item(s).")
                            reset_challan_rows("create_dc")
                            refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))

    with tab3:
        if challans.empty:
            st.info("No challans.")
        else:
            sel_no_dc = st.selectbox("Select Challan",
                challans["challan_no"].astype(str).tolist(), key="upd_dc")
            sel_row_dc = challans.loc[
                challans["challan_no"].astype(str) == sel_no_dc
            ].iloc[0]
            cid_dc2 = sel_row_dc["challan_id"]

            def _v_dc(col):
                v = sel_row_dc.get(col)
                return str(v) if pd.notna(v) else ""

            with st.form("upd_dc_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    d = date.today()
                    if pd.notna(sel_row_dc["challan_date"]):
                        try:
                            d = pd.to_datetime(sel_row_dc["challan_date"]).date()
                        except Exception:
                            d = date.today()
                    ed_dc = st.date_input("Challan Date", value=d, key="ed_dc")
                    ecn_dc = st.text_input("Customer Name", value=_v_dc("customer_name"), key="ecn_dc")
                    ecdt_dc = st.text_input("Contact Detail", value=_v_dc("contact_detail"), key="ecdt_dc")
                with c2:
                    epj_dc = st.text_input("Project", value=_v_dc("project"), key="epj_dc")
                    elc_dc = st.text_input("Location", value=_v_dc("location"), key="elc_dc")
                    esh_dc = st.text_input("Sales Head", value=_v_dc("sales_head"), key="esh_dc")
                with c3:
                    ept_dc = st.text_input("Payment Terms", value=_v_dc("payment_terms"), key="ept_dc")
                    evn_dc = st.text_input("Vehicle No", value=_v_dc("vehicle_no"), key="evn_dc")
                    erb_dc = st.text_input("Received By", value=_v_dc("received_by"), key="erb_dc")
                    esb_dc = st.text_input("Sent By", value=_v_dc("sent_by"), key="esb_dc")
                upd_dc = st.form_submit_button("Update Header", type="primary")

            if upd_dc:
                try:
                    supabase.table(CHALLAN_TABLE).update({
                        "challan_date": date_str(ed_dc),
                        "customer_name": ecn_dc.strip(),
                        "contact_detail": ecdt_dc.strip() or None,
                        "project": epj_dc.strip() or None,
                        "location": elc_dc.strip() or None,
                        "sales_head": esh_dc.strip() or None,
                        "payment_terms": ept_dc.strip() or None,
                        "vehicle_no": evn_dc.strip() or None,
                        "received_by": erb_dc.strip() or None,
                        "sent_by": esb_dc.strip() or None,
                    }).eq("challan_id", cid_dc2).execute()
                    st.success("Updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))

            if st.button("Delete Challan", type="secondary", key="del_dc"):
                try:
                    supabase.table(CHALLAN_TABLE).delete().eq(
                        "challan_id", cid_dc2).execute()
                    st.success("Deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Failed.")
                    st.code(str(e))

    with tab4:
        if challans.empty:
            st.info("No challans.")
        else:
            sel_no_dc2 = st.selectbox("Select Challan",
                challans["challan_no"].astype(str).tolist(), key="items_dc")
            sel_row_dc2 = challans.loc[
                challans["challan_no"].astype(str) == sel_no_dc2
            ].iloc[0]
            cid_dc3 = sel_row_dc2["challan_id"]

            cur_dc = challan_items[
                challan_items["challan_id"] == cid_dc3
            ].sort_values("sr_no")

            st.markdown(f"#### Items for {sel_no_dc2}")
            if cur_dc.empty:
                st.info("No items.")
                next_sr_dc = 1
            else:
                st.dataframe(cur_dc, use_container_width=True, hide_index=True)
                next_sr_dc = int(cur_dc["sr_no"].max()) + 1

            item_options_dc = get_item_options(items)
            with st.form("add_item_dc_form"):
                st.markdown("#### Add New Item")
                c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                with c1:
                    if item_options_dc:
                        ni_dc = st.selectbox("Item ID",
                            ["(none)"] + item_options_dc, key="add_ci_dc")
                    else:
                        ni_dc = st.text_input("Item ID", key="add_cit_dc")
                with c2:
                    auto_desc_dc = auto_description(ni_dc) if ni_dc != "(none)" else ""
                    nd_dc = st.text_input("Description", value=auto_desc_dc,
                                          key=f"add_cd_dc_{ni_dc}")
                with c3:
                    nq_dc = st.number_input("Qty", min_value=0.0, value=0.0,
                                            step=1.0, key="add_cq_dc")
                with c4:
                    nu_dc = st.text_input("Unit", value="Meter", key="add_cu_dc")
                ad_dc = st.form_submit_button("Add", type="primary")

            if ad_dc:
                if not nd_dc.strip() or nq_dc <= 0:
                    st.error("Desc + Qty required.")
                else:
                    try:
                        supabase.table(CHALLAN_ITEMS_TABLE).insert({
                            "challan_id": cid_dc3, "sr_no": next_sr_dc,
                            "item_id": ni_dc if ni_dc != "(none)" else None,
                            "description": nd_dc.strip(),
                            "quantity": nq_dc, "unit": nu_dc.strip() or "Meter"
                        }).execute()
                        st.success("Added.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))

            if not cur_dc.empty:
                st.markdown("---")
                st.markdown("#### Edit / Delete")
                eid_dc = st.selectbox("Select Item",
                    cur_dc["challan_item_id"].astype(str).tolist(),
                    key="edit_ci_sel_dc")
                er_dc = cur_dc.loc[
                    cur_dc["challan_item_id"].astype(str) == eid_dc
                ].iloc[0]

                with st.form("edit_item_dc_form"):
                    c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                    with c1:
                        ce_dc = str(er_dc["item_id"]) if pd.notna(er_dc["item_id"]) else "(none)"
                        if item_options_dc:
                            idx = item_options_dc.index(ce_dc) + 1 if ce_dc in item_options_dc else 0
                            ei_dc = st.selectbox("Item ID",
                                ["(none)"] + item_options_dc, index=idx,
                                key="edit_ci_dc")
                        else:
                            ei_dc = st.text_input("Item ID", value=ce_dc, key="edit_cit_dc")
                    with c2:
                        ed_dc = st.text_input("Description",
                            value=str(er_dc["description"]) if pd.notna(er_dc["description"]) else "",
                            key="edit_cd_dc")
                    with c3:
                        eq_dc = st.number_input("Qty", min_value=0.0,
                            value=float(er_dc["quantity"]) if pd.notna(er_dc["quantity"]) else 0.0,
                            step=1.0, key="edit_cq_dc")
                    with c4:
                        eu_dc = st.text_input("Unit",
                            value=str(er_dc["unit"]) if pd.notna(er_dc["unit"]) else "Meter",
                            key="edit_cu_dc")
                    sv_dc = st.form_submit_button("Save", type="primary")

                if sv_dc:
                    try:
                        supabase.table(CHALLAN_ITEMS_TABLE).update({
                            "item_id": ei_dc if ei_dc != "(none)" else None,
                            "description": ed_dc.strip(),
                            "quantity": eq_dc,
                            "unit": eu_dc.strip() or "Meter"
                        }).eq("challan_item_id", eid_dc).execute()
                        st.success("Updated.")
                        refresh_all()
                    except Exception as e:
                        st.error("Update failed.")
                        st.code(str(e))

                if st.button("Delete Item", type="secondary", key="del_ci_dc"):
                    try:
                        supabase.table(CHALLAN_ITEMS_TABLE).delete().eq(
                            "challan_item_id", eid_dc).execute()
                        st.success("Deleted.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))


elif page == "Return Challan":
    st.title("Return Challan")

    if return_challans_err:
        st.error(f"Failed to load Return_Challan: {return_challans_err}")
    if return_challan_items_err:
        st.error(f"Failed to load Return_Challan_Items: {return_challan_items_err}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "View / Print", "Create", "Update / Delete", "Manage Items"
    ])

    with tab1:
        if return_challans.empty:
            st.info("No return challans yet.")
        else:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                search_rc = st.text_input("Search",
                    placeholder="Challan No, Customer, Location...",
                    key="search_rc")
            with c2:
                sort_by_rc = st.selectbox("Sort by",
                    ["Challan Date", "Challan ID", "Challan No"],
                    key="sortby_rc")
            with c3:
                sort_ord_rc = st.selectbox("Order",
                    ["Newest first", "Oldest first"],
                    key="sortorder_rc")

            display_rc = return_challans.copy()
            if search_rc:
                display_rc = filter_df(display_rc, search_rc)

            sort_col_rc = None
            if sort_by_rc == "Challan Date":
                sort_col_rc = "challan_date"
            elif sort_by_rc == "Challan ID":
                sort_col_rc = "challan_id"
            elif sort_by_rc == "Challan No":
                sort_col_rc = "challan_no"

            if sort_col_rc and sort_col_rc in display_rc.columns:
                try:
                    if sort_col_rc == "challan_date":
                        display_rc[sort_col_rc] = pd.to_datetime(
                            display_rc[sort_col_rc], errors="coerce")
                    display_rc = display_rc.sort_values(
                        by=sort_col_rc,
                        ascending=(sort_ord_rc == "Oldest first"),
                        na_position="last")
                except Exception:
                    pass

            if display_rc.empty:
                st.warning("No challans match the search.")
            else:
                left_col_rc, right_col_rc = st.columns([1, 1.6])

                with left_col_rc:
                    st.markdown(f"#### {len(display_rc)} Challan(s)")

                    options_display_rc = []
                    id_map_rc = {}
                    for _, row in display_rc.iterrows():
                        no = str(row.get("challan_no", ""))
                        d = fmt_date_only(row.get("challan_date", ""))
                        cid = row.get("challan_id")
                        label = f"{no}  •  {d}"
                        options_display_rc.append(label)
                        id_map_rc[label] = cid

                    picked_label_rc = st.radio("Challans",
                        options_display_rc, key="pick_rc",
                        label_visibility="collapsed")
                    picked_id_rc = id_map_rc.get(picked_label_rc)

                    picked_row_rc = display_rc.loc[
                        display_rc["challan_id"] == picked_id_rc
                    ].iloc[0]

                    items_for_rc = return_challan_items[
                        return_challan_items["challan_id"] == picked_id_rc
                    ].sort_values("sr_no")

                    st.markdown("---")
                    st.markdown(
                        f"**Challan No:** {picked_row_rc.get('challan_no', '')}  \n"
                        f"**Date:** {fmt_date_only(picked_row_rc.get('challan_date', ''))}  \n"
                        f"**Customer:** {picked_row_rc.get('customer_name', '')}  \n"
                        f"**Contact:** {picked_row_rc.get('contact_detail', '')}  \n"
                        f"**Project:** {picked_row_rc.get('project', '')}  \n"
                        f"**Location:** {picked_row_rc.get('location', '')}  \n"
                        f"**Sales Head:** {picked_row_rc.get('sales_head', '')}  \n"
                        f"**Payment Terms:** {picked_row_rc.get('payment_terms', '')}  \n"
                        f"**Items:** {len(items_for_rc)}"
                    )

                with right_col_rc:
                    st.markdown("#### Print / Download")
                    html_rc = build_challan_html(picked_row_rc, items_for_rc,
                                                 "RETURN CHALLAN")
                    c1, c2 = st.columns(2)
                    with c1:
                        printable_rc = build_printable_html_page(html_rc)
                        st.download_button("PDF (Print)",
                            data=printable_rc.encode("utf-8"),
                            file_name=f"{picked_row_rc.get('challan_no', 'rc')}_print.html",
                            mime="text/html",
                            use_container_width=True, key="pdf_rc")
                    with c2:
                        st.download_button("HTML",
                            data=html_rc.encode("utf-8"),
                            file_name=f"{picked_row_rc.get('challan_no', 'rc')}.html",
                            mime="text/html",
                            use_container_width=True, key="html_rc")

                    if not items_for_rc.empty:
                        st.download_button("CSV (Items)",
                            data=items_for_rc.to_csv(index=False).encode("utf-8"),
                            file_name=f"{picked_row_rc.get('challan_no', 'rc')}_items.csv",
                            mime="text/csv",
                            use_container_width=True, key="csv_rc")
                        st.markdown("#### Items")
                        st.dataframe(items_for_rc[
                            ["sr_no", "item_id", "description", "quantity", "unit"]
                        ], use_container_width=True, hide_index=True)

    with tab2:
        next_no_rc = next_challan_no(return_challans, "RC")
        st.info(f"Next Challan No: {next_no_rc}")

        st.markdown("#### Customer Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            cd_rc = st.date_input("Challan Date", value=date.today(), key="cd_rc")
            cn_rc = st.text_input("Customer Name", key="cn_rc")
            cdt_rc = st.text_input("Contact Detail", key="cdt_rc")
        with c2:
            pj_rc = st.text_input("Project", key="pj_rc")
            lc_rc = st.text_input("Location", key="lc_rc")
            sh_rc = st.text_input("Sales Head", key="sh_rc")
        with c3:
            pt_rc = st.text_input("Payment Terms", key="pt_rc")
            vn_rc = st.text_input("Vehicle No", key="vn_rc")
            rb_rc = st.text_input("Received By", key="rb_rc")
            sb_rc = st.text_input("Sent By", key="sb_rc")

        st.markdown("---")
        st.markdown("#### Items")
        item_rows_rc = challan_items_editor("create_rc")

        st.markdown("---")
        if st.button("Create Challan", type="primary", key="create_btn_rc"):
            if not cn_rc.strip():
                st.error("Customer Name required.")
            else:
                valid_rc = [r for r in item_rows_rc
                            if r["description"].strip() and r["quantity"] > 0]
                if not valid_rc:
                    st.error("At least one valid item row required.")
                else:
                    try:
                        hdr_rc = {
                            "challan_no": next_no_rc,
                            "challan_date": date_str(cd_rc),
                            "customer_name": cn_rc.strip(),
                            "contact_detail": cdt_rc.strip() or None,
                            "project": pj_rc.strip() or None,
                            "location": lc_rc.strip() or None,
                            "sales_head": sh_rc.strip() or None,
                            "payment_terms": pt_rc.strip() or None,
                            "vehicle_no": vn_rc.strip() or None,
                            "received_by": rb_rc.strip() or None,
                            "sent_by": sb_rc.strip() or None,
                        }
                        resp_rc = supabase.table(RETURN_CHALLAN_TABLE).insert(hdr_rc).execute()
                        if resp_rc.data:
                            cid_rc = resp_rc.data[0]["challan_id"]
                            payloads_rc = []
                            for idx, r in enumerate(valid_rc, 1):
                                payloads_rc.append({
                                    "challan_id": cid_rc, "sr_no": idx,
                                    "item_id": r["item_id"] if r["item_id"] != "(none)" else None,
                                    "description": r["description"].strip(),
                                    "quantity": r["quantity"],
                                    "unit": (r["unit"] or "Meter").strip()
                                })
                            supabase.table(RETURN_CHALLAN_ITEMS_TABLE).insert(payloads_rc).execute()
                            st.success(f"Challan {next_no_rc} created with {len(valid_rc)} item(s).")
                            reset_challan_rows("create_rc")
                            refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))

    with tab3:
        if return_challans.empty:
            st.info("No challans.")
        else:
            sel_no_rc = st.selectbox("Select Challan",
                return_challans["challan_no"].astype(str).tolist(), key="upd_rc")
            sel_row_rc = return_challans.loc[
                return_challans["challan_no"].astype(str) == sel_no_rc
            ].iloc[0]
            cid_rc2 = sel_row_rc["challan_id"]

            def _v_rc(col):
                v = sel_row_rc.get(col)
                return str(v) if pd.notna(v) else ""

            with st.form("upd_rc_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    d = date.today()
                    if pd.notna(sel_row_rc["challan_date"]):
                        try:
                            d = pd.to_datetime(sel_row_rc["challan_date"]).date()
                        except Exception:
                            d = date.today()
                    ed_rc = st.date_input("Challan Date", value=d, key="ed_rc")
                    ecn_rc = st.text_input("Customer Name", value=_v_rc("customer_name"), key="ecn_rc")
                    ecdt_rc = st.text_input("Contact Detail", value=_v_rc("contact_detail"), key="ecdt_rc")
                with c2:
                    epj_rc = st.text_input("Project", value=_v_rc("project"), key="epj_rc")
                    elc_rc = st.text_input("Location", value=_v_rc("location"), key="elc_rc")
                    esh_rc = st.text_input("Sales Head", value=_v_rc("sales_head"), key="esh_rc")
                with c3:
                    ept_rc = st.text_input("Payment Terms", value=_v_rc("payment_terms"), key="ept_rc")
                    evn_rc = st.text_input("Vehicle No", value=_v_rc("vehicle_no"), key="evn_rc")
                    erb_rc = st.text_input("Received By", value=_v_rc("received_by"), key="erb_rc")
                    esb_rc = st.text_input("Sent By", value=_v_rc("sent_by"), key="esb_rc")
                upd_rc = st.form_submit_button("Update Header", type="primary")

            if upd_rc:
                try:
                    supabase.table(RETURN_CHALLAN_TABLE).update({
                        "challan_date": date_str(ed_rc),
                        "customer_name": ecn_rc.strip(),
                        "contact_detail": ecdt_rc.strip() or None,
                        "project": epj_rc.strip() or None,
                        "location": elc_rc.strip() or None,
                        "sales_head": esh_rc.strip() or None,
                        "payment_terms": ept_rc.strip() or None,
                        "vehicle_no": evn_rc.strip() or None,
                        "received_by": erb_rc.strip() or None,
                        "sent_by": esb_rc.strip() or None,
                    }).eq("challan_id", cid_rc2).execute()
                    st.success("Updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))

            if st.button("Delete Challan", type="secondary", key="del_rc"):
                try:
                    supabase.table(RETURN_CHALLAN_TABLE).delete().eq(
                        "challan_id", cid_rc2).execute()
                    st.success("Deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Failed.")
                    st.code(str(e))

    with tab4:
        if return_challans.empty:
            st.info("No challans.")
        else:
            sel_no_rc2 = st.selectbox("Select Challan",
                return_challans["challan_no"].astype(str).tolist(), key="items_rc")
            sel_row_rc2 = return_challans.loc[
                return_challans["challan_no"].astype(str) == sel_no_rc2
            ].iloc[0]
            cid_rc3 = sel_row_rc2["challan_id"]

            cur_rc = return_challan_items[
                return_challan_items["challan_id"] == cid_rc3
            ].sort_values("sr_no")

            st.markdown(f"#### Items for {sel_no_rc2}")
            if cur_rc.empty:
                st.info("No items.")
                next_sr_rc = 1
            else:
                st.dataframe(cur_rc, use_container_width=True, hide_index=True)
                next_sr_rc = int(cur_rc["sr_no"].max()) + 1

            item_options_rc = get_item_options(items)
            with st.form("add_item_rc_form"):
                st.markdown("#### Add New Item")
                c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                with c1:
                    if item_options_rc:
                        ni_rc = st.selectbox("Item ID",
                            ["(none)"] + item_options_rc, key="add_ci_rc")
                    else:
                        ni_rc = st.text_input("Item ID", key="add_cit_rc")
                with c2:
                    auto_desc_rc = auto_description(ni_rc) if ni_rc != "(none)" else ""
                    nd_rc = st.text_input("Description", value=auto_desc_rc,
                                          key=f"add_cd_rc_{ni_rc}")
                with c3:
                    nq_rc = st.number_input("Qty", min_value=0.0, value=0.0,
                                            step=1.0, key="add_cq_rc")
                with c4:
                    nu_rc = st.text_input("Unit", value="Meter", key="add_cu_rc")
                ad_rc = st.form_submit_button("Add", type="primary")

            if ad_rc:
                if not nd_rc.strip() or nq_rc <= 0:
                    st.error("Desc + Qty required.")
                else:
                    try:
                        supabase.table(RETURN_CHALLAN_ITEMS_TABLE).insert({
                            "challan_id": cid_rc3, "sr_no": next_sr_rc,
                            "item_id": ni_rc if ni_rc != "(none)" else None,
                            "description": nd_rc.strip(),
                            "quantity": nq_rc, "unit": nu_rc.strip() or "Meter"
                        }).execute()
                        st.success("Added.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))

            if not cur_rc.empty:
                st.markdown("---")
                st.markdown("#### Edit / Delete")
                eid_rc = st.selectbox("Select Item",
                    cur_rc["challan_item_id"].astype(str).tolist(),
                    key="edit_ci_sel_rc")
                er_rc = cur_rc.loc[
                    cur_rc["challan_item_id"].astype(str) == eid_rc
                ].iloc[0]

                with st.form("edit_item_rc_form"):
                    c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                    with c1:
                        ce_rc = str(er_rc["item_id"]) if pd.notna(er_rc["item_id"]) else "(none)"
                        if item_options_rc:
                            idx = item_options_rc.index(ce_rc) + 1 if ce_rc in item_options_rc else 0
                            ei_rc = st.selectbox("Item ID",
                                ["(none)"] + item_options_rc, index=idx,
                                key="edit_ci_rc")
                        else:
                            ei_rc = st.text_input("Item ID", value=ce_rc, key="edit_cit_rc")
                    with c2:
                        ed_rc = st.text_input("Description",
                            value=str(er_rc["description"]) if pd.notna(er_rc["description"]) else "",
                            key="edit_cd_rc")
                    with c3:
                        eq_rc = st.number_input("Qty", min_value=0.0,
                            value=float(er_rc["quantity"]) if pd.notna(er_rc["quantity"]) else 0.0,
                            step=1.0, key="edit_cq_rc")
                    with c4:
                        eu_rc = st.text_input("Unit",
                            value=str(er_rc["unit"]) if pd.notna(er_rc["unit"]) else "Meter",
                            key="edit_cu_rc")
                    sv_rc = st.form_submit_button("Save", type="primary")

                if sv_rc:
                    try:
                        supabase.table(RETURN_CHALLAN_ITEMS_TABLE).update({
                            "item_id": ei_rc if ei_rc != "(none)" else None,
                            "description": ed_rc.strip(),
                            "quantity": eq_rc,
                            "unit": eu_rc.strip() or "Meter"
                        }).eq("challan_item_id", eid_rc).execute()
                        st.success("Updated.")
                        refresh_all()
                    except Exception as e:
                        st.error("Update failed.")
                        st.code(str(e))

                if st.button("Delete Item", type="secondary", key="del_ci_rc"):
                    try:
                        supabase.table(RETURN_CHALLAN_ITEMS_TABLE).delete().eq(
                            "challan_item_id", eid_rc).execute()
                        st.success("Deleted.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))


elif page == "Analytics":
    st.title("Analytics")

    st.subheader("Production Performance")
    if not production.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Planned", f"{TOTALS['planned']:,.0f} m")
        c2.metric("Good", f"{TOTALS['good']:,.0f} m")
        c3.metric("Rejected", f"{TOTALS['rejected']:,.0f} m")


elif page == "Custom Charts":
    st.title("Custom Charts")

    sources = {
        "Production": production,
        "Item Registration": items,
        "Opening Stock": opening,
        "Production Qty": prod_qty,
        "Dispatch Qty": dispatch,
        "Return Qty": return_qty,
        "Stock Adjustment": adjustment,
        "Stock Ledger": STOCK_LEDGER,
        "Delivery Challan": challans,
        "Delivery Challan Items": challan_items,
        "Return Challan": return_challans,
        "Return Challan Items": return_challan_items,
    }

    src = st.selectbox("Select a dataset", list(sources.keys()))
    df_chart = sources[src].copy()

    if df_chart.empty:
        empty_state(f"{src} has no records.")
        st.stop()

    num_cols = [c for c in df_chart.columns
                if pd.api.types.is_numeric_dtype(df_chart[c])]
    all_cols = df_chart.columns.tolist()

    cht = st.selectbox("Chart Type",
        ["Bar Chart", "Grouped Bar Chart", "Stacked Bar Chart",
         "Line Chart", "Area Chart", "Pie Chart", "Donut Chart",
         "Scatter Plot", "Histogram", "Box Plot"])

    c1, c2, c3 = st.columns(3)
    with c1:
        dx = "Item_ID" if "Item_ID" in all_cols else all_cols[0]
        x = st.selectbox("X-axis", all_cols, index=all_cols.index(dx))
    with c2:
        y = st.selectbox("Y-axis", num_cols if num_cols else ["(no numeric)"])
    with c3:
        cb = st.selectbox("Color / Group by", ["(none)"] + all_cols)

    try:
        if cht == "Bar Chart":
            fig = px.bar(df_chart, x=x, y=y,
                         color=(cb if cb != "(none)" else None), text_auto=True)
        elif cht == "Grouped Bar Chart":
            fig = px.bar(df_chart, x=x, y=y,
                         color=(cb if cb != "(none)" else None), barmode="group")
        elif cht == "Stacked Bar Chart":
            fig = px.bar(df_chart, x=x, y=y,
                         color=(cb if cb != "(none)" else None), barmode="stack")
        elif cht == "Line Chart":
            fig = px.line(df_chart, x=x, y=y,
                          color=(cb if cb != "(none)" else None), markers=True)
        elif cht == "Area Chart":
            fig = px.area(df_chart, x=x, y=y,
                          color=(cb if cb != "(none)" else None))
        elif cht == "Pie Chart":
            fig = px.pie(df_chart, names=x, values=y)
        elif cht == "Donut Chart":
            fig = px.pie(df_chart, names=x, values=y, hole=0.5)
        elif cht == "Scatter Plot":
            fig = px.scatter(df_chart, x=x, y=y,
                             color=(cb if cb != "(none)" else None))
        elif cht == "Histogram":
            fig = px.histogram(df_chart, x=x,
                               color=(cb if cb != "(none)" else None))
        elif cht == "Box Plot":
            fig = px.box(df_chart, x=x, y=y,
                         color=(cb if cb != "(none)" else None))
        else:
            fig = None

        if fig is not None:
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=520)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error("Chart error.")
        st.code(str(e))


elif page == "Data Management":
    st.title("Data Management")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items", len(items))
    c2.metric("Production", len(production))
    c3.metric("Delivery Challans", len(challans))
    c4.metric("Return Challans", len(return_challans))

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
        ("Delivery Challan", challans),
        ("Delivery Challan Items", challan_items),
        ("Return Challan", return_challans),
        ("Return Challan Items", return_challan_items),
    ]:
        st.subheader(label)
        st.dataframe(frame, use_container_width=True, hide_index=True)


st.markdown("---")
st.caption("Flex Head Industries Pvt Ltd | ERP Management System")
