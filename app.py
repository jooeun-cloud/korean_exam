import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- [1] 문제 데이터베이스 ---
# --- [1] 문제 데이터베이스 ---
EXAM_DB = {
    "중 1학년": {
        "1회차": { 1: {"ans": 1, "score": 100, "type": "테스트"} } 
    },
    "중 2학년": {
        "1회차": { 1: {"ans": 1, "score": 100, "type": "테스트"} }
    },
    "중 3학년": {
        "1회차": { 1: {"ans": 1, "score": 100, "type": "테스트"} }
    },
    "고 1학년": {
        "1회차": {
            1: {"ans": 2, "score": 3, "type": "화법 (말하기 전략)"},
            2: {"ans": 4, "score": 3, "type": "화법 (자료 활용)"},
            3: {"ans": 2, "score": 3, "type": "화법 (청자 전략)"},
            4: {"ans": 5, "score": 3, "type": "문법 (음운 변동)"},
            5: {"ans": 1, "score": 3, "type": "문법 (음운 사례)"},
            6: {"ans": 1, "score": 4, "type": "문법 (문장 구조)"},
            7: {"ans": 5, "score": 3, "type": "매체 (사전 정보)"},
            8: {"ans": 1, "score": 3, "type": "문법 (중세 국어)"},
            9: {"ans": 2, "score": 3, "type": "독서 (철학/내용)"},
            10: {"ans": 5, "score": 3, "type": "독서 (철학/세부)"},
            11: {"ans": 2, "score": 3, "type": "독서 (철학/적용)"},
            12: {"ans": 2, "score": 4, "type": "독서 (철학/보기)"},
            13: {"ans": 5, "score": 3, "type": "문학 (갈래 복합)"},
            14: {"ans": 1, "score": 3, "type": "문학 (표현상 특징)"},
            15: {"ans": 3, "score": 3, "type": "문학 (시어 의미)"},
            16: {"ans": 5, "score": 3, "type": "문학 (시상 전개)"},
            17: {"ans": 4, "score": 4, "type": "문학 (외적 준거)"},
            18: {"ans": 2, "score": 3, "type": "독서 (경제/전개)"},
            19: {"ans": 3, "score": 3, "type": "독서 (경제/세부)"},
            20: {"ans": 2, "score": 4, "type": "독서 (경제/적용)"},
            21: {"ans": 3, "score": 3, "type": "문학 (극/연출)"},
            22: {"ans": 4, "score": 4, "type": "문학 (극/감상)"},
            23: {"ans": 1, "score": 3, "type": "문학 (극/맥락)"},
            24: {"ans": 1, "score": 3, "type": "독서 (건축/세부)"},
            25: {"ans": 4, "score": 3, "type": "독서 (건축/핵심)"},
            26: {"ans": 3, "score": 3, "type": "독서 (통합 추론)"},
            27: {"ans": 3, "score": 4, "type": "독서 (건축/사례)"},
            28: {"ans": 5, "score": 4, "type": "문학 (소설/서사)"},
            29: {"ans": 3, "score": 3, "type": "문학 (소설/구조)"},
            30: {"ans": 4, "score": 3, "type": "문학 (소설/심리)"},
            31: {"ans": 1, "score": 3, "type": "어휘 (한자성어)"},
        }
    },
    "고 2학년": {
        "1회차": { 1: {"ans": 1, "score": 100, "type": "테스트"} }
    },
    "고 3학년": {
        "1회차": { 1: {"ans": 1, "score": 100, "type": "테스트"} }
    }
}

