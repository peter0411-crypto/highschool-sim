import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- 1. 학교 리스트 (분당중앙고 제외) ---
ALL_SCHOOLS = [
    "낙생고", "돌마고", "보평고", "분당고", "분당대진고", 
    "불곡고", "서현고", "송림고", "수내고", 
    "야탑고", "영덕여고", "운중고", "이매고", "늘푸른고",
    "태원고", "판교고", "한솔고"
]

# --- 2. 초기 세션 상태 설정 ---
if 'initialized' not in st.session_state:
    params = st.query_params
    st.session_state.step = params.get("step", "SETTING")
    st.session_state.gender = params.get("gender", "남학생")
    st.session_state.sub_step = int(params.get("sub_step", 1))
    
    # 위젯 강제 초기화를 위한 버전 카운터 추가
    st.session_state.ms_version = 0
    
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

g_code = "m" if st.session_state.gender == "남학생" else "f"
curr_choices = st.session_state.c_m if g_code == "m" else st.session_state.c_f
DISPLAY_SCHOOLS = sorted([s for s in ALL_SCHOOLS if not (g_code == "m" and s == "영덕여고")])

st.set_page_config(page_title="성남 2구역 고교 배정 시뮬레이터", layout="wide")

# --- 4. 메인 화면 로직 ---

if st.session_state.step == "SETTING":
    st.title("⚙️ 1단계: 학교별 마감 지망 설정")
    new_gender = st.radio("성별 선택", ["남학생", "여학생"], index=0 if g_code == "m" else 1, horizontal=True)
    if new_gender != st.session_state.gender:
        st.session_state.gender = new_gender
        sync_to_url(); st.rerun()
    
    st.divider()
    cols = st.columns(6)
    for i, school in enumerate(DISPLAY_SCHOOLS):
        key = f"lim_{g_code}_{school}"
        with cols[i % 6]:
            st.session_state[key] = st.number_input(f"{school}", 1, 18, value=st.session_state[key], key=f"in_{key}")

    if st.button("➡️ 지망 순위 작성하러 가기", use_container_width=True, type="primary"):
        sync_to_url(); st.session_state.step = "CHOICE"; st.rerun()

elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    
    col_title, col_reset = st.columns([4, 1])
    with col_reset:
        # 핵심 수정 사항: 버튼을 누를 때 version 번호를 올려 키를 바꿉니다.
        if st.button("🧹 지망 리스트 비우기", use_container_width=True):
            curr_choices["s1"] = []
            curr_choices["s2"] = []
            st.session_state.ms_version += 1 # 위젯 키 변경을 위한 변수
            st.rerun()

    st.info("💡 학교를 클릭하는 순서대로 지망 순위가 결정됩니다.")
    
    c1, c2 = st.columns(2)
    # 키값에 v_{st.session_state.ms_version}를 추가하여 강제 리렌더링 유도
    with c1:
        st.session_state.ms1_val = st.multiselect(
            "1. 학군내 배정 (5개)", 
            DISPLAY_SCHOOLS, 
            default=curr_choices["s1"], 
            max_selections=5, 
            key=f"ms1_{g_code}_v{st.session_state.ms_version}"
        )
        curr_choices["s1"] = st.session_state.ms1_val
    with c2:
        max_n = len(DISPLAY_SCHOOLS)
        st.session_state.ms2_val = st.multiselect(
            f"2. 구역내 배정 ({max_n}개)", 
            DISPLAY_SCHOOLS, 
            default=curr_choices["s2"], 
            max_selections=max_n, 
            key=f"ms2_{g_code}_v{st.session_state.ms_version}"
        )
        curr_choices["s2"] = st.session_state.ms2_val

    st.divider()
    if st.button("🚀 시뮬레이션 시작", use_container_width=True, type="primary"):
        if len(curr_choices["s1"]) == 5 and len(curr_choices["s2"]) == max_n:
            st.session_state.step = "STAGE1"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()
        else:
            st.error(f"지망 학교를 모두 선택해 주세요. (현재 학군내 {len(curr_choices['s1'])}/5, 구역내 {len(curr_choices['s2'])}/{max_n})")

