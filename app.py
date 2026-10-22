"""
세아특수강 CDM 봉강생산팀 — FIX 2026 3D 스마트 참관 네비게이터
Streamlit Cloud 배포판

● 기존 cdm_fix_2026_3d.py 의 OSError 원인
  Streamlit Cloud 컨테이너는 애플리케이션이 직접 소켓 포트를 bind 하는 것을 허용하지 않는다.
  (http.server.HTTPServer((HOST, 8080), ...) → self.socket.bind() → OSError)
  따라서 HTTPServer 를 전부 걷어내고, Streamlit 자체 웹서버 위에
  커스텀 컴포넌트(iframe) + SQLite 로 동일한 기능을 재구성했다.

● 저장 구조 (자동 하이브리드)
  1차 : 브라우저 localStorage  — 전시장에서 네트워크가 끊겨도 아이디어가 보존된다
  2차 : 서버 SQLite           — 컴포넌트가 미동기화 건을 올려 보내면 즉시 INSERT
  재연결되면 미동기화 건이 자동으로 올라가고, 상단 아일랜드 바에 접속 상태가 표시된다.

● 배포 방법 (GitHub → share.streamlit.io)
  레포지토리에 아래 3개 파일만 올리면 된다.
    app.py
    seah_fix2026_navigator.html
    requirements.txt
  Main file path 는 app.py 로 지정한다.

  ※ Streamlit Community Cloud 의 디스크는 재부팅/재배포 시 초기화된다.
    SQLite 는 "현장 수집 중 공용 집계" 용도이며, 영구 보관은
    사이드바의 CSV 내려받기(또는 앱 안 아이디어함 → 엑셀 CSV)로 확보할 것.
    각 팀원 휴대폰의 localStorage 사본은 초기화되지 않으므로 이중 안전망이 된다.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

APP_DIR = Path(__file__).parent.resolve()
HTML_FILE = APP_DIR / "seah_fix2026_navigator.html"
DB_PATH = Path(os.environ.get("SEAH_DB_PATH", APP_DIR / "seah_fix_ideas.db"))

CSV_COLUMNS = [
    "순번", "부스번호", "부스/기업명", "작성자",
    "소속공정", "제안아이디어", "기대효과", "등록일시",
]

st.set_page_config(
    page_title="세아특수강 CDM · FIX 2026 3D 네비게이터",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ──────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────
def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_resource(show_spinner=False)
def init_database() -> str:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ideas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid        TEXT UNIQUE,
                booth_step  INTEGER,
                booth_id    TEXT,
                booth_name  TEXT,
                author      TEXT NOT NULL,
                factory     TEXT NOT NULL,
                idea_text   TEXT NOT NULL,
                benefits    TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_step ON ideas(booth_step)")
        conn.commit()
    return str(DB_PATH)


def fetch_ideas() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, booth_step, booth_id, booth_name, author, factory, "
            "idea_text, benefits, created_at FROM ideas ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def insert_ideas(payload: list[dict]) -> int:
    """컴포넌트가 올려 보낸 미동기화 건을 INSERT. 중복 uuid 는 무시. 신규 건수를 반환."""
    if not payload:
        return 0
    inserted = 0
    with connect() as conn:
        for row in payload:
            if not isinstance(row, dict):
                continue
            uuid = str(row.get("uuid") or "").strip()
            author = str(row.get("author") or "").strip()
            idea_text = str(row.get("idea_text") or "").strip()
            if not uuid or not author or not idea_text:
                continue
            try:
                step = int(row.get("booth_step"))
            except (TypeError, ValueError):
                step = None
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO ideas
                    (uuid, booth_step, booth_id, booth_name,
                     author, factory, idea_text, benefits, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid[:120],
                    step,
                    str(row.get("booth_id") or "")[:40],
                    str(row.get("booth_name") or "")[:200],
                    author[:60],
                    str(row.get("factory") or "")[:120],
                    idea_text[:4000],
                    str(row.get("benefits") or "")[:600],
                    str(row.get("created_at") or "")[:40]
                    or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            inserted += cur.rowcount or 0
        conn.commit()
    return inserted


def build_csv(rows: list[dict]) -> bytes:
    """엑셀에서 한글이 깨지지 않도록 UTF-8 BOM 을 붙인 CSV."""
    ordered = sorted(rows, key=lambda r: (r.get("booth_step") or 99))

    def q(v) -> str:
        return '"' + str(v if v is not None else "").replace('"', '""') + '"'

    out = ["﻿" + ",".join(CSV_COLUMNS)]
    for i, r in enumerate(ordered, start=1):
        out.append(
            ",".join(
                [
                    str(i),
                    q(r.get("booth_id")),
                    q(r.get("booth_name")),
                    q(r.get("author")),
                    q(r.get("factory")),
                    q(r.get("idea_text")),
                    q(r.get("benefits")),
                    q(r.get("created_at")),
                ]
            )
        )
    return ("\n".join(out) + "\n").encode("utf-8")


# ──────────────────────────────────────────────────────────────────────
# CUSTOM COMPONENT  (HTTPServer 대체)
# ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_navigator():
    """
    단일 HTML 을 Streamlit 커스텀 컴포넌트로 등록한다.
    declare_component 가 막힌 환경에서는 components.html 로 자동 강등된다
    (이 경우 저장은 브라우저 localStorage 전용으로 동작한다).
    """
    if not HTML_FILE.exists():
        return None, "missing"

    html = HTML_FILE.read_text(encoding="utf-8")
    try:
        root = Path(tempfile.gettempdir()) / "seah_fix2026_component"
        root.mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(html, encoding="utf-8")
        component = components.declare_component("seah_fix2026_nav", path=str(root))
        return component, "component"
    except Exception:
        return html, "iframe"


def render_navigator(component, mode: str, server_ideas: list[dict]):
    if mode == "missing":
        st.error(
            "seah_fix2026_navigator.html 파일을 찾을 수 없습니다. "
            "app.py 와 같은 폴더에 함께 업로드해 주세요."
        )
        return None
    if mode == "iframe":
        render_html = getattr(st, "iframe", None) or components.html
        render_html(component, height=820, scrolling=False)
        return None
    return component(ideas=server_ideas, key="seah_nav_component", default=None)


# ──────────────────────────────────────────────────────────────────────
# LAYOUT — 전체 화면 몰입형 (Streamlit 기본 크롬 제거)
# ──────────────────────────────────────────────────────────────────────
FULLBLEED_CSS = """
<style>
  #MainMenu, header[data-testid="stHeader"], footer, .stAppDeployButton {visibility:hidden; height:0;}
  .stApp {background:#050811;}
  .block-container, section.main > div.block-container {
      padding:0 !important; margin:0 !important; max-width:100% !important;
  }
  div[data-testid="stAppViewBlockContainer"] {padding:0 !important;}
  iframe[title*="seah_fix2026_nav"] {
      width:100vw !important; min-height:100dvh !important; border:0 !important; display:block;
  }
  div[data-testid="stSidebarCollapsedControl"] {z-index:90;}
  div[data-testid="stToast"] {z-index:95;}
</style>
"""

st.markdown(FULLBLEED_CSS, unsafe_allow_html=True)

db_path = init_database()
component, mode = load_navigator()
server_ideas = fetch_ideas()

returned = render_navigator(component, mode, server_ideas)

# 컴포넌트가 올려 보낸 미동기화 아이디어를 SQLite 에 반영
if isinstance(returned, dict):
    new_rows = returned.get("ideas") or []
    if isinstance(new_rows, str):
        try:
            new_rows = json.loads(new_rows)
        except json.JSONDecodeError:
            new_rows = []
    added = insert_ideas(new_rows if isinstance(new_rows, list) else [])
    if added:
        st.rerun()


# ──────────────────────────────────────────────────────────────────────
# SIDEBAR — 관리자용 집계 / 백업
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📦 수집 현황")
    rows = fetch_ideas()
    visited = {r["booth_step"] for r in rows if r.get("booth_step")}
    c1, c2 = st.columns(2)
    c1.metric("총 아이디어", f"{len(rows)}건")
    c2.metric("작성 부스", f"{len(visited)}/11")

    st.download_button(
        "⬇️ 전체 CSV 내려받기 (엑셀)",
        data=build_csv(rows),
        file_name=f"SeAH_CDM_FIX2026_ideas_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=not rows,
    )

    if rows:
        with st.expander("목록 미리보기", expanded=False):
            st.dataframe(
                [
                    {
                        "부스": f'{r["booth_step"] or "-"}. {r["booth_id"] or ""}',
                        "기업": r["booth_name"],
                        "작성자": r["author"],
                        "아이디어": r["idea_text"],
                        "등록": r["created_at"],
                    }
                    for r in rows
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    st.caption(f"DB: `{db_path}`")
    if mode == "iframe":
        st.warning(
            "커스텀 컴포넌트를 등록하지 못해 브라우저 저장 전용으로 동작합니다. "
            "아이디어는 각 기기의 아이디어함에 보관되며 앱 안에서 CSV 로 내려받을 수 있습니다.",
            icon="⚠️",
        )
    else:
        st.caption(
            "Streamlit Cloud 디스크는 재배포 시 초기화됩니다. "
            "참관 종료 후 CSV 를 반드시 내려받아 보관하세요."
        )
