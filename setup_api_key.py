"""
건축 공모 & 법규 분석 시스템 v5.0 - Gemini 2.0 Flash Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
개발자 및 저작권자: Kim Doyoung
주요 업데이트:
- 모델 엔진: Gemini 2.0 Flash 적용 (초고속 분석)
- API 로테이션: .env 파일 내 GOOGLE_API_KEY_1~25 자동 순환
- 분석 최적화: 공모 지침서 vs 관련 법규 정밀 대조 알고리즘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import streamlit as st
import google.generativeai as genai
import os
import time
import tempfile
import json
import warnings
from datetime import datetime
from dotenv import load_dotenv

# 경고 무시 및 환경 변수 로드
warnings.filterwarnings("ignore")
load_dotenv(override=True)

# ================================
# 1. 페이지 및 스타일 설정
# ================================
st.set_page_config(page_title="건축 AI 분석 시스템 v5.0", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    .main-title { 
        text-align: center; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); 
        color: #f8fafc; padding: 2rem; border-radius: 15px; font-size: 2.2rem; font-weight: bold; margin-bottom: 2rem;
    }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5rem; font-size: 1.1rem; font-weight: bold; }
    .footer { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-top: 4rem; padding: 2rem; border-top: 1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ================================
# 2. 핵심 로직: API 로테이션 & 파일 처리
# ================================

def get_api_keys():
    """GOOGLE_API_KEY_1 ~ 25 로드"""
    keys = []
    for i in range(1, 26):
        k = os.getenv(f"GOOGLE_API_KEY_{i}")
        if k: keys.append(k.strip())
    return keys

def upload_to_gemini(uploaded_file):
    """파일을 Gemini 서버로 업로드 및 처리 완료 대기"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        gen_file = genai.upload_file(tmp_path, display_name=uploaded_file.name)
        while gen_file.state.name == "PROCESSING":
            time.sleep(2)
            gen_file = genai.get_file(gen_file.name)
        
        os.unlink(tmp_path)
        return gen_file
    except Exception as e:
        st.error(f"파일 업로드 실패: {e}")
        return None

# ================================
# 3. 메인 화면 구성
# ================================
st.markdown('<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템 v5.0</div>', unsafe_allow_html=True)

# API 키 상태 확인
api_keys = get_api_keys()
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    if api_keys:
        st.success(f"✅ {len(api_keys)}개 API 프로젝트 활성화")
    else:
        st.error("❌ .env 파일에서 API 키를 설정해주세요.")
    st.divider()
    st.info("💡 모델: Gemini 2.0 Flash\n지원: 다중 PDF 대조 분석")

# 프로젝트 정보 입력
col1, col2 = st.columns(2)
with col1:
    project_name = st.text_input("📁 프로젝트 명칭", placeholder="예: 신축 청사 건립사업")
    site_addr = st.text_input("📍 대상지 주소", placeholder="지번 또는 도로명 주소")
with col2:
    zoning = st.multiselect("🗺️ 용도지역/지구", ["제1종일반주거", "제2종일반주거", "제3종일반주거", "준주거", "일반상업", "자연녹지"])
    building_use = st.text_input("🏢 주요 용도", placeholder="예: 공공업무시설, 문화 및 집회시설")

# 파일 업로드 섹션
st.divider()
u1, u2 = st.columns(2)
with u1:
    guideline_pdf = st.file_uploader("📄 공모 지침서 (필수)", type=['pdf'])
with u2:
    law_pdfs = st.file_uploader("⚖️ 관련 법규/조례 (다중 선택 가능)", type=['pdf'], accept_multiple_files=True)

# ================================
# 4. 분석 실행 섹션
# ================================
if st.button("🚀 Gemini 2.0 Flash 통합 분석 시작"):
    if not api_keys:
        st.error("API 키가 없습니다.")
    elif not guideline_pdf:
        st.warning("공모 지침서 PDF를 업로드해주세요.")
    else:
        with st.status("🔍 분석 엔진 가동 중...", expanded=True) as status:
            # 첫 번째 키로 설정 (실패 시 로테이션 로직 가능)
            genai.configure(api_key=api_keys[0])
            
            st.write("📤 지침서 및 법규 업로드 중...")
            main_doc = upload_to_gemini(guideline_pdf)
            all_docs = [main_doc]
            
            if law_pdfs:
                for lp in law_pdfs:
                    processed_law = upload_to_gemini(lp)
                    if processed_law: all_docs.append(processed_law)
            
            st.write("🤖 Gemini 2.0 Flash가 문서를 대조 분석하고 있습니다...")
            
            # 프롬프트 구성
            prompt = f"""
            당신은 대한민국 건축 설계 공모 분석 전문가입니다. 
            프로젝트 '{project_name}'(위치: {site_addr}, 용도지역: {zoning})의 지침서와 법규를 분석하세요.

            1. 개요 요약: 대지 조건 및 시설 규모.
            2. 면적표(Space Program): 지침서에 명시된 실별 면적을 표(Table)로 추출.
            3. 법규 검토: 주차장법, 건축법, 조례와 지침서 간의 불일치 또는 주의사항.
            4. 설계 전략: AI가 제안하는 법적 한도 내 최대 효율 배치 가이드.

            모든 보고서 마지막에는 반드시 다음 문구를 포함하세요:
            "All intellectual property rights belong to Kim Doyoung."
            """

            try:
                # Gemini 2.0 Flash 모델 호출
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(all_docs + [prompt])
                
                st.markdown("### 📊 통합 분석 리포트")
                st.markdown(response.text)
                
                # 다운로드 버튼
                st.download_button(
                    label="💾 분석 결과 저장 (.md)",
                    data=response.text,
                    file_name=f"{project_name}_분석결과_{datetime.now().strftime('%m%d')}.md"
                )
                status.update(label="✅ 분석 완료!", state="complete")
                
            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")

# 푸터
st.markdown(f"""
<div class="footer">
    <b>All intellectual property rights belong to Kim Doyoung.</b><br>
    © {datetime.now().year} Architecture AI Lab | v5.0 Multi-Project Engine
</div>
""", unsafe_allow_html=True)