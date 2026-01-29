import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import streamlit as st

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


APP_TITLE = "K-드라마 튜터"
APP_SUBTITLE = "K-드라마 대사로 배우는 한국어 — 어휘/표현/퀴즈/롤플레이"


@dataclass
class LineItem:
    show: str
    level: str  # A1/A2/B1...
    kr: str
    roman: str
    en: str
    notes: str
    vocab: List[Tuple[str, str]]  # (kr, meaning)
    patterns: List[Tuple[str, str]]  # (pattern, explanation)


SAMPLE_LINES: List[LineItem] = [
    LineItem(
        show="(샘플) 오피스/로코",
        level="A1",
        kr="괜찮아요? 많이 놀랐죠?",
        roman="Gwaenchana-yo? Mani nollat-jyo?",
        en="Are you okay? You must have been really surprised.",
        notes="상대 상태 확인 + 공감/배려 표현.",
        vocab=[("괜찮아요", "괜찮습니다/OK"), ("놀라다", "to be surprised"), ("많이", "a lot")],
        patterns=[("-(으)ㄹ까요?", "제안/의향을 부드럽게 묻기"), ("-죠?", "상대의 동의를 기대하며 확인")],
    ),
    LineItem(
        show="(샘플) 스릴러",
        level="A2",
        kr="지금 어디예요? 바로 갈게요.",
        roman="Jigeum eodieyo? Baro galgeyo.",
        en="Where are you now? I'll come right away.",
        notes="현재 위치 질문 + 즉시 행동 약속.",
        vocab=[("지금", "now"), ("어디예요", "where is it/are you"), ("바로", "right away"), ("가다", "to go")],
        patterns=[("-게요", "화자의 의지/약속 표현"), ("어디예요?", "장소/상태 질문")],
    ),
    LineItem(
        show="(샘플) 가족/휴먼",
        level="B1",
        kr="네가 하고 싶은 대로 해. 나는 네 편이야.",
        roman="Nega hago sipeun-daero hae. Naneun ne pyeoniya.",
        en="Do it the way you want. I'm on your side.",
        notes="지지/응원, 감정적 안정감을 주는 표현.",
        vocab=[("하고 싶은 대로", "as you want"), ("편", "side/team"), ("네 편", "your side")],
        patterns=[("-대로", "‘~한 방식/그대로’ 의미"), ("-야", "친근한 해체 종결")],
    ),
    LineItem(
        show="(샘플) 로맨스",
        level="A2",
        kr="그렇게 보면 내가 설레잖아.",
        roman="Geureoke bomyeon naega seollee-jana.",
        en="If you look at me like that, you make my heart flutter.",
        notes="감정 표현(설레다). 친근한 말투 ‘-잖아’.",
        vocab=[("그렇게", "like that"), ("보다", "to look/see"), ("설레다", "to flutter/be excited")],
        patterns=[("-잖아", "이미 알고 있거나 당연함을 강조/투덜/설명")],
    ),
]


LEVELS = ["A1", "A2", "B1", "B2", "C1"]


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_state() -> None:
    ss = st.session_state
    ss.setdefault("profile", {"name": "학습자", "level": "A2", "goal": "K-드라마로 자연스러운 회화 익히기"})
    ss.setdefault("gemini_api_key", "")
    ss.setdefault("history", [])  # list[dict]
    ss.setdefault("saved_lines", [])  # list[dict]
    ss.setdefault("deck", [])  # quiz items
    ss.setdefault("deck_stats", {"correct": 0, "wrong": 0})


def add_history(event_type: str, payload: Dict) -> None:
    st.session_state.history.append({"ts": now_iso(), "type": event_type, "payload": payload})


def render_header() -> None:
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)


