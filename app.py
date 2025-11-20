import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- [1] 문제 데이터베이스 ---
EXAM_DB = {
    "1학년": {
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
        },
        "2회차": {
            1: {"ans": 1, "score": 100, "type": "테스트"},
        }
    },
    "2학년": {
        "1회차": {
            1: {"ans": 1, "score": 100, "type": "테스트"},
        }
    }
}

# --- [NEW] 유형 통합 함수 (핵심!) ---
# 세부 유형 이름을 피드백용 '큰 카테고리'로 바꿔줍니다.
def normalize_type(detail_type):
    if any(x in detail_type for x in ["화법", "말하기", "강연"]): return "화법"
    if any(x in detail_type for x in ["음운"]): return "문법 (음운)"
    if any(x in detail_type for x in ["문장", "문법"]): return "문법 (통사)"
    if any(x in detail_type for x in ["중세", "국어사전", "매체"]): return "문법 (국어사/매체)"
    if any(x in detail_type for x in ["철학", "인문"]): return "독서 (인문/철학)"
    if any(x in detail_type for x in ["경제", "사회"]): return "독서 (사회/경제)"
    if any(x in detail_type for x in ["건축", "기술", "과학"]): return "독서 (과학/기술)"
    if any(x in detail_type for x in ["소설", "각본", "서사", "극"]): return "문학 (산문)"
    if any(x in detail_type for x in ["시가", "시어", "작품", "표현"]): return "문학 (운문)"
    if any(x in detail_type for x in ["적용", "보기", "준거", "추론"]): return "고난도 (보기/적용)"
    return "기타"

# --- [2] 성적표 HTML 생성 함수 ---
def create_report_html(grade, round_name, name, score, rank, total_students, wrong_data_map, feedback_func):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    
    has_wrong = bool(wrong_data_map)
    feedback_section_html = ""
    
    if has_wrong:
        for category, q_nums in wrong_data_map.items():
            nums_str = ", ".join([str(n) for n in q_nums]) + "번"
            msg = feedback_func(category) # 통합된 카테고리로 피드백 호출
            
            clean_msg = msg.strip().replace(">", "💡").replace("**", "").replace("-", "•")
            clean_msg = clean_msg.replace("\n", "<br>")
            
            if clean_msg.startswith("###"):
                parts = clean_msg.split("<br>", 1)
                title_txt = parts[0].replace("###", "").strip()
                body_txt = parts[1] if len(parts) > 1 else ""
                
                feedback_section_html += f"""
                <div class="feedback-card">
                    <div class="card-header">
                        <span class="card-title">{title_txt}</span>
                        <span class="card-nums">❌ 틀린 문제: {nums_str}</span>
                    </div>
                    <div class="card-body">{body_txt}</div>
                </div>
                """
            else:
                feedback_section_html += f"""
                <div class="feedback-card">
                    <div class="card-header"><span class="card-nums">❌ 틀린 문제: {nums_str}</span></div>
                    <div class="card-body">{clean_msg}</div>
                </div>
                """
    else:
        feedback_section_html = """
        <div class="feedback-card" style="border-color: #4CAF50; background-color: #E8F5E9;">
            <h3 style="color: #2E7D32; margin:0;">🎉 완벽합니다!</h3>
            <p style="margin:10px 0 0 0;">약점이 없습니다. 훌륭한 실력입니다.</p>
        </div>
        """

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
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets 설정 필요")
        return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    try:
        return client.open("ExamResults").sheet1
    except:
        st.error("구글 시트 'ExamResults'를 찾을 수 없습니다.")
        return None

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

# --- [5] 메인 앱 ---
st.set_page_config(page_title="국어 모의고사 통합 시스템", page_icon="📚", layout="wide")
st.title("📚 국어 모의고사 통합 관리 시스템")

tab1, tab2, tab3 = st.tabs(["📝 시험 응시하기", "🔍 결과 조회", "📈 종합 기록부"])

