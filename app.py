import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# --- [1] 문제 데이터베이스 (학년 > 회차 > 문제) ---
# 이제 제일 상위 카테고리가 '학년'이 됩니다.
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
            # 1학년 2회차 문제...
            1: {"ans": 1, "score": 50, "type": "테스트"},
            2: {"ans": 1, "score": 50, "type": "테스트"},
        }
    },
    
    "2학년": {
        "1회차": {
            # 2학년 1회차 문제...
            1: {"ans": 3, "score": 50, "type": "독서"},
            2: {"ans": 3, "score": 50, "type": "문학"},
        }
    },
    
    "3학년": {
        # 3학년 문제...
        "1회차": {
            # 2학년 1회차 문제...
            1: {"ans": 3, "score": 50, "type": "독서"},
            2: {"ans": 3, "score": 50, "type": "문학"},
        }
    }
}

# --- [2] 성적표 HTML 생성 함수 (한글깨짐 방지 + 디자인) ---
def create_report_html(grade, round_name, name, score, rank, total_students, wrong_q_nums, wrong_list, feedback_text):
    now = datetime.now().strftime("%Y년 %m월 %d일 %H시 %M분")
    wrong_nums_str = ", ".join(wrong_q_nums) + "번" if wrong_q_nums else "없음 (만점)"

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{name} 성적표</title>
        <style>
            body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; }}
            .paper {{ max-width: 800px; margin: 0 auto; border: 2px solid #333; padding: 30px; }}
            h1 {{ text-align: center; border-bottom: 2px solid black; padding-bottom: 15px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid black; padding: 10px; text-align: center; }}
            th {{ background-color: #f8f9fa; width: 20%; font-weight: bold; }}
            .score {{ font-size: 32px; font-weight: bold; }}
            .score-box {{ border: 1px solid black; padding: 15px; margin-bottom: 20px; }}
            .feedback-box {{ border: 1px solid black; padding: 5px 10px; margin-bottom: 10px; font-size: 13px; line-height: 1.4; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #555; }}
        </style>
    </head>
    <body>
        <div class="paper">
            <h1>📑 {grade} {round_name} 국어 성적표</h1>
            <table>
                <tr><th>이 름</th><td>{name}</td><th>응시일</th><td>{now}</td></tr>
                <tr><th>점 수</th><td><span class="score">{int(score)}</span> 점</td><th>등 수</th><td>{rank}등 / {total_students}명</td></tr>
            </table>
            <div class="score-box">
                <strong>[ 틀린 문제 번호 ]</strong><br>
                <div style="margin-top:5px; font-size:18px;">{wrong_nums_str}</div>
            </div>
            <h3>💊 유형별 상세 처방</h3>
            {feedback_text}
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

# --- [4] 피드백 함수 (선생님의 긴 피드백 그대로 사용) ---
def get_feedback_message(question_type):
    # =================================================================
    # [1] 문법 (음운, 통사, 국어사)
    # =================================================================
    if "음운" in question_type:
        return """
### 🛑 [긴급 처방] 문법: '음운 변동'의 원리를 놓치고 있습니다.

**1. 진단: 왜 틀렸을까요?**
단순히 단어를 발음해보고 감으로 답을 찾으려 했거나, '교체, 탈락, 첨가, 축약'의 개념이 머릿속에서 뒤섞여 있기 때문입니다. 음운 변동은 발음 습관이 아니라 **엄격한 음운 환경의 법칙**입니다.

**2. 핵심 개념 정리 (이것만은 꼭!)**
* **교체:** 비음화, 유음화, 구개음화, 된소리되기, 음절의 끝소리 규칙 (개수 변화 없음)
* **탈락:** 자음군 단순화, ㄹ탈락, ㅎ탈락, 으탈락 (의문 개수 -1)
* **첨가:** ㄴ첨가 (의문 개수 +1)
* **축약:** 거센소리되기 (자음 축약) (의문 개수 -1)

**3. 구체적인 행동 지침 (Action Plan)**
1.  **백지 복습:** 교과서를 덮고 위 4가지 카테고리에 해당하는 세부 규칙들을 안 보고 적을 수 있는지 테스트하세요. 못 적으면 모르는 것입니다.
2.  **환경 분석:** 특히 '비음화'가 일어나는 조건(파열음 뒤에 비음이 올 때 등)을 예시 단어 3개와 함께 정리하세요.
3.  **도식화 훈련:** 틀린 단어를 놓고 `국물 -> [궁물] (ㄱ->ㅇ, 비음화, 교체)` 처럼 **[변화 양상 / 규칙 이름 / 변동 유형]** 3단계를 적는 연습을 하세요.
"""

    elif "문장" in question_type or "문법" in question_type:
        return """
### 🏗️ [심층 분석] 문법: 문장의 '뼈대'를 보는 눈이 필요합니다.

**1. 진단: 왜 틀렸을까요?**
문장이 조금만 길어지거나 관형절이 숨어있으면 성분을 찾지 못하고 헤매는 경우입니다. '어미'와 '조사'를 보는 눈이 예민하지 못해서 문장이 어디서 끊어지는지 파악하지 못한 것입니다.

**2. 핵심 개념 정리**
* **안긴문장 찾기:** 문장 중간에 `-(으)ㄴ/는`(관형사형 어미), `-(으)ㅁ/기`(명사형 어미), `-게/도록`(부사형 어미)이 보이면 무조건 네모 박스를 치세요. 그게 바로 안긴문장입니다.
* **서술어 자릿수:** 서술어(동사/형용사)가 온전한 문장이 되기 위해 주어 외에 목적어나 부사어가 꼭 필요한지 판단해야 합니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **꼬리 찾기:** 오늘 틀린 지문의 모든 문장에서 **서술어**에 먼저 밑줄을 그으세요.
2.  **짝 짓기:** 그 서술어의 주어가 무엇인지 화살표로 연결하세요. (주어가 생략되었다면 괄호 치고 채워 넣으세요.)
3.  **성분 분석:** 문장 성분을 묻는 문제였다면, `이/가(주어)`, `을/를(목적어)`, `에/에게/로(부사어)` 등 격조사에 동그라미 치며 성분을 구별하세요.
"""

    elif "중세" in question_type or "국어사전" in question_type:
        return """
### 📜 [심층 분석] 문법: 중세 국어는 '다른 그림 찾기'입니다.

**1. 진단: 왜 틀렸을까요?**
중세 국어 표기가 낯설어서 겁을 먹었을 확률이 큽니다. 하지만 수능 국어에서 중세 국어는 고문 해독 능력을 묻는 게 아니라, **현대어 풀이와 비교하여 문법적인 차이를 발견하는 능력**을 묻습니다.

**2. 핵심 개념 정리**
* **조사의 차이:** 주격조사 `이` 외에 모음 뒤에 쓰인 `ㅣ`, 생략되는 경우를 구분해야 합니다. 관형격 조사 `ㅅ`의 쓰임도 단골 문제입니다.
* **객체 높임:** `삽, 잡, 압` 같은 선어말 어미가 누구를 높이는지(목적어, 부사어) 반드시 현대어 풀이와 대조해야 합니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **일대일 대응:** 문제에 나온 <보기> 지문(중세어) 바로 밑에 현대어 풀이를 한 단어씩 짝지어 적어보세요.
2.  **차이점 발견:** 형태가 다른 부분(예: '백셩이' vs '백성이')을 찾고, 왜 달라졌는지(이어적기 vs 끊어적기) 문법 용어로 설명해보세요.
3.  **개념어 암기:** 이어적기, 끊어적기, 거듭적기, 8종성법 등 기초 용어 10개를 노트에 정리하고 암기하세요.
"""

    # =================================================================
    # [2] 비문학 (철학, 경제, 기술/과학)
    # =================================================================
    elif "철학" in question_type or "인문" in question_type:
        return """
### 🧠 [심층 분석] 비문학(인문): 학자들의 '말싸움'을 정리하세요.

**1. 진단: 왜 틀렸을까요?**
글을 읽긴 읽었는데 머릿속에 남는 게 없다면, 정보가 **구조화**되지 않고 둥둥 떠다니기 때문입니다. 특히 철학 지문은 A학자와 B학자가 서로 다른 주장을 하거나, 시대가 흐르며 사상이 변하는 과정을 놓치면 문제를 풀 수 없습니다.

**2. 독해 전략 (Reading Strategy)**
* **이항 대립:** 지문에 두 가지 관점이 나오면 무조건 `A vs B` 구도로 나누어 읽으세요.
* **차이점 주목:** 두 학자가 동의하는 부분(공통 전제)과, 결정적으로 갈라지는 부분(차이점)이 문제의 정답이 됩니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **표 그리기:** 지문을 다 읽고 나서 빈 종이에 A학자와 B학자의 이름을 적고, 그들의 핵심 키워드(주장, 근거, 한계)를 표로 정리하세요.
2.  **접속사 체크:** '그러나', '반면', '오히려' 같은 역접 접속사에 세모 표시를 하세요. 그 뒤에 진짜 중요한 정보가 나옵니다.
3.  **단정적 표현 주의:** 선지에서 '반드시', '모든', '유일한' 같은 표현이 나오면, 지문에서 예외가 없었는지 의심의 눈초리로 확인하세요.
"""

    elif "경제" in question_type or "사회" in question_type:
        return """
### 📈 [심층 분석] 비문학(경제): '인과 관계'의 화살표를 그리세요.

**1. 진단: 왜 틀렸을까요?**
경제 지문은 텍스트로 된 **수학 문제**입니다. 환율이 오르면 수출이 어떻게 되고, 금리가 내리면 투자가 어떻게 되는지 그 **메커니즘(과정)**을 이해하지 못하고 글자만 읽었기 때문입니다.

**2. 독해 전략 (Reading Strategy)**
* **비례/반비례 표시:** 지문을 읽을 때 `금리(↑) -> 통화량(↓)` 처럼 변수 옆에 화살표를 반드시 표시하세요.
* **수식의 이해:** `A = B / C` 같은 수식 관계가 나오면, C가 커지면 A는 작아진다는 반비례 관계를 머릿속에 넣어야 합니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **관계도 그리기:** 오답 노트에 지문에 나온 경제 현상의 인과 관계를 화살표 도식으로 그려보세요. (원인 -> 결과1 -> 결과2)
2.  **그래프 해석:** 지문에 그래프가 있다면 X축(가로)과 Y축(세로)이 무엇을 의미하는지, 곡선이 우상향하는지 우하향하는지 먼저 파악하고 지문을 읽으세요.
3.  **가상 대입:** <보기> 문제에 구체적인 상황(예: A국가의 환율 폭등)이 나오면, 지문에서 정리한 화살표 공식에 그대로 대입해서 결과를 예측하세요.
"""

    elif "건축" in question_type or "기술" in question_type or "과학" in question_type:
        return """
### ⚙️ [심층 분석] 비문학(기술/과학): '작동 원리'를 시각화하세요.

**1. 진단: 왜 틀렸을까요?**
기술 지문은 어떤 장치의 **구조**와 **작동 순서**를 설명합니다. 틀린 이유는 1문단에 나온 부품의 이름과 역할을 기억하지 못한 채, 3문단의 복잡한 작동 과정을 읽으려 했기 때문입니다. 정보량이 쏟아질 때 '교통정리'를 실패한 것입니다.

**2. 독해 전략 (Reading Strategy)**
* **구성 요소 파악:** 'A장치는 a, b, c로 구성된다'라는 문장이 나오면 a, b, c에 각각 번호(①, ②, ③)를 매기고 동그라미 치세요.
* **순서 체크:** '먼저', '그 후', '마지막으로' 같은 순서 표지에 민감해야 합니다. 과정이 바뀌는 지점을 끊어 읽으세요.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **그림 그리기:** 지문 옆 여백에 장치의 구조를 간단한 그림이나 모형으로 그려보세요.
2.  **과정 번호 매기기:** 작동 원리가 설명된 문단에는 문장마다 ①, ②, ③ 번호를 매겨서 프로세스를 분할하세요.
3.  **인과성 확인:** 'A가 B를 누르면 C가 열린다'처럼 부품 간의 상호작용(인과)을 화살표로 연결하며 읽는 연습을 하세요.
"""

    # =================================================================
    # [3] 문학 (소설, 시가)
    # =================================================================
    elif "소설" in question_type or "각본" in question_type or "서사" in question_type:
        return """
### 🎭 [심층 분석] 문학(산문): 인물 관계도와 갈등을 잡으세요.

**1. 진단: 왜 틀렸을까요?**
소설은 '이야기'입니다. 내용을 틀렸다는 건 **누가, 누구에게, 왜 화를 내는지(갈등)** 그 맥락을 놓쳤다는 뜻입니다. 지엽적인 문장에 집착하다가 전체 줄거리의 흐름을 놓친 경우입니다.

**2. 독해 전략 (Reading Strategy)**
* **인물 표시:** 긍정적/아군 인물에는 `O`, 부정적/적군 인물에는 `X` 또는 `세모` 표시를 하며 읽으세요.
* **심리/태도 밑줄:** 인물의 기분을 나타내는 형용사나 부사, 대사에는 물결 밑줄(`~~~~`)을 그으세요. 그게 곧 문제의 정답 근거입니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **인물 관계도:** 지문을 다 읽고 중심 인물들을 적은 뒤, 서로 좋아하는지(화살표), 싫어하는지(번개표시 ⚡) 관계도를 그려보세요.
2.  **장면 끊기:** 소설은 '중략'이나 장소가 바뀌는 부분에서 장면이 전환됩니다. 장면별로 '누가', '무엇을 했나'를 한 줄로 요약하세요.
3.  **서술자 찾기:** '나'가 나오면 1인칭, 안 나오면 3인칭입니다. 서술자가 인물의 속마음까지 다 아는지(전지적), 관찰만 하는지 체크하세요.
"""

    elif "시가" in question_type or "시어" in question_type or "작품" in question_type:
        return """
### 🌙 [심층 분석] 문학(운문): 화자의 '상황'과 '정서'만 찾으세요.

**1. 진단: 왜 틀렸을까요?**
시를 너무 심오하게 해석하려 했거나, 자신의 주관적인 감정으로 읽었기 때문입니다. 수능 시 문학은 '숨은 의미 찾기'가 아니라, 텍스트에 드러난 **객관적인 상황 정보**를 찾는 게임입니다.

**2. 독해 전략 (Reading Strategy)**
* **주어 찾기:** 누가(화자가) 무엇을 보고 있는지 찾으세요.
* **상황 파악:** 이별 중인지, 자연 속에 있는지, 가난한 상황인지 팩트만 체크하세요.
* **정서/태도:** 그래서 슬픈가? 기쁜가? 의지적인가? 체념적인가? 시어 뒤에 숨은 서술어에서 힌트를 얻으세요.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **형광펜 칠하기:** 시를 읽으며 감정을 나타내는 단어(슬픔, 눈물, 외로움, 즐거움 등)에만 형광펜을 칠해 보세요. 그것만 연결해도 주제가 나옵니다.
2.  **시어의 기호화:** 긍정적인 시어(생명, 사랑, 희망)는 `(+)`, 부정적인 시어(죽음, 이별, 시련)는 `(-)`로 표시하며 읽는 훈련을 하세요.
3.  **보기 먼저 읽기:** <보기>가 있는 문제는 무조건 <보기>를 먼저 읽어야 합니다. <보기>는 해석의 기준(안경)을 제공해 줍니다.
"""

    # =================================================================
    # [4] 고난도 응용 (보기, 적용)
    # =================================================================
    elif "적용" in question_type or "보기" in question_type:
        return """
### 🔥 [심층 분석] 고난도: <보기>는 또 하나의 지문입니다.

**1. 진단: 왜 틀렸을까요?**
이 유형은 국어 시험의 '보스 몬스터'입니다. 틀린 이유는 지문의 내용도 알고 <보기>도 읽었지만, **이 둘을 연결(Mapping)**하지 못했기 때문입니다. 따로따로 생각하면 절대 풀리지 않습니다.

**2. 문제 해결 알고리즘**
1.  **지문(일반론):** 지문에서 설명하는 핵심 원리나 공식을 먼저 완벽히 이해합니다.
2.  **보기(구체적 사례):** <보기>에 나온 사례가 지문의 어떤 개념에 해당하는지 일대일로 매칭합니다. (예: 지문의 '수요' = 보기의 '아이스크림 구매량')
3.  **선지 판단:** 선지의 내용이 지문의 원리에 위배되는지, 혹은 <보기>의 상황과 맞지 않는지 논리적 모순을 찾습니다.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **매칭 연습:** 문제를 풀 때, 선지의 단어가 지문의 몇 번째 문단에서 왔는지, <보기>의 어떤 단어와 연결되는지 화살표를 긋는 연습을 하세요.
2.  **선지 끊어 읽기:** 3점짜리 보기 문제의 선지는 깁니다. `~해서(근거)` / `~하다(판단)`로 사선을 그어 끊으세요. 앞부분 근거가 틀렸는지 뒷부분 판단이 틀렸는지 쪼개서 봐야 보입니다.
3.  **기출 분석:** 맞은 문제라도 해설지를 보며 '출제자가 지문의 A개념을 보기의 B상황으로 어떻게 변형했는지' 그 출제 패턴을 분석하세요.
"""
    elif "강연" in question_type or "말하기" in question_type or "화법" in question_type:
        return """
### 🗣️ [심층 분석] 화법: 강연자의 '전략'을 꿰뚫어 보세요.

**1. 진단: 왜 틀렸을까요?**
내용 일치(팩트 체크)에만 집중하다가, 강연자가 청중을 위해 사용한 **'말하기 장치'**를 놓쳤기 때문입니다. 화법은 '무엇을' 말했느냐보다 **'어떻게'** 전달했느냐가 핵심입니다.

**2. 독해 전략 (Reading Strategy)**
* **전략 표지 찾기:** '질문을 통해', '자료를 제시하며', '전문가의 말을 인용하여' 같은 서술어에 민감해야 합니다.
* **청중 반응:** 강연자가 청중의 이해를 돕기 위해 예시를 들었는지, 반응을 확인했는지 체크하세요.

**3. 구체적인 행동 지침 (Action Plan)**
1.  **담화 표지 체크:** '첫째/둘째', '하지만', '정리하자면' 같은 표지어에 세모 표시를 하며 구조를 잡으세요.
2.  **비언어적 표현:** (웃으며), (자료를 가리키며) 같은 지문 속 괄호 내용이 문제의 정답 근거가 됩니다.
"""
    
    else:
        return """
### ⚠️ [종합 진단] 기초 체력을 길러야 할 때입니다.

**1. 진단**
해당 유형은 국어 영역의 가장 기초적인 독해력이나 어휘력이 부족하여 발생한 오답일 수 있습니다. 혹은 문제를 너무 급하게 풀다가 실수를 했을 수도 있습니다.

**2. 처방전**
* **어휘력 점검:** 선지나 지문에 모르는 단어가 3개 이상 있었다면, 단어장 정리가 최우선입니다.
* **해설지 정독:** 정답이 왜 정답인지 아는 것보다, **내가 고른 오답이 왜 답이 될 수 없는지**를 남에게 설명할 수 있을 정도로 분석하세요.
* **시간 관리:** 문제를 푸는 속도보다 **정확도**가 먼저입니다. 천천히 읽더라도 한 번에 정확하게 읽는 연습을 하세요.
"""

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
    
    # 1. 학년 선택
    selected_grade = col_g.selectbox("학년 선택", list(EXAM_DB.keys()))
    
    # 2. 해당 학년의 회차만 보여주기
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
                user_answers[q_num] = st.number_input(
                    f"{q_num}번 ({info['score']}점) [{info['type']}]", 
                    min_value=1, max_value=5, step=1, key=f"q_{selected_grade}_{selected_round}_{q_num}"
                )

        submit = st.form_submit_button("답안 제출하기", use_container_width=True)

    if submit:
        if not name or not student_id:
            st.error("이름과 학번을 입력하세요!")
        else:
            # 중복 체크 (학년 + 회차 + ID)
            sheet = get_google_sheet_data()
            is_duplicate = False
            
            if sheet:
                try:
                    records = sheet.get_all_records()
                    df = pd.DataFrame(records)
                    
                    if not df.empty:
                        # 문자열 변환 & 공백 제거
                        df['Grade'] = df['Grade'].astype(str).str.strip()
                        df['Round'] = df['Round'].astype(str).str.strip()
                        df['ID'] = df['ID'].astype(str).str.strip()
                        
                        # 정규화 함수 (0 처리)
                        def normalize(val):
                            try: return str(int(val))
                            except: return str(val).strip()
                        
                        df['ID_Clean'] = df['ID'].apply(normalize)
                        input_id_clean = normalize(student_id)
                        
                        # 중복 조건: 학년, 회차, ID 모두 같으면 중복!
                        dup = df[
                            (df['Grade'] == str(selected_grade)) &
                            (df['Round'] == str(selected_round)) &
                            (df['ID_Clean'] == input_id_clean)
                        ]
                        if not dup.empty:
                            is_duplicate = True
                except:
                    pass

            if is_duplicate:
                st.error(f"⛔ **이미 제출된 기록이 있습니다.** ({selected_grade} {student_id}번)")
                st.warning("결과 조회 탭에서 점수를 확인하세요.")
            else:
                # 채점
                total_score = 0
                wrong_list = []
                wrong_q_nums = []
                
                for q, info in current_exam_data.items():
                    if user_answers[q] == info['ans']:
                        total_score += info['score']
                    else:
                        wrong_list.append(info['type'])
                        wrong_q_nums.append(str(q))
                
                if sheet:
                    try:
                        wrong_q_str = ", ".join(wrong_q_nums) if wrong_q_nums else "없음"
                        new_row = [
                            selected_grade, # A열: 학년
                            selected_round, # B열: 회차
                            student_id,     # C열: ID
                            name, 
                            total_score, 
                            " | ".join(wrong_list), 
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            wrong_q_str
                        ]
                        sheet.append_row(new_row)
                        st.balloons()
                        st.success("제출 완료! 결과 조회 탭으로 이동하세요.")
                    except Exception as e:
                        st.error(f"저장 오류: {e}")

# === [탭 2] 결과 조회 ===
with tab2:
    st.header("🔍 성적표 조회")
    
    c_g, c_r = st.columns(2)
    chk_grade = c_g.selectbox("학년", list(EXAM_DB.keys()), key="chk_grade")
    chk_rounds = list(EXAM_DB[chk_grade].keys())
    chk_round = c_r.selectbox("회차", chk_rounds, key="chk_round")
    
    chk_id = st.text_input("학번(ID) 입력", key="chk_id")
    
    if st.button("조회하기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                
                # 전처리
                df['Grade'] = df['Grade'].astype(str).str.strip()
                df['Round'] = df['Round'].astype(str).str.strip()
                df['ID'] = df['ID'].astype(str)
                
                def normalize(val):
                    try: return str(int(val))
                    except: return str(val).strip()
                
                df['ID_Clean'] = df['ID'].apply(normalize)
                in_id = normalize(chk_id)
                
                # 3가지 조건(학년, 회차, ID) 모두 일치해야 함
                my_data = df[
                    (df['Grade'] == str(chk_grade)) &
                    (df['Round'] == str(chk_round)) &
                    (df['ID_Clean'] == in_id)
                ]
                
                if not my_data.empty:
                    last_row = my_data.iloc[-1]
                    
                    # 등수 계산 (같은 학년, 같은 회차 내에서만 비교)
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
                    
                    # (이하 피드백 출력 로직은 기존과 동일 - 생략 없이 그대로 사용)
                    w_q = str(last_row['Wrong_Questions']) if 'Wrong_Questions' in last_row else "없음"
                    if w_q != "없음" and w_q.strip():
                         st.error(f"❌ 틀린 문제: {w_q}번")
                    else:
                         st.success("⭕ 만점입니다!")

                    w_types = str(last_row['Wrong_Types']).split(" | ") if str(last_row['Wrong_Types']).strip() else []
                    
                    # 강점 분석
                    st.info("🌟 **나의 강점**")
                    found_str = False
                    target_exam = EXAM_DB[chk_grade][chk_round]
                    
                    keys_map = {
                        "문법": ["문법", "음운", "중세"],
                        "비문학": ["비문학", "철학", "경제", "기술", "과학"],
                        "문학": ["문학", "시가", "소설"],
                        "보기": ["보기", "적용"]
                    }
                    
                    for label, keywords in keys_map.items():
                        is_wrong = any(any(k in w for k in keywords) for w in w_types)
                        has_q = any(any(k in info['type'] for k in keywords) for info in target_exam.values())
                        
                        if has_q and not is_wrong:
                            st.write(f"- {get_strength_message(label)}")
                            found_str = True
                    
                    if not found_str: st.write("- 이번엔 골고루 실수가 있었네요.")
                    
                    # 약점 피드백
                    final_html = ""
                    if w_types:
                        st.markdown("---")
                        st.warning("💡 상세 피드백")
                        unique_fb = set(get_feedback_message(w) for w in w_types)
                        for msg in unique_fb:
                            st.markdown(msg)
                            st.markdown("---")
                            
                            # HTML 변환
                            clean_msg = msg.strip().replace(">", "💡").replace("**", "").replace("-", "•")
                            clean_msg = clean_msg.replace("\n", "<br>")
                            if clean_msg.startswith("###"):
                                parts = clean_msg.split("<br>", 1)
                                title = parts[0].replace("###", "").strip()
                                body = parts[1] if len(parts) > 1 else ""
                                clean_msg = f"<div style='font-size:16px; font-weight:bold; border-bottom:1px dashed #ccc; margin-bottom:5px;'>{title}</div><div>{body}</div>"
                            
                            final_html += f"<div class='feedback-box'>{clean_msg}</div>"
                    else:
                        final_html = "<div class='feedback-box'><h3>🎉 완벽합니다!</h3>약점이 없습니다.</div>"
                    
                    # 다운로드
                    w_nums = w_q.split(", ") if w_q != "없음" else []
                    report = create_report_html(chk_grade, chk_round, last_row['Name'], last_row['Score'], rank, total, w_nums, w_types, final_html)
                    st.download_button("📥 성적표 다운로드", report, file_name="성적표.html", mime="text/html")
                    with st.expander("📱 모바일 저장 방법"):
                        st.write("크롬에서 파일 열기 > 공유 > 인쇄 > PDF로 저장")

                else:
                    st.error("기록이 없습니다. (학년/회차/ID 확인)")
            except Exception as e:
                st.error(f"오류: {e}")

# === [탭 3] 종합 기록부 ===
with tab3:
    st.header("📈 나만의 포트폴리오")
    
    # 포트폴리오도 학년을 고르고 검색해야 정확함 (같은 번호 다른 학년 방지)
    p_grade = st.selectbox("학년 선택", list(EXAM_DB.keys()), key="p_grade")
    p_id = st.text_input("학번(ID) 입력", key="p_id")
    
    if st.button("종합 분석 보기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                
                df['Grade'] = df['Grade'].astype(str).str.strip()
                df['ID'] = df['ID'].astype(str)
                def normalize(val):
                    try: return str(int(val))
                    except: return str(val).strip()
                df['ID_Clean'] = df['ID'].apply(normalize)
                clean_p_id = normalize(p_id)
                
                # 학년과 ID가 모두 맞는 데이터만 필터링
                my_hist = df[
                    (df['Grade'] == str(p_grade)) & 
                    (df['ID_Clean'] == clean_p_id)
                ]
                
                if not my_hist.empty:
                    st.success(f"**{p_grade} {my_hist.iloc[-1]['Name']}**님의 성장 기록")
                    
                    # 그래프
                    chart = alt.Chart(my_hist).mark_line(point=True).encode(
                        x='Round', y=alt.Y('Score', scale=alt.Scale(domain=[0, 100]))
                    )
                    st.altair_chart(chart, use_container_width=True)
                    
                    # 표
                    st.dataframe(my_hist[['Round', 'Score', 'Wrong_Types']])
                else:
                    st.warning("기록이 없습니다.")
            except Exception as e:
                st.error(f"오류: {e}")
