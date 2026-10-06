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
    "challan_id", "challan_no", "challan_date", "sent_to",
    "vehicle_no", "received_by", "sent_by", "created_at"
)
CHALLAN_ITEMS_COLUMNS = (
    "challan_item_id", "challan_id", "sr_no",
    "item_id", "description", "quantity", "unit", "created_at"
)
RETURN_CHALLAN_COLUMNS = (
    "challan_id", "challan_no", "challan_date", "sent_to",
    "vehicle_no", "received_by", "sent_by", "created_at"
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
    """Logo markup — MEDIUM size (130px), left aligned."""
    if LOGO_B64:
        return f'<img src="{LOGO_B64}" style="width:130px;height:auto;display:block;" alt="Logo"/>'
    return """<svg viewBox="0 0 100 80" xmlns="http://www.w3.org/2000/svg"
                style="width:130px;height:auto;display:block;">
        <g fill="#000">
            <path d="M5 55 L25 25 L40 25 L20 55 Z"/>
            <path d="M30 60 L50 20 L65 20 L45 60 Z"/>
            <path d="M55 60 L75 25 L90 25 L70 60 Z"/>
        </g>
    </svg>"""


def build_challan_html(header_row, items_df, challan_title="DELIVERY CHALLAN"):
    challan_no = header_row.get("challan_no", "") or ""
    challan_date = fmt_date_only(header_row.get("challan_date", ""))
    sent_to = header_row.get("sent_to", "") or ""

    def _clean(v):
        if v is None:
            return ""
        s = str(v).strip()
        if s.lower() in ("nan", "none", "null"):
            return ""
        return s

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

    return f"""
<div id="challan-print" class="challan-page">
<style>
.challan-page{{font-family:Arial,Helvetica,sans-serif;color:#000;background:#fff;
padding:20px 25px;max-width:920px;margin:0 auto;font-size:12px;}}

/* ---- LEFT-SIDE LOGO HEADER ---- */
.challan-page .hdr-flex{{display:flex;align-items:center;gap:16px;
margin-bottom:10px;padding-bottom:12px;border-bottom:2px solid #000;}}
.challan-page .logo-left{{width:130px;flex-shrink:0;text-align:left;}}
.challan-page .logo-left img{{width:130px;height:auto;display:block;}}
.challan-page .company-info{{flex:1;text-align:left;}}
.challan-page .cname{{font-size:24px;font-weight:900;letter-spacing:1px;
margin:0 0 6px 0;color:#000;}}
.challan-page .caddr{{font-size:10px;line-height:1.55;color:#000;}}
.challan-page .caddr-line{{margin:1px 0;}}

/* ---- META ROW ---- */
.challan-page .meta-row{{display:flex;justify-content:space-between;
font-size:12px;margin:12px 0 10px 0;gap:20px;padding:8px 0;
border-top:1px solid #000;border-bottom:1px solid #000;}}
.challan-page .meta-row b{{font-weight:900;}}
.challan-page .meta-row span{{font-weight:400;}}

/* ---- TITLE BAR ---- */
.challan-page .bar{{background:#000;color:#fff;text-align:center;
font-weight:900;font-size:18px;letter-spacing:3px;padding:10px 0;
margin:8px 0 12px 0;}}

/* ---- TABLE ---- */
.challan-page table{{width:100%;border-collapse:collapse;font-size:11px;}}
.challan-page th,.challan-page td{{border:1px solid #000;padding:6px 8px;
vertical-align:middle;height:22px;}}
.challan-page th{{background:#f2f2f2;font-weight:900;text-transform:uppercase;
font-size:12px;padding:8px;text-align:center;}}
.challan-page td.c{{text-align:center;}}

/* ---- FOOTER ---- */
.challan-page .ftr{{display:flex;justify-content:space-between;
margin-top:60px;font-size:11px;font-weight:900;gap:20px;}}
.challan-page .sig{{width:30%;text-align:center;}}
.challan-page .sig-value{{min-height:22px;font-size:12px;
font-weight:700;margin-bottom:6px;color:#000;padding-top:6px;}}
.challan-page .sig-line{{border-top:1.5px solid #000;margin:0 auto;width:100%;}}
.challan-page .sig-label{{text-transform:uppercase;letter-spacing:0.5px;
padding-top:5px;font-weight:900;}}

@media print{{
  body *{{visibility:hidden;}}
  #challan-print, #challan-print *{{visibility:visible;}}
  #challan-print{{position:absolute;left:0;top:0;width:100%;padding:0;}}
  @page{{margin:12mm;}}
}}
</style>

<div class="hdr-flex">
  <div class="logo-left">{logo_markup}</div>
  <div class="company-info">
    <div class="cname">{COMPANY_NAME}</div>
    <div class="caddr">
      <div class="caddr-line">{COMPANY_ADDR_LINE1}</div>
      <div class="caddr-line">{COMPANY_ADDR_LINE2}</div>
      <div class="caddr-line">{COMPANY_ADDR_LINE3}</div>
    </div>
  </div>
</div>

<div class="meta-row">
  <div><b>Challan No:</b> <span>{challan_no}</span></div>
  <div><b>Date:</b> <span>{challan_date}</span></div>
  <div><b>Sent To:</b> <span>{sent_to}</span></div>
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


def render_challan_png(html_content, output_filename="challan.png"):
    try:
        from html2image import Html2Image
        hti = Html2Image(
            output_path="/tmp",
            size=(1200, 1700),
            custom_flags=["--no-sandbox", "--disable-gpu"]
        )
        hti.screenshot(html_str=html_content, save_as=output_filename)
        path = f"/tmp/{output_filename}"
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
    except Exception:
        return None
    return None


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
    with hc3: st.markdown("**Description**")
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
                row["item_id"] = st.selectbox(
                    "Item ID", opts, index=pos,
                    key=f"{key_prefix}_item_{rid}",
                    label_visibility="collapsed"
                )
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


def render_challan_module(
    page_title, challan_table, challan_items_table,
    challan_df, challan_items_df,
    challan_no_prefix, challan_title,
    challans_load_err, items_load_err,
    widget_key_suffix
):
    st.title(page_title)

    if challans_load_err:
        st.error(f"Failed to load {challan_table}: {challans_load_err}")
    if items_load_err:
        st.error(f"Failed to load {challan_items_table}: {items_load_err}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "View / Print", "Create", "Update / Delete", "Manage Items"
    ])

    with tab1:
        if challan_df.empty:
            st.info(f"No {page_title.lower()} records yet.")
        else:
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                search = st.text_input(
                    "Search",
                    placeholder="Challan No, Sent To, Vehicle No...",
                    key=f"search_{widget_key_suffix}"
                )
            with c2:
                sort_by = st.selectbox(
                    "Sort by",
                    ["Challan Date", "Challan No", "Challan ID"],
                    key=f"sortby_{widget_key_suffix}"
                )
            with c3:
                sort_order = st.selectbox(
                    "Order",
                    ["Newest first", "Oldest first"],
                    key=f"sortorder_{widget_key_suffix}"
                )

            display = challan_df.copy()
            if search:
                display = filter_df(display, search)

            sort_col = None
            if sort_by == "Challan Date":
                sort_col = "challan_date"
            elif sort_by == "Challan No":
                sort_col = "challan_no"
            elif sort_by == "Challan ID":
                sort_col = "challan_id"

            if sort_col and sort_col in display.columns:
                try:
                    if sort_col == "challan_date":
                        display[sort_col] = pd.to_datetime(
                            display[sort_col], errors="coerce"
                        )
                    display = display.sort_values(
                        by=sort_col,
                        ascending=(sort_order == "Oldest first"),
                        na_position="last"
                    )
                except Exception:
                    pass

            st.caption(f"{len(display)} challan(s) found")
            if display.empty:
                st.warning("No challans match the search.")
                st.stop()

            picked_no = st.selectbox(
                "Select Challan",
                display["challan_no"].astype(str).tolist(),
                key=f"pick_{widget_key_suffix}"
            )
            picked_row = display.loc[
                display["challan_no"].astype(str) == picked_no
            ].iloc[0]
            picked_id = picked_row["challan_id"]

            items_for = challan_items_df[
                challan_items_df["challan_id"] == picked_id
            ].sort_values("sr_no")

            html = build_challan_html(picked_row, items_for, challan_title)

            st.markdown("---")
            st.markdown("#### Preview")
            st.markdown(
                f'<div style="border:1px solid #ddd; padding:10px; '
                f'background:#fff; border-radius:6px; overflow-x:auto;">{html}</div>',
                unsafe_allow_html=True
            )

            st.markdown("---")
            st.markdown("#### Download")

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                st.download_button(
                    "HTML",
                    data=html.encode("utf-8"),
                    file_name=f"{picked_no}.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"dlh_{widget_key_suffix}_{picked_no}"
                )

            with c2:
                if not items_for.empty:
                    st.download_button(
                        "CSV",
                        data=items_for.to_csv(index=False).encode("utf-8"),
                        file_name=f"{picked_no}_items.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key=f"dlc_{widget_key_suffix}_{picked_no}"
                    )

            with c3:
                printable = build_printable_html_page(html)
                st.download_button(
                    "PDF (Print)",
                    data=printable.encode("utf-8"),
                    file_name=f"{picked_no}_print.html",
                    mime="text/html",
                    use_container_width=True,
                    key=f"pdf_{widget_key_suffix}_{picked_no}"
                )

            with c4:
                if st.button("PNG", use_container_width=True,
                             key=f"png_btn_{widget_key_suffix}_{picked_no}"):
                    with st.spinner("Rendering..."):
                        png = render_challan_png(html, f"{picked_no}.png")
                        if png:
                            st.session_state[
                                f"png_data_{widget_key_suffix}_{picked_no}"
                            ] = png
                            st.success("PNG ready!")
                        else:
                            st.warning("PNG rendering unavailable. Use PDF (Print).")

            with c5:
                png_key = f"png_data_{widget_key_suffix}_{picked_no}"
                if png_key in st.session_state:
                    st.download_button(
                        "Save PNG",
                        data=st.session_state[png_key],
                        file_name=f"{picked_no}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"pngdl_{widget_key_suffix}_{picked_no}"
                    )

    with tab2:
        next_no = next_challan_no(challan_df, challan_no_prefix)
        st.info(f"Next Challan No: {next_no}")

        c1, c2, c3 = st.columns(3)
        with c1:
            challan_date = st.date_input("Challan Date", value=date.today(),
                                         key=f"cd_{widget_key_suffix}")
            sent_to = st.text_input("Sent To", key=f"ct_{widget_key_suffix}")
        with c2:
            vehicle_no = st.text_input("Vehicle No", key=f"cv_{widget_key_suffix}")
            received_by = st.text_input("Received By", key=f"cr_{widget_key_suffix}")
        with c3:
            sent_by = st.text_input("Sent By", key=f"cs_{widget_key_suffix}")

        st.markdown("---")
        st.markdown("#### Items")
        item_rows = challan_items_editor(f"create_{widget_key_suffix}")

        st.markdown("---")
        if st.button("Create Challan", type="primary",
                     key=f"create_btn_{widget_key_suffix}"):
            if not sent_to.strip():
                st.error("Sent To required.")
            else:
                valid = [r for r in item_rows
                         if r["description"].strip() and r["quantity"] > 0]
                if not valid:
                    st.error("At least one valid item row required.")
                else:
                    try:
                        hdr = {
                            "challan_no": next_no,
                            "challan_date": date_str(challan_date),
                            "sent_to": sent_to.strip(),
                            "vehicle_no": vehicle_no.strip() or None,
                            "received_by": received_by.strip() or None,
                            "sent_by": sent_by.strip() or None,
                        }
                        resp = supabase.table(challan_table).insert(hdr).execute()
                        if resp.data:
                            cid = resp.data[0]["challan_id"]
                            payloads = []
                            for idx, r in enumerate(valid, 1):
                                payloads.append({
                                    "challan_id": cid, "sr_no": idx,
                                    "item_id": r["item_id"] if r["item_id"] != "(none)" else None,
                                    "description": r["description"].strip(),
                                    "quantity": r["quantity"],
                                    "unit": (r["unit"] or "Meter").strip()
                                })
                            supabase.table(challan_items_table).insert(payloads).execute()
                            st.success(f"Challan {next_no} created with {len(valid)} item(s).")
                            reset_challan_rows(f"create_{widget_key_suffix}")
                            refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))
                        h = rls_hint(str(e), challan_table, "insert")
                        if h: st.info(h)

    with tab3:
        if challan_df.empty:
            st.info("No challans.")
        else:
            selected_no = st.selectbox("Select Challan",
                challan_df["challan_no"].astype(str).tolist(),
                key=f"upd_{widget_key_suffix}")
            selected = challan_df.loc[
                challan_df["challan_no"].astype(str) == selected_no
            ].iloc[0]
            cid = selected["challan_id"]

            with st.form(f"upd_{widget_key_suffix}_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    d = date.today()
                    if pd.notna(selected["challan_date"]):
                        try:
                            d = pd.to_datetime(selected["challan_date"]).date()
                        except Exception:
                            d = date.today()
                    ed = st.date_input("Challan Date", value=d,
                                       key=f"ed_{widget_key_suffix}")
                    et = st.text_input("Sent To",
                        value=str(selected["sent_to"]) if pd.notna(selected["sent_to"]) else "",
                        key=f"et_{widget_key_suffix}")
                with c2:
                    ev = st.text_input("Vehicle No",
                        value=str(selected["vehicle_no"]) if pd.notna(selected["vehicle_no"]) else "",
                        key=f"ev_{widget_key_suffix}")
                    er = st.text_input("Received By",
                        value=str(selected["received_by"]) if pd.notna(selected["received_by"]) else "",
                        key=f"er_{widget_key_suffix}")
                with c3:
                    es = st.text_input("Sent By",
                        value=str(selected["sent_by"]) if pd.notna(selected["sent_by"]) else "",
                        key=f"es_{widget_key_suffix}")
                upd = st.form_submit_button("Update Header", type="primary")

            if upd:
                try:
                    supabase.table(challan_table).update({
                        "challan_date": date_str(ed),
                        "sent_to": et.strip(),
                        "vehicle_no": ev.strip() or None,
                        "received_by": er.strip() or None,
                        "sent_by": es.strip() or None
                    }).eq("challan_id", cid).execute()
                    st.success("Updated.")
                    refresh_all()
                except Exception as e:
                    st.error("Update failed.")
                    st.code(str(e))

            if st.button("Delete Challan", type="secondary",
                         key=f"del_ch_{widget_key_suffix}"):
                try:
                    supabase.table(challan_table).delete().eq(
                        "challan_id", cid).execute()
                    st.success("Challan deleted.")
                    refresh_all()
                except Exception as e:
                    st.error("Delete failed.")
                    st.code(str(e))

    with tab4:
        if challan_df.empty:
            st.info("No challans.")
        else:
            selected_no = st.selectbox("Select Challan",
                challan_df["challan_no"].astype(str).tolist(),
                key=f"items_{widget_key_suffix}")
            selected = challan_df.loc[
                challan_df["challan_no"].astype(str) == selected_no
            ].iloc[0]
            cid = selected["challan_id"]

            cur = challan_items_df[
                challan_items_df["challan_id"] == cid
            ].sort_values("sr_no")

            st.markdown(f"#### Items for {selected_no}")
            if cur.empty:
                st.info("No items.")
                next_sr = 1
            else:
                st.dataframe(cur, use_container_width=True, hide_index=True)
                next_sr = int(cur["sr_no"].max()) + 1

            item_options = get_item_options(items)
            with st.form(f"add_item_{widget_key_suffix}_form"):
                st.markdown("#### Add New Item")
                c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                with c1:
                    if item_options:
                        ni = st.selectbox("Item ID",
                            ["(none)"] + item_options,
                            key=f"add_ci_{widget_key_suffix}")
                    else:
                        ni = st.text_input("Item ID",
                            key=f"add_cit_{widget_key_suffix}")
                with c2:
                    nd = st.text_input("Description",
                        key=f"add_cd_{widget_key_suffix}")
                with c3:
                    nq = st.number_input("Qty", min_value=0.0, value=0.0,
                                         step=1.0,
                                         key=f"add_cq_{widget_key_suffix}")
                with c4:
                    nu = st.text_input("Unit", value="Meter",
                        key=f"add_cu_{widget_key_suffix}")
                ad = st.form_submit_button("Add", type="primary")

            if ad:
                if not nd.strip() or nq <= 0:
                    st.error("Desc + Qty required.")
                else:
                    try:
                        supabase.table(challan_items_table).insert({
                            "challan_id": cid, "sr_no": next_sr,
                            "item_id": ni if ni != "(none)" else None,
                            "description": nd.strip(),
                            "quantity": nq, "unit": nu.strip() or "Meter"
                        }).execute()
                        st.success("Added.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))

            if not cur.empty:
                st.markdown("---")
                st.markdown("#### Edit / Delete")
                eid = st.selectbox("Select Item",
                    cur["challan_item_id"].astype(str).tolist(),
                    key=f"edit_ci_sel_{widget_key_suffix}")
                er = cur.loc[cur["challan_item_id"].astype(str) == eid].iloc[0]

                with st.form(f"edit_item_{widget_key_suffix}_form"):
                    c1, c2, c3, c4 = st.columns([2, 4, 2, 2])
                    with c1:
                        ce = str(er["item_id"]) if pd.notna(er["item_id"]) else "(none)"
                        if item_options:
                            idx = item_options.index(ce) + 1 if ce in item_options else 0
                            ei = st.selectbox("Item ID",
                                ["(none)"] + item_options, index=idx,
                                key=f"edit_ci_{widget_key_suffix}")
                        else:
                            ei = st.text_input("Item ID", value=ce,
                                key=f"edit_cit_{widget_key_suffix}")
                    with c2:
                        ed = st.text_input("Description",
                            value=str(er["description"]) if pd.notna(er["description"]) else "",
                            key=f"edit_cd_{widget_key_suffix}")
                    with c3:
                        eq = st.number_input("Qty", min_value=0.0,
                            value=float(er["quantity"]) if pd.notna(er["quantity"]) else 0.0,
                            step=1.0,
                            key=f"edit_cq_{widget_key_suffix}")
                    with c4:
                        eu = st.text_input("Unit",
                            value=str(er["unit"]) if pd.notna(er["unit"]) else "Meter",
                            key=f"edit_cu_{widget_key_suffix}")
                    sv = st.form_submit_button("Save", type="primary")

                if sv:
                    try:
                        supabase.table(challan_items_table).update({
                            "item_id": ei if ei != "(none)" else None,
                            "description": ed.strip(),
                            "quantity": eq,
                            "unit": eu.strip() or "Meter"
                        }).eq("challan_item_id", eid).execute()
                        st.success("Updated.")
                        refresh_all()
                    except Exception as e:
                        st.error("Update failed.")
                        st.code(str(e))

                if st.button("Delete Item", type="secondary",
                             key=f"del_ci_{widget_key_suffix}"):
                    try:
                        supabase.table(challan_items_table).delete().eq(
                            "challan_item_id", eid).execute()
                        st.success("Deleted.")
                        refresh_all()
                    except Exception as e:
                        st.error("Failed.")
                        st.code(str(e))


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

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Opening Stock", f"{t['opening']:,.0f}")
    c2.metric("Produced Qty", f"{t['prod_qty']:,.0f}")
    c3.metric("Dispatched", f"{t['dispatched']:,.0f}")
    c4.metric("Returned", f"{t['returned']:,.0f}")
    c5.metric("Adjusted", f"{t['adjusted']:,.0f}")

    st.markdown("---")

    left, right = st.columns(2)
    with left:
        st.subheader("Production Status")
        if not production.empty:
            sdf = (production["Production_Status"].fillna("Unknown")
                   .value_counts().rename_axis("Status").reset_index(name="Count"))
            st.plotly_chart(px.pie(sdf, names="Status", values="Count", hole=0.5),
                            use_container_width=True)
        else:
            empty_state("No production records found.")

    with right:
        st.subheader("Production by Machine")
        if not production.empty and "Production_Line" in production.columns:
            mdf = production.groupby("Production_Line", as_index=False)[
                ["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"]
            ].sum()
            st.plotly_chart(
                px.bar(mdf, x="Production_Line",
                       y=["Planned_Qty_m", "Good_Qty_m", "Rejected_Qty_m"],
                       barmode="group"),
                use_container_width=True
            )
        else:
            empty_state("No production records found.")

    st.subheader("Stock Ledger")
    if not STOCK_LEDGER.empty:
        st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)
    else:
        empty_state("No ledger data available.")


elif page == "Item Registration":
    st.title("Item Registration")

    if items_err:
        st.error(f"Failed to load Item table: {items_err}")

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
                diameter = st.number_input("Nominal Diameter (mm)", min_value=1, value=1, step=1)
                wall = st.number_input("Wall Thickness (mm)", min_value=1, value=1, step=1)
                sdr = st.text_input("SDR")
            with c3:
                color = st.text_input("Color")
                standard_length = st.number_input("Standard Length", min_value=1, value=1, step=1)
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

    with tab3:
        if items.empty:
            st.info("No items available.")
        else:
            selected_id = st.selectbox("Select Item ID",
                                       items["Item_ID"].astype(str).tolist())
            selected = items.loc[items["Item_ID"].astype(str) == selected_id].iloc[0]

            with st.form("update_item_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_code = st.text_input("Item Code",
                        value=str(selected["Item_Code"]) if pd.notna(selected["Item_Code"]) else "")
                    new_grade = st.selectbox("Material Grade", ["PE-80", "PE-100"],
                        index=(1 if str(selected["Material_Grade"]) == "PE-100" else 0))
                    new_application = st.text_input("Application",
                        value=str(selected["Application"]) if pd.notna(selected["Application"]) else "")
                with c2:
                    new_diameter = st.number_input("Nominal Diameter (mm)", min_value=1,
                        value=max(1, int(selected["Nominal_Diameter_mm"])), step=1)
                    new_wall = st.number_input("Wall Thickness (mm)", min_value=1,
                        value=max(1, int(selected["Wall_Thickness_mm"])), step=1)
                    new_sdr = st.text_input("SDR",
                        value=str(selected["SDR"]) if pd.notna(selected["SDR"]) else "")
                with c3:
                    new_color = st.text_input("Color",
                        value=str(selected["Color"]) if pd.notna(selected["Color"]) else "")
                    new_length = st.number_input("Standard Length", min_value=1,
                        value=max(1, int(selected["Standard_Length"])), step=1)
                    new_unit = st.text_input("Unit",
                        value=str(selected["Unit"]) if pd.notna(selected["Unit"]) else "")
                update = st.form_submit_button("Update Item", type="primary")

            if update:
                try:
                    supabase.table(ITEM_TABLE).update({
                        "Item_Code": new_code, "Material_Grade": new_grade,
                        "Application": new_application,
                        "Nominal_Diameter_mm": new_diameter,
                        "Wall_Thickness_mm": new_wall, "SDR": new_sdr,
                        "Color": new_color, "Standard_Length": new_length,
                        "Unit": new_unit
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
    render_challan_module(
        page_title="Delivery Challan",
        challan_table=CHALLAN_TABLE,
        challan_items_table=CHALLAN_ITEMS_TABLE,
        challan_df=challans,
        challan_items_df=challan_items,
        challan_no_prefix="DC",
        challan_title="DELIVERY CHALLAN",
        challans_load_err=challans_err,
        items_load_err=challan_items_err,
        widget_key_suffix="dc"
    )


elif page == "Return Challan":
    render_challan_module(
        page_title="Return Challan",
        challan_table=RETURN_CHALLAN_TABLE,
        challan_items_table=RETURN_CHALLAN_ITEMS_TABLE,
        challan_df=return_challans,
        challan_items_df=return_challan_items,
        challan_no_prefix="RC",
        challan_title="RETURN CHALLAN",
        challans_load_err=return_challans_err,
        items_load_err=return_challan_items_err,
        widget_key_suffix="rc"
    )


elif page == "Analytics":
    st.title("Analytics")

    st.subheader("Production Performance")
    if not production.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Planned", f"{TOTALS['planned']:,.0f} m")
        c2.metric("Good", f"{TOTALS['good']:,.0f} m")
        c3.metric("Rejected", f"{TOTALS['rejected']:,.0f} m")

        adf = pd.DataFrame({
            "Type": ["Good", "Rejected"],
            "Quantity": [TOTALS["good"], TOTALS["rejected"]]
        })
        st.plotly_chart(px.bar(adf, x="Type", y="Quantity", text_auto=True),
                        use_container_width=True)
    else:
        empty_state("No production data.")

    st.markdown("---")
    st.subheader("Stock Ledger")
    if not STOCK_LEDGER.empty:
        st.dataframe(STOCK_LEDGER, use_container_width=True, hide_index=True)
        cols = ["Opening", "Produced", "Dispatched",
                "Returned", "Adjusted", "Closing"]
        st.plotly_chart(
            px.bar(STOCK_LEDGER, x="Item_ID", y=cols, barmode="group"),
            use_container_width=True
        )
    else:
        empty_state("No stock data.")


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
    df = sources[src].copy()

    if df.empty:
        empty_state(f"{src} has no records.")
        st.stop()

    with st.expander("Filters", expanded=False):
        fcols = st.multiselect("Filter by column",
            options=[c for c in df.columns
                     if df[c].dtype == "object" or df[c].nunique() < 30],
            default=[])
        for col in fcols:
            uv = df[col].dropna().astype(str).unique().tolist()
            if not uv: continue
            picked = st.multiselect(f"{col}", uv, default=uv, key=f"f_{col}")
            df = df[df[col].astype(str).isin(picked)]

    if df.empty:
        st.warning("No data after filters.")
        st.stop()

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    all_cols = df.columns.tolist()

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

    agg = "None"
    if cht not in ["Histogram", "Scatter Plot", "Box Plot"]:
        agg = st.selectbox("Aggregation", ["sum", "mean", "count", "max", "min"])

    top_n = st.slider("Top N (0 = all)", 0, 50, 0)
    srt = st.radio("Sort order", ["Descending", "Ascending", "None"], horizontal=True)

    plot_df = df.copy()
    try:
        if agg != "None" and cht not in ["Histogram", "Scatter Plot", "Box Plot"]:
            gcols = [x]
            if cb != "(none)" and cb != x:
                gcols.append(cb)
            if agg == "count":
                plot_df = (plot_df.groupby(gcols)[y].count().reset_index()
                           .rename(columns={y: "count"}))
                yp = "count"
            else:
                plot_df = plot_df.groupby(gcols)[y].agg(agg).reset_index()
                yp = y
        else:
            yp = y

        if agg != "None" and yp in plot_df.columns and srt != "None":
            plot_df = plot_df.sort_values(yp, ascending=(srt == "Ascending"))
        if top_n > 0 and yp in plot_df.columns:
            plot_df = plot_df.head(top_n)

        carg = cb if cb != "(none)" else None

        if cht == "Bar Chart":
            fig = px.bar(plot_df, x=x, y=yp, color=carg, text_auto=True)
        elif cht == "Grouped Bar Chart":
            fig = px.bar(plot_df, x=x, y=yp, color=carg, barmode="group")
        elif cht == "Stacked Bar Chart":
            fig = px.bar(plot_df, x=x, y=yp, color=carg, barmode="stack")
        elif cht == "Line Chart":
            fig = px.line(plot_df, x=x, y=yp, color=carg, markers=True)
        elif cht == "Area Chart":
            fig = px.area(plot_df, x=x, y=yp, color=carg)
        elif cht == "Pie Chart":
            fig = px.pie(plot_df, names=x, values=yp)
        elif cht == "Donut Chart":
            fig = px.pie(plot_df, names=x, values=yp, hole=0.5)
        elif cht == "Scatter Plot":
            fig = px.scatter(plot_df, x=x, y=yp, color=carg)
        elif cht == "Histogram":
            fig = px.histogram(plot_df, x=x, color=carg)
        elif cht == "Box Plot":
            fig = px.box(plot_df, x=x, y=yp, color=carg)
        else:
            fig = None

        if fig is not None:
            fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=520)
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("View underlying data"):
            st.dataframe(plot_df, use_container_width=True, hide_index=True)

        csv = plot_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv,
                           file_name=f"chart_{src.lower().replace(' ', '_')}.csv",
                           mime="text/csv")
    except Exception as e:
        st.error("Chart build error.")
        st.code(str(e))


elif page == "Data Management":
    st.title("Data Management")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items", len(items))
    c2.metric("Production", len(production))
    c3.metric("Delivery Challans", len(challans))
    c4.metric("Return Challans", len(return_challans))

    st.markdown("---")

    with st.expander("Table Diagnostics", expanded=False):
        diag = pd.DataFrame({
            "Table": [
                ITEM_TABLE, PRODUCTION_TABLE, OPENING_TABLE,
                PRODUCTION_QTY_TABLE, DISPATCH_TABLE, RETURN_TABLE,
                CLOSING_TABLE, ADJUSTMENT_TABLE,
                CHALLAN_TABLE, CHALLAN_ITEMS_TABLE,
                RETURN_CHALLAN_TABLE, RETURN_CHALLAN_ITEMS_TABLE,
            ],
            "Rows": [
                len(items), len(production), len(opening),
                len(prod_qty), len(dispatch), len(return_qty),
                len(closing), len(adjustment),
                len(challans), len(challan_items),
                len(return_challans), len(return_challan_items),
            ],
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
        ("Delivery Challan", challans),
        ("Delivery Challan Items", challan_items),
        ("Return Challan", return_challans),
        ("Return Challan Items", return_challan_items),
    ]:
        st.subheader(label)
        st.dataframe(frame, use_container_width=True, hide_index=True)


st.markdown("---")
st.caption("Flex Head Industries Pvt Ltd | ERP Management System")
