import streamlit as st
import FinanceDataReader as fdr
import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

# -------------------------
# Page config (MUST be the first Streamlit command)
# -------------------------
st.set_page_config(
    page_title="Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------------
# CSS (only <style> injection; no custom HTML wrappers for content)
# -------------------------
st.markdown(
    """
    <style>
      footer {display:none;}
      [data-testid="stHeader"] {display:none;}
      #MainMenu {visibility:hidden;}

      /* Layout padding */
      section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"]{
        padding-top: 18px;
        padding-bottom: 28px;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
        margin: 0 auto;
      }

      /* Make Streamlit containers look like cards */
      div[data-testid="stVerticalBlockBorderWrapper"]{
        background: rgba(12,14,21,1);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px 14px 12px 14px;
        box-shadow: 0 8px 18px rgba(0,0,0,0.28);
      }

      /* Title size */
      h1{
        font-size: 52px !important;
        line-height: 1.05 !important;
        margin-bottom: 0.25rem !important;
      }

      /* Metrics spacing inside cards */
      div[data-testid="stMetric"]{
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 10px 12px 8px 12px;
        margin-bottom: 10px;
      }

      /* Reduce gap between blocks */
      div[data-testid="stVerticalBlock"]{ gap: 0.75rem; }

      @media (max-width: 900px){
        section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"]{
          padding-left: 1rem; padding-right: 1rem;
        }
        h1{ font-size: 38px !important; }
      }
    
      /* -----------------------------
         Custom KPI blocks (Today card)
         - Use HTML markup for precise alignment/line breaks
         ----------------------------- */
      /* -----------------------------
         Custom KPI blocks (Today card)
         - Use HTML markup for precise alignment/line breaks
         ----------------------------- */
      .kpi{
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 10px 12px 8px 12px;
        box-sizing: border-box;

        /* ✅ 동일 박스 크기 */
        min-height: 90px;

        /* ✅ 내부 정렬 */
        display: flex;
        flex-direction: column;
        
      }
      .kpi_label{
        font-size: 12px;
        opacity: 0.85;
        line-height: 1.2;
        text-align: left;
        margin: 0;
      }
      .kpi_value{
        font-size: 20px;
        font-weight: 800;
        line-height: 1.15;
        margin-top: 6px;
        text-align: left;
      }
      .kpi_delta{
        font-size: 12px;
        margin-top: 4px;
        text-align: left;
        font-weight: 700;
        opacity: 0.95;
      }
      .kpi_delta.pos{
        color: #ff1744; /* up = red */
      }
      .kpi_delta.neg{
        color: #2962ff; /* down = blue */
      }

      /* High/Low coloring inside KPI */
      .kpi_value_high{ color: #ff1744 !important; }  /* high = red */
      .kpi_value_low{  color: #2962ff !important; }  /* low  = blue */
</style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Data helpers
# -------------------------
@st.cache_data(show_spinner=False, ttl=60 * 15)
def get_symbols(market: str):
    """종목 목록을 가져와서 '시가총액(가능하면) 내림차순'으로 정렬합니다.
    - FinanceDataReader.StockListing() 결과에 시총 컬럼이 있으면 사용합니다.
    - 시총 컬럼이 없으면 Name 기준 정렬로 fallback 합니다.
    """
    df = fdr.StockListing(market).copy()

    # 최소 컬럼 보장
    for c in ("Code", "Name"):
        if c not in df.columns:
            raise ValueError(f"StockListing 결과에 '{c}' 컬럼이 없습니다. columns={list(df.columns)}")

    # 시총 컬럼 후보 탐색 (환경/버전별로 이름이 달라질 수 있어 후보를 둡니다)
    cap_col = None
    for cand in ("Marcap", "MarketCap", "MarketCap(KRW)"):
        if cand in df.columns:
            cap_col = cand
            break

    cols = ["Code", "Name"] + ([cap_col] if cap_col else [])
    df = df[cols].dropna(subset=["Code", "Name"])

    # 표시 라벨
    df["Label"] = df["Name"].astype(str) + " (" + df["Code"].astype(str) + ")"

    # ✅ 시총 내림차순 정렬 (없으면 Name 정렬)
    if cap_col:
        df["_cap"] = pd.to_numeric(
            df[cap_col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )
        df = df.sort_values(["_cap", "Name"], ascending=[False, True]).drop(columns=["_cap"])
    else:
        df = df.sort_values("Name")

    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=60 * 10)
def get_ohlcv(code: str, date_start, date_end):
    return fdr.DataReader(code, date_start, date_end)

@st.cache_data(show_spinner=False, ttl=60 * 5)
def get_latest_snapshot(code: str):
    end = datetime.today().date()
    start = (datetime.today() - timedelta(days=10)).date()
    df = fdr.DataReader(code, start, end)
    if df is None or len(df) < 2:
        return None
    today_close = float(df.iloc[-1]["Close"])
    prev_close = float(df.iloc[-2]["Close"])
    diff = today_close - prev_close
    diff_rate = (diff / prev_close) * 100 if prev_close else 0.0
    high = float(df.iloc[-1]["High"])
    low = float(df.iloc[-1]["Low"])
    vol = float(df.iloc[-1]["Volume"]) if "Volume" in df.columns else None
    asof = str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1])
    return today_close, diff, diff_rate, high, low, vol, asof

# -------------------------
# UI constants
# -------------------------
WATCHLIST = [
    ("삼성전자", "005930"),
    ("SK하이닉스", "000660"),
    ("NAVER", "035420"),
    ("현대차", "005380"),
]

COLOR_MAP = {
    "파랑": "#2962ff",
    "초록": "#00c853",
    "빨강": "#ff1744",
    "핑크": "#e91e63",
}


def parse_mav_input(raw: str) -> list[int]:
    """
    사용자가 입력한 이평선 기간을 파싱합니다.
    - 허용: '7', '7,14,30', '7 14 30'
    - 반환: 중복 제거/정렬된 int 리스트 (각 값은 2 이상)
    - 비어 있으면 [] 반환
    """
    s = (raw or "").strip()
    if not s:
        return []
    parts = [p.strip() for p in s.replace(" ", ",").split(",") if p.strip()]
    out: list[int] = []
    for p in parts:
        n = int(p)
        if n < 2:
            raise ValueError("이평선 기간은 2 이상 정수만 가능합니다.")
        out.append(n)
    return sorted(set(out))

# -------------------------
# Session state (keep last params)
# -------------------------
if "params" not in st.session_state:
    st.session_state["params"] = {
        "market": "KOSPI",
        "selected_label": None,
        "days": 365,
        "up_name": "파랑",
        "down_name": "핑크",
        "show_volume": True,
        "mav": [],
    }

# -------------------------
# Draft params (for instant UI updates without auto-refreshing chart)
# -------------------------
if "draft" not in st.session_state:
    st.session_state["draft"] = dict(st.session_state["params"])

# -------------------------
# Header
# -------------------------
st.title("Stock Dashboard")
st.caption("FinanceDataReader 기반 · 캔들차트 / 지표 / 워치리스트")

st.write("")  # spacer

# -------------------------
# Watchlist row (REAL cards using st.container(border=True))
# -------------------------
wl_cols = st.columns(4, gap="medium")
for (nm, cd), col in zip(WATCHLIST, wl_cols):
    with col:
        with st.container(border=True):
            st.markdown(f"**{nm}**")
            st.caption(cd)

            snap = None
            try:
                snap = get_latest_snapshot(cd)
            except Exception:
                snap = None

            if snap is None:
                st.metric("현재가", "—")
                st.caption("데이터 없음")
            else:
                close, diff, diff_rate, *_rest = snap
                st.metric("현재가", f"{close:,.0f}", delta=f"{diff:,.0f} ({diff_rate:.2f}%)")
                st.caption(f"전일 대비 기준 ({snap[-1]})")

st.write("")  # spacer

# -------------------------
# Body: chart + side panel
# -------------------------
side_col, empty, main_col = st.columns([2.4, 0.08, 7.52], gap="small")

# Load symbols for initial selection
symbols_df = get_symbols(st.session_state["params"]["market"])
if st.session_state["params"]["selected_label"] is None:
    st.session_state["params"]["selected_label"] = symbols_df["Label"].iloc[0]

with side_col:
    with st.container(border=True):
        st.subheader("Chart Parameters")

        # Widgets (draft) — changes show immediately; chart updates on Apply button
        d = st.session_state["draft"]

        market = st.selectbox("시장", ["KOSPI", "KOSDAQ"],
                              index=0 if d.get("market","KOSPI") == "KOSPI" else 1, key="draft_market")

        df_symbols = get_symbols(st.session_state['draft_market'])
        labels = df_symbols['Label'].tolist()
        if st.session_state.get('draft_selected_label') not in labels:
            st.session_state['draft_selected_label'] = labels[0] if labels else None
        selected_label = st.selectbox("종목 선택", labels,
                                     index=labels.index(st.session_state['draft_selected_label']) if labels and st.session_state.get('draft_selected_label') in labels else 0,
                                     key="draft_selected_label")

        days = st.number_input("조회 기간(일)", min_value=5, max_value=3650,
                               value=int(d.get("days", 365)), step=30, key="draft_days")

        c1, c2 = st.columns(2)
        with c1:
            up_name = st.selectbox("상승봉 색", ["파랑", "초록", "빨강"],
                                   index=["파랑","초록","빨강"].index(d.get("up_name","파랑")), key="draft_up_name")
        with c2:
            down_name = st.selectbox("하락봉 색", ["핑크", "빨강", "파랑"],
                                     index=["핑크","빨강","파랑"].index(d.get("down_name","핑크")), key="draft_down_name")

        show_volume = st.checkbox("거래량 표시", value=bool(d.get("show_volume", True)), key="draft_show_volume")

        mav_text = st.text_input(
            "이평선 기간(쉼표/공백 구분, 비우면 미표시)",
            value=str(d.get("mav_text", "")),
            placeholder="예: 7, 14, 30, 200",
            key="draft_mav_text",
        )

        apply = st.button("적용 / 차트 갱신", use_container_width=True)
        if apply:
            # ✅ mav_text -> mav(list[int])로 변환 (비어있으면 [])
            try:
                mav = parse_mav_input(st.session_state.get("draft_mav_text", ""))
            except Exception as e:
                st.error(f"이평선 입력 오류: {e}")
                mav = None

            if mav is not None:
                st.session_state["draft"] = {
                    "market": st.session_state["draft_market"],
                    "selected_label": st.session_state.get("draft_selected_label"),
                    "days": int(st.session_state["draft_days"]),
                    "up_name": st.session_state["draft_up_name"],
                    "down_name": st.session_state["draft_down_name"],
                    "show_volume": bool(st.session_state["draft_show_volume"]),
                    "mav_text": st.session_state.get("draft_mav_text", ""),
                    "mav": mav,
                }

                # apply to params (chart uses params)
                st.session_state["params"].update(st.session_state["draft"])
                st.success("설정이 적용되었습니다.")


with main_col:
    # ✅ Today summary (top, horizontal)
    with st.container(border=True):
        st.subheader("Today")
        p = st.session_state["params"]
        code = p["selected_label"].split("(")[-1].split(")")[0].strip()
        name = p["selected_label"].split("(")[0].strip()

        st.caption(f"{name} ({code})")

        snap = None
        try:
            snap = get_latest_snapshot(code)
        except Exception:
            snap = None

        if snap is None:
            st.caption("지표를 불러오지 못했습니다.")
        else:
            close, diff, diff_rate, high, low, vol, asof = snap
            sign = "+" if diff >= 0 else ""
            delta_cls = "pos" if diff >= 0 else "neg"
            

            c1, c2, c3, c4 = st.columns(4, gap="medium")

            with c1:
                st.markdown(
                    f'''
                    <div class="kpi">
                      <div class="kpi_label">금일 종가</div>
                      <div class="kpi_value">{close:,.0f}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f'''
                    <div class="kpi">
                      <div class="kpi_label">전일 대비</div>
                      <div class="kpi_value">{sign}{diff:,.0f}</div>
                      <div class="kpi_delta {delta_cls}">{sign}{diff_rate:.2f}%</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

            with c3:
                st.markdown(
                    f'''
                    <div class="kpi">
                      <div class="kpi_label">고가 / 저가</div>
                      <div class="kpi_value">
                        <span class="kpi_value_high">{high:,.0f}</span><br/>
                        <span class="kpi_value_low">{low:,.0f}</span>
                      </div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

            with c4:
                vol_text = f"{vol:,.0f}" if vol is not None else "—"
                st.markdown(
                    f'''
                    <div class="kpi">
                      <div class="kpi_label">거래량(주)</div>
                      <div class="kpi_value">{vol_text}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
            st.write("")  # spacer
            st.caption(f"기준일: {asof}")

    with st.container(border=True):
        p = st.session_state["params"]
        code = p["selected_label"].split("(")[-1].split(")")[0].strip()
        name = p["selected_label"].split("(")[0].strip()

        st.subheader(f"{name} ({code}) · 최근 {p['days']}일")

        date_end = datetime.today().date()
        date_start = (datetime.today() - timedelta(days=int(p["days"]))).date()

        try:
            df = get_ohlcv(code, date_start, date_end)
            if df is None or df.empty or len(df) < 2:
                st.error("데이터가 부족합니다.")
            else:
                up_color = COLOR_MAP[p["up_name"]]
                down_color = COLOR_MAP[p["down_name"]]

                mc = mpf.make_marketcolors(up=up_color, down=down_color, inherit=True)
                s = mpf.make_mpf_style(
                    base_mpf_style="nightclouds",
                    marketcolors=mc,
                    rc={
                        "figure.facecolor": "#131722",
                        "axes.facecolor": "#131722",
                        "savefig.facecolor": "#131722",
                        "axes.labelcolor": "#f6f6f6",
                        "xtick.color": "#b2b5be",
                        "ytick.color": "#b2b5be",
                        "grid.color": "#2a2e39",
                    },
                )

                fig, _ = mpf.plot(
                    df,
                    type="candle",
                    style=s,
                    volume=bool(p["show_volume"]),
                    **({"mav": p["mav"]} if p["mav"] else {}),
                    figscale=1.05,
                    figratio=(18, 9),
                    returnfig=True,
                    warn_too_much_data=99999,
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

                with st.expander("원본 데이터 (최근 200행)"):
                    st.dataframe(df.tail(200), use_container_width=True)
        except Exception as e:
            st.error(f"에러 발생: {e}")
