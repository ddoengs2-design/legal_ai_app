"""
건축 공모 & 법규 분석 시스템 v4.6 - Single Account Multi-Project Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 핵심 전략:
- 한 개 구글 계정으로 여러 프로젝트 생성 (최대 25개)
- 각 프로젝트마다 독립적인 할당량 (1,500 RPD)
- 프로젝트별 API 키 발급 및 자동 로테이션
- 총 할당량: 37,500 RPD (25개 프로젝트 x 1,500)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

필수 라이브러리:
pip install streamlit google-generativeai python-dotenv python-docx plotly pandas
"""

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

# 문서 생성
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# .env 파일 로드
load_dotenv(override=True)

# ================================
# 페이지 설정
# ================================
st.set_page_config(
    page_title="건축 공모 & 법규 분석 시스템 v4.6",
    page_icon="🏛️",
    layout="wide"
)

# ================================
# 커스텀 CSS
# ================================
st.markdown("""
<style>
    .main-title { 
        text-align: center; 
        background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%); 
        color: white; 
        padding: 1.5rem; 
        border-radius: 15px; 
        font-size: 2rem; 
        font-weight: bold; 
        margin-bottom: 2rem; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .version-badge {
        display: inline-block;
        background: #10b981;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        margin-left: 0.5rem;
    }
    
    .project-badge {
        display: inline-block;
        background: #3b82f6;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 10px;
        font-size: 0.75rem;
        margin: 0.2rem;
    }
    
    .section-header { 
        background: #fff7ed; 
        padding: 0.8rem; 
        border-left: 5px solid #f97316; 
        border-radius: 5px; 
        margin: 1.5rem 0 1rem 0; 
        font-weight: bold; 
        color: #9a3412;
    }
    
    .info-box {
        background: #eff6ff;
        border: 2px solid #93c5fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #f0fdf4;
        border: 2px solid #86efac;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: #fffbeb;
        border: 2px solid #fcd34d;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: #fef2f2;
        border: 2px solid #fca5a5;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .quota-info {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 5px solid #0ea5e9;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .copyright {
        text-align: center; 
        color: #94a3b8; 
        font-size: 0.85rem; 
        margin-top: 50px; 
        padding: 25px; 
        border-top: 1px solid #e2e8f0; 
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ================================
# 지역지구 데이터
# ================================
ZONES_DATA = {
    "🏢 용도지역 (도시)": [
        "제1종전용주거지역", "제2종전용주거지역", 
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", 
        "준주거지역",
        "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역",
        "전용공업지역", "일반공업지역", "준공업지역",
        "보전녹지지역", "생산녹지지역", "자연녹지지역"
    ],
    "🌲 용도지역 (비도시)": [
        "보전관리지역", "생산관리지역", "계획관리지역", 
        "농림지역", "자연환경보전지역"
    ],
    "⚠️ 용도지구": [
        "경관지구", "고도지구", "방화지구", "방재지구", 
        "보호지구", "취락지구", "개발진흥지구", 
        "특정용도제한지구", "복합용도지구"
    ],
    "🛑 용도구역": [
        "개발제한구역", "도시자연공원구역", "시가화조정구역", 
        "수산자원보호구역", "입지규제최소구역"
    ],
    "🎖️ 군사/기타": [
        "군사기지 및 군사시설 보호구역", "제한보호구역", 
        "통제보호구역", "비행안전구역", "역사문화환경보존지역", 
        "가축사육제한구역", "지구단위계획구역", "상수원보호구역"
    ]
}

# ================================
# 유틸리티 함수
# ================================

def load_api_keys_from_env():
    """
    .env 파일에서 API 키 로드
    최대 25개 프로젝트 지원
    """
    api_keys = []
    
    # GOOGLE_API_KEY_1 ~ GOOGLE_API_KEY_25
    for i in range(1, 26):
        key = os.getenv(f"GOOGLE_API_KEY_{i}", "")
        if key.strip():
            api_keys.append({
                "key": key.strip(),
                "project": f"Project-{i}",
                "index": i
            })
    
    return api_keys


def upload_to_gemini(file, display_name=None):
    """PDF 파일을 Gemini에 업로드"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        
        name = display_name or file.name
        gemini_file = genai.upload_file(tmp_path, display_name=name)
        
        # 처리 대기 (최대 60초)
        max_wait = 60
        waited = 0
        while gemini_file.state.name == "PROCESSING" and waited < max_wait:
            time.sleep(2)
            gemini_file = genai.get_file(gemini_file.name)
            waited += 2
        
        os.unlink(tmp_path)
        
        if gemini_file.state.name == "FAILED":
            raise Exception(f"파일 처리 실패: {name}")
        
        return gemini_file
        
    except Exception as e:
        st.error(f"❌ 파일 업로드 오류 ({file.name}): {str(e)}")
        return None


def parse_error_message(error):
    """에러 메시지 파싱하여 타입 및 재시도 시간 추출"""
    error_str = str(error)
    
    if "429" in error_str or "quota" in error_str.lower():
        # 재시도 시간 추출
        retry_match = re.search(r'retry.*?(\d+)', error_str)
        retry_seconds = int(retry_match.group(1)) if retry_match else 60
        
        return {
            "type": "quota_exceeded",
            "retry_seconds": retry_seconds,
            "message": "API 할당량 초과"
        }
    elif "503" in error_str:
        return {
            "type": "server_error",
            "retry_seconds": 30,
            "message": "서버 일시적 오류"
        }
    else:
        return {
            "type": "unknown",
            "retry_seconds": 0,
            "message": str(error)
        }


def try_with_multi_project_keys(api_keys_info, call_func, max_retries_per_key=2):
    """
    여러 프로젝트의 API 키로 순차 시도
    
    Args:
        api_keys_info: API 키 정보 리스트 [{"key": ..., "project": ..., "index": ...}]
        call_func: 실행할 함수
        max_retries_per_key: 각 키당 최대 재시도 횟수
        
    Returns:
        (성공 여부, 결과 또는 에러, 사용된 프로젝트 정보)
    """
    
    if not api_keys_info:
        return False, "API 키가 없습니다.", None
    
    total_keys = len(api_keys_info)
    
    # 세션 상태 초기화
    if 'current_project_idx' not in st.session_state:
        st.session_state.current_project_idx = 0
    if 'project_fail_count' not in st.session_state:
        st.session_state.project_fail_count = {}
    
    # 모든 프로젝트 순회
    attempts = 0
    max_attempts = total_keys * max_retries_per_key
    
    while attempts < max_attempts:
        current_idx = st.session_state.current_project_idx
        key_info = api_keys_info[current_idx]
        
        project_name = key_info["project"]
        api_key = key_info["key"]
        
        # 프로젝트 실패 횟수 확인
        if project_name not in st.session_state.project_fail_count:
            st.session_state.project_fail_count[project_name] = 0
        
        # 실패 횟수 초과 시 건너뛰기
        if st.session_state.project_fail_count[project_name] >= max_retries_per_key:
            st.warning(f"⏭️ {project_name} 건너뛰기 (실패 {max_retries_per_key}회 초과)")
            st.session_state.current_project_idx = (current_idx + 1) % total_keys
            attempts += 1
            continue
        
        try:
            # API 설정
            genai.configure(api_key=api_key)
            
            st.info(f"🔄 **{project_name}** 사용 중... (키 #{key_info['index']})")
            
            # 함수 실행
            result = call_func()
            
            # 성공!
            st.success(f"✅ **분석 성공!** ({project_name} - 키 #{key_info['index']})")
            
            # 성공 시 실패 카운트 초기화
            st.session_state.project_fail_count[project_name] = 0
            
            return True, result, key_info
            
        except Exception as e:
            error_info = parse_error_message(e)
            
            # 실패 카운트 증가
            st.session_state.project_fail_count[project_name] += 1
            
            if error_info["type"] == "quota_exceeded":
                retry_sec = error_info["retry_seconds"]
                
                st.warning(f"""
                ⚠️ **{project_name} 할당량 초과**
                - 프로젝트: {project_name}
                - 키 번호: #{key_info['index']}
                - 권장 대기: {retry_sec}초
                - 다음 프로젝트로 전환...
                """)
                
                # 다음 프로젝트로
                st.session_state.current_project_idx = (current_idx + 1) % total_keys
                
                # 짧은 대기 (다른 프로젝트는 할당량이 다름)
                time.sleep(min(5, retry_sec / 10))
                
            elif error_info["type"] == "server_error":
                st.warning(f"⚠️ 서버 오류 ({project_name}). {error_info['retry_seconds']}초 대기...")
                time.sleep(error_info["retry_seconds"])
                
            else:
                st.error(f"❌ 알 수 없는 오류 ({project_name}): {error_info['message']}")
                return False, str(e), key_info
            
            attempts += 1
    
    # 모든 시도 실패
    return False, "모든 프로젝트의 할당량이 소진되었거나 서버 오류입니다.", None


# ================================
# 사이드바 (Multi-Project Manager)
# ================================
with st.sidebar:
    st.markdown("## 🎯 Multi-Project Manager")
    
    st.markdown("""
    <div class="info-box">
        <b>💡 단일 계정 다중 프로젝트 전략</b><br><br>
        
        <b>핵심 개념:</b><br>
        • 한 개 구글 계정으로 여러 프로젝트 생성 (최대 25개)<br>
        • 각 프로젝트 = 독립적 할당량 (1,500 RPD)<br>
        • 총 37,500 RPD 활용 가능! 🚀
    </div>
    """, unsafe_allow_html=True)
    
    # 모델 선택
    st.markdown("### 🤖 AI 모델")
    
    selected_model = "gemini-2.5-flash"
    st.success(f"✅ {selected_model}")
    
    st.divider()
    
    # API 키 관리
    st.markdown("### 🔐 프로젝트 API 키")
    
    # .env에서 자동 로드
    env_keys = load_api_keys_from_env()
    
    if env_keys:
        st.success(f"✅ .env에서 {len(env_keys)}개 프로젝트 로드됨")
        
        # 프로젝트 목록 표시
        with st.expander(f"📋 로드된 프로젝트 목록 ({len(env_keys)}개)", expanded=False):
            for key_info in env_keys:
                st.markdown(f"""
                <div class="project-badge">
                    Project-{key_info['index']}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ .env 파일에 API 키가 없습니다.")
    
    # 수동 입력 옵션
    st.markdown("**수동 입력 (선택):**")
    
    use_manual = st.checkbox("수동으로 키 입력", value=False)
    
    manual_keys = []
    if use_manual:
        num_manual = st.number_input(
            "입력할 프로젝트 수",
            min_value=1,
            max_value=25,
            value=3,
            help="각 프로젝트의 API 키를 입력하세요"
        )
        
        for i in range(int(num_manual)):
            key = st.text_input(
                f"Project-{i+1} API Key",
                type="password",
                key=f"manual_key_{i}",
                help=f"프로젝트 #{i+1}의 API 키"
            )
            
            if key.strip():
                manual_keys.append({
                    "key": key.strip(),
                    "project": f"Project-{i+1}",
                    "index": i+1
                })
    
    # 키 병합
    all_keys = env_keys if env_keys else manual_keys
    
    st.divider()
    
    # 상태 표시
    st.markdown("### 📊 시스템 상태")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("프로젝트", f"{len(all_keys)}개")
    
    with col2:
        total_quota = len(all_keys) * 1500
        st.metric("총 일일 할당량", f"{total_quota:,}")
    
    if all_keys:
        st.success("🟢 준비 완료")
        
        # 현재 활성 프로젝트
        if 'current_project_idx' in st.session_state:
            idx = st.session_state.current_project_idx
            if idx < len(all_keys):
                current = all_keys[idx]
                st.info(f"현재: {current['project']}")
    else:
        st.error("🔴 API 키를 입력하세요")
    
    st.divider()
    
    # 할당량 정보
    st.markdown("### 📈 할당량 안내")
    
    st.markdown(f"""
    <div class="quota-info">
        <b>프로젝트당 무료 티어:</b><br>
        • 분당: 15 RPM<br>
        • 일일: 1,500 RPD<br>
        • 토큰: 1M TPM<br><br>
        
        <b>현재 시스템:</b><br>
        • 프로젝트: {len(all_keys)}개<br>
        • 총 일일 할당량: <b>{len(all_keys) * 1500:,} RPD</b> 🚀<br>
        • 분당 할당량: <b>{len(all_keys) * 15} RPM</b><br><br>
        
        <b>💡 예상 분석 가능 횟수:</b><br>
        • 일일: 약 {len(all_keys) * 1500:,}회<br>
        • 시간당: 약 {len(all_keys) * 60:,}회
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # 프로젝트 생성 가이드
    with st.expander("📚 프로젝트 생성 가이드", expanded=False):
        st.markdown("""
        **단계별 가이드:**
        
        1. **Google Cloud Console 접속**
           - https://console.cloud.google.com
        
        2. **새 프로젝트 생성** (최대 25개)
           - 좌측 상단 프로젝트 선택
           - "새 프로젝트" 클릭
           - 프로젝트 이름 입력 (예: arch-analysis-1)
           - 생성 완료
        
        3. **Gemini API 활성화**
           - API 및 서비스 → 라이브러리
           - "Generative Language API" 검색
           - 사용 설정 클릭
        
        4. **API 키 생성**
           - 사용자 인증 정보 → API 키 만들기
           - 키 복사
        
        5. **반복** (프로젝트 2, 3, ... 25까지)
        
        6. **.env 파일에 추가**
           ```
           GOOGLE_API_KEY_1=첫번째프로젝트키
           GOOGLE_API_KEY_2=두번째프로젝트키
           ...
           GOOGLE_API_KEY_25=25번째프로젝트키
           ```
        """)


# ================================
# 메인 UI
# ================================
st.markdown(
    '<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템'
    '<span class="version-badge">v4.6</span></div>',
    unsafe_allow_html=True
)

st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <p style='font-size: 1.1rem; color: #555;'>
        🚀 <b>Gemini 2.5 Flash</b> | 단일 계정 다중 프로젝트 전략<br>
        한 계정으로 최대 <b>37,500 RPD</b> 활용!
    </p>
</div>
""", unsafe_allow_html=True)

# 시스템 정보 표시
if all_keys:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📂 활성 프로젝트", f"{len(all_keys)}개")
    
    with col2:
        st.metric("📊 총 일일 할당량", f"{len(all_keys) * 1500:,}")
    
    with col3:
        st.metric("⚡ 분당 할당량", f"{len(all_keys) * 15}")
    
    with col4:
        st.metric("🎯 예상 분석", f"~{len(all_keys) * 1500:,}회/일")

st.divider()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 입력 섹션
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-header">📍 1. 대상지 정보</div>', unsafe_allow_html=True)

target_address = st.text_input(
    "대상지 주소",
    placeholder="예: 서울특별시 강남구 역삼동 123-45"
)

st.markdown('<div class="section-header">🗺️ 2. 지역지구 선택</div>', unsafe_allow_html=True)

selected_all_zones = []
cols = st.columns(len(ZONES_DATA))

for i, (cat, opts) in enumerate(ZONES_DATA.items()):
    with cols[i]:
        st.markdown(f'<span style="font-size: 0.85rem; font-weight: bold; color: #c2410c;">{cat}</span>', unsafe_allow_html=True)
        selected = st.multiselect(
            f"선택_{i}",
            opts,
            key=f"zone_sel_{i}",
            label_visibility="collapsed"
        )
        selected_all_zones.extend(selected)

if selected_all_zones:
    st.success(f"✅ 선택: {', '.join(selected_all_zones)}")

st.divider()

st.markdown('<div class="section-header">📂 3. 파일 업로드</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    comp_file = st.file_uploader(
        "📄 공모 지침서 (PDF)",
        type=['pdf']
    )
    
    if comp_file:
        st.success(f"✅ {comp_file.name} ({comp_file.size / 1024:.1f} KB)")

with col2:
    reg_files = st.file_uploader(
        "⚖️ 조례/법규 PDF (다중)",
        type=['pdf'],
        accept_multiple_files=True
    )
    
    if reg_files:
        st.success(f"✅ {len(reg_files)}개 파일")
        for idx, f in enumerate(reg_files, 1):
            st.text(f"{idx}. {f.name} ({f.size / 1024:.1f} KB)")

st.divider()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 분석 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-header">🚀 4. AI 분석 실행</div>', unsafe_allow_html=True)

analyze_button = st.button(
    "🔍 멀티 프로젝트 통합 분석 시작",
    type="primary",
    use_container_width=True
)

if analyze_button:
    # 검증
    if not all_keys:
        st.error("❌ API 키를 최소 1개 이상 등록하세요!")
    elif not comp_file:
        st.error("❌ 공모 지침서를 업로드하세요!")
    elif not target_address:
        st.error("❌ 대상지 주소를 입력하세요!")
    elif not selected_all_zones:
        st.error("❌ 지역지구를 선택하세요!")
    else:
        st.markdown("---")
        st.markdown("### 🔄 분석 진행 중...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 파일 업로드
        status_text.info("📤 1/3: 파일 업로드 중...")
        progress_bar.progress(0.1)
        
        try:
            # 첫 번째 프로젝트로 파일 업로드
            genai.configure(api_key=all_keys[0]["key"])
            
            comp_gemini = upload_to_gemini(comp_file, "공모지침서")
            
            if not comp_gemini:
                raise Exception("공모지침서 업로드 실패")
            
            progress_bar.progress(0.3)
            
            reg_geminis = []
            for idx, reg_file in enumerate(reg_files, 1):
                status_text.info(f"📤 법규 {idx}/{len(reg_files)} 업로드 중...")
                reg_gemini = upload_to_gemini(reg_file, f"법규_{idx}")
                
                if reg_gemini:
                    reg_geminis.append(reg_gemini)
                
                progress_bar.progress(0.3 + (0.2 * idx / len(reg_files)))
            
            status_text.success("✅ 파일 업로드 완료!")
            progress_bar.progress(0.5)
            
        except Exception as e:
            st.error(f"❌ 파일 업로드 오류: {str(e)}")
            st.stop()
        
        # AI 분석
        status_text.info("🤖 2/3: AI 분석 중 (멀티 프로젝트 로테이션)...")
        progress_bar.progress(0.6)
        
        def analyze_with_ai():
            """AI 분석 함수"""
            model = genai.GenerativeModel(selected_model)
            
            prompt = f"""
당신은 대한민국 건축법 전문가입니다.
첨부된 공모지침서와 법규를 분석하여 종합 보고서를 작성하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 **대상지 정보**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 주소: {target_address}
• 지역지구: {', '.join(selected_all_zones)}
• 법규 문서: {len(reg_geminis)}개

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 **분석 요청**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **공모 개요**
   - 프로젝트명, 위치, 용도
   - 대지면적, 건폐율, 용적률
   - 층수, 높이 제한

2. **법규 위계 분석**
   - 상위법 (국계법)
   - 하위법 (조례)
   - 실질 적용 기준

3. **설계 가이드**
   - 필수 준수사항
   - 완화 가능 조건
   - 주의사항

**출력:**
- 명확한 구조
- 조항 번호 정확히
- 구체적 수치
"""
            
            content_list = [comp_gemini] + reg_geminis + [prompt]
            
            response = model.generate_content(
                content_list,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                }
            )
            
            return response.text
        
        # 멀티 프로젝트 분석 시도
        success, result, used_project = try_with_multi_project_keys(
            all_keys,
            analyze_with_ai,
            max_retries_per_key=2
        )
        
        progress_bar.progress(0.9)
        
        if success:
            status_text.success("✅ 분석 완료!")
            progress_bar.progress(1.0)
            
            # 사용된 프로젝트 정보
            if used_project:
                st.markdown(f"""
                <div class="success-box">
                    <b>✅ 분석 성공!</b><br>
                    사용된 프로젝트: <b>{used_project['project']}</b> (키 #{used_project['index']})<br>
                    총 프로젝트: {len(all_keys)}개 중 사용
                </div>
                """, unsafe_allow_html=True)
            
            # 결과 표시
            st.markdown("---")
            st.markdown("### 📊 분석 결과")
            
            st.markdown(result)
            
            # 다운로드
            st.divider()
            st.markdown("### 💾 결과 저장")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    "📄 Markdown",
                    data=result,
                    file_name=f"분석_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    "📝 텍스트",
                    data=result,
                    file_name=f"분석_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col3:
                json_data = {
                    "분석일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "대상지": target_address,
                    "지역지구": selected_all_zones,
                    "사용프로젝트": used_project['project'] if used_project else "Unknown",
                    "총프로젝트수": len(all_keys),
                    "결과": result
                }
                
                st.download_button(
                    "📊 JSON",
                    data=json.dumps(json_data, ensure_ascii=False, indent=2),
                    file_name=f"데이터_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        else:
            status_text.error("❌ 분석 실패")
            progress_bar.progress(0)
            
            st.markdown(f"""
            <div class="error-box">
                <h4>❌ 분석 실패</h4>
                <p><b>오류:</b> {result}</p>
                
                <h5>💡 해결 방법:</h5>
                <ol>
                    <li><b>프로젝트 추가:</b> Google Cloud에서 새 프로젝트 생성</li>
                    <li><b>대기:</b> 1시간 후 재시도 (할당량 복구)</li>
                    <li><b>파일 최적화:</b> PDF 크기/개수 줄이기</li>
                    <li><b>분산 사용:</b> 시간대를 분산하여 사용</li>
                </ol>
                
                <h5>📞 지원:</h5>
                <p>문제 지속 시 <a href="https://ai.google.dev/gemini-api/docs/quota" target="_blank">할당량 가이드</a> 참조</p>
            </div>
            """, unsafe_allow_html=True)

# 푸터
st.divider()

st.markdown(f"""
<div class="copyright">
    <b>All intellectual property rights belong to Kim Doyoung.</b><br>
    Copyright © {datetime.now().year} Architecture AI Lab. All Rights Reserved.<br><br>
    
    🚀 <b>Powered by Google Gemini 2.5 Flash</b> | v4.6 Multi-Project Edition<br>
    단일 계정 다중 프로젝트 전략 | 최대 37,500 RPD | 스마트 로테이션<br><br>
    
    <small>
    ⚠️ <b>법적 고지:</b> 본 분석은 AI 기반 참고 자료이며, 법적 효력이 없습니다.<br>
    실제 건축 계획 시 반드시 전문가의 검토를 받으시기 바랍니다.
    </small>
</div>
""", unsafe_allow_html=True)