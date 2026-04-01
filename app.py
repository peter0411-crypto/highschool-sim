import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import extra_streamlit_components as stx

# --- 쿠키 매니저 초기화 ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 1. 초기 세션 상태 설정 ---
if 'step' not in st.session_state:
    st.session_state.step = "SETTING"
    st.session_state.gender = "남학생" # 기본값
    st.session_state.sub_step = 1
    st.session_state.my_assigned = None
    st.session_state.history_data = []
    st.session_state.state_stack = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False
    
    # 성별별 지망 순위 저장소
    st.session_state.choices_male = {"s1": [], "s2": []}
    st.session_state.choices_female = {"s1": [], "s2": []}
    
    schools = [
        "낙생고", "돌마고", "보평고", "분당고", "분당대진고", 
        "분당중앙고", "불곡고", "서현고", "송림고", "수내고", 
        "야탑고", "영덕여고", "운중고", "이매고", "늘푸른고",
        "태원고", "판교고", "한솔고"
    ]
    
    # 성별별 마감 설정 로드
    m_limits = cookie_manager.get(cookie="limits_male")
    f_limits = cookie_manager.get(cookie="limits_female")
    
    st.session_state.limits_male = m_limits if m_limits else {s: 1 for s in schools}
    st.session_state.limits_female = f_limits if f_limits else {s: 1 for s in schools}

# 현재 성별에 따른 데이터 참조 단축어
gender_key = "male" if st.session_state.gender == "남학생" else "female"
current_limits = st.session_state.limits_male if gender_key == "male" else st.session_state.limits_female
current_choices = st.session_state.choices_male if gender_key == "male" else st.session_state.choices_female

DISTRICT_2_SCHOOLS = sorted(list(current_limits.keys()))

# --- 유틸리티 함수 ---
def save_to_cookie():
    cookie_manager.set(f"limits_{gender_key}", current_limits, key=f"save_{gender_key}")

def reset_simulation_only():
    st.session_state.step = "STAGE1"
    st.session_state.sub_step = 1
    st.session_state.my_assigned = None
    st.session_state.history_data = []
    st.session_state.state_stack = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False

st.set_page_config(page_title="성남 2구역 고교 배정 시뮬레이터", layout="wide")

# --- STEP 1: 설정 및 성별 선택 ---
if st.session_state.step == "SETTING":
    st.title("⚙️ 1단계: 성별 및 학교별 마감 설정")
    
    # 성별 선택 추가
    st.session_state.gender = st.radio("성별을 선택하세요", ["남학생", "여학생"], horizontal=True)
    st.info(f"💡 **{st.session_state.gender}** 기준으로 설정을 저장하고 시뮬레이션을 진행합니다.")
    
    st.divider()
    
    cols = st.columns(6) 
    for i, school in enumerate(DISTRICT_2_SCHOOLS):
        with cols[i % 6]:
            current_limits[school] = st.number_input(
                f"{school}", min_value=1, max_value=18, 
                value=current_limits[school], key=f"lim_{gender_key}_{school}"
            )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 설정 저장 및 지망 작성하러 가기", use_container_width=True, type="primary"):
        save_to_cookie()
        st.session_state.step = "CHOICE"
        st.rerun()

# --- STEP 2: 지망 작성 ---
elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    col1, col2 = st.columns(2)
    with col1:
        current_choices["s1"] = st.multiselect(
            "학군내 배정 (5개교)", DISTRICT_2_SCHOOLS, 
            default=current_choices["s1"], max_selections=5, key=f"sel1_{gender_key}"
        )
    with col2:
        current_choices["s2"] = st.multiselect(
            "구역내 배정 (18개교 전체)", DISTRICT_2_SCHOOLS, 
            default=current_choices["s2"], max_selections=18, key=f"sel2_{gender_key}"
        )
    
    if st.button("🚀 시뮬레이션 시작", use_container_width=True, type="primary"):
        if len(current_choices["s1"]) == 5 and len(current_choices["s2"]) == 18:
            reset_simulation_only(); st.rerun()
        else: st.error("모든 지망을 선택해주세요.")

