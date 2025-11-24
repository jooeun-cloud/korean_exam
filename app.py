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

    # 세션 기본값 설정
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
                # 🔁 별도의 rerun 필요 없음 (Streamlit이 자동으로 재실행함)
            else:
                st.error("❌ ID 또는 비밀번호가 올바르지 않습니다.")
    else:
        role_label = "최종관리자" if st.session_state["is_superadmin"] else "일반 관리자"
        st.success(f"접속 계정: {st.session_state['admin_id']}")
        st.caption(f"권한 : {role_label}")

        st.markdown("---")
        if st.button("🔄 문제 DB 새로고침"):
            st.cache_data.clear()
            st.success("문제 DB 캐시를 초기화했습니다. (다음 화면부터 반영됩니다)")

        if st.button("로그아웃"):
            for k in ["is_authenticated", "admin_id", "is_superadmin"]:
                st.session_state.pop(k, None)
            st.success("로그아웃 되었습니다.")
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
# 세분화된 Type 값에 대한 전용 피드백
FEEDBACK_BY_TYPE = {
    "화법(강연-말하기 전략)": """### 🗣️ 화법: 강연에서의 말하기 전략
**1. 진단**  
강연 내용을 이해하는 데 집중하느라, 화자가 사용한 **말하기 전략(예시, 비교, 질문, 강조)**을 구분하지 못했을 가능성이 큽니다. 그래서 비슷한 선지 사이에서 계속 헷갈립니다.

**2. Action Plan**  
1. 지문을 읽을 때 중요한 문장 옆에 `[예시] [비교] [질문] [강조]`처럼 전략 이름을 직접 적게 하세요.  
2. 각 전략이 쓰인 문장마다 “이 전략을 쓰면 청자가 어떤 느낌/정보를 더 잘 받는가?”를 말로 설명하게 해 보세요.  
3. 마지막에는 반드시 **“이 화자는 무엇을 하게 만들려고 이 말을 했을까?”**를 한 문장으로 요약하게 하세요.""",

    "화법(강연-시각 자료·예시 활용)": """### 🗣️ 화법: 시각 자료·예시 활용
**1. 진단**  
그래프·사진·도표 등을 그냥 ‘꾸미기용 그림’처럼 보고, **말하기 내용과 연결된 기능**으로 해석하지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 시각 자료가 나올 때마다 옆에 **“이 자료가 없으면 어떤 정보가 약해질까?”**를 적게 하세요. (이해 보조 / 설득 강화 / 비교 강조 중 무엇인지)  
2. 자료에 담긴 핵심 숫자·변화 방향만 뽑아서 한 줄로 요약하게 하세요.  
3. 선지에서 시각 자료의 ‘역할’을 묻는지, ‘내용’ 자체를 묻는지 먼저 구분하도록 지도하세요.""",

    "화법(강연-청자 반응·이해 평가)": """### 🗣️ 화법: 청자 반응·이해 평가
**1. 진단**  
청자의 질문·고개 끄덕임·웃음 등을 단순한 행동 묘사로만 보고, **이 반응이 이해/평가/공감/반박 중 무엇인지**를 구분하지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 청자 발화마다 옆에 `[이해 확인] [공감] [비판] [추가 질문]`처럼 듣기 유형 꼬리표를 붙이게 하세요.  
2. “이 반응이 나오면, 화자는 다음에 어떤 전략으로 이어갈까?”를 예측하게 해 보세요.  
3. 선지를 볼 때는, 반응의 **내용**이 아니라 그 반응이 가진 **기능(역할)**을 기준으로 옳고 그름을 판단하도록 지도하세요.""",

    "문법-음운(비음화·유음화 개념 이해)": """### 🧬 문법: 비음화·유음화 개념 정리
**1. 진단**  
비음화·유음화의 정의는 외웠지만, **실제 단어에서 ‘왜’ 그런 변화가 일어나는지**를 설명하지 못했을 가능성이 큽니다. 받침 뒤에 오는 소리를 제대로 보지 않고 정답을 고른 경우가 많습니다.

**2. Action Plan**  
1. 항상 **‘받침 + 뒤 음운’** 구조로 단어를 쪼개 보게 하세요. (예: [국+물] → [궁물])  
2. 비음화 = 뒤에 **[ㄴ, ㅁ, ㅇ] 비음**이 올 때, 유음화 = **ㄴ이 ㄹ 앞에서 ㄹ로 바뀜**이라는 최소한의 조건을 말로 설명하게 하세요.  
3. 문제를 풀 때, 먼저 “어떤 음이 어떤 음 옆으로 갔는지”를 입으로 읽어 보고, 그다음에 용어(비음화/유음화)를 붙이도록 지도하세요.""",

    "문법-음운(구개음화-조음 위치·환경 분석)": """### 🧬 문법: 구개음화(조음 위치·환경)
**1. 진단**  
구개음화를 ‘ㄷ/ㅌ + 이 → ㅈ/ㅊ’ 공식으로만 외우고, **뒤에 오는 모음·자음 환경**을 제대로 보지 않았을 가능성이 큽니다. 조음 위치가 앞쪽(입천장 쪽)으로 옮겨지는 원리를 이해하지 못한 상태입니다.

**2. Action Plan**  
1. 단어를 항상 `[자음 + 모음]` 단위로 끊고, **ㄷ·ㅌ 뒤에 ㅣ(또는 ㅕ, ㅛ, ㅠ 등 ㅣ 계열 모음)**이 오는지 먼저 체크하게 하세요.  
2. 구개음화는 “혀의 닿는 위치가 앞쪽(경구개)으로 당겨진다”는 그림을 함께 보여 주며 설명하면 기억이 오래 갑니다.  
3. 음성 변화 과정을 **/디/ → [지]**처럼 기호로 적어 보게 하고, 그 뒤에 용어(구개음화)를 붙이도록 연습시키세요.""",

    "문법-문장 성분/구문 도해(주어·목적어·조사)": """### 🧱 문법: 문장 성분·구문 도해
**1. 진단**  
문장을 단어 나열로만 보고, **서술어-주어-목적어 관계를 구조적으로 파악하지 못했을 가능성**이 큽니다. 특히 조사를 그냥 단어의 일부로 보고, 문장 성분의 역할을 구분하지 못합니다.

**2. Action Plan**  
1. 어떤 문장이든 먼저 **서술어(동사·형용사)**에 밑줄을 긋게 하세요.  
2. 그다음 “누가(주어), 무엇을(목적어), 어떤 상태가 되게 하는가(보어)”를 질문으로 던지며 해당 성분을 찾게 합니다.  
3. 조사는 ‘꾸며주는 꼬리표’라는 것을 강조하고, 체언과 분리해서 표시하는 연습(예: 학생/이, 책/을)을 반복시키세요.""",

    "문법-사전 정보 해석(있다/없다-발음·품사)": """### 📖 문법: 사전 정보(발음·품사)
**1. 진단**  
사전 뜻풀이에서 **발음 기호와 품사 정보**를 건너뛰고, 뜻풀이만 보고 판단했을 가능성이 큽니다. 그래서 같은 표기의 다른 품사를 구별하지 못했을 수 있습니다.

**2. Action Plan**  
1. 사전 문제가 나오면 먼저 **발음 기호, 품사, 문형** 순으로 표시하게 하세요. (뜻은 그다음)  
2. 예문을 볼 때 “이 예문에서는 어떤 품사로 쓰였는지”를 동그라미 치게 하여, 품사-뜻풀이-예문이 서로 어떻게 대응되는지 연결하도록 지도하세요.  
3. ‘있다/없다’처럼 일상적 단어일수록 품사가 여러 개일 수 있다는 점을 강조해 주세요.""",

    "문법-사전 정보 해석(있다/없다-의미·용례 적용)": """### 📖 문법: 사전 의미·용례 적용
**1. 진단**  
사전에서 제시한 **여러 개의 의미 중 어느 의미가 문제 속 문장에 해당하는지**를 고르는 데 실패했습니다. 문장 속 쓰임을 정확히 파악하지 못한 상태입니다.

**2. Action Plan**  
1. 먼저 문제에 나온 문장을 자신의 말로 풀어 쓰게 하여, 실제 의미를 명확히 하게 하세요.  
2. 그다음 사전 뜻풀이 각 항목 옆에 “비슷한 말”을 하나씩 적어 보게 하고, 문제 속 문장과 가장 잘 맞는 항목을 고르게 지도하세요.  
3. 비슷해 보이는 의미를 구분할 때는 ‘대상’과 ‘상황’을 기준으로 나누게 하세요 (예: 존재/소유/경험 등).""",

    "비문학-인문/철학(흄·데카르트-진리관 비교)": """### 🧠 인문/철학: 흄·데카르트 진리관 비교
**1. 진단**  
두 사상가의 입장을 따로따로 외우고, **어떤 기준에서 대립하는지**를 표로 정리하지 못했을 가능성이 큽니다. 그래서 선지에서 관점이 섞여 나올 때 쉽게 헷갈립니다.

**2. Action Plan**  
1. 지문에서 철학자가 두 명 이상 나오면, 반드시 다음 틀로 정리하게 하세요.  
   - 흄: 경험/인상 중심, 인과 필연성 회의  
   - 데카르트: 이성/명석판명한 인식 중심  
2. 각 사상가에 대해 “○○는 진리를 무엇으로 보나?” 한 줄 요약을 적게 하고, 모든 선지는 그 한 줄과 비교해서 판단하도록 지도하세요.""",

    "비문학-인문/철학(인상/관념 개념 추론)": """### 🧠 인문/철학: 인상·관념 개념 이해
**1. 진단**  
‘인상’과 ‘관념’의 정의를 읽었지만, 구체적인 예시에 대입해 보지 않아 **어떤 것이 인상이고 어떤 것이 관념인지** 구분하지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 수업 시간에 직접 예시를 만들게 하세요.  
   - 인상: 지금 막 불을 본 강렬한 경험  
   - 관념: 나중에 떠올리는 ‘불’에 대한 생각  
2. 지문 속 예들을 보고, 인상/관념 옆에 각각 I, C 같은 약어 표시를 하게 하여 개념과 사례를 계속 묶도록 지도하세요.  
3. 학생이 자신의 말로 “인상 = ○○, 관념 = ○○”를 설명하게 해 보고, 말로 설명이 안 되면 개념 재학습이 필요합니다.""",

    "비문학-인문/철학(보기 적용-경험론 사례 분석)": """### 🧠 인문/철학: 보기 적용(경험론 사례)
**1. 진단**  
[보기]에 나온 일상 사례를 지문에서 설명한 **경험론 개념**으로 번역하지 못했습니다. 그래서 지문과 보기의 연결 고리를 찾지 못한 상태입니다.

**2. Action Plan**  
1. [보기]를 볼 때, 문장 옆에 “= 지문의 ○○”처럼 어떤 개념에 해당하는지 직접 적게 하세요. (예: ‘습관적인 믿음’ = 흄의 인과관계 이해 방식)  
2. 지문 용어 ↔ 일상 사례를 1:1로 짝짓는 표를 만들어 보게 하고, 표를 완성한 뒤에 선지를 검토하도록 지도하세요.  
3. 보기 적용 문제는 ‘지문 요약 없이 보기부터 읽는 것’을 금지시키고, 반드시 **지문 개념 → 보기 사례 순서**로 읽게 하세요.""",

    "비문학-인문/철학(주장·타당성 평가)": """### 🧠 인문/철학: 주장·타당성 평가
**1. 진단**  
글쓴이의 주장을 파악했지만, 그 주장이 성립하기 위한 **전제와 조건**을 충분히 생각하지 못했습니다. 그래서 반례가 되는 사례나 조건 누락을 발견하지 못합니다.

**2. Action Plan**  
1. 주장 문장(결론)을 찾은 뒤, “이게 성립하려면 무엇이 사실이어야 하지?”를 세 가지 이상 떠올리게 하세요.  
2. 지문이나 선지에 등장하는 사례가 그 전제를 깨는지, 아니면 오히려 강화하는지 구분하게 지도하세요.  
3. “전제를 건드리는 선지”가 있는지를 먼저 확인하게 하면, 고난도 타당성 평가 문제에서 실수를 줄일 수 있습니다.""",

    "문학-운문(서정시 전통-형식·내용 개관)": """### 🌙 문학(운문): 서정시 전통 이해
**1. 진단**  
시의 형식(운율, 행 구분 등)은 보았지만, **한국 서정시 전통 속에서 이 작품이 어떤 계열에 속하는지**를 정리하지 못했습니다.

**2. Action Plan**  
1. 작품을 읽은 뒤, 먼저 “이 시는 ‘자연 예찬 / 현실 비판 / 민족 정서 / 사랑·이별’ 중 어디에 가까운가?”를 분류하게 하세요.  
2. 형식적 특징(음보, 반복, 종결 어미, 시적 화자의 태도)을 나열하고, 그것이 내용과 어떻게 연결되는지 한 줄로 설명하게 훈련시키세요.  
3. 비슷한 전통의 시 두 편을 나란히 놓고 공통점·차이점을 비교하는 활동을 통해 ‘서정시 전통’이라는 큰 틀을 잡게 하는 것이 좋습니다.""",

    "문학-운문(고전시가-상황·정서 파악)": """### 🌙 문학(운문): 고전시가 상황·정서
**1. 진단**  
고전 어휘와 어순에 막혀, 화자가 처한 **상황과 정서**를 현재어로 번역하지 못했습니다. 그래서 시어의 의미와 정서의 방향을 잘못 파악했을 가능성이 큽니다.

**2. Action Plan**  
1. 먼저 각 행을 오늘날 말로 옮겨 적게 하세요. (너무 예쁘게 번역하려 하지 말고, 말하듯이 쓰게)  
2. 그다음 “화자가 지금 어디에서, 누구를 떠올리며, 무엇을 바라는지”를 한 문장으로 정리하게 하세요.  
3. 정서를 볼 때는 개별 단어에 매달리기보다 ‘화자–님–자연–현실’ 사이의 관계(가까워지는가/멀어지는가, 긍정/부정)를 중심으로 보게 지도하세요.""",

    "문학-운문(현대시-이미지·정서 해석)": """### 🌙 문학(운문): 현대시 이미지·정서
**1. 진단**  
시어를 **사전적 의미**로만 해석하고, 그 이미지가 만들어 내는 분위기·정서까지 연결하지 못했습니다. ‘길’, ‘바다’, ‘어둠’ 같은 상징적 시어가 문자 그대로만 읽혔을 가능성이 큽니다.

**2. Action Plan**  
1. 학생에게 “이 시어를 풍경·상태·관계 중 어떤 것으로 보면 자연스러운가?”를 묻게 하세요. (예: ‘길’ = 삶의 방향, 방황)  
2. 시의 이미지를 긍정/부정, 밝음/어둠, 정지/움직임 등 **대비 축**에서 분류하게 하여, 전체 정서 흐름을 시각적으로 정리하게 합니다.  
3. 마지막에는 “시 전체에서 화자가 느끼는 핵심 감정 한 단어”를 뽑게 하고, 근거가 되는 시어 세 개를 함께 제시하게 하세요.""",

    "문학-운문(전통 계승·변용 방식 평가)": """### 🌙 문학(운문): 전통 계승·변용
**1. 진단**  
고전시가의 전통 요소와 현대시의 변용 요소를 분리해서 보지 못했습니다. 그래서 ‘계승’과 ‘파격’이 뒤섞인 선지를 구분하는 데 어려움을 겪었을 가능성이 큽니다.

**2. Action Plan**  
1. 고전 작품과의 공통점/차이점을 각각 한 줄씩 쓰게 하세요. (예: 자연 소재 사용은 계승, 화자의 태도는 변용)  
2. 형식(운율, 반복 구조)과 내용(정서, 주제)이 각각 어떻게 전통을 이어받았는지/뒤틀었는지 표로 정리하게 합니다.  
3. 선지를 볼 때 “이건 ‘계승’에 초점인가, ‘변용’에 초점인가?”를 먼저 구분하고 읽도록 지도하세요.""",

    "문학-운문(보기 적용-종합 감상)": """### 🌙 문학(운문): 보기 적용·종합 감상
**1. 진단**  
[보기]의 감상 문장을 지문의 근거와 연결하지 않고, 자신의 느낌에 가까운 선지를 고른 경우가 많습니다. 근거 없는 감상은 정답일 수 없습니다.

**2. Action Plan**  
1. [보기]의 각 문장마다 시 속에서의 **근거 시어**를 찾게 하세요. (없다면 그 감상은 오답 가능성이 큼)  
2. “이 감상이 맞으려면, 시 속에서 어떤 표현이 반드시 있어야 하지?”를 질문해 보게 합니다.  
3. 보기 감상과 시 내용을 비교할 때, 감정 단어만 보지 말고 **관계·상황·태도**까지 함께 확인하도록 지도하세요.""",

    "비문학-사회/경제(조세-효율성·공평성 개념)": """### 📈 사회/경제: 조세·효율성·공평성 개념
**1. 진단**  
조세 정책을 설명하는 문단에서 **효율성과 공평성의 개념**은 대략 이해했으나, 둘이 어떤 상황에서 충돌하는지 구체적으로 떠올리지 못했습니다.

**2. Action Plan**  
1. 효율성 = 전체 파이 키우기, 공평성 = 파이 나누는 방식이라는 비유로 다시 정리하게 하세요.  
2. 실제 사례(누진세, 복지 정책 등)를 가지고 “이건 효율성/공평성 중 어느 쪽을 더 중시한 정책인가?”를 분류해 보게 합니다.  
3. 문제를 풀 때는 문장 옆에 `효율↑ 공평↓` 같은 화살표 메모를 하게 해서, 방향성을 시각적으로 익히도록 지도하세요.""",

    "비문학-사회/경제(효율성 vs 공평성 비교)": """### 📈 사회/경제: 효율성 vs 공평성 비교
**1. 진단**  
두 가치가 서로 충돌할 때 어떤 선택을 하는지, 그에 따른 장단점을 논리적으로 비교하는 데 어려움이 있습니다.

**2. Action Plan**  
1. “효율성만 높이면 생길 수 있는 문제 / 공평성만 중시하면 생길 수 있는 문제”를 각각 두 가지씩 써 보게 하세요.  
2. 지문에서 제시한 입장이 어느 쪽에 더 치우쳐 있는지, 근거 문장을 표시하게 합니다.  
3. 선지를 읽을 때, 두 가치를 모두 만족시키는지보다 **어느 가치를 더 우선시하는지**에 초점을 맞추도록 지도하세요.""",

    "비문학-사회/경제(보기 적용-조세 사례 분석)": """### 📈 사회/경제: 보기 적용(조세 사례)
**1. 진단**  
[보기]에 제시된 구체적인 세금 사례를, 지문에서 설명한 조세 원리(효율성/공평성, 조세 형평 등)와 연결하지 못했습니다.

**2. Action Plan**  
1. 보기 속 사례 옆에 “= 효율성 중시 / 공평성 중시 / 혼합”처럼 지문 개념을 붙이게 하세요.  
2. 세율 구조·과세 대상·재원 사용처가 각각 효율성·공평성과 어떻게 연결되는지 질문하며 하나씩 따져 보게 합니다.  
3. 보기 적용 문제는 반드시 **지문 개념 요약 → 보기 사례 읽기 → 개념 라벨 붙이기** 순서를 지키도록 지도하세요.""",

    "매체-영화/시나리오(장면 연출 의도 파악)": """### 🎬 매체: 영화/시나리오 장면 연출 의도
**1. 진단**  
장면 전환, 카메라 거리, 배경음악 등 연출 요소를 그냥 ‘상황 설명’ 정도로만 이해하고, **관객에게 주는 효과**까지 연결하지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 컷 전환, 클로즈업, 롱숏, 배경음 등 연출 장치 옆에 `긴장 강화`, `감정 집중`, `정보 제공` 같은 효과를 적게 하세요.  
2. 같은 내용이라도 어떻게 찍느냐에 따라 관객 인상이 달라진다는 점을 짧은 영상 예시로 경험하게 하는 것이 좋습니다.  
3. 문제에서 묻는 것이 ‘내용’인지 ‘연출 효과’인지 먼저 구분하도록 지도하세요.""",

    "매체-영화/시나리오(보기 적용-감상 관점)": """### 🎬 매체: 영화 감상 관점(보기 적용)
**1. 진단**  
[보기]의 감상문이 사용하는 관점(인물 중심, 주제 중심, 연출 중심 등)을 구분하지 못했습니다. 그래서 감상 관점과 맞지 않는 내용을 걸러내지 못합니다.

**2. Action Plan**  
1. 보기 감상문에서 반복되는 단어나 강조되는 부분을 찾아 “이 감상은 **인물/주제/연출/사회적 의미** 중 어디에 초점이 있는가?”를 분류하게 하세요.  
2. 각 관점별로 어떤 요소를 중점적으로 언급하는지(인물 내면, 상징, 카메라 움직임 등) 간단한 리스트를 만들어 두고, 그 기준으로 선지를 판단하도록 지도하세요.""",

    "매체-영화/시나리오(구성·장면 배열 효과)": """### 🎬 매체: 구성·장면 배열 효과
**1. 진단**  
사건이 제시되는 순서를 바꾸었을 때 **긴장감·정보 공개 시점**이 어떻게 달라지는지 상상하지 못했습니다.

**2. Action Plan**  
1. 제시된 장면 순서를 바꾸어 다시 배열해 보게 하고, “이렇게 바꾸면 관객은 어떤 정보를 언제 알게 되는가?”를 비교하게 하세요.  
2. 플래시백, 미리 제시된 결말 장면 등 비선형 구성이 작품 해석에 어떤 역할을 하는지 토론해 보게 하면 효과적입니다.  
3. 문제에서 ‘구성상 효과’를 묻는 선지는 항상 **정보 공개 시점·긴장감·인물에 대한 인상 변화** 중 어디를 말하는지 확인하게 하세요.""",

    "비문학-과학/기술(초고층 건물-하중 개념 이해)": """### ⚙️ 과학/기술: 초고층 건물·하중 개념
**1. 진단**  
하중의 종류(고정 하중/활동 하중/풍하중 등)를 구분하지 못하거나, 구조물에 어떤 방식으로 작용하는지 상상하지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 지문에 나온 하중 종류 옆에 간단한 예시(사람·가구·바람 등)를 직접 그려 보게 하세요.  
2. “어떤 하중은 항상 존재하고, 어떤 하중은 시간에 따라 달라지는가?”를 기준으로 분류하게 합니다.  
3. 선지에서 하중의 방향(수직/수평)과 지속성(항상/일시적)을 바꾸어 말하고 있는지 확인하도록 지도하세요.""",

    "비문학-과학/기술(구조 유형 비교·설명 방식)": """### ⚙️ 과학/기술: 구조 유형 비교
**1. 진단**  
여러 구조 유형(예: 라멘, 트러스 등)의 특징을 암기 수준으로만 알고, **어떤 구조가 어떤 하중에 적합한지** 연결하지 못했습니다.

**2. Action Plan**  
1. 구조별로 “어떤 방향의 힘에 강한지, 주로 어디에 쓰이는지”를 짧게 정리한 표를 만들게 하세요.  
2. 지문 설명에서 ‘비교/대조’ 표현(반면에, 그러나, ~와 달리)을 표시하게 하여, 구조 간 차이점을 눈에 띄게 합니다.  
3. 보기나 선지에 제시된 상황(바람이 강한 지역, 지진 가능성 등)에 어떤 구조가 적합한지 스스로 판단해 보게 하는 연습을 시키세요.""",

    "비문학-과학/기술(TLCD 작동 원리 이해)": """### ⚙️ 과학/기술: TLCD 작동 원리
**1. 진단**  
TLCD의 구조와 작동 원리를 글로만 읽고, **‘흔들림 → 액체 움직임 → 힘 상쇄’**라는 과정을 단계적으로 정리하지 못했습니다.

**2. Action Plan**  
1. TLCD의 구조를 간단히 그림으로 그리게 하고, 건물이 한쪽으로 기울 때 액체가 어떻게 움직여 반대 힘을 만드는지 화살표로 표시하게 하세요.  
2. 원인-결과를 `건물 흔들림 ↑ → 액체 운동 ↑ → 상쇄력 ↑`처럼 한 줄 공식으로 정리하도록 지도하세요.  
3. 계산이나 수치보다, “어떤 요소가 변할 때 어떤 결과가 따라오는지”에 초점을 맞춰 읽게 해야 합니다.""",

    "비문학-과학/기술(보기-도식 정보 적용)": """### ⚙️ 과학/기술: 도식 정보 적용
**1. 진단**  
[보기]에 제시된 도식·그래프·표를 TLCD 설명과 정확히 연결하지 못했습니다. 도식의 각 요소가 지문에서 무엇을 의미하는지 파악이 부족한 상태입니다.

**2. Action Plan**  
1. 도식의 각 부분(상자, 화살표)에 지문 용어를 직접 적게 하여 1:1로 매칭시켜 보게 하세요.  
2. 지문과 도식 중 무엇이 ‘원리 설명’이고 무엇이 ‘구체적 예시’인지 나누게 합니다.  
3. 도식 설명 문제는 지문 전체를 다시 읽기보다, 도식-지문 사이의 대응 관계를 먼저 완성한 뒤 선지를 검토하게 하세요.""",

    "문학-고전소설(배비장전-작품·모티프 개관)": """### 📖 문학(고전소설): 배비장전 개관
**1. 진단**  
배비장전을 단순한 옛날 이야기로만 보고, **풍자·해학·위선 폭로**라는 핵심 모티프를 잡지 못했을 가능성이 큽니다.

**2. Action Plan**  
1. 배비장 인물을 한 줄로 요약하게 하세요. (예: 밖에서는 엄격한 선비, 속으로는 욕망에 흔들리는 인물)  
2. 이야기의 주요 사건을 “겉으로 드러난 모습 vs 속마음” 구조로 나눠 정리하게 합니다.  
3. 다른 풍자 소설(예: 허생전 등)과 비교하여, 어떤 방식으로 인물의 위선을 드러내는지 공통점·차이점을 정리하게 하세요.""",

    "문학-고전소설(배비장전-인물·갈등 구조)": """### 📖 문학(고전소설): 배비장전 인물·갈등
**1. 진단**  
사건 전개는 이해했지만, 인물들 사이의 **갈등 구조와 힘의 역전**을 충분히 파악하지 못했습니다. 특히 주인공의 심리 변화와 주변 인물의 의도를 놓쳤을 수 있습니다.

**2. Action Plan**  
1. 배비장, 기생, 아내, 주변 인물의 관계도를 그리고, 각 인물이 배비장을 어떻게 ‘시험’하거나 ‘조롱’하는지 화살표로 표시하게 하세요.  
2. 갈등이 최고조에 이르는 장면과, 그 갈등이 어떻게 해소되는지를 구체적으로 적게 합니다.  
3. 선지를 읽을 때 단순한 사건 요약인지, 인물의 가치관·태도를 드러내는지 구분해서 보게 지도하세요.""",

    "문학-고전소설(배비장전-장면별 태도 해석)": """### 📖 문학(고전소설): 장면별 태도 해석
**1. 진단**  
각 장면에서 배비장이 보이는 태도(체면/욕망/두려움 등)를 상황에 맞게 읽어내지 못했습니다. 한 번 형성한 인물 이미지만 고수한 채, 장면별 변화를 놓친 경우가 많습니다.

**2. Action Plan**  
1. 주요 장면마다 “밖으로 드러난 말/행동”과 “속마음”을 따로 적게 하여, 위선 구조를 분명하게 인식하게 하세요.  
2. “이 장면에서 배비장은 무엇을 가장 두려워하는가?” 같은 질문을 던져, 감정의 초점을 찾게 합니다.  
3. 태도 선지를 볼 때는 단어 하나에만 반응하지 말고, 그 단어가 작품 전체에서의 배비장과 어울리는지 검증하게 지도하세요.""",

    "문학-고전소설(배비장전-상황에 맞는 성어)": """### 📖 문학(고전소설): 상황에 맞는 성어 이해
**1. 진단**  
성어의 뜻은 대략 알고 있지만, **작품 속 구체적 장면과 성어의 핵심 이미지**를 연결하지 못했습니다. 비슷한 의미의 성어를 혼동했을 가능성이 큽니다.

**2. Action Plan**  
1. 자주 나오는 성어들의 한자 구성과 기본 이미지를 먼저 정리하게 하세요. (예: 자승자박 = 스스로 만든 올가미에 걸림)  
2. 작품 속 장면을 한 줄로 요약한 뒤, 그 상황과 가장 잘 어울리는 성어를 고르는 연습을 여러 작품에 걸쳐 반복시키세요.  
3. 성어 문제를 풀 때는 단어 뜻만 보지 말고, **‘누가 누구에게 무엇을 해서 어떤 꼴이 되었는가’**를 기준으로 판단하도록 지도하세요."""
}

def get_feedback_message_list(question_type):
    messages = []
    q = str(question_type).strip()

    if q in FEEDBACK_BY_TYPE:
        messages.append(FEEDBACK_BY_TYPE[q])

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
