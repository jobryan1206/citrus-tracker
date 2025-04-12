import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import json

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

fruit_options = ["Lime", "Lemon", "Orange", "Grapefruit", "Apple", "Cucumber", "Other"]
selected = st.selectbox("Fruit type", fruit_options, key="fruit_select")

if selected == "Other":
    fruit = st.text_input("Enter fruit name", key="fruit_custom").strip().capitalize()
else:
    fruit = selected

limes = st.number_input("Number of fruits", min_value=0, step=1, format="%i", value=None, placeholder="e.g. 4", key="num_fruits")
weight = st.number_input("Total weight (g)", min_value=0.0, value=None, placeholder="e.g. 350.5", key="weight_input")
juice = st.number_input("Juice collected (fl oz)", min_value=0.0, value=None, placeholder="e.g. 5.5", key="juice_input")

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
        if "num_fruits" in st.session_state:
            st.session_state["num_fruits"] = None
        if "weight_input" in st.session_state:
            st.session_state["weight_input"] = None
        if "juice_input" in st.session_state:
            st.session_state["juice_input"] = None
        if selected == "Other" and "fruit_custom" in st.session_state:
            st.session_state["fruit_custom"] = ""

        # Show entry stats
        st.subheader("📌 This Entry’s Stats")
        if limes > 0 and weight > 0:
            per_lime = juice / limes
            per_100g = (juice / weight) * 100
            limes_for_8oz = 8 / per_lime if per_lime > 0 else None

            st.write(f"• Juice per fruit: **{per_lime:.2f} fl oz**")
            st.write(f"• Juice per 100g: **{per_100g:.2f} fl oz/100g**")
            st.write(f"• Est. fruits for 8 oz: **{limes_for_8oz:.1f} {fruit.lower()}s**")

            if not df.empty:
                fruit_only = df[df["Fruit"] == fruit]
                if not fruit_only.empty and fruit_only["Limes"].sum() > 0 and fruit_only["Weight (g)"].sum() > 0:
                    total_juice = fruit_only["Juice (fl oz)"].sum()
                    total_limes = fruit_only["Limes"].sum()
                    total_weight = fruit_only["Weight (g)"].sum()

                    avg_per_lime = total_juice / total_limes
                    avg_per_100g = (total_juice / total_weight) * 100
                    avg_limes_for_8oz = 8 / avg_per_lime

                    st.subheader("📊 Compared to Averages for This Fruit")
                    st.write(f"• Avg juice per fruit: **{avg_per_lime:.2f} fl oz**")
                    st.write(f"• Avg juice per 100g: **{avg_per_100g:.2f} fl oz/100g**")
                    st.write(f"• Avg fruits for 8 oz: **{avg_limes_for_8oz:.1f} {fruit.lower()}s**")