def sidebar_profile() -> None:
    st.sidebar.header("Gemini API Key")
    api_key = st.sidebar.text_input(
        "API 키를 입력하세요",
        value=st.session_state.get("gemini_api_key", ""),
        type="password",
        help="Gemini API 키를 입력하면 AI 기능을 사용할 수 있습니다.",
        key="gemini_api_key_input"
    )
    if api_key != st.session_state.get("gemini_api_key", ""):
        st.session_state.gemini_api_key = api_key.strip()
        if api_key.strip():
            try:
                if GEMINI_AVAILABLE:
                    genai.configure(api_key=api_key.strip())
                    st.sidebar.success("API 키가 설정되었습니다.")
                    add_history("api_key_set", {"status": "success"})
                else:
                    st.sidebar.warning("google-generativeai 패키지가 설치되지 않았습니다. requirements.txt를 확인하세요.")
            except Exception as e:
                st.sidebar.error(f"API 키 설정 오류: {str(e)}")
        else:
            st.sidebar.info("API 키가 제거되었습니다. 기본 규칙 기반 기능만 사용됩니다.")
    
    if st.session_state.get("gemini_api_key", ""):
        st.sidebar.success("✓ AI 기능 활성화됨")
    else:
        st.sidebar.info("ℹ 기본 모드 (규칙 기반)")
    
    st.sidebar.divider()
    st.sidebar.header("학습 설정")
    name = st.sidebar.text_input("이름", value=st.session_state.profile["name"])
    level = st.sidebar.selectbox("레벨", options=LEVELS, index=LEVELS.index(st.session_state.profile["level"]))
    goal = st.sidebar.text_area("목표", value=st.session_state.profile["goal"], height=80)
    if st.sidebar.button("설정 저장"):
        st.session_state.profile.update({"name": normalize_ws(name) or "학습자", "level": level, "goal": normalize_ws(goal)})
        add_history("profile_saved", dict(st.session_state.profile))
        st.sidebar.success("저장했어요.")

    st.sidebar.divider()
    st.sidebar.header("데이터")
    if st.sidebar.button("학습 기록 초기화"):
        st.session_state.history = []
        st.session_state.saved_lines = []
        st.session_state.deck = []
        st.session_state.deck_stats = {"correct": 0, "wrong": 0}
        st.sidebar.warning("기록/저장/덱을 초기화했어요.")


def line_picker(lines: List[LineItem], preferred_level: str) -> List[LineItem]:
    # 단순 필터: 레벨 <= 학습자 레벨(대략)만 노출
    idx = {lvl: i for i, lvl in enumerate(LEVELS)}
    p = idx.get(preferred_level, 1)
    return [x for x in lines if idx.get(x.level, 1) <= p]


def card_line(item: LineItem) -> None:
    st.subheader(f"{item.show} · {item.level}")
    st.markdown(f"**대사(KR)**: {item.kr}")
    st.markdown(f"**로마자**: {item.roman}")
    st.markdown(f"**의미(EN)**: {item.en}")
    if item.notes:
        st.info(item.notes)

    with st.expander("어휘(핵심 단어)"):
        for w, m in item.vocab:
            st.write(f"- **{w}**: {m}")

    with st.expander("패턴/문법 포인트"):
        for p, e in item.patterns:
            st.write(f"- **{p}**: {e}")

    # 고유한 키 생성 (대사 내용 기반)
    item_hash = hashlib.md5(f"{item.show}_{item.kr}".encode()).hexdigest()[:8]
    
    cols = st.columns(3)
    if cols[0].button("이 대사 저장", use_container_width=True, key=f"save_line_{item_hash}"):
        st.session_state.saved_lines.append(
            {"saved_at": now_iso(), "show": item.show, "level": item.level, "kr": item.kr, "roman": item.roman, "en": item.en}
        )
        add_history("line_saved", {"kr": item.kr, "show": item.show})
        st.success("저장했어요.")

    if cols[1].button("퀴즈에 추가", use_container_width=True, key=f"add_quiz_{item_hash}"):
        make_quiz_from_line(item)
        add_history("deck_add", {"kr": item.kr})
        st.success("덱에 추가했어요.")

    if cols[2].button("롤플레이 시작", use_container_width=True, key=f"start_roleplay_{item_hash}"):
        add_history("roleplay_start", {"kr": item.kr})
        st.session_state["roleplay_seed"] = {"kr": item.kr, "en": item.en}
        st.info("아래 ‘롤플레이’ 탭에서 진행해요.")


