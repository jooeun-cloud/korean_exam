import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --------------------------------------------------
# [0] 기본 설정
# --------------------------------------------------
st.set_page_config(page_title="국어 모의고사 통합 시스템", page_icon="📚", layout="wide")

GRADE_ORDER = ["중 1학년", "중 2학년", "중 3학년", "고 1학년", "고 2학년", "고 3학년"]

# --------------------------------------------------
# [1] 관리자 계정 불러오기
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_admins():
    if "gcp_service_account" not in st.secrets:
        return {}

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["gcp_service_account"]), scope
    )
    client = gspread.authorize(creds)

    admins = {}
    try:
        sheet = client.open("ExamResults").worksheet("Admins")
        records = sheet.get_all_records()

        for row in records:
            admin_id = str(row.get("AdminID", "")).strip()
            if not admin_id:
                continue

            admins[admin_id] = {
                "password": str(row.get("Password", "")).strip(),
                "role": str(row.get("Role", "admin")).strip().lower()  # admin / superadmin
            }
    except Exception as e:
        st.error(f"관리자 시트 로딩 오류: {e}")

    return admins


ADMINS = load_admins()

# --------------------------------------------------
# [2] 로그인 처리
# --------------------------------------------------
with st.sidebar:
    st.header("🔐 관리자 로그인")

    if "is_authenticated" not in st.session_state:
        st.session_state["is_authenticated"] = False
        st.session_state["admin_id"] = None
        st.session_state["is_superadmin"] = False

    if not st.session_state["is_authenticated"]:
        admin_id_input = st.text_input("관리자 ID")
        pw_input = st.text_input("비밀번호", type="password")

        if st.button("로그인"):
            admin_info = ADMINS.get(admin_id_input)

            if admin_info and pw_input == admin_info["password"]:
                st.session_state["is_authenticated"] = True
                st.session_state["admin_id"] = admin_id_input
                st.session_state["is_superadmin"] = (admin_info["role"] == "superadmin")

                st.success(f"✅ {admin_id_input} 로그인 성공")
                st.experimental_rerun()
            else:
                st.error("❌ ID 또는 비밀번호가 올바르지 않습니다.")

    else:
        role_label = "최종관리자" if st.session_state["is_superadmin"] else "일반 관리자"
        st.success(f"접속 계정: {st.session_state['admin_id']}")
        st.caption(f"권한 : {role_label}")

        st.markdown("---")
        if st.button("🔄 문제 DB 새로고침"):
            st.cache_data.clear()
            st.rerun()

        if st.button("로그아웃"):
            for k in ["is_authenticated", "admin_id", "is_superadmin"]:
                st.session_state.pop(k, None)
            st.rerun()


# 로그인 안 되어 있으면 앱 중단
if not st.session_state.get("is_authenticated", False):
    st.warning("이 시스템은 관리자 전용입니다. 왼쪽에서 로그인해 주세요.")
    st.stop()

current_admin = st.session_state.get("admin_id")
is_superadmin = st.session_state.get("is_superadmin", False)
is_admin = True


# --------------------------------------------------
# [3] 정답 DB 로드
# --------------------------------------------------
@st.cache_data(ttl=600)
def load_exam_db():
    if "gcp_service_account" not in st.secrets:
        return {}

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)

    db = {}

    for grade in GRADE_ORDER:
        try:
            sheet_name = f"정답_{grade}"
            sheet = client.open("ExamResults").worksheet(sheet_name)
            records = sheet.get_all_records()

            if grade not in db:
                db[grade] = {}

            for row in records:
                round_name = str(row['Round']).strip()
                q_num = int(row['Q_Num'])

                if round_name not in db[grade]:
                    db[grade][round_name] = {}

                db[grade][round_name][q_num] = {
                    "ans": int(row['Answer']),
                    "score": int(row['Score']),
                    "type": str(row['Type']).strip()
                }

        except gspread.WorksheetNotFound:
            continue
        except Exception as e:
            st.error(f"'{grade}' 정답 로딩 오류: {e}")

    return db


EXAM_DB = load_exam_db()

