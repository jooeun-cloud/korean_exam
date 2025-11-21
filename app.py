import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- [0] 앱 설정 ---
st.set_page_config(page_title="국어 모의고사 통합 시스템", page_icon="📚", layout="wide")
ADMIN_PASSWORD = "1234" 

with st.sidebar:
    st.header("🔐 관리자 로그인")
    input_pw = st.text_input("비밀번호", type="password")
    if input_pw == ADMIN_PASSWORD:
        st.session_state['is_admin'] = True
        st.success("관리자 모드 ON ✅")
        st.markdown("---")
        if st.button("🔄 문제 DB 새로고침"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.session_state['is_admin'] = False

is_admin = st.session_state.get('is_admin', False)

# --- [1] 데이터베이스 (구글 시트 '정답_학년' 탭 연동) ---
GRADE_ORDER = ["중 1학년", "중 2학년", "중 3학년", "고 1학년", "고 2학년", "고 3학년"]

@st.cache_data(ttl=600)
def load_exam_db():
    if "gcp_service_account" not in st.secrets: return {}
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    
    db = {}
    for grade in GRADE_ORDER:
        try:
            sheet_name = f"정답_{grade}"
            sheet = client.open("ExamResults").worksheet(sheet_name)
            records = sheet.get_all_records()
            
            if grade not in db: db[grade] = {}
            
            for row in records:
                round_name = str(row['Round']).strip()
                q_num = int(row['Q_Num'])
                
                if round_name not in db[grade]: db[grade][round_name] = {}
                
                db[grade][round_name][q_num] = {
                    "ans": int(row['Answer']),
                    "score": int(row['Score']),
                    "type": str(row['Type']).strip()
                }
        except gspread.WorksheetNotFound: continue
        except Exception as e: st.error(f"'{grade}' 정답 로딩 오류: {e}")
            
    return db

EXAM_DB = load_exam_db()

# --- [2] 성적표 HTML 생성 함수 ---
def create_report_html(grade, round_name, name, score, rank, total_students, wrong_data_map, feedback_func):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    has_wrong = bool(wrong_data_map)
    feedback_section_html = ""
    
    if has_wrong:
        for title, q_nums in wrong_data_map.items():
            nums_str = ", ".join([str(n) for n in q_nums]) + "번"
            
            # title이 이미 피드백 제목이거나 유형이므로, 이를 통해 메시지를 가져오거나(람다) 직접 씀
            msg = feedback_func(title)
            
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

    return f"""
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

# --- [3] 구글 시트 연결 (학생 답안용: 첫번째 시트 고정) ---
def get_student_sheet():
    if "gcp_service_account" not in st.secrets: return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    try:
        # [핵심] 무조건 첫 번째 시트(Sheet1)를 엽니다.
        return client.open("ExamResults").sheet1
    except Exception as e:
        st.error(f"시트 연결 오류: {e}")
        return None

# --- [4] 피드백 함수 ---
def get_feedback_message_list(question_type):
    messages = []
    if "문법" in question_type or "문장" in question_type:
        if "음운" not in question_type and "사전" not in question_type and "중세" not in question_type:
            messages.append("""### 🏗️ [심층 분석] 문법: 문장의 '뼈대' 찾기
**1. 진단**
문장 성분 분석과 조사의 쓰임을 놓쳤을 가능성이 큽니다.
**2. Action Plan**
1. 서술어(동사/형용사)에 밑줄을 그으세요.
2. 필수 성분(주어, 목적어, 보어)이 빠지지 않았는지 확인하세요.""")

    if "사전" in question_type:
        messages.append("""### 📖 [심층 분석] 문법: 사전 정보 해석
**1. 진단**
사전에 제시된 품사 기호와 문형 정보를 해석하지 못했습니다.
**2. Action Plan**
1. 품사 기호(동사/형용사)를 먼저 확인하세요.
2. 뜻풀이 예문과 문제의 <보기> 예문을 비교하세요.""")

    if "음운" in question_type:
        messages.append("""### 🛑 [긴급 처방] 문법: 음운 변동
**1. 진단**
교체, 탈락, 첨가, 축약의 조건을 모릅니다.
**2. Action Plan**
1. 변동 조건을 백지에 써보세요.
2. 발음 과정을 기호로 분석하세요.""")

    if "철학" in question_type or "인문" in question_type:
        messages.append("""### 🧠 [심층 분석] 인문/철학: 관점 비교
**1. 진단**
사상가(A vs B)의 관점 차이나 용어 정의를 놓쳤습니다.
**2. Action Plan**
1. 학자별 공통점/차이점을 표로 정리하세요.""")

    if "경제" in question_type or "사회" in question_type or ("법" in question_type and "문법" not in question_type and "화법" not in question_type):
        messages.append("""### 📈 [심층 분석] 사회/경제: 인과 관계
**1. 진단**
변수의 비례/반비례 관계를 놓쳤습니다.
**2. Action Plan**
1. 화살표 메모(`금리↑ → 투자↓`)를 하세요.""")

    if "과학" in question_type or "기술" in question_type:
        messages.append("""### ⚙️ [심층 분석] 과학/기술: 작동 원리
**1. 진단**
장치의 구조와 작동 순서가 꼬였습니다.
**2. Action Plan**
1. 구조도를 간단히 그리세요.""")

    if "소설" in question_type or "서사" in question_type:
        messages.append("""### 🎭 [심층 분석] 문학(산문): 갈등 파악
**1. 진단**
인물 간의 갈등 관계를 놓쳤습니다.
**2. Action Plan**
1. 인물 관계도를 그리세요.""")

    if ("시가" in question_type or "시어" in question_type) and "비문학" not in question_type:
        messages.append("""### 🌙 [심층 분석] 문학(운문): 상황/정서
**1. 진단**
주관적 감상에 빠졌습니다.
**2. Action Plan**
1. 긍정(+), 부정(-) 시어를 구분하세요.""")

    if "화법" in question_type or "강연" in question_type:
        messages.append("""### 🗣️ [심층 분석] 화법: 말하기 전략
**1. 진단**
'어떻게' 전달했는지를 놓쳤습니다.
**2. Action Plan**
1. 담화 표지어(첫째, 그러나)를 찾으세요.""")
        
    if "매체" in question_type:
        messages.append("""### 🖥️ [심층 분석] 매체: 소통 방식
**1. 진단**
매체별 특징(쌍방향성 등)을 놓쳤습니다.
**2. Action Plan**
1. 댓글, 하이퍼링크 등 기능에 주목하세요.""")

    if "보기" in question_type or "적용" in question_type:
        messages.append("""### 🔥 [고난도 꿀팁] 보기 적용
**1. 진단**
지문 원리와 보기 사례 연결 실패.
**2. Action Plan**
1. 보기 사례를 지문 용어로 치환하세요.""")

    if not messages:
        messages.append("""### ⚠️ [종합 진단] 기초 독해력
**1. 진단**
어휘력 부족 또는 실수일 수 있습니다.
**2. Action Plan**
1. 오답 근거를 스스로 찾아보세요.""")
    
    return messages

def get_strength_message(question_type):
    if "문법" in question_type: return "💎 **[문법 마스터]** 문법 개념이 탄탄합니다!"
    if "비문학" in question_type: return "🧠 **[논리왕]** 독해력이 탁월합니다!"
    if "문학" in question_type: return "💖 **[공감 능력자]** 문학적 감수성이 뛰어납니다!"
    return "✨ **[성실한 학습자]** 학습 이해도가 높습니다!"


# --- [5] 메인 화면 ---
tab1, tab2, tab3 = st.tabs(["📝 시험 응시하기", "🔍 결과 조회", "📈 종합 기록부"])
active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]

# =====================================================================
# [탭 1] 시험 응시 (점수만 공개)
# =====================================================================
with tab1:
    st.header("학년을 선택하세요")
    if not active_grades:
        st.error("데이터 없음 (AnswerKey 탭 확인)")
    else:
        exam_tabs = st.tabs(active_grades)
        for i, grade in enumerate(active_grades):
            with exam_tabs[i]:
                rounds = list(EXAM_DB[grade].keys())
                selected_round = st.selectbox("회차 선택", rounds, key=f"ex_rd_{grade}")
                current_exam_data = EXAM_DB[grade][selected_round]
                
                st.info(f"📢 **{grade} - {selected_round}** 응시를 시작합니다.")
                
                with st.form(key=f"f_{grade}_{selected_round}"):
                    c1,c2 = st.columns(2)
                    nm = st.text_input("이름", key=f"n_{grade}")
                    sid = st.text_input("학번", key=f"i_{grade}")
                    st.markdown("---")
                    
                    user_answers = {}
                    s_keys = sorted(current_exam_data.keys())
                    for idx in range(0, len(s_keys), 2):
                        cols = st.columns(2)
                        q1 = s_keys[idx]
                        info1 = current_exam_data[q1]
                        with cols[0]:
                            st.markdown(f"**{q1}번** <small>({info1['score']}점)</small>", unsafe_allow_html=True)
                            user_answers[q1] = st.radio(f"q{q1}", [1,2,3,4,5], horizontal=True, label_visibility="collapsed", index=None, key=f"q_{grade}_{selected_round}_{q1}")
                            st.write("")
                        if idx+1 < len(s_keys):
                            q2 = s_keys[idx+1]
                            info2 = current_exam_data[q2]
                            with cols[1]:
                                st.markdown(f"**{q2}번** <small>({info2['score']}점)</small>", unsafe_allow_html=True)
                                user_answers[q2] = st.radio(f"q{q2}", [1,2,3,4,5], horizontal=True, label_visibility="collapsed", index=None, key=f"q_{grade}_{selected_round}_{q2}")
                                st.write("")
                    submit = st.form_submit_button("답안 제출하기", use_container_width=True)
                
                if submit:
                    if not nm or not sid:
                        st.error("이름과 학번을 입력하세요!")
                    else:
                        # [수정] 통합 시트(Sheet1) 사용
                        sheet = get_student_sheet()
                        is_dup = False
                        if sheet:
                            try:
                                recs = sheet.get_all_records()
                                df = pd.DataFrame(recs)
                                if not df.empty:
                                    df['Grade'] = df['Grade'].astype(str).str.strip()
                                    df['Round'] = df['Round'].astype(str).str.strip()
                                    df['ID'] = df['ID'].astype(str).str.strip()
                                    def norm(v):
                                        try: return str(int(v))
                                        except: return str(v).strip()
                                    df['ID_Clean'] = df['ID'].apply(norm)
                                    in_id = norm(sid)
                                    dup = df[(df['Grade']==str(grade))&(df['Round']==str(selected_round))&(df['ID_Clean']==in_id)]
                                    if not dup.empty: is_dup = True
                            except: pass
                        
                        if is_dup:
                            st.error("⛔ 이미 제출된 기록이 있습니다.")
                        else:
                            total_score = 0
                            wrong_list = []
                            wrong_q_nums = []
                            
                            for q, info in current_exam_data.items():
                                ua = user_answers.get(q, 0)
                                if ua == info['ans']:
                                    total_score += info['score']
                                else:
                                    wrong_list.append(info['type'])
                                    wrong_q_nums.append(str(q))
                            
                            if sheet:
                                try:
                                    w_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                                    new_row = [grade, selected_round, sid, nm, total_score, " | ".join(wrong_list), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), w_q_str]
                                    sheet.append_row(new_row)
                                    
                                    st.balloons()
                                    st.success(f"✅ {nm}님, 제출 완료!")
                                    st.markdown(f"<div style='text-align:center; border:2px solid #4CAF50; padding:20px; border-radius:10px; background:#E8F5E9; margin-top:20px;'><h3 style='margin:0;'>내 점수</h3><h1 style='color:#D32F2F; font-size:60px; margin:10px 0;'>{int(total_score)}점</h1></div>", unsafe_allow_html=True)
                                    st.info("👉 상세 결과는 **[결과 조회]** 탭에서 확인하세요.")
                                except Exception as e: st.error(f"저장 오류: {e}")

# =====================================================================
# [탭 2] 결과 조회
# =====================================================================
with tab2:
    st.header("🔍 성적표 조회")
    if active_grades:
        res_tabs = st.tabs(active_grades)
        
        def render_res(grade):
            rounds = list(EXAM_DB[grade].keys())
            c1,c2 = st.columns(2)
            chk_rd = c1.selectbox("회차", rounds, key=f"r_{grade}")
            chk_id = c2.text_input("학번", key=f"i_{grade}")
            
            if st.button("조회", key=f"b_{grade}"):
                sheet = get_student_sheet()
                if sheet:
                    try:
                        recs = sheet.get_all_records()
                        df = pd.DataFrame(recs)
                        df['Grade'] = df['Grade'].astype(str).str.strip()
                        df['Round'] = df['Round'].astype(str).str.strip()
                        df['ID'] = df['ID'].astype(str)
                        def norm(v):
                            try: return str(int(v))
                            except: return str(v).strip()
                        df['ID_Clean'] = df['ID'].apply(norm)
                        in_id = norm(chk_id)
                        
                        my_data = df[(df['Grade']==str(grade))&(df['Round']==str(chk_rd))&(df['ID_Clean']==in_id)]
                        
                        if not my_data.empty:
                            last_row = my_data.iloc[-1]
                            
                            r_data = df[(df['Grade']==str(grade)) & (df['Round']==str(chk_rd))]
                            rank = r_data[r_data['Score'] > last_row['Score']].shape[0] + 1
                            total = len(r_data)
                            pct = (rank / total) * 100
                            
                            st.divider()
                            st.subheader(f"📢 {grade} {last_row['Name']}님의 결과")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("점수", f"{int(last_row['Score'])}")
                            m2.metric("등수", f"{rank} / {total}")
                            m3.metric("상위", f"{pct:.1f}%")
                            
                            w_q_str = str(last_row.get('Wrong_Questions', ''))
                            w_nums = [int(x.strip()) for x in w_q_str.split(",") if x.strip().isdigit()] if w_q_str != "없음" else []
                            
                            st.markdown("---")
                            if w_nums: st.error(f"❌ **틀린 문제:** {w_q_str}번")
                            else: st.success("만점입니다!")
                            
                            # 관리자
                            if is_admin:
                                st.info("🔒 상세 분석")
                                feedback_group = {}
                                curr_db = EXAM_DB[grade][chk_rd]
                                
                                for q in w_nums:
                                    if q in curr_db:
                                        qt = curr_db[q]['type']
                                        msgs = get_feedback_message_list(qt)
                                        for msg in msgs:
                                            if msg not in feedback_group: feedback_group[msg] = []
                                            if q not in feedback_group[msg]: feedback_group[msg].append(q)
                                
                                if feedback_group:
                                    st.write("### 💡 유형별 피드백")
                                    for msg, nums in feedback_group.items():
                                        nums.sort()
                                        n_txt = ", ".join(map(str, nums))
                                        title = msg.strip().split('\n')[0].replace("###", "").strip() if "###" in msg else "상세 피드백"
                                        with st.expander(f"❌ **{title}** (틀린 문제: {n_txt}번)", expanded=True):
                                            st.markdown(msg)
                                
                                report_map = {}
                                title_to_msg = {}
                                for msg, nums in feedback_group.items():
                                    t = msg.strip().split('\n')[0].replace("###", "").strip() if "###" in msg else "기타"
                                    report_map[t] = nums
                                    title_to_msg[t] = msg
                                
                                st.markdown("---")
                                st.write("### 💾 저장")
                                rpt = create_report_html(grade, chk_rd, last_row['Name'], last_row['Score'], rank, total, report_map, lambda x: title_to_msg.get(x,""))
                                st.download_button("📥 다운로드", rpt, file_name="report.html", mime="text/html", key=f"d_{grade}_{chk_id}")
                            else:
                                st.warning("🔒 선생님만 볼 수 있습니다.")
                        else: st.error("기록 없음")
                    except Exception as e: st.error(f"오류: {e}")
        
        for i, g in enumerate(active_grades):
            with res_tabs[i]: render_res(g)

# [탭 3] 종합 기록부
with tab3:
    st.header("📈 포트폴리오")
    if not is_admin:
        st.error("⛔ 접근 권한 없음")
    else:
        c1, c2 = st.columns(2)
        pg = c1.selectbox("학년", active_grades, key="pg")
        pid = c2.text_input("학번(ID)", key="pid")
        
        if st.button("분석 보기", key="btn_port"):
            sheet = get_student_sheet()
            if sheet:
                try:
                    recs = sheet.get_all_records()
                    df = pd.DataFrame(recs)
                    df['Grade'] = df['Grade'].astype(str).str.strip()
                    df['ID'] = df['ID'].astype(str)
                    def norm(v):
                        try: return str(int(v))
                        except: return str(v).strip()
                    df['ID_Clean'] = df['ID'].apply(norm)
                    in_id = norm(pid)
                    
                    my_hist = df[(df['Grade']==str(pg)) & (df['ID_Clean']==in_id)]
                    
                    if not my_hist.empty:
                        sname = my_hist.iloc[-1]['Name']
                        st.success(f"**{pg} {sname}**님의 성장 기록")
                        chart = alt.Chart(my_hist).mark_line(point=True).encode(x='Round', y='Score')
                        st.altair_chart(chart, use_container_width=True)
                        
                        st.markdown("---")
                        st.write("### 2️⃣ 누적 취약점 분석 (TOP 3)")
                        all_w = []
                        for i, r in my_hist.iterrows():
                            if str(r['Wrong_Types']).strip(): all_w.extend(str(r['Wrong_Types']).split(" | "))
                        
                        if all_w:
                            from collections import Counter
                            cnt = Counter(all_w).most_common()
                            c_l, c_r = st.columns([1, 1.5])
                            with c_l:
                                st.write("📉 **많이 틀린 유형**")
                                for i, (t, c) in enumerate(cnt[:3]):
                                    st.write(f"{i+1}위: **{t}** ({c}회)")
                            with c_r:
                                st.info("💡 **맞춤 처방**")
                                seen = set()
                                shown = 0
                                for i, (t, c) in enumerate(cnt):
                                    if shown >= 3: break
                                    msgs = get_feedback_message_list(t)
                                    full = "\n\n---\n\n".join(msgs)
                                    if full not in seen:
                                        with st.expander(f"{t} 처방전", expanded=(shown==0)):
                                            st.markdown(full)
                                        seen.add(full)
                                        shown += 1
                        st.dataframe(my_hist[['Round', 'Score', 'Wrong_Types']])
                    else: st.warning("기록 없음")
                except Exception as e: st.error(f"오류: {e}")