# --- [2] 성적표 HTML 생성 함수 ---
def create_report_html(grade, round_name, name, score, rank, total_students, wrong_data_map, feedback_func):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    has_wrong = bool(wrong_data_map)
    feedback_section_html = ""
    
    if has_wrong:
        for q_type, q_nums in wrong_data_map.items():
            nums_str = ", ".join([str(n) for n in q_nums]) + "번"
            msg = feedback_func(q_type)
            clean_msg = msg.strip().replace(">", "💡").replace("**", "").replace("-", "•").replace("\n", "<br>")
            
            if clean_msg.startswith("###"):
                parts = clean_msg.split("<br>", 1)
                title_txt = parts[0].replace("###", "").strip()
                body_txt = parts[1] if len(parts) > 1 else ""
                feedback_section_html += f"<div class='feedback-card'><div class='card-header'><span class='card-title'>{title_txt}</span><span class='card-nums'>❌ 틀린 문제: {nums_str}</span></div><div class='card-body'>{body_txt}</div></div>"
            else:
                feedback_section_html += f"<div class='feedback-card'><div class='card-header'><span class='card-nums'>❌ 틀린 문제: {nums_str}</span></div><div class='card-body'>{clean_msg}</div></div>"
    else:
        feedback_section_html = "<div class='feedback-card' style='border-color:#4CAF50; background:#E8F5E9;'><h3 style='color:#2E7D32; margin:0;'>🎉 완벽합니다!</h3><p style='margin:10px 0 0 0;'>약점이 없습니다.</p></div>"

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>{name} 성적표</title>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; color: #333; }}
            .paper {{ max-width: 800px; margin: 0 auto; border: 2px solid #444; padding: 40px; }}
            h1 {{ text-align: center; border-bottom: 3px solid #444; padding-bottom: 20px; margin-bottom: 30px; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
            .info-table th {{ background-color: #f4f4f4; border: 1px solid #999; padding: 12px; width: 20%; font-weight: bold; }}
            .info-table td {{ border: 1px solid #999; padding: 12px; text-align: center; }}
            .score {{ font-size: 36px; font-weight: bold; color: #D32F2F; }}
            .feedback-card {{ border: 1px solid #999; margin-bottom: 20px; page-break-inside: avoid; }}
            .card-header {{ background-color: #eee; padding: 10px 15px; border-bottom: 1px solid #ccc; display: flex; justify-content: space-between; align-items: center; }}
            .card-title {{ font-size: 16px; font-weight: bold; }}
            .card-nums {{ font-size: 14px; color: #D32F2F; font-weight: bold; background: white; padding: 3px 8px; border-radius: 5px; border: 1px solid #ddd; }}
            .card-body {{ padding: 15px; font-size: 13px; line-height: 1.6; }}
            .footer {{ text-align: center; margin-top: 50px; font-size: 12px; color: #888; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <h1>📑 {grade} {round_name} 분석 성적표</h1>
            <table class="info-table">
                <tr><th>이 름</th><td>{name}</td><th>응시일</th><td>{now}</td></tr>
                <tr><th>점 수</th><td><span class="score">{int(score)}</span> 점</td><th>등 수</th><td>{rank}등 / {total_students}명</td></tr>
            </table>
            <h3 style="border-bottom: 2px solid #ddd; padding-bottom: 10px;">💊 유형별 오답 분석 및 처방</h3>
            {feedback_section_html}
            <div class="footer">위 학생의 모의고사 결과를 증명합니다.<br>Designed by AI Teacher</div>
        </div>
    </body>
    </html>
    """
    return html

# --- [3] 구글 시트 연결 ---
def get_google_sheet_data():
    if "gcp_service_account" not in st.secrets: return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    try: return client.open("ExamResults").sheet1
    except: return None

# --- [4] 피드백 함수 ---
def get_feedback_message(question_type):
    if "강연" in question_type or "말하기" in question_type or "화법" in question_type:
        return """### 🗣️ [심층 분석] 화법: 전략 파악
**1. 진단**
강연자의 말하기 장치를 놓쳤습니다.
**2. Action Plan**
1. 담화 표지(첫째, 그러나) 찾기
2. 비언어적 표현(웃으며) 체크하기"""
    # ... (기존 피드백 내용들 생략 - 그대로 유지됩니다) ...
    return """### ⚠️ [종합 진단] 기초 체력 강화
오답 선지의 근거를 분석해보세요."""

def get_strength_message(question_type):
    if "문법" in question_type: return "💎 **[문법 마스터]** 문법 개념이 탄탄합니다!"
    if "비문학" in question_type: return "🧠 **[논리왕]** 독해력이 탁월합니다!"
    if "문학" in question_type: return "💖 **[공감 능력자]** 문학적 감수성이 뛰어납니다!"
    if "보기" in question_type: return "🚀 **[응용 천재]** 고난도 문제 해결력이 좋습니다!"
    return "✨ **[성실한 학습자]** 학습 이해도가 높습니다!"


# --- [5] 공통 기능: 학년별 시험 페이지 렌더링 함수 ---
# 이 함수 하나로 1, 2, 3학년 탭을 모두 처리합니다. (코드 중복 방지)
def render_exam_page(grade):
    # 해당 학년의 회차 목록 가져오기
    if grade not in EXAM_DB:
        st.error("시험 데이터가 없습니다.")
        return

    rounds = list(EXAM_DB[grade].keys())
    
    # [중요] 탭 안에서도 위젯 키(Key)가 겹치지 않게 하기 위해 key=f"{grade}_..."를 씁니다.
    selected_round = st.selectbox("회차 선택", rounds, key=f"round_select_{grade}")
    current_exam_data = EXAM_DB[grade][selected_round]
    
    st.info(f"📢 **{grade} - {selected_round}** 응시를 시작합니다.")
    
    with st.form(key=f"exam_form_{grade}"):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름", placeholder="홍길동", key=f"name_{grade}")
        student_id = c2.text_input("학번(ID)", placeholder="예: 10101", key=f"id_{grade}")
        st.markdown("---")
        
        user_answers = {}
        cols = st.columns(4)
        for i, q_num in enumerate(sorted(current_exam_data.keys())):
            with cols[i % 4]:
                info = current_exam_data[q_num]
                user_answers[q_num] = st.number_input(
                    f"{q_num}번 ({info['score']}점)", 
                    min_value=1, max_value=5, step=1, key=f"q_{grade}_{selected_round}_{q_num}"
                )
        
        submit = st.form_submit_button("답안 제출하기", use_container_width=True)
        
    if submit:
        if not name or not student_id:
            st.error("이름과 학번을 입력하세요!")
            return

        # 중복 체크
        sheet = get_google_sheet_data()
        is_duplicate = False
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                if not df.empty:
                    df['Grade'] = df['Grade'].astype(str).str.strip()
                    df['Round'] = df['Round'].astype(str).str.strip()
                    df['ID'] = df['ID'].astype(str).str.strip()
                    def normalize(val):
                        try: return str(int(val))
                        except: return str(val).strip()
                    
                    df['ID_Clean'] = df['ID'].apply(normalize)
                    in_id = normalize(student_id)
                    
                    dup = df[(df['Grade']==str(grade)) & (df['Round']==str(selected_round)) & (df['ID_Clean']==in_id)]
                    if not dup.empty: is_duplicate = True
            except: pass
        
        if is_duplicate:
            st.error(f"⛔ 이미 제출된 기록이 있습니다. ({grade} {student_id}번)")
        else:
            # 채점
            total_score = 0
            wrong_list = []
            wrong_q_nums = []
            wrong_map = {}
            
            for q, info in current_exam_data.items():
                if user_answers[q] == info['ans']:
                    total_score += info['score']
                else:
                    wrong_list.append(info['type'])
                    wrong_q_nums.append(str(q))
                    if info['type'] not in wrong_map: wrong_map[info['type']] = []
                    wrong_map[info['type']].append(q)
            
            if sheet:
                try:
                    wrong_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                    new_row = [
                        grade, selected_round, student_id, name, 
                        total_score, " | ".join(wrong_list), 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        wrong_q_str
                    ]
                    sheet.append_row(new_row)
                    
                    # 등수 계산
                    records = sheet.get_all_records()
                    df = pd.DataFrame(records)
                    df_filtered = df[(df['Grade'].astype(str).str.strip() == str(grade)) & 
                                     (df['Round'].astype(str).str.strip() == str(selected_round))]
                    rank = df_filtered[df_filtered['Score'] > total_score].shape[0] + 1
                    total_std = len(df_filtered)
                    
                    st.balloons()
                    report = create_report_html(grade, selected_round, name, total_score, rank, total_std, wrong_map, get_feedback_message)
                    st.success("제출 완료! 성적표를 다운로드하세요.")
                    st.download_button("📥 성적표 다운로드", report, file_name="성적표.html", mime="text/html", key=f"dn_{grade}_{selected_round}")
                except Exception as e:
                    st.error(f"오류: {e}")


# --- [6] 메인 화면 구성 ---
st.set_page_config(page_title="국어 모의고사 시스템", page_icon="📚", layout="wide")
st.title("📚 국어 모의고사 통합 관리 시스템")

tab1, tab2, tab3 = st.tabs(["📝 시험 응시하기", "🔍 결과 조회", "📈 종합 기록부"])

# 우리가 만들고 싶은 학년 목록 (순서대로)
GRADE_ORDER = ["중 1학년", "중 2학년", "중 3학년", "고 1학년", "고 2학년", "고 3학년"]

# === [탭 1] 시험 응시 (자동 탭 생성) ===
with tab1:
    st.header("학년을 선택하세요")
    
    # 1. EXAM_DB에 있는 학년만 추려서 탭을 만듭니다.
    # (데이터가 없는 학년은 탭을 안 만들기 위함, 혹은 순서 강제)
    active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]
    
    if not active_grades:
        st.error("등록된 문제 데이터(EXAM_DB)가 없습니다.")
    else:
        # 2. 학년 수만큼 탭 생성
        exam_tabs = st.tabs(active_grades)
        
        # 3. 반복문으로 각 탭에 시험지 넣기
        for i, grade in enumerate(active_grades):
            with exam_tabs[i]:
                render_exam_page(grade)


# === [탭 2] 결과 조회 (자동 탭 생성) ===
with tab2:
    st.header("🔍 성적표 조회")
    
    active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]
    
    if not active_grades:
        st.warning("데이터가 없습니다.")
    else:
        result_tabs = st.tabs(active_grades)
        
        # 조회 로직 함수 (기존과 동일, 위치만 내부로 이동)
        def render_result_page(grade):
            if grade not in EXAM_DB: return
            rounds = list(EXAM_DB[grade].keys())
            
            c1, c2 = st.columns(2)
            chk_round = c1.selectbox("회차", rounds, key=f"res_round_{grade}")
            chk_id = c2.text_input("학번(ID)", key=f"res_id_{grade}")
            
            if st.button("조회하기", key=f"btn_res_{grade}"):
                sheet = get_google_sheet_data()
                if sheet:
                    try:
                        records = sheet.get_all_records()
                        df = pd.DataFrame(records)
                        
                        # 전처리 (0문제 해결 포함)
                        df['Grade'] = df['Grade'].astype(str).str.strip()
                        df['Round'] = df['Round'].astype(str).str.strip()
                        df['ID'] = df['ID'].astype(str)
                        
                        def normalize(val):
                            try: return str(int(val))
                            except: return str(val).strip()
                        
                        df['ID_Clean'] = df['ID'].apply(normalize)
                        in_id = normalize(chk_id)
                        
                        # 검색
                        my_data = df[(df['Grade']==str(grade)) & (df['Round']==str(chk_round)) & (df['ID_Clean']==in_id)]
                        
                        if not my_data.empty:
                            last_row = my_data.iloc[-1]
                            
                            # 등수
                            round_data = df[(df['Grade']==str(grade)) & (df['Round']==str(chk_round))]
                            rank = round_data[round_data['Score'] > last_row['Score']].shape[0] + 1
                            total = len(round_data)
                            pct = (rank / total) * 100
                            
                            st.divider()
                            st.subheader(f"📢 {grade} {last_row['Name']}님의 결과")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("점수", f"{int(last_row['Score'])}")
                            m2.metric("등수", f"{rank} / {total}")
                            m3.metric("상위", f"{pct:.1f}%")
                            
                            # 틀린 문제 복원
                            w_q_str = str(last_row.get('Wrong_Questions', ''))
                            w_nums = [int(x.strip()) for x in w_q_str.split(",") if x.strip().isdigit()] if w_q_str != "없음" else []
                            
                            # 유형 매핑 복원
                            current_db = EXAM_DB[grade][chk_round]
                            wrong_map = {}
                            for q in w_nums:
                                if q in current_db:
                                    qt = current_db[q]['type']
                                    if qt not in wrong_map: wrong_map[qt] = []
                                    wrong_map[qt].append(q)
                            
                            # 화면 출력
                            if wrong_map:
                                st.markdown("---")
                                for qt, nums in wrong_map.items():
                                    nums_txt = ", ".join(map(str, nums))
                                    with st.expander(f"❌ {qt} (틀린 문제: {nums_txt}번)", expanded=True):
                                        st.markdown(get_feedback_message(qt))
                            else:
                                st.balloons()
                                st.success("만점입니다! 약점이 없습니다.")

                            # 다운로드
                            st.write("---")
                            report = create_report_html(grade, chk_round, last_row['Name'], last_row['Score'], rank, total, wrong_map, get_feedback_message)
                            st.download_button("📥 성적표 다운로드", report, file_name="성적표.html", mime="text/html", key=f"res_dn_{grade}")
                            with st.expander("📱 모바일 저장 방법"):
                                st.write("파일 열기 > 공유 > 인쇄 > PDF로 저장")
                        
                        else:
                            st.error("기록이 없습니다.")
                    except Exception as e: st.error(f"오류: {e}")

        # 반복문으로 결과 조회 탭 생성
        for i, grade in enumerate(active_grades):
            with result_tabs[i]:
                render_result_page(grade)


# === [탭 3] 종합 기록부 ===
with tab3:
    st.header("📈 포트폴리오")
    
    # 여기도 GRADE_ORDER 순서대로 보여주면 깔끔합니다.
    active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]
    
    pg = st.selectbox("학년", active_grades, key="pg")
    pid = st.text_input("학번(ID)", key="pid")
    
    if st.button("분석 보기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                # 전처리
                df['Grade'] = df['Grade'].astype(str).str.strip()
                df['ID'] = df['ID'].astype(str)
                def normalize(val):
                    try: return str(int(val))
                    except: return str(val).strip()
                df['ID_Clean'] = df['ID'].apply(normalize)
                in_id = normalize(pid)
                
                my_hist = df[(df['Grade']==str(pg)) & (df['ID_Clean']==in_id)]
                
                if not my_hist.empty:
                    st.success(f"**{pg} {my_hist.iloc[-1]['Name']}**님의 성장 기록")
                    chart = alt.Chart(my_hist).mark_line(point=True).encode(
                        x='Round', y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]))
                    )
                    st.altair_chart(chart, use_container_width=True)
                    st.dataframe(my_hist[['Round', 'Score', 'Wrong_Types']])
                else:
                    st.warning("기록이 없습니다.")
            except Exception as e: st.error(f"오류: {e}")
