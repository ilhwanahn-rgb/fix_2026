import os
import sys
import json
import sqlite3
import socket
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Default Server Configuration
HOST = "0.0.0.0"
PORT = 8080
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seah_fix_ideas.db")

def init_database():
    """Initializes the SQLite database schema to permanently store ideas."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE,
                booth_step INTEGER,
                booth_id TEXT,
                booth_name TEXT,
                author TEXT NOT NULL,
                factory TEXT NOT NULL,
                idea_text TEXT NOT NULL,
                benefits TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="세아 FIX 네비">
  <meta name="theme-color" content="#0b0f19">
  <title>세아특수강 CDM 봉강생산팀 FIX 2026 3D 스마트 참관 네비게이터</title>
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- FontAwesome Icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <!-- Three.js & OrbitControls -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
  <!-- GSAP for smooth animations -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&display=swap');
    * {
      font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
      -webkit-tap-highlight-color: transparent;
      box-sizing: border-box;
      touch-action: manipulation;
    }
    body, html {
      margin: 0; padding: 0; width: 100%; height: 100%;
      overflow: hidden; background-color: #0b0f19;
      overscroll-behavior-y: none; -webkit-user-select: none; user-select: none;
    }
    #webgl-canvas {
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      z-index: 1; display: block; outline: none; touch-action: none;
    }
    .glass-panel {
      background: rgba(15, 23, 42, 0.92);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    #booth-detail-card {
      transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.28s ease;
      padding-bottom: max(1.25rem, env(safe-area-inset-bottom));
    }
    #booth-detail-card.panel-collapsed {
      transform: translateY(calc(100% + 20px));
      opacity: 0; pointer-events: none;
    }
    @media (min-width: 640px) {
      #booth-detail-card.panel-collapsed {
        transform: translateX(calc(-100% - 20px));
        opacity: 0.2; pointer-events: none;
      }
    }
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
  </style>
</head>
<body class="text-slate-100 select-none overflow-hidden">

  <!-- 3D WebGL Canvas -->
  <canvas id="webgl-canvas"></canvas>

  <!-- Top Header Navigation Bar -->
  <header class="absolute top-0 left-0 right-0 z-20 pt-[max(0.5rem,env(safe-area-inset-top))] px-2.5 sm:px-4 pb-2 flex items-center justify-between pointer-events-none">
    <div class="flex items-center space-x-2 pointer-events-auto">
      <div class="glass-panel px-2.5 py-1.5 sm:px-3.5 sm:py-2 rounded-2xl flex items-center gap-2 shadow-xl border border-slate-700/60">
        <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-black text-white text-xs sm:text-base shadow-lg shadow-blue-500/30">
          S
        </div>
        <div>
          <div class="flex items-center gap-1.5">
            <span class="text-[9px] sm:text-[11px] font-bold tracking-wider text-blue-400 uppercase">SeAH CDM</span>
            <span class="px-1.5 py-0.2 rounded text-[8px] sm:text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 font-medium">FIX 2026</span>
            <span class="px-1.5 py-0.2 rounded text-[8px] sm:text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">Python Server</span>
          </div>
          <h1 class="text-[11px] sm:text-sm font-bold text-white tracking-tight">봉강생산팀 3D 네비게이터</h1>
        </div>
      </div>
    </div>

    <!-- Quick Action Tool Buttons -->
    <div class="flex items-center space-x-1 sm:space-x-2 pointer-events-auto">
      <!-- Idea Collection Viewer Button -->
      <button id="btn-open-ideas-board" type="button" class="glass-panel hover:bg-slate-800 active:scale-95 transition-all text-xs font-bold px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-xl text-amber-300 border-amber-500/40 flex items-center gap-1.5 shadow-xl bg-amber-500/10">
        <i class="fa-solid fa-database text-amber-400"></i>
        <span class="hidden sm:inline">아이디어함</span>
        <span id="idea-count-badge" class="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500 text-slate-950 font-black">0</span>
      </button>

      <!-- Rapid Add Idea Trigger -->
      <button id="btn-open-form-direct" type="button" class="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-95 transition-all text-xs font-bold px-3 py-1.5 sm:py-2 rounded-xl text-white shadow-lg shadow-blue-600/30 flex items-center gap-1.5 border border-blue-400/30">
        <i class="fa-solid fa-lightbulb text-yellow-300"></i>
        <span>등록</span>
      </button>
    </div>
  </header>

  <!-- Left Dock Toggle Tab -->
  <button id="btn-dock-expand" type="button" class="fixed top-16 sm:top-24 left-2 z-30 px-3 py-2 rounded-xl glass-panel text-amber-300 font-bold text-xs flex items-center gap-1.5 shadow-2xl border-amber-500/40 hover:bg-slate-800 transition-all opacity-0 pointer-events-none">
    <i class="fa-solid fa-angles-right text-amber-400"></i>
    <span id="dock-expand-label">부스 상세 보기</span>
  </button>

  <!-- Floating Viewport Controls -->
  <div class="absolute top-16 sm:top-20 right-2 sm:right-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
    <div class="glass-panel p-1 rounded-2xl flex flex-col gap-1 shadow-2xl">
      <button id="btn-view-iso" type="button" title="입체 조감도 (3D)" class="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold bg-blue-600 text-white shadow-lg shadow-blue-500/30 transition-all">3D</button>
      <button id="btn-view-top" type="button" title="평면 2D 맵" class="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold text-slate-400 hover:bg-slate-700 hover:text-white transition-all">2D</button>
      <button id="btn-reset-cam" type="button" title="시점 원위치" class="w-8 h-8 rounded-xl flex items-center justify-center text-xs text-slate-400 hover:bg-slate-700 hover:text-white transition-all"><i class="fa-solid fa-compress"></i></button>
    </div>
    <div class="glass-panel p-1 rounded-2xl flex flex-col gap-1 shadow-2xl">
      <button id="btn-toggle-route" type="button" title="최적 동선 토글" class="w-8 h-8 rounded-xl flex items-center justify-center text-xs text-emerald-400 bg-emerald-500/20 border border-emerald-500/40 hover:bg-emerald-500 hover:text-white transition-all"><i class="fa-solid fa-route"></i></button>
      <button id="btn-auto-tour" type="button" title="1~11번 자동 투어" class="w-8 h-8 rounded-xl flex items-center justify-center text-xs text-amber-400 bg-amber-500/20 border border-amber-500/40 hover:bg-amber-500 hover:text-white transition-all"><i class="fa-solid fa-play"></i></button>
    </div>
  </div>

  <!-- Bottom Step Navigator Bar -->
  <div class="absolute bottom-1 sm:bottom-3 left-1/2 -translate-x-1/2 z-20 w-[96%] max-w-4xl pb-[max(0.25rem,env(safe-area-inset-bottom))] pointer-events-auto">
    <div class="glass-panel p-2 sm:p-3 rounded-2xl sm:rounded-3xl shadow-2xl border border-slate-700/80 flex flex-col gap-1.5 sm:gap-2">
      <div class="flex items-center justify-between gap-1 sm:gap-2">
        <div class="flex items-center gap-1 shrink-0">
          <span class="px-2 py-0.5 rounded-lg bg-blue-600/30 text-blue-300 border border-blue-500/40 text-[9px] sm:text-[11px] font-bold flex items-center gap-1">
            <i class="fa-solid fa-arrow-right-long text-blue-400"></i>
            <span>동선 (1~11)</span>
          </span>
        </div>
        <div id="step-buttons-container" class="flex items-center gap-1 overflow-x-auto no-scrollbar py-0.5"></div>
      </div>

      <div class="flex items-center justify-between gap-1.5 pt-1.5 border-t border-slate-800/90">
        <button id="btn-prev-step" type="button" class="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 text-xs text-slate-300 font-semibold flex items-center gap-1 transition-all">
          <i class="fa-solid fa-chevron-left"></i>
          <span class="hidden sm:inline">이전</span>
        </button>
        <div id="current-step-indicator" class="flex-1 text-center truncate px-1 cursor-pointer hover:opacity-90 active:scale-98 transition-all">
          <span class="text-amber-400 font-bold text-xs" id="nav-step-num">[1/11]</span>
          <span class="text-sky-300 font-mono font-black text-xs ml-0.5 px-1 py-0.5 rounded bg-sky-950/70 border border-sky-500/40" id="nav-step-booth-id">W2-219</span>
          <span class="text-white font-bold text-xs sm:text-sm ml-1" id="nav-step-title">원프레딕트</span>
        </div>
        <button id="btn-log-current-booth" type="button" class="px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 active:scale-95 text-xs text-slate-950 font-black flex items-center gap-1 shadow-lg shadow-amber-500/20 transition-all">
          <i class="fa-solid fa-pen-to-square"></i>
          <span>아이디어</span>
        </button>
        <button id="btn-next-step" type="button" class="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:scale-95 text-xs text-white font-bold flex items-center gap-1 shadow-lg shadow-blue-600/30 transition-all">
          <span class="hidden sm:inline">다음</span>
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>

  <!-- Booth Strategy Card (Streamlined) -->
  <div id="booth-detail-card" class="fixed bottom-0 sm:bottom-auto sm:top-20 sm:left-4 z-30 w-full sm:w-[410px] max-h-[70vh] sm:max-h-[calc(100vh-175px)] glass-panel rounded-t-3xl sm:rounded-2xl p-4 sm:p-5 shadow-2xl border-t sm:border border-slate-700/80 translate-y-full sm:translate-y-0 sm:opacity-0 sm:pointer-events-none overflow-y-auto">
    <div class="w-12 h-1 bg-slate-600/80 rounded-full mx-auto mb-2.5 sm:hidden cursor-pointer" id="drag-handle-sheet"></div>
    <div class="flex items-start justify-between pb-2.5 border-b border-slate-700/60">
      <div>
        <div class="flex items-center gap-1.5 mb-1 flex-wrap">
          <span id="detail-step-badge" class="px-2 py-0.5 rounded text-[10px] font-black bg-blue-600 text-white">1번 부스</span>
          <span id="detail-track-badge" class="px-2 py-0.5 rounded text-[9px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">T3. AI 예지보전</span>
          <span id="detail-booth-id" class="px-2.5 py-0.5 rounded-lg text-xs font-black font-mono bg-amber-400/20 text-amber-300 border border-amber-400/50 shadow-sm">W2-219</span>
        </div>
        <h3 id="detail-company" class="text-sm sm:text-lg font-black text-white tracking-tight">원프레딕트</h3>
      </div>
      <div class="flex items-center gap-1">
        <button id="btn-collapse-panel" type="button" title="패널 접기" class="w-7 h-7 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-xs transition-all"><i class="fa-solid fa-angles-down sm:fa-angles-left"></i></button>
        <button id="btn-close-detail" type="button" title="닫기" class="w-7 h-7 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-xs transition-all"><i class="fa-solid fa-xmark"></i></button>
      </div>
    </div>
    <div class="mt-2.5 space-y-2.5 text-xs">
      <div>
        <h4 class="text-slate-400 font-semibold mb-1 flex items-center gap-1.5"><i class="fa-solid fa-industry text-blue-400"></i> 세아특수강 CDM 공정 접목 포인트</h4>
        <p id="detail-process" class="text-slate-200 bg-slate-800/70 p-2.5 rounded-xl leading-relaxed border border-slate-700/50">CDM 메인 인발 캐리지 감속기 & 2롤 교정기 베어링 진단</p>
      </div>
      <div>
        <h4 class="text-slate-400 font-semibold mb-1 flex items-center gap-1.5"><i class="fa-solid fa-binoculars text-emerald-400"></i> 현장 핵심 관전 포인트</h4>
        <p id="detail-highlight" class="text-slate-300 leading-relaxed bg-slate-900/40 p-2.5 rounded-xl border border-slate-800/60">국내 1위 산업 AI 예지보전 GuardiOne 딥러닝 기반 베어링 편마모 예측</p>
      </div>
    </div>
    <div class="mt-3 pt-2.5 border-t border-slate-700/60 flex flex-col gap-2">
      <div class="flex items-center justify-between text-[11px] text-slate-400 px-1">
        <span>다음 목적지: <strong id="detail-next-target" class="text-blue-300">2. 그룸깃다</strong></span>
        <button id="btn-detail-go-next" type="button" class="text-blue-400 hover:underline flex items-center gap-1 font-semibold">바로 이동 <i class="fa-solid fa-arrow-right"></i></button>
      </div>
      <div class="flex gap-2">
        <button id="btn-detail-to-form" type="button" class="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-black text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-amber-500/20 active:scale-95 transition-all">
          <i class="fa-solid fa-bolt"></i> 이 부스로 즉시 아이디어 등록
        </button>
        <button id="btn-focus-booth" type="button" class="py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold active:scale-95 transition-all"><i class="fa-solid fa-crosshairs"></i> 시점</button>
      </div>
    </div>
  </div>

  <!-- Rapid Idea Entry Modal -->
  <div id="modal-idea-form" class="fixed inset-0 z-40 bg-black/80 backdrop-blur-md flex items-end sm:items-center justify-center p-0 sm:p-4 opacity-0 pointer-events-none transition-all duration-300">
    <div class="w-full sm:max-w-lg glass-panel rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl border border-slate-700/80 max-h-[92vh] overflow-y-auto transform translate-y-8 transition-all duration-300 pb-[max(1rem,env(safe-area-inset-bottom))]">
      <div class="flex items-center justify-between pb-2.5 border-b border-slate-700/60">
        <div class="flex items-center gap-2">
          <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center text-sm sm:text-base font-bold border border-amber-500/30">
            <i class="fa-solid fa-lightbulb"></i>
          </div>
          <div>
            <h2 class="text-xs sm:text-base font-bold text-white">현장 아이디어 즉시 등록 (DB 영구저장)</h2>
            <p class="text-[10px] sm:text-[11px] text-slate-400">등록 시 서버 DB에 실시간 안전하게 저장됩니다</p>
          </div>
        </div>
        <button id="btn-close-form" type="button" class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center text-base"><i class="fa-solid fa-xmark"></i></button>
      </div>

      <form id="lean-idea-form" class="mt-3 space-y-3">
        <div>
          <label class="block text-[11px] font-semibold text-slate-300 mb-1">1. 작성자 및 소속 <span class="text-amber-400">*</span></label>
          <div class="grid grid-cols-2 gap-2">
            <input type="text" id="form-author" required placeholder="이름 (자동 기억)" class="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-2.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
            <select id="form-factory" class="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-2 py-2 text-[11px] text-white focus:outline-none focus:border-blue-500">
              <option value="포항-CDM 1라인(마봉강 인발)">포항 - CDM 1라인</option>
              <option value="포항-CDM 2라인(마봉강 인발)">포항 - CDM 2라인</option>
              <option value="포항-2롤 교정/정정">포항 - 2롤 교정/정정</option>
              <option value="포항-면취/포장/출하">포항 - 면취/포장/출하</option>
              <option value="포항-봉강 설비보전/공무">포항 - 보전/공무</option>
              <option value="충주-봉강 생산라인">충주 - 봉강라인</option>
              <option value="품질보증/생관/기술">품질/생관/기술</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-semibold text-slate-300 mb-1">2. 해당 부스 / 기업명 <span class="text-amber-400">*</span></label>
          <input type="text" id="form-booth" required placeholder="부스 선택" class="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-2.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500">
          <div class="flex flex-wrap gap-1 mt-1.5" id="fast-booth-chips"></div>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-[11px] font-semibold text-slate-300">3. CDM 공정 적용 아이디어 <span class="text-amber-400">*</span></label>
            <button id="btn-voice-input" type="button" class="px-2.5 py-0.5 rounded-lg bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 hover:bg-indigo-600 hover:text-white text-[10px] font-bold flex items-center gap-1 transition-all active:scale-95">
              <i class="fa-solid fa-microphone text-indigo-400" id="voice-mic-icon"></i>
              <span id="voice-btn-label">말해서 입력</span>
            </button>
          </div>

          <div class="flex flex-wrap gap-1 mb-1.5" id="quick-cdm-tags">
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="CDM 인발 캐리지 감속기 진동 예지보전 센서 부착">⚙️ 인발 감속기</button>
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="2롤 교정기 고속 회전 롤러 베어링 실시간 진단">🔄 2롤 교정기</button>
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="4~6m 장척 봉강 번들 결속 및 캡핑 협동로봇 적용">🤖 번들 결속 로봇</button>
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="경면 마봉강 표면 롤마크/크랙 인라인 3D 비전 검사">🔍 표면 롤마크 비전</button>
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="봉강 랙 공장 내 자동 반송 자율주행 AMR 물류 도입">🚚 장척물 AMR</button>
            <button type="button" class="cdm-tag-btn px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300 hover:bg-slate-700" data-text="전기차 감속기 샤프트용 고청정 마봉강 품질 벤치마킹">⚡ 전기차 샤프트</button>
          </div>

          <textarea id="form-idea" rows="3" required placeholder="위 태그를 누르거나 마이크 버튼을 눌러 음성으로 입력하세요." class="w-full bg-slate-800/90 border border-slate-700 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 leading-relaxed"></textarea>
        </div>

        <div>
          <label class="block text-[11px] font-semibold text-slate-300 mb-1">4. 예상 기대 효과 (중복 선택)</label>
          <div class="grid grid-cols-2 gap-1.5" id="benefit-checkboxes">
            <label class="flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/80 cursor-pointer text-[10px] text-slate-200">
              <input type="checkbox" name="benefit" value="장척 봉강(4~6m) 취급 끼임 차단" class="accent-blue-500 rounded">
              <span>🛡️ 장척물 취급 안전</span>
            </label>
            <label class="flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/80 cursor-pointer text-[10px] text-slate-200">
              <input type="checkbox" name="benefit" value="CDM 캐리지·교정기 돌발정지 제로" class="accent-blue-500 rounded" checked>
              <span>⚙️ 설비 돌발정지 방지</span>
            </label>
            <label class="flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/80 cursor-pointer text-[10px] text-slate-200">
              <input type="checkbox" name="benefit" value="마봉강 표면 롤마크/결함 전수 검출" class="accent-blue-500 rounded">
              <span>🔍 롤마크/결함 검출</span>
            </label>
            <label class="flex items-center gap-1.5 p-1.5 rounded-xl bg-slate-800/60 border border-slate-700/80 cursor-pointer text-[10px] text-slate-200">
              <input type="checkbox" name="benefit" value="육각 번들링·스트랩 결속 무인화" class="accent-blue-500 rounded">
              <span>🤖 번들 결속 자동화</span>
            </label>
          </div>
        </div>

        <div class="pt-1">
          <button type="submit" id="btn-submit-idea" class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 hover:opacity-95 active:scale-95 text-slate-950 font-black text-xs sm:text-sm shadow-xl shadow-amber-500/20 flex items-center justify-center gap-2 transition-all">
            <i class="fa-solid fa-floppy-disk"></i> 파이썬 서버 DB에 영구 저장
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- Ideas Dashboard Modal -->
  <div id="modal-ideas-board" class="fixed inset-0 z-40 bg-black/85 backdrop-blur-md flex items-end sm:items-center justify-center p-0 sm:p-4 opacity-0 pointer-events-none transition-all duration-300">
    <div class="w-full sm:max-w-2xl glass-panel rounded-t-3xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl border border-slate-700/80 max-h-[90vh] overflow-y-auto flex flex-col pb-[max(1rem,env(safe-area-inset-bottom))]">
      <div class="flex items-center justify-between pb-3 border-b border-slate-700/70 shrink-0">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center text-base border border-amber-500/30">
            <i class="fa-solid fa-database"></i>
          </div>
          <div>
            <div class="flex items-center gap-1.5">
              <h2 class="text-xs sm:text-base font-bold text-white">세아특수강 CDM 참관 아이디어 DB</h2>
              <span id="board-total-count-badge" class="px-2 py-0.5 rounded-full text-[10px] bg-amber-500 text-slate-950 font-black">0건</span>
            </div>
            <p class="text-[10px] text-slate-400">서버 SQLite에 안전하게 축적된 팀원 제안 목록입니다</p>
          </div>
        </div>
        <button id="btn-close-ideas-board" type="button" class="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center text-base"><i class="fa-solid fa-xmark"></i></button>
      </div>

      <!-- Tour Progress -->
      <div class="my-3 p-3 rounded-2xl bg-slate-800/80 border border-slate-700/70 shrink-0">
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="text-slate-300 font-semibold flex items-center gap-1"><i class="fa-solid fa-flag-checkered text-amber-400"></i> 참관 추천 부스(총 11개) 작성 달성도</span>
          <span id="board-progress-text" class="text-amber-400 font-bold text-[11px]">0 / 11개 부스</span>
        </div>
        <div class="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden">
          <div id="board-progress-bar" class="bg-gradient-to-r from-blue-500 to-amber-500 h-2.5 rounded-full transition-all duration-500" style="width: 0%"></div>
        </div>
      </div>

      <!-- Action Toolbar -->
      <div class="flex flex-wrap items-center justify-between gap-1.5 mb-3 shrink-0">
        <div class="flex items-center gap-1.5">
          <button id="btn-copy-all-board" type="button" class="px-2.5 py-1.5 rounded-xl bg-blue-600/30 hover:bg-blue-600 border border-blue-500/40 text-blue-300 hover:text-white text-xs font-bold flex items-center gap-1 transition-all">
            <i class="fa-solid fa-copy"></i> 카톡/보고서 복사
          </button>
          <a href="/api/export-csv" download class="px-2.5 py-1.5 rounded-xl bg-emerald-600/30 hover:bg-emerald-600 border border-emerald-500/40 text-emerald-300 hover:text-white text-xs font-bold flex items-center gap-1 transition-all">
            <i class="fa-solid fa-file-excel"></i> 엑셀(CSV) 다운로드
          </a>
        </div>
        <div class="flex items-center gap-1.5">
          <button id="btn-board-add-new" type="button" class="px-2.5 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black flex items-center gap-1 transition-all"><i class="fa-solid fa-plus"></i> 추가</button>
          <button id="btn-refresh-server-db" type="button" class="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-semibold transition-all" title="서버 동기화"><i class="fa-solid fa-arrows-rotate"></i> 새로고침</button>
        </div>
      </div>

      <div id="board-ideas-container" class="space-y-2.5 overflow-y-auto pr-1 flex-1 min-h-[160px]"></div>
    </div>
  </div>

  <!-- Toast Message -->
  <div id="toast-message" class="fixed top-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-2xl bg-blue-600 text-white text-xs font-semibold shadow-2xl flex items-center gap-2 transform -translate-y-20 opacity-0 transition-all duration-300 pointer-events-none">
    <i class="fa-solid fa-circle-check text-green-300"></i>
    <span id="toast-text">알림</span>
  </div>

  <script>
    const BOOTH_DATA = [
      { step: 1, id: "W2-219", hallCode: "서관 ITCE 2홀", company: "원프레딕트", shortName: "원프레딕트", hall: "ITCE 서관 2홀", trackName: "T3. AI 예지보전", color: 0xa855f7, x: -42, z: -18, w: 15, d: 13, h: 4.8, process: "CDM 메인 인발 캐리지 감속기 & 2롤 교정기 롤러 베어링 상태진단", highlight: "국내 1위 산업 AI 예지보전 GuardiOne. 딥러닝 기반 베어링 편마모/기어 손상 사전 예측" },
      { step: 2, id: "W2-198", hallCode: "서관 ITCE 2홀", company: "주식회사 그룸깃다", shortName: "그룸깃다(구글)", hall: "ITCE 서관 2홀", trackName: "T3. 스마트팩토리 AI", color: 0xa855f7, x: -55, z: 2, w: 12, d: 11, h: 4.2, process: "마봉강 치수 & 비파괴 검사(ECT) 데이터 인라인 Edge AI 수집", highlight: "구글 클라우드 파트너 기반 스마트팩토리 데이터 플랫폼 및 초경량 Edge 분석" },
      { step: 3, id: "W1-200", hallCode: "서관 ITCE 1홀", company: "한국기계연구원 (대경융합연구본부)", shortName: "한국기계연구원", hall: "ITCE 서관 1홀", trackName: "T4. 금속기계 소성자동화", color: 0xf59e0b, x: -18, z: 0, w: 13, d: 11, h: 4.0, process: "장척 봉강 자동 정렬 및 소성가공 공정 지능화 기계 연구", highlight: "금속 소성가공 기계 및 스마트 제조 자동화 국책 실증 연구" },
      { step: 4, id: "W3-131", hallCode: "서관 ROBEX 3홀", company: "HD현대로보틱스", shortName: "HD현대로봇", hall: "ROBEX 서관 3홀", trackName: "T1. 고가반하중 핸들링", color: 0x3b82f6, x: 42, z: -8, w: 18, d: 16, h: 6.2, process: "4~6m 장척 봉강 번들(수 톤) 로딩/언로딩 및 크레인 없는 자동 이송", highlight: "Heavy Payload 다관절 로봇(가반하중 500kg~1톤급), 롱바 특수 그리퍼" },
      { step: 5, id: "W3-141", hallCode: "서관 ROBEX 3홀", company: "두산로보틱스", shortName: "두산로보틱스", hall: "ROBEX 서관 3홀", trackName: "T2. 협동로봇·포장", color: 0x10b981, x: 42, z: -35, w: 18, d: 16, h: 5.8, process: "CDM 후단 육각 번들 자동 밴딩(Strap 결속), 끝단 캡 삽입, 라벨 태깅", highlight: "고가반하중 H/P시리즈 협동로봇, 토크 센서 기반 최고 등급 안전 보호" },
      { step: 6, id: "W3-331", hallCode: "서관 ROBEX 3홀", company: "아이엠로보틱스(주)", shortName: "아이엠로보틱스", hall: "ROBEX 서관 3홀", trackName: "T1. 중량물 AMR 물류", color: 0x3b82f6, x: 18, z: -10, w: 13, d: 14, h: 4.8, process: "CDM 인발 후 열처리 또는 교정 공정 간 봉강 랙 무인 AMR 이송", highlight: "고중량 자율이송로봇(AMR), 공장 바닥 요철 및 금속 플레이트 주행 제어" },
      { step: 7, id: "W3-231", hallCode: "서관 ROBEX 3홀", company: "브라토(주)", shortName: "브라토", hall: "ROBEX 서관 3홀", trackName: "T1. 특수 그리퍼/기구", color: 0x3b82f6, x: 28, z: 8, w: 12, d: 11, h: 4.2, process: "2롤 교정기 및 면취기 전후단 봉강 정밀 이송 롤러 및 고하중 클램핑 그리퍼", highlight: "흠집 없는 파지 메커니즘 및 대형 서보 전동 그리퍼" },
      { step: 8, id: "W3-201", hallCode: "서관 ROBEX 3홀", company: "에이치알티로보틱스", shortName: "HRT로보틱스", hall: "ROBEX 서관 3홀", trackName: "T4. AI 비전 검사", color: 0xf59e0b, x: 25, z: 38, w: 14, d: 9, h: 4.2, process: "마봉강 표면 롤 마크, 미세 스크래치, 헤어라인 크랙 인라인 비전 검사", highlight: "고속 3D 레이저 프로파일러 + 딥러닝 결함 검출 로봇 셀" },
      { step: 9, id: "W3-641", hallCode: "서관 ROBEX 3홀", company: "한국로봇산업진흥원", shortName: "로봇진흥원", hall: "ROBEX 서관 3홀", trackName: "T4. 정부지원 바우처", color: 0xf59e0b, x: -2, z: -40, w: 15, d: 13, h: 4.8, process: "봉강 CDM 라인 중량물 고위험 공정 자동화 국비 50~70% 보조금 사업 상담", highlight: "국내 제조기업 로봇 실증 보급사업 총괄 전담기관 현장 데스크" },
      { step: 10, id: "E4-210", hallCode: "동관 DIFA 4홀", company: "BYD (비야디)", shortName: "BYD(전기차)", hall: "DIFA 동관 4홀", trackName: "T5. 중국 EV 벤치마킹", color: 0xef4444, x: 108, z: -25, w: 20, d: 18, h: 6.0, process: "전기차 감속기 샤프트용 고청정 마봉강 & 블레이드 배터리 볼트 강재 수요 파악", highlight: "글로벌 1위 EV 제조사. e-Platform 3.0 일체화 구동모터 샤프트 전시" },
      { step: 11, id: "E4-232", hallCode: "동관 DIFA 4홀", company: "지커 (ZEEKR)", shortName: "지커(ZEEKR)", hall: "DIFA 동관 4홀", trackName: "T5. 중국 EV 벤치마킹", color: 0x06b6d4, x: 108, z: 20, w: 19, d: 16, h: 5.5, process: "대형 기가캐스팅 차체 도입에 따른 스티어링 랙바, 타이로드 마봉강 설계 변화 대응", highlight: "지리자동차 프리미엄 EV 브랜드. SEA 전기차 플랫폼 및 기가캐스팅 시연" }
    ];

    const ENTRANCE_POINT = { x: -25, z: 50 };
    let currentStepIndex = 0;
    let serverIdeasCache = [];

    // Three.js instances
    let scene = null, camera = null, renderer = null, controls = null;
    let boothGroups = [], boothMeshes = [], routeLine = null, selectedBooth = null;
    let isAutoTouring = false, autoTourInterval = null, raycaster = null, mouse = null;
    let isDragging = false, pointerDownPos = { x: 0, y: 0 };
    const clock = new THREE.Clock();
    let isPanelOpen = false;

    function initThree() {
      const canvas = document.getElementById('webgl-canvas');
      if (!canvas) return;
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0b0f19);
      scene.fog = new THREE.FogExp2(0x0b0f19, 0.005);

      camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.5, 600);
      camera.position.set(0, 85, 95);

      renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
      renderer.setSize(window.innerWidth, window.innerHeight);

      if (typeof THREE.OrbitControls === 'function') {
        controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.09;
        controls.maxPolarAngle = Math.PI / 2 - 0.04;
        controls.minDistance = 15;
        controls.maxDistance = 260;
        controls.target.set(0, 0, 0);
      }

      raycaster = new THREE.Raycaster();
      mouse = new THREE.Vector2();

      setupLights();
      createExhibitionHall();
      createBooths();
      createRoutePolyline();

      window.addEventListener('resize', () => {
        if (!camera || !renderer) return;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      });

      renderer.domElement.addEventListener('pointerdown', (e) => {
        isDragging = false;
        pointerDownPos = { x: e.clientX, y: e.clientY };
      });
      renderer.domElement.addEventListener('pointermove', (e) => {
        if (Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y) > 8) isDragging = true;
      });
      renderer.domElement.addEventListener('pointerup', (e) => {
        if (!isDragging) {
          const rect = renderer.domElement.getBoundingClientRect();
          mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
          mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
          raycaster.setFromCamera(mouse, camera);
          const hits = raycaster.intersectObjects(boothMeshes, false);
          if (hits.length > 0) selectStep(hits[0].object.userData.index, true);
        }
      });
    }

    function setupLights() {
      scene.add(new THREE.AmbientLight(0xffffff, 0.8));
      const hemi = new THREE.HemisphereLight(0x93c5fd, 0x0f172a, 0.65);
      hemi.position.set(0, 100, 0);
      scene.add(hemi);
      const dir = new THREE.DirectionalLight(0xffffff, 0.95);
      dir.position.set(40, 90, 50);
      scene.add(dir);
    }

    function createExhibitionHall() {
      const floorGeo = new THREE.PlaneGeometry(280, 200);
      const floorMat = new THREE.MeshStandardMaterial({ color: 0x080c16, roughness: 0.85 });
      const floor = new THREE.Mesh(floorGeo, floorMat);
      floor.rotation.x = -Math.PI / 2;
      scene.add(floor);

      const grid = new THREE.GridHelper(260, 52, 0x1e3a8a, 0x1e293b);
      grid.position.y = 0.02;
      scene.add(grid);

      createZonePod(-40, -10, 70, 90, 0x1e1e38, "서관 ITCE (1·2홀)");
      createZonePod(30, -5, 68, 105, 0x172554, "서관 ROBEX (3홀)");

      const bridgeGeo = new THREE.BoxGeometry(24, 0.4, 18);
      const bridge = new THREE.Mesh(bridgeGeo, new THREE.MeshStandardMaterial({ color: 0x0369a1 }));
      bridge.position.set(78, 0.2, 0);
      scene.add(bridge);

      createZonePod(115, 0, 52, 100, 0x3b0764, "동관 DIFA (4홀) - 중국 EV");
    }

    function createZonePod(x, z, width, depth, colorHex, label) {
      const pod = new THREE.Mesh(new THREE.BoxGeometry(width, 0.3, depth), new THREE.MeshStandardMaterial({ color: colorHex }));
      pod.position.set(x, 0.15, z);
      scene.add(pod);
    }

    function createBooths() {
      boothGroups = []; boothMeshes = [];
      BOOTH_DATA.forEach((b, idx) => {
        const group = new THREE.Group();
        group.position.set(b.x, 0, b.z);

        const base = new THREE.Mesh(new THREE.BoxGeometry(b.w, 0.5, b.d), new THREE.MeshStandardMaterial({ color: 0x1e293b }));
        base.position.y = 0.25;
        group.add(base);

        const body = new THREE.Mesh(new THREE.BoxGeometry(b.w * 0.88, b.h, b.d * 0.88), new THREE.MeshStandardMaterial({ color: 0x0f172a }));
        body.position.y = b.h / 2 + 0.5;
        body.userData = { index: idx, booth: b };
        group.add(body);
        boothMeshes.push(body);

        const signSprite = createBoothSign(b);
        signSprite.position.set(0, b.h + 5.2, 0);
        group.add(signSprite);

        const pin = new THREE.Mesh(new THREE.ConeGeometry(1.2, 2.5, 4), new THREE.MeshBasicMaterial({ color: 0xfbbf24 }));
        pin.rotation.x = Math.PI;
        pin.position.set(0, b.h + 8.8, 0);
        group.add(pin);

        group.userData = { pin, baseHeight: b.h + 8.8, index: idx, booth: b };
        scene.add(group);
        boothGroups.push(group);
      });
    }

    function createBoothSign(booth) {
      const canvas = document.createElement('canvas');
      canvas.width = 640; canvas.height = 240;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = "rgba(11, 15, 25, 0.94)";
      ctx.roundRect(8, 8, 624, 224, 28);
      ctx.fill();
      ctx.strokeStyle = "#" + booth.color.toString(16).padStart(6, '0');
      ctx.lineWidth = 8;
      ctx.stroke();

      ctx.fillStyle = "#fbbf24";
      ctx.font = "900 44px monospace";
      ctx.fillText("[" + booth.id + "]", 32, 60);

      ctx.fillStyle = "#ffffff";
      ctx.font = "900 48px sans-serif";
      ctx.fillText(booth.step + ". " + booth.shortName, 32, 160);

      const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }));
      sprite.scale.set(13, 5, 1);
      return sprite;
    }

    function createRoutePolyline() {
      const points = [new THREE.Vector3(ENTRANCE_POINT.x, 0.5, ENTRANCE_POINT.z)];
      BOOTH_DATA.forEach(b => points.push(new THREE.Vector3(b.x, 0.5, b.z)));
      const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal', 0.2);
      routeLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(curve.getPoints(120)),
        new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.85 })
      );
      scene.add(routeLine);
    }

    function animate() {
      requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();
      boothGroups.forEach(g => {
        if (g.userData && g.userData.pin) {
          g.userData.pin.position.y = g.userData.baseHeight + Math.sin(elapsedTime * 3.5 + g.position.x) * 0.45;
          g.userData.pin.rotation.y = elapsedTime * 1.5;
        }
      });
      if (controls) controls.update();
      if (renderer && scene && camera) renderer.render(scene, camera);
    }

    async function fetchServerIdeas() {
      try {
        const res = await fetch('/api/ideas');
        if (res.ok) {
          serverIdeasCache = await res.json();
          updateUIWithIdeas();
        }
      } catch (err) {
        console.warn("Server sync error:", err);
      }
    }

    function updateUIWithIdeas() {
      const count = serverIdeasCache.length;
      document.getElementById('idea-count-badge').textContent = count;
      document.getElementById('board-total-count-badge').textContent = count + '건';

      const visited = new Set(serverIdeasCache.map(i => i.booth_step).filter(Boolean));
      const percent = Math.min(100, Math.round((visited.size / 11) * 100));
      document.getElementById('board-progress-text').textContent = visited.size + " / 11개 부스 (" + percent + "%)";
      document.getElementById('board-progress-bar').style.width = percent + "%";

      renderStepButtons();
    }

    function renderStepButtons() {
      const container = document.getElementById('step-buttons-container');
      if (!container) return;
      container.innerHTML = '';

      BOOTH_DATA.forEach((b, idx) => {
        const hasIdea = serverIdeasCache.some(i => i.booth_step === b.step);
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'step-btn-' + idx;
        btn.className = 'step-nav-btn shrink-0 px-2.5 sm:px-3 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border ' +
          (idx === currentStepIndex ? 'bg-blue-600 text-white border-blue-400' : 'bg-slate-800/80 text-slate-300 border-slate-700');
        btn.innerHTML = '<span class="font-mono text-[10px] text-amber-300 font-black">[' + b.id + ']</span>' +
                        '<span>' + b.step + '.' + b.shortName + '</span>' +
                        (hasIdea ? '<span class="text-amber-400 text-[10px]"><i class="fa-solid fa-circle-check"></i></span>' : '');
        btn.addEventListener('click', () => selectStep(idx, true));
        container.appendChild(btn);
      });
    }

    function selectStep(index, zoomCamera = true) {
      if (index < 0 || index >= BOOTH_DATA.length) return;
      currentStepIndex = index;
      const b = BOOTH_DATA[index];
      selectedBooth = b;

      document.getElementById('nav-step-num').textContent = '[' + b.step + '/11]';
      document.getElementById('nav-step-booth-id').textContent = b.id;
      document.getElementById('nav-step-title').textContent = b.company;

      document.getElementById('detail-step-badge').textContent = b.step + '번 부스';
      document.getElementById('detail-track-badge').textContent = b.trackName;
      document.getElementById('detail-booth-id').textContent = b.hall + ' · ' + b.id;
      document.getElementById('detail-company').textContent = b.company;
      document.getElementById('detail-process').textContent = b.process;
      document.getElementById('detail-highlight').textContent = b.highlight;

      const nextB = BOOTH_DATA[(index + 1) % BOOTH_DATA.length];
      document.getElementById('detail-next-target').textContent = nextB.step + '. [' + nextB.id + '] ' + nextB.company;

      const card = document.getElementById('booth-detail-card');
      card.classList.remove('translate-y-full', 'sm:opacity-0', 'sm:pointer-events-none', 'panel-collapsed');
      document.getElementById('btn-dock-expand').classList.add('opacity-0', 'pointer-events-none');

      if (zoomCamera) {
        gsap.to(camera.position, { x: b.x + 14, y: b.h + 16, z: b.z + 24, duration: 0.8 });
        if (controls) gsap.to(controls.target, { x: b.x - 8, y: b.h / 2, z: b.z, duration: 0.8 });
      }
      renderStepButtons();
    }

    async function handleIdeaSubmit(e) {
      e.preventDefault();
      const author = document.getElementById('form-author').value.trim();
      const factory = document.getElementById('form-factory').value;
      const boothStr = document.getElementById('form-booth').value.trim();
      const ideaText = document.getElementById('form-idea').value.trim();

      const benefits = [];
      document.querySelectorAll('#benefit-checkboxes input[type=checkbox]:checked').forEach(c => benefits.push(c.value));

      if (!author || !boothStr || !ideaText) {
        showToast("모든 필수 항목을 입력해주세요.");
        return;
      }

      localStorage.setItem('SEAH_USER', JSON.stringify({ author, factory }));

      let stepNum = selectedBooth ? selectedBooth.step : null;
      let boothId = selectedBooth ? selectedBooth.id : "";
      const match = boothStr.match(/^(\d+)\./);
      if (match) stepNum = parseInt(match[1], 10);

      const payload = {
        uuid: "ID_" + Date.now(),
        booth_step: stepNum,
        booth_id: boothId,
        booth_name: boothStr,
        author: author,
        factory: factory,
        idea_text: ideaText,
        benefits: benefits.join(", ")
      };

      try {
        const res = await fetch('/api/ideas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          showToast("💾 파이썬 서버 DB에 영구 저장되었습니다!");
          document.getElementById('form-idea').value = '';
          document.getElementById('modal-idea-form').classList.add('opacity-0', 'pointer-events-none');
          await fetchServerIdeas();
        } else {
          showToast("서버 저장 실패. 네트워크를 확인하세요.");
        }
      } catch (err) {
        showToast("서버 연결 실패: " + err);
      }
    }

    function renderIdeasBoard() {
      const container = document.getElementById('board-ideas-container');
      container.innerHTML = '';
      if (serverIdeasCache.length === 0) {
        container.innerHTML = '<div class="py-8 text-center text-slate-500">등록된 아이디어가 없습니다.</div>';
        return;
      }

      serverIdeasCache.forEach(item => {
        const card = document.createElement('div');
        card.className = "p-3 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex flex-col gap-2";
        card.innerHTML = `
          <div class="flex items-start justify-between">
            <div>
              <span class="px-2 py-0.5 rounded text-[10px] font-black bg-amber-500/20 text-amber-300">${item.booth_step ? item.booth_step + '번' : '참관'} [${item.booth_id || ''}]</span>
              <strong class="text-xs text-white ml-1">${item.booth_name}</strong>
              <div class="text-[11px] text-slate-400 mt-1">작성자: <strong class="text-slate-200">${item.author}</strong> (${item.factory}) · ${item.created_at}</div>
            </div>
          </div>
          <div class="p-2.5 rounded-xl bg-slate-900/70 text-xs text-slate-200 leading-relaxed">${item.idea_text}</div>
          <div class="text-[10px] text-blue-300 font-mono">${item.benefits || ''}</div>
        `;
        container.appendChild(card);
      });
    }

    function showToast(msg) {
      const t = document.getElementById('toast-message');
      document.getElementById('toast-text').textContent = msg;
      t.classList.remove('-translate-y-20', 'opacity-0');
      setTimeout(() => t.classList.add('-translate-y-20', 'opacity-0'), 2500);
    }

    function setupEvents() {
      document.getElementById('btn-prev-step').addEventListener('click', () => {
        selectStep((currentStepIndex - 1 + BOOTH_DATA.length) % BOOTH_DATA.length, true);
      });
      document.getElementById('btn-next-step').addEventListener('click', () => {
        selectStep((currentStepIndex + 1) % BOOTH_DATA.length, true);
      });
      document.getElementById('btn-open-form-direct').addEventListener('click', () => openFormModal(selectedBooth));
      document.getElementById('btn-log-current-booth').addEventListener('click', () => openFormModal(selectedBooth));
      document.getElementById('btn-detail-to-form').addEventListener('click', () => openFormModal(selectedBooth));
      document.getElementById('btn-close-form').addEventListener('click', () => {
        document.getElementById('modal-idea-form').classList.add('opacity-0', 'pointer-events-none');
      });
      document.getElementById('btn-open-ideas-board').addEventListener('click', () => {
        renderIdeasBoard();
        document.getElementById('modal-ideas-board').classList.remove('opacity-0', 'pointer-events-none');
      });
      document.getElementById('btn-close-ideas-board').addEventListener('click', () => {
        document.getElementById('modal-ideas-board').classList.add('opacity-0', 'pointer-events-none');
      });
      document.getElementById('btn-refresh-server-db').addEventListener('click', async () => {
        await fetchServerIdeas();
        renderIdeasBoard();
        showToast("서버 DB와 최신 동기화 완료");
      });
      document.getElementById('lean-idea-form').addEventListener('submit', handleIdeaSubmit);
      document.getElementById('btn-close-detail').addEventListener('click', () => {
        document.getElementById('booth-detail-card').classList.add('translate-y-full');
      });
      document.getElementById('btn-collapse-panel').addEventListener('click', () => {
        document.getElementById('booth-detail-card').classList.add('panel-collapsed');
        document.getElementById('btn-dock-expand').classList.remove('opacity-0', 'pointer-events-none');
      });
      document.getElementById('btn-dock-expand').addEventListener('click', () => {
        document.getElementById('booth-detail-card').classList.remove('panel-collapsed');
        document.getElementById('btn-dock-expand').classList.add('opacity-0', 'pointer-events-none');
      });

      // Quick Tag Chips
      document.querySelectorAll('.cdm-tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const area = document.getElementById('form-idea');
          const t = btn.getAttribute('data-text');
          area.value = area.value ? area.value + ' / ' + t : t;
        });
      });

      // Fast Booth Chips
      const chipBox = document.getElementById('fast-booth-chips');
      BOOTH_DATA.forEach(b => {
        const c = document.createElement('button');
        c.type = 'button';
        c.className = 'px-2 py-0.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300';
        c.textContent = b.step + '. ' + b.shortName;
        c.addEventListener('click', () => {
          document.getElementById('form-booth').value = b.step + '. ' + b.company + ' (' + b.id + ')';
        });
        chipBox.appendChild(c);
      });
    }

    function openFormModal(booth) {
      const b = booth || BOOTH_DATA[currentStepIndex];
      const savedUser = JSON.parse(localStorage.getItem('SEAH_USER') || '{}');
      if (savedUser.author) document.getElementById('form-author').value = savedUser.author;
      if (savedUser.factory) document.getElementById('form-factory').value = savedUser.factory;
      document.getElementById('form-booth').value = b.step + '. ' + b.company + ' (' + b.id + ')';
      document.getElementById('modal-idea-form').classList.remove('opacity-0', 'pointer-events-none');
    }

    window.addEventListener('load', () => {
      initThree();
      animate();
      setupEvents();
      selectStep(0, false);
      fetchServerIdeas();
    });
  </script>
</body>
</html>
"""

