
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt

# =====================================================
st.set_page_config("CE‑PE Average Comparison", layout="wide")
st.title("📊 Average CE / PE Price Comparison Across Files")

# ---- SIDEBAR ----
num_strikes = st.sidebar.slider("Top strikes by Open Interest", 1, 20, 6)
st.sidebar.markdown("Upload Option‑Chain CSV files 👇")

uploaded = st.file_uploader(
    "Drop one or more option‑chain CSV files",
    type=["csv"], accept_multiple_files=True
)
if not uploaded:
    st.info("⬅️ Upload CSVs to start.")
    st.stop()

# ---- TIMESTAMP EXTRACTOR ----
def extract_timestamp(name: str):
    try:
        base = name.replace(".csv", "")
        return datetime.strptime(
            base.split("_")[-2] + "_" + base.split("_")[-1], "%d%m%Y_%H%M%S"
        )
    except Exception:
        return datetime.now()

# ---- LOAD ----
frames = []
for f in uploaded:
    ts = extract_timestamp(f.name)
    df = pd.read_csv(f)
    df["timestamp"] = ts
    frames.append(df)
raw = pd.concat(frames, ignore_index=True)
st.success(f"✅ Loaded {len(uploaded)} file(s), {len(raw)} rows total.")

# ---- GET TOP STRIKES FROM FIRST FILE ----
first_df = pd.read_csv(uploaded[0])
top_strikes = (
    first_df.groupby("CE_strikePrice")["CE_openInterest"]
    .mean()
    .sort_values(ascending=False)
    .head(num_strikes)
    .index.tolist()
)
st.caption(f"Top {num_strikes} strikes (from first file): {', '.join(map(str,top_strikes))}")

# ---- CALCULATE AVERAGE PER FILE ----
summary = []
for f in uploaded:
    ts = extract_timestamp(f.name)
    df = pd.read_csv(f)
    df = df[df["CE_strikePrice"].isin(top_strikes)].copy()

    avg_ce = df["CE_lastPrice"].mean(skipna=True)
    avg_pe = df["PE_lastPrice"].mean(skipna=True)
    diff   = avg_ce - avg_pe

    summary.append({"timestamp": ts, "Avg_CE": avg_ce, "Avg_PE": avg_pe, "CE_minus_PE": diff})

avg_df = pd.DataFrame(summary).sort_values("timestamp")
avg_df["timestamp_str"] = avg_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

# ---- CHART 1 – CE AVG ----
st.subheader("💙 Average CE Price over Time")
ce_chart = (
    alt.Chart(avg_df)
    .mark_line(point=True, color="#1f77b4")
    .encode(
        x="timestamp:T",
        y=alt.Y("Avg_CE:Q", title="Average CE Price"),
        tooltip=["timestamp_str", "Avg_CE"],
    )
    .properties(height=300)
)
st.altair_chart(ce_chart, use_container_width=True)

# ---- CHART 2 – PE AVG ----
st.subheader("❤️ Average PE Price over Time")
pe_chart = (
    alt.Chart(avg_df)
    .mark_line(point=True, color="#e15759")
    .encode(
        x="timestamp:T",
        y=alt.Y("Avg_PE:Q", title="Average PE Price"),
        tooltip=["timestamp_str", "Avg_PE"],
    )
    .properties(height=300)
)
st.altair_chart(pe_chart, use_container_width=True)

# ---- CHART 3 – CE‑PE DIFFERENCE ----
st.subheader("🟢 Difference (CE – PE) per File Timestamp")
diff_chart = (
    alt.Chart(avg_df)
    .mark_bar(color="#2ca02c")
    .encode(
        x=alt.X("timestamp:T", title="Timestamp"),
        y=alt.Y("CE_minus_PE:Q", title="CE – PE Average Price"),
        color=alt.condition("datum.CE_minus_PE > 0", alt.value("#33cc33"), alt.value("#ff6666")),
        tooltip=[
            "timestamp_str",
            alt.Tooltip("CE_minus_PE:Q", title="CE − PE"),
            "Avg_CE",
            "Avg_PE",
        ],
    )
    .properties(height=300)
)
zero_line = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(color="gray",strokeDash=[4,4]).encode(y="y:Q")
st.altair_chart(diff_chart + zero_line, use_container_width=True)

# ---- SUMMARY TABLE + DOWNLOAD ----
st.subheader("📄 CE/PE Summary")
show_cols = ["timestamp_str","Avg_CE","Avg_PE","CE_minus_PE"]
st.dataframe(
    avg_df[show_cols].rename(columns={
        "timestamp_str":"Timestamp","Avg_CE":"Avg CE","Avg_PE":"Avg PE","CE_minus_PE":"CE−PE"
    }),
    use_container_width=True
)
st.download_button(
    "⬇️ Download CE‑PE Comparison CSV",
    avg_df[["timestamp_str","Avg_CE","Avg_PE","CE_minus_PE"]].to_csv(index=False).encode("utf‑8"),
    "ce_pe_comparison.csv",
    "text/csv",
)
