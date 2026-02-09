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
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.3", page_icon="🏛️", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# [ZONES_DATA 및 유틸리티 함수]
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

# ================================
# 메인 로직 및 사이드바 (키 10개 확장)
# ================================
with st.sidebar:
    st.header("🔑 Multi-API Manager")
    st.info("새로운 구글 계정으로 키를 여러 개 발급받아 아래에 등록하세요.")
    
    selected_model = "gemini-2.0-flash"
    
    # 10개의 API 키 입력창 (한 번 입력하면 세션에 유지되도록 설정 권장)
    api_keys = []
    for i in range(1, 11):
        key = st.text_input(f"API Key #{i}", value=os.getenv(f"GOOGLE_API_KEY_{i}", ""), type="password", key=f"key_input_{i}")
        if key.strip():
            api_keys.append(key.strip())
    
    st.write(f"✅ 총 {len(api_keys)}개의 키가 로드되었습니다.")
    
    if 'current_key_idx' not in st.session_state:
        st.session_state.current_key_idx = 0

# UI 구성
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 v4.3</div>', unsafe_allow_html=True)

target_address = st.text_input("📌 대상지 주소")
selected_all_zones = []
cols = st.columns(len(ZONES_DATA))
for i, (cat, opts) in enumerate(ZONES_DATA.items()):
    with cols[i]:
        st.markdown(f'<span class="category-label">{cat}</span>', unsafe_allow_html=True)
        selected_all_zones.extend(st.multiselect(cat, opts, key=f"sel_{i}"))

up1, up2 = st.columns(2)
with up1: comp_file = st.file_uploader("📂 공모 지침서 (PDF)", type=['pdf'])
with up2: reg_files = st.file_uploader("⚖️ 조례/법규 (PDF)", type=['pdf'], accept_multiple_files=True)

# 분석 실행 버튼
if st.button("🚀 AI 통합 법규 분석 시작", type="primary", use_container_width=True):
    if not api_keys:
        st.error("사이드바에 최소 하나 이상의 API 키를 입력해주세요.")
    elif not (comp_file and target_address and selected_all_zones):
        st.error("주소, 지역지구, 지침서 파일은 필수입니다.")
    else:
        with st.spinner("전문 AI가 분석 중입니다..."):
            success = False
            # 등록된 모든 키를 순회하며 시도
            for _ in range(len(api_keys)):
                active_key = api_keys[st.session_state.current_key_idx]
                genai.configure(api_key=active_key)
                
                try:
                    # 파일 업로드 및 분석 수행
                    comp_gemini = upload_to_gemini(comp_file)
                    reg_geminis = [upload_to_gemini(f) for f in reg_files]
                    
                    model = genai.GenerativeModel(selected_model)
                    prompt = f"건축 전문가로서 {target_address} 분석. 면적데이터 JSON, 법규 분석, 설계 주의사항 포함."
                    
                    response = model.generate_content([comp_gemini] + reg_geminis + [prompt])
                    
                    # 성공 시 결과 출력
                    st.success(f"✅ 분석 성공 (사용한 키: #{st.session_state.current_key_idx + 1})")
                    st.markdown(response.text)
                    success = True
                    break
                    
                except Exception as e:
                    if "429" in str(e):
                        st.warning(f"⚠️ Key #{st.session_state.current_key_idx + 1} 한도 초과. 다음 키로 자동 전환합니다.")
                        # 인덱스 변경 및 잠시 대기
                        st.session_state.current_key_idx = (st.session_state.current_key_idx + 1) % len(api_keys)
                        time.sleep(5) # API 교체 간격
                    else:
                        st.error(f"❌ 오류 발생: {e}")
                        break
            
            if not success:
                st.error("🚫 모든 API 키의 일일 할당량이 소진되었거나 서버 오류입니다. 잠시 후 다시 시도하세요.")

# 저작권 표기
st.markdown(f"""
<div class="copyright">
    All intellectual property rights belong to Kim Doyoung.<br>
    Copyright © {datetime.now().year} Architecture AI Lab. All Rights Reserved.
</div>
""", unsafe_allow_html=True)