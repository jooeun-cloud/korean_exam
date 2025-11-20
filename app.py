import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- [추가] 성적표 HTML 생성 함수 ---
def create_report_html(name, score, rank, total_students, wrong_q_nums, wrong_list, feedback_text):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    
    if wrong_q_nums:
        wrong_nums_str = ", ".join(wrong_q_nums) + "번"
    else:
        wrong_nums_str = "없음 (만점)"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; padding: 40px; background-color: #f0f0f0; }}
            .paper {{ background-color: white; padding: 50px; max-width: 800px; margin: 0 auto; border: 1px solid #ccc; box-shadow: 5px 5px 15px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; border-bottom: 2px solid #333; padding-bottom: 20px; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
            .info-table th {{ background-color: #eee; padding: 10px; border: 1px solid #ddd; width: 30%; }}
            .info-table td {{ padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold; }}
            .score-box {{ text-align: center; padding: 20px; background-color: #f9f9f9; border-radius: 10px; margin: 20px 0; }}
            .score {{ font-size: 40px; color: #d32f2f; font-weight: bold; }}
            .feedback-section {{ margin-top: 30px; line-height: 1.6; }}
            .feedback-box {{ background-color: #fff8e1; padding: 15px; border-left: 5px solid #ffb300; margin-bottom: 15px; }}
            .footer {{ margin-top: 50px; text-align: center; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <h1>📑 국어 모의고사 분석 성적표</h1>
            
            <table class="info-table">
                <tr>
                    <th>이름</th>
                    <td>{name}</td>
                    <th>응시일자</th>
                    <td>{now}</td>
                </tr>
                <tr>
                    <th>내 점수</th>
                    <td style="color: blue;">{int(score)}점</td>
                    <th>전체 등수</th>
                    <td>{rank}등 / {total_students}명</td>
                </tr>
            </table>

            <div class="score-box">
                <div>틀린 문제 번호</div>
                <div style="font-size: 18px; margin-top: 5px;">❌ {wrong_nums_str}</div>
            </div>

            <div class="feedback-section">
                <h2>💊 유형별 상세 처방</h2>
                {feedback_text}
            </div>

            <div class="footer">
                위 학생의 모의고사 결과를 증명합니다.<br>
                Designed by AI Teacher
            </div>
        </div>
    </body>
    </html>
    """
    return html

# --- 1. 구글 시트 인증 및 연결 설정 ---
def get_google_sheet_data():
    if "gcp_service_account" not in st.secrets:
        st.error("비밀 키(Secrets)가 설정되지 않았습니다.")
        return None

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    
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

# --- 3. 피드백 및 칭찬 메시지 함수 ---
def get_feedback_message(question_type):
    if "음운" in question_type:
        return """
### 🛑 [긴급 처방] 문법: '음운 변동'의 원리를 놓치고 있습니다.
**1. 진단: 왜 틀렸을까요?**
'교체, 탈락, 첨가, 축약'의 개념이 머릿속에서 뒤섞여 있기 때문입니다.
**2. 핵심 개념 정리**
* **교체:** 비음화, 유음화, 구개음화, 된소리되기
* **탈락:** 자음군 단순화, ㄹ탈락, ㅎ탈락
**3. Action Plan**
1. 교과서를 덮고 4가지 카테고리를 안 보고 적어보세요.
2. 틀린 단어의 변동 과정을 기호로 풀어서 적어보세요.
"""
    elif "문장" in question_type or "문법" in question_type:
        return """
### 🏗️ [심층 분석] 문법: 문장의 '뼈대'를 보는 눈이 필요합니다.
**1. 진단**
관형절이 숨어있으면 성분을 찾지 못하고 헤매는 경우입니다.
**2. 핵심 개념**
* **안긴문장 찾기:** `-(으)ㄴ/는`, `-(으)ㅁ/기` 어미가 보이면 네모 박스를 치세요.
**3. Action Plan**
1. 모든 문장의 **서술어**에 밑줄을 그으세요.
2. 그 서술어의 주어를 찾아 연결하세요.
"""
    elif "중세" in question_type or "국어사전" in question_type:
        return """
### 📜 [심층 분석] 문법: 중세 국어는 '다른 그림 찾기'입니다.
**1. 진단**
현대어 풀이와 비교하여 문법적인 차이를 발견하는 능력이 필요합니다.
**2. 핵심 개념**
* **조사:** 주격조사 `이/ㅣ`와 관형격 조사 `ㅅ` 구분하기
**3. Action Plan**
1. <보기> 지문 밑에 현대어 풀이를 한 단어씩 짝지어 적어보세요.
"""
    elif "철학" in question_type or "인문" in question_type:
        return """
### 🧠 [심층 분석] 비문학(인문): 학자들의 '말싸움'을 정리하세요.
**1. 진단**
A학자와 B학자의 주장이 섞여서 정보 구조화가 안 된 상태입니다.
**2. 독해 전략**
* **이항 대립:** `A vs B` 구도로 나누어 읽으세요.
**3. Action Plan**
1. 학자별 핵심 키워드(주장, 근거)를 표로 정리하세요.
2. '그러나', '반면' 뒤에 나오는 내용에 주목하세요.
"""
    elif "경제" in question_type or "사회" in question_type:
        return """
### 📈 [심층 분석] 비문학(경제): '인과 관계'의 화살표를 그리세요.
**1. 진단**
환율, 금리 등 변수의 등락 관계(메커니즘)를 이해하지 못했습니다.
**2. 독해 전략**
* **화살표 표시:** `금리(↑) -> 통화량(↓)` 표시 필수!
**3. Action Plan**
1. 지문의 경제 현상을 화살표 도식으로 그려보세요.
2. 그래프의 X축과 Y축 의미를 먼저 파악하세요.
"""
    elif "건축" in question_type or "기술" in question_type or "과학" in question_type:
        return """
### ⚙️ [심층 분석] 비문학(기술/과학): '작동 원리'를 시각화하세요.
**1. 진단**
장치의 구조와 작동 순서를 머릿속으로 그리지 못했습니다.
**2. 독해 전략**
* **번호 매기기:** 작동 과정 문장에 ①, ②, ③ 번호를 매기세요.
**3. Action Plan**
1. 지문 여백에 장치의 구조를 간단히 그려보세요.
"""
    elif "소설" in question_type or "각본" in question_type or "서사" in question_type:
        return """
### 🎭 [심층 분석] 문학(산문): 인물 관계도와 갈등을 잡으세요.
**1. 진단**
전체 줄거리와 인물 간의 갈등(누가 누구를 싫어하는지)을 놓쳤습니다.
**2. 독해 전략**
* **인물 표시:** 긍정(O), 부정(X) 표시하며 읽기.
**3. Action Plan**
1. 중심 인물들의 관계도를 그려보세요.
2. 장면이 전환되는 부분에서 끊어 읽으세요.
"""
    elif "시가" in question_type or "시어" in question_type or "작품" in question_type:
        return """
### 🌙 [심층 분석] 문학(운문): 화자의 '상황'과 '정서'만 찾으세요.
**1. 진단**
너무 주관적으로 해석했습니다. 객관적인 상황 정보(이별, 가난 등)를 찾아야 합니다.
**2. 독해 전략**
* **정서 찾기:** 슬픔, 외로움 등 감정 단어에 형광펜 칠하기.
**3. Action Plan**
1. 긍정 시어(+), 부정 시어(-) 표시 훈련을 하세요.
2. <보기>를 먼저 읽고 기준을 잡으세요.
"""
    elif "적용" in question_type or "보기" in question_type:
        return """
### 🔥 [심층 분석] 고난도: <보기>는 또 하나의 지문입니다.
**1. 진단**
지문과 <보기>를 연결(Mapping)하지 못했습니다.
**2. 해결 알고리즘**
1. 지문(원리) 이해 -> 2. 보기(사례) 대입 -> 3. 선지 판단
**3. Action Plan**
1. 선지의 단어가 지문의 어디에서 왔는지 화살표로 연결하세요.
2. 선지를 근거/판단으로 끊어 읽으세요.
"""
    else:
        return """
### ⚠️ [종합 진단] 기초 체력 강화 필요
어휘력 부족이나 급하게 푸는 습관이 원인일 수 있습니다.
오답 선지가 왜 답이 아닌지 남에게 설명하듯 분석해 보세요.
"""

def get_strength_message(question_type):
    if "문법" in question_type:
        return "💎 **[문법 마스터]** 문법 개념이 아주 탄탄하게 잡혀있네요! 논리적인 접근이 돋보입니다."
    elif "비문학" in question_type:
        return "🧠 **[논리왕]** 정보량이 많은 비문학 지문을 구조적으로 독해하는 능력이 탁월합니다!"
    elif "문학" in question_type:
        return "💖 **[공감 능력자]** 작품 속 인물의 심리와 작가의 의도를 꿰뚫어 보는 감수성이 뛰어납니다!"
    elif "보기" in question_type:
        return "🚀 **[응용 천재]** 남들이 가장 어려워하는 <보기> 응용 문제를 완벽하게 해결했네요."
    else:
        return "✨ **[성실한 학습자]** 해당 유형에 대한 이해도가 완벽합니다."

# --- 4. 메인 화면 (UI) ---
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
            total_score = 0
            wrong_list = []
            wrong_q_nums = []
            
            for q, info in EXAM_DATA.items():
                if user_answers[q] == info['ans']:
                    total_score += info['score']
                else:
                    wrong_list.append(info['type'])
                    wrong_q_nums.append(str(q))
            
            sheet = get_google_sheet_data()
            if sheet:
                try:
                    records = sheet.get_all_records()
                    wrong_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                    
                    new_row = [
                        student_id, name, total_score, 
                        " | ".join(wrong_list), 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        wrong_q_str
                    ]
                    sheet.append_row(new_row)
                    
                    records = sheet.get_all_records()
                    df = pd.DataFrame(records)
                    my_rank = df[df['Score'] > total_score].shape[0] + 1
                    total_students = len(df)
                    percentile = (my_rank / total_students) * 100
                    
                    # 결과 출력
                    st.divider()
                    st.subheader(f"📢 {name}님의 분석 결과")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("내 점수", f"{int(total_score)}점")
                    c2.metric("현재 등수", f"{my_rank}등", f"/ {total_students}명")
                    c3.metric("상위", f"{percentile:.1f}%")
                    
                    st.markdown("---")
                    
                    if wrong_q_nums:
                        st.error(f"❌ **틀린 문제 번호:** {', '.join(wrong_q_nums)}번")
                    else:
                        st.success("⭕ **틀린 문제가 없습니다!**")

                    # 강점 분석
                    st.success("🌟 **나의 강점 발견!**")
                    found_any_strength = False
                    
                    grammar_keys = ["문법", "음운", "국어사전", "중세"]
                    is_grammar_wrong = any(any(k in w_type for k in grammar_keys) for w_type in wrong_list)
                    has_grammar_q = any(any(k in info['type'] for k in grammar_keys) for info in EXAM_DATA.values())
                    if has_grammar_q and not is_grammar_wrong:
                        st.write(f"- {get_strength_message('문법')}")
                        found_any_strength = True

                    nonlit_keys = ["비문학", "철학", "경제", "건축", "기술", "과학", "인문", "사회"]
                    is_nonlit_wrong = any(any(k in w_type for k in nonlit_keys) for w_type in wrong_list)
                    has_nonlit_q = any(any(k in info['type'] for k in nonlit_keys) for info in EXAM_DATA.values())
                    if has_nonlit_q and not is_nonlit_wrong:
                        st.write(f"- {get_strength_message('비문학')}")
                        found_any_strength = True

                    lit_keys = ["시가", "작품", "시어", "소설", "각본", "서사"]
                    is_lit_wrong = any(any(k in w_type for k in lit_keys) for w_type in wrong_list)
                    has_lit_q = any(any(k in info['type'] for k in lit_keys) for info in EXAM_DATA.values())
                    if has_lit_q and not is_lit_wrong:
                        st.write(f"- {get_strength_message('문학')}")
                        found_any_strength = True

                    hard_keys = ["적용", "보기", "준거"]
                    is_hard_wrong = any(any(k in w_type for k in hard_keys) for w_type in wrong_list)
                    has_hard_q = any(any(k in info['type'] for k in hard_keys) for info in EXAM_DATA.values())
                    if has_hard_q and not is_hard_wrong:
                        st.write(f"- {get_strength_message('보기')}")
                        found_any_strength = True

                    if not found_any_strength:
                        st.write("- 모든 영역에서 조금씩 실수가 있었네요. 다음엔 만점입니다! 💪")

                    # 약점 분석 및 성적표 생성
                    final_feedback_html = ""
                    if wrong_list:
                        st.markdown("---")
                        st.error(f"🚨 **보완이 필요한 부분 ({len(wrong_list)}문제 오답)**")
                        unique_feedback = set(get_feedback_message(w) for w in wrong_list)
                        for msg in unique_feedback:
                            st.markdown(msg)
                            st.markdown("---")
                            clean_msg = msg.replace("###", "<h3>").replace("**", "<b>").replace("\n", "<br>")
                            final_feedback_html += f"<div class='feedback-box'>{clean_msg}</div>"
                    else:
                        st.balloons()
                        st.write("### 🎉 완벽합니다! 약점이 없는 무결점 실력입니다!")
                        final_feedback_html = "<div class='feedback-box'><h3>🎉 완벽합니다!</h3>틀린 문제가 없어 학습 처방이 없습니다.</div>"

                    st.write("### 💾 결과 저장")
                    report_html = create_report_html(
                        name, total_score, my_rank, total_students, wrong_q_nums, wrong_list, final_feedback_html
                    )
                    
                    st.download_button(
                        label="📥 성적표 다운로드 (PDF 저장용)",
                        data=report_html,
                        file_name=f"{name}_국어성적표.html",
                        mime="text/html"
                    )

                except Exception as e: # <--- 여기가 바로 아까 사라졌던 그 부분입니다!
                    st.error(f"데이터 저장 오류: {e}")

# === [탭 2] 등수 재조회 ===
with tab2:
    st.header("🔍 내 등수 & 틀린 문제 확인")
    check_id = st.text_input("학번(ID) 입력", key="check_input")
    
    if st.button("조회하기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                df['ID'] = df['ID'].astype(str) 
                user_record = df[df['ID'] == check_id]
                
                if not user_record.empty:
                    last_row = user_record.iloc[-1]
                    current_score = last_row['Score']
                    
                    wrong_q_print = "없음"
                    if 'Wrong_Questions' in df.columns:
                        val = last_row['Wrong_Questions']
                        if pd.notna(val) and str(val).strip() != "":
                            wrong_q_print = str(val)
                    
                    wrong_types_str = str(last_row.get('Wrong_Types', ''))
                    wrong_list = wrong_types_str.split(" | ") if wrong_types_str.strip() else []

                    realtime_rank = df[df['Score'] > current_score].shape[0] + 1
                    total_now = len(df)
                    top_pct = (realtime_rank / total_now) * 100
                    
                    st.success(f"반갑습니다, **{last_row['Name']}**님!")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("내 점수", f"{int(current_score)}점")
                    m2.metric("현재 등수", f"{realtime_rank}등 / {total_now}명")
                    m3.metric("상위", f"{top_pct:.1f}%")
                    st.markdown("---")
                    
                    if wrong_q_print and wrong_q_print != "없음":
                        st.error(f"❌ **틀린 문제 번호:** {wrong_q_print}번")
                    else:
                        st.success("⭕ **틀린 문제가 없거나, 이전 기록이라 번호 데이터가 없습니다.**")

                    # 강점 분석 (재사용)
                    st.info("🌟 **나의 강점 다시 보기**")
                    found_any_strength = False
                    grammar_keys = ["문법", "음운", "국어사전", "중세"]
                    is_grammar_wrong = any(any(k in w_type for k in grammar_keys) for w_type in wrong_list)
                    has_grammar_q = any(any(k in info['type'] for k in grammar_keys) for info in EXAM_DATA.values())
                    if has_grammar_q and not is_grammar_wrong:
                        st.write(f"- {get_strength_message('문법')}")
                        found_any_strength = True

                    nonlit_keys = ["비문학", "철학", "경제", "건축", "기술", "과학", "인문", "사회"]
                    is_nonlit_wrong = any(any(k in w_type for k in nonlit_keys) for w_type in wrong_list)
                    has_nonlit_q = any(any(k in info['type'] for k in nonlit_keys) for info in EXAM_DATA.values())
                    if has_nonlit_q and not is_nonlit_wrong:
                        st.write(f"- {get_strength_message('비문학')}")
                        found_any_strength = True

                    lit_keys = ["시가", "작품", "시어", "소설", "각본", "서사"]
                    is_lit_wrong = any(any(k in w_type for k in lit_keys) for w_type in wrong_list)
                    has_lit_q = any(any(k in info['type'] for k in lit_keys) for info in EXAM_DATA.values())
                    if has_lit_q and not is_lit_wrong:
                        st.write(f"- {get_strength_message('문학')}")
                        found_any_strength = True

                    hard_keys = ["적용", "보기", "준거"]
                    is_hard_wrong = any(any(k in w_type for k in hard_keys) for w_type in wrong_list)
                    has_hard_q = any(any(k in info['type'] for k in hard_keys) for info in EXAM_DATA.values())
                    if has_hard_q and not is_hard_wrong:
                        st.write(f"- {get_strength_message('보기')}")
                        found_any_strength = True

                    if not found_any_strength:
                        st.write("- 모든 영역에서 조금씩 실수가 있었네요. 화이팅!")

                    # 약점 분석 (재사용)
                    final_feedback_html = ""
                    if wrong_list:
                        st.markdown("---")
                        st.error("🚨 **보완이 필요한 부분 다시 보기**")
                        unique_feedback = set(get_feedback_message(w) for w in wrong_list)
                        for msg in unique_feedback:
                            st.markdown(msg)
                            st.markdown("---")
                            clean_msg = msg.replace("###", "<h3>").replace("**", "<b>").replace("\n", "<br>")
                            final_feedback_html += f"<div class='feedback-box'>{clean_msg}</div>"
                    else:
                        final_feedback_html = "<div class='feedback-box'><h3>🎉 완벽합니다!</h3>오답 내역이 없습니다.</div>"

                    st.markdown("---")
                    st.write("### 💾 성적표 다시 저장하기")
                    
                    if wrong_q_print and wrong_q_print != "없음":
                        w_nums = wrong_q_print.split(", ")
                    else:
                        w_nums = []

                    report_html = create_report_html(
                        last_row['Name'], current_score, realtime_rank, total_now, w_nums, wrong_list, final_feedback_html
                    )
                    
                    st.download_button(
                        label="📥 성적표 다시 다운로드",
                        data=report_html,
                        file_name=f"{last_row['Name']}_국어성적표_재발급.html",
                        mime="text/html"
                    )

                else:
                    st.warning("해당 학번의 기록이 없습니다.")
            except Exception as e:
                st.error(f"조회 중 오류 발생: {e}")
