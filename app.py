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

# --- 2. 유형별 맞춤 피드백 & 칭찬 메시지 함수 ---

# [1] 약점 피드백 (틀렸을 때)
def get_feedback_message(question_type):
    if "문법" in question_type or "음운" in question_type or "국어사전" in question_type or "중세" in question_type:
        return """### 🔧 [문법/어휘] 개념의 '적용' 연습이 시급합니다!
> 문법은 감으로 푸는 게 아니라 **정확한 공식**을 대입해야 하는 수학 같은 영역입니다.

- **음운 변동:** 교체, 탈락, 첨가, 축약의 조건을 백지에 써보며 정리하세요.
- **문장 성분:** '서술어'를 먼저 찾고, 그에 해당하는 주어를 찾는 연습을 하세요.
- **중세 국어:** 현대어 풀이와 일대일로 대응시켜 보며 다른 조사를 찾아보세요."""

    elif "비문학" in question_type or "철학" in question_type or "경제" in question_type or "건축" in question_type:
        return """### 📚 [비문학 독서] '정보의 구조화'가 필요합니다.
> 지문의 내용을 눈으로만 읽지 말고, **손으로 구조를 그리며** 읽어야 합니다.

- **문단 요약:** 각 문단의 핵심 내용을 한 문장으로 요약하는 연습을 하세요.
- **정보 대조:** 철학/경제 지문은 서로 다른 관점(A학자 vs B학자)의 차이점을 표로 정리하는 습관이 중요합니다.
- **선지 근거:** 정답이 아니라도, 나머지 오답 선지가 지문의 '어디'에 나와 있는지 찾는 숨은그림찾기 훈련을 하세요."""

    elif "시가" in question_type or "작품" in question_type or "시어" in question_type or "소설" in question_type or "각본" in question_type:
        return """### 🎨 [문학] '상황'과 '정서' 파악에 집중하세요.
> 문학은 작가의 마음이 되어 **공감**하는 것이 시작입니다.

- **시 문학:** 화자가 어떤 상황(이별, 자연 예찬 등)에 있는지 먼저 파악하고, 시어의 긍정/부정 의미를 기호(O, X)로 표시해 보세요.
- **소설/극:** 인물 간의 갈등 관계도(누가 누구를 싫어하는지)를 그리면서 읽으면 전체 줄거리가 한눈에 들어옵니다."""

    elif "적용" in question_type or "보기" in question_type or "준거" in question_type:
        return """### 🔥 [고난도/응용] '보기'는 힌트 창고입니다.
> <보기> 문제나 3점짜리 문제는 지문의 내용을 새로운 상황에 적용하는 **논리력**을 묻습니다.

- <보기>의 내용을 먼저 완벽하게 이해한 뒤, 지문의 핵심 키워드와 연결하는 연습을 하세요.
- 이 유형을 틀린다는 것은 독해력보다는 **'문제 해결력'**이 부족하다는 뜻입니다. 고난도 기출 문제만 모아서 하루 3개씩 꾸준히 풀어보세요."""

    elif "강연" in question_type or "말하기" in question_type:
        return """### 🗣️ [화법] 말하기 전략을 파악하세요.
> 화법은 강연자가 청중에게 **어떤 의도**로 말하고 있는지를 묻습니다.

- 질문을 던지며 흥미를 유발하는지, 전문가의 말을 인용하는지 등 **말하기 방식(전략)**을 정리해 두어야 합니다."""
    
    else:
        return """### ⚠️ [기타] 기초 학습이 필요합니다.
해당 유형의 기출 문제를 다시 풀어보고, 해설지를 정독하여 출제 의도를 파악해 보세요."""