# --- STEP 3 & 4: 추첨 단계 (결과 중앙 배치 포함) ---
elif st.session_state.step in ["STAGE1", "STAGE2"]:
    is_s1 = st.session_state.step == "STAGE1"
    curr_idx = st.session_state.sub_step - 1
    target = current_choices["s1"][curr_idx] if is_s1 else current_choices["s2"][curr_idx]
    base_limit = current_limits[target]
    res_key = f"{st.session_state.step}_{st.session_state.sub_step}"
    
    if res_key not in st.session_state.stage_results:
        # 시뮬레이션 로직
        prob = np.random.random()
        actual_limit = base_limit
        if base_limit > 1:
            if prob < 0.2: actual_limit = max(1, base_limit - 1)
            elif prob < 0.5: actual_limit = base_limit + 1
        
        if st.session_state.sub_step < actual_limit:
            rem, comp, reason = st.session_state.remaining_quota, np.random.randint(5, 20), "정원 여유"
        elif st.session_state.sub_step == actual_limit:
            rem = st.session_state.remaining_quota
            comp = np.random.randint(rem+1, rem+40)
            reason = f"추첨 경합 (1:{comp/rem:.1f})"
        else:
            rem, comp, reason = 0, np.random.randint(50, 100), "정원 마감"
        st.session_state.stage_results[res_key] = {'comp': comp, 'rem': rem, 'reason': reason, 'others_taken': np.random.randint(5, 12)}

    res = st.session_state.stage_results[res_key]

    if st.session_state.show_intermediate:
        st.markdown("<br><br>", unsafe_allow_html=True)
        _, m_col, _ = st.columns([1, 2, 1])
        with m_col:
            if st.session_state.current_result == "PASS":
                st.success(f"### 🎊 **{target}** 배정 성공!")
                if st.button("최종 리포트 확인 🏆", use_container_width=True, type="primary"):
                    st.session_state.my_assigned = target
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "합격", "사유": res['reason']})
                    st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; st.rerun()
            else:
                st.error(f"### ❌ **{target}** 탈락")
                if st.button("다음 지망으로 이동 ➡️", use_container_width=True, type="primary"):
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "탈락", "사유": res['reason']})
                    st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                    if is_s1 and st.session_state.sub_step == 5:
                        st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                    else: st.session_state.sub_step += 1
                    st.session_state.show_intermediate = False; st.rerun()
    else:
        st.title(f"📍 {st.session_state.sub_step}지망 추첨 현황 ({st.session_state.gender})")
        m1, m2 = st.columns([2, 1])
        with m1:
            fig = px.bar(x=["남은 정원", "지원자 수"], y=[res['rem'], res['comp']], color=["남은 정원", "지원자 수"], text=[res['rem'], res['comp']], color_discrete_map={"남은 정원":"#2ecc71", "지원자 수":"#e74c3c"})
            fig.update_traces(textposition='inside', textfont_size=24, insidetextanchor='middle'); fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        with m2:
            st.subheader(target)
            if res['rem'] == 0:
                st.error("마감됨"); 
                if st.button("탈락 확인", use_container_width=True): st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            elif res['comp'] > res['rem']:
                st.warning("경합 발생"); 
                if st.button("🎯 합격 시나리오", use_container_width=True, type="primary"): st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()
                if st.button("❌ 탈락 시나리오", use_container_width=True): st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            else:
                st.success("안정권"); 
                if st.button("결과 확인 👉", use_container_width=True, type="primary"): st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()

# --- STEP 5: 최종 리포트 ---
elif st.session_state.step == "RESULT":
    st.balloons(); st.title(f"🎊 {st.session_state.gender} 최종 배정 결과")
    st.info(f"### 최종 배정교: {st.session_state.my_assigned}")
    st.table(pd.DataFrame(st.session_state.history_data))

# --- 하단 컨트롤 바 ---
st.divider()
f_cols = st.columns([1, 1, 1.2, 1, 2])
if st.session_state.step != "SETTING":
    if f_cols[1].button("🏠 처음 화면으로"): st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; st.session_state.stage_results = {}; st.rerun()
    if f_cols[2].button("🧹 내 지망만 초기화"): current_choices["s1"] = []; current_choices["s2"] = []; st.session_state.step = "CHOICE"; st.rerun()
    if f_cols[3].button("🚨 전체 초기화"): cookie_manager.delete(f"limits_{gender_key}"); [st.session_state.pop(k) for k in list(st.session_state.keys())]; st.rerun()