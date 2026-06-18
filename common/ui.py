# common/ui.py
"""팀 공용 UI 테마.

모든 페이지가 동일한 폰트·색·위젯 룩을 쓰도록 공통 스타일을 한 곳에서 관리한다.
각 페이지는 st.set_page_config() 바로 다음에 inject_theme() 을 호출하면 된다.

기준 톤: 화이트 배경 + 블루(#2563EB) 포인트 (page3 충전수요 대시보드 기준).
"""
import streamlit as st

# 공용 색 팔레트 ------------------------------------------------------------
PRIMARY = "#2563EB"   # 메인 블루
CYAN = "#06B6D4"      # 보조 시안
GREEN = "#22C55E"     # 보조 그린
ORANGE = "#F97316"    # 보조 오렌지
INK = "#111827"       # 진한 글자
MUTED = "#6B7280"     # 흐린 글자
LINE = "#E5E7EB"      # 보더


def inject_theme():
    """전 페이지 공통 폰트·색·위젯 스타일 주입."""
    st.markdown(
        """
        <style>
          html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
          }
          [data-testid="stAppViewContainer"] { background: #FFFFFF; }
          .main .block-container { padding-top: 2.2rem; padding-bottom: 2rem; }

          h1 { font-weight: 850 !important; letter-spacing: 0 !important; color: #2563EB; }
          h2, h3 { letter-spacing: 0 !important; color: #111827; }

          /* 라디오 → pill 버튼 */
          [data-testid="stRadio"] > label { font-weight: 750; color: #111827; }
          [data-testid="stRadio"] div[role="radiogroup"] { gap: 0.55rem; }
          [data-testid="stRadio"] div[role="radiogroup"] label {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 999px;
            padding: 0.32rem 0.85rem; box-shadow: 0 2px 8px rgba(17,24,39,0.04); color: #6B7280;
          }
          [data-testid="stRadio"] div[role="radiogroup"] label:hover {
            background: #F8FAFC; border-color: #2563EB; color: #2563EB;
          }
          [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
            background: #2563EB; border-color: #2563EB; color: #FFFFFF;
            box-shadow: 0 8px 18px rgba(37,99,235,0.18);
          }

          /* 체크박스 카드 룩 */
          [data-testid="stCheckbox"] label {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px;
            padding: 0.28rem 0.62rem; box-shadow: 0 2px 8px rgba(17,24,39,0.04);
          }
          [data-testid="stCheckbox"] label:hover { border-color: #06B6D4; background: #F8FAFC; }

          /* 차트 컨테이너 */
          [data-testid="stVegaLiteChart"],
          [data-testid="stDeckGlJsonChart"],
          [data-testid="stPlotlyChart"] {
            border: 1px solid #E5E7EB; border-radius: 14px; padding: 0.35rem;
            background: #FFFFFF; box-shadow: 0 10px 24px rgba(17,24,39,0.07);
          }

          /* 지표(metric) 카드 */
          [data-testid="stMetric"] {
            background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px;
            padding: 0.9rem 1rem; box-shadow: 0 4px 14px rgba(17,24,39,0.05);
          }
          [data-testid="stMetricLabel"] { color: #6B7280; }
        </style>
        """,
        unsafe_allow_html=True,
    )