class SeAHTourHandler(BaseHTTPRequestHandler):
    """Custom HTTP Request Handler serving 3D app and persisting idea submissions."""

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}\n")

    def do_GET(self):
        url = urlparse(self.path)

        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif url.path == "/api/ideas":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            with sqlite3.connect(DB_FILE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ideas ORDER BY id DESC")
                rows = [dict(row) for row in cursor.fetchall()]
                self.wfile.write(json.dumps(rows, ensure_ascii=False).encode("utf-8"))

        elif url.path == "/api/export-csv":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="seah_cdm_fix_ideas.csv"')
            self.end_headers()

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, booth_step, booth_id, booth_name, author, factory, idea_text, benefits, created_at FROM ideas ORDER BY id ASC")
                rows = cursor.fetchall()

            # UTF-8 BOM for Excel compatibility
            csv_data = "\uFEFF순번,부스번호,기업명,작성자,소속공정,제안아이디어,기대효과,등록일시\n"
            for r in rows:
                clean_idea = str(r[6]).replace('"', '""')
                clean_benefit = str(r[7]).replace('"', '""')
                csv_data += f'{r[0]},"{r[2]}","{r[3]}","{r[4]}","{r[5]}","{clean_idea}","{clean_benefit}","{r[8]}"\n'

            self.wfile.write(csv_data.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        if self.path == "/api/ideas":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")

            try:
                data = json.loads(body)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO ideas (uuid, booth_step, booth_id, booth_name, author, factory, idea_text, benefits, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data.get("uuid"),
                        data.get("booth_step"),
                        data.get("booth_id"),
                        data.get("booth_name"),
                        data.get("author"),
                        data.get("factory"),
                        data.get("idea_text"),
                        data.get("benefits"),
                        now_str
                    ))
                    conn.commit()

                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "saved_at": now_str}).encode("utf-8"))

            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def get_local_ip():
    """Detects primary local IP address to allow smartphone connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def run_server():
    """Starts the SeAH CDM FIX 2026 Navigation Server."""
    init_database()
    local_ip = get_local_ip()

    server = HTTPServer((HOST, PORT), SeAHTourHandler)
    local_url = f"http://localhost:{PORT}"
    network_url = f"http://{local_ip}:{PORT}"

    print("=" * 64)
    print(" [세아특수강 CDM 봉강생산팀] FIX 2026 3D 스마트 네비게이터 서버")
    print("=" * 64)
    print(f" * PC 로컬 접속:       {local_url}")
    print(f" * 팀원 스마트폰 접속:  {network_url}")
    print(f" * 데이터베이스:       {DB_FILE} (자동 SQLite 영구저장)")
    print("=" * 64)
    print(" 💡 사용 방법:")
    print(f" 1. 같은 사내 Wi-Fi 또는 핫스팟 연결 후 팀원 폰에서 '{network_url}' 접속")
    print(" 2. 스마트폰에서 아이디어 등록 시 본 PC의 SQLite 데이터베이스에 즉시 영구 저장")
    print(" 3. 종료하려면 터미널에서 Ctrl + C 를 누르세요.")
    print("=" * 64)

    # Automatically open in browser for the host PC
    try:
        webbrowser.open(local_url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[서버 종료] 세아특수강 FIX 2026 네비게이터 서버가 안전하게 중지되었습니다.")
        server.server_close()

if __name__ == "__main__":
    run_server()