# --------------------------------------------------
# [4] 학생 시트 (Sheet1)
# --------------------------------------------------
def get_student_sheet():
    if "gcp_service_account" not in st.secrets:
        return None

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)

    try:
        return client.open("ExamResults").sheet1
    except Exception as e:
        st.error(f"시트 연결 오류: {e}")
        return None

# --------------------------------------------------
# [5] 피드백 함수
# --------------------------------------------------
def get_feedback_message_list(question_type):
    messages = []

    if "문법" in question_type or "문장" in question_type:
        if "음운" not in question_type and "사전" not in question_type and "중세" not in question_type:
            messages.append("""### 🏗️ 문법: 문장의 '뼈대' 찾기
문장 성분 분석과 조사의 쓰임을 놓쳤습니다.
→ 서술어 확인 → 필수 성분(주어·목적어·보어) 점검""")

    if "사전" in question_type:
        messages.append("""### 📖 문법: 사전 정보
품사 / 문형 / 예문 연결이 부족합니다.
→ 품사 먼저 체크 후 예문 비교""")

    if "음운" in question_type:
        messages.append("""### 🛑 문법: 음운 변동
‘유형’보다 ‘환경’을 먼저 봐야 합니다.
→ 받침+자음 / 받침+모음 / ㄷ·ㅌ+이 구조 먼저 확인""")

    if "철학" in question_type or "인문" in question_type:
        messages.append("""### 🧠 인문/철학
사상가별 기준과 용어가 섞였습니다.
→ 공통점/차이점 표로 정리 + 키워드 한 줄 요약""")

    if "경제" in question_type or "사회" in question_type:
        messages.append("""### 📈 사회/경제
원인 → 과정 → 결과 흐름을 못 봤습니다.
→ 금리↑ → 소비↓ → 경기↓ 처럼 화살표 정리""")

    if "소설" in question_type or "서사" in question_type:
        messages.append("""### 🎭 문학(산문)
갈등 지점을 못 잡았습니다.
→ 인물관계도 + 말/행동 변화 표시""")

    if "시가" in question_type:
        messages.append("""### 🌙 문학(운문)
감정어가 아니라 ‘관계/상황’을 봐야 합니다.
→ 화자-대상-상황 한 문장 정리""")

    if "화법" in question_type:
        messages.append("""### 🗣️ 화법
전달 ‘방식/전략’을 못 봤습니다.
→ 강조/비교/질문/예시 표시""")

    if "매체" in question_type:
        messages.append("""### 🖥️ 매체
기능과 효과 연결이 부족했습니다.
→ 댓글/링크/그래프 = 어떤 효과?""")

    if "보기" in question_type:
        messages.append("""### 🔥 보기 적용
지문 개념 → 보기 상황 번역 실패
→ 보기 단어를 지문 용어로 치환""")

    if not messages:
        messages.append("### ⚠️ 기초 독해력 → 근거부터 재확인")

    return messages


# --------------------------------------------------
# [6] 탭 구성
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📝 시험 응시", "🔍 성적 조회", "📈 포트폴리오"])
active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]


# ==================================================
# [탭 1] 시험 응시
# ==================================================
with tab1:
    st.header("시험 응시")

    if not active_grades:
        st.error("데이터가 없습니다.")
    else:
        exam_tabs = st.tabs(active_grades)

        for i, grade in enumerate(active_grades):
            with exam_tabs[i]:
                rounds = list(EXAM_DB[grade].keys())
                selected_round = st.selectbox("회차", rounds, key=f"ex_r_{grade}")
                current_exam_data = EXAM_DB[grade][selected_round]

                with st.form(f"form_{grade}_{selected_round}"):

                    nm = st.text_input("이름")
                    sid = st.text_input("학번")

                    user_answers = {}
                    for q, info in current_exam_data.items():
                        user_answers[q] = st.radio(
                            f"{q}번 ({info['score']}점)",
                            [1,2,3,4,5],
                            horizontal=True,
                            index=None
                        )

                    submit = st.form_submit_button("제출")

                if submit:
                    sheet = get_student_sheet()
                    if not sheet:
                        st.error("시트 연결 실패")
                        continue

                    total_score = 0
                    wrong_list = []
                    wrong_q = []

                    for q, info in current_exam_data.items():
                        if user_answers.get(q) == info['ans']:
                            total_score += info['score']
                        else:
                            wrong_list.append(info['type'])
                            wrong_q.append(str(q))

                    w_q_str = ", ".join(wrong_q) if wrong_q else "없음"

                    # ✅ 관리자 정보 같이 저장
                    new_row = [
                        grade,
                        selected_round,
                        sid,
                        nm,
                        total_score,
                        " | ".join(wrong_list),
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        w_q_str,
                        current_admin
                    ]

                    sheet.append_row(new_row)

                    st.success(f"{nm}점수: {total_score}점 저장 완료!")


