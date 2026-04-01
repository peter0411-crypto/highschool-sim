import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 1. 학교 리스트 및 상수 ---
ALL_SCHOOLS = [
    "낙생고", "돌마고", "보평고", "분당고", "분당대진고", 
    "분당중앙고", "불곡고", "서현고", "송림고", "수내고", 
    "야탑고", "영덕여고", "운중고", "이매고", "늘푸른고",
    "태원고", "판교고", "한솔고"
]

# --- 2. 초기 세션 상태 설정 및 URL 로드 ---
if 'initialized' not in st.session_state:
    params = st.query_params
    st.session_state.step = params.get("step", "SETTING")
    st.session_state.gender = params.get("gender", "남학생")
    st.session_state.sub_step = int(params.get("sub_step", 1))
    
    for s in ALL_SCHOOLS:
        st.session_state[f"lim_m_{s}"] = int(params.get(f"m_{s}", 1))
        st.session_state[f"lim_f_{s}"] = int(params.get(f"f_{s}", 1))
    
    def parse_list(key):
        val = params.get(key, "")
        return [x for x in val.split(",") if x] if val else []

    st.session_state.c_m = {"s1": parse_list("cm1"), "s2": parse_list("cm2")}
    st.session_state.c_f = {"s1": parse_list("cf1"), "s2": parse_list("cf2")}
    
    st.session_state.history_data = []
    st.session_state.stage_results = {}
    st.session_state.remaining_quota = 40
    st.session_state.show_intermediate = False
    st.session_state.initialized = True

# --- 3. 데이터 동기화 함수 (URL 업데이트) ---
def sync_to_url():
    new_params = {
        "step": st.session_state.step,
        "gender": st.session_state.gender,
        "sub_step": st.session_state.sub_step,
        "cm1": ",".join(st.session_state.c_m["s1"]),
        "cm2": ",".join(st.session_state.c_m["s2"]),
        "cf1": ",".join(st.session_state.c_f["s1"]),
        "cf2": ",".join(st.session_state.c_f["s2"])
    }
    for s in ALL_SCHOOLS:
        new_params[f"m_{s}"] = st.session_state[f"lim_m_{s}"]
        new_params[f"f_{s}"] = st.session_state[f"lim_f_{s}"]
    st.query_params.update(new_params)

# 현재 데이터 매핑
g_code = "m" if st.session_state.gender == "남학생" else "f"
curr_choices = st.session_state.c_m if g_code == "m" else st.session_state.c_f
DISPLAY_SCHOOLS = sorted([s for s in ALL_SCHOOLS if not (g_code == "m" and s == "영덕여고")])

st.set_page_config(page_title="성남 2구역 고교 배정 시뮬레이터", layout="wide")

# --- 4. 메인 화면 로직 (구조 주의) ---

# STEP 1: 설정 (여기가 'if'로 시작해야 합니다)
if st.session_state.step == "SETTING":
    st.title("⚙️ 1단계: 학교별 마감 지망 설정")
    new_gender = st.radio("성별 선택", ["남학생", "여학생"], index=0 if g_code == "m" else 1, horizontal=True)
    if new_gender != st.session_state.gender:
        st.session_state.gender = new_gender
        sync_to_url(); st.rerun()
    
    st.divider()
    cols = st.columns(6)
    for i, school in enumerate(DISPLAY_SCHOOLS):
        with cols[i % 6]:
            key = f"lim_{g_code}_{school}"
            st.session_state[key] = st.number_input(f"{school}", 1, 18, value=st.session_state[key], key=f"in_{key}")

    if st.button("➡️ 지망 순위 작성하러 가기", use_container_width=True, type="primary"):
        sync_to_url(); st.session_state.step = "CHOICE"; st.rerun()

# STEP 2: 지망 선택 및 순위 조정 (여기가 'elif'입니다)
# --- STEP 2: 지망 선택 및 순위 조정 (완전 수정 버전) ---
elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    st.info("💡 학교를 먼저 모두 선택한 후, 아래 리스트의 🔼🔽 버튼으로 순서를 조정하세요.")
    
    c1, c2 = st.columns(2)
    
    # [수정 포인트 1] 학군내 배정
    with c1:
        st.subheader("1. 학군내 배정 (5개교)")
        # 위젯의 key를 성별과 현재 리스트 상태에 연동하여, 순서 변경 시 위젯이 강제 갱신되게 함
        selected_s1 = st.multiselect(
            "학교 선택", 
            DISPLAY_SCHOOLS, 
            default=st.session_state.c_m["s1"] if g_code == "m" else st.session_state.c_f["s1"],
            max_selections=5,
            key=f"ms1_widget_{g_code}_{len(curr_choices['s1'])}" 
        )
        # 위젯 선택 결과를 세션에 즉시 반영
        curr_choices["s1"] = selected_s1
        
        # 순서 조정 UI
        for i, sch in enumerate(curr_choices["s1"]):
            r_cols = st.columns([3, 1, 1])
            r_cols[0].write(f"**{i+1}지망**: {sch}")
            # [수정 포인트 2] 버튼 클릭 시 세션 리스트를 직접 수정하고 즉시 sync & rerun
            if r_cols[1].button("🔼", key=f"u1_{sch}_{i}") and i > 0:
                curr_choices["s1"][i], curr_choices["s1"][i-1] = curr_choices["s1"][i-1], curr_choices["s1"][i]
                sync_to_url()
                st.rerun()
            if r_cols[2].button("🔽", key=f"d1_{sch}_{i}") and i < len(curr_choices["s1"])-1:
                curr_choices["s1"][i], curr_choices["s1"][i+1] = curr_choices["s1"][i+1], curr_choices["s1"][i]
                sync_to_url()
                st.rerun()

    # [수정 포인트 3] 구역내 배정
    with c2:
        st.subheader("2. 구역내 배정 (전체)")
        max_n = 17 if g_code == "m" else 18
        selected_s2 = st.multiselect(
            f"학교 선택 ({max_n}개교)", 
            DISPLAY_SCHOOLS, 
            default=curr_choices["s2"],
            max_selections=max_n,
            key=f"ms2_widget_{g_code}_{len(curr_choices['s2'])}"
        )
        curr_choices["s2"] = selected_s2
        
        with st.expander("구역내 지망 순위 상세 조정", expanded=True):
            for i, sch in enumerate(curr_choices["s2"]):
                r_cols = st.columns([3, 1, 1])
                r_cols[0].write(f"**{i+1}지망**: {sch}")
                if r_cols[1].button("🔼", key=f"u2_{sch}_{i}") and i > 0:
                    curr_choices["s2"][i], curr_choices["s2"][i-1] = curr_choices["s2"][i-1], curr_choices["s2"][i]
                    sync_to_url()
                    st.rerun()
                if r_cols[2].button("🔽", key=f"d2_{sch}_{i}") and i < len(curr_choices["s2"])-1:
                    curr_choices["s2"][i], curr_choices["s2"][i+1] = curr_choices["s2"][i+1], curr_choices["s2"][i]
                    sync_to_url()
                    st.rerun()

