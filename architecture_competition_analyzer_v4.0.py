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

# 5. 업로드 섹션 분리 (핵심 업데이트)
col_main, col_sub = st.columns(2)

with col_main:
    st.subheader("📑 메인 공모지침서 (단일)")
    # 단일 파일 업로드 (accept_multiple_files=False가 기본값)
    main_guideline = st.file_uploader(
        "분석의 기준이 되는 지침서 1개를 업로드하세요", 
        type=['pdf'], 
        key="main_pdf"
    )

with col_sub:
    st.subheader("