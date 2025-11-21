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
    # 통합된 카테고리 이름을 기준으로 피드백을 제공합니다.
    if "화법" in question_type:
        return """### 🗣️ [심층 분석] 화법: 강연자의 '전략'을 꿰뚫어 보세요.
**1. 진단**
내용 일치보다 강연자가 사용한 **'말하기 장치'**를 놓쳤기 때문입니다.

**2. Action Plan**
1. '질문을 통해', '자료를 제시하며' 같은 서술어 찾기.
2. (웃으며) 같은 비언어적 표현 체크하기."""
    if "음운" in question_type:
        return """### 🛑 [긴급 처방] 문법: '음운 변동'의 원리를 놓치고 있습니다.
        
**1. 진단**
'교체, 탈락, 첨가, 축약'의 개념이 머릿속에서 뒤섞여 있기 때문입니다.

**2. Action Plan**
1. 교과서를 덮고 4가지 카테고리를 안 보고 적어보세요.
2. 틀린 단어의 변동 과정을 기호로 풀어서 적어보세요."""
    if "통사" in question_type or "문장" in question_type:
        return """### 🏗️ [심층 분석] 문법: 문장의 '뼈대'를 보는 눈이 필요합니다.
        
**1. 진단**
관형절이 숨어있으면 성분을 찾지 못하고 헤매는 경우입니다.

**2. Action Plan**
1. 모든 문장의 **서술어**에 밑줄을 그으세요.
2. 그 서술어의 주어를 찾아 연결하세요."""
    if "국어사" in question_type:
        return """### 📜 [심층 분석] 문법: 중세 국어는 '다른 그림 찾기'입니다.
        
**1. 진단**
현대어 풀이와 비교하여 문법적인 차이를 발견하는 능력이 필요합니다.

**2. Action Plan**
1. <보기> 지문 밑에 현대어 풀이를 한 단어씩 짝지어 적어보세요."""
    if "인문" in question_type:
        return """### 🧠 [심층 분석] 비문학(인문): 학자들의 '말싸움'을 정리하세요.
        
**1. 진단**
A학자와 B학자의 주장이 섞여서 정보 구조화가 안 된 상태입니다.

**2. Action Plan**
1. 학자별 핵심 키워드(주장, 근거)를 표로 정리하세요.
2. '그러나', '반면' 뒤에 나오는 내용에 주목하세요."""
    if "경제" in question_type:
        return """### 📈 [심층 분석] 비문학(경제): '인과 관계'의 화살표를 그리세요.
        
**1. 진단**
환율, 금리 등 변수의 등락 관계(메커니즘)를 이해하지 못했습니다.

**2. Action Plan**
1. 지문의 경제 현상을 화살표 도식으로 그려보세요.
2. 그래프의 X축과 Y축 의미를 먼저 파악하세요."""
    if "과학" in question_type:        
       return """### ⚙️ [심층 분석] 비문학(기술/과학): '작동 원리'를 시각화하세요.
       
**1. 진단**
장치의 구조와 작동 순서를 머릿속으로 그리지 못했습니다.

**2. Action Plan**
1. 지문 여백에 장치의 구조를 간단히 그려보세요."""
    if "산문" in question_type:
        return """### 🎭 [심층 분석] 문학(산문): 인물 관계도와 갈등을 잡으세요.
        
**1. 진단**
전체 줄거리와 인물 간의 갈등을 놓쳤습니다.

**2. Action Plan**
1. 중심 인물들의 관계도를 그려보세요.
2. 장면이 전환되는 부분에서 끊어 읽으세요."""
    if "운문" in question_type:
        return """### 🌙 [심층 분석] 문학(운문): 화자의 '상황'과 '정서'만 찾으세요.
        
**1. 진단**
너무 주관적으로 해석했습니다. 객관적인 상황 정보를 찾아야 합니다.
**2. Action Plan**
1. 긍정 시어(+), 부정 시어(-) 표시 훈련을 하세요.
2. <보기>를 먼저 읽고 기준을 잡으세요."""
    if "고난도" in question_type or "보기" in question_type:
        return """### 🔥 [심층 분석] 고난도: <보기>는 또 하나의 지문입니다.
        
**1. 진단**
지문과 <보기>를 연결(Mapping)하지 못했습니다.

**2. Action Plan**
1. 선지의 단어가 지문의 어디에서 왔는지 화살표로 연결하세요.
2. 선지를 근거/판단으로 끊어 읽으세요."""
    return """### ⚠️ [종합 진단] 기초 체력 강화 필요
어휘력 부족이나 급하게 푸는 습관이 원인일 수 있습니다.
오답 선지가 왜 답이 아닌지 남에게 설명하듯 분석해 보세요."""


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
        
        # [핵심 수정] 문제 리스트를 정렬해서 가져옵니다.
        sorted_q_nums = sorted(current_exam_data.keys())
        
        # 2개씩 짝지어서 반복문 돌리기 (Step 2)
        # 이렇게 하면 [Row 1: 1번, 2번], [Row 2: 3번, 4번]... 순서로 생성됩니다.
        for i in range(0, len(sorted_q_nums), 2):
            # 매 반복마다 새로운 2단 컬럼(한 줄)을 만듭니다.
            cols = st.columns(2)
            
            # --- 왼쪽 문제 (i번째) ---
            q_num = sorted_q_nums[i]
            info = current_exam_data[q_num]
            
            with cols[0]:
                st.markdown(f"**{q_num}번** <small>({info['score']}점)</small>", unsafe_allow_html=True)
                user_answers[q_num] = st.radio(
                    label=f"{q_num}번 답안",
                    options=[1, 2, 3, 4, 5],
                    horizontal=True,
                    label_visibility="collapsed",
                    index=None,
                    key=f"q_{grade}_{selected_round}_{q_num}"
                )
                st.write("") # 간격 띄우기

            # --- 오른쪽 문제 (i+1번째) ---
            # 홀수 개일 경우 마지막 문제가 없을 수 있으므로 체크
            if i + 1 < len(sorted_q_nums):
                q_num_next = sorted_q_nums[i+1]
                info_next = current_exam_data[q_num_next]
                
                with cols[1]:
                    st.markdown(f"**{q_num_next}번** <small>({info_next['score']}점)</small>", unsafe_allow_html=True)
                    user_answers[q_num_next] = st.radio(
                        label=f"{q_num_next}번 답안",
                        options=[1, 2, 3, 4, 5],
                        horizontal=True,
                        label_visibility="collapsed",
                        index=None,
                        key=f"q_{grade}_{selected_round}_{q_num_next}"
                    )
                    st.write("")

        st.markdown("---")
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
            
            # (채점 로직 for문 안에서)
            for q, info in current_exam_data.items():
                # user_answers[q]가 None(선택 안함)일 경우 0으로 처리
                user_ans = user_answers[q] if user_answers[q] is not None else 0
                
                if user_ans == info['ans']:
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
# ▼▼▼ [추가] 관리자 비밀번호 설정 (원하는 비번으로 바꾸세요) ▼▼▼
ADMIN_PASSWORD = "1234" 

