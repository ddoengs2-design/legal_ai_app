import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
import pandas as pd
import plotly.express as px
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from io import BytesIO

# 문서 생성 도구
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

# .env 파일 로드
load_dotenv(override=True)

# ================================
# 페이지 설정 및 스타일 (Orange Theme)
# ================================
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.2", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    .main-title { 
        text-align: center; 
        background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); 
        color: white; padding: 1.5rem; border-radius: 15px; 
        font-size: 2rem; font-weight: bold; margin-bottom: 2rem; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .section-header { 
        background: #fff7ed; padding: 0.8rem; border-left: 5px solid #f97316; 
        border-radius: 5px; margin: 1.5rem 0 1rem 0; font-weight: bold; color: #9a3412;
    }
    .category-label { 
        font-size: 0.85rem; font-weight: bold; color: #c2410c; margin-bottom: 5px; display: block; 
    }
    .copyright {
        text-align: center; color: #94a3b8; font-size: 0.85rem; 
        margin-top: 50px; padding: 25px; border-top: 1px solid #e2e8f0; line-height: 1.6;
    }
    .api-status-success { color: #10b981; font-weight: bold; font-size: 0.8rem; }
    .api-status-fail { color: #ef4444; font-weight: bold; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ================================
# 지역지구 데이터 및 유틸리티
# ================================
ZONES_DATA = {
    "🏢 용도지역 (도시)": ["제1종전용주거지역", "제2종전용주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역", "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "전용공업지역", "일반공업지역", "준공업지역", "보전녹지지역", "생산녹지지역", "자연녹지지역"],
    "🌲 용도지역 (비도시)": ["보전관리지역", "생산관리지역", "계획관리지역", "농림지역", "자연환경보전지역"],
    "⚠️ 용도지구": ["경관지구", "고도지구", "방화지구", "방재지구", "보호지구", "취락지구", "개발진흥지구", "특정용도제한지구", "복합용도지구"],
    "🛑 용도구역": ["개발제한구역", "도시자연공원구역", "시가화조정구역", "수산자원보호구역", "입지규제최소구역"],
    "🎖️ 군사/기타": ["군사기지 및 군사시설 보호구역", "제한보호구역", "통제보호구역", "비행안전구역", "역사문화환경보존지역", "가축사육제한구역", "지구단위계획구역", "상수원보호구역"]
}

def upload_to_gemini(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.getvalue())
        tmp_path = tmp.name
    gemini_file = genai.upload_file(tmp_path)
    while gemini_file.state.name == "PROCESSING":
        time.sleep(1)
        gemini_file = genai.get_file(gemini_file.name)
    return gemini_file

def create_docx(address, zones, analysis_text):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = '맑은 고딕'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')
    title = doc.add_heading('법 규 검 토 서', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"분석일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph(f"대상지 주소: {address}")
    doc.add_paragraph(f"지역지구 지정현황: {', '.join(zones)}")
    doc.add_heading('1. 통합 법규 분석 결과', level=1)
    doc.add_paragraph(re.sub(r'[#*`-]', '', analysis_text))
    doc.add_paragraph("\nAll intellectual property rights belong to Kim Doyoung.")
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ================================
# 메인 로직 및 사이드바 (다중 API 설정)
# ================================
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 v4.2</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 분석 설정 및 API 관리")
    selected_model = "gemini-2.0-flash"
    
    # 예비 키를 포함한 3개의 키 입력 필드
    key1 = st.text_input("🔑 메인 API 키", value=os.getenv("GOOGLE_API_KEY_1", ""), type="password")
    key2 = st.text_input("🔑 예비 API 키 1", value=os.getenv("GOOGLE_API_KEY_2", ""), type="password")
    key3 = st.text_input("🔑 예비 API 키 2", value=os.getenv("GOOGLE_API_KEY_3", ""), type="password")
    key4 = st.text_input("🔑 예비 API 키 3", value=os.getenv("GOOGLE_API_KEY_4", ""), type="password")    
    # 사용 가능한 키 리스트 생성
    available_keys = [k for k in [key1, key2, key3] if k.strip()]
    
    if available_keys:
        # 현재 활성화된 키 인덱스 (세션 상태 저장)
        if 'key_index' not in st.session_state:
            st.session_state.key_index = 0
            
        current_key = available_keys[st.session_state.key_index]
        genai.configure(api_key=current_key)
        st.markdown(f'<p class="api-status-success">✅ 현재 연결: API 키 #{st.session_state.key_index + 1} 사용 중</p>', unsafe_allow_html=True)
        
        if st.button("🔄 다음 예비 키로 강제 전환"):
            st.session_state.key_index = (st.session_state.key_index + 1) % len(available_keys)
            st.rerun()
    else:
        st.markdown('<p class="api-status-fail">⚠️ 등록된 API 키가 없습니다.</p>', unsafe_allow_html=True)

# 1. 정보 입력
st.markdown('<div class="section-header">📍 1. 대상지 정보 및 지역지구 상세 선택</div>', unsafe_allow_html=True)
target_address = st.text_input("📌 대상지 주소 (예: 부산광역시 남구 용호동 943)")

selected_all_zones = []
zone_cols = st.columns(len(ZONES_DATA))
for i, (category, options) in enumerate(ZONES_DATA.items()):
    with zone_cols[i]:
        st.markdown(f'<span class="category-label">{category}</span>', unsafe_allow_html=True)
        selected = st.multiselect(category, options, label_visibility="collapsed")
        selected_all_zones.extend(selected)

# 2. 파일 업로드
st.markdown('<div class="section-header">📄 2. 분석 자료 업로드</div>', unsafe_allow_html=True)
up1, up2 = st.columns(2)
with up1:
    comp_file = st.file_uploader("📂 공모 지침서 (PDF)", type=['pdf'])
with up2:
    reg_files = st.file_uploader("⚖️ 관련 법규/조례 (PDF)", type=['pdf'], accept_multiple_files=True)

# 3. 분석 실행 (자동 예비 키 전환 로직 포함)
if st.button("🚀 AI 통합 법규 분석 시작", type="primary", use_container_width=True):
    if not available_keys:
        st.error("사이드바에서 API 키를 최소 하나 이상 입력해주세요.")
    elif not (comp_file and target_address and selected_all_zones):
        st.error("⚠️ 필수 정보(주소, 지역지구, 지침서)가 누락되었습니다.")
    else:
        with st.spinner("AI가 분석 중입니다... (API 오류 발생 시 예비 키로 자동 전환됩니다)"):
            success = False
            attempts = 0
            max_attempts = len(available_keys)
            
            while attempts < max_attempts and not success:
                try:
                    # 현재 설정된 키로 시도
                    current_key = available_keys[st.session_state.key_index]
                    genai.configure(api_key=current_key)
                    
                    comp_gemini = upload_to_gemini(comp_file)
                    reg_geminis = [upload_to_gemini(f) for f in reg_files]
                    
                    model = genai.GenerativeModel(selected_model)
                    prompt = f"건축 전문가로서 다음을 분석하라: {target_address}, 지역지구: {selected_all_zones}. 면적데이터(JSON), 법규위계, 설계가이드를 포함하라."
                    
                    response = model.generate_content([comp_gemini] + reg_geminis + [prompt])
                    full_text = response.text
                    
                    # 분석 결과 시각화
                    st.markdown('<div class="section-header">📊 데이터 분석 결과</div>', unsafe_allow_html=True)
                    json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        rdf = pd.DataFrame({"구분": ["전용", "공용"], "면적": [data.get('net_area', 0), data.get('gross_area', 0)]})
                        st.plotly_chart(px.pie(rdf, values='면적', names='구분', hole=0.5, color_discrete_sequence=['#ea580c', '#fbbf24']))

                    st.markdown('<div class="section-header">💡 설계 상세 가이드</div>', unsafe_allow_html=True)
                    st.write(full_text)

                    docx_file = create_docx(target_address, selected_all_zones, full_text)
                    st.download_button("📥 보고서 다운로드", docx_file, f"건축분석_{datetime.now().strftime('%m%d')}.docx", use_container_width=True)
                    
                    success = True
                
                except Exception as e:
                    attempts += 1
                    st.warning(f"⚠️ API 키 #{st.session_state.key_index + 1} 오류 발생. 예비 키로 전환을 시도합니다...")
                    st.session_state.key_index = (st.session_state.key_index + 1) % len(available_keys)
                    if attempts == max_attempts:
                        st.error(f"❌ 모든 API 키가 실패했습니다: {e}")

# 저작권 표기
st.markdown(f"""
<div class="copyright">
    All intellectual property rights belong to Kim Doyoung.<br>
    Copyright © {datetime.now().year} Architecture AI Lab. All Rights Reserved.
</div>
""", unsafe_allow_html=True)