# STEP 3: 추첨 단계
elif st.session_state.step in ["STAGE1", "STAGE2"]:
    is_s1 = st.session_state.step == "STAGE1"
    curr_idx = st.session_state.sub_step - 1
    target = curr_choices["s1"][curr_idx] if is_s1 else curr_choices["s2"][curr_idx]
    base_limit = st.session_state[f"lim_{g_code}_{target}"]
    res_key = f"{st.session_state.step}_{st.session_state.sub_step}"
    
    def calculate_draw():
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
            reason = f"추첨 경합"
        else:
            rem, comp, reason = 0, np.random.randint(50, 100), "정원 마감"
        return {'comp': comp, 'rem': rem, 'reason': reason, 'others_taken': np.random.randint(5, 12)}

    if res_key not in st.session_state.stage_results:
        st.session_state.stage_results[res_key] = calculate_draw()
    res = st.session_state.stage_results[res_key]

    if st.session_state.show_intermediate:
        _, m_col, _ = st.columns([1, 2, 1])
        with m_col:
            if st.session_state.current_result == "PASS":
                st.success(f"### 🎊 **{target}** 배정 성공!")
                if st.button("최종 리포트 확인 🏆", use_container_width=True, type="primary"):
                    st.session_state.my_assigned = target; st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "합격"})
                    st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; sync_to_url(); st.rerun()
            else:
                st.error(f"### ❌ **{target}** 탈락")
                if st.button("다음 지망으로 이동 ➡️", use_container_width=True, type="primary"):
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "탈락"})
                    st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                    if is_s1 and st.session_state.sub_step == 5: st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                    else: st.session_state.sub_step += 1
                    st.session_state.show_intermediate = False; sync_to_url(); st.rerun()
    else:
        st.title(f"📍 {st.session_state.sub_step}지망 추첨 현황")
        m1, m2 = st.columns([2, 1])
        with m1:
            fig = px.bar(x=["남은 정원", "지원자 수"], y=[res['rem'], res['comp']], color=["남은 정원", "지원자 수"], text=[res['rem'], res['comp']], color_discrete_map={"남은 정원":"#2ecc71", "지원자 수":"#e74c3c"})
            st.plotly_chart(fig, use_container_width=True)
        with m2:
            st.subheader(target)
            if res['rem'] == 0:
                st.error("마감"); st.button("탈락 확인", on_click=lambda: (st.session_state.update({"current_result":"FAIL", "show_intermediate":True})))
            elif res['comp'] > res['rem']:
                st.warning("경합 발생")
                st.button("🎯 합격 시나리오", on_click=lambda: (st.session_state.update({"current_result":"PASS", "show_intermediate":True})))
                st.button("❌ 탈락 시나리오", on_click=lambda: (st.session_state.update({"current_result":"FAIL", "show_intermediate":True})))
            else:
                st.success("안정권"); st.button("결과 확인 👉", on_click=lambda: (st.session_state.update({"current_result":"PASS", "show_intermediate":True})))

elif st.session_state.step == "RESULT":
    st.balloons(); st.title("🎊 최종 결과"); st.info(f"### 최종 배정교: {st.session_state.my_assigned}")
    st.table(pd.DataFrame(st.session_state.history_data))

# --- 하단 컨트롤 바 (항상 표시) ---
st.divider()
b_cols = st.columns(4)
if st.session_state.step != "SETTING":
    if b_cols[0].button("⬅️ 뒤로가기", use_container_width=True):
        if st.session_state.step == "CHOICE": st.session_state.step = "SETTING"
        elif st.session_state.step in ["STAGE1", "STAGE2"]: st.session_state.step = "CHOICE"
        elif st.session_state.step == "RESULT": st.session_state.step = "CHOICE"
        sync_to_url(); st.rerun()

if b_cols[1].button("🏠 처음으로", use_container_width=True):
    st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()

if b_cols[2].button("💾 현재 설정 저장", use_container_width=True):
    sync_to_url(); st.toast("✅ 주소창에 저장되었습니다!")

if b_cols[3].button("🚨 전체 초기화", use_container_width=True):
    st.query_params.clear(); st.session_state.clear(); st.rerun()