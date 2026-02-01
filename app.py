<!-- Chosen Palette: Warm Neutrals & Muted Teal (Calm, Academic, Modern) -->
<!-- Application Structure Plan: The SPA is designed as a "Product Specification & Design System" dashboard for the K-Tutor Global project. 
    1.  **Executive Summary:** High-level project vision and core goals.
    2.  **Tech Stack Analysis:** Interactive visualization of the technology architecture (Python, Streamlit, Gemini).
    3.  **Core Features Breakdown:** Detailed cards explaining the logic for Roleplay, Correction, and TTS.
    4.  **Interactive UX Prototype (The "Optimal Design"):** A fully functional simulation of the proposed web interface. This allows the stakeholder to "feel" the recommended design (Home Screen with Cards -> Chat Interface with Bubbles/Correction/Audio). 
    5.  **Technical Architecture:** Data flow visualization using charts.
    Rationale: This structure bridges the gap between raw requirements and visual implementation, allowing the developer to see both the *what* (specs) and the *how* (design). -->
<!-- Visualization & Content Choices:
    1.  **Tech Stack Distribution (Doughnut Chart):** Visually represents the reliance on different technologies (Core vs AI vs Interface). Goal: Inform.
    2.  **User Flow Funnel (Bar Chart):** Shows the steps a user takes (Scenario Select -> Chat -> Feedback). Goal: Understand process.
    3.  **Interactive Prototype (HTML/JS Simulation):** The centerpiece. Instead of static text describing the design, I built a live mock-up. Users can click scenarios and simulate a chat. This directly answers the user's request for "optimal design".
    4.  **Feature Cards:** Expandable text blocks to organize the detailed requirements (TTS, Regex, Prompts). -->
