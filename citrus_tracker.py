import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("citrus_creds.json", scope)
client = gspread.authorize(creds)

# Open the sheet
sheet = client.open("Citrus Juice Tracker").worksheet("juice_data")

# Load existing data into a DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.title("🍋 Citrus Juice Tracker")

# Input section
st.subheader("Add New Entry")
fruit = st.selectbox("Fruit type", ["Lime", "Lemon"])
limes = st.number_input("Number of fruits", min_value=0, step=1)
weight = st.number_input("Total weight (g)", min_value=0.0)
juice = st.number_input("Juice collected (fl oz)", min_value=0.0)

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


# View and analyze data
if not df.empty:
    st.subheader("📄 All Entries")
    st.dataframe(df)

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

# Deletion section
if not df.empty:
    st.subheader("🗑 Delete an Entry")
    index_to_delete = st.selectbox("Select a row to delete (by index)", df.index)
    st.write(df.loc[index_to_delete])
    if st.button("Delete Selected Entry"):
        df = df.drop(index=index_to_delete).reset_index(drop=True)
        df.to_csv(FILE, index=False)
        st.success("Entry deleted.")
