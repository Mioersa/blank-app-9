import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt

st.set_page_config("Normalized CE‑PE Comparison", layout="wide")
st.title("📊 Normalized Average CE / PE Price Comparison")

# ---- Sidebar ----
num_strikes = st.sidebar.slider("Top strikes by Open Interest", 1, 20, 6)
chart_type = st.sidebar.radio("Difference Chart Type", ["Bar", "Line"])
uploaded = st.file_uploader(
    "Drop Option‑Chain CSV files (multiple allowed)",
    type=["csv"], accept_multiple_files=True,
)
if not uploaded:
    st.info("⬅️ Upload CSV files to start.")
    st.stop()

# ---- Helpers ----
def extract_timestamp(name):
    try:
        base = name.replace(".csv","")
        return datetime.strptime(base.split("_")[-2]+"_"+base.split("_")[-1], "%d%m%Y_%H%M%S")
    except Exception:
        return datetime.now()

def safe_read(f):
    try:
        f.seek(0)
        content = f.read()
        if len(content.strip()) == 0:
            return None
        f.seek(0)
        return pd.read_csv(f)
    except Exception:
        return None

# ---- Load ----
frames=[]
for f in uploaded:
    df=safe_read(f)
    if df is None or df.empty: 
        continue
    df["timestamp"]=extract_timestamp(f.name)
    frames.append(df)

if not frames:
    st.error("No valid CSV data found.")
    st.stop()

# ---- Top strikes from first file ----
first_df=frames[0]
top_strikes=(
    first_df.groupby("CE_strikePrice")["CE_openInterest"]
    .mean().sort_values(ascending=False)
    .head(num_strikes).index.tolist()
)
st.caption(f"Top {num_strikes} strikes (from first file): {', '.join(map(str,top_strikes))}")

# ---- Compute per‑file averages ----
summary=[]
for df in frames:
    ts=df["timestamp"].iloc[0]
    subset=df[df["CE_strikePrice"].isin(top_strikes)].copy()
    if subset.empty: continue
    avg_ce=subset["CE_lastPrice"].mean()
    avg_pe=subset["PE_lastPrice"].mean()
    summary.append({"timestamp":ts,"Avg_CE":avg_ce,"Avg_PE":avg_pe})
avg_df=pd.DataFrame(summary).sort_values("timestamp")

# ---- Normalize (z‑score) ----
avg_df["CE_norm"]=(avg_df["Avg_CE"]-avg_df["Avg_CE"].mean())/avg_df["Avg_CE"].std(ddof=0)
avg_df["PE_norm"]=(avg_df["Avg_PE"]-avg_df["Avg_PE"].mean())/avg_df["Avg_PE"].std(ddof=0)
avg_df["Diff_norm"]=avg_df["CE_norm"]-avg_df["PE_norm"]
avg_df["timestamp_str"]=avg_df["timestamp"].dt.strftime("%Y‑%m‑%d %H:%M:%S")

# ---- Charts ----
st.subheader("💙 Normalized Average CE Price")
ce_chart=(
    alt.Chart(avg_df)
    .mark_line(point=True,color="#1f77b4")
    .encode(x="timestamp:T",y="CE_norm:Q",tooltip=["timestamp_str","CE_norm"])
    .properties(height=300)
)
st.altair_chart(ce_chart,use_container_width=True)

st.subheader("❤️ Normalized Average PE Price")
pe_chart=(
    alt.Chart(avg_df)
    .mark_line(point=True,color="#e15759")
    .encode(x="timestamp:T",y="PE_norm:Q",tooltip=["timestamp_str","PE_norm"])
    .properties(height=300)
)
st.altair_chart(pe_chart,use_container_width=True)

# ---- Difference chart ----
st.subheader("🟢 Normalized Difference (CE − PE)")
if chart_type=="Bar":
    diff_chart=(
        alt.Chart(avg_df)
        .mark_bar()
        .encode(
            x="timestamp:T",
            y=alt.Y("Diff_norm:Q",title="Normalized (CE−PE)"),
            color=alt.condition("datum.Diff_norm>0",
                alt.value("#33cc33"),alt.value("#ff6666")),
            tooltip=["timestamp_str","Diff_norm"],
        )
        .properties(height=300)
    )
else:
    diff_chart=(
        alt.Chart(avg_df)
        .mark_line(point=True,color="#2ca02c")
        .encode(
            x="timestamp:T",
            y=alt.Y("Diff_norm:Q",title="Normalized (CE−PE)"),
            tooltip=["timestamp_str","Diff_norm"],
        )
        .properties(height=300)
    )

zero_line=alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(
    color="gray",strokeDash=[4,4]
).encode(y="y:Q")
st.altair_chart(diff_chart+zero_line,use_container_width=True)

# ---- Table + Download ----
st.subheader("📄 Summary Data")
show=avg_df[["timestamp_str","Avg_CE","Avg_PE","CE_norm","PE_norm","Diff_norm"]]
st.dataframe(show.rename(columns={
    "timestamp_str":"Timestamp","Avg_CE":"Avg CE","Avg_PE":"Avg PE",
    "CE_norm":"Norm CE","PE_norm":"Norm PE","Diff_norm":"Norm Diff (CE‑PE)"
}),use_container_width=True)

st.download_button(
    "⬇️ Download Summary CSV",
    show.to_csv(index=False).encode("utf‑8"),
    "normalized_ce_pe_summary.csv","text/csv",
)
