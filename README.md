# Flex Head Industry Pvt Ltd — ERP Dashboard

## Included
- `app.py` — Streamlit ERP application
- `style.css` — professional ERP interface styling
- `requirements.txt` — dependencies
- CSV files — uploaded source data used as local fallback

## Modules
1. Executive Dashboard
2. Item Registration
3. Production Management
4. Stock Control
5. Analytics & Insights
6. Data Management

## Supabase setup

Create these PostgreSQL tables in Supabase:

### item_registration
Columns:
- Item_ID (text, primary key)
- Item_Code (text)
- Material_Grade (text)
- Application (text)
- Nominal_Diameter_mm (numeric)
- Wall_Thickness_mm (numeric)
- SDR (text)
- Color (text)
- Standard_Length (numeric)
- Unit (text)

### production
Columns:
- Production_ID (text, primary key)
- Item_ID (text)
- Production_Date (date)
- Batch_No (text)
- Production_Line (text)
- Planned_Qty_m (numeric)
- Good_Qty_m (numeric)
- Rejected_Qty_m (numeric)
- Production_Status (text)

### stock_control
Columns:
- Stock_ID (text, primary key)
- Item_ID (text)
- Production_ID (text)
- Batch_No (text)
- Stock_Date (date)
- Opening_Stock_m (numeric)
- Produced_Qty_m (numeric)
- Dispatched_Qty_m (numeric)
- Closing_Stock_m (numeric)
- Stock_Status (text)

## Environment variables

Set:

SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_KEY=YOUR-SUPABASE-ANON-KEY

For Streamlit Cloud, add them under App Settings → Secrets.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The application automatically uses the CSV files if Supabase credentials are not configured.
