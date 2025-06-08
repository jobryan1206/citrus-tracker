
import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)
sheet = client.open("Citrus Juice Tracker").worksheet("juice_data")

# Load existing data
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🍋 Citrus Juice Tracker")

# Input section
st.subheader("Add New Entry")

fruit_options = ["Lime", "Lemon", "Orange", "Grapefruit", "Apple", "Cucumber", "Ginger", "Other"]
selected = st.selectbox("Fruit type", fruit_options, key="fruit_select")

if selected == "Other":
    fruit = st.text_input("Enter fruit name", key="fruit_custom").strip().capitalize()
else:
    fruit = selected

limes = st.number_input("Number of fruits", min_value=0, step=1, format="%i", value=None, placeholder="e.g. 4", key="num_fruits")
weight = st.number_input("Total weight (g)", min_value=0.0, value=None, placeholder="e.g. 350.5", key="weight_input")
juice = st.number_input("Juice collected (fl oz)", min_value=0.0, value=None, placeholder="e.g. 5.5", key="juice_input")

# Predictions based on historical data
if fruit and limes and weight:
    fruit_df = df[df["Fruit"] == fruit]
    if not fruit_df.empty:
        per_fruit_vals = fruit_df["Juice (fl oz)"] / fruit_df["Limes"]
        per_100g_vals = fruit_df["Juice (fl oz)"] / fruit_df["Weight (g)"] * 100

        fruit_vals = per_fruit_vals.dropna()
        weight_vals = per_100g_vals.dropna()

        # Averages and standard deviations
        fruit_avg = fruit_vals.mean()
        fruit_std = fruit_vals.std()

        weight_avg = weight_vals.mean()
        weight_std = weight_vals.std()

        # Prediction ranges
        pred_table = pd.DataFrame({
            "Method": ["By fruit count", "By weight"],
            "Avg (fl oz)": [
                round(fruit_avg * limes, 2),
                round((weight_avg / 100) * weight, 2)
            ],
            "±1σ (fl oz)": [
                f"{round((fruit_avg - fruit_std) * limes, 2)} – {round((fruit_avg + fruit_std) * limes, 2)}",
                f"{round(((weight_avg - weight_std) / 100) * weight, 2)} – {round(((weight_avg + weight_std) / 100) * weight, 2)}"
            ],
            "±2σ (fl oz)": [
                f"{round((fruit_avg - 2 * fruit_std) * limes, 2)} – {round((fruit_avg + 2 * fruit_std) * limes, 2)}",
                f"{round(((weight_avg - 2 * weight_std) / 100) * weight, 2)} – {round(((weight_avg + 2 * weight_std) / 100) * weight, 2)}"
            ]
        })

        st.subheader("📈 Predicted Juice Yield (fl oz)")
        st.table(pred_table.style.hide(axis="index"))

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

        # Show entry stats
        st.subheader("📌 This Entry’s Stats")
        if limes > 0 and weight > 0:
            per_lime = juice / limes
            per_pound = juice / (weight / 453.592)

            st.write(f"• Juice per fruit: **{per_lime:.2f} fl oz**")
            st.write(f"• Juice per pound: **{per_pound:.2f} fl oz/lb**")

            if not df.empty:
                fruit_only = df[df["Fruit"] == fruit]
                if not fruit_only.empty and fruit_only["Limes"].sum() > 0 and fruit_only["Weight (g)"].sum() > 0:
                    total_juice = fruit_only["Juice (fl oz)"].sum()
                    total_limes = fruit_only["Limes"].sum()
                    total_weight = fruit_only["Weight (g)"].sum()

                    avg_per_lime = total_juice / total_limes
                    avg_per_pound = total_juice / (total_weight / 453.592)

                    st.subheader("📊 Compared to Averages for This Fruit")
                    st.write(f"• Avg juice per fruit: **{avg_per_lime:.2f} fl oz**")
                    st.write(f"• Avg juice per pound: **{avg_per_pound:.2f} fl oz/lb**")
