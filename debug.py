import streamlit as st
from supabase import create_client

st.set_page_config(page_title="Debug", layout="wide")
st.title("Supabase Connection Debug")

# 1. Secrets
st.header("1. Secrets Load")
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    st.success("✅ Secrets loaded")
    st.code(f"URL: {URL}")
    st.code(f"KEY (first 30): {KEY[:30]}...")
    st.code(f"KEY length: {len(KEY)}")
except Exception as e:
    st.error(f"❌ Secrets missing: {e}")
    st.stop()

# 2. Client
st.header("2. Client Creation")
try:
    supabase = create_client(URL, KEY)
    st.success("✅ Client created")
except Exception as e:
    st.error(f"❌ Failed: {e}")
    st.stop()

# 3. Table listing (raw SQL through RPC won't work, so we try known tables)
st.header("3. Table Access Test")

TABLES = [
    "Item_Registration",
    "Production",
    "Opening_Stock",
    "Production_Qty",
    "Dispatch_Qty",
    "Return_Qty",
    "Closing_Stock",
    "Stock_Adjustment",
]

for t in TABLES:
    with st.expander(f"📋 {t}", expanded=True):
        try:
            resp = supabase.table(t).select("*").execute()
            data = resp.data or []
            st.write(f"**Records: {len(data)}**")

            if data:
                st.success("✅ Data returned")
                st.write("**First record:**")
                st.json(data[0])
                st.write(f"**Columns in first record:** {list(data[0].keys())}")
            else:
                st.warning("⚠️ Empty array returned (no error)")
                st.info(
                    "Iske 2 matlab hain:\n"
                    "1. Table actually empty hai, ya\n"
                    "2. RLS SELECT block kar raha hai (Supabase silently [] return karta hai)"
                )
        except Exception as e:
            st.error(f"❌ ERROR: {type(e).__name__}")
            st.code(str(e))

# 4. Direct count test (via select with count)
st.header("4. Record Count Test")
for t in TABLES:
    try:
        resp = supabase.table(t).select("*", count="exact").limit(1).execute()
        st.write(f"**{t}**: count = {resp.count}")
    except Exception as e:
        st.write(f"**{t}**: ERROR — {e}")

# 5. Insert test
st.header("5. Insert Test (to verify RLS INSERT)")
if st.button("Test insert into Stock_Adjustment"):
    try:
        supabase.table("Stock_Adjustment").insert({
            "Adjustment_ID": "ADJ-TEST",
            "Item_ID": "ITM-001",
            "Adjustment_Date": "2026-01-01",
            "Qty": 0,
            "Reason": "Other",
            "Remarks": "Debug test row"
        }).execute()
        st.success("✅ Insert worked")
        # Clean up
        supabase.table("Stock_Adjustment").delete().eq("Adjustment_ID", "ADJ-TEST").execute()
        st.info("Test row cleaned up")
    except Exception as e:
        st.error(f"❌ Insert failed: {e}")