<!-- CONFIRMATION: NO SVG graphics used. NO Mermaid JS used. -->

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>K-Tutor Global: Product Specification & UX Design</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans KR', sans-serif; background-color: #FDFBF7; color: #1F2937; }
        .chart-container { position: relative; width: 100%; max-width: 500px; margin: 0 auto; height: 300px; }
        .glass-panel { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); border: 1px solid rgba(229, 231, 235, 0.5); }
        .chat-bubble { max-width: 80%; border-radius: 1.5rem; padding: 1rem; margin-bottom: 0.75rem; position: relative; animation: fadeIn 0.3s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .bubble-ai { background-color: #F3F4F6; color: #1F2937; border-bottom-left-radius: 0.25rem; }
        .bubble-user { background-color: #2DD4BF; color: white; border-bottom-right-radius: 0.25rem; margin-left: auto; }
        .correction-box { background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 0.75rem; font-size: 0.875rem; margin-top: 0.5rem; border-radius: 0.25rem; }
        .audio-player-mock { display: flex; align-items: center; gap: 0.5rem; background: #E5E7EB; padding: 0.5rem 1rem; border-radius: 9999px; width: fit-content; margin-top: 0.5rem; }
        .play-btn { width: 24px; height: 24px; background: #4B5563; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; cursor: pointer; }
        /* Custom scrollbar for chat */
        .chat-scroll::-webkit-scrollbar { width: 6px; }
        .chat-scroll::-webkit-scrollbar-track { background: transparent; }
        .chat-scroll::-webkit-scrollbar-thumb { background-color: #D1D5DB; border-radius: 20px; }
    </style>
</head>
<body class="bg-[#FDFBF7] text-gray-800 antialiased">

    <!-- Navigation -->
    <nav class="sticky top-0 z-50 glass-panel border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <span class="text-2xl font-bold text-teal-700">K-Tutor Global</span>
                    <span class="ml-3 px-2 py-1 text-xs font-semibold bg-orange-100 text-orange-700 rounded-full hidden sm:inline-block">Spec & Prototype</span>
                </div>
                <div class="flex items-center space-x-6">
                    <button onclick="scrollToSection('specs')" class="text-gray-600 hover:text-teal-600 font-medium transition">명세서 (Specs)</button>
                    <button onclick="scrollToSection('architecture')" class="text-gray-600 hover:text-teal-600 font-medium transition">아키텍처</button>
                    <button onclick="scrollToSection('prototype')" class="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg font-bold transition shadow-md">UX 프로토타입 체험</button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Header / Intro -->
    <header class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
        <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">외국인을 위한 AI 한국어 롤플레잉 튜터</h1>
        <p class="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Google Gemini 2.0 Flash와 Streamlit을 활용한 실시간 회화 연습 플랫폼.<br>
            상황별 시나리오, 실시간 교정, 그리고 감정 기반 TTS를 통합한 몰입형 학습 경험.
        </p>
        <div class="flex justify-center gap-4">
            <div class="flex items-center gap-2 text-sm font-semibold text-gray-500 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span> Python Core
            </div>
            <div class="flex items-center gap-2 text-sm font-semibold text-gray-500 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                <span class="w-2 h-2 rounded-full bg-red-500"></span> Streamlit UI
            </div>
            <div class="flex items-center gap-2 text-sm font-semibold text-gray-500 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                <span class="w-2 h-2 rounded-full bg-purple-500"></span> Gemini AI
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 space-y-24">

        <!-- Section 1: Specifications & Tech Stack -->
        <section id="specs" class="scroll-mt-24">
            <div class="mb-8">
                <h2 class="text-3xl font-bold text-gray-900 mb-2 border-l-4 border-teal-500 pl-4">기술 스택 및 기능 명세</h2>
                <p class="text-gray-600 pl-5">안정적인 Python 생태계와 최신 Generative AI 기술의 결합</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
                <!-- Tech Stack Visual -->
                <div class="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                    <h3 class="text-lg font-bold text-gray-800 mb-6 text-center">시스템 구성 비율 (Tech Composition)</h3>
                    <div class="chart-container">
                        <canvas id="techChart"></canvas>
                    </div>
                    <p class="mt-4 text-sm text-gray-500 text-center">Streamlit이 인터페이스를 담당하고, Gemini가 핵심 로직을 처리하는 구조입니다.</p>
                </div>

                <!-- Core Features Grid -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="bg-white p-5 rounded-xl border border-gray-100 hover:border-teal-200 transition shadow-sm hover:shadow-md">
                        <div class="text-2xl mb-2">🎭</div>
                        <h4 class="font-bold text-gray-900">페르소나 롤플레잉</h4>
                        <p class="text-sm text-gray-600 mt-1">Gemini에게 특정 역할(입국 심사관, 점원 등)을 부여하여 몰입감 있는 대화 유도.</p>
                    </div>
                    <div class="bg-white p-5 rounded-xl border border-gray-100 hover:border-teal-200 transition shadow-sm hover:shadow-md">
                        <div class="text-2xl mb-2">🛠️</div>
                        <h4 class="font-bold text-gray-900">실시간 문장 교정</h4>
                        <p class="text-sm text-gray-600 mt-1">사용자 입력 오류 시 <code>||</code> 태그를 활용해 자연스러운 교정 피드백 제공.</p>
                    </div>
                    <div class="bg-white p-5 rounded-xl border border-gray-100 hover:border-teal-200 transition shadow-sm hover:shadow-md">
                        <div class="text-2xl mb-2">🔊</div>
                        <h4 class="font-bold text-gray-900">자동 TTS 생성</h4>
                        <p class="text-sm text-gray-600 mt-1">gTTS 라이브러리로 AI 응답을 즉시 오디오로 변환, 듣기 연습 강화.</p>
                    </div>
                    <div class="bg-white p-5 rounded-xl border border-gray-100 hover:border-teal-200 transition shadow-sm hover:shadow-md">
                        <div class="text-2xl mb-2">🖼️</div>
                        <h4 class="font-bold text-gray-900">동적 이미지 매핑</h4>
                        <p class="text-sm text-gray-600 mt-1">대화 맥락에 따라 <code>[IMAGE: key]</code> 태그를 감지하여 시각 자료 표시.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 2: Architecture Flow -->
        <section id="architecture" class="scroll-mt-24">
            <div class="mb-8">
                <h2 class="text-3xl font-bold text-gray-900 mb-2 border-l-4 border-teal-500 pl-4">데이터 처리 파이프라인</h2>
                <p class="text-gray-600 pl-5">사용자 입력부터 AI 응답 및 오디오 생성까지의 흐름</p>
            </div>
            
            <div class="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
                <div class="flex flex-col md:flex-row justify-between items-center gap-4 text-center md:text-left">
                    
                    <div class="flex-1 p-4 bg-gray-50 rounded-lg w-full">
                        <span class="block text-xs font-bold text-gray-400 mb-1">INPUT</span>
                        <div class="font-bold text-gray-800">User Input</div>
                        <div class="text-xs text-gray-500">(Streamlit Chat Input)</div>
                    </div>

                    <div class="text-gray-400 text-2xl hidden md:block">→</div>
                    <div class="text-gray-400 text-2xl md:hidden">↓</div>

                    <div class="flex-1 p-4 bg-teal-50 border border-teal-100 rounded-lg w-full relative">
                        <span class="absolute -top-2 -right-2 bg-teal-600 text-white text-[10px] px-2 py-0.5 rounded-full">CORE</span>
                        <span class="block text-xs font-bold text-teal-600 mb-1">PROCESSING</span>
                        <div class="font-bold text-teal-900">Gemini 2.0 Flash</div>
                        <div class="text-xs text-teal-700">Context + Persona + Correction</div>
                    </div>

                    <div class="text-gray-400 text-2xl hidden md:block">→</div>
                    <div class="text-gray-400 text-2xl md:hidden">↓</div>

                    <div class="flex-1 p-4 bg-gray-50 rounded-lg w-full">
                        <span class="block text-xs font-bold text-gray-400 mb-1">OUTPUT PARSING</span>
                        <div class="font-bold text-gray-800">Response Logic</div>
                        <ul class="text-xs text-left mt-2 space-y-1 text-gray-500">
                            <li>• Check for <code>||</code> (Correction)</li>
                            <li>• Check for <code>[IMAGE]</code></li>
                            <li>• Trigger gTTS (Audio)</li>
                        </ul>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 3: Design Prototype (The Main Feature) -->
        <section id="prototype" class="scroll-mt-24">
            <div class="flex flex-col md:flex-row justify-between items-end mb-8 border-b border-gray-200 pb-4">
                <div>
                    <h2 class="text-3xl font-bold text-gray-900 mb-2 border-l-4 border-teal-500 pl-4">UX 프로토타입 (Interactive)</h2>
                    <p class="text-gray-600 pl-5">제안하는 최적의 UI/UX 디자인입니다. 직접 시나리오를 선택하고 대화를 체험해보세요.</p>
                </div>
                <div class="mt-4 md:mt-0 px-4 py-2 bg-yellow-100 text-yellow-800 text-sm rounded-lg font-medium">
                    💡 Tip: Streamlit 배포 시 이 레이아웃을 참고하세요.
                </div>
            </div>

            <!-- The Simulator -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                <!-- Prototype Controls / Description -->
                <div class="lg:col-span-1 space-y-6">
                    <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                        <h3 class="font-bold text-lg mb-4 text-gray-800">디자인 포인트</h3>
                        <ul class="space-y-4">
                            <li class="flex items-start">
                                <span class="text-teal-500 mr-2 mt-1">✓</span>
                                <div>
                                    <strong class="block text-sm text-gray-900">카드형 시나리오 선택</strong>
                                    <span class="text-xs text-gray-500">이미지와 큰 텍스트를 사용하여 직관적인 선택 유도. 터치 친화적 UI.</span>
                                </div>
                            </li>
                            <li class="flex items-start">
                                <span class="text-teal-500 mr-2 mt-1">✓</span>
                                <div>
                                    <strong class="block text-sm text-gray-900">명확한 교정(Correction) UI</strong>
                                    <span class="text-xs text-gray-500">AI의 피드백을 빨간색 박스로 분리하여 학습 효과 극대화.</span>
                                </div>
                            </li>
                            <li class="flex items-start">
                                <span class="text-teal-500 mr-2 mt-1">✓</span>
                                <div>
                                    <strong class="block text-sm text-gray-900">통합 오디오 플레이어</strong>
                                    <span class="text-xs text-gray-500">말풍선 내부에 재생 버튼을 배치하여 흐름을 끊지 않음.</span>
                                </div>
                            </li>
                        </ul>
                    </div>

                    <div class="bg-indigo-50 p-6 rounded-2xl border border-indigo-100">
                        <h3 class="font-bold text-lg mb-2 text-indigo-900">프로토타입 상태</h3>
                        <div id="prototypeStatus" class="text-indigo-700 text-sm font-medium mb-4">현재 화면: 홈 (시나리오 선택)</div>
                        <button onclick="resetPrototype()" class="w-full py-2 bg-white border border-indigo-200 text-indigo-600 rounded-lg text-sm hover:bg-indigo-50 transition">
                            처음으로 리셋 (Reset)
                        </button>
                    </div>
                </div>

                <!-- Phone/App Simulator Frame -->
                <div class="lg:col-span-2">
                    <div class="mx-auto max-w-sm md:max-w-md bg-gray-900 rounded-[3rem] p-4 shadow-2xl relative overflow-hidden border-4 border-gray-800">
                        <!-- Camera Notch (Visual Only) -->
                        <div class="absolute top-0 left-1/2 transform -translate-x-1/2 h-6 w-32 bg-gray-900 rounded-b-xl z-20"></div>
                        
                        <!-- Screen Content -->
                        <div class="bg-white w-full h-[650px] rounded-[2rem] overflow-hidden relative flex flex-col">
                            
                            <!-- App Header -->
                            <div class="bg-white border-b border-gray-100 p-4 pt-10 flex items-center justify-between sticky top-0 z-10">
                                <button id="backBtn" onclick="goHome()" class="text-gray-400 hover:text-gray-800 transition opacity-0 pointer-events-none">
                                    <span class="text-xl">←</span>
                                </button>
                                <div class="font-bold text-lg text-teal-700">K-Tutor</div>
                                <div class="w-6"></div> <!-- Spacer -->
                            </div>

                            <!-- VIEW: HOME (Scenario Selection) -->
                            <div id="viewHome" class="flex-1 overflow-y-auto p-4 transition-all duration-300">
                                <h2 class="text-2xl font-bold text-gray-800 mb-2">어떤 상황을<br>연습할까요?</h2>
                                <p class="text-gray-400 text-sm mb-6">오늘의 학습 시나리오를 선택하세요.</p>

                                <div class="grid grid-cols-1 gap-4">
                                    <!-- Scenario Card 1 -->
                                    <button onclick="startScenario('airport')" class="group relative overflow-hidden rounded-2xl h-40 w-full text-left shadow-md transition transform hover:scale-[1.02]">
                                        <div class="absolute inset-0 bg-gradient-to-r from-blue-600 to-blue-400 opacity-90"></div>
                                        <div class="absolute inset-0 p-5 flex flex-col justify-between text-white z-10">
                                            <div>
                                                <div class="text-2xl mb-1">✈️</div>
                                                <h3 class="font-bold text-xl">공항 입국심사</h3>
                                            </div>
                                            <span class="text-xs bg-white/20 backdrop-blur-sm px-2 py-1 rounded w-fit">초급 레벨</span>
                                        </div>
                                        <div class="absolute -right-4 -bottom-4 text-9xl text-white opacity-10 rotate-12">✈️</div>
                                    </button>

                                    <!-- Scenario Card 2 -->
                                    <button onclick="startScenario('restaurant')" class="group relative overflow-hidden rounded-2xl h-40 w-full text-left shadow-md transition transform hover:scale-[1.02]">
                                        <div class="absolute inset-0 bg-gradient-to-r from-orange-500 to-amber-400 opacity-90"></div>
                                        <div class="absolute inset-0 p-5 flex flex-col justify-between text-white z-10">
                                            <div>
                                                <div class="text-2xl mb-1">🍜</div>
                                                <h3 class="font-bold text-xl">식당 주문하기</h3>
                                            </div>
                                            <span class="text-xs bg-white/20 backdrop-blur-sm px-2 py-1 rounded w-fit">중급 레벨</span>
                                        </div>
                                        <div class="absolute -right-4 -bottom-4 text-9xl text-white opacity-10 rotate-12">🍜</div>
                                    </button>

                                    <!-- Scenario Card 3 -->
                                    <button onclick="startScenario('market')" class="group relative overflow-hidden rounded-2xl h-40 w-full text-left shadow-md transition transform hover:scale-[1.02]">
                                        <div class="absolute inset-0 bg-gradient-to-r from-teal-500 to-emerald-400 opacity-90"></div>
                                        <div class="absolute inset-0 p-5 flex flex-col justify-between text-white z-10">
                                            <div>
                                                <div class="text-2xl mb-1">🛍️</div>
                                                <h3 class="font-bold text-xl">전통시장 흥정</h3>
                                            </div>
                                            <span class="text-xs bg-white/20 backdrop-blur-sm px-2 py-1 rounded w-fit">고급 레벨</span>
                                        </div>
                                        <div class="absolute -right-4 -bottom-4 text-9xl text-white opacity-10 rotate-12">🛍️</div>
                                    </button>
                                </div>
                            </div>

                            <!-- VIEW: CHAT (Roleplay) -->
                            <div id="viewChat" class="flex-1 flex flex-col hidden transition-all duration-300 bg-gray-50">
                                <!-- Chat Area -->
                                <div id="chatMessages" class="flex-1 overflow-y-auto p-4 chat-scroll space-y-4">
                                    <!-- Messages will be injected here by JS -->
                                </div>

                                <!-- Input Area -->
                                <div class="bg-white p-4 border-t border-gray-100">
                                    <div class="flex gap-2 mb-3 overflow-x-auto pb-2" id="quickReplies">
                                        <!-- Quick replies injected by JS -->
                                    </div>
                                    <div class="relative">
                                        <input type="text" id="chatInput" placeholder="한국어로 대답해보세요..." class="w-full bg-gray-100 rounded-full pl-4 pr-12 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 transition">
                                        <button onclick="sendUserMessage()" class="absolute right-2 top-1/2 transform -translate-y-1/2 bg-teal-500 hover:bg-teal-600 text-white w-8 h-8 rounded-full flex items-center justify-center transition">
                                            ↑
                                        </button>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <footer class="bg-gray-900 text-white py-12">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p class="text-gray-400 text-sm">© 2024 K-Tutor Global Spec Report. Generated by Canvas Create Webapp.</p>
        </div>
    </footer>

    <script>
        // --- DATA & STATE ---
        const scenarios = {
            'airport': {
                title: '공항 입국심사',
                role: '입국 심사관',
                color: 'blue',
                initialMsg: '여권을 보여주시겠습니까? 한국 방문 목적이 무엇인가요?',
                quickReplies: ['여행하러 왔어요.', '친구를 만나러 왔어요.', '일하러 왔습니다.']
            },
            'restaurant': {
                title: '식당 주문하기',
                role: '식당 종업원',
                color: 'orange',
                initialMsg: '어서오세요! 몇 분이신가요? 편하신 자리에 앉으세요.',
                quickReplies: ['두 명이에요.', '메뉴판 좀 주세요.', '추천 메뉴 있나요?']
            },
            'market': {
                title: '전통시장 흥정',
                role: '시장 상인',
                color: 'teal',
                initialMsg: '아이고 어서오세요! 싱싱한 과일 보고 가세요~ 뭐 드릴까?',
                quickReplies: ['사과 얼마예요?', '좀 깎아주세요.', '너무 비싸요.']
            }
        };

        let currentScenarioKey = null;

        // --- CHART CONFIG ---
        const initCharts = () => {
            const ctxTech = document.getElementById('techChart').getContext('2d');
            new Chart(ctxTech, {
                type: 'doughnut',
                data: {
                    labels: ['Interface (Streamlit)', 'Logic/Backend (Python)', 'AI Model (Gemini)', 'Audio/Media (gTTS)'],
                    datasets: [{
                        data: [40, 20, 30, 10],
                        backgroundColor: ['#F87171', '#60A5FA', '#A78BFA', '#34D399'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } }
                    },
                    cutout: '70%'
                }
            });
        };

        // --- PROTOTYPE LOGIC ---

        function scrollToSection(id) {
            document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
        }

        function startScenario(key) {
            currentScenarioKey = key;
            const data = scenarios[key];
            
            // Switch Views
            document.getElementById('viewHome').classList.add('hidden');
            document.getElementById('viewChat').classList.remove('hidden');
            document.getElementById('viewChat').classList.add('flex');
            
            // Update Header & Status
            document.getElementById('backBtn').classList.remove('opacity-0', 'pointer-events-none');
            document.getElementById('prototypeStatus').innerText = `현재 화면: 채팅 (${data.title})`;

            // Clear Chat & Add Initial Message
            const chatContainer = document.getElementById('chatMessages');
            chatContainer.innerHTML = '';
            
            // Add Date Separator
            const dateDiv = document.createElement('div');
            dateDiv.className = 'text-center text-xs text-gray-400 my-4';
            dateDiv.innerText = new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'long' });
            chatContainer.appendChild(dateDiv);

            // Simulate AI Typing then Message
            setTimeout(() => {
                addAiMessage(data.initialMsg);
            }, 600);

            // Update Quick Replies
            updateQuickReplies(data.quickReplies);
        }

        function goHome() {
            document.getElementById('viewChat').classList.add('hidden');
            document.getElementById('viewChat').classList.remove('flex');
            document.getElementById('viewHome').classList.remove('hidden');
            document.getElementById('backBtn').classList.add('opacity-0', 'pointer-events-none');
            document.getElementById('prototypeStatus').innerText = `현재 화면: 홈 (시나리오 선택)`;
            currentScenarioKey = null;
        }

        function resetPrototype() {
            goHome();
        }

        function updateQuickReplies(replies) {
            const container = document.getElementById('quickReplies');
            container.innerHTML = '';
            replies.forEach(text => {
                const btn = document.createElement('button');
                btn.className = 'whitespace-nowrap px-3 py-1 bg-white border border-teal-200 text-teal-700 text-xs rounded-full shadow-sm hover:bg-teal-50 transition';
                btn.innerText = text;
                btn.onclick = () => {
                    document.getElementById('chatInput').value = text;
                    sendUserMessage();
                };
                container.appendChild(btn);
            });
        }

        function sendUserMessage() {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text) return;

            // Add User Message
            const chatContainer = document.getElementById('chatMessages');
            const userBubble = document.createElement('div');
            userBubble.className = 'chat-bubble bubble-user';
            userBubble.innerText = text;
            chatContainer.appendChild(userBubble);
            
            input.value = '';
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Simulate AI Response Logic (Mocking Gemini + Streamlit logic)
            setTimeout(() => {
                // Mock Logic: If text is short, assume it's okay. If it contains "깎아", give specific response.
                // Randomly trigger "Correction" to demonstrate feature.
                
                let responseText = "";
                let correction = null;

                if (currentScenarioKey === 'market' && text.includes('깎아')) {
                    responseText = "에이~ 남는 것도 없어! 그럼 500원만 깎아줄게.";
                } else if (currentScenarioKey === 'restaurant' && text.includes('메뉴')) {
                    responseText = "여기 메뉴판 있습니다. 불고기가 아주 맛있어요.";
                } else if (Math.random() > 0.5) {
                    responseText = "네, 알겠습니다. 또 필요한 건 없으신가요?";
                } else {
                    // Trigger Correction Scenario Mock
                    responseText = "네, 확인했습니다.";
                    correction = {
                        original: text,
                        better: text + "요" // Simple mock correction logic
                    };
                }

                addAiMessage(responseText, correction);

            }, 1000);
        }

        function addAiMessage(text, correction = null) {
            const chatContainer = document.getElementById('chatMessages');
            
            const wrapper = document.createElement('div');
            wrapper.className = 'flex flex-col items-start max-w-[85%] mb-4 animation-fade-in';

            // Persona Icon
            const icon = document.createElement('div');
            icon.className = 'text-xs text-gray-500 mb-1 ml-1';
            icon.innerText = scenarios[currentScenarioKey].role;
            wrapper.appendChild(icon);

            // Bubble
            const bubble = document.createElement('div');
            bubble.className = 'chat-bubble bubble-ai w-full';
            
            // Text Content
            const textSpan = document.createElement('span');
            textSpan.innerText = text;
            bubble.appendChild(textSpan);

            // Correction UI (If exists)
            if (correction) {
                const corBox = document.createElement('div');
                corBox.className = 'correction-box';
                corBox.innerHTML = `
                    <div class="font-bold text-red-500 text-[10px] uppercase mb-1">AI Correction Tip</div>
                    <div class="text-gray-400 line-through text-xs">${correction.original}</div>
                    <div class="text-teal-700 font-medium text-sm">"${correction.better}" (더 자연스러워요)</div>
                `;
                bubble.appendChild(corBox);
            }

            // Mock Audio Player (gTTS)
            const audioMock = document.createElement('div');
            audioMock.className = 'audio-player-mock';
            audioMock.innerHTML = `
                <div class="play-btn">▶</div>
                <div class="h-1 bg-gray-300 w-24 rounded overflow-hidden">
                    <div class="h-full bg-teal-500 w-1/3"></div>
                </div>
                <div class="text-[10px] text-gray-500">0:04</div>
            `;
            audioMock.onclick = () => {
                // Visual feedback only
                audioMock.querySelector('.play-btn').innerText = '⏸';
                setTimeout(() => audioMock.querySelector('.play-btn').innerText = '▶', 1000);
            };
            bubble.appendChild(audioMock);

            wrapper.appendChild(bubble);
            chatContainer.appendChild(wrapper);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        // Initialize
        window.onload = function() {
            initCharts();
        };

    </script>
</body>
</html>