import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# App setup
# =========================
st.set_page_config(page_title="🍋 Citrus Juice Tracker", page_icon="🍋", layout="wide")
st.title("🍋 Citrus Juice Tracker")

# Force-clear widgets after submit by changing their keys
if "reset" not in st.session_state:
    st.session_state["reset"] = 0

# --- Google Sheets setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google"]  # expects [google] block in Secrets
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)
sheet = client.open("Citrus Juice Tracker").worksheet("juice_data")

# Load data
data = sheet.get_all_records()
df = pd.DataFrame(data)

# =========================
# Input section
# =========================
st.subheader("Add New Entry")

fruit_options = ["Lime", "Lemon", "Grapefruit", "Ginger", "Apple", "Cucumber", "Other"]

selected = st.selectbox(
    "Fruit type",
    fruit_options,
    key=f"fruit_select_{st.session_state['reset']}",
)

if selected == "Other":
    fruit = st.text_input(
        "Enter fruit name",
        key=f"fruit_custom_{st.session_state['reset']}",
    ).strip().capitalize()
else:
    fruit = selected

limes = st.number_input(
    "Number of fruits",
    min_value=0, step=1, format="%i",
    value=None, placeholder="e.g. 4",
    key=f"num_fruits_{st.session_state['reset']}",
)

weight = st.number_input(
    "Total weight (g)",
    min_value=0.0,
    value=None, placeholder="e.g. 350.5",
    key=f"weight_input_{st.session_state['reset']}",
)

juice = st.number_input(
    "Juice collected (fl oz)",
    min_value=0.0,
    value=None, placeholder="e.g. 5.5",
    key=f"juice_input_{st.session_state['reset']}",
)

# --- Toggle for rolling average ---
use_rolling = st.toggle("Use rolling average (last 10 entries)", value=True)

