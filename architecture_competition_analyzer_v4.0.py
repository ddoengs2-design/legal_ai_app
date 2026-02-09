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

# 데이터 처리 및 시각화
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 문서 생성
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# .env 파일 로드
load_dotenv()

# ================================
# 페이지 설정 및 CSS
# ================================
st.set_page_config(
    page_title="건축 공모 & 법규 분석 시스템 v4.2",
    page_icon="🏛️",
    layout="wide"
)

st.markdown("""
<style>
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .section-header {
        background: #f8fafc;
        padding: 0.8rem;
        border-left: 5px solid #3b82f6;
        border-radius: 5px;
        margin: 1.5rem 0 1rem 0;
        font-weight: bold;
    }
    .legal-card {
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .highlight-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        padding: 1rem;
        border-radius: 8px;
        color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# 사이드바 설정
# ================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    
    # [핵심] .env 파일 왼쪽에 적힌 '변수명'만 정확히 입력합니다.
    key_options = {
        "메인 키 (계정1)": os.getenv("GOOGLE_API_KEY_1"),
        "예비 키 1 (계정2)": os.getenv("GOOGLE_API_KEY_2"),
        "예비 키 2 (계정3)": os.getenv("GOOGLE_API_KEY_3")
    }
    
    # 실제로 값이 존재하여 불러오기에 성공한 키들만 리스트에 담습니다.
    valid_keys = {name: key for name, key in key_options.items() if key}
    
    if valid_keys:
        # 이제 "직접 입력" 대신 이 선택 박스가 화면에 나타납니다.
        selected_name = st.selectbox("🔑 사용할 API 키 선택", list(valid_keys.keys()))
        api_key = valid_keys[selected_name]
        
        if api_key:
            genai.configure(api_key=api_key)
            st.success(f"{selected_name} 연결 완료")
    else:
        # 여전히 직접 입력이 뜬다면 .env 파일의 위치나 파일명을 다시 확인해야 합니다.
        st.warning("⚠️ .env 파일에서 키를 찾을 수 없습니다.")
        api_key = st.text_input("Gemini API Key 직접 입력", type="password")
        if api_key:
            genai.configure(api_key=api_key)
# ================================
# 메인 UI: 입력 섹션
# ================================
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 v4.2</div>', unsafe_allow_html=True)

# 1. 대상지 기본 정보
st.markdown('<div class="section-header">📍 1. 대상지 기본 정보 입력</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    target_address = st.text_input("📌 대상지 주소", placeholder="예: 경기도 여주시 가업동 9-1")
with col2:
    zone_options = ["제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역", "일반상업지역", "근린상업지역", "자연녹지지역", "지구단위계획구역"]
    target_zones = st.multiselect("🏢 용도지역/지구 선택", options=zone_options)

# 2. 파일 업로드
st.markdown('<div class="section-header">📄 2. 분석 파일 업로드</div>', unsafe_allow_html=True)
up_col1, up_col2 = st.columns(2)
with up_col1:
    competition_file = st.file_uploader("메인 공모지침서 (단일 PDF)", type=['pdf'])
with up_col2:
    regulation_files = st.file_uploader("관련 법규 및 조례 (다중 PDF)", type=['pdf'], accept_multiple_files=True)

# ================================
# 핵심 함수 로직
# ================================

def upload_to_gemini(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.getvalue())
        tmp_path = tmp.name
    gemini_file = genai.upload_file(tmp_path)
    while gemini_file.state.name == "PROCESSING":
        time.sleep(1)
        gemini_file = genai.get_file(gemini_file.name)
    return gemini_file

def perform_analysis(comp_pdf, reg_pdfs, address, zones):
    model = genai.GenerativeModel(selected_model)
    
    prompt = f"""
    당신은 건축 공모 및 법규 분석 전문가입니다. 아래 정보를 바탕으로 통합 분석 보고서를 작성하세요.
    
    [입력 정보]
    - 주소: {address}
    - 지역지구: {', '.join(zones)}
    
    [분석 요청 사항]
    1. 지침서 분석: 사업개요, 설계조건, 실별 면적표를 JSON 구조로 추출할 것.
    2. 법규 위계 분석: 
       - [상위법] 국계법(건폐율/용적률 범위) 및 건축법 분석
       - [하위법] 해당 주소지의 '도시계획 조례' 및 '건축 조례'를 분석하여 실질 적용 수치 도출
    3. 결론: 상위법보다 우선하는 '하위법(조례)'의 핵심 제한사항을 하이라이트하여 정리할 것.
    
    [응답 형식]
    반드시 다음의 구조를 포함한 마크다운 형식으로 답변하세요.
    ---
    ### [공모지침_데이터]
    (여기에 실별면적표가 포함된 JSON 데이터를 위치시킬 것)
    ---
    ### [법규_위계_분석]
    #### 1. 상위법 (국계법/건축법)
    #### 2. 하위법 (자치법규/조례)
    #### 3. 실질 적용 결론 (Highlight)
    """
    
    inputs = [comp_pdf] + reg_pdfs + [prompt]
    response = model.generate_content(inputs)
    return response.text

# ================================
# 결과 시각화 및 출력
# ================================

if st.button("🚀 AI 통합 분석 시작", type="primary", use_container_width=True):
    if not (competition_file and regulation_files and target_address):
        st.error("모든 필드와 파일을 입력해주세요.")
    else:
        with st.spinner("전문 AI가 법규 위계를 교차 분석 중입니다..."):
            # 파일 업로드
            comp_gemini = upload_to_gemini(competition_file)
            reg_geminis = [upload_to_gemini(f) for f in regulation_files]
            
            # 분석 실행
            full_text = perform_analysis(comp_gemini, reg_geminis, target_address, target_zones)
            
            # 1. JSON 데이터 파싱 및 그래프 시각화
            try:
                json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    st.markdown('<div class="section-header">📊 실별 면적 분석 그래프</div>', unsafe_allow_html=True)
                    
                    # 면적 데이터 추출 (예시 구조 대응)
                    area_data = data.get("실별면적표", data.get("공간계획", []))
                    if area_data:
                        df = pd.DataFrame(area_data)
                        # 컬럼명 유연화 및 숫자 변환
                        df.columns = ['실명', '면적'] if len(df.columns) >= 2 else df.columns
                        df['면적_val'] = df['면적'].replace(r'[^0-9.]', '', regex=True).astype(float)
                        
                        viz_col1, viz_col2 = st.columns(2)
                        with viz_col1:
                            fig_pie = px.pie(df, values='면적_val', names='실명', title='실별 면적 비중', hole=0.4)
                            st.plotly_chart(fig_pie)
                        with viz_col2:
                            fig_bar = px.bar(df, x='실명', y='면적_val', color='실명', title='실별 상세 면적(㎡)')
                            st.plotly_chart(fig_bar)
            except:
                st.info("데이터 구조화 진행 중... 그래프 생성 대기")

            # 2. 법규 위계 분석 출력
            st.markdown('<div class="section-header">⚖️ 법규 위계 및 교차 분석 결과</div>', unsafe_allow_html=True)
            
            # 섹션별 분리 및 스타일 적용
            sections = full_text.split("####")
            for section in sections:
                if "1. 상위법" in section:
                    st.info(f"**🏛️ 국계법 및 상위 법령 분석**\n\n{section.replace('1. 상위법', '')}")
                elif "2. 하위법" in section:
                    st.success(f"**📜 지자체 조례 및 하위 법령 분석 (실무 적용)**\n\n{section.replace('2. 하위법', '')}")
                elif "3. 실질 적용" in section:
                    st.markdown("### 📌 최종 설계 적용 가이드")
                    st.markdown(f'<div class="highlight-box">{section.replace("3. 실질 적용", "")}</div>', unsafe_allow_html=True)

st.divider()
st.caption("Powered by Google Gemini 2.0 Flash | v4.2 Professional Edition | © 2026 Kim Doyoung")