def make_quiz_from_line(item: LineItem) -> None:
    # 퀴즈: 빈칸 채우기(어휘/패턴 기반), 의미 맞히기(객관식/주관식)
    if not item.vocab:
        return
    key_word, _meaning = item.vocab[0]
    blanked = item.kr.replace(key_word, "____", 1)
    st.session_state.deck.append(
        {"type": "blank", "prompt": blanked, "answer": key_word, "source": item.kr, "show": item.show, "level": item.level}
    )
    st.session_state.deck.append(
        {"type": "meaning", "prompt": f"다음 대사의 의미를 한국어로 자연스럽게 설명해보세요:\n\n{item.kr}", "answer": item.en, "source": item.kr}
    )


def tab_home() -> None:
    st.header("대사 선택")
    profile = st.session_state.profile
    eligible = line_picker(SAMPLE_LINES, preferred_level=profile["level"])
    if not eligible:
        eligible = SAMPLE_LINES

    idx = st.selectbox(
        "샘플 대사",
        options=list(range(len(eligible))),
        format_func=lambda i: f"{eligible[i].level} · {eligible[i].kr}",
    )
    item = eligible[idx]
    card_line(item)

    st.divider()
    st.subheader("내 대사로 학습하기")
    user_line = st.text_area("드라마 대사(자막/대사) 붙여넣기", placeholder="예) 그건 아니지.", height=90)
    if st.button("이 대사로 학습 카드 만들기"):
        kr = normalize_ws(user_line)
        if not kr:
            st.error("대사를 입력해 주세요.")
            return
        generated = generate_support_card(kr, profile_level=profile["level"])
        add_history("custom_line_generated", {"kr": kr})
        card_line(generated)


def generate_support_card(kr: str, profile_level: str) -> LineItem:
    api_key = st.session_state.get("gemini_api_key", "").strip()
    
    # API 키가 있고 Gemini가 사용 가능하면 AI 사용
    if api_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""다음 한국어 드라마 대사를 분석해주세요. JSON 형식으로 답변해주세요.

대사: {kr}
학습자 레벨: {profile_level}

다음 형식으로 답변해주세요:
{{
    "roman": "로마자 발음 (예: Gwaenchana-yo?)",
    "en": "영어 번역",
    "notes": "대사의 맥락/의미 설명 (한국어)",
    "vocab": [["단어1", "의미1"], ["단어2", "의미2"]],
    "patterns": [["문법 패턴1", "설명1"], ["문법 패턴2", "설명2"]]
}}