# (이하 추첨 및 결과 로직은 이전과 동일하므로 생략)
# --- 하단 컨트롤 바 부분 ---
elif st.session_state.step in ["STAGE1", "STAGE2"]:
    # --- 사이드바에 지망 순위 및 마감 설정 표시 ---
    with st.sidebar:
        st.header("📋 내 지망 순위 요약")
        st.caption("괄호 안은 1단계에서 설정한 마감 지망입니다.")
        
        # 학군내 배정 (1단계) 요약
        st.subheader("1. 학군내 배정")
        for i, school in enumerate(curr_choices["s1"]):
            # 해당 학교의 마감 설정값 가져오기
            limit_val = st.session_state.get(f"lim_{g_code}_{school}", "?")
            is_current = (st.session_state.step == "STAGE1" and st.session_state.sub_step == i + 1)
            
            # 레이블 구성 (예: 📍 1지망: 낙생고 (마감: 2))
            label = f"{i+1}지망: {school} (마감: {limit_val})"
            
            if is_current:
                st.info(f"**📍 {label} (추첨 중)**")
            elif any(d['학교'] == school and d['결과'] == '탈락' for d in st.session_state.history_data):
                st.text(f"❌ {label} (탈락)")
            else:
                st.text(f"▫️ {label}")
        
        st.divider()
        
        # 구역내 배정 (2단계) 요약
        st.subheader("2. 구역내 배정")
        for i, school in enumerate(curr_choices["s2"]):
            limit_val = st.session_state.get(f"lim_{g_code}_{school}", "?")
            is_current = (st.session_state.step == "STAGE2" and st.session_state.sub_step == i + 1)
            
            label = f"{i+1}지망: {school} (마감: {limit_val})"
            
            if is_current:
                st.info(f"**📍 {label} (추첨 중)**")
            elif any(d['학교'] == school and d['결과'] == '탈락' for d in st.session_state.history_data):
                st.text(f"❌ {label} (탈락)")
            else:
                st.text(f"▫️ {label}")

    # --- 기존 추첨 로직 계속 ---
    is_s1 = st.session_state.step == "STAGE1"
    # ... (이후 동일)
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
            reason = "추첨 경합"
        else:
            rem, comp, reason = 0, np.random.randint(50, 100), "정원 마감"
        return {'comp': comp, 'rem': rem, 'reason': reason, 'others_taken': np.random.randint(5, 12)}

    if res_key not in st.session_state.stage_results:
        st.session_state.stage_results[res_key] = calculate_draw()
    res = st.session_state.stage_results[res_key]

    if st.session_state.show_intermediate:
        st.markdown("<br>" * 6, unsafe_allow_html=True) 
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            if st.session_state.current_result == "PASS":
                st.success(f"## 🎊 **{target}** 배정 성공!")
                if st.button("최종 리포트 확인 🏆", use_container_width=True, type="primary"):
                    st.session_state.my_assigned = target
                    st.session_state.history_data.append({"지망": f"{st.session_state.step} {st.session_state.sub_step}지망", "학교": target, "결과": "합격"})
                    st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; sync_to_url(); st.rerun()
            else:
                st.error(f"## ❌ **{target}** 탈락")
                if st.button("다음 지망으로 이동 ➡️", use_container_width=True, type="primary"):
                    st.session_state.history_data.append({"지망": f"{st.session_state.step} {st.session_state.sub_step}지망", "학교": target, "결과": "탈락"})
                    st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                    if is_s1 and st.session_state.sub_step == 5:
                        st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                    else: st.session_state.sub_step += 1
                    st.session_state.show_intermediate = False; sync_to_url(); st.rerun()
    else:
        st.title(f"📍 {st.session_state.sub_step}지망 추첨 현황 ({target})")
        m1, m2 = st.columns([2, 1])
        with m1:
            fig = px.bar(x=["남은 정원", "지원자 수"], y=[res['rem'], res['comp']], 
                         color=["남은 정원", "지원자 수"], text=[res['rem'], res['comp']], 
                         color_discrete_map={"남은 정원":"#2ecc71", "지원자 수":"#e74c3c"})
            st.plotly_chart(fig, use_container_width=True)
        with m2:
            st.subheader(target)
            if res['rem'] == 0:
                st.error("정원 마감"); st.button("탈락 확인", on_click=lambda: st.session_state.update({"current_result":"FAIL", "show_intermediate":True}))
            elif res['comp'] > res['rem']:
                st.warning("경합 발생")
                st.button("🎯 합격 시나리오", on_click=lambda: st.session_state.update({"current_result":"PASS", "show_intermediate":True}))
                st.button("❌ 탈락 시나리오", on_click=lambda: st.session_state.update({"current_result":"FAIL", "show_intermediate":True}))
            else:
                st.success("안정권"); st.button("결과 확인 👉", on_click=lambda: st.session_state.update({"current_result":"PASS", "show_intermediate":True}))
            
            st.divider()
            if st.button("🔄 다시 추첨하기", use_container_width=True):
                if res_key in st.session_state.stage_results: del st.session_state.stage_results[res_key]
                st.rerun()

elif st.session_state.step == "RESULT":
    st.balloons(); st.title("🎊 최종 배정 결과")
    st.info(f"### 최종 배정 학교: **{st.session_state.my_assigned}**")
    st.table(pd.DataFrame(st.session_state.history_data))

st.divider()
if st.session_state.step == "CHOICE":
    b_cols = st.columns(3)
    if b_cols[0].button("⬅️ 뒤로가기", use_container_width=True):
        st.session_state.step = "SETTING"; sync_to_url(); st.rerun()
    if b_cols[1].button("🏠 처음으로", use_container_width=True):
        st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()
    if b_cols[2].button("💾 설정 저장", use_container_width=True):
        sync_to_url(); st.toast("✅ 주소창에 저장 완료!")
else:
    b_cols = st.columns(4)
    if st.session_state.step != "SETTING":
        if b_cols[0].button("⬅️ 뒤로가기", use_container_width=True):
            if st.session_state.step in ["STAGE1", "STAGE2"]:
                if st.session_state.show_intermediate: st.session_state.show_intermediate = False
                elif st.session_state.sub_step > 1:
                    st.session_state.sub_step -= 1
                    if st.session_state.history_data: st.session_state.history_data.pop()
                else:
                    if st.session_state.step == "STAGE2":
                        st.session_state.step = "STAGE1"; st.session_state.sub_step = 5
                        if st.session_state.history_data: st.session_state.history_data.pop()
                    else: st.session_state.step = "CHOICE"
            elif st.session_state.step == "RESULT": st.session_state.step = "STAGE1" 
            sync_to_url(); st.rerun()

    if b_cols[1].button("🏠 처음으로", use_container_width=True):
        st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()
    if b_cols[2].button("💾 설정 저장", use_container_width=True):
        sync_to_url(); st.toast("✅ 주소창에 저장 완료!")
    if b_cols[3].button("🚨 전체 초기화", use_container_width=True):
        st.query_params.clear(); st.session_state.clear(); st.rerun()