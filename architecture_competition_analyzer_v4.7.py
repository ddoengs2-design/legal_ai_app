"""
건축 공모 & 법규 분석 시스템 v4.7 - Enhanced API Validation Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 v4.7 주요 개선:
- API 키 유효성 사전 체크
- Generative Language API 활성화 확인
- 상세한 에러 메시지 및 해결 가이드
- 프로젝트별 키 상태 표시
- 자동 문제 진단 및 해결책 제시
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
    page_title="건축 공모 & 법규 분석 시스템 v4.7",
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
    
    .key-status-valid {
        background: #d1fae5;
        border: 2px solid #10b981;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.3rem 0;
    }
    
    .key-status-invalid {
        background: #fee2e2;
        border: 2px solid #ef4444;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.3rem 0;
    }
    
    .key-status-checking {
        background: #fef3c7;
        border: 2px solid #f59e0b;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.3rem 0;
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
    
    .help-box {
        background: #eff6ff;
        border: 2px solid #3b82f6;
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
# API 키 검증 함수
# ================================

def validate_api_key(api_key, project_name="Unknown"):
    """
    API 키 유효성 검증
    
    Returns:
        dict: {"valid": bool, "message": str, "error_type": str}
    """
    try:
        # API 키 설정
        genai.configure(api_key=api_key)
        
        # 간단한 테스트 (모델 리스트 조회)
        models = genai.list_models()
        
        # Gemini 모델 존재 확인
        gemini_models = [m for m in models if 'gemini' in m.name.lower()]
        
        if gemini_models:
            return {
                "valid": True,
                "message": f"✅ {project_name}: API 키 유효",
                "error_type": None
            }
        else:
            return {
                "valid": False,
                "message": f"❌ {project_name}: Gemini 모델 없음",
                "error_type": "no_gemini_models"
            }
            
    except Exception as e:
        error_str = str(e)
        
        if "API_KEY_INVALID" in error_str or "not valid" in error_str:
            return {
                "valid": False,
                "message": f"❌ {project_name}: API 키 유효하지 않음",
                "error_type": "invalid_key"
            }
        elif "API has not been used" in error_str or "disabled" in error_str:
            return {
                "valid": False,
                "message": f"⚠️ {project_name}: Generative Language API 미활성화",
                "error_type": "api_not_enabled"
            }
        elif "PERMISSION_DENIED" in error_str:
            return {
                "valid": False,
                "message": f"⚠️ {project_name}: 권한 오류",
                "error_type": "permission_denied"
            }
        else:
            return {
                "valid": False,
                "message": f"❌ {project_name}: {str(e)[:100]}",
                "error_type": "unknown"
            }


def get_solution_for_error(error_type):
    """에러 타입별 해결책 제공"""
    
    solutions = {
        "invalid_key": """
        <div class="error-box">
            <h4>❌ API 키가 유효하지 않습니다</h4>
            
            <h5>🔧 해결 방법:</h5>
            <ol>
                <li><b>키 재확인:</b> API 키를 정확히 복사했는지 확인
                    <ul>
                        <li>공백 없이 복사</li>
                        <li>전체 키 복사 (AIzaSy로 시작)</li>
                    </ul>
                </li>
                <li><b>키 재생성:</b>
                    <ul>
                        <li><a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a> 접속</li>
                        <li>해당 프로젝트 선택</li>
                        <li>API 및 서비스 → 사용자 인증 정보</li>
                        <li>기존 키 삭제 후 새로 생성</li>
                    </ul>
                </li>
                <li><b>.env 파일 업데이트:</b> 새 키로 교체 후 앱 재시작</li>
            </ol>
        </div>
        """,
        
        "api_not_enabled": """
        <div class="warning-box">
            <h4>⚠️ Generative Language API가 활성화되지 않았습니다</h4>
            
            <h5>🔧 해결 방법:</h5>
            <ol>
                <li><b>Google Cloud Console 접속:</b>
                    <a href="https://console.cloud.google.com" target="_blank">console.cloud.google.com</a>
                </li>
                <li><b>프로젝트 선택:</b> 문제가 있는 프로젝트 선택</li>
                <li><b>API 라이브러리 이동:</b> 좌측 메뉴 → API 및 서비스 → 라이브러리</li>
                <li><b>Gemini API 검색:</b> "Generative Language API" 검색</li>
                <li><b>활성화:</b> "사용 설정" 또는 "Enable" 클릭</li>
                <li><b>대기:</b> 활성화 완료까지 1-2분 대기</li>
                <li><b>앱 재시작:</b> Streamlit 앱 새로고침</li>
            </ol>
            
            <p><b>💡 팁:</b> 각 프로젝트마다 API를 별도로 활성화해야 합니다!</p>
        </div>
        """,
        
        "permission_denied": """
        <div class="warning-box">
            <h4>⚠️ 권한 오류가 발생했습니다</h4>
            
            <h5>🔧 해결 방법:</h5>
            <ol>
                <li><b>결제 계정 확인:</b>
                    <ul>
                        <li>Google Cloud에 결제 계정이 연결되어 있는지 확인</li>
                        <li>무료 티어 사용도 결제 계정 필요</li>
                    </ul>
                </li>
                <li><b>프로젝트 권한 확인:</b>
                    <ul>
                        <li>본인이 프로젝트 소유자 또는 편집자인지 확인</li>
                        <li>IAM 및 관리자 → IAM에서 권한 확인</li>
                    </ul>
                </li>
                <li><b>API 키 제한 확인:</b>
                    <ul>
                        <li>API 키에 IP 제한이 없는지 확인</li>
                        <li>API 제한이 Generative Language API를 포함하는지 확인</li>
                    </ul>
                </li>
            </ol>
        </div>
        """,
        
        "no_gemini_models": """
        <div class="error-box">
            <h4>❌ Gemini 모델을 찾을 수 없습니다</h4>
            
            <h5>🔧 해결 방법:</h5>
            <ol>
                <li><b>API 활성화 확인:</b> Generative Language API가 활성화되었는지 재확인</li>
                <li><b>지역 확인:</b> 일부 지역에서는 Gemini API가 제한될 수 있음</li>
                <li><b>대기:</b> API 활성화 후 5-10분 대기</li>
                <li><b>다른 프로젝트 시도:</b> 새 프로젝트를 만들어 테스트</li>
            </ol>
        </div>
        """,
        
        "unknown": """
        <div class="error-box">
            <h4>❌ 알 수 없는 오류</h4>
            
            <h5>🔧 일반적인 해결 방법:</h5>
            <ol>
                <li>인터넷 연결 확인</li>
                <li>방화벽 또는 프록시 설정 확인</li>
                <li>Google Cloud 서비스 상태 확인</li>
                <li>잠시 후 다시 시도</li>
            </ol>
            
            <p>
                <b>지원:</b> 
                <a href="https://ai.google.dev/gemini-api/docs/troubleshooting" target="_blank">
                    Gemini API 문제 해결 가이드
                </a>
            </p>
        </div>
        """
    }
    
    return solutions.get(error_type, solutions["unknown"])


def load_and_validate_api_keys():
    """
    .env에서 API 키 로드 및 유효성 검증
    
    Returns:
        tuple: (valid_keys, invalid_keys, validation_results)
    """
    valid_keys = []
    invalid_keys = []
    validation_results = []
    
    # .env에서 로드
    for i in range(1, 26):
        key = os.getenv(f"GOOGLE_API_KEY_{i}", "")
        
        if key.strip():
            project_name = f"Project-{i}"
            
            # 유효성 검증
            result = validate_api_key(key.strip(), project_name)
            
            validation_results.append({
                "project": project_name,
                "index": i,
                **result
            })
            
            if result["valid"]:
                valid_keys.append({
                    "key": key.strip(),
                    "project": project_name,
                    "index": i
                })
            else:
                invalid_keys.append({
                    "project": project_name,
                    "index": i,
                    "error_type": result["error_type"],
                    "message": result["message"]
                })
    
    return valid_keys, invalid_keys, validation_results


# ================================
# 기타 유틸리티 함수
# ================================

def upload_to_gemini(file, display_name=None):
    """PDF 파일을 Gemini에 업로드"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        
        name = display_name or file.name
        gemini_file = genai.upload_file(tmp_path, display_name=name)
        
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
        raise Exception(f"파일 업로드 오류: {str(e)}")


