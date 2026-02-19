import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt
import io

st.set_page_config("CE‑PE Average Comparison", layout="wide")
st.title("📊 Average CE / PE Price Comparison Across Files")

# ---- SIDEBAR ----
num_strikes = st.sidebar.slider("Top strikes by Open Interest", 1, 20, 6)
uploaded = st.file_uploader(
    "Drop option‑chain CSV files (multiple allowed)", type=["csv"], accept_multiple_files=True
)
if not uploaded:
    st.info("⬅️ Upload CSV files to start.")
    st.stop()

# ---- Helper ----
def extract_timestamp(name):
    try:
        base = name.replace(".csv","")
        return datetime.strptime(base.split("_")[-2]+"_"+base.split("_")[-1], "%d%m%Y_%H%M%S")
    except Exception:
        return datetime.now()

def safe_read(f):
    try:
        # Rewind file pointer just in case Streamlit read earlier
        f.seek(0)
        content = f.read()
        if len(content.strip()) == 0:
            return None
        f.seek(0)
        return pd.read_csv(f)
    except Exception as e:
        st.warning(f"⚠️ Skipped {f.name} ({e})")
        return None

# ---- Load all files ----
frames=[]
for f in uploaded:
    df = safe_read(f)
    if df is None or df.empty:
        continue
    ts = extract_timestamp(f.name)
    df["timestamp"]=ts
    frames.append(df)

if not frames:
    st.error("No valid CSV data found — please check uploads.")
    st.stop()

raw = pd.concat(frames, ignore_index=True)
st.success(f"✅ Loaded {len(frames)} valid file(s), {len(raw)} rows.")

# ---- Get top strikes from first valid file ----
first_df = frames[0]
if "CE_openInterest" not in first_df or "CE_strikePrice" not in first_df:
    st.error("Missing columns (CE_openInterest / CE_strikePrice) in first CSV.")
    st.stop()

top_strikes = (
    first_df.groupby("CE_strikePrice")["CE_openInterest"]
    .mean()
    .sort_values(ascending=False)
    .head(num_strikes)
    .index.tolist()
)
st.caption(f"Top {num_strikes} strikes (from first file): {', '.join(map(str,top_strikes))}")

# ---- Per‑file averages ----
summary=[]
for df in frames:
    ts = df["timestamp"].iloc[0]
    df = df[df["CE_strikePrice"].isin(top_strikes)].copy()
    if df.empty: 
        continue
    avg_ce = df.get("CE_lastPrice", pd.Series(dtype=float)).mean()
    avg_pe = df.get("PE_lastPrice", pd.Series(dtype=float)).mean()
    summary.append({
        "timestamp": ts,
        "Avg_CE": avg_ce,
        "Avg_PE": avg_pe,
        "CE_minus_PE": avg_ce - avg_pe,
    })

avg_df = pd.DataFrame(summary).sort_values("timestamp")
if avg_df.empty:
    st.error("No valid data after processing top strikes.")
    st.stop()
avg_df["timestamp_str"] = avg_df["timestamp"].dt.strftime("%Y‑%m‑%d %H:%M:%S")

# ---- Charts ----
st.subheader("💙 Average CE Price")
ce_chart = alt.Chart(avg_df).mark_line(point=True, color="#1f77b4").encode(
    x="timestamp:T", y="Avg_CE:Q", tooltip=["timestamp_str","Avg_CE"]
).properties(height=300)
st.altair_chart(ce_chart, use_container_width=True)

st.subheader("❤️ Average PE Price")
pe_chart = alt.Chart(avg_df).mark_line(point=True, color="#e15759").encode(
    x="timestamp:T", y="Avg_PE:Q", tooltip=["timestamp_str","Avg_PE"]
).properties(height=300)
st.altair_chart(pe_chart, use_container_width=True)

st.subheader("🟢 Difference (CE – PE)")
diff_chart = (
    alt.Chart(avg_df)
    .mark_bar()
    .encode(
        x="timestamp:T",
        y=alt.Y("CE_minus_PE:Q", title="CE − PE"),
        color=alt.condition("datum.CE_minus_PE > 0", alt.value("#33cc33"), alt.value("#ff6666")),
        tooltip=["timestamp_str","Avg_CE","Avg_PE","CE_minus_PE"],
    )
    .properties(height=300)
)
zero_line = alt.Chart(pd.DataFrame({"y":[0]})).mark_rule(
    color="gray", strokeDash=[4,4]
).encode(y="y:Q")
st.altair_chart(diff_chart + zero_line, use_container_width=True)

# ---- Table + Download ----
st.subheader("📄 Summary Data")
st.dataframe(
    avg_df[["timestamp_str","Avg_CE","Avg_PE","CE_minus_PE"]]
    .rename(columns={
        "timestamp_str":"Timestamp","Avg_CE":"Avg CE","Avg_PE":"Avg PE","CE_minus_PE":"CE−PE"
    }),
    use_container_width=True
)
st.download_button(
    "⬇️ Download CE‑PE Comparison",
    avg_df.to_csv(index=False).encode("utf‑8"),
    "ce_pe_comparison.csv",
    "text/csv",
)


