import streamlit as st
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Authenticate and connect to Google Sheets
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
fruit_options = ["Lime", "Lemon", "Orange", "Grapefruit", "Apple", "Cucumber", "Other"]
selected = st.selectbox("Fruit type", fruit_options, key="fruit_select")

if selected == "Other":
    fruit = st.text_input("Enter fruit name", key="fruit_custom").strip().capitalize()
else:
    fruit = selected

limes = st.number_input("Number of fruits", min_value=0, step=1, value=None, placeholder="e.g. 4", key="num_fruits")
weight = st.number_input("Total weight (g)", min_value=0.0, value=None, placeholder="e.g. 350.5", key="weight_input")

# Prediction section (before entering juice)
if fruit and (limes or weight):
    fruit_only = df[df["Fruit"] == fruit]
    if not fruit_only.empty:
        per_fruit_vals = fruit_only["Juice (fl oz)"] / fruit_only["Limes"]
        per_100g_vals = fruit_only["Juice (fl oz)"] / fruit_only["Weight (g)"] * 100

        pred_data = {
            "Method": ["By fruit count", "By weight"],
            "Avg (fl oz)": [],
            "+1 SD": [],
            "-1 SD": [],
            "Last (fl oz)": []
        }

        # Fruit count-based predictions
        if limes > 0:
            pred_data["Avg (fl oz)"].append(per_fruit_vals.mean() * limes)
            pred_data["+1 SD"].append((per_fruit_vals.mean() + per_fruit_vals.std()) * limes)
            pred_data["-1 SD"].append((per_fruit_vals.mean() - per_fruit_vals.std()) * limes)
            pred_data["Last (fl oz)"].append(per_fruit_vals.iloc[-1] * limes)
        else:
            pred_data["Avg (fl oz)"].append(np.nan)
            pred_data["+1 SD"].append(np.nan)
            pred_data["-1 SD"].append(np.nan)
            pred_data["Last (fl oz)"].append(np.nan)

        # Weight-based predictions
        if weight > 0:
            per_g_vals = per_100g_vals / 100
            pred_data["Avg (fl oz)"].append(per_g_vals.mean() * weight)
            pred_data["+1 SD"].append((per_g_vals.mean() + per_g_vals.std()) * weight)
            pred_data["-1 SD"].append((per_g_vals.mean() - per_g_vals.std()) * weight)
            pred_data["Last (fl oz)"].append(per_g_vals.iloc[-1] * weight)
        else:
            pred_data["Avg (fl oz)"].append(np.nan)
            pred_data["+1 SD"].append(np.nan)
            pred_data["-1 SD"].append(np.nan)
            pred_data["Last (fl oz)"].append(np.nan)

        pred_df = pd.DataFrame(pred_data).round(2)
        st.subheader("📈 Predicted Juice Yield (fl oz)")
        st.dataframe(pred_df.style.hide(axis="index"), use_container_width=True)

juice = st.number_input("Juice collected (fl oz)", min_value=0.0, value=None, placeholder="e.g. 5.5", key="juice_input")

if st.button("Add Entry"):
    if not fruit:
        st.warning("Please enter a fruit name.")
    else:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            fruit,
            limes,
            weight,
            juice
        ])
        st.success("Entry added!")

        # Clear input fields
        for key in ["num_fruits", "weight_input", "juice_input", "fruit_custom"]:
            if key in st.session_state:
                del st.session_state[key]

        # Entry stats
        st.subheader("📌 This Entry’s Stats")
        if limes > 0:
            st.write(f"• Juice per fruit: **{juice / limes:.2f} fl oz**")
        if weight > 0:
            st.write(f"• Juice per pound: **{(juice / weight) * 453.592:.2f} fl oz/lb**")

        # Historical stats
        fruit_only = df[df["Fruit"] == fruit]
        if not fruit_only.empty:
            total_juice = fruit_only["Juice (fl oz)"].sum()
            total_limes = fruit_only["Limes"].sum()
            total_weight = fruit_only["Weight (g)"].sum()

            st.subheader("📊 Historical Averages for This Fruit")
            if total_limes > 0:
                st.write(f"• Avg juice per fruit: **{total_juice / total_limes:.2f} fl oz**")
            if total_weight > 0:
                st.write(f"• Avg juice per pound: **{(total_juice / total_weight) * 453.592:.2f} fl oz/lb**")
