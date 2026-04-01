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
    st.session_state.gender = "남학생"
    st.session_state.sub_step = 1
    st.session_state.my_assigned = None
    st.session_state.history_data = []
    st.session_state.state_stack = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False
    
    # 전체 학교 리스트
    all_schools = [
        "낙생고", "돌마고", "보평고", "분당고", "분당대진고", 
        "분당중앙고", "불곡고", "서현고", "송림고", "수내고", 
        "야탑고", "영덕여고", "운중고", "이매고", "늘푸른고",
        "태원고", "판교고", "한솔고"
    ]
    
    # 쿠키 로드
    m_limits = cookie_manager.get(cookie="limits_male")
    f_limits = cookie_manager.get(cookie="limits_female")
    m_choices = cookie_manager.get(cookie="choices_male")
    f_choices = cookie_manager.get(cookie="choices_female")
    
    st.session_state.limits_male = m_limits if m_limits else {s: 1 for s in all_schools if s != "영덕여고"}
    st.session_state.limits_female = f_limits if f_limits else {s: 1 for s in all_schools}
    st.session_state.choices_male = m_choices if m_choices else {"s1": [], "s2": []}
    st.session_state.choices_female = f_choices if f_choices else {"s1": [], "s2": []}

# 현재 성별 데이터 매핑
gender_key = "male" if st.session_state.gender == "남학생" else "female"
current_limits = st.session_state.limits_male if gender_key == "male" else st.session_state.limits_female
current_choices = st.session_state.choices_male if gender_key == "male" else st.session_state.choices_female
DISPLAY_SCHOOLS = sorted([s for s in current_limits.keys() if not (gender_key == "male" and s == "영덕여고")])

# --- 유틸리티 함수 ---
def save_all_to_cookie():
    cookie_manager.set(f"limits_{gender_key}", current_limits, key=f"save_lim_{gender_key}")
    cookie_manager.set(f"choices_{gender_key}", current_choices, key=f"save_cho_{gender_key}")

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

# --- STEP 1: 설정 ---
if st.session_state.step == "SETTING":
    st.title("⚙️ 1단계: 성별 및 학교 마감 설정")
    st.session_state.gender = st.radio("성별 선택", ["남학생", "여학생"], horizontal=True)
    st.info(f"💡 {st.session_state.gender} 기준 (남학생 선택 시 영덕여고 제외)")
    
    st.divider()
    cols = st.columns(6) 
    for i, school in enumerate(DISPLAY_SCHOOLS):
        with cols[i % 6]:
            current_limits[school] = st.number_input(
                f"{school}", min_value=1, max_value=18, 
                value=current_limits[school], key=f"lim_in_{gender_key}_{school}"
            )
    
    if st.button("💾 설정 저장 및 지망 작성", use_container_width=True, type="primary"):
        save_all_to_cookie()
        st.session_state.step = "CHOICE"
        st.rerun()

# --- STEP 2: 지망 작성 ---
elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    col1, col2 = st.columns(2)
    with col1:
        current_choices["s1"] = st.multiselect("학군내 (5개)", DISPLAY_SCHOOLS, default=current_choices["s1"], max_selections=5, key=f"sel1_{gender_key}")
    with col2:
        max_num = 17 if gender_key == "male" else 18
        current_choices["s2"] = st.multiselect(f"구역내 ({max_num}개)", DISPLAY_SCHOOLS, default=current_choices["s2"], max_selections=max_num, key=f"sel2_{gender_key}")
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("💾 현재 지망 순위 저장", use_container_width=True):
            save_all_to_cookie()
            st.success("저장 완료!")
    with c_btn2:
        if st.button("🚀 시뮬레이션 시작", use_container_width=True, type="primary"):
            if len(current_choices["s1"]) == 5 and len(current_choices["s2"]) == max_num:
                reset_simulation_only(); st.rerun()
            else: st.error("모든 지망을 선택해주세요.")

# --- STEP 3 & 4: 추첨 단계 ---
elif st.session_state.step in ["STAGE1", "STAGE2"]:
    is_s1 = st.session_state.step == "STAGE1"
    curr_idx = st.session_state.sub_step - 1
    target = current_choices["s1"][curr_idx] if is_s1 else current_choices["s2"][curr_idx]
    base_limit = current_limits[target]
    res_key = f"{st.session_state.step}_{st.session_state.sub_step}"
    
    if res_key not in st.session_state.stage_results:
        # 시뮬레이션 연산
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
        _, m_col, _ = st.columns([1, 2, 1])
        with m_col:
            if st.session_state.current_result == "PASS":
                st.success(f"### 🎊 **{target}** 배정 성공!")
                if st.button("최종 리포트 확인", use_container_width=True, type="primary"):
                    st.session_state.my_assigned = target
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "합격", "사유": res['reason']})
                    st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; st.rerun()
            else:
                st.error(f"### ❌ **{target}** 탈락")
                if st.button("다음 지망으로 이동", use_container_width=True, type="primary"):
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "탈락", "사유": res['reason']})
                    st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                    if is_s1 and st.session_state.sub_step == 5:
                        st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                    else: st.session_state.sub_step += 1
                    st.session_state.show_intermediate = False; st.rerun()
    else:
        st.title(f"📍 {st.session_state.sub_step}지망 추첨 현황")
        m1, m2 = st.columns([2, 1])
        with m1:
            fig = px.bar(x=["남은 정원", "지원자 수"], y=[res['rem'], res['comp']], color=["남은 정원", "지원자 수"], text=[res['rem'], res['comp']], color_discrete_map={"남은 정원":"#2ecc71", "지원자 수":"#e74c3c"})
            st.plotly_chart(fig, use_container_width=True)
        with m2:
            st.subheader(target)
            if res['rem'] == 0:
                st.error("마감")
                if st.button("탈락 확인", use_container_width=True): 
                    st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            elif res['comp'] > res['rem']:
                st.warning("추첨 경합")
                if st.button("🎯 합격", use_container_width=True, type="primary"): 
                    st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()
                if st.button("❌ 탈락", use_container_width=True): 
                    st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            else:
                st.success("안정권")
                if st.button("결과 확인 👉", use_container_width=True, type="primary"): 
                    st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()

# --- STEP 5: 최종 리포트 ---
elif st.session_state.step == "RESULT":
    st.balloons(); st.title("🎊 최종 결과")
    st.info(f"### 최종 배정교: {st.session_state.my_assigned}")
    st.table(pd.DataFrame(st.session_state.history_data))

# --- 컨트롤 바 ---
st.divider()
f_cols = st.columns([1, 1, 1, 1, 2])
if st.session_state.step != "SETTING":
    if f_cols[1].button("🏠 처음으로"): st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; st.rerun()
    if f_cols[2].button("🧹 지망 비우기"): current_choices["s1"] = []; current_choices["s2"] = []; st.session_state.step = "CHOICE"; st.rerun()
    if f_cols[3].button("🚨 전체 초기화"): 
        cookie_manager.delete(f"limits_{gender_key}"); cookie_manager.delete(f"choices_{gender_key}")
        for k in list(st.session_state.keys()): st.session_state.pop(k)
        st.rerun()