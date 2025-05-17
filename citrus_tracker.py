import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)
sheet = client.open("Citrus Juice Tracker").worksheet("juice_data")

# Load data
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🍋 Citrus Juice Tracker")

# --- Input section ---
st.subheader("Add New Entry")

fruit_options = ["Lime", "Lemon", "Orange", "Grapefruit", "Apple", "Cucumber", "Other"]
selected = st.selectbox("Fruit type", fruit_options, key="fruit_select")

if selected == "Other":
    fruit = st.text_input("Enter fruit name", key="fruit_custom").strip().capitalize()
else:
    fruit = selected

limes = st.number_input("Number of fruits", min_value=0, step=1, format="%i",
                        value=None, placeholder="e.g. 4", key="num_fruits")
weight = st.number_input("Total weight (g)", min_value=0.0,
                         value=None, placeholder="e.g. 350.5", key="weight_input")
juice = st.number_input("Juice collected (fl oz)", min_value=0.0,
                        value=None, placeholder="e.g. 5.5", key="juice_input")

# --- Toggle for rolling average ---
use_rolling = st.toggle("Use rolling average (last 10 entries)", value=True)

# --- Yield prediction (min/avg/max + accuracy) ---
if not df.empty and limes and weight:
    fruit_df = df[df["Fruit"] == fruit].copy()
    recent_df = fruit_df.tail(10) if use_rolling else fruit_df

    if not recent_df.empty and recent_df["Limes"].sum() > 0 and recent_df["Weight (g)"].sum() > 0:
        per_fruit_vals = recent_df["Juice (fl oz)"] / recent_df["Limes"]
        per_100g_vals = recent_df["Juice (fl oz)"] / recent_df["Weight (g)"] * 100

        pred_table = pd.DataFrame({
            "Method": ["By fruit count", "By weight"],
            "Min (fl oz)": [
                per_fruit_vals.min() * limes,
                (per_100g_vals.min() / 100) * weight
            ],
            "Avg (fl oz)": [
                per_fruit_vals.mean() * limes,
                (per_100g_vals.mean() / 100) * weight
            ],
            "Max (fl oz)": [
                per_fruit_vals.max() * limes,
                (per_100g_vals.max() / 100) * weight
            ]
        })

        for col in ["Min (fl oz)", "Avg (fl oz)", "Max (fl oz)"]:
            pred_table[col] = pred_table[col].map(lambda x: f"{x:.1f}")


        st.subheader("📈 Predicted Juice Yield (fl oz)")
        st.table(pred_table.set_index("Method"))

        if juice:
            st.subheader("🔍 Prediction Accuracy")

            def compare(pred, actual):
                diff = pred - actual
                pct = (diff / actual) * 100
                direction = "overestimated" if diff > 0 else "underestimated"
                return diff, abs(pct), direction

            avg_pred_fruit = per_fruit_vals.mean() * limes
            avg_pred_weight = (per_100g_vals.mean() / 100) * weight

            _, pct_fruit, dir_fruit = compare(avg_pred_fruit, juice)
            _, pct_weight, dir_weight = compare(avg_pred_weight, juice)

            st.write(f"• Avg fruit prediction {dir_fruit} by **{pct_fruit:.1f}%**")
            st.write(f"• Avg weight prediction {dir_weight} by **{pct_weight:.1f}%**")
    else:
        st.info("Not enough data to generate predictions.")

# --- Save entry ---
if st.button("Add Entry"):
    if not fruit:
        st.warning("Please enter a fruit name.")
    else:
        new_entry = [
            datetime.now().strftime("%Y-%m-%d"),
            fruit,
            limes,
            weight,
            juice
        ]
        sheet.append_row(new_entry)
        st.success("Entry added!")

        for key in ["num_fruits", "weight_input", "juice_input", "fruit_custom"]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()

# --- Current Entry Stats ---
if juice and limes > 0 and weight > 0:
    st.subheader("📌 This Entry’s Stats")
    per_lime = juice / limes
    per_lb = juice / (weight / 453.6)
    st.write(f"• Juice per fruit: **{per_lime:.2f} fl oz**")
    st.write(f"• Juice per pound: **{per_lb:.2f} fl oz/lb**")

    # --- Historical Averages for This Fruit ---
    if not df.empty:
        fruit_df = df[df["Fruit"] == fruit]
        if not fruit_df.empty and fruit_df["Limes"].sum() > 0 and fruit_df["Weight (g)"].sum() > 0:
            hist_oz = fruit_df["Juice (fl oz)"].sum()
            hist_fruit = fruit_df["Limes"].sum()
            hist_weight = fruit_df["Weight (g)"].sum()
            hist_per_fruit = hist_oz / hist_fruit
            hist_per_lb = hist_oz / (hist_weight / 453.6)

            st.subheader("📊 Historical Averages for This Fruit")
            st.write(f"• Avg juice per fruit: **{hist_per_fruit:.2f} fl oz**")
            st.write(f"• Avg juice per pound: **{hist_per_lb:.2f} fl oz/lb**")

# --- Averages by Fruit ---
if not df.empty and "Fruit" in df.columns:
    st.subheader("📊 Averages by Fruit")

    grouped = df.groupby("Fruit").agg({
        "Limes": "sum",
        "Weight (g)": "sum",
        "Juice (fl oz)": "sum"
    }).reset_index()

    for _, row in grouped.iterrows():
        if row["Limes"] > 0 and row["Weight (g)"] > 0:
            per_fruit = row["Juice (fl oz)"] / row["Limes"]
            per_lb = row["Juice (fl oz)"] / (row["Weight (g)"] / 453.6)
            st.markdown(f"**{row['Fruit']}**")
            st.write(f"• Juice per fruit: {per_fruit:.2f} fl oz")
            st.write(f"• Juice per pound: {per_lb:.2f} fl oz/lb")

    st.subheader("📄 All Entries")
    st.dataframe(df)

# --- Prediction vs Actual Over Time ---
if not df.empty and "Juice (fl oz)" in df.columns:
    st.subheader("📈 Prediction vs Actual Over Time")

    chart_df = df[df["Limes"] > 0].copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])

    avg_per_fruit = df["Juice (fl oz)"].sum() / df["Limes"].sum()
    avg_per_100g = df["Juice (fl oz)"].sum() / df["Weight (g)"].sum()

    chart_df["Predicted (Fruits)"] = chart_df["Limes"] * avg_per_fruit
    chart_df["Predicted (Weight)"] = (chart_df["Weight (g)"] / 100) * avg_per_100g

    st.line_chart(chart_df.set_index("Date")[["Juice (fl oz)", "Predicted (Fruits)", "Predicted (Weight)"]])
