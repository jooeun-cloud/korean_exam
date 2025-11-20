import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 구글 시트 인증 및 연결 설정 ---
# (주의: Streamlit Cloud의 Secrets 기능을 사용해야 작동합니다)
def get_google_sheet_data():
    # 비밀키가 있는지 확인
    if "gcp_service_account" not in st.secrets:
        st.error("비밀 키(Secrets)가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return None

    # 구글 시트 연결
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    
    # 시트 열기 (시트 이름이 'ExamResults'라고 가정)
    # ※ 다음 단계에서 구글 시트 이름을 꼭 'ExamResults'로 만들어주세요!
    try:
        sheet = client.open("ExamResults").sheet1
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("구글 시트를 찾을 수 없습니다. 시트 이름을 'ExamResults'로 설정했는지 확인하세요.")
        return None

# --- 2. 문제 데이터 및 정답 설정 ---
EXAM_DATA = {
    1: {"ans": 2, "score": 3, "type": "강연자의 말하기 방식 이해"},
    2: {"ans": 4, "score": 3, "type": "강연 자료의 적절성 판단"},
    3: {"ans": 2, "score": 3, "type": "<보기>를 보고 청자의 듣기 전략 이해"},
    4: {"ans": 5, "score": 3, "type": "음운 동화 이해"},
    5: {"ans": 1, "score": 3, "type": "음운 동화의 구체적 사례 이해"},
    6: {"ans": 1, "score": 4, "type": "문장의 짜임 이해 (문법)"},
    7: {"ans": 5, "score": 3, "type": "국어사전의 정보 탐구"},
    8: {"ans": 1, "score": 3, "type": "중세국어의 특징 탐구"},
    9: {"ans": 2, "score": 3, "type": "철학 비문학 지문 내용 이해"},
    10: {"ans": 5, "score": 3, "type": "철학 비문학 지문 세부 내용 이해"},
    11: {"ans": 2, "score": 3, "type": "철학 비문학 핵심내용 <보기> 적용"},
    12: {"ans": 2, "score": 4, "type": "철학 비문학 바탕으로 <보기> 자료 해석"},
    13: {"ans": 5, "score": 3, "type": "한국의 전통시가/한국문학 특징 이해"},
    14: {"ans": 1, "score": 3, "type": "작품의 표현상의 특징 파악"},
    15: {"ans": 3, "score": 3, "type": "시어의 의미 파악"},
    16: {"ans": 5, "score": 3, "type": "작품의 시상 전개 과정 파악"},
    17: {"ans": 4, "score": 4, "type": "외적 준거를 바탕으로 작품 감상"},
    18: {"ans": 2, "score": 3, "type": "경제 비문학 지문 내용 전개 방식"},
    19: {"ans": 3, "score": 3, "type": "경제 비문학 지문 세부 정보 이해"},
    20: {"ans": 2, "score": 4, "type": "경제 비문학 내용 구체적 상황 적용"},
    21: {"ans": 3, "score": 3, "type": "각본을 읽고 연출 계획 적절성 평가"},
    22: {"ans": 4, "score": 4, "type": "각본을 외적 준거에 따라 감상"},
    23: {"ans": 1, "score": 3, "type": "각본 작품 맥락 파악 및 구절 의미"},
    24: {"ans": 1, "score": 3, "type": "건축 비문학 글의 세부 정보 파악"},
    25: {"ans": 4, "score": 3, "type": "건축 비문학 글의 핵심 정보 파악"},
    26: {"ans": 3, "score": 3, "type": "비문학 세부 내용 공통점 추론"},
    27: {"ans": 3, "score": 4, "type": "건축 비문학 내용 구체적 사례 적용"},
    28: {"ans": 5, "score": 4, "type": "소설의 서사적 특징 이해"},
    29: {"ans": 3, "score": 3, "type": "소설의 재담 구조 이해"},
    30: {"ans": 4, "score": 3, "type": "소설을 읽고 인물의 심리 이해"},
    31: {"ans": 1, "score": 3, "type": "상황에 맞는 한자성어 이해"},
}

def get_feedback_message(question_type):
    if "문법" in question_type or "음운" in question_type or "국어사전" in question_type or "중세" in question_type:
        return "🔧 **[문법/어휘]** 단순히 개념을 외우는 것을 넘어, 실제 예문에 적용하는 연습이 부족해 보입니다. \n 특히 '음운의 변동' 규칙 4가지(교체, 탈락, 첨가, 축약)를 백지에 써보면서 복습하세요."
    elif "비문학" in question_type:
        return "📚 **[비문학 독서]** 지문의 핵심 정보와 세부 내용을 대조하는 훈련이 필요합니다."
    elif "시가" in question_type or "작품" in question_type or "시어" in question_type or "소설" in question_type or "각본" in question_type:
        return "🎨 **[문학]** 작품 감상 능력과 문학 개념어(표현법, 서사 구조 등)를 보완해야 합니다."
    elif "적용" in question_type or "보기" in question_type or "준거" in question_type:
        return "🔥 **[고난도/응용]** <보기>나 새로운 상황에 지문 내용을 적용하는 심화 문제 연습이 필수입니다."
    elif "강연" in question_type or "말하기" in question_type:
        return "🗣️ **[화법]** 말하기 전략과 자료 활용 방식을 묻는 문제 유형에 익숙해져야 합니다."
    elif "한자성어" in question_type:
        return "📖 **[어휘]** 필수 한자성어와 어휘 암기가 필요합니다."
    else:
        return "⚠️ 해당 유형의 기출 문제를 더 풀어보세요."

# --- 3. UI 및 메인 로직 ---
st.set_page_config(page_title="국어 모의고사 채점", page_icon="📝")
st.title("📝 국어 모의고사 자동 채점 & 분석")

tab1, tab2 = st.tabs(["답안 제출하기", "내 등수 조회하기"])

# === [탭 1] 답안 입력 및 채점 ===
with tab1:
    st.write("##### 학생 정보를 입력하고 답안을 체크하세요.")
    with st.form("exam_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름", placeholder="홍길동")
        student_id = c2.text_input("학번 (또는 ID)", placeholder="예: 10101")
        
        st.markdown("---")
        user_answers = {}
        
        # 4개 컬럼으로 나누어 배치
        cols = st.columns(4)
        for q_num in EXAM_DATA.keys():
            col_idx = (q_num - 1) % 4
            with cols[col_idx]:
                user_answers[q_num] = st.number_input(
                    f"{q_num}번 ({EXAM_DATA[q_num]['score']}점)", 
                    min_value=1, max_value=5, step=1, key=f"q_{q_num}"
                )

        submit = st.form_submit_button("채점 제출하기", use_container_width=True)

    if submit:
        if not name or not student_id:
            st.error("이름과 학번을 반드시 입력해주세요!")
        else:
            # 1. 채점
            total_score = 0
            wrong_list = []
            for q, info in EXAM_DATA.items():
                if user_answers[q] == info['ans']:
                    total_score += info['score']
                else:
                    wrong_list.append(info['type'])
            
            # 2. 구글 시트에 저장
            sheet = get_google_sheet_data()
            if sheet:
                try:
                    # 기존 데이터 가져오기 (등수 계산 및 중복 확인용)
                    records = sheet.get_all_records()
                    df = pd.DataFrame(records)
                    
                    # 기존에 같은 ID가 있으면 해당 행 삭제 (업데이트 효과)
                    # (복잡함을 피하기 위해 여기선 단순히 맨 아래에 추가하고, 나중에 조회할 때 최신 것만 쓰거나 필터링)
                    # *더 정확한 로직: ID가 있는지 찾아서 그 셀을 업데이트*
                    # 여기서는 간단히 '추가(append)' 방식을 씁니다.
                    
                    new_row = [
                        student_id, 
                        name, 
                        total_score, 
                        " | ".join(wrong_list), 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    sheet.append_row(new_row)
                    
                    # 3. 등수 계산을 위해 데이터 다시 로드 (방금 추가한 것 포함)
                    records = sheet.get_all_records()
                    df = pd.DataFrame(records)
                    
                    # 내 등수 계산
                    # 학번이 같은 중복 데이터가 있다면 가장 최근 점수만 남기는 처리 필요할 수 있음
                    # 여기서는 단순하게 전체 데이터 기준
                    my_rank = df[df['Score'] > total_score].shape[0] + 1
                    total_students = len(df)
                    percentile = (my_rank / total_students) * 100
                    
                    st.divider()
                    st.subheader(f"📢 {name}님의 결과")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("내 점수", f"{int(total_score)}점")
                    c2.metric("현재 등수", f"{my_rank}등", f"/ {total_students}명")
                    c3.metric("상위", f"{percentile:.1f}%")
                    
                    if wrong_list:
                        st.error(f"🚨 {len(wrong_list)}문제 틀렸습니다.")
                        st.markdown("### 💊 유형별 맞춤 처방")
                        unique_feedback = set(get_feedback_message(w) for w in wrong_list)
                        for msg in unique_feedback:
                            st.write(msg)
                    else:
                        st.balloons()
                        st.success("만점입니다! 축하합니다!")

                except Exception as e:
                    st.error(f"데이터 저장 중 오류 발생: {e}")

# === [탭 2] 등수 재조회 ===
with tab2:
    st.header("🔍 내 등수 실시간 확인")
    check_id = st.text_input("학번(ID) 입력", key="check_input")
    
    if st.button("조회하기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                
                # ID로 검색 (ID는 문자열로 변환해서 비교)
                df['ID'] = df['ID'].astype(str) 
                user_record = df[df['ID'] == check_id]
                
                if not user_record.empty:
                    # 가장 마지막(최신) 기록 사용
                    last_row = user_record.iloc[-1]
                    current_score = last_row['Score']
                    
                    realtime_rank = df[df['Score'] > current_score].shape[0] + 1
                    total_now = len(df)
                    top_pct = (realtime_rank / total_now) * 100
                    
                    st.success(f"반갑습니다, **{last_row['Name']}**님!")
                    m1, m2 = st.columns(2)
                    m1.metric("내 점수", f"{int(current_score)}점")
                    m2.metric("현재 등수", f"{realtime_rank}등 / {total_now}명", f"상위 {top_pct:.1f}%")
                else:
                    st.warning("해당 학번의 기록이 없습니다.")
            except Exception as e:
                st.error(f"조회 중 오류 발생: {e}")