# =========================
# Yield prediction with proper confidence intervals
# =========================
if not df.empty and limes and weight:
    fruit_df = df[df["Fruit"] == fruit].copy()
    recent_df = fruit_df.tail(10) if use_rolling else fruit_df

    if not recent_df.empty and recent_df["Limes"].sum() > 0 and recent_df["Weight (g)"].sum() > 0:
        # Calculate per-fruit and per-100g values
        per_fruit_vals = recent_df["Juice (fl oz)"] / recent_df["Limes"]
        per_100g_vals = recent_df["Juice (fl oz)"] / recent_df["Weight (g)"] * 100

        # Calculate statistics
        fruit_mean = per_fruit_vals.mean()
        fruit_std = per_fruit_vals.std() if len(per_fruit_vals) > 1 else 0
        weight_mean = per_100g_vals.mean()
        weight_std = per_100g_vals.std() if len(per_100g_vals) > 1 else 0
        
        # Calculate coefficient of variation (relative standard deviation)
        fruit_cv = fruit_std / fruit_mean if fruit_mean > 0 else 0
        weight_cv = weight_std / weight_mean if weight_mean > 0 else 0

        # Per-fruit predictions with proper scaling
        fruit_avg = fruit_mean * limes
        # Standard deviation of the prediction scales with sqrt(n) for independent samples
        # But for a single batch, we use the CV to estimate uncertainty
        fruit_std_pred = fruit_avg * fruit_cv
        fruit_1sd_lower = max(0, fruit_avg - fruit_std_pred)
        fruit_1sd_upper = fruit_avg + fruit_std_pred
        fruit_2sd_lower = max(0, fruit_avg - 2 * fruit_std_pred)
        fruit_2sd_upper = fruit_avg + 2 * fruit_std_pred

        # Per-weight predictions with proper scaling
        weight_avg = (weight_mean / 100) * weight
        weight_std_pred = weight_avg * weight_cv
        weight_1sd_lower = max(0, weight_avg - weight_std_pred)
        weight_1sd_upper = weight_avg + weight_std_pred
        weight_2sd_lower = max(0, weight_avg - 2 * weight_std_pred)
        weight_2sd_upper = weight_avg + 2 * weight_std_pred

        # Like Last Entry (per-fruit and per-100g)
        if len(recent_df) > 0:
            last_entry = recent_df.iloc[-1]
            last_per_fruit = last_entry["Juice (fl oz)"] / last_entry["Limes"] if last_entry["Limes"] > 0 else 0
            last_per_100g = (last_entry["Juice (fl oz)"] / last_entry["Weight (g)"] * 100) if last_entry["Weight (g)"] > 0 else 0
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

        pred_table["Avg (fl oz)"] = pred_table["Avg (fl oz)"].map(lambda x: f"{x:.1f}")

        st.subheader("📈 Predicted Juice Yield (fl oz)")
        st.table(pred_table.set_index("Method"))
        
        # Show the underlying statistics for transparency
        with st.expander("View calculation details"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Per-fruit statistics:**")
                st.write(f"- Mean: {fruit_mean:.3f} fl oz/fruit")
                st.write(f"- Std Dev: {fruit_std:.3f} fl oz/fruit")
                st.write(f"- CV: {fruit_cv:.1%}")
            with col2:
                st.write("**Per-100g statistics:**")
                st.write(f"- Mean: {weight_mean:.3f} fl oz/100g")
                st.write(f"- Std Dev: {weight_std:.3f} fl oz/100g")
                st.write(f"- CV: {weight_cv:.1%}")

        st.caption("1σ ≈ 68% of outcomes, 2σ ≈ 95%. Ranges based on coefficient of variation from historical data.")

        if juice:
            st.subheader("🔍 Prediction Accuracy")

            def compare(pred, actual):
                diff = pred - actual
                pct = (diff / actual) * 100 if actual else 0
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
            
            # Check if actual is within confidence intervals
            in_1sd_fruit = fruit_1sd_lower <= juice <= fruit_1sd_upper
            in_2sd_fruit = fruit_2sd_lower <= juice <= fruit_2sd_upper
            in_1sd_weight = weight_1sd_lower <= juice <= weight_1sd_upper
            in_2sd_weight = weight_2sd_lower <= juice <= weight_2sd_upper
            
            col1, col2 = st.columns(2)
            with col1:
                if in_1sd_fruit:
                    st.success("✓ Within 1σ range (fruit method)")
                elif in_2sd_fruit:
                    st.info("✓ Within 2σ range (fruit method)")
                else:
                    st.warning("Outside 2σ range (fruit method)")
            with col2:
                if in_1sd_weight:
                    st.success("✓ Within 1σ range (weight method)")
                elif in_2sd_weight:
                    st.info("✓ Within 2σ range (weight method)")
                else:
                    st.warning("Outside 2σ range (weight method)")
    else:
        st.info("Not enough data to generate predictions.")

# =========================
# Save entry (and clear inputs)
# =========================
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
        st.toast("Entry added!", icon="✅")

        # Force-clear all widgets by bumping the key suffix and rerunning
        st.session_state["reset"] += 1
        st.rerun()

# =========================
# Juice Efficiency Over Time
# =========================
if not df.empty and fruit:  # Only show if a fruit is selected
    st.subheader(f"📈 {fruit} Efficiency Over Time")

    fruit_data = df[df["Fruit"] == fruit].copy()

    if len(fruit_data) > 1:
        chart_df = fruit_data.copy()
        chart_df["Date"] = pd.to_datetime(chart_df["Date"])

        chart_df["Juice per fruit (fl oz)"] = chart_df.apply(
            lambda row: row["Juice (fl oz)"] / row["Limes"] if row["Limes"] > 0 else np.nan,
            axis=1
        )
        chart_df["Juice per 100g (fl oz)"] = chart_df.apply(
            lambda row: (row["Juice (fl oz)"] / row["Weight (g)"]) * 100 if row["Weight (g)"] > 0 else np.nan,
            axis=1
        )

        chart_df = chart_df.dropna(subset=["Juice per fruit (fl oz)", "Juice per 100g (fl oz)"]).sort_values("Date")

        if not chart_df.empty:
            st.line_chart(
                chart_df.set_index("Date")[["Juice per fruit (fl oz)", "Juice per 100g (fl oz)"]]
            )

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

# =========================
# This Entry's Stats
# =========================
if juice and limes > 0 and weight > 0:
    st.subheader("📌 This Entry's Stats")
    per_lime = juice / limes
    per_lb = juice / (weight / 453.6)
    st.write(f"• Juice per fruit: **{per_lime:.2f} fl oz**")
    st.write(f"• Juice per pound: **{per_lb:.2f} fl oz/lb**")

    # Historical Averages for This Fruit
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

# =========================
# Averages by Fruit + All Entries
# =========================
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

# =========================
# Prediction vs Actual Over Time
# =========================
if not df.empty and "Juice (fl oz)" in df.columns:
    st.subheader("📈 Prediction vs Actual Over Time")

    chart_df = df[df["Limes"] > 0].copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])

    avg_per_fruit = df["Juice (fl oz)"].sum() / df["Limes"].sum() if df["Limes"].sum() else 0
    avg_per_100g = df["Juice (fl oz)"].sum() / df["Weight (g)"].sum() * 100 if df["Weight (g)"].sum() else 0

    chart_df["Predicted (Fruits)"] = chart_df["Limes"] * avg_per_fruit
    chart_df["Predicted (Weight)"] = (chart_df["Weight (g)"] / 100) * avg_per_100g

    st.line_chart(chart_df.set_index("Date")[["Juice (fl oz)", "Predicted (Fruits)", "Predicted (Weight)"]])
