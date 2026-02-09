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
# 페이지 설정 및 스타일
# ================================
st.set_page_config(page_title="건축 공모 & 법규 분석 시스템 v4.2", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    .main-title { text-align: center; background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 1.5rem; border-radius: 15px; font-size: 2rem; font-weight: bold; margin-bottom: 2rem; }
    .section-header { background: #f8fafc; padding: 0.8rem; border-left: 5px solid #3b82f6; border-radius: 5px; margin: 1.5rem 0 1rem 0; font-weight: bold; }
    .highlight-box { background-color: #fff3cd; border: 1px solid #ffeeba; padding: 1.2rem; border-radius: 8px; color: #856404; line-height: 1.7; }
</style>
""", unsafe_allow_html=True)

# ================================
# 사이드바 설정
# ================================
with st.sidebar:
    st.header("⚙️ 분석 설정")
    selected_model = "models/gemini-2.5-flash"
    
    key_options = {
        "메인 키 (계정1)": os.getenv("GOOGLE_API_KEY_1"),
        "예비 키 1 (계정2)": os.getenv("GOOGLE_API_KEY_2"),
        "예비 키 2 (계정3)": os.getenv("GOOGLE_API_KEY_3")
    }
    valid_keys = {name: key for name, key in key_options.items() if key}
    
    if valid_keys:
        selected_name = st.selectbox("🔑 사용할 API 키 선택", list(valid_keys.keys()))
        genai.configure(api_key=valid_keys[selected_name])
        st.success(f"{selected_name} 연결 완료")
    else:
        st.error("⚠️ API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")

    st.divider()
    st.caption(f"Model: {selected_model}\nVersion: 4.2 Pro")

# ================================
# 유틸리티 함수
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

def create_docx(address, zones, analysis_text):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = '맑은 고딕'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')

    title = doc.add_heading('법 규 검 토 서', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"일시: {datetime.now().strftime('%Y-%m-%d')}")
    doc.add_paragraph(f"대상지: {address}")
    doc.add_paragraph(f"용도지역: {', '.join(zones)}")
    
    doc.add_heading('1. 분석 결과 요약', level=1)
    clean_text = re.sub(r'[#*`-]', '', analysis_text)
    doc.add_paragraph(clean_text)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ================================
# 메인 로직
# ================================
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 v4.2</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    target_address = st.text_input("📌 대상지 주소", placeholder="예: 경기도 여주시 가업동 9-1")
with col2:
    target_zones = st.multiselect("🏢 용도지역/지구 선택", ["자연녹지지역", "제1종일반주거", "제2종일반주거", "일반상업지역", "군사시설보호구역", "역사문화환경보존지역"])

up1, up2 = st.columns(2)
with up1:
    comp_file = st.file_uploader("📄 메인 공모지침서 (PDF)", type=['pdf'])
with up2:
    reg_files = st.file_uploader("⚖️ 관련 법규/조례 (PDF)", type=['pdf'], accept_multiple_files=True)

if st.button("🚀 AI 통합 분석 및 보고서 생성", type="primary", use_container_width=True):
    if not (comp_file and target_address):
        st.error("필수 정보를 입력해주세요.")
    else:
        with st.spinner("AI가 법규 위계와 면적을 교차 분석 중입니다..."):
            try:
                # 파일 업로드
                comp_gemini = upload_to_gemini(comp_file)
                reg_geminis = [upload_to_gemini(f) for f in reg_files]
                
                model = genai.GenerativeModel(selected_model)
                
                # 프롬프트 내 중괄호를 {{ }}로 처리하여 오류 방지
                prompt = f"""
                건축 전문가로서 다음을 분석하라:
                1. [면적데이터]: 전용면적과 공용면적의 수치를 포함한 JSON 형식으로 추출하라.
                   형식 예시: {{"net_area": 수치, "gross_area": 수치, "rooms": [{{"name": "실명", "area": 수치}}]}}
                2. [법규위계]: 상위법(국계법, 주차장법)과 하위법(여주시 조례)을 비교 분석하라.
                3. [가이드]: 설계 시 반드시 준수해야 할 핵심 지침들을 발췌하라.
                
                주소: {target_address}
                지역지구: {', '.join(target_zones)}
                """
                
                response = model.generate_content([comp_gemini] + reg_geminis + [prompt])
                full_text = response.text

                # 1. 시각화 섹션
                st.markdown('<div class="section-header">📊 실별 면적 및 전용/공용 비율 분석</div>', unsafe_allow_html=True)
                json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        v_col1, v_col2 = st.columns(2)
                        with v_col1:
                            ratio_df = pd.DataFrame({"구분": ["전용면적", "공용면적"], "면적": [data.get('net_area', 0), data.get('gross_area', 0)]})
                            fig1 = px.pie(ratio_df, values='면적', names='구분', hole=0.5, title="전용 vs 공용 비율 (도넛)", color_discrete_sequence=['#1e3a8a', '#3b82f6'])
                            st.plotly_chart(fig1)
                        with v_col2:
                            room_df = pd.DataFrame(data.get('rooms', []))
                            if not room_df.empty:
                                fig2 = px.bar(room_df, x='name', y='area', title="실별 상세 면적 (㎡)", color='area', color_continuous_scale='Blues')
                                st.plotly_chart(fig2)
                    except:
                        st.warning("데이터 시각화 중 형식 오류가 발생했습니다. 텍스트 분석을 확인하세요.")

                # 2. 아코디언 가이드
                st.markdown('<div class="section-header">💡 최종 설계 적용 가이드 (상세 발췌)</div>', unsafe_allow_html=True)
                sections = full_text.split("###")
                for sec in sections:
                    if "법규" in sec or "가이드" in sec or "적용" in sec:
                        with st.expander(f"🔍 {sec.splitlines()[0]} 관련 상세 내용 보기"):
                            st.write(sec)

                # 3. 종합 요약 표
                st.markdown('<div class="section-header">📋 핵심 법규 및 지침 요약표</div>', unsafe_allow_html=True)
                # AI 응답에서 핵심 키워드 추출 시뮬레이션
                summary_data = {
                    "구분": ["대상지", "용도지역", "주차기준", "특이사항"],
                    "주요 내용": [target_address, ", ".join(target_zones), "조례 및 주차장법 준수", "역사문화환경 및 군사협의 확인"]
                }
                st.table(pd.DataFrame(summary_data))

                # 4. 다운로드 버튼
                docx_file = create_docx(target_address, target_zones, full_text)
                st.download_button(
                    label="📥 법규검토서(HWP호환) 다운로드",
                    data=docx_file,
                    file_name=f"법규검토서_{datetime.now().strftime('%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")

st.divider()
st.caption("Powered by Google Gemini 2.5 Flash | v4.2 Professional Edition")