# === [탭 1] 시험 응시 ===
with tab1:
    st.subheader("학년과 회차를 선택하세요.")
    col_g, col_r = st.columns(2)
    
    selected_grade = col_g.selectbox("학년 선택", list(EXAM_DB.keys()))
    available_rounds = list(EXAM_DB[selected_grade].keys())
    selected_round = col_r.selectbox("회차 선택", available_rounds)
    
    current_exam_data = EXAM_DB[selected_grade][selected_round]
    st.info(f"📢 현재 **{selected_grade} - {selected_round}** 응시 중입니다.")

    with st.form("exam_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름", placeholder="홍길동")
        student_id = c2.text_input("학번(ID)", placeholder="예: 10101")
        st.markdown("---")
        user_answers = {}
        cols = st.columns(4)
        sorted_keys = sorted(current_exam_data.keys())
        
        for i, q_num in enumerate(sorted_keys):
            col_idx = i % 4
            info = current_exam_data[q_num]
            with cols[col_idx]:
                # [핵심 수정] 입력창 라벨에서 [유형] 제거
                user_answers[q_num] = st.number_input(
                    f"{q_num}번 ({info['score']}점)", 
                    min_value=1, max_value=5, step=1, key=f"q_{selected_grade}_{selected_round}_{q_num}"
                )

        submit = st.form_submit_button("답안 제출하기", use_container_width=True)

    if submit:
        if not name or not student_id:
            st.error("이름과 학번을 입력하세요!")
        else:
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
                        input_id_clean = normalize(student_id)
                        dup = df[(df['Grade'] == str(selected_grade)) & (df['Round'] == str(selected_round)) & (df['ID_Clean'] == input_id_clean)]
                        if not dup.empty: is_duplicate = True
                except: pass

            if is_duplicate:
                st.error(f"⛔ **이미 제출된 기록이 있습니다.**")
                st.warning("결과 조회 탭에서 점수를 확인하세요.")
            else:
                total_score = 0
                wrong_list = [] # 여기엔 세부 유형 저장 (DB용)
                wrong_q_nums = []
                
                # 성적표용 그룹핑 변수
                grouped_wrong_map = {} 
                
                for q, info in current_exam_data.items():
                    if user_answers[q] == info['ans']:
                        total_score += info['score']
                    else:
                        q_type_detail = info['type']
                        wrong_list.append(q_type_detail)
                        wrong_q_nums.append(str(q))
                        
                        # [핵심] 세부 유형을 통합 카테고리로 변환하여 묶기
                        category = normalize_type(q_type_detail)
                        if category not in grouped_wrong_map:
                            grouped_wrong_map[category] = []
                        grouped_wrong_map[category].append(q)
                
                if sheet:
                    try:
                        wrong_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                        new_row = [selected_grade, selected_round, student_id, name, total_score, " | ".join(wrong_list), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wrong_q_str]
                        sheet.append_row(new_row)
                        
                        records = sheet.get_all_records()
                        df = pd.DataFrame(records)
                        df_filtered = df[(df['Grade'].astype(str).str.strip() == str(selected_grade)) & (df['Round'].astype(str).str.strip() == str(selected_round))]
                        rank = df_filtered[df_filtered['Score'] > total_score].shape[0] + 1
                        total_std = len(df_filtered)
                        
                        st.balloons()
                        
                        # 성적표 생성 (통합된 grouped_wrong_map 전달)
                        report = create_report_html(selected_grade, selected_round, name, total_score, rank, total_std, grouped_wrong_map, get_feedback_message)
                        
                        st.success("제출 완료! 성적표를 확인하세요.")
                        st.download_button("📥 성적표 즉시 다운로드", report, file_name="성적표.html", mime="text/html")
                        with st.expander("📱 모바일 저장 방법"): st.write("파일 열기 > 공유 > 인쇄 > PDF로 저장")
                    except Exception as e: st.error(f"저장 오류: {e}")

# === [탭 2] 결과 조회 ===
with tab2:
    st.header("🔍 성적표 조회")
    c_g, c_r = st.columns(2)
    chk_grade = c_g.selectbox("학년", list(EXAM_DB.keys()), key="chk_grade")
    chk_round = c_r.selectbox("회차", list(EXAM_DB[chk_grade].keys()), key="chk_round")
    chk_id = st.text_input("학번(ID) 입력", key="chk_id")
    
    if st.button("조회하기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                df['Grade'] = df['Grade'].astype(str).str.strip()
                df['Round'] = df['Round'].astype(str).str.strip()
                df['ID'] = df['ID'].astype(str)
                def normalize(val):
                    try: return str(int(val))
                    except: return str(val).strip()
                df['ID_Clean'] = df['ID'].apply(normalize)
                in_id = normalize(chk_id)
                
                my_data = df[(df['Grade'] == str(chk_grade)) & (df['Round'] == str(chk_round)) & (df['ID_Clean'] == in_id)]
                
                if not my_data.empty:
                    last_row = my_data.iloc[-1]
                    round_data = df[(df['Grade'] == str(chk_grade)) & (df['Round'] == str(chk_round))]
                    rank = round_data[round_data['Score'] > last_row['Score']].shape[0] + 1
                    total = len(round_data)
                    pct = (rank / total) * 100
                    
                    st.divider()
                    st.subheader(f"📢 {chk_grade} {last_row['Name']}님의 결과")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("점수", f"{int(last_row['Score'])}")
                    m2.metric("등수", f"{rank} / {total}")
                    m3.metric("상위", f"{pct:.1f}%")
                    
                    # [핵심] 틀린 번호를 바탕으로 유형 다시 묶기
                    current_db = EXAM_DB[chk_grade][chk_round]
                    grouped_wrong_map = {}
                    w_q_str = str(last_row.get('Wrong_Questions', '')).strip()
                    
                    if w_q_str and w_q_str != "없음":
                        w_nums = [int(x.strip()) for x in w_q_str.split(",") if x.strip().isdigit()]
                        st.error(f"❌ 틀린 문제: {w_q_str}번")
                        
                        for q_num in w_nums:
                            if q_num in current_db:
                                q_type_detail = current_db[q_num]['type']
                                # [핵심] 세부 유형 -> 통합 카테고리 변환
                                category = normalize_type(q_type_detail)
                                if category not in grouped_wrong_map:
                                    grouped_wrong_map[category] = []
                                grouped_wrong_map[category].append(q_num)
                    else:
                        st.success("⭕ 만점입니다!")

                    # 피드백 출력
                    if grouped_wrong_map:
                        st.markdown("---")
                        st.write("### 💡 유형별 오답 분석")
                        for category, nums in grouped_wrong_map.items():
                            nums_txt = ", ".join(map(str, nums))
                            msg = get_feedback_message(category)
                            
                            with st.expander(f"❌ {category} (틀린 문제: {nums_txt}번)", expanded=True):
                                st.markdown(msg)
                    elif w_q_str == "없음":
                         st.info("약점이 없습니다. 완벽합니다!")

                    # 다운로드
                    st.write("---")
                    report = create_report_html(chk_grade, chk_round, last_row['Name'], last_row['Score'], rank, total, grouped_wrong_map, get_feedback_message)
                    st.download_button("📥 성적표 다운로드", report, file_name="성적표.html", mime="text/html")
                else:
                    st.error("기록이 없습니다.")
            except Exception as e: st.error(f"오류: {e}")

# === [탭 3] 종합 기록부 ===
with tab3:
    st.header("📈 나만의 포트폴리오")
    p_grade = st.selectbox("학년 선택", list(EXAM_DB.keys()), key="p_grade")
    p_id = st.text_input("학번(ID) 입력", key="p_id")
    if st.button("종합 분석 보기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                df['ID'] = df['ID'].astype(str)
                def normalize(val):
                    try: return str(int(val))
                    except: return str(val).strip()
                df['ID_Clean'] = df['ID'].apply(normalize)
                clean_p_id = normalize(p_id)
                
                my_hist = df[(df['Grade'].astype(str).str.strip() == str(p_grade)) & (df['ID_Clean'] == clean_p_id)]
                
                if not my_hist.empty:
                    st.success(f"**{p_grade} {my_hist.iloc[-1]['Name']}**님의 성장 기록")
                    c = alt.Chart(my_hist).mark_line(point=True).encode(x='Round', y=alt.Y('Score', scale=alt.Scale(domain=[0, 100])))
                    st.altair_chart(c, use_container_width=True)
                    st.dataframe(my_hist[['Round', 'Score', 'Wrong_Types']])
                else: st.warning("기록이 없습니다.")
            except Exception as e: st.error(f"오류: {e}")