# [2] 강점 칭찬 (다 맞았을 때)
def get_strength_message(question_type):
    if "문법" in question_type or "음운" in question_type:
        return "💎 **[문법 마스터]** 문법 개념이 아주 탄탄하게 잡혀있네요! 어려운 문법 문제도 논리적으로 잘 해결하고 있습니다."
    elif "비문학" in question_type:
        return "🧠 **[논리왕]** 정보량이 많은 비문학 지문을 구조적으로 독해하는 능력이 탁월합니다! 가장 어려운 파트를 잘 잡으셨어요."
    elif "문학" in question_type or "소설" in question_type or "시가" in question_type:
        return "💖 **[공감 능력자]** 작품 속 인물의 심리와 작가의 의도를 꿰뚫어 보는 감수성이 뛰어납니다! 문학은 당신의 강력한 무기입니다."
    elif "보기" in question_type or "적용" in question_type:
        return "🚀 **[응용 천재]** 남들이 가장 어려워하는 <보기> 응용 문제를 완벽하게 해결했네요. 사고력이 매우 뛰어납니다!"
    else:
        return "✨ **[성실한 학습자]** 해당 유형에 대한 이해도가 완벽합니다. 지금처럼만 꾸준히 하세요!"
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
            # 1. 채점 및 유형 분석
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
                    # 데이터 저장
                    records = sheet.get_all_records()
                    new_row = [
                        student_id, name, total_score, 
                        " | ".join(wrong_list), 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    sheet.append_row(new_row)
                    
                    # 등수 계산
                    records = sheet.get_all_records() # 업데이트된 데이터 다시 로드
                    df = pd.DataFrame(records)
                    my_rank = df[df['Score'] > total_score].shape[0] + 1
                    total_students = len(df)
                    percentile = (my_rank / total_students) * 100
                    
                    # --- 3. 결과 화면 출력 ---
                    st.divider()
                    st.subheader(f"📢 {name}님의 분석 결과")
                    
                    # 점수판
                    c1, c2, c3 = st.columns(3)
                    c1.metric("내 점수", f"{int(total_score)}점")
                    c2.metric("현재 등수", f"{my_rank}등", f"/ {total_students}명")
                    c3.metric("상위", f"{percentile:.1f}%")
                    
                    st.markdown("---")

                    # === [A] 강점 분석 (로직 수정됨) ===
                    # 이제 '음운'을 틀려도 '문법' 칭찬이 나오지 않도록 그룹으로 묶어서 검사합니다.
                    
                    st.success("🌟 **나의 강점 발견!**")
                    found_any_strength = False

                    # 1. 문법/어휘 패밀리 검사
                    grammar_keys = ["문법", "음운", "국어사전", "중세"]
                    # 문법 관련 문제를 하나라도 틀렸는지 확인
                    is_grammar_wrong = any(any(k in w_type for k in grammar_keys) for w_type in wrong_list)
                    # 시험에 문법 문제가 존재하는지 확인
                    has_grammar_q = any(any(k in info['type'] for k in grammar_keys) for info in EXAM_DATA.values())

                    if has_grammar_q and not is_grammar_wrong:
                        st.write(f"- {get_strength_message('문법')}")
                        found_any_strength = True

                    # 2. 비문학 패밀리 검사
                    nonlit_keys = ["비문학", "철학", "경제", "건축"]
                    is_nonlit_wrong = any(any(k in w_type for k in nonlit_keys) for w_type in wrong_list)
                    has_nonlit_q = any(any(k in info['type'] for k in nonlit_keys) for info in EXAM_DATA.values())

                    if has_nonlit_q and not is_nonlit_wrong:
                        st.write(f"- {get_strength_message('비문학')}")
                        found_any_strength = True

                    # 3. 문학 패밀리 검사
                    lit_keys = ["시가", "작품", "시어", "소설", "각본"]
                    is_lit_wrong = any(any(k in w_type for k in lit_keys) for w_type in wrong_list)
                    has_lit_q = any(any(k in info['type'] for k in lit_keys) for info in EXAM_DATA.values())

                    if has_lit_q and not is_lit_wrong:
                        st.write(f"- {get_strength_message('문학')}")
                        found_any_strength = True

                    # 4. 고난도/보기 패밀리 검사
                    hard_keys = ["적용", "보기", "준거"]
                    is_hard_wrong = any(any(k in w_type for k in hard_keys) for w_type in wrong_list)
                    has_hard_q = any(any(k in info['type'] for k in hard_keys) for info in EXAM_DATA.values())

                    if has_hard_q and not is_hard_wrong:
                        st.write(f"- {get_strength_message('보기')}")
                        found_any_strength = True

                    # 칭찬할 게 하나도 없을 때 (골고루 틀렸을 때)
                    if not found_any_strength:
                        st.write("- 모든 영역에서 조금씩 실수가 있었네요. 오답 정리를 통해 빈틈을 채우면 다음엔 만점입니다! 💪")

                    # === [B] 약점 분석 (피드백) ===
                    if wrong_list:
                        st.markdown("---")
                        st.error(f"🚨 **보완이 필요한 부분 ({len(wrong_list)}문제 오답)**")
                        unique_feedback = set(get_feedback_message(w) for w in wrong_list)
                        for msg in unique_feedback:
                            st.markdown(msg)
                            st.markdown("---")
                    else:
                        st.balloons()
                        st.write("### 🎉 완벽합니다! 약점이 없는 무결점 실력입니다!")

                except Exception as e:
                    st.error(f"데이터 저장 오류: {e}")
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