# ==================================================
# [탭 2] 성적 조회
# ==================================================
with tab2:
    st.header("성적 조회")

    res_tabs = st.tabs(active_grades)

    def render_result(grade):
        rounds = list(EXAM_DB[grade].keys())
        r = st.selectbox("회차", rounds, key=f"res_r_{grade}")
        sid = st.text_input("학번", key=f"res_id_{grade}")

        if st.button("조회", key=f"btn_{grade}"):

            sheet = get_student_sheet()
            if not sheet:
                st.error("시트 오류")
                return

            df = pd.DataFrame(sheet.get_all_records())
            df["AdminID"] = df.get("AdminID", "").astype(str)

            if not is_superadmin:
                df = df[df["AdminID"] == current_admin]

            df["ID"] = df["ID"].astype(str).str.strip()
            df["Round"] = df["Round"].astype(str).str.strip()

            res = df[(df["Grade"]==grade) & (df["Round"]==r) & (df["ID"]==sid)]

            if res.empty:
                st.warning("기록 없음")
                return

            last = res.iloc[-1]
            st.success(f"{last['Name']} - {last['Score']}점")
            st.write(f"틀린 문제: {last['Wrong_Questions']}")

    for i, g in enumerate(active_grades):
        with res_tabs[i]:
            render_result(g)


# ==================================================
# [탭 3] 포트폴리오
# ==================================================
with tab3:
    st.header("포트폴리오")

    pg = st.selectbox("학년", active_grades)
    pid = st.text_input("학번")

    if st.button("분석"):

        sheet = get_student_sheet()
        if not sheet:
            st.error("시트 오류")
            st.stop()

        df = pd.DataFrame(sheet.get_all_records())

        df["AdminID"] = df.get("AdminID", "").astype(str)

        if not is_superadmin:
            df = df[df["AdminID"] == current_admin]

        df["ID"] = df["ID"].astype(str).str.strip()
        df["Grade"] = df["Grade"].astype(str).str.strip()

        my_hist = df[(df["Grade"]==pg) & (df["ID"]==pid)]

        if my_hist.empty:
            st.warning("기록 없음")
            st.stop()

        name = my_hist.iloc[-1]["Name"]

        st.success(f"{name} 성장 기록")

        chart = alt.Chart(my_hist).mark_line(point=True).encode(
            x="Round",
            y="Score"
        )
        st.altair_chart(chart, use_container_width=True)

        all_wrong = []
        for _, r in my_hist.iterrows():
            if r["Wrong_Types"]:
                all_wrong += str(r["Wrong_Types"]).split(" | ")

        from collections import Counter
        cnt = Counter(all_wrong).most_common()

        selected = []
        seen = set()

        for t, c in cnt:
            msg = "\n".join(get_feedback_message_list(t))
            if msg not in seen:
                seen.add(msg)
                selected.append((t, c))
            if len(selected) == 3:
                break

        st.markdown("### 취약 유형")
        feedback_map = {}

        for t, c in selected:
            st.write(f"{t} ({c}회)")
            full = "\n".join(get_feedback_message_list(t))
            feedback_map[t] = full
            with st.expander(t):
                st.markdown(full)

        # ✅ HTML 리포트 다운로드
        html = f"<h1>{pg} {name} 포트폴리오</h1>"

        for t, c in selected:
            html += f"<h3>{t} ({c})</h3><p>{feedback_map[t]}</p>"

        st.download_button(
            "📥 포트폴리오 다운로드",
            html,
            file_name=f"{name}_portfolio.html",
            mime="text/html"
        )
