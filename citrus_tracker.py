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
    new_entry = [
        datetime.now().strftime("%Y-%m-%d"),
        fruit,
        limes,
        weight,
        juice
    ]
    sheet.append_row(new_entry)
    st.success("Entry added!")

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
