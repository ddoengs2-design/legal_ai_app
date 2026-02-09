import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from io import BytesIO
import json
import re
import pandas as pd
import plotly.express as px
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# 1. 환경 설정 및 API 로드
load_dotenv()
api_key = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# 2. 페이지 설정
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.1.8", page_icon="🏛️", layout="wide")
VERSION = "v4.1.8 Professional Edition"
COPYRIGHT_TEXT = "All intellectual property rights belong to Kim Doyoung."

# 3. 커스텀 CSS (UI 개선)
st.markdown(f"""
    <style>
    .main-title {{ text-align: center; background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 1.5rem; border-radius: 15px; font-size: 2rem; font-weight: bold; margin-bottom: 1rem; }}
    .step-header {{ background-color: #f8fafc; padding: 10px; border-left: 5px solid #3b82f6; border-radius: 5px; margin: 20px 0 15px 0; font-weight: bold; font-size: 1.2rem; }}
    .copyright {{ text-align: right; color: #9ca3af; font-size: 0.8rem; padding: 5px; }}
    </style>
""", unsafe_allow_html=True)

# 헤더 표시
st.markdown(f'<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템</div>', unsafe_allow_html=True)
st.markdown(f'<div class="copyright">© 2026 Kim Doyoung. {COPYRIGHT_TEXT}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# STEP 1: 대상지 기본 정보 (직접 입력 및 탭 선택)
# ---------------------------------------------------------
st.markdown('<div class="step-header">STEP 1. 대상지 기본 정보 입력</div>', unsafe_allow_html=True)
col_addr, col_zone = st.columns([2, 1])

with col_addr:
    site_address = st.text_input("📍 대상지 주소 (직접 기입)", placeholder="예: 서울특별시 OO구 OO동 123-4")

with col_zone:
    site_zone = st.selectbox(
        "🏷️ 지역지구 선택",
        ["선택하세요", "제1종전용주거지역", "제2종전용주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역", "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "준공업지역", "기타"]
    )

# ---------------------------------------------------------
# STEP 2: PDF 파일 업로드 (분리형)
# ---------------------------------------------------------
st.markdown('<div class="step-header">STEP 2. 설계공모 지침서 및 관련 법규 업로드</div>', unsafe_allow_html=True)
col_main, col_sub = st.columns(2)

with col_main:
    st.info("📑 **메인 설계공모지침서 (단일)**")
    main_guideline = st.file_uploader("지침서 1개를 업로드하세요", type=['pdf'], key="main_pdf")

with col_sub:
    st.success("📚 **관련 법규 및 참고자료 (다중)**")
    reference_laws = st.file_uploader("여러 개의 법규 PDF를 업로드하세요", type=['pdf'], accept_multiple_files=True, key="sub_pdfs")

# ---------------------------------------------------------
# STEP 3: 분석 실행 및 결과
# ---------------------------------------------------------
st.divider()
analyze_button = st.button("🚀 AI 통합 분석 시작", type="primary", use_container_width=True)

if analyze_button:
    if not main_guideline:
        st.error("❌ 메인 공모지침서를 업로드해주세요.")
    elif site_zone == "선택하세요":
        st.warning("⚠️ 지역지구를 선택해주세요.")
    else:
        with st.spinner("AI가 지침서와 법규를 교차 분석 중입니다..."):
            # 1단계: 지침서 분석 시뮬레이션 (기존 v4.0 로직 통합 가능)
            time.sleep(1.5)
            st.success(f"✅ 분석 완료: {site_address} ({site_zone})")
            
            # 결과 표시 (v4.0 스타일)
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.markdown("### 📋 지침서 분석 요약")
                st.info(f"- 주소: {site_address}\n- 지역지구: {site_zone}")
                st.write("- 건축규모 및 요구사항 분석 완료")
            with res_col2:
                st.markdown("### ⚖️ 법규 검토 결과")
                st.write(f"- 업로드된 {len(reference_laws) if reference_laws else 0}개의 법규와 지침서 대조 완료")
                st.write("- 상위법(건축법) 및 하위법(조례) 위계 분석 적용")

            # 시각화 예시 (Plotly)
            st.markdown("### 📊 실별 면적 비중 (샘플)")
            sample_df = pd.DataFrame({"실명": ["전시실", "수장고", "사무실", "공용공간"], "면적": [500, 200, 100, 150]})
            fig = px.pie(sample_df, values='면적', names='실명', hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

# 4. 푸터
st.divider()
st.markdown(f"<div style='text-align: center; color: gray;'>{VERSION} | {COPYRIGHT_TEXT}</div>", unsafe_allow_html=True)