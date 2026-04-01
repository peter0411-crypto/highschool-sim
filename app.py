import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 1. 초기 세션 상태 설정 ---
if 'step' not in st.session_state:
    st.session_state.step = "SETTING"
    st.session_state.sub_step = 1
    st.session_state.my_assigned = None
    st.session_state.history_data = [] # 상세 데이터 저장을 위해 리스트로 변경
    st.session_state.state_stack = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False
    st.session_state.current_result = None
    st.session_state.school_limits = {school: 1 for school in [
        "낙생고", "돌마고", "보평고", "분당고", "분당대진고", 
        "분당중앙고", "불곡고", "서현고", "송림고", "수내고", 
        "야탑고", "영덕여고", "운중고", "이매고", "태원고", 
        "판교고", "한솔고"
    ]}

DISTRICT_2_SCHOOLS = list(st.session_state.school_limits.keys())

def reset_simulation_only():
    st.session_state.step = "STAGE1"
    st.session_state.sub_step = 1
    st.session_state.my_assigned = None
    st.session_state.history_data = []
    st.session_state.state_stack = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False

def go_back():
    if st.session_state.state_stack:
        prev = st.session_state.state_stack.pop()
        for key, value in prev.items():
            st.session_state[key] = value
        st.rerun()

def save_state():
    state = {
        'step': st.session_state.step,
        'sub_step': st.session_state.sub_step,
        'my_assigned': st.session_state.my_assigned,
        'history_data': list(st.session_state.history_data),
        'remaining_quota': st.session_state.remaining_quota,
        'show_intermediate': st.session_state.show_intermediate
    }
    st.session_state.state_stack.append(state)

st.set_page_config(page_title="성남 2구역 고교 배정 시뮬레이터", layout="wide")

# --- STEP 1: 설정 ---
if st.session_state.step == "SETTING":
    st.title("⚙️ 1단계: 학교별 마감 지망 설정")
    st.info("💡 1지망 마감 설정교는 예외 없이 1지망에서 끝납니다. 그 외는 변동성이 발생할 수 있습니다.")
    cols = st.columns(4)
    for i, school in enumerate(DISTRICT_2_SCHOOLS):
        with cols[i % 4]:
            st.session_state.school_limits[school] = st.number_input(
                f"{school}", min_value=1, max_value=17, 
                value=st.session_state.school_limits[school], key=f"lim_{school}"
            )
    if st.button("설정 완료 👉 지망 작성", use_container_width=True, type="primary"):
        st.session_state.step = "CHOICE"; st.rerun()

# --- STEP 2: 지망 작성 ---
elif st.session_state.step == "CHOICE":
    st.title("📋 2단계: 나의 지망 순위 작성")
    col1, col2 = st.columns(2)
    with col1:
        c1 = st.multiselect("학군내 배정 (5개교)", DISTRICT_2_SCHOOLS, default=st.session_state.get('my_choices_1', []), max_selections=5)
    with col2:
        c2 = st.multiselect("구역내 배정 (17개교 전체)", DISTRICT_2_SCHOOLS, default=st.session_state.get('my_choices_2', []), max_selections=17)
    
    if st.button("🚀 시뮬레이션 시작", use_container_width=True, type="primary"):
        if len(c1) == 5 and len(c2) == 17:
            st.session_state.my_choices_1, st.session_state.my_choices_2 = c1, c2
            reset_simulation_only(); st.rerun()
        else: st.error("모든 지망을 채워주세요.")

# --- STEP 3 & 4: 추첨 ---
elif st.session_state.step in ["STAGE1", "STAGE2"]:
    is_s1 = st.session_state.step == "STAGE1"
    curr_idx = st.session_state.sub_step - 1
    target = st.session_state.my_choices_1[curr_idx] if is_s1 else st.session_state.my_choices_2[curr_idx]
    base_limit = st.session_state.school_limits[target]
    res_key = f"{st.session_state.step}_{st.session_state.sub_step}"
    
    if res_key not in st.session_state.stage_results:
        # 로직: 1지망은 고정, 나머지는 유동적
        prob = np.random.random()
        actual_limit = base_limit
        note = "설정값 유지"
        if base_limit > 1:
            if prob < 0.2: actual_limit = max(1, base_limit - 1); note = "인기 폭주(조기마감)"
            elif prob < 0.5: actual_limit = base_limit + 1; note = "지원 미달(연장됨)"
        
        if st.session_state.sub_step < actual_limit:
            rem, comp, rank, reason = st.session_state.remaining_quota, np.random.randint(5, 20), 1, "정원 여유"
        elif st.session_state.sub_step == actual_limit:
            rem = st.session_state.remaining_quota
            comp = np.random.randint(rem+1, rem+40)
            rank = np.random.randint(1, comp+1)
            reason = f"추첨 경합 (1:{comp/rem:.1f})"
        else:
            rem, comp, rank, reason = 0, np.random.randint(50, 100), 999, "정원 마감"

        st.session_state.stage_results[res_key] = {
            'comp': comp, 'rank': rank, 'rem': rem, 'reason': reason, 'note': note, 'others_taken': np.random.randint(5, 12)
        }

    res = st.session_state.stage_results[res_key]

    if st.session_state.show_intermediate:
        st.title(f"📢 {st.session_state.sub_step}지망 결과")
        if st.session_state.current_result == "PASS":
            st.success(f"🎊 **{target}** 배정 성공!")
            if st.button("최종 리포트 확인", use_container_width=True):
                st.session_state.my_assigned = target
                st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "합격", "사유": res['reason']})
                st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; st.rerun()
        else:
            st.error(f"❌ **{target}** 탈락")
            if st.button("다음 지망으로 이동", use_container_width=True):
                st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "탈락", "사유": res['reason']})
                st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                if is_s1 and st.session_state.sub_step == 5:
                    st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                else: st.session_state.sub_step += 1
                st.session_state.show_intermediate = False; st.rerun()
    else:
        st.title(f"📍 {st.session_state.sub_step}지망 추첨 중")
        m1, m2 = st.columns([2, 1])
        with m1:
            fig = px.bar(x=["남은 정원", "지원자 수"], y=[res['rem'], res['comp']], color=["남은 정원", "지원자 수"], text=[res['rem'], res['comp']], color_discrete_map={"남은 정원":"#2ecc71", "지원자 수":"#e74c3c"})
            fig.update_traces(textposition='inside', textfont_size=24); fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        with m2:
            st.subheader(target); st.caption(res['note'])
            if res['rem'] == 0:
                st.error("마감됨"); 
                if st.button("탈락 확인", use_container_width=True): save_state(); st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            elif res['comp'] > res['rem']:
                st.warning("경합 발생"); 
                if st.button("🎯 합격", use_container_width=True, type="primary"): save_state(); res['rank']=1; st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()
                if st.button("❌ 탈락", use_container_width=True): save_state(); res['rank']=999; st.session_state.current_result="FAIL"; st.session_state.show_intermediate=True; st.rerun()
            else:
                st.success("안심권"); 
                if st.button("확인", use_container_width=True, type="primary"): save_state(); st.session_state.current_result="PASS"; st.session_state.show_intermediate=True; st.rerun()

# --- STEP 5: 최종 리포트 ---
elif st.session_state.step == "RESULT":
    st.balloons(); st.title("🎊 최종 배정 결과")
    st.info(f"### 배정 학교: {st.session_state.my_assigned}")
    
    st.subheader("📋 배정 상세 히스토리")
    df_history = pd.DataFrame(st.session_state.history_data)
    st.table(df_history) # 깔끔한 표 형태로 출력

    if st.button("🔄 처음부터 다시하기", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()