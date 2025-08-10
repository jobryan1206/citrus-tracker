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

fruit_options = ["Lime", "Lemon", "Grapefruit", "Ginger", "Apple", "Cucumber", "Other"]
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

# --- Yield prediction (avg + standard deviation ranges) ---
if not df.empty and limes and weight:
    fruit_df = df[df["Fruit"] == fruit].copy()
    recent_df = fruit_df.tail(10) if use_rolling else fruit_df

    if not recent_df.empty and recent_df["Limes"].sum() > 0 and recent_df["Weight (g)"].sum() > 0:
        per_fruit_vals = recent_df["Juice (fl oz)"] / recent_df["Limes"]
        per_100g_vals = recent_df["Juice (fl oz)"] / recent_df["Weight (g)"] * 100

        # Calculate means and standard deviations
        fruit_mean = per_fruit_vals.mean()
        fruit_std = per_fruit_vals.std()
        weight_mean = per_100g_vals.mean()
        weight_std = per_100g_vals.std()

        # Calculate predictions with standard deviation ranges
        fruit_avg = fruit_mean * limes
        fruit_1sd_lower = (fruit_mean - fruit_std) * limes
        fruit_1sd_upper = (fruit_mean + fruit_std) * limes
        fruit_2sd_lower = (fruit_mean - 2*fruit_std) * limes
        fruit_2sd_upper = (fruit_mean + 2*fruit_std) * limes

        weight_avg = (weight_mean / 100) * weight
        weight_1sd_lower = ((weight_mean - weight_std) / 100) * weight
        weight_1sd_upper = ((weight_mean + weight_std) / 100) * weight
        weight_2sd_lower = ((weight_mean - 2*weight_std) / 100) * weight
        weight_2sd_upper = ((weight_mean + 2*weight_std) / 100) * weight

        # Get most recent entry for this fruit type
        if len(recent_df) > 0:
            last_entry = recent_df.iloc[-1]
            last_per_fruit = last_entry["Juice (fl oz)"] / last_entry["Limes"] if last_entry["Limes"] > 0 else 0
            last_per_100g = last_entry["Juice (fl oz)"] / last_entry["Weight (g)"] * 100 if last_entry["Weight (g)"] > 0 else 0
            
            last_fruit_pred = last_per_fruit * limes
            last_weight_pred = (last_per_100g / 100) * weight
        else:
            last_fruit_pred = 0
            last_weight_pred = 0

        pred_table = pd.DataFrame({
            "Method": ["By fruit count", "By weight"],
            "Avg (fl oz)": [fruit_avg, weight_avg],
            "1σ Range (fl oz)": [
                f"{fruit_1sd_lower:.1f} - {fruit_1sd_upper:.1f}",
                f"{weight_1sd_lower:.1f} - {weight_1sd_upper:.1f}"
            ],
            "2σ Range (fl oz)": [
                f"{fruit_2sd_lower:.1f} - {fruit_2sd_upper:.1f}",
                f"{weight_2sd_lower:.1f} - {weight_2sd_upper:.1f}"
            ],
            "Like Last Entry (fl oz)": [
                f"{last_fruit_pred:.1f}",
                f"{last_weight_pred:.1f}"
            ]
        })

        # Format the average column
        pred_table["Avg (fl oz)"] = pred_table["Avg (fl oz)"].map(lambda x: f"{x:.1f}")

        st.subheader("📈 Predicted Juice Yield (fl oz)")
        st.table(pred_table.set_index("Method"))
        
        # Add explanatory text
        st.caption("1σ range covers ~68% of expected outcomes, 2σ range covers ~95% of expected outcomes. 'Like Last Entry' shows predictions if this session matches your most recent entry for this fruit type.")

        if juice:
            st.subheader("🔍 Prediction Accuracy")

            def compare(pred, actual):
                diff = pred - actual
                pct = (diff / actual) * 100
                direction = "overestimated" if diff > 0 else "underestimated"
                return diff, abs(pct), direction

            _, pct_fruit, dir_fruit = compare(fruit_avg, juice)
            _, pct_weight, dir_weight = compare(weight_avg, juice)
            _, pct_last_fruit, dir_last_fruit = compare(last_fruit_pred, juice)
            _, pct_last_weight, dir_last_weight = compare(last_weight_pred, juice)

            st.write(f"• Avg fruit prediction {dir_fruit} by **{pct_fruit:.1f}%**")
            st.write(f"• Avg weight prediction {dir_weight} by **{pct_weight:.1f}%**")
            st.write(f"• Last entry (fruit method) {dir_last_fruit} by **{pct_last_fruit:.1f}%**")
            st.write(f"• Last entry (weight method) {dir_last_weight} by **{pct_last_weight:.1f}%**")
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

        # Reset all fields
        for key in ["fruit_select", "fruit_custom", "num_fruits", "weight_input", "juice_input"]:
            if key in st.session_state:
                st.session_state[key] = "" if isinstance(st.session_state[key], str) else None

        st.rerun()

# --- Juice Efficiency Over Time ---
if not df.empty and fruit:  # Only show if a fruit is selected
    st.subheader(f"📈 {fruit} Efficiency Over Time")
    
    # Filter data for the selected fruit type only
    fruit_data = df[df["Fruit"] == fruit].copy()
    
    if len(fruit_data) > 1:
        # Create efficiency chart data
        chart_df = fruit_data.copy()
        chart_df["Date"] = pd.to_datetime(chart_df["Date"])
        
        # Calculate efficiency metrics for each entry
        chart_df["Juice per fruit (fl oz)"] = chart_df.apply(
            lambda row: row["Juice (fl oz)"] / row["Limes"] if row["Limes"] > 0 else np.nan, 
            axis=1
        )
        chart_df["Juice per 100g (fl oz)"] = chart_df.apply(
            lambda row: (row["Juice (fl oz)"] / row["Weight (g)"]) * 100 if row["Weight (g)"] > 0 else np.nan, 
            axis=1
        )
        
        # Filter out entries with missing data and sort by date
        chart_df = chart_df.dropna(subset=["Juice per fruit (fl oz)", "Juice per 100g (fl oz)"])
        chart_df = chart_df.sort_values("Date")
        
        if not chart_df.empty:
            # Create the line chart
            st.line_chart(
                chart_df.set_index("Date")[["Juice per fruit (fl oz)", "Juice per 100g (fl oz)"]]
            )
            
            # Add some summary stats
            col1, col2 = st.columns(2)
            with col1:
                latest_per_fruit = chart_df["Juice per fruit (fl oz)"].iloc[-1]
                avg_per_fruit = chart_df["Juice per fruit (fl oz)"].mean()
                st.metric(
                    f"Latest vs Avg (per {fruit.lower()})", 
                    f"{latest_per_fruit:.2f} fl oz",
                    f"{latest_per_fruit - avg_per_fruit:+.2f} fl oz"
                )
            
            with col2:
                latest_per_100g = chart_df["Juice per 100g (fl oz)"].iloc[-1]
                avg_per_100g = chart_df["Juice per 100g (fl oz)"].mean()
                st.metric(
                    f"Latest vs Avg (per 100g {fruit.lower()})", 
                    f"{latest_per_100g:.2f} fl oz",
                    f"{latest_per_100g - avg_per_100g:+.2f} fl oz"
                )
        else:
            st.info(f"Not enough complete {fruit.lower()} entries to display efficiency trends.")
    else:
        st.info(f"Add more {fruit.lower()} entries to see efficiency trends over time (need at least 2 entries).")
        
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


