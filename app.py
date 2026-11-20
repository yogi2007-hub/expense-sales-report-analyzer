"""Interactive expense and sales report analyzer."""

from __future__ import annotations

import streamlit as st

from analyzer import analyze_transactions, load_transactions


st.set_page_config(page_title="Expense & Sales Analyzer", page_icon="📊", layout="wide")
st.title("📊 Expense & Sales Report Analyzer")
st.caption("Upload a CSV to summarize transactions, compare trends, and spot unusual amounts.")

with st.sidebar:
    st.header("Upload data")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    st.markdown("**Required columns:** `Date`, `Type`, `Category`, `Amount`")
    st.markdown("Optional: `Description`, `Payment Method`")
    st.download_button(
        "Download sample CSV",
        data=(
            "Date,Type,Category,Amount,Description,Payment Method\n"
            "2026-01-03,Expense,Software,49.00,Monthly subscription,Card\n"
            "2026-01-05,Sale,Online,320.00,Website order,Transfer\n"
            "2026-01-08,Expense,Travel,86.50,Client visit,Card\n"
            "2026-02-02,Sale,In-store,540.00,Weekend sales,Cash\n"
            "2026-02-11,Expense,Marketing,125.00,Social campaign,Card\n"
            "2026-02-19,Sale,Online,410.00,Website order,Transfer\n"
            "2026-03-01,Expense,Office,62.75,Office supplies,Card\n"
            "2026-03-07,Sale,In-store,690.00,Weekend sales,Cash\n"
            "2026-03-14,Expense,Travel,94.00,Client visit,Card\n"
            "2026-03-20,Sale,Online,485.00,Website order,Transfer\n"
        ),
        file_name="sample_transactions.csv",
        mime="text/csv",
    )

if uploaded_file is None:
    st.info("Upload a CSV or download the sample CSV from the sidebar to get started.")
    st.stop()

try:
    transactions = load_transactions(uploaded_file)
    report = analyze_transactions(transactions)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if transactions.empty:
    st.warning("The file has no valid transaction rows.")
    st.stop()

types = sorted(transactions["Type"].unique())
selected_types = st.multiselect("Transaction types", types, default=types)
filtered = transactions[transactions["Type"].isin(selected_types)]
report = analyze_transactions(filtered)

income = report["income"]
expenses = report["expenses"]
net = income - expenses
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total sales / income", f"${income:,.2f}")
c2.metric("Total expenses", f"${expenses:,.2f}")
c3.metric("Net", f"${net:,.2f}", delta=f"{net:,.2f}")
c4.metric("Transactions", f"{len(filtered):,}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly trend")
    monthly = report["monthly"]
    if not monthly.empty:
        st.line_chart(monthly.set_index("Month")[["Sales", "Expenses"]])
    else:
        st.caption("No dated transactions to chart.")
with right:
    st.subheader("Amount by category")
    category = report["category"]
    if not category.empty:
        st.bar_chart(category.set_index("Category")[["Sales", "Expenses"]])
    else:
        st.caption("No category totals to chart.")

st.subheader("Unusual transactions")
outliers = report["outliers"]
if outliers.empty:
    st.success("No unusual amounts found using the 1.5× IQR rule within each transaction type.")
else:
    st.warning(f"Found {len(outliers)} unusual transaction(s). Review these before relying on the report.")
    st.dataframe(outliers, use_container_width=True, hide_index=True)

with st.expander("View analyzed transactions"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)

st.download_button(
    "Download analyzed transactions",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="analyzed_transactions.csv",
    mime="text/csv",
)
st.caption("Anomaly flags are statistical hints, not proof of fraud or errors. Currency is displayed in USD; update the app for your preferred currency.")