# 사이드바 로그인 창
with st.sidebar:
    st.header("🔐 관리자 로그인")
    input_pw = st.text_input("비밀번호", type="password")
    if input_pw == ADMIN_PASSWORD:
        st.session_state['is_admin'] = True
        st.success("관리자 모드 ON ✅")
    else:
        st.session_state['is_admin'] = False
        if input_pw:
            st.error("비밀번호 오류")

# 관리자 여부 변수 (편의용)
is_admin = st.session_state.get('is_admin', False)
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
# === [탭 2] 결과 조회 (관리자 기능 포함 + 에러 수정) ===
with tab2:
    st.header("🔍 성적표 조회")
    
    # 학년별 조회 탭 생성
    active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]
    
    if not active_grades:
        st.warning("데이터가 없습니다.")
    else:
        result_tabs = st.tabs(active_grades)
        
        # 조회 로직 함수
        def render_result_page(grade):
            if grade not in EXAM_DB: return
            rounds = list(EXAM_DB[grade].keys())
            
            c1, c2 = st.columns(2)
            chk_round = c1.selectbox("회차", rounds, key=f"res_round_{grade}")
            chk_id = c2.text_input("학번(ID)", key=f"res_id_{grade}")
            
            if st.button("조회하기", key=f"btn_res_{grade}"):
                sheet = get_google_sheet_data()
                if sheet:
                    try: # <--- 여기서 try가 시작됩니다.
                        records = sheet.get_all_records()
                        df = pd.DataFrame(records)
                        
                        # 전처리 (0 문제 해결)
                        df['Grade'] = df['Grade'].astype(str).str.strip()
                        df['Round'] = df['Round'].astype(str).str.strip()
                        df['ID'] = df['ID'].astype(str)
                        
                        def normalize(val):
                            try: return str(int(val))
                            except: return str(val).strip()
                        
                        df['ID_Clean'] = df['ID'].apply(normalize)
                        in_id = normalize(chk_id)
                        
                        # 데이터 검색
                        my_data = df[
                            (df['Grade'] == str(grade)) & 
                            (df['Round'] == str(chk_round)) & 
                            (df['ID_Clean'] == in_id)
                        ]
                        
                        if not my_data.empty:
                            last_row = my_data.iloc[-1]
                            
                            # 등수 계산
                            round_data = df[(df['Grade']==str(grade)) & (df['Round']==str(chk_round))]
                            rank = round_data[round_data['Score'] > last_row['Score']].shape[0] + 1
                            total = len(round_data)
                            pct = (rank / total) * 100
                            
                            # --- 기본 정보 출력 ---
                            st.divider()
                            st.subheader(f"📢 {grade} {last_row['Name']}님의 결과")
                            m1, m2, m3 = st.columns(3)
                            m1.metric("점수", f"{int(last_row['Score'])}")
                            m2.metric("등수", f"{rank} / {total}")
                            m3.metric("상위", f"{pct:.1f}%")
                            
                            # 틀린 문제 번호 가져오기
                            w_q_str = str(last_row.get('Wrong_Questions', ''))
                            w_nums = [int(x.strip()) for x in w_q_str.split(",") if x.strip().isdigit()] if w_q_str != "없음" else []
                            
                            st.markdown("---")
                            if w_nums:
                                st.error(f"❌ **틀린 문제 번호:** {w_q_str}번")
                            else:
                                st.success("⭕ 만점입니다!")

                            # --- [관리자 권한 체크 및 분기] ---
                            # --- [관리자 권한 체크 및 분기] ---
                            if is_admin:
                                st.info("🔒 **관리자 권한으로 상세 분석 내용을 확인합니다.**")
                                
                                current_db = EXAM_DB[grade][chk_round]
                                
                                # [핵심 수정] 피드백 내용(Message)을 기준으로 그룹화
                                # Key: 피드백 메시지 전체
                                # Value: 틀린 문제 번호 리스트
                                feedback_grouping = {}
                                
                                for q in w_nums:
                                    if q in current_db:
                                        qt = current_db[q]['type']
                                        msg = get_feedback_message(qt) # 해당 유형의 피드백 가져오기
                                        
                                        if msg not in feedback_grouping:
                                            feedback_grouping[msg] = []
                                        feedback_grouping[msg].append(q)
                                
                                # 화면 출력
                                if feedback_grouping:
                                    st.markdown("---")
                                    st.write("### 💡 유형별 상세 분석 (통합)")
                                    
                                    for msg, nums in feedback_grouping.items():
                                        # 문제 번호 나열
                                        nums_txt = ", ".join(map(str, nums))
                                        
                                        # Expander 제목을 예쁘게 뽑기 위해 피드백의 '첫 줄(제목)'을 추출
                                        # 예: "### 🔧 문법..." -> "🔧 문법..."
                                        title_preview = "상세 피드백"
                                        first_line = msg.strip().split('\n')[0]
                                        if "###" in first_line:
                                            title_preview = first_line.replace("###", "").strip()
                                        
                                        # 하나로 통합된 피드백 박스 출력
                                        with st.expander(f"❌ {title_preview} (틀린 문제: {nums_txt}번)", expanded=True):
                                            st.markdown(msg)
                                else:
                                    st.balloons()
                                    st.success("완벽합니다! 피드백이 없습니다.")

                                # 성적표 다운로드 버튼
                                st.write("---")
                                
                                # [추가] 성적표 생성 함수에 넘겨줄 데이터도 '그룹화된 형태'로 변환
                                # create_report_html 함수는 {유형이름: 번호리스트} 형태를 받습니다.
                                # 따라서 '피드백 제목'을 '유형이름'처럼 위장해서 넘겨줍니다.
                                report_map = {}
                                
                                # 피드백 제목을 Key로 사용하는 맵 생성
                                for msg, nums in feedback_grouping.items():
                                    first_line = msg.strip().split('\n')[0]
                                    title = first_line.replace("###", "").strip() if "###" in first_line else "기타 유형"
                                    report_map[title] = nums
                                
                                # 단, create_report_html 내부에서 다시 get_feedback_message를 호출하므로
                                # 이를 우회하기 위해 '임시 피드백 함수'를 람다(Lambda)로 만들어 넘깁니다.
                                # (이미 메시지 내용을 알고 있으므로, 제목을 주면 본문을 리턴하도록 매핑)
                                
                                # 1. 제목 -> 본문 매핑 테이블 생성
                                title_to_msg = {}
                                for msg in feedback_grouping.keys():
                                    first_line = msg.strip().split('\n')[0]
                                    title = first_line.replace("###", "").strip() if "###" in first_line else "기타 유형"
                                    title_to_msg[title] = msg
                                    
                                # 2. 성적표 생성 호출
                                report = create_report_html(
                                    grade, chk_round, last_row['Name'], last_row['Score'], 
                                    rank, total, 
                                    report_map, # 유형 대신 '제목'이 들어간 맵
                                    lambda x: title_to_msg.get(x, "") # 제목을 넣으면 본문을 주는 가짜 함수
                                )
                                
                                st.download_button(
                                    "📥 성적표 다운로드", report, 
                                    file_name="성적표.html", mime="text/html", 
                                    key=f"res_dn_{grade}"
                                )
                            
                            else:
                                # [학생일 경우]
                                st.warning("🔒 **상세 피드백과 성적표 다운로드는 선생님(관리자)만 확인할 수 있습니다.**")
                                st.write("틀린 문제 번호를 확인하고 오답노트를 작성하세요.")
                        
                        else:
                            st.error("기록이 없습니다.")
                    
                    except Exception as e: # <--- 아까 이 부분이 빠져있었습니다!
                        st.error(f"조회 중 오류 발생: {e}")

        # 반복문으로 탭 생성
        for i, grade in enumerate(active_grades):
            with result_tabs[i]:
                render_result_page(grade)