핵심 어휘 3-5개와 중요한 문법 패턴 2-3개를 추출해주세요."""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # JSON 파싱 시도
            import json
            # 마크다운 코드 블록 제거
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            try:
                data = json.loads(result_text)
                roman = data.get("roman", simple_romanize_hint(kr))
                en = data.get("en", "의미를 분석 중입니다...")
                notes = data.get("notes", "대사 분석 결과입니다.")
                vocab = [tuple(v) if isinstance(v, list) else (v, "") for v in data.get("vocab", [])]
                patterns = [tuple(p) if isinstance(p, list) else (p, "") for p in data.get("patterns", [])]
                
                return LineItem(
                    show="(내 대사 - AI 분석)",
                    level=profile_level,
                    kr=kr,
                    roman=roman,
                    en=en,
                    notes=notes,
                    vocab=vocab[:6],
                    patterns=patterns[:6]
                )
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 사용
                pass
        
        except Exception as e:
            st.warning(f"AI 분석 중 오류가 발생했습니다. 기본 분석을 사용합니다: {str(e)}")
    
    # API 키가 없거나 오류 발생 시 규칙 기반 분석 사용
    roman = simple_romanize_hint(kr)
    en = "Meaning (auto): This is a placeholder gloss. (Gemini API 키를 입력하면 더 정확한 분석을 받을 수 있어요.)"
    vocab = extract_vocab_hints(kr)
    patterns = extract_pattern_hints(kr)
    notes = "입력한 대사로 학습 카드를 만들었어요. (로마자/의미는 간단 힌트이며, 필요하면 직접 수정해도 좋아요.)"
    return LineItem(show="(내 대사)", level=profile_level, kr=kr, roman=roman, en=en, notes=notes, vocab=vocab, patterns=patterns)


def simple_romanize_hint(kr: str) -> str:
    # 정확한 로마자 변환은 외부 라이브러리가 필요하므로, 초보자용 발음 힌트만 제공합니다.
    # 한글 모음/받침까지 완벽히 처리하진 않지만, 앱이 오프라인으로 바로 실행되도록 설계합니다.
    return "발음 힌트(간단): " + kr


COMMON_VOCAB: List[Tuple[str, str]] = [
    ("괜찮아", "괜찮다/OK"),
    ("괜찮아요", "괜찮습니다/OK"),
    ("진짜", "really"),
    ("지금", "now"),
    ("왜", "why"),
    ("어디", "where"),
    ("뭐", "what"),
    ("그냥", "just"),
    ("미안해", "sorry"),
    ("고마워", "thanks"),
    ("좋아", "good/like"),
]


def extract_vocab_hints(kr: str) -> List[Tuple[str, str]]:
    hits: List[Tuple[str, str]] = []
    for w, m in COMMON_VOCAB:
        if w in kr:
            hits.append((w, m))
    # 너무 비면, 길이 짧은 토큰 몇 개를 힌트로
    if not hits:
        tokens = re.findall(r"[가-힣]+", kr)
        for t in tokens[:3]:
            hits.append((t, "의미를 적어보세요"))
    # 중복 제거
    seen = set()
    out = []
    for w, m in hits:
        if w not in seen:
            seen.add(w)
            out.append((w, m))
    return out[:6]


PATTERN_RULES: List[Tuple[str, str]] = [
    ("겠", "추측/의지(예: 하겠어요)"),
    ("-게요", "의지/약속(부드럽게)"),
    ("-죠", "동의 기대/확인"),
    ("-잖아", "당연함/이미 앎 강조"),
    ("-지?", "확인/동의 요청(친근)"),
    ("-지 마", "금지(하지 마)"),
    ("-(으)ㄹ까", "제안/고민"),
    ("-(으)ㄹ래", "의향/제안(친근)"),
    ("-고 싶", "하고 싶다(희망)"),
]


def extract_pattern_hints(kr: str) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    if "게요" in kr:
        found.append(("-게요", "화자의 의지/약속 표현"))
    if "죠" in kr:
        found.append(("-죠?", "상대의 동의를 기대하며 확인"))
    if "잖아" in kr:
        found.append(("-잖아", "당연함/이미 앎 강조"))
    if "고 싶" in kr or "고싶" in kr:
        found.append(("-고 싶다", "희망/바람"))
    if not found:
        # 약한 규칙: 자주 등장하는 형태소/어미 힌트
        for key, exp in PATTERN_RULES:
            if key.replace("-", "") in kr:
                found.append((key, exp))
    # 중복 제거
    seen = set()
    out = []
    for p, e in found:
        if p not in seen:
            seen.add(p)
            out.append((p, e))
    return out[:6]


def tab_quiz() -> None:
    st.header("퀴즈")
    deck = st.session_state.deck
    stats = st.session_state.deck_stats

    if not deck:
        st.info("아직 퀴즈 덱이 비어있어요. ‘대사 선택’에서 ‘퀴즈에 추가’를 눌러주세요.")
        return

    st.caption(f"덱 카드: {len(deck)} · 정답 {stats['correct']} / 오답 {stats['wrong']}")

    # 매번 섞지 않고, 현재 인덱스를 세션에 저장
    st.session_state.setdefault("quiz_i", 0)
    i = st.session_state.quiz_i % len(deck)
    q = deck[i]

    st.subheader(f"문항 {i+1} / {len(deck)}")
    st.write(q["prompt"])

    user = st.text_input("답", key=f"quiz_answer_{i}")
    cols = st.columns(3)
    if cols[0].button("채점", use_container_width=True):
        ok = grade_answer(q, user)
        if ok:
            stats["correct"] += 1
            add_history("quiz_correct", {"i": i, "type": q["type"], "source": q.get("source", "")})
            st.success("정답!")
        else:
            stats["wrong"] += 1
            add_history("quiz_wrong", {"i": i, "type": q["type"], "source": q.get("source", "")})
            st.error(f"아쉬워요. 정답 힌트: {q['answer']}")

    if cols[1].button("다음", use_container_width=True):
        st.session_state.quiz_i = (st.session_state.quiz_i + 1) % len(deck)
        st.rerun()

    if cols[2].button("이 문항 삭제", use_container_width=True):
        deck.pop(i)
        add_history("quiz_remove", {"i": i})
        st.session_state.quiz_i = 0
        st.rerun()


def grade_answer(q: Dict, user: str) -> bool:
    u = normalize_ws(user).lower()
    a = normalize_ws(str(q.get("answer", ""))).lower()
    if not u:
        return False
    if q.get("type") == "blank":
        return u == a
    # meaning(주관식): 영어 의미 키워드 일부 포함이면 정답 처리(관대하게)
    # (오프라인 규칙 기반이라 완벽하지 않음)
    tokens = [t for t in re.findall(r"[a-z]+", a) if len(t) >= 4]
    hit = sum(1 for t in tokens[:6] if t in u)
    return hit >= max(1, min(2, len(tokens[:6]) // 2))


def tab_roleplay() -> None:
    st.header("롤플레이")
    profile = st.session_state.profile
    seed = st.session_state.get("roleplay_seed")

    st.write("상황을 정하고, 대사 스타일을 ‘K-드라마 톤’으로 연습해요.")
    situation = st.text_input("상황", value="카페에서 우연히 만남")
    your_role = st.text_input("내 역할", value="손님")
    other_role = st.text_input("상대 역할", value="알바/직원")
    tone = st.selectbox("톤", ["로코", "스릴러", "휴먼", "사극(현대어)", "차분한 현실 대화"])

    st.divider()
    if seed:
        st.caption("선택한 대사 기반으로 시작할게요.")
        st.write(f"- 시작 대사: **{seed['kr']}**")

    user_msg = st.text_area("내가 말할 대사(한국어)", placeholder="예) 아메리카노 한 잔 주세요.", height=90)
    if st.button("코칭 받기"):
        msg = normalize_ws(user_msg)
        if not msg:
            st.error("대사를 입력해 주세요.")
            return
        feedback = coach_message(msg, profile_level=profile["level"], tone=tone)
        add_history("roleplay_coach", {"msg": msg, "tone": tone})
        st.subheader("코칭")
        st.write(feedback["one_liner"])
        st.write("**더 자연스러운 대사 제안**")
        for s in feedback["suggestions"]:
            st.write(f"- {s}")
        st.write("**포인트**")
        for p in feedback["points"]:
            st.write(f"- {p}")


def coach_message(msg: str, profile_level: str, tone: str) -> Dict:
    api_key = st.session_state.get("gemini_api_key", "").strip()
    
    # API 키가 있고 Gemini가 사용 가능하면 AI 사용
    if api_key and GEMINI_AVAILABLE:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""다음 한국어 대사를 K-드라마 {tone} 톤으로 개선해주세요.

원본 대사: {msg}
학습자 레벨: {profile_level}
드라마 톤: {tone}

다음 형식으로 JSON으로 답변해주세요:
{{
    "one_liner": "한 줄 코칭 메시지 (한국어)",
    "suggestions": ["개선된 대사 1", "개선된 대사 2", "개선된 대사 3"],
    "points": ["포인트 1", "포인트 2", "포인트 3"]
}}

더 자연스럽고 드라마틱한 표현으로 개선해주세요. 학습자 레벨에 맞는 어휘와 문법을 사용해주세요."""
            
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # JSON 파싱 시도
            import json
            # 마크다운 코드 블록 제거
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            try:
                data = json.loads(result_text)
                return {
                    "one_liner": data.get("one_liner", f"({tone} 톤) 대사를 분석했습니다."),
                    "suggestions": data.get("suggestions", [msg])[:6],
                    "points": data.get("points", [])[:6]
                }
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 사용
                pass
        
        except Exception as e:
            st.warning(f"AI 코칭 중 오류가 발생했습니다. 기본 코칭을 사용합니다: {str(e)}")
    
    # API 키가 없거나 오류 발생 시 규칙 기반 코칭 사용
    suggestions = []
    points = []

    polite = any(x in msg for x in ["요", "주세요", "합니다", "해요"])
    if profile_level in ["A1", "A2"] and not polite:
        suggestions.append(msg + "요")
        points.append("초급에서는 ‘-요’ 체로 말하면 안전해요.")

    if "진짜" in msg and tone in ["로코", "스릴러"]:
        points.append("‘진짜’는 드라마 톤에서 감정 강조에 자주 써요.")

    if msg.endswith("?"):
        points.append("질문 끝을 올리는 억양을 상상해보세요.")

    # 톤별 감정 단어 힌트
    if tone == "로코":
        suggestions.extend([msg, msg.replace("요", "요..."), "아니, 잠깐만요. " + msg])
        points.append("로코는 ‘머뭇/여운’(… )을 넣으면 느낌이 살아나요.")
    elif tone == "스릴러":
        suggestions.extend([msg, "지금 " + msg, "당장 " + msg])
        points.append("짧고 단호한 부사(지금/당장/바로)가 긴장감을 만들어요.")
    elif tone == "휴먼":
        suggestions.extend([msg, "괜찮아요. " + msg, "천천히 해도 돼요. " + msg])
        points.append("휴먼물은 공감/배려 표현을 먼저 두면 자연스러워요.")
    elif tone.startswith("사극"):
        suggestions.extend(["송구하오나, " + msg, "부디, " + msg])
        points.append("사극 톤은 어휘를 살짝 바꾸는 것만으로도 분위기가 나요.")
    else:
        suggestions.extend([msg, "혹시 " + msg, msg + " 괜찮을까요?"])
        points.append("현실 대화는 완곡 표현(혹시/괜찮을까요?)이 도움돼요.")

    # 중복 제거
    dedup = []
    seen = set()
    for s in suggestions:
        s2 = normalize_ws(s)
        if s2 and s2 not in seen:
            seen.add(s2)
            dedup.append(s2)

    one_liner = f"({tone} 톤) 핵심은 **리듬**과 **감정 단어**예요. 지금 문장은 충분히 좋아요—조금만 다듬어볼게요. (Gemini API 키를 입력하면 더 정확한 코칭을 받을 수 있어요.)"
    return {"one_liner": one_liner, "suggestions": dedup[:6], "points": points[:6]}


