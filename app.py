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
    st.header("🔍 내 등수 & 피드백 다시 보기")
    st.write("나의 등수 변화와 학습 피드백을 언제든 다시 확인하세요.")
    
    check_id = st.text_input("학번(ID) 입력", key="check_input")
    
    if st.button("조회하기"):
        sheet = get_google_sheet_data()
        if sheet:
            try:
                records = sheet.get_all_records()
                df = pd.DataFrame(records)
                
                # ID로 검색 (문자열 변환 후 비교)
                df['ID'] = df['ID'].astype(str) 
                user_record = df[df['ID'] == check_id]
                
                if not user_record.empty:
                    # 가장 최신 기록 가져오기
                    last_row = user_record.iloc[-1]
                    current_score = last_row['Score']
                    
                    # 저장된 오답 유형 문자열을 다시 리스트로 복구
                    # (저장할 때 " | "로 합쳤으므로, 다시 쪼갭니다)
                    wrong_types_str = str(last_row['Wrong_Types'])
                    if wrong_types_str.strip():
                        wrong_list = wrong_types_str.split(" | ")
                    else:
                        wrong_list = [] # 다 맞은 경우

                    # 실시간 등수 재계산
                    realtime_rank = df[df['Score'] > current_score].shape[0] + 1
                    total_now = len(df)
                    top_pct = (realtime_rank / total_now) * 100
                    
                    # 1. 점수 및 등수 표시
                    st.success(f"반갑습니다, **{last_row['Name']}**님! 다시 오셨군요.")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("내 점수", f"{int(current_score)}점")
                    m2.metric("현재 실시간 등수", f"{realtime_rank}등 / {total_now}명")
                    m3.metric("상위", f"{top_pct:.1f}%")
                    
                    st.markdown("---")

                    # 2. 강점 분석 (칭찬) 로직 재실행
                    st.info("🌟 **나의 강점 다시 보기**")
                    found_any_strength = False

                    # (1) 문법 패밀리
                    grammar_keys = ["문법", "음운", "국어사전", "중세"]
                    is_grammar_wrong = any(any(k in w_type for k in grammar_keys) for w_type in wrong_list)
                    has_grammar_q = any(any(k in info['type'] for k in grammar_keys) for info in EXAM_DATA.values())
                    if has_grammar_q and not is_grammar_wrong:
                        st.write(f"- {get_strength_message('문법')}")
                        found_any_strength = True

                    # (2) 비문학 패밀리
                    nonlit_keys = ["비문학", "철학", "경제", "건축", "기술", "과학", "인문", "사회"]
                    is_nonlit_wrong = any(any(k in w_type for k in nonlit_keys) for w_type in wrong_list)
                    has_nonlit_q = any(any(k in info['type'] for k in nonlit_keys) for info in EXAM_DATA.values())
                    if has_nonlit_q and not is_nonlit_wrong:
                        st.write(f"- {get_strength_message('비문학')}")
                        found_any_strength = True

                    # (3) 문학 패밀리
                    lit_keys = ["시가", "작품", "시어", "소설", "각본", "서사"]
                    is_lit_wrong = any(any(k in w_type for k in lit_keys) for w_type in wrong_list)
                    has_lit_q = any(any(k in info['type'] for k in lit_keys) for info in EXAM_DATA.values())
                    if has_lit_q and not is_lit_wrong:
                        st.write(f"- {get_strength_message('문학')}")
                        found_any_strength = True

                    # (4) 고난도 패밀리
                    hard_keys = ["적용", "보기", "준거"]
                    is_hard_wrong = any(any(k in w_type for k in hard_keys) for w_type in wrong_list)
                    has_hard_q = any(any(k in info['type'] for k in hard_keys) for info in EXAM_DATA.values())
                    if has_hard_q and not is_hard_wrong:
                        st.write(f"- {get_strength_message('보기')}")
                        found_any_strength = True

                    if not found_any_strength:
                        st.write("- 모든 영역에서 조금씩 실수가 있었네요. 오답 정리를 통해 빈틈을 채우면 다음엔 만점입니다! 💪")

                    # 3. 약점 분석 (피드백) 로직 재실행
                    if wrong_list:
                        st.markdown("---")
                        st.error(f"🚨 **보완이 필요한 부분 ({len(wrong_list)}문제 오답)**")
                        
                        # 중복 제거 후 피드백 출력
                        unique_feedback = set(get_feedback_message(w) for w in wrong_list)
                        for msg in unique_feedback:
                            st.markdown(msg)
                            st.markdown("---")
                    else:
                        st.balloons()
                        st.write("### 🎉 완벽합니다! 약점이 없는 무결점 실력입니다!")

                else:
                    st.warning("해당 학번의 기록이 없습니다. 답안을 먼저 제출해주세요.")
            except Exception as e:
                st.error(f"조회 중 오류 발생: {e}")
