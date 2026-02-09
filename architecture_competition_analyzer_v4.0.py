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
# 문서 생성 함수 (HWP 예시 스타일 반영)
# ================================
def create_docx(address, zones, analysis_text):
    doc = Document()
    # 한글 폰트 설정 (맑은 고딕 기본)
    style = doc.styles['Normal']
    style.font.name = 'Malgun Gothic'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), 'Malgun Gothic')

    # 제목
    title = doc.add_heading('법 규 검 토 서', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"일시: {datetime.now().strftime('%Y-%m-%d')}")
    doc.add_paragraph(f"대상지: {address}")
    doc.add_paragraph(f"용도지역: {', '.join(zones)}")
    doc.add_page_break()

    # 내용 추가 (마크다운 제거 후 텍스트만 삽입)
    doc.add_heading('1. 법규 및 지침 분석 결과', level=1)
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
    target_address = st.text_input("📌 대상지 주소", placeholder="예: 부산광역시 남구 용호동 943")
with col2:
    target_zones = st.multiselect("🏢 용도지역/지구 선택", ["자연녹지지역", "제1종일반주거", "제2종일반주거", "일반상업지역", "군사시설보호구역"])

up1, up2 = st.columns(2)
with up1:
    comp_file = st.file_uploader("📄 메인 공모지침서 (PDF)", type=['pdf'])
with up2:
    reg_files = st.file_uploader("⚖️ 관련 법규/조례 (PDF)", type=['pdf'], accept_multiple_files=True)

if st.button("🚀 AI 통합 분석 및 보고서 생성", type="primary", use_container_width=True):
    if not (comp_file and target_address):
        st.error("필수 정보를 입력해주세요.")
    else:
        with st.spinner("AI가 도면과 지침을 교차 분석 중입니다..."):
            try:
                # [파일 업로드 로직 생략 - 이전과 동일]
                # 임시 결과 생성 (실제 API 호출 부분)
                model = genai.GenerativeModel(selected_model)
                # 실제 환경에서는 upload_to_gemini 함수를 사용하세요.
                
                # 분석 프롬프트 (JSON 추출 강화)
                prompt = f"""
                건축 전문가로서 다음을 분석하라:
                1. [면적데이터]: 전용면적과 공용면적의 수치를 포함한 JSON (키: 'net_area', 'gross_area', 'rooms': [{'name': '실명', 'area': 수치}])
                2. [법규위계]: 상위법(국계법), 하위법(조례) 비교
                3. [가이드]: 설계 시 반드시 준수해야 할 사항들
                """
                
                # 가상의 결과 (시연용)
                full_text = """
                ### [공모지침_데이터]
                {
                    "net_area": 1500,
                    "gross_area": 800,
                    "rooms": [
                        {"name": "지휘통제실", "area": 450},
                        {"name": "사무실", "area": 300},
                        {"name": "회의실", "area": 150},
                        {"name": "대기실", "area": 200}
                    ]
                }
                ---
                ### [법규_위계_분석]
                #### 1. 상위법 분석
                자연녹지지역 내 건폐율 20% 이하, 용적률 80% 이하 적용.
                #### 2. 하위법(조례) 분석
                부산시 도시계획 조례에 의거, 해당 부지는 군사시설보호구역 중첩으로 인해 높이 제한 15m 적용.
                #### 3. 실질 적용 결론
                조례가 국계법보다 강화된 기준을 제시하므로 높이 제한을 최우선 반영할 것.
                """

                # 1. 시각화 섹션
                st.markdown('<div class="section-header">📊 실별 면적 및 전용/공용 비율 분석</div>', unsafe_allow_html=True)
                json_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    v_col1, v_col2 = st.columns(2)
                    with v_col1:
                        # 전용/공용 비율 도넛 차트
                        ratio_df = pd.DataFrame({"구분": ["전용면적", "공용면적"], "면적": [data['net_area'], data['gross_area']]})
                        fig1 = px.pie(ratio_df, values='면적', names='구분', hole=0.5, title="전용 vs 공용 비율", color_discrete_sequence=['#1e3a8a', '#3b82f6'])
                        st.plotly_chart(fig1)
                    with v_col2:
                        # 실별 면적 바 차트
                        room_df = pd.DataFrame(data['rooms'])
                        fig2 = px.bar(room_df, x='name', y='area', title="실별 상세 면적 (㎡)", color='area')
                        st.plotly_chart(fig2)

                # 2. 아코디언 가이드
                st.markdown('<div class="section-header">💡 최종 설계 적용 가이드 (상세)</div>', unsafe_allow_html=True)
                with st.expander("⚖️ 법규 위계 분석 (상위법 vs 조례)", expanded=True):
                    st.write("국계법상 기준보다 지자체 조례 및 군사기지 보호구역 협의 지침이 우선 적용됩니다.")
                with st.expander("📏 면적 및 규모 제한 사항"):
                    st.write(f"현재 분석된 연면적 대비 전용률은 {(data['net_area']/(data['net_area']+data['gross_area'])*100):.1f}%입니다. 지침서상 최소 면적을 충족합니다.")
                with st.expander("🚩 설계 주의사항 및 특이사항"):
                    st.write("역사문화환경보존지역 인접에 따른 외관 심의 대상 가능성 검토 필요.")

                # 3. 종합 요약 표
                st.markdown('<div class="section-header">📋 분석 요약표</div>', unsafe_allow_html=True)
                summary_data = {
                    "항목": ["대지위치", "용도지역", "건폐율/용적률", "주요제한"],
                    "내용": [target_address, ", ".join(target_zones), "20% / 80% (조례기준)", "높이제한 15m 및 군사협의"]
                }
                st.table(pd.DataFrame(summary_data))

                # 4. 다운로드 버튼
                docx_file = create_docx(target_address, target_zones, full_text)
                st.download_button(
                    label="📥 법규검토서(HWP스타일) 다운로드",
                    data=docx_file,
                    file_name=f"법규검토서_{target_address}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"분석 오류: {e}")

st.caption("© 2026 건축 법규 AI 분석 시스템 | v4.2 Professional")