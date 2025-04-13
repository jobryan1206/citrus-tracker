import streamlit as st
import pandas as pd
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
                        value=st.session_state.get("num_fruits", 0),
                        placeholder="e.g. 4", key="num_fruits")

weight = st.number_input("Total weight (g)", min_value=0.0,
                         value=st.session_state.get("weight_input", 0.0),
                         placeholder="e.g. 350.5", key="weight_input")

juice = st.number_input("Juice collected (fl oz)", min_value=0.0,
                        value=st.session_state.get("juice_input", 0.0),
                        placeholder="e.g. 5.5", key="juice_input")

# --- Prediction toggle ---
use_rolling = st.toggle("Use rolling average (last 10 entries)", value=True)

# --- Yield prediction section ---
if not df.empty and limes > 0 and weight > 0:
    fruit_df = df[df["Fruit"] == fruit].copy()
    recent_df = fruit_df.tail(10) if use_rolling else fruit_df

    if not recent_df.empty and recent_df["Limes"].sum() > 0 and recent_df["Weight (g)"].sum() > 0:
        avg_juice_per_fruit = recent_df["Juice (fl oz)"].sum() / recent_df["Limes"].sum()
        avg_juice_per_100g = (recent_df["Juice (fl oz)"].sum() / recent_df["Weight (g)"].sum()) * 100

        predicted_by_fruit = avg_juice_per_fruit * limes
        predicted_by_weight = (avg_juice_per_100g / 100) * weight

        st.subheader("📈 Predicted Juice Yield")
        st.write(f"• Based on fruit count: **{predicted_by_fruit:.2f} fl oz**")
        st.write(f"• Based on weight: **{predicted_by_weight:.2f} fl oz**")

        if juice > 0:
            st.subheader("🔍 Prediction Accuracy")

            def compare_prediction(predicted, actual):
                diff = predicted - actual
                percent_error = (diff / actual) * 100
                direction = "overestimated" if diff > 0 else "underestimated"
                return diff, abs(percent_error), direction

            diff_fruit, pct_fruit, dir_fruit = compare_prediction(predicted_by_fruit, juice)
            diff_weight, pct_weight, dir_weight = compare_prediction(predicted_by_weight, juice)

            st.write(f"• Fruit prediction {dir_fruit} by **{pct_fruit:.1f}%** ({diff_fruit:+.2f} fl oz)")
            st.write(f"• Weight prediction {dir_weight} by **{pct_weight:.1f}%** ({diff_weight:+.2f} fl oz)")
    else:
        st.info("Not enough recent data to make a prediction.")

# --- Submission block ---
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

        # Clear input fields safely
        for key in ["num_fruits", "weight_input", "juice_input", "fruit_custom"]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()

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
            st.markdown(f"**{row['Fruit']}**")
            st.write(f"• Juice per fruit: {row['Juice (fl oz)'] / row['Limes']:.2f} fl oz")
            st.write(f"• Juice per 100g: {(row['Juice (fl oz)'] / row['Weight (g)']) * 100:.2f} fl oz/100g")

# --- Data Table ---
    st.subheader("📄 All Entries")
    st.dataframe(df)

# --- Chart: Prediction vs Actual Over Time ---
if not df.empty and "Juice (fl oz)" in df.columns:
    st.subheader("📈 Prediction vs Actual Over Time")

    chart_df = df[df["Limes"] > 0].copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])

    # Calculate full-history averages
    full_avg_per_fruit = df["Juice (fl oz)"].sum() / df["Limes"].sum()
    full_avg_per_100g = df["Juice (fl oz)"].sum() / df["Weight (g)"].sum()

    chart_df["Predicted (Fruits)"] = chart_df["Limes"] * full_avg_per_fruit
    chart_df["Predicted (Weight)"] = (chart_df["Weight (g)"] / 100) * (full_avg_per_100g * 100)

    st.line_chart(
        chart_df[["Date", "Juice (fl oz)", "Predicted (Fruits)", "Predicted (Weight)"]].set_index("Date")
    )
