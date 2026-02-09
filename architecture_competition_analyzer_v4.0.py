import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# 1. 환경 설정 및 API 로드
load_dotenv()
api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 2. 페이지 설정
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.1.3", layout="wide")
VERSION = "v4.1.3 Professional Edition"
COPYRIGHT_TEXT = "All intellectual property rights belong to Kim Doyoung."

# 3. 헤더 및 저작권 (상단 고정)
st.markdown(f'<h1 style="color: #1E3A8A;">🏛️ 건축 공모 & 법규 분석 시스템 {VERSION}</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color: #6B7280;">© 2026 Kim Doyoung. {COPYRIGHT_TEXT}</p>', unsafe_allow_html=True)

# 4. 대상지 정보 입력
st.subheader("📍 대상지 기본 정보")
col_info1, col_info2 = st.columns(2)
with col_info1:
    site_address = st.text_input("대상지 주소", placeholder="예: 서울특별시 OO구 OO동 123-4")
with col_info2:
    site_zone = st.text_input("용도지역/지구", placeholder="예: 일반상업지역, 제3종일반주거지역")

st.divider()

# 5. 업로드 섹션 분리 (에러가 발생했던 지점 수정 완료)
col_main, col_sub = st.columns(2)

with col_main:
    st.subheader("📑 메인 공모지침서 (단일)")
    main_guideline = st.file_uploader(
        "분석의 기준이 되는 지침서 1개를 업로드하세요", 
        type=['pdf'], 
        key="main_pdf",
        accept_multiple_files=False
    )

with col_sub:
    st.subheader("📚 관련 법규 및 참고자료 (다중)")
    reference_laws = st.file_uploader(
        "참고할 법규나 조례 PDF들을 모두 선택하세요", 
        type=['pdf'], 
        accept_multiple_files=True,
        key="sub_pdfs"
    )

# 6. 분석 옵션
st.subheader("⚙️ 분석 집중 항목")
analysis_focus = st.multiselect(
    "AI가 중점적으로 검토할 항목을 선택하세요",
    ["건축규모/면적", "용도/프로그램", "법적 제한사항", "설계 공모 일정", "제출물 목록"],
    default=["건축규모/면적", "법적 제한사항"]
)

# 7