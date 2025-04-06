import streamlit as st
import pandas as pd
from datetime import datetime
import os

# File name
FILE = "citrus_data.csv"

# Load or initialize dataset
if os.path.exists(FILE):
    df = pd.read_csv(FILE)
else:
    df = pd.DataFrame(columns=["Date", "Fruit", "Limes", "Weight (g)", "Juice (fl oz)"])

st.title("🍋 Citrus Juice Tracker")

# Input section
st.subheader("Add New Entry")
fruit = st.selectbox("Fruit type", ["Lime", "Lemon"])
limes = st.number_input("Number of fruits", min_value=0, step=1)
weight = st.number_input("Total weight (g)", min_value=0.0)
juice = st.number_input("Juice collected (fl oz)", min_value=0.0)

if st.button("Add Entry"):
    new_entry = {
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Fruit": fruit,
        "Limes": limes,
        "Weight (g)": weight,
        "Juice (fl oz)": juice
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FILE, index=False)
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
