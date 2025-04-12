import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import json

creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
client = gspread.authorize(creds)

sheet = client.open("Citrus Juice Tracker").worksheet("juice_data")

# Load existing data into a DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🍋 Citrus Juice Tracker")

# Input section
st.subheader("Add New Entry")
fruit_options = ["Lime", "Lemon", "Orange", "Grapefruit", "Apple", "Cucumber", "Other"]
selected = st.selectbox("Fruit type", fruit_options)

if selected == "Other":
    fruit = st.text_input("Enter fruit name")
else:
    fruit = selected

limes = st.number_input("Number of fruits", min_value=0, step=1, format="%i", value=None, placeholder="e.g. 4")
weight = st.number_input("Total weight (g)", min_value=0.0, value=None, placeholder="e.g. 350.5")
juice = st.number_input("Juice collected (fl oz)", min_value=0.0, value=None, placeholder="e.g. 5.5")

if st.button("Add Entry"):
    if not fruit:
        st.warning("Please enter a fruit name.")
    else:
        new_entry = [
            datetime.now().strftime("%Y-%m-%d"),
            f"{fruit} {fruit_emoji}".strip(),
            limes,
            weight,
            juice
        ]
        sheet.append_row(new_entry)
        st.success("Entry added!")

        # Display entry stats immediately
        st.subheader("📌 This Entry’s Stats")

        if limes > 0 and weight > 0:
            per_lime = juice / limes
            per_100g = (juice / weight) * 100
            limes_for_8oz = 8 / per_lime if per_lime > 0 else None

            st.write(f"• Juice per fruit: **{per_lime:.2f} fl oz**")
            st.write(f"• Juice per 100g: **{per_100g:.2f} fl oz/100g**")
            st.write(f"• Est. fruits for 8 oz: **{limes_for_8oz:.1f} {fruit.lower()}s**")

            # Show comparison to historical average for this fruit
            if not df.empty:
                fruit_only = df[df["Fruit"] == f"{fruit} {fruit_emoji}".strip()]
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


# Show stats first
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

# Then show the full table
st.subheader("📄 All Entries")
st.dataframe(df)
