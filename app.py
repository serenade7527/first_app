import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="가계부 대시보드", layout="wide", page_icon="💰")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 50%, #fdf4ff 100%);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #14532d 0%, #166534 100%);
    border-right: none;
}
[data-testid="stSidebar"] * { color: #dcfce7 !important; }
[data-testid="stSidebar"] .stMultiSelect span { color: #14532d !important; }
h1 {
    background: linear-gradient(90deg, #16a34a, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
}
.kpi-row { display: flex; gap: 16px; margin-bottom: 1.4rem; }
.kpi-card {
    flex: 1; background: white; border-radius: 16px;
    padding: 20px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border-left: 6px solid;
}
.kpi-card.green  { border-color: #16a34a; }
.kpi-card.red    { border-color: #dc2626; }
.kpi-card.blue   { border-color: #2563eb; }
.kpi-card.purple { border-color: #7c3aed; }
.kpi-label { font-size: 0.80rem; font-weight: 600; color: #6b7280;
    text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.kpi-value { font-size: 1.7rem; font-weight: 800; color: #111827; line-height: 1.1; }
.kpi-sub   { font-size: 0.76rem; color: #9ca3af; margin-top: 4px; }
.upload-hint {
    background: white; border-radius: 16px; padding: 56px 32px;
    text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); color: #6b7280;
}
.upload-hint h2 { color: #14532d; font-size: 1.5rem; }
hr { border: none; border-top: 1.5px solid #e5e7eb; margin: 1rem 0; }
[data-testid="stDataFrame"] th {
    background-color: #f0fdf4 !important;
    color: #15803d !important; font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)


# ── 사이드바: 파일 업로드 ─────────────────────────────────────
st.sidebar.markdown("## 📂 파일 업로드")
st.sidebar.markdown("---")
uploaded = st.sidebar.file_uploader(
    "📊 가계부 엑셀 파일",
    type=["xlsx", "xls"],
    help="날짜 / 구분 / 카테고리 / 항목 / 금액(원) / 결제수단 컬럼이 필요합니다.",
)
st.sidebar.markdown("---")

st.markdown("# 💰 가계부 대시보드")

# ── 파일 로드 (업로드 없으면 기본 데이터 자동 표시) ──────────
import os
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "가계부_2024_더미데이터.xlsx")

if uploaded:
    source = uploaded
    st.sidebar.success("✅ 업로드 파일 사용 중")
elif os.path.exists(DEFAULT_FILE):
    source = DEFAULT_FILE
    st.sidebar.info("📂 기본 샘플 데이터 표시 중")
else:
    st.markdown("""
    <div class="upload-hint">
        <h2>📂 가계부 엑셀 파일을 업로드하세요</h2>
        <p>왼쪽 사이드바에서 파일을 업로드하면 대시보드가 자동으로 표시됩니다.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

try:
    df = pd.read_excel(source)
except Exception as e:
    st.error(f"파일을 읽을 수 없습니다: {e}")
    st.stop()

REQUIRED = ["날짜", "구분", "카테고리", "항목", "금액(원)", "결제수단"]
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"필요한 컬럼이 없습니다: `{missing}`\n\n실제 컬럼: `{list(df.columns)}`")
    st.stop()

df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
df["금액(원)"] = pd.to_numeric(df["금액(원)"], errors="coerce").fillna(0)
df = df.dropna(subset=["날짜"])
df["월"] = df["날짜"].dt.to_period("M").astype(str)

st.sidebar.success(f"✅ 로드 완료 ({len(df)}건)")

# ── 사이드바 필터 ─────────────────────────────────────────────
st.sidebar.markdown("## 🔍 필터")

all_types = sorted(df["구분"].dropna().unique())
all_cats  = sorted(df["카테고리"].dropna().unique())
all_pay   = sorted(df["결제수단"].dropna().unique())

sel_types = st.sidebar.multiselect("구분", all_types, default=all_types)
sel_cats  = st.sidebar.multiselect("카테고리", all_cats, default=all_cats)
sel_pay   = st.sidebar.multiselect("결제수단", all_pay, default=all_pay)

date_min, date_max = df["날짜"].min(), df["날짜"].max()
date_range = st.sidebar.date_input("날짜 범위",
    value=(date_min.date(), date_max.date()),
    min_value=date_min.date(), max_value=date_max.date())

filtered = df[
    df["구분"].isin(sel_types) &
    df["카테고리"].isin(sel_cats) &
    df["결제수단"].isin(sel_pay)
]
if len(date_range) == 2:
    s, e = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["날짜"] >= s) & (filtered["날짜"] <= e)]

st.caption(f"전체 {len(df)}건 | 필터 적용 후: {len(filtered)}건")
st.markdown("<hr>", unsafe_allow_html=True)

# ── KPI 카드 ─────────────────────────────────────────────────
income  = filtered[filtered["구분"] == "수입"]["금액(원)"].sum()
expense = filtered[filtered["구분"] == "지출"]["금액(원)"].sum()
savings = filtered[filtered["구분"] == "저축"]["금액(원)"].sum()
net     = income - expense - savings

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card green">
    <div class="kpi-label">📥 총 수입</div>
    <div class="kpi-value">₩{income:,.0f}</div>
    <div class="kpi-sub">기간 합계</div>
  </div>
  <div class="kpi-card red">
    <div class="kpi-label">📤 총 지출</div>
    <div class="kpi-value">₩{expense:,.0f}</div>
    <div class="kpi-sub">기간 합계</div>
  </div>
  <div class="kpi-card blue">
    <div class="kpi-label">🏦 총 저축</div>
    <div class="kpi-value">₩{savings:,.0f}</div>
    <div class="kpi-sub">기간 합계</div>
  </div>
  <div class="kpi-card purple">
    <div class="kpi-label">💹 순수지</div>
    <div class="kpi-value" style="color:{'#16a34a' if net >= 0 else '#dc2626'}">
        {'▲' if net >= 0 else '▼'} ₩{abs(net):,.0f}
    </div>
    <div class="kpi-sub">수입 - 지출 - 저축</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Row 1: 카테고리별 지출 / 월별 추이 ───────────────────────
col1, col2 = st.columns([1, 1.3], gap="large")

with col1:
    with st.container(border=True):
        st.subheader("🗂️ 카테고리별 지출")
        cat_exp = (
            filtered[filtered["구분"] == "지출"]
            .groupby("카테고리")["금액(원)"].sum()
            .reset_index()
            .sort_values("금액(원)", ascending=False)
        )
        if cat_exp.empty:
            st.info("지출 데이터가 없습니다.")
        else:
            chart1 = (
                alt.Chart(cat_exp)
                .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
                .encode(
                    y=alt.Y("카테고리:N", sort="-x",
                            axis=alt.Axis(title=None, labelFontSize=12)),
                    x=alt.X("금액(원):Q",
                            axis=alt.Axis(title="금액 (원)", format=",.0f")),
                    color=alt.Color("카테고리:N", legend=None,
                                    scale=alt.Scale(scheme="tableau10")),
                    tooltip=["카테고리",
                             alt.Tooltip("금액(원):Q", format=",.0f", title="금액")],
                )
                .properties(height=300)
                .configure_view(strokeWidth=0)
                .configure_axis(grid=False)
            )
            st.altair_chart(chart1, use_container_width=True)

with col2:
    with st.container(border=True):
        st.subheader("📅 월별 수입 · 지출 · 저축 추이")
        monthly = (
            filtered[filtered["구분"].isin(["수입", "지출", "저축"])]
            .groupby(["월", "구분"])["금액(원)"].sum()
            .reset_index()
        )
        type_colors = {"수입": "#16a34a", "지출": "#dc2626", "저축": "#2563eb"}
        if monthly.empty:
            st.info("데이터가 없습니다.")
        else:
            chart2 = (
                alt.Chart(monthly)
                .mark_bar()
                .encode(
                    x=alt.X("월:O", axis=alt.Axis(title=None, labelAngle=-30)),
                    y=alt.Y("금액(원):Q",
                            axis=alt.Axis(title="금액 (원)", format=",.0f")),
                    color=alt.Color(
                        "구분:N",
                        scale=alt.Scale(
                            domain=list(type_colors.keys()),
                            range=list(type_colors.values()),
                        ),
                        legend=alt.Legend(title="구분"),
                    ),
                    xOffset="구분:N",
                    tooltip=["월", "구분",
                             alt.Tooltip("금액(원):Q", format=",.0f", title="금액")],
                )
                .properties(height=300)
                .configure_view(strokeWidth=0)
                .configure_axis(grid=False)
            )
            st.altair_chart(chart2, use_container_width=True)

# ── Row 2: 결제수단 / 구분별 비율 ────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
col3, col4 = st.columns(2, gap="large")

with col3:
    with st.container(border=True):
        st.subheader("💳 결제수단별 지출")
        pay_exp = (
            filtered[filtered["구분"] == "지출"]
            .groupby("결제수단")["금액(원)"].sum()
            .reset_index()
        )
        if pay_exp.empty:
            st.info("지출 데이터가 없습니다.")
        else:
            chart3 = (
                alt.Chart(pay_exp)
                .mark_arc(innerRadius=55)
                .encode(
                    theta=alt.Theta("금액(원):Q"),
                    color=alt.Color("결제수단:N",
                                    scale=alt.Scale(scheme="set2"),
                                    legend=alt.Legend(title="결제수단")),
                    tooltip=["결제수단",
                             alt.Tooltip("금액(원):Q", format=",.0f", title="금액")],
                )
                .properties(height=280)
            )
            st.altair_chart(chart3, use_container_width=True)

with col4:
    with st.container(border=True):
        st.subheader("📊 항목별 상세 지출 순위")
        item_exp = (
            filtered[filtered["구분"] == "지출"]
            .groupby("항목")["금액(원)"].sum()
            .reset_index()
            .sort_values("금액(원)", ascending=False)
            .head(10)
        )
        if item_exp.empty:
            st.info("지출 데이터가 없습니다.")
        else:
            item_exp.insert(0, "순위",
                ["🥇","🥈","🥉"] + [f"{i}위" for i in range(4, len(item_exp)+1)])
            item_exp["금액(원)"] = item_exp["금액(원)"].map("₩{:,.0f}".format)
            st.dataframe(item_exp, use_container_width=True,
                         hide_index=True, height=300)

# ── 전체 내역 테이블 ─────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
with st.expander("🗂️ 전체 내역 보기"):
    preview = filtered.copy()
    preview["날짜"] = preview["날짜"].dt.strftime("%Y-%m-%d")
    preview["금액(원)"] = preview["금액(원)"].map("₩{:,.0f}".format)
    st.dataframe(
        preview[["날짜", "구분", "카테고리", "항목", "금액(원)", "결제수단", "메모"]]
        .reset_index(drop=True),
        use_container_width=True,
    )