def parse_error_message(error):
    """에러 메시지 파싱"""
    error_str = str(error)
    
    if "429" in error_str or "quota" in error_str.lower():
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
    """여러 프로젝트의 API 키로 순차 시도"""
    
    if not api_keys_info:
        return False, "유효한 API 키가 없습니다.", None
    
    total_keys = len(api_keys_info)
    
    if 'current_project_idx' not in st.session_state:
        st.session_state.current_project_idx = 0
    if 'project_fail_count' not in st.session_state:
        st.session_state.project_fail_count = {}
    
    attempts = 0
    max_attempts = total_keys * max_retries_per_key
    
    while attempts < max_attempts:
        current_idx = st.session_state.current_project_idx
        key_info = api_keys_info[current_idx]
        
        project_name = key_info["project"]
        api_key = key_info["key"]
        
        if project_name not in st.session_state.project_fail_count:
            st.session_state.project_fail_count[project_name] = 0
        
        if st.session_state.project_fail_count[project_name] >= max_retries_per_key:
            st.warning(f"⏭️ {project_name} 건너뛰기")
            st.session_state.current_project_idx = (current_idx + 1) % total_keys
            attempts += 1
            continue
        
        try:
            genai.configure(api_key=api_key)
            
            st.info(f"🔄 **{project_name}** 사용 중...")
            
            result = call_func()
            
            st.success(f"✅ **분석 성공!** ({project_name})")
            
            st.session_state.project_fail_count[project_name] = 0
            
            return True, result, key_info
            
        except Exception as e:
            error_info = parse_error_message(e)
            
            st.session_state.project_fail_count[project_name] += 1
            
            if error_info["type"] == "quota_exceeded":
                retry_sec = error_info["retry_seconds"]
                
                st.warning(f"⚠️ {project_name} 할당량 초과. 다음 프로젝트로 전환...")
                
                st.session_state.current_project_idx = (current_idx + 1) % total_keys
                
                time.sleep(min(5, retry_sec / 10))
                
            elif error_info["type"] == "server_error":
                st.warning(f"⚠️ 서버 오류. {error_info['retry_seconds']}초 대기...")
                time.sleep(error_info["retry_seconds"])
                
            else:
                st.error(f"❌ 오류 ({project_name}): {error_info['message']}")
                return False, str(e), key_info
            
            attempts += 1
    
    return False, "모든 프로젝트의 할당량이 소진되었습니다.", None


