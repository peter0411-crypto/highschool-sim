# --- STEP 2: 지망 선택 및 순위 조정 (수정 버전) ---
elif st.session_state.step == "CHOICE":
    st.title(f"📋 2단계: {st.session_state.gender} 지망 순위 작성")
    st.info("💡 학교를 먼저 선택한 후, 아래 리스트에서 🔼🔽 버튼을 눌러 최종 순위를 결정하세요.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. 학군내 배정 (5개교)")
        # ms1_list라는 임시 변수를 사용해 위젯 값 관리
        temp_s1 = st.multiselect(
            "학교 선택", 
            DISPLAY_SCHOOLS, 
            default=st.session_state[f"c_{g_code}"]["s1"], 
            max_selections=5,
            key=f"ms1_widget_{g_code}" # 위젯 전용 키
        )
        # 위젯에서 선택된 값을 즉시 세션에 반영
        st.session_state[f"c_{g_code}"]["s1"] = temp_s1
        
        # 순서 조정 UI
        s1_list = st.session_state[f"c_{g_code}"]["s1"]
        for i, sch in enumerate(s1_list):
            r_cols = st.columns([3, 1, 1])
            r_cols[0].write(f"**{i+1}지망**: {sch}")
            if r_cols[1].button("🔼", key=f"u1_{sch}") and i > 0:
                s1_list[i], s1_list[i-1] = s1_list[i-1], s1_list[i]
                sync_to_url()
                st.rerun() # 변경 즉시 화면 다시 그리기
            if r_cols[2].button("🔽", key=f"d1_{sch}") and i < len(s1_list)-1:
                s1_list[i], s1_list[i+1] = s1_list[i+1], s1_list[i]
                sync_to_url()
                st.rerun()

    with c2:
        st.subheader("2. 구역내 배정 (전체)")
        max_n = 17 if g_code == "m" else 18
        temp_s2 = st.multiselect(
            f"학교 선택 ({max_n}개교)", 
            DISPLAY_SCHOOLS, 
            default=st.session_state[f"c_{g_code}"]["s2"], 
            max_selections=max_n,
            key=f"ms2_widget_{g_code}"
        )
        st.session_state[f"c_{g_code}"]["s2"] = temp_s2
        
        s2_list = st.session_state[f"c_{g_code}"]["s2"]
        with st.expander("구역내 지망 순위 상세 조정", expanded=True):
            for i, sch in enumerate(s2_list):
                r_cols = st.columns([3, 1, 1])
                r_cols[0].write(f"**{i+1}지망**: {sch}")
                if r_cols[1].button("🔼", key=f"u2_{sch}") and i > 0:
                    s2_list[i], s2_list[i-1] = s2_list[i-1], s2_list[i]
                    sync_to_url()
                    st.rerun()
                if r_cols[2].button("🔽", key=f"d2_{sch}") and i < len(s2_list)-1:
                    s2_list[i], s2_list[i+1] = s2_list[i+1], s2_list[i]
                    sync_to_url()
                    st.rerun()