# === [탭 3] 종합 기록부 ===
with tab3:
    # === [탭 3] 종합 기록부 (관리자 전용 + 심층 분석) ===
with tab3:
    st.header("📈 포트폴리오")
    
    # 1. 관리자 권한 체크
    if not is_admin:
        st.error("⛔ **접근 권한이 없습니다.**")
        st.info("종합 기록부는 선생님만 열람할 수 있습니다. 왼쪽 사이드바에서 로그인하세요.")
        st.stop()

    # 2. 검색 인터페이스
    active_grades = [g for g in GRADE_ORDER if g in EXAM_DB]
    
    c1, c2 = st.columns(2)
    pg = c1.selectbox("학년", active_grades, key="pg")
    pid = c2.text_input("학번(ID)", key="pid")
    
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
                
                # 데이터 필터링
                my_hist = df[(df['Grade']==str(pg)) & (df['ID_Clean']==in_id)]
                
                if not my_hist.empty:
                    # --- 기본 정보 및 그래프 ---
                    student_name = my_hist.iloc[-1]['Name']
                    st.success(f"**{pg} {student_name}**님의 성장 기록입니다.")
                    
                    avg_score = my_hist['Score'].mean()
                    max_score = my_hist['Score'].max()
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("총 응시 횟수", f"{len(my_hist)}회")
                    m2.metric("평균 점수", f"{avg_score:.1f}점")
                    m3.metric("최고 점수", f"{int(max_score)}점")
                    
                    st.markdown("### 1️⃣ 성적 변화 추이")
                    chart = alt.Chart(my_hist).mark_line(point=True).encode(
                        x=alt.X('Round', sort=None, title='시험 회차'),
                        y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]), title='점수'),
                        tooltip=['Round', 'Score']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                    
                    # --- [핵심 추가] 누적 약점 분석 ---
                    st.markdown("---")
                    st.markdown("### 2️⃣ 누적 취약점 분석 (AI 진단)")
                    
                    # 모든 회차의 오답 유형을 하나로 모으기
                    all_wrong_types = []
                    for idx, row in my_hist.iterrows():
                        if str(row['Wrong_Types']).strip():
                            # "문법 | 독서" -> ["문법", "독서"]
                            types = str(row['Wrong_Types']).split(" | ")
                            all_wrong_types.extend(types)
                    
                    if all_wrong_types:
                        from collections import Counter
                        # 가장 많이 틀린 순서대로 정렬
                        counts = Counter(all_wrong_types)
                        sorted_counts = counts.most_common()
                        
                        # 화면 분할: 왼쪽(순위표) / 오른쪽(상세 피드백)
                        col_list, col_feedback = st.columns([1, 1.5])
                        
                        with col_list:
                            st.write("📉 **가장 많이 틀린 유형 TOP 3**")
                            for i, (w_type, count) in enumerate(sorted_counts[:3]):
                                st.error(f"**{i+1}위: {w_type}** (총 {count}회 오답)")
                        
                        with col_feedback:
                            st.info("💡 **맞춤 학습 처방**")
                            # 1위 약점에 대한 심층 피드백 제공
                            worst_type = sorted_counts[0][0]
                            msg = get_feedback_message(worst_type)
                            
                            st.write(f"가장 취약한 **'{worst_type}'** 해결이 시급합니다.")
                            with st.expander("클릭해서 처방전 보기", expanded=True):
                                st.markdown(msg)
                                
                        # (선택) 모든 약점 리스트 펼쳐보기
                        with st.expander("📋 전체 오답 유형 빈도 확인하기"):
                            st.dataframe(
                                pd.DataFrame(sorted_counts, columns=["유형", "틀린 횟수"]),
                                use_container_width=True
                            )
                            
                    else:
                        st.balloons()
                        st.success("🎉 대단합니다! 지금까지 틀린 문제가 단 하나도 없습니다.")

                    # --- 3. 상세 기록 표 ---
                    st.markdown("---")
                    st.markdown("### 3️⃣ 응시 기록 상세")
                    st.dataframe(my_hist[['Round', 'Score', 'Timestamp', 'Wrong_Types']])
                    
                else:
                    st.warning("응시 기록이 없습니다.")
            except Exception as e: st.error(f"오류: {e}")
