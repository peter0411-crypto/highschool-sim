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
    
    # 학교별 마감 지망 설정값 로드
    for s in ALL_SCHOOLS:
        st.session_state[f"lim_m_{s}"] = int(params.get(f"m_{s}", 1))
        st.session_state[f"lim_f_{s}"] = int(params.get(f"f_{s}", 1))
    
    def parse_list(key):
        val = params.get(key, "")
        return [x for x in val.split(",") if x] if val else []

    # 지망 리스트 초기화
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

# --- 4. 메인 화면 로직 ---

# STEP 1: 설정
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

# STEP 2: 지망 선택 (2단계 분리 방식)
elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    
    # [1] 학교 풀 선택 (순서 무관)
    st.subheader("1. 지망할 학교들을 먼저 고르세요")
    pool_key = f"pool_{g_code}"
    if pool_key not in st.session_state:
        st.session_state[pool_key] = curr_choices["s1"]
        
    selected_pool = st.multiselect(
        "학교 바구니에 담기 (학군내 5개 필수)",
        DISPLAY_SCHOOLS,
        default=st.session_state[pool_key],
        key=f"widget_pool_{g_code}"
    )
    st.session_state[pool_key] = selected_pool
    
    st.divider()

    # [2] 선택된 학교 내에서 순서 배정
    if len(selected_pool) >= 5:
        st.subheader("2. 최종 지망 순위 결정 (1~5지망)")
        final_s1 = []
        available_options = list(selected_pool)
        
        cols = st.columns(5)
        for i in range(5):
            # 이전에 선택했던 값이 유효하면 기본값으로 유지
            prev_val = curr_choices["s1"][i] if len(curr_choices["s1"]) > i and curr_choices["s1"][i] in available_options else None
            
            choice = cols[i].selectbox(
                f"{i+1}지망",
                options=["선택하세요"] + available_options,
                index=available_options.index(prev_val) + 1 if prev_val else 0,
                key=f"sb_s1_{i}_{g_code}"
            )
            if choice != "선택하세요":
                final_s1.append(choice)
                available_options.remove(choice) # 중복 선택 방지
        
        curr_choices["s1"] = final_s1
        
        # 구역내 배정(s2)은 편의상 전체 리스트로 자동 채움 (필요시 s1과 동일 로직 추가 가능)
        curr_choices["s2"] = DISPLAY_SCHOOLS 

        if len(final_s1) == 5:
            st.success(f"✅ 확정된 순서: {' > '.join(final_s1)}")
            if st.button("🚀 시뮬레이션 시작", use_container_width=True, type="primary"):
                st.session_state.step = "STAGE1"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()
        else:
            st.info("5지망까지 모두 다른 학교로 지정해 주세요.")
    else:
        st.warning("위의 드롭다운에서 학교를 5개 이상 선택해야 지망 순위를 정할 수 있습니다.")

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
            reason = "추첨 경합"
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
                    st.session_state.my_assigned = target
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "합격"})
                    st.session_state.step = "RESULT"; st.session_state.show_intermediate = False; sync_to_url(); st.rerun()
            else:
                st.error(f"### ❌ **{target}** 탈락")
                if st.button("다음 지망으로 이동 ➡️", use_container_width=True, type="primary"):
                    st.session_state.history_data.append({"지망": f"{st.session_state.sub_step}지망", "학교": target, "결과": "탈락"})
                    st.session_state.remaining_quota = max(0, st.session_state.remaining_quota - res['others_taken'])
                    if is_s1 and st.session_state.sub_step == 5:
                        st.session_state.step = "STAGE2"; st.session_state.sub_step = 1; st.session_state.remaining_quota = 45
                    else:
                        st.session_state.sub_step += 1
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
            if st.button("🔄 다시 추첨하기", use_container_width=True):
                st.session_state.stage_results[res_key] = calculate_draw(); st.rerun()

# STEP 4: 최종 결과
elif st.session_state.step == "RESULT":
    st.balloons(); st.title("🎊 최종 배정 결과")
    st.info(f"### 최종 배정 학교: **{st.session_state.my_assigned}**")
    st.table(pd.DataFrame(st.session_state.history_data))

# --- 5. 공통 하단 컨트롤 바 ---
st.divider()
b_cols = st.columns(4)
if st.session_state.step != "SETTING":
    if b_cols[0].button("⬅️ 뒤로가기", use_container_width=True):
        if st.session_state.step == "CHOICE": st.session_state.step = "SETTING"
        elif st.session_state.step in ["STAGE1", "STAGE2"]: st.session_state.step = "CHOICE"
        else: st.session_state.step = "CHOICE"
        sync_to_url(); st.rerun()

if b_cols[1].button("🏠 처음으로", use_container_width=True):
    st.session_state.step = "SETTING"; st.session_state.sub_step = 1; st.session_state.history_data = []; sync_to_url(); st.rerun()

if b_cols[2].button("💾 현재 설정 저장", use_container_width=True):
    sync_to_url(); st.toast("✅ 주소창에 현재 데이터가 저장되었습니다! (북마크 가능)")

if b_cols[3].button("🚨 전체 초기화", use_container_width=True):
    st.query_params.clear(); st.session_state.clear(); st.rerun()