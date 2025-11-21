import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

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
    
# --- [추가] 종합 포트폴리오 HTML 생성 함수 ---
def create_portfolio_html(grade, name, total_count, avg_score, max_score, weakness_data, history_df):
    now = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 1. 취약점 HTML 생성
    weakness_html = ""
    if weakness_data:
        for rank, (w_type, count, clean_msg) in enumerate(weakness_data):
            weakness_html += f"""
            <div class='section-box'>
                <div class='box-title'>
                    <span class='rank-badge'>{rank+1}위</span> {w_type} (총 {count}회 오답)
                </div>
                <div class='box-content'>{clean_msg}</div>
            </div>
            """
    else:
        weakness_html = "<div style='padding:20px; text-align:center;'>🎉 완벽합니다! 발견된 약점이 없습니다.</div>"

    # 2. 히스토리 테이블 HTML 생성
    history_rows = ""
    # 최신순 정렬되어 있다고 가정
    for idx, row in history_df.iterrows():
        wrong_summary = row['Wrong_Types'] if row['Wrong_Types'] else "없음 (만점)"
        history_rows += f"""
        <tr>
            <td>{row['Round']}</td>
            <td>{row['Timestamp'].split(' ')[0]}</td> <td><b style='color:#D32F2F;'>{int(row['Score'])}점</b></td>
            <td style='text-align:left; font-size:12px;'>{wrong_summary}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>{name} 종합 포트폴리오</title>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; padding: 30px; color: #333; }}
            .paper {{ max-width: 800px; margin: 0 auto; border: 2px solid #444; padding: 40px; }}
            h1 {{ text-align: center; border-bottom: 3px solid #444; padding-bottom: 10px; margin-bottom: 10px; }}
            .sub-title {{ text-align: center; margin-bottom: 30px; color: #666; font-size: 14px; }}
            
            /* 요약 통계 박스 */
            .stats-container {{ display: flex; justify-content: space-between; margin-bottom: 30px; background: #f9f9f9; padding: 15px; border-radius: 8px; }}
            .stat-item {{ text-align: center; width: 30%; }}
            .stat-label {{ font-size: 12px; color: #666; }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #333; }}
            
            /* 섹션 스타일 */
            h2 {{ border-left: 5px solid #D32F2F; padding-left: 10px; margin-top: 30px; font-size: 20px; }}
            
            /* 취약점 박스 */
            .section-box {{ border: 1px solid #ccc; margin-bottom: 15px; break-inside: avoid; page-break-inside: avoid; }}
            .box-title {{ background: #eee; padding: 8px 15px; font-weight: bold; border-bottom: 1px solid #ccc; }}
            .rank-badge {{ background: #D32F2F; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-right: 5px; }}
            .box-content {{ padding: 15px; font-size: 13px; line-height: 1.5; }}
            
            /* 표 스타일 */
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
            th {{ background: #f4f4f4; border-bottom: 2px solid #999; padding: 8px; }}
            td {{ border-bottom: 1px solid #ddd; padding: 8px; text-align: center; }}
            
            .footer {{ text-align: center; margin-top: 50px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <h1>📈 사계국어 학습 종합 분석 보고서</h1>
            <div class="sub-title">수험자: {grade} <b>{name}</b> | 작성일: {now}</div>
            
            <div class="stats-container">
                <div class="stat-item">
                    <div class="stat-label">총 응시</div>
                    <div class="stat-value">{total_count}회</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">평균 점수</div>
                    <div class="stat-value">{avg_score:.1f}점</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">최고 점수</div>
                    <div class="stat-value" style="color:#D32F2F;">{int(max_score)}점</div>
                </div>
            </div>

            <h2>2️⃣ 누적 약점 및 처방 (TOP 3)</h2>
            <p style="font-size:13px; color:#666;">데이터 분석 결과, 가장 많이 틀린 유형에 대한 맞춤 처방입니다.</p>
            {weakness_html}

            <h2>3️⃣ 전체 응시 이력</h2>
            <table>
                <thead>
                    <tr>
                        <th width="15%">회차</th>
                        <th width="20%">응시일</th>
                        <th width="15%">점수</th>
                        <th>오답 유형 요약</th>
                    </tr>
                </thead>
                <tbody>
                    {history_rows}
                </tbody>
            </table>
            
            <div class="footer">Designed by AI Teacher | 본 리포트는 학생의 학습 지도를 위한 참고 자료입니다.</div>
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
# --- [4] 피드백 및 강점 함수 (초정밀 버전) ---
def get_feedback_message(question_type):
    # ---------------------------------------------------------
    # [1] 비문학 (독서) 세부 영역
    # ---------------------------------------------------------
    if "철학" in question_type or "인문" in question_type:
        return """### 🧠 [심층 분석] 인문/철학: 사상가의 '관점'을 비교하세요.

**1. 진단: 왜 틀렸을까요?**
철학 지문은 정보량보다는 **'관점의 차이'**를 묻습니다. A학자와 B학자의 주장이 섞였거나, 용어(개념)의 정의를 정확히 잡지 못해 선택지에서 혼란을 겪은 것입니다.

**2. 핵심 공략법**
* **이항 대립:** 지문에 두 명 이상의 사상가가 나오면 무조건 `A vs B` 또는 `A -> B(계승/반박)` 구조를 파악해야 합니다.
* **개념 정의:** 학자가 말하는 핵심 키워드(예: 이기론, 절대정신)의 뜻을 밑줄 긋고 시작하세요.

**3. Action Plan**
1. 지문 옆에 학자 이름(A, B)을 쓰고 그들의 **공통점**과 **차이점**을 표로 메모하며 읽으세요.
2. '그러나', '반면' 뒤에 나오는 문장이 문제의 정답이 됩니다. 접속어에 세모 표시하세요."""

    elif "경제" in question_type or "사회" in question_type or "법" in question_type:
        return """### 📈 [심층 분석] 사회/경제: '인과 관계'와 '변수'를 잡으세요.

**1. 진단: 왜 틀렸을까요?**
경제 지문은 글로 쓰인 **수학 문제**입니다. 환율, 금리, 물가 등 변수들이 움직일 때 결괏값이 커지는지(비례) 작아지는지(반비례) 그 **메커니즘**을 놓쳤기 때문입니다.

**2. 핵심 공략법**
* **화살표 메모:** 지문을 눈으로만 읽지 말고, 여백에 `금리(↑) → 투자(↓) → 소득(↓)` 처럼 화살표로 인과 관계를 도식화해야 합니다.
* **그래프 해석:** 그래프가 나오면 X축과 Y축의 변수가 무엇인지, 곡선의 기울기가 무엇을 의미하는지 먼저 확인하세요.

**3. Action Plan**
1. 틀린 지문을 다시 펴고, 모든 인과 관계 문장 옆에 화살표(↑, ↓)를 표시해 보세요.
2. <보기>의 사례에 지문의 원리를 대입할 때는 주어와 서술어를 정확히 매칭하세요."""

    elif "과학" in question_type or "기술" in question_type or "건축" in question_type:
        return """### ⚙️ [심층 분석] 과학/기술: '작동 원리'와 '과정'을 시각화하세요.

**1. 진단: 왜 틀렸을까요?**
기술 지문은 낯선 장치의 **구조**와 **작동 순서**를 설명합니다. 1문단에 나온 부품의 이름과 역할을 기억하지 못한 채, 복잡한 작동 과정을 읽으려니 정보가 꼬인 것입니다.

**2. 핵심 공략법**
* **구성 요소:** 'A는 a, b, c로 구성된다'라는 문장이 나오면 각각 동그라미 치고 번호를 매기세요.
* **순서 파악:** '먼저 ~하고, 그 후 ~한다' 같은 과정 서술에 민감해야 합니다. 단계별로 끊어 읽으세요.

**3. Action Plan**
1. 지문을 읽으며 여백에 장치의 구조를 간단한 그림이나 모형으로 그려보세요.
2. 작동 순서가 나오는 문단에는 문장마다 ①, ②, ③ 번호를 매겨 프로세스를 분리하세요."""

    # ---------------------------------------------------------
    # [2] 문법 (언어) 세부 영역
    # ---------------------------------------------------------
    elif "음운" in question_type:
        return """### 🛑 [긴급 처방] 문법: '음운 변동'의 환경을 암기하세요.

**1. 진단**
단순히 발음해보고 감으로 풀면 무조건 틀립니다. '교체, 탈락, 첨가, 축약'이 일어나는 **음운 환경(조건)**을 정확히 외우지 못했습니다.

**2. Action Plan**
1. **비음화/유음화/구개음화**가 일어나는 앞뒤 자음 조건을 백지에 써보세요.
2. 틀린 단어의 발음 과정을 `국물 → [궁물] (ㄱ→ㅇ, 비음화, 교체)` 처럼 3단계로 분석하는 연습을 하세요."""

    elif "문장" in question_type or "문법" in question_type: # 문장 구조 등
        return """### 🏗️ [심층 분석] 문법: 문장의 '뼈대'를 해부하세요.

**1. 진단**
문장이 길어지거나 안긴문장이 숨어있을 때, 주어와 서술어의 호응을 찾지 못했습니다. 문장 성분 분석 훈련이 부족합니다.

**2. Action Plan**
1. 지문 속 문장의 **서술어**를 먼저 찾고 밑줄을 그으세요.
2. 그 서술어의 주어가 무엇인지 찾아 연결하고, `-(으)ㄴ/는` 같은 관형사형 어미에 네모 박스를 치세요."""

    elif "중세" in question_type or "국어사전" in question_type:
        return """### 📜 [심층 분석] 문법: 중세 국어는 '숨은그림찾기'입니다.

**1. 진단**
중세 국어 표기가 낯설어 겁을 먹었습니다. 하지만 이 유형은 지식보다는 **현대어 풀이와의 일대일 대응 능력**을 묻습니다.

**2. Action Plan**
1. 문제에 나온 고어(옛말) 바로 밑에 현대어 풀이를 한 단어씩 짝지어 적으세요.
2. 주격조사(이/ㅣ), 관형격조사(ㅅ) 등 조사의 쓰임새 차이만 발견하면 정답이 보입니다."""

    # ---------------------------------------------------------
    # [3] 화법과 작문
    # ---------------------------------------------------------
    elif "강연" in question_type or "말하기" in question_type or "화법" in question_type:
        return """### 🗣️ [심층 분석] 화법: 강연자의 '전략'을 꿰뚫어 보세요.

**1. 진단**
내용 일치(Fact) 확인에만 급급했습니다. 화법은 '무엇을' 말했냐보다, 청중을 위해 **'어떻게(전략)'** 말했냐를 묻습니다.

**2. Action Plan**
1. '질문을 통해', '자료를 제시하며', '전문가를 인용하여' 같은 **방식**을 묻는 선지를 먼저 확인하세요.
2. 지문 속 `(웃으며)`, `(자료를 가리키며)` 같은 괄호 지시문이 정답의 핵심 단서입니다."""

    elif "작문" in question_type or "고쳐쓰기" in question_type or "글쓰기" in question_type:
        return """### ✍️ [심층 분석] 작문: '조건'을 모두 충족해야 정답입니다.

**1. 진단**
<보기>에 제시된 조건이 2~3개일 때, 그중 하나만 보고 급하게 답을 골랐습니다. 작문은 꼼꼼함 싸움입니다.

**2. Action Plan**
1. 문제의 <조건>에 번호를 매기세요. (예: ①비유법 사용, ②설의법 사용)
2. 선지를 볼 때 ①번 조건 통과? ②번 조건 통과? 하나씩 지워가며 소거법으로 푸세요."""

    # ---------------------------------------------------------
    # [4] 문학 세부 영역
    # ---------------------------------------------------------
    elif "소설" in question_type or "각본" in question_type or "서사" in question_type:
        return """### 🎭 [심층 분석] 문학(산문): 인물 관계도와 갈등을 잡으세요.

**1. 진단**
지엽적인 문장에 집착하다가 전체 줄거리와 **'누가 누구와 싸우는지(갈등)'**를 놓쳤습니다.

**2. Action Plan**
1. 긍정적 인물(O)과 부정적 인물(X)을 표시하며 읽으세요.
2. 장면이 바뀌는 부분(중략, 다음 날 등)에서 끊고, 사건을 한 줄로 요약해 보세요."""

    elif "시가" in question_type or "시어" in question_type or "작품" in question_type or "운문" in question_type:
        return """### 🌙 [심층 분석] 문학(운문): 화자의 '상황'과 '정서'만 찾으세요.

**1. 진단**
시를 너무 주관적으로 해석했습니다. 수능 시는 '숨은 의미 찾기'가 아니라 **객관적인 상황 정보** 찾기입니다.

**2. Action Plan**
1. 화자가 처한 상황(이별, 가난, 자연 등)에 밑줄을 그으세요.
2. 감정을 나타내는 단어(슬픔, 외로움, 즐거움)에 형광펜을 칠하고, 긍정(+)인지 부정(-)인지 기호를 표시하세요."""

    # ---------------------------------------------------------
    # [5] 고난도 / 기타
    # ---------------------------------------------------------
    elif "적용" in question_type or "보기" in question_type:
        return """### 🔥 [심층 분석] 고난도: <보기>는 또 하나의 지문입니다.

**1. 진단**
지문의 원리와 <보기>의 사례를 연결(Mapping)하지 못했습니다. 따로따로 생각하면 절대 풀리지 않습니다.

**2. Action Plan**
1. 선지의 단어가 지문의 몇 번째 문단에서 왔는지 근거를 찾으세요.
2. <보기>의 구체적 사례를 지문의 핵심 개념어로 바꿔서 읽는 연습(치환)이 필수입니다."""

    else:
        return """### ⚠️ [종합 진단] 기초 독해력 점검이 필요합니다.

**1. 진단**
해당 유형은 국어의 가장 기초적인 어휘력이나 사실적 독해력이 부족하여 발생한 실수일 수 있습니다.

**2. Action Plan**
1. 문제를 풀 때 너무 급하게 풀지 않았는지 점검하세요.
2. 해설지를 펴고 정답인 이유보다 **'오답이 왜 오답인지'**를 남에게 설명하듯 분석해 보세요."""


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

# === [탭 3] 종합 기록부 (관리자 전용 + 포트폴리오 다운로드) ===
with tab3:
    st.header("📈 포트폴리오")
    
    if not is_admin:
        st.error("⛔ **접근 권한이 없습니다.**")
        st.info("종합 기록부는 선생님만 열람할 수 있습니다.")
        st.stop()

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
                
                my_hist = df[(df['Grade']==str(pg)) & (df['ID_Clean']==in_id)]
                
                if not my_hist.empty:
                    student_name = my_hist.iloc[-1]['Name']
                    st.success(f"**{pg} {student_name}**님의 성장 기록입니다.")
                    
                    avg_score = my_hist['Score'].mean()
                    max_score = my_hist['Score'].max()
                    total_count = len(my_hist)
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("총 응시", f"{total_count}회")
                    m2.metric("평균 점수", f"{avg_score:.1f}점")
                    m3.metric("최고 점수", f"{int(max_score)}점")
                    
                    st.markdown("### 1️⃣ 성적 변화 추이")
                    chart = alt.Chart(my_hist).mark_line(point=True).encode(
                        x=alt.X('Round', sort=None, title='시험 회차'),
                        y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]), title='점수'),
                        tooltip=['Round', 'Score']
                    ).properties(height=300)
                    st.altair_chart(chart, use_container_width=True)
                    
                    # --- 누적 약점 분석 ---
                    st.markdown("---")
                    st.markdown("### 2️⃣ 누적 취약점 분석 (TOP 3)")
                    
                    all_wrong_types = []
                    for idx, row in my_hist.iterrows():
                        if str(row['Wrong_Types']).strip():
                            types = str(row['Wrong_Types']).split(" | ")
                            all_wrong_types.extend(types)
                    
                    weakness_report_data = [] # 리포트 생성용 데이터 저장 리스트
                    
                    if all_wrong_types:
                        from collections import Counter
                        counts = Counter(all_wrong_types)
                        sorted_counts = counts.most_common()
                        
                        col_list, col_feedback = st.columns([1, 1.5])
                        
                        with col_list:
                            st.write("📉 **많이 틀린 유형**")
                            for i, (w_type, count) in enumerate(sorted_counts[:3]):
                                icon = ["🥇", "🥈", "🥉"][i]
                                st.write(f"{icon} **{w_type}** ({count}회)")
                        
                        with col_feedback:
                            st.info("💡 **맞춤 처방전**")
                            for i, (w_type, count) in enumerate(sorted_counts[:3]):
                                raw_msg = get_feedback_message(w_type)
                                
                                # 화면 출력
                                with st.expander(f"클릭: {w_type} 처방", expanded=(i==0)):
                                    st.markdown(raw_msg)
                                
                                # [리포트용 데이터 준비] 마크다운 -> HTML 변환
                                clean_msg = raw_msg.strip().replace(">", "💡").replace("**", "").replace("-", "•").replace("\n", "<br>")
                                if clean_msg.startswith("###"):
                                    parts = clean_msg.split("<br>", 1)
                                    title = parts[0].replace("###", "").strip()
                                    body = parts[1] if len(parts) > 1 else ""
                                    clean_msg = f"<div style='font-weight:bold; margin-bottom:5px;'>{title}</div><div>{body}</div>"
                                
                                weakness_report_data.append((w_type, count, clean_msg))
                    else:
                        st.success("약점이 없습니다.")

                    # --- 상세 기록 및 다운로드 ---
                    st.markdown("---")
                    st.markdown("### 3️⃣ 응시 기록 및 저장")
                    
                    history_view = my_hist[['Round', 'Score', 'Timestamp', 'Wrong_Types']].copy()
                    history_view.columns = ['회차', '점수', '응시일시', '틀린 유형']
                    st.dataframe(history_view)
                    
                    # [NEW] 포트폴리오 다운로드 버튼
                    portfolio_html = create_portfolio_html(
                        pg, student_name, total_count, avg_score, max_score, 
                        weakness_report_data, my_hist
                    )
                    
                    st.download_button(
                        label="📥 종합 포트폴리오 다운로드 (PDF 저장용)",
                        data=portfolio_html,
                        file_name=f"{student_name}_종합분석보고서.html",
                        mime="text/html"
                    )
                    with st.expander("📱 모바일 저장 방법"):
                        st.write("파일 열기 > 공유 > 인쇄 > PDF로 저장")
                    
                else:
                    st.warning("응시 기록이 없습니다.")
            except Exception as e: st.error(f"오류: {e}")
