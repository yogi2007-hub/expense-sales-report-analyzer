"""Data cleaning and reporting functions for the Streamlit application."""

from __future__ import annotations

from typing import BinaryIO

import pandas as pd

REQUIRED_COLUMNS = {"Date", "Type", "Category", "Amount"}
VALID_TYPES = {"expense": "Expense", "sale": "Sale", "income": "Sale"}


def load_transactions(file: BinaryIO) -> pd.DataFrame:
    """Read and validate an uploaded CSV, returning cleaned transaction rows."""
    try:
        frame = pd.read_csv(file)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        raise ValueError(f"Could not read this CSV file: {exc}") from exc

    frame.columns = [str(column).strip() for column in frame.columns]
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(sorted(missing)))
    if frame.empty:
        return frame.assign(Date=pd.to_datetime([]), Type=[], Category=[], Amount=[])

    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Type"] = frame["Type"].astype("string").str.strip().str.lower().map(VALID_TYPES)
    frame["Category"] = frame["Category"].astype("string").str.strip()
    frame["Amount"] = pd.to_numeric(frame["Amount"], errors="coerce")

    invalid = frame["Date"].isna() | frame["Type"].isna() | frame["Category"].isna() | frame["Amount"].isna()
    invalid |= frame["Category"].eq("") | (frame["Amount"] < 0)
    cleaned = frame.loc[~invalid].copy()
    cleaned["Amount"] = cleaned["Amount"].abs()
    if "Description" not in cleaned:
        cleaned["Description"] = ""
    return cleaned.sort_values("Date").reset_index(drop=True)


def analyze_transactions(frame: pd.DataFrame) -> dict[str, object]:
    """Build summary totals, monthly/category tables, and IQR outlier flags."""
    data = frame.copy()
    if data.empty:
        return {
            "income": 0.0,
            "expenses": 0.0,
            "monthly": pd.DataFrame(columns=["Month", "Sales", "Expenses"]),
            "category": pd.DataFrame(columns=["Category", "Sales", "Expenses"]),
            "outliers": data,
        }

    sales = data.loc[data["Type"] == "Sale", "Amount"].sum()
    expenses = data.loc[data["Type"] == "Expense", "Amount"].sum()
    data["Month"] = data["Date"].dt.to_period("M").astype(str)
    monthly = data.pivot_table(index="Month", columns="Type", values="Amount", aggfunc="sum", fill_value=0)
    for column in ("Sale", "Expense"):
        if column not in monthly:
            monthly[column] = 0.0
    monthly = monthly.rename(columns={"Sale": "Sales", "Expense": "Expenses"})[["Sales", "Expenses"]].reset_index()

    category = data.pivot_table(index="Category", columns="Type", values="Amount", aggfunc="sum", fill_value=0)
    for column in ("Sale", "Expense"):
        if column not in category:
            category[column] = 0.0
    category = category.rename(columns={"Sale": "Sales", "Expense": "Expenses"})[["Sales", "Expenses"]].sort_values(
        ["Expenses", "Sales"], ascending=False
    ).reset_index()

    flagged = pd.Series(False, index=data.index)
    for _, group in data.groupby("Type"):
        if len(group) >= 4:
            q1, q3 = group["Amount"].quantile([0.25, 0.75])
            spread = q3 - q1
            flagged.loc[group.index] = (group["Amount"] < q1 - 1.5 * spread) | (group["Amount"] > q3 + 1.5 * spread)
    outliers = data.loc[flagged].drop(columns=["Month"]).sort_values("Amount", ascending=False)
    return {"income": float(sales), "expenses": float(expenses), "monthly": monthly, "category": category, "outliers": outliers}