def tab_saved() -> None:
    st.header("저장한 대사")
    saved = st.session_state.saved_lines
    if not saved:
        st.info("저장한 대사가 없어요. ‘대사 선택’에서 ‘이 대사 저장’을 눌러주세요.")
        return

    for i, item in enumerate(reversed(saved), start=1):
        st.markdown(f"**{i}. {item['kr']}**  \n{item['show']} · {item['level']} · 저장: {item['saved_at']}")

    st.divider()
    if st.button("저장 목록 내보내기(JSON)"):
        add_history("saved_export", {"count": len(saved)})
        st.download_button(
            label="다운로드",
            data=str(saved).encode("utf-8"),
            file_name="saved_lines.json",
            mime="application/json",
        )


def tab_history() -> None:
    st.header("학습 기록")
    hist = st.session_state.history
    if not hist:
        st.info("아직 기록이 없어요.")
        return
    st.caption("최근 기록이 아래에 표시됩니다.")
    for h in hist[-80:][::-1]:
        st.write(f"- {h['ts']} · **{h['type']}** · {h['payload']}")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🎬", layout="wide")
    init_state()
    render_header()
    sidebar_profile()

    tabs = st.tabs(["대사 선택", "퀴즈", "롤플레이", "저장한 대사", "학습 기록"])
    with tabs[0]:
        tab_home()
    with tabs[1]:
        tab_quiz()
    with tabs[2]:
        tab_roleplay()
    with tabs[3]:
        tab_saved()
    with tabs[4]:
        tab_history()

    st.caption("팁: 더 정확한 의미/로마자/설명을 원하면, API 연동 버전으로 업그레이드할 수 있어요.")


if __name__ == "__main__":
    main()

