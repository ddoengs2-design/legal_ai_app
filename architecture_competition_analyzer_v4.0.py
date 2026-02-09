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

# 데이터 처리
import pandas as pd

# 그래프
import plotly.express as px
import plotly.graph_objects as go

# 문서 생성
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# .env 파일 로드
load_dotenv()

# ================================
# 페이지 설정
# ================================
st.set_page_config(
    page_title="건축 공모 & 법규 분석 시스템 v4.0",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================================
# 고급 커스텀 CSS
# ================================
st.markdown("""
<style>
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .version-badge {
        display: inline-block;
        background: #f59e0b;
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        margin-left: 1rem;
    }
    .section-header {
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        padding: 1rem;
        border-left: 5px solid #3b82f6;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# 사이드바 설정
# ================================
with st.sidebar:
    st.markdown("## ⚙️ 설정")
    env_api_key = os.getenv("GOOGLE_API_KEY", "")
    api_key = env_api_key if env_api_key else st.text_input("Google Gemini API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        st.success("🎯 API 연결 완료!")
    
    st.markdown("---")
    selected_model = "models/gemini-2.5-flash"
    st.info(f"✅ {selected_model}")
    
    analysis_depth = st.selectbox("분석 상세도", ["표준", "상세", "매우 상세"], index=1)
    include_visualization = st.checkbox("📊 실별 면적표 시각화", value=True)

# ================================
# [신규] 핵심 데이터 입력 섹션
# ================================
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 <span class="version-badge">v4.0</span></div>', unsafe_allow_html=True)

st.markdown('<div class="section-header"><h2>📍 1. 대상지 기본 정보 입력 (필수)</h2></div>', unsafe_allow_html=True)

col_addr, col_zone = st.columns([1, 1])

with col_addr:
    target_address = st.text_input(
        "📌 대상지 주소",
        placeholder="예: 서울특별시 ○○구 ○○동 123-4번지",
        help="법규 분석의 기준이 되는 정확한 주소를 입력하세요."
    )

with col_zone:
    # 건축물 용도 및 지역지구 선택 리스트 (일반적인 항목들)
    zone_options = [
        "제1종전용주거지역", "제2종전용주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역",
        "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역",
        "전용공업지역", "일반공업지역", "준공업지역",
        "보존녹지지역", "생산녹지지역", "자연녹지지역",
        "지구단위계획구역", "정비구역", "경관지구", "방화지구"
    ]
    target_zones = st.multiselect(
        "🏢 지역지구 선택",
        options=zone_options,
        help="해당 대지에 적용되는 지역지구를 모두 선택하세요."
    )

st.divider()

# ================================
# 나머지 UI 및 분석 로직 (업로드 부분)
# ================================
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 📄 A. 공모지침서 업로드")
    competition_file = st.file_uploader("지침서 PDF (단일)", type=['pdf'])

with col_b:
    st.markdown("### ⚖️ B. 관련 법규 업로드")
    regulation_files = st.file_uploader("법규/조례 PDF (다중)", type=['pdf'], accept_multiple_files=True)

# ================================
# 핵심 함수 보강 (입력값 반영)
# ================================

def upload_pdf_to_gemini(uploaded_file, display_name=None):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        name = display_name or uploaded_file.name
        uploaded_gemini_file = genai.upload_file(tmp_path, display_name=name)
        while uploaded_gemini_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_gemini_file = genai.get_file(uploaded_gemini_file.name)
        os.unlink(tmp_path)
        return uploaded_gemini_file
    except Exception as e:
        st.error(f"❌ 업로드 오류: {str(e)}")
        return None

def analyze_combined_data(comp_file, reg_files, address, zones, model_name):
    """사용자 입력 정보(주소, 지역지구)를 포함하여 분석 수행"""
    
    # 지역지구 리스트를 문자열로 변환
    zones_str = ", ".join(zones) if zones else "지침서 분석 필요"
    
    prompt = f"""
당신은 대한민국 건축 법규 및 공모 분석 전문가입니다. 
다음의 **사용자 입력 정보**를 최우선 기준으로 하여 첨부된 지침서와 법규를 분석하십시오.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 [최우선] 사용자 입력 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 대상지 주소: {address}
- 지정 지역지구: {zones_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 분석 과업
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 공모지침서 분석: 사업개요, 설계조건, 실별 면적표 추출
2. 법규 위계 분석: 위 주소와 지역지구에 의거하여 [상위법(국계법/건축법)]과 [하위법(해당 지자체 조례)]를 매칭
3. 실질 적용 기준 도출: 사용자가 입력한 '{zones_str}'에 대한 건폐율, 용적률, 층수 제한을 조례 기준으로 확정하여 제시

출력은 반드시 이전과 동일한 JSON 형식(지침 분석)과 마크다운 보고서 형식(법규 분석)을 유지하십시오.
"""
    
    try:
        model = genai.GenerativeModel(model_name)
        # 지침서와 법규 파일들 결합
        content_list = [comp_file] + reg_files + [prompt]
        response = model.generate_content(content_list)
        return response.text
    except Exception as e:
        st.error(f"❌ 통합 분석 오류: {str(e)}")
        return None

# ================================
# 실행 버튼 및 결과 표시
# ================================
if st.button("🚀 통합 분석 시작", type="primary", use_container_width=True):
    if not target_address or not target_zones:
        st.warning("⚠️ 대상지 주소와 지역지구를 먼저 입력/선택해주세요.")
    elif not competition_file or not regulation_files:
        st.warning("⚠️ 분석할 PDF 파일들을 업로드해주세요.")
    else:
        with st.status("🔍 AI 전문가가 데이터를 분석하고 있습니다...", expanded=True) as status:
            st.write("1. 공모지침서 업로드 중...")
            comp_gemini = upload_pdf_to_gemini(competition_file, "지침서")
            
            st.write("2. 법규 문서 업로드 중...")
            reg_geminis = []
            for f in regulation_files:
                reg_geminis.append(upload_pdf_to_gemini(f))
            
            st.write("3. 법규 위계 및 교차 분석 진행 중...")
            # 여기서는 편의상 통합 분석 함수 하나로 예시를 작성했습니다.
            # 실제 구현시에는 상기 작성하신 개별 함수들을 순차적으로 호출하며 address와 zones 변수를 인자로 넘겨주시면 됩니다.
            final_result = analyze_combined_data(comp_gemini, reg_geminis, target_address, target_zones, selected_model)
            
            status.update(label="✅ 분석 완료!", state="complete", expanded=False)

        if final_result:
            st.success("### 📊 분석 결과")
            st.markdown(final_result)
            
            # 이후 시각화 및 보고서 생성 로직은 기존 코드와 동일하게 처리
            # (guideline_data 등 파싱 로직 포함)