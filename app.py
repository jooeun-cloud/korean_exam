import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt # 그래프 그리는 도구

# --- [1] 문제 데이터베이스 (회차별 관리) ---
# 여기에 2회차, 3회차 데이터를 계속 추가하시면 됩니다.
EXAM_DB = {
    "1회차": {
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
    },
    
    "2회차 (예시)": { 
        # 2회차 문제 예시 (형식 똑같이 맞춰서 추가하면 됨)
        1: {"ans": 1, "score": 3, "type": "화법"},
        2: {"ans": 2, "score": 3, "type": "작문"},
        3: {"ans": 3, "score": 4, "type": "문법"},
        # ... 필요한 만큼 추가 ...
    }
}


# --- [2] 성적표 HTML 생성 함수 ---
def create_report_html(round_name, name, score, rank, total_students, wrong_q_nums, wrong_list, feedback_text):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    wrong_nums_str = ", ".join(wrong_q_nums) + "번" if wrong_q_nums else "없음 (만점)"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; }}
            .paper {{ max-width: 800px; margin: 0 auto; border: 2px solid #333; padding: 30px; }}
            h1 {{ text-align: center; border-bottom: 2px solid black; padding-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid black; padding: 10px; text-align: center; }}
            th {{ background-color: #f0f0f0; }}
            .score {{ font-size: 32px; font-weight: bold; color: black; }}
            .feedback-box {{ border: 1px solid black; padding: 15px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <h1>📑 {round_name} 국어 모의고사 성적표</h1>
            <table>
                <tr><th>이 름</th><td>{name}</td><th>응시일</th><td>{now}</td></tr>
                <tr><th>점 수</th><td><span class="score">{int(score)}</span> 점</td><th>등 수</th><td>{rank} / {total_students}</td></tr>
            </table>
            <div style="border: 1px solid black; padding: 15px; margin-bottom: 20px;">
                <strong>[ 틀린 문제 번호 ]</strong><br>{wrong_nums_str}
            </div>
            <h3>💊 유형별 상세 처방</h3>
            {feedback_text}
            <div style="text-align: center; margin-top: 30px; font-size: 12px;">Designed by AI Teacher</div>
        </div>
    </body>
    </html>
    """
    return html

# --- [3] 구글 시트 연결 ---
def get_google_sheet_data():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets 설정이 필요합니다.")
        return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    try:
        return client.open("ExamResults").sheet1
    except:
        st.error("구글 시트 'ExamResults'를 찾을 수 없습니다.")
        return None

# --- [4] 피드백 함수 (아까 그 긴 버전) ---
# (여기에 아까 작성해드린 긴 get_feedback_message 함수를 그대로 넣으세요)
# (여기에 아까 작성해드린 get_strength_message 함수를 그대로 넣으세요)
# **중요: 코드 길이상 생략했습니다. 아까 쓰시던 함수 그대로 복사해서 쓰시면 됩니다.**
def get_feedback_message(question_type):
    return "📝 상세 피드백 내용이 여기에 들어갑니다. (이전 코드의 내용을 복사해서 넣으세요)" 

def get_strength_message(question_type):
    return "💎 강점 분석 내용이 여기에 들어갑니다."


# --- [5] 메인 앱 ---
st.set_page_config(page_title="국어 모의고사 통합 시스템", page_icon="📚", layout="wide")
st.title("📚 국어 모의고사 통합 관리 시스템")

# 탭 구성: 1.시험응시 / 2.이번회차 결과 / 3.나의 종합기록부(NEW)
tab1, tab2, tab3 = st.tabs(["📝 시험 응시하기", "🔍 이번 결과 조회", "📈 나의 종합 기록부"])

# === [탭 1] 시험 응시 ===
with tab1:
    st.subheader("응시할 시험을 선택하세요.")
    
    # 회차 선택 기능
    selected_round = st.selectbox("시험 회차 선택", list(EXAM_DB.keys()))
    current_exam_data = EXAM_DB[selected_round]
    
    with st.form("exam_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("이름", placeholder="홍길동")
        student_id = c2.text_input("학번(ID)", placeholder="예: 10101")
        
        st.markdown("---")
        user_answers = {}
        
        # 문제 동적 생성
        # (화면 배치를 위해 4열로 나눔)
        cols = st.columns(4)
        sorted_keys = sorted(current_exam_data.keys()) # 문제 번호 순서대로
        
        for i, q_num in enumerate(sorted_keys):
            col_idx = i % 4
            info = current_exam_data[q_num]
            with cols[col_idx]:
                user_answers[q_num] = st.number_input(
                    f"{q_num}번 ({info['score']}점)", 
                    min_value=1, max_value=5, step=1, key=f"q_{selected_round}_{q_num}"
                )

        submit = st.form_submit_button("답안 제출하기", use_container_width=True)

    if submit:
        if not name or not student_id:
            st.error("이름과 학번을 입력하세요!")
        else:
            total_score = 0
            wrong_list = []
            wrong_q_nums = []
            
            for q, info in current_exam_data.items():
                if user_answers[q] == info['ans']:
                    total_score += info['score']
                else:
                    wrong_list.append(info['type'])
                    wrong_q_nums.append(str(q))
            
            sheet = get_google_sheet_data()
            if sheet:
                try:
                    wrong_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                    
                    # [수정] A열에 selected_round(회차) 추가
                    new_row = [
                        selected_round, # A열: 회차
                        student_id,     # B열: ID
                        name, 
                        total_score, 
                        " | ".join(wrong_list), 
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        wrong_q_str
                    ]
                    sheet.append_row(new_row)
                    
                    st.balloons()
                    st.success(f"{name}님, {selected_round} 답안이 제출되었습니다! [이번 결과 조회] 탭에서 확인하세요.")
                    
                except Exception as e:
                    st.error(f"저장 오류: {e}")

# === [탭 2] 결과 조회 (특정 회차) ===
with tab2:
    st.header("🔍 회차별 결과 조회")
    col_a, col_b = st.columns(2)
    check_round = col_a.selectbox("확인할 회차", list(EXAM_DB.keys()), key="check_round")
    check_id = col_b.text_input("학번(ID) 입력", key="check_id_tab2")
    
    if st.button("결과 확인하기"):
        sheet = get_google_sheet_data()
        if sheet:
            records = sheet.get_all_records()
            df = pd.DataFrame(records)
            df['ID'] = df['ID'].astype(str)
            
            # 회차와 ID가 모두 일치하는 데이터 찾기
            my_data = df[(df['ID'] == check_id) & (df['Round'] == check_round)]
            
            if not my_data.empty:
                # 같은 회차를 여러번 쳤으면 가장 최신 것만
                last_row = my_data.iloc[-1]
                
                # 해당 회차 전체 응시자 데이터 (등수 계산용)
                round_data = df[df['Round'] == check_round]
                rank = round_data[round_data['Score'] > last_row['Score']].shape[0] + 1
                total_std = len(round_data)
                pct = (rank / total_std) * 100
                
                st.divider()
                st.subheader(f"📢 {last_row['Name']}님의 {check_round} 결과")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("점수", f"{int(last_row['Score'])}점")
                m2.metric("등수", f"{rank}등 / {total_std}명")
                m3.metric("상위", f"{pct:.1f}%")
                
                # 틀린 문제 출력 (A열이 추가되어 컬럼 위치 조심)
                w_q = str(last_row['Wrong_Questions'])
                if w_q and w_q != "없음":
                    st.error(f"❌ 틀린 문제: {w_q}번")
                else:
                    st.success("⭕ 만점입니다!")
                
                # 피드백 출력 (약식 구현)
                w_types = str(last_row['Wrong_Types']).split(" | ") if str(last_row['Wrong_Types']) else []
                
                final_html = ""
                if w_types:
                    st.warning("보완이 필요한 부분")
                    unique_fb = set(get_feedback_message(w) for w in w_types)
                    for msg in unique_fb:
                        st.write(msg)
                        final_html += f"<div>{msg}</div>"
                else:
                    final_html = "<div>완벽합니다!</div>"
                
                # 성적표 다운로드
                st.write("---")
                w_nums_list = w_q.split(", ") if w_q != "없음" else []
                report = create_report_html(check_round, last_row['Name'], last_row['Score'], rank, total_std, w_nums_list, w_types, final_html)
                st.download_button("📥 성적표 다운로드", report, file_name=f"{check_round}_성적표.html", mime="text/html")

            else:
                st.error("해당 회차의 응시 기록이 없습니다.")

# === [탭 3] 나의 종합 기록부 (NEW!) ===
with tab3:
    st.header("📈 종합 학습 분석 (포트폴리오)")
    st.write("지금까지 응시한 모든 시험 결과를 모아서 분석해 드립니다.")
    
    port_id = st.text_input("학번(ID) 입력", key="port_id")
    
    if st.button("종합 분석 시작"):
        sheet = get_google_sheet_data()
        if sheet:
            records = sheet.get_all_records()
            df = pd.DataFrame(records)
            df['ID'] = df['ID'].astype(str)
            
            # 내 모든 기록 가져오기
            my_history = df[df['ID'] == port_id]
            
            if not my_history.empty:
                st.success(f"**{my_history.iloc[0]['Name']}**님의 학습 데이터를 불러왔습니다.")
                
                # 1. 성적 변화 그래프
                st.subheader("1️⃣ 성적 변화 추이")
                
                # 그래프를 위해 데이터 정리
                chart_data = my_history[['Round', 'Score']].copy()
                # Round 문자열("1회차")을 그대로 X축으로 씁니다.
                
                # Altair 차트 그리기 (선 그래프 + 점)
                c = alt.Chart(chart_data).mark_line(point=True).encode(
                    x=alt.X('Round', sort=None, title='시험 회차'),
                    y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]), title='점수'),
                    tooltip=['Round', 'Score']
                ).properties(height=300)
                
                st.altair_chart(c, use_container_width=True)
                
                # 2. 평균 점수 및 요약
                avg_score = my_history['Score'].mean()
                max_score = my_history['Score'].max()
                st.info(f"📊 **총 {len(my_history)}회** 응시 | 평균 점수: **{avg_score:.1f}점** | 최고 점수: **{max_score}점**")
                
                # 3. 취약 유형 누적 분석 (워드 클라우드 느낌)
                st.subheader("2️⃣ 누적 약점 분석 (자주 틀리는 유형)")
                
                all_wrong_types = []
                for idx, row in my_history.iterrows():
                    if row['Wrong_Types']:
                        types = str(row['Wrong_Types']).split(" | ")
                        all_wrong_types.extend(types)
                
                if all_wrong_types:
                    # 많이 틀린 순서대로 정렬
                    from collections import Counter
                    counts = Counter(all_wrong_types)
                    sorted_counts = counts.most_common()
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write("📉 **가장 많이 틀린 유형 TOP 3**")
                        for i, (w_type, count) in enumerate(sorted_counts[:3]):
                            st.write(f"**{i+1}위:** {w_type} ({count}회)")
                    
                    with col2:
                        st.write("💡 **AI 총평**")
                        worst_type = sorted_counts[0][0]
                        st.write(f"""
                        데이터 분석 결과, **'{worst_type}'** 유형에서 실수가 가장 잦습니다.
                        점수 상승을 위해 다음 시험 전까지 이 파트를 집중 공략하는 것을 추천합니다.
                        """)
                else:
                    st.success("지금까지 틀린 문제가 하나도 없습니다! 완벽합니다.")
                
                # 4. 히스토리 표
                st.subheader("3️⃣ 응시 기록 상세")
                st.dataframe(my_history[['Round', 'Score', 'Timestamp', 'Wrong_Types']].style.format({"Score": "{:.0f}"}))

            else:
                st.warning("응시 기록이 없습니다.")