# ================================
# 사이드바
# ================================
with st.sidebar:
    st.markdown("## 🔐 API 키 관리 v4.7")
    
    st.markdown("""
    <div class="help-box">
        <b>✨ v4.7 신기능</b><br>
        • API 키 자동 유효성 검증<br>
        • 프로젝트별 상태 표시<br>
        • 에러 진단 및 해결책 제시<br>
        • 실시간 상태 모니터링
    </div>
    """, unsafe_allow_html=True)
    
    # 모델 선택
    st.markdown("### 🤖 AI 모델")
    selected_model = "gemini-2.5-flash"
    st.success(f"✅ {selected_model}")
    
    st.divider()
    
    # API 키 검증
    st.markdown("### 🔍 API 키 검증")
    
    if st.button("🔄 API 키 유효성 검사", use_container_width=True):
        with st.spinner("API 키 검증 중..."):
            valid_keys, invalid_keys, validation_results = load_and_validate_api_keys()
            
            st.session_state['valid_keys'] = valid_keys
            st.session_state['invalid_keys'] = invalid_keys
            st.session_state['validation_results'] = validation_results
            st.session_state['validation_done'] = True
    
    # 검증 결과 표시
    if st.session_state.get('validation_done', False):
        st.divider()
        
        valid_keys = st.session_state.get('valid_keys', [])
        invalid_keys = st.session_state.get('invalid_keys', [])
        validation_results = st.session_state.get('validation_results', [])
        
        # 요약
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ 유효", len(valid_keys))
        with col2:
            st.metric("❌ 무효", len(invalid_keys))
        
        # 상세 결과
        with st.expander(f"📋 검증 결과 상세 ({len(validation_results)}개)", expanded=True):
            for result in validation_results:
                if result['valid']:
                    st.markdown(f"""
                    <div class="key-status-valid">
                        ✅ <b>{result['project']}</b><br>
                        API 키 정상 작동
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="key-status-invalid">
                        ❌ <b>{result['project']}</b><br>
                        {result['message']}<br>
                        <small>타입: {result['error_type']}</small>
                    </div>
                    """, unsafe_allow_html=True)
        
        # 무효 키 해결 가이드
        if invalid_keys:
            st.divider()
            st.markdown("### 🔧 문제 해결")
            
            for invalid in invalid_keys:
                with st.expander(f"❌ {invalid['project']} 해결 방법"):
                    st.markdown(get_solution_for_error(invalid['error_type']), unsafe_allow_html=True)
    
    else:
        st.info("👆 'API 키 유효성 검사' 버튼을 클릭하여 키를 검증하세요")
    
    st.divider()
    
    # 할당량 정보
    st.markdown("### 📈 할당량 안내")
    
    valid_count = len(st.session_state.get('valid_keys', []))
    
    if valid_count > 0:
        st.markdown(f"""
        <div class="success-box">
            <b>✅ 활성 프로젝트: {valid_count}개</b><br>
            총 일일 할당량: <b>{valid_count * 1500:,} RPD</b><br>
            분당 할당량: <b>{valid_count * 15} RPM</b>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ 유효한 API 키를 등록하세요")


# ================================
# 메인 UI
# ================================
st.markdown(
    '<div class="main-title">🏛️ 건축 공모 & 법규 분석 시스템'
    '<span class="version-badge">v4.7</span></div>',
    unsafe_allow_html=True
)

st.markdown("""
<div style='text-align: center; margin-bottom: 2rem;'>
    <p style='font-size: 1.1rem; color: #555;'>
        🚀 <b>Gemini 2.5 Flash</b> | API 키 자동 검증 + 스마트 에러 핸들링<br>
        단일 계정 다중 프로젝트 전략 | 최대 37,500 RPD
    </p>
</div>
""", unsafe_allow_html=True)

# 유효한 키 확인
valid_keys = st.session_state.get('valid_keys', [])

if not valid_keys:
    st.markdown("""
    <div class="warning-box">
        <h3>⚠️ 시작하기 전에</h3>
        <ol>
            <li><b>사이드바</b>에서 "🔄 API 키 유효성 검사" 버튼 클릭</li>
            <li>유효한 키가 없으면 <b>.env 파일 설정</b> 확인</li>
            <li>API 키 발급 방법: <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
        </ol>
        
        <h4>📋 .env 파일 형식:</h4>
        <code>
        GOOGLE_API_KEY_1=AIzaSyD-your-key-here<br>
        GOOGLE_API_KEY_2=AIzaSyD-another-key<br>
        GOOGLE_API_KEY_3=AIzaSyD-third-key
        </code>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# 시스템 정보
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("✅ 유효 프로젝트", len(valid_keys))

with col2:
    st.metric("📊 총 할당량", f"{len(valid_keys) * 1500:,} RPD")

with col3:
    st.metric("⚡ 분당 할당량", f"{len(valid_keys) * 15} RPM")

with col4:
    invalid_count = len(st.session_state.get('invalid_keys', []))
    st.metric("⚠️ 무효 키", invalid_count)

st.divider()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 입력 섹션
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-header">📍 1. 대상지 정보</div>', unsafe_allow_html=True)

target_address = st.text_input("대상지 주소", placeholder="예: 서울특별시 강남구 역삼동 123-45")

st.markdown('<div class="section-header">🗺️ 2. 지역지구 선택</div>', unsafe_allow_html=True)

selected_all_zones = []
cols = st.columns(len(ZONES_DATA))

for i, (cat, opts) in enumerate(ZONES_DATA.items()):
    with cols[i]:
        st.markdown(f'<span style="font-size: 0.85rem; font-weight: bold; color: #c2410c;">{cat}</span>', unsafe_allow_html=True)
        selected = st.multiselect(f"선택_{i}", opts, key=f"zone_sel_{i}", label_visibility="collapsed")
        selected_all_zones.extend(selected)

if selected_all_zones:
    st.success(f"✅ {', '.join(selected_all_zones)}")

st.divider()

st.markdown('<div class="section-header">📂 3. 파일 업로드</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    comp_file = st.file_uploader("📄 공모 지침서 (PDF)", type=['pdf'])
    if comp_file:
        st.success(f"✅ {comp_file.name} ({comp_file.size / 1024:.1f} KB)")

with col2:
    reg_files = st.file_uploader("⚖️ 조례/법규 PDF", type=['pdf'], accept_multiple_files=True)
    if reg_files:
        st.success(f"✅ {len(reg_files)}개 파일")

st.divider()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 분석 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-header">🚀 4. AI 분석</div>', unsafe_allow_html=True)

analyze_button = st.button("🔍 통합 분석 시작", type="primary", use_container_width=True)

if analyze_button:
    if not comp_file:
        st.error("❌ 공모 지침서를 업로드하세요!")
    elif not target_address:
        st.error("❌ 대상지 주소를 입력하세요!")
    elif not selected_all_zones:
        st.error("❌ 지역지구를 선택하세요!")
    else:
        st.markdown("---")
        st.markdown("### 🔄 분석 진행")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 파일 업로드
        status_text.info("📤 파일 업로드 중...")
        progress_bar.progress(0.1)
        
        try:
            # 첫 번째 유효 키로 파일 업로드
            genai.configure(api_key=valid_keys[0]["key"])
            
            comp_gemini = upload_to_gemini(comp_file, "공모지침서")
            progress_bar.progress(0.3)
            
            reg_geminis = []
            for idx, reg_file in enumerate(reg_files, 1):
                status_text.info(f"📤 법규 {idx}/{len(reg_files)} 업로드...")
                reg_gemini = upload_to_gemini(reg_file, f"법규_{idx}")
                reg_geminis.append(reg_gemini)
                progress_bar.progress(0.3 + (0.2 * idx / len(reg_files)))
            
            status_text.success("✅ 파일 업로드 완료!")
            progress_bar.progress(0.5)
            
        except Exception as e:
            st.error(f"❌ 파일 업로드 오류: {str(e)}")
            st.stop()
        
        # AI 분석
        status_text.info("🤖 AI 분석 중...")
        progress_bar.progress(0.6)
        
        def analyze_with_ai():
            model = genai.GenerativeModel(selected_model)
            
            prompt = f"""
건축법 전문가로서 다음을 분석하세요:

대상지: {target_address}
지역지구: {', '.join(selected_all_zones)}
법규: {len(reg_geminis)}개 문서

1. 공모 개요 (프로젝트명, 위치, 용도, 건폐율, 용적률)
2. 법규 분석 (상위법/하위법 구분)
3. 설계 가이드 (준수사항, 완화 조건)

명확한 구조, 정확한 조항 인용, 구체적 수치 제시
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
        
        success, result, used_project = try_with_multi_project_keys(valid_keys, analyze_with_ai, 2)
        
        progress_bar.progress(0.9)
        
        if success:
            status_text.success("✅ 분석 완료!")
            progress_bar.progress(1.0)
            
            if used_project:
                st.markdown(f"""
                <div class="success-box">
                    ✅ <b>분석 성공!</b><br>
                    사용 프로젝트: <b>{used_project['project']}</b>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 📊 분석 결과")
            st.markdown(result)
            
            # 다운로드
            st.divider()
            st.markdown("### 💾 저장")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button("📄 Markdown", result, f"분석_{datetime.now().strftime('%Y%m%d_%H%M')}.md", "text/markdown", use_container_width=True)
            
            with col2:
                st.download_button("📝 텍스트", result, f"분석_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", "text/plain", use_container_width=True)
            
            with col3:
                json_data = {
                    "분석일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "대상지": target_address,
                    "지역지구": selected_all_zones,
                    "프로젝트": used_project['project'] if used_project else "Unknown",
                    "결과": result
                }
                
                st.download_button("📊 JSON", json.dumps(json_data, ensure_ascii=False, indent=2), f"데이터_{datetime.now().strftime('%Y%m%d_%H%M')}.json", "application/json", use_container_width=True)
        
        else:
            status_text.error("❌ 분석 실패")
            progress_bar.progress(0)
            
            st.error(f"오류: {result}")

# 푸터
st.divider()

st.markdown(f"""
<div class="copyright">
    <b>All intellectual property rights belong to Kim Doyoung.</b><br>
    Copyright © {datetime.now().year} Architecture AI Lab. All Rights Reserved.<br><br>
    
    🚀 <b>Powered by Gemini 2.5 Flash</b> | v4.7 Enhanced API Validation<br>
    API 키 자동 검증 | 스마트 에러 핸들링 | 실시간 상태 모니터링
</div>
""", unsafe_allow_html=True)