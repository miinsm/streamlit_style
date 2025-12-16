v3는 Streamlit 요소를 HTML div로 감싸지 않습니다.
- 워치카드/파라미터/차트/KPI 모두 st.container(border=True)로 '진짜 카드'를 만들고,
- CSS는 container wrapper에만 적용해서 깨짐을 줄였습니다.

실행:
  python -m pip install -r requirements.txt
  streamlit run app.py
