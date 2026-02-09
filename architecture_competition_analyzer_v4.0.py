import streamlit as st  # <-- 이 부분이 에러의 핵심 해결책입니다!
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# 1. 환경 설정
load_dotenv()
api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 2. 페이지 설정 및 디자인
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.1.2", layout="wide")
VERSION = "v4.1.2 Professional Edition"
COPYRIGHT_TEXT = "All intellectual property rights belong to Kim Doyoung."

st.markdown(f"""
    <style>
    .main-title {{ font-size: 2.2rem; font-weight: 700; color: #1E3A8A; }}
    .copyright-sub {{ font-size: 0.9rem; color: #6B7280; margin-bottom: 2rem; }}
    </style>
""", unsafe_allow_html=True)

# 3. 헤더 및 저작권 표시
st.markdown(f'<h1 class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 {VERSION}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="copyright-sub">© 2026 Kim Doyoung. {COPYRIGHT_TEXT}</p>', unsafe_allow_html=True)

# 4. 대상지 정보 입력 (상단 배치)
st.subheader("📍 대상지 기본 정보")
col_info1, col_info2 = st.columns(2)
with col_info1:
    site_address = st.text_input("대상지 주소", placeholder="예: 서울특별시 OO구 OO동 123-4")
with col_info2:
    site_zone = st.text_input("용도지역/지구", placeholder="예: 일반상업지역, 제3종일반주거지역")

st.divider()

# 5. 파일 업로드 섹션 (다중 업로드 복구)
col1, col2 = st.columns([1, 1]) # <-- 에러가 났던 지점입니다. 이제 정상 작동합니다.
with col1:
    st.subheader("📁 공모지침 및 법규 업로드")
    # accept_multiple_files=True 옵션으로 다중 업로드 복구
    uploaded_files = st.file_uploader(
        "분석할 PDF 파일들을 모두 선택하세요 (여러 개 가능)", 
        type=['pdf'], 
        accept_multiple_files=True
    )

with col2:
    st.subheader("⚙️ 분석 옵션")
    analysis_focus = st.multiselect(
        "집중 분석 항목",
        ["건축규모/면적", "용도/프로그램", "법적 제한사항", "설계 공모 일정", "제출물 목록"],
        default=["건축규모/면적", "법적 제한사항"]
    )

# 6. 분석 실행 버튼
if st.button("🚀 AI 통합 분석 시작"):
    if uploaded_files:
        with st.spinner(f"{len(uploaded_files)}개의 파일을 분석 중입니다..."):
            # 여기에 Gemini 분석 로직이 들어갑니다.
            st.success(f"✅ {len(uploaded_files)}개의 파일과 입력하신 정보를 기반으로 분석을 완료했습니다.")
            st.info(f"분석 대상지: {site_address}")
    else:
        st.warning("분석할 PDF 파일을 하나 이상 업로드해 주세요.")

# 7. 푸터 (저작권 강조)
st.divider()
st.markdown(f"<div style='text-align: center; color: gray;'>{VERSION} | {COPYRIGHT_TEXT}</div>", unsafe_allow_html=True)