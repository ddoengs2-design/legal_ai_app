import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from docx import Document
from docx.shared import Inches
import pandas as pd
import json
from datetime import datetime
import io

# 설정 및 환경 변수 로드
load_dotenv()
# Streamlit Secrets 또는 .env에서 API 키 로드
api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# 페이지 설정
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.1", layout="wide", page_icon="🏛️")

# 고정 저작권 및 버전 정보
VERSION = "v4.1 Professional Edition"
UPDATE_DATE = "2026년 2월"
COPYRIGHT_TEXT = "All intellectual property rights belong to Kim Doyoung."

# 커스텀 CSS (이미지의 레이아웃 스타일 유지)
st.markdown(f"""
    <style>
    .main-title {{ font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.5rem; }}
    .sub-title {{ font-size: 1.1rem; color: #6B7280; margin-bottom: 2rem; }}
    .copyright-main {{ font-size: 0.9rem; color: #374151; font-weight: 500; margin-top: -1rem; margin-bottom: 2rem; border-left: 3px solid #1E3A8A; padding-left: 10px; }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3rem; background-color: #1E3A8A; color: white; }}
    .report-box {{ padding: 20px; border-radius: 10px; border: 1px solid #E5E7EB; background-color: #F9FAFB; }}
    </style>
""", unsafe_allow_html=True)

# --- 1. 헤더 섹션 ---
st.markdown(f'<h1 class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 {VERSION}</h1>', unsafe_allow_html=True)
# 저작권 문구를 상단 제목 아래에 더 잘 보이게 추가
st.markdown(f'<p class="copyright-main">© 2026 Kim Doyoung. {COPYRIGHT_TEXT}</p>', unsafe_allow_html=True)

# --- 2. 대상지 기본 정보 입력 (새로 추가된 섹션) ---
with st.container():
    st.subheader("📍 대상지 기본 정보")
    col_addr1, col_addr2 = st.columns(2)
    with col_addr1:
        site_address = st.text_input("대상지 주소", placeholder="예: 서울특별시 OO구 OO동 123-4")
    with col_addr2:
        site_zone = st.text_input("용도지역/지구", placeholder="예: 일반상업지역, 제3종일반주거지역")
st.divider()

# --- 3. 파일 업로드 섹션 ---
col1, col2 = st.columns([1, 1])
with col1:
    st.subheader("📁 공모지침서 업로드 (PDF)")
    uploaded_file = st.file_uploader("분석할 지침서 파일을 선택하세요", type=['pdf'])

with col2:
    st.subheader("⚙️ 분석 옵션")
    analysis_focus = st.multiselect(
        "특별히 집중해서 분석할 항목을 선택하세요",
        ["건축규모/면적", "용도/프로그램", "법적 제한사항", "설계 공모 일정", "제출물 목록"],
        default=["건축규모/면적", "법적 제한사항"]
    )

# --- 4. 분석 로직 및 결과 표시 ---
if st.button("🚀 AI 통합 분석 시작"):
    if uploaded_file is not None:
        with st.spinner("AI가 지침서와 법규를 분석 중입니다..."):
            # (실제 분석 로직은 기존 v4.0의 코드를 따릅니다)
            # 여기서는 결과 데이터 구조에 입력한 주소 정보를 통합하는 예시를 보여줍니다.
            
            # 가상의 결과 데이터 (Gemini API 결과라고 가정)
            analysis_result = f"""
            ### [분석 결과 리포트]
            **1. 입력 대상지 정보**
            * 주소: {site_address if site_address else "미입력"}
            * 용도지역: {site_zone if site_zone else "미입력"}
            
            **2. 지침서 분석 데이터**
            (여기에 Gemini API가 분석한 상세 내용이 출력됩니다...)
            """
            
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.markdown(analysis_result)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 다운로드용 데이터 생성 (주소 정보 포함)
            json_data = {
                "version": VERSION,
                "date": UPDATE_DATE,
                "site_info": {
                    "address": site_address,
                    "zone": site_zone
                },
                "analysis_content": "분석된 상세 내용들..."
            }
            
            # --- 5. 다운로드 섹션 ---
            st.subheader("📥 분석 결과 저장")
            d_col1, d_col2 = st.columns(2)
            with d_col1:
                st.download_button(
                    label="📄 JSON 데이터 다운로드",
                    data=json.dumps(json_data, ensure_ascii=False, indent=2),
                    file_name=f"건축분석_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
    else:
        st.error("지침서 파일을 업로드해주세요.")

# --- 6. 푸터 (저작권 및 버전 정보 유지) ---
st.divider()
st.markdown(f"""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>
            <b>Powered by Google Gemini 2.5 Flash</b><br>
            건축 공모 & 법규 분석 시스템 {VERSION}<br><br>
            ⚖️ <b>법적 고지:</b> 본 분석은 AI 기반 참고 자료이며, 법적 효력이 없습니다.<br>
            실제 설계 시 반드시 전문가의 검토를 받으시기 바랍니다.<br><br>
            <b>{VERSION}</b> | {UPDATE_DATE}<br>
            {COPYRIGHT_TEXT}
        </small>
    </div>
""", unsafe_allow_html=True)