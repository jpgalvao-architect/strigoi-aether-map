// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const pt = {};
  document.querySelectorAll('[data-i18n]').forEach(el => { pt[el.dataset.i18n] ??= el.innerHTML; });
  document.querySelectorAll('[data-i18n-alt]').forEach(el => { pt[el.dataset.i18nAlt] ??= el.alt; });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { pt[el.dataset.i18nAria] ??= el.getAttribute('aria-label'); });
  Object.assign(pt, {
    'page.title': 'Azphelumbra — sua próxima descoberta',
    'legal.page.title': 'Termos de uso — Azphelumbra',
    'screen.overlay': 'Configuração do overlay com as mesmas camadas para Atlas, minimapa e mapa grande',
    'screen.events': 'Agenda de eventos do Azphelumbra com perfil da América do Sul',
    'screen.sonar': 'Tela do Sonar de cubos com seleção do aplicativo e sensibilidade',
    'showcase.overlay.title': 'Um filtro. Todos os mapas.',
    'showcase.overlay.description': 'As camadas acompanham a região reconhecida no minimapa e no mapa grande. Seus filtros continuam ativos ao viajar.',
    'showcase.events.title': 'Um olho na aventura. Outro no relógio.',
    'showcase.events.description': 'Escolha o evento do painel flutuante. Recolha para acompanhar o próximo horário ou expanda para ver o dia.',
    "tab.routes": "Rotas",
    "screen.routes": "Prévia de rota de farm com paradas e opções de percurso",
    "showcase.routes.title": "Escolha o alvo. Trace sua jornada.",
    "showcase.routes.description": "Crie circuitos ou trajetos de ida, ajuste passagens e acompanhe as paradas no minimapa com o guia Fio ou Guia. Linhas sugeridas precisam ser conferidas.",
    'tab.routine': 'Rotina',
    'screen.routine': 'Panorama de personagens e saldos de Energia de Odyle',
    'showcase.routine.title': 'Seus personagens. Sua próxima jornada.',
    'showcase.routine.description': 'Consulte os saldos de Odyle recebidos do jogo e escolha Pulso compacto ou Faixa para acompanhar o personagem atual. Cada registro mostra se a leitura é atual ou salva.',
    'tab.pets': 'Pets',
    'screen.pets': 'Coleção de pets com retratos originais e acompanhamento',
    'showcase.pets.title': 'Sua coleção. Seus próximos objetivos.',
    'showcase.pets.description': 'Marque um pet para acompanhar as almas coletadas. Abra seus detalhes no jogo para ler o Insight e confirmar o total. Os mapas mostram locais de farm de referência.',
    'tab.combat': 'Combate',
    'screen.combat': 'Módulo Combate com dano observado, DPS e participação do grupo',
    'showcase.combat.title': 'Seu grupo. Seu dano observado.',
    'showcase.combat.description': 'A medição aguarda o jogo e o painel aparece nas instâncias reconhecidas. Ao sair, ele se oculta; a leitura continua. O menu rápido permite desativar a exibição, e o histórico fica preservado.',
    'download.beta': "A beta.17 reúne pins e desenhos no Editor tático e adiciona ferramentas rápidas ao Live Sync.",
    'download.siege': "Configurar Siege Command",
    'showcase.sonar.title': 'O som vira uma pista na tela.',
    'showcase.sonar.description': 'Ative o Sonar para receber um aviso visual quando o som de um Cubo Oculto for reconhecido.',
  });
  const en = {
    'download.release': "GitHub release notes",
    'download.previous': "Previous version · beta.16",
    'download.stable': "Stable release · v0.8.0",
    "live.feature.title": "Live Sync Beta — Share strategies in real time",
    "live.feature.intro": "Share Lower Reshanta pins, flight rings and tactical drawings with your group during a siege.",
    "live.feature.host": "Host on your Cloudflare account",
    "live.feature.hostBody": "The caller creates a session in their own account, uses quick tools to mark the map, and decides when to publish.",
    "live.feature.join": "Join with an invite",
    "live.feature.joinBody": "Players can join without a Cloudflare account and automatically receive each published revision.",
    "live.feature.map": "See the plan on the game map",
    "live.feature.mapBody": "Markers appear in the Reshanta overlay. Your personal data and local presets stay on your computer.",
    "live.feature.guide": "Open the Live Sync guide",
    "live.feature.feedback": "Report an issue",
    "live.feature.limit": "The 2,000-client test used a local emulator. Capacity for a real session still needs to be measured.",
    'skip': 'Skip to content', 'navigation': 'Main navigation', 'language': 'Language',
    'page.title': 'Azphelumbra — your next discovery', 'legal.page.title': 'Terms of use — Azphelumbra',
    'nav.explore': 'Explore', 'nav.sonar': 'Sonar', 'nav.download': 'Downloads',
    'hero.title': 'Your next<br>discovery<br><em>starts here.</em>',
    'hero.description': 'Maps, farming routes, cubes, pets, events and combat in one place. Aether minds the map. You live the adventure.',
    'hero.tour': 'Meet the app', 'hero.platform': 'Windows 10/11 · 64-bit · PT-BR / EN-US / ES-419',
    'hero.free': 'Free, with open-source code', 'hero.license': 'GPLv3 code',
    'hero.cube': 'Your next clue is nearby.', 'hero.map': 'Your exploration journal',
    'hero.guardian': 'LITTLE GUARDIAN. GREAT DISCOVERIES.',
    'mascot.alt': 'Aether, a small Asmodian-inspired vampire with a map and dark wings',
    'ribbon.maps': 'Real maps', 'ribbon.overlay': 'External overlay', 'ribbon.sonar': 'Hearing accessibility', 'ribbon.local': 'Your records, on your PC',
    'explore.eyebrow': 'LESS ALT-TAB. MORE EXPLORATION.',
    'explore.title': 'A map that follows<br>your journey.',
    'explore.description': 'Choose your layers, record your visits and let Azphelumbra track what matters to you.',
    'showcase.label': 'Explore the app screens', 'tab.atlas': 'Atlas', 'tab.overlay': 'Overlay', 'tab.events': 'Events',
    'showcase.actual': 'ACTUAL APP SCREEN',
    'screen.atlas': 'App atlas displaying the real Altgard map',
    'screen.overlay': 'Overlay settings with shared layers for the atlas, minimap and full map',
    'screen.events': 'Azphelumbra event schedule with a South America profile',
    'screen.sonar': 'Cube Sonar screen with application and sensitivity selection',
    'showcase.atlas.title': 'Your atlas. Your layers.',
    'showcase.atlas.description': 'See herbs and cubes together, filter resources and mark the places you have visited.',
    'showcase.overlay.title': 'One filter. Every map.',
    'showcase.overlay.description': 'Layers follow the region recognized on the minimap and full map. Your filters stay active as you travel.',
    'showcase.events.title': 'Adventure in sight. Time on your side.',
    'showcase.events.description': 'Choose the floating panel event. Collapse it to track the next occurrence or expand it to see the day.',
    "tab.routes": "Routes",
    "screen.routes": "Farming route preview with stops and journey controls",
    "showcase.routes.title": "Choose your target. Plan your journey.",
    "showcase.routes.description": "Build circuits or one-way routes, edit passages and follow minimap stops with Strip or Guide. Suggested paths need in-game checking.",
    'tab.routine': 'Routine',
    'screen.routine': 'Character overview and Odyle Energy balances',
    'showcase.routine.title': 'Your characters. Your next journey.',
    'showcase.routine.description': 'View Odyle balances received from the game and choose Compact Pulse or Strip to follow the current character. Each record distinguishes current and saved readings.',
    'tab.pets': 'Pets',
    'screen.pets': 'Pet collection with original portraits and tracking',
    'showcase.pets.title': 'Your collection. Your next goals.',
    'showcase.pets.description': 'Track a pet and follow collected souls. Open its in-game details to read Insight and confirm the total. Maps show reference farming locations.',
    'tab.combat': 'Combat',
    'screen.combat': 'Combat module with observed damage, DPS and group share',
    'showcase.combat.title': 'Your group. Your observed damage.',
    'showcase.combat.description': 'Capture waits for the game and the panel appears in recognized instances. On exit it hides while capture continues. Quick controls can disable panel display, and history is preserved.',
    'download.beta': "Beta.17 brings pins and drawings together in the Tactical editor and adds quick tools to Live Sync.",
    'download.siege': "Set up Siege Command",
    'showcase.sonar.title': 'Sound becomes a clue on screen.',
    'showcase.sonar.description': 'Enable Sonar to receive a visual alert when it recognizes the sound of a Hidden Cube.',
    'explore.source': 'Real map images and community locations with documented sources. Markers indicate possible locations, not guaranteed spawns.',
    'sonar.eyebrow': 'HEARING ACCESSIBILITY',
    'sonar.title': 'A clue you<br>can <em>see.</em>',
    'sonar.description': 'Sonar recognizes the Hidden Cube sound and shows an alert so you can search nearby.',
    'sonar.point1': 'Select the game application and enable it when you want.',
    'sonar.point2': 'No microphone, recording or audio uploads.',
    'sonar.point3': 'Sonar remembers your choice and waits for the game when reopened.',
    'sonar.note': 'Developed as an accessibility feature for deaf and hard-of-hearing people. The alert is a clue: it does not confirm a cube or reveal its exact location.',
    'sonar.visual': 'A SOUND CUE. A VISUAL ALERT.',
    'start.eyebrow': 'FROM DOWNLOAD TO ADVENTURE', 'start.title': 'Ready in a few steps.',
    'start.one.title': 'Install and choose your language', 'start.one.text': 'Download Setup, choose a language, and read the terms. Azphelumbra runs without installing Python.',
    'start.two.title': 'Build your map', 'start.two.text': 'Choose your atlas layers. The same selection appears on the minimap and full map.',
    'start.three.title': 'Join the adventure', 'start.three.text': 'Enable the overlay, select the minimap terrain once and choose the event to track.',
    'download.eyebrow': 'YOUR LITTLE GUARDIAN IS READY', 'download.title': 'See you in Atreia.',
    'download.description': 'Choose how to use Azphelumbra. Both versions offer the same features and include source code.',
    'download.installer': 'Download installer', 'download.recommended': 'Recommended',
    'download.installer.detail': 'Shortcuts, initial language, uninstaller and official Npcap setup for Combat and Pets.',
    'download.portable': 'Download portable', 'download.portable.detail': 'Extract the entire folder and open the app.',
    'download.terms': 'Read the terms of use', 'download.checksums': 'Verify files · SHA-256',
    'faq.eyebrow': 'NO MYSTERY', 'faq.title': 'Before you set off.',
    'faq.one.q': 'Does the app modify the game?',
    'faq.one.a': 'No. Markers and alerts are external overlay windows. The app analyzes the screen image and receives audio through Windows; it does not inject code into DLLs, modify files or read AION 2 memory. Combat passively reads the game connection using Npcap. The terms describe the conditions of use.',
    'faq.two.q': 'Does it work on the minimap and full map?',
    'faq.two.a': 'Yes, with a rectangular, north-fixed minimap. Select only the minimap terrain, without the title bar. Opening the full map with M switches the overlay automatically; closing it returns to the minimap.',
    'faq.three.q': 'Is the schedule for South America?',
    'faq.three.a': 'SA schedule profiles include documented sources and times in your chosen time zone. Maps and possible locations come from shared community datasets; locations have not been individually verified in SA. You can view the sources in the app.',
    'faq.four.q': 'Can I use it without opening the game?',
    'faq.four.a': 'The atlas, visits and local schedule work offline. For overlay and Sonar, open the game and enable these features. Your preferences and records stay on your computer.',
    'faq.five.q': 'How do I change the language after installing?',
    'faq.five.a': 'Open Settings → App language. Switch instantly between Brazilian Portuguese, US English, and Latin American Spanish. Your filters, visits, region, and time zone are preserved.',
    'faq.six.q': 'Where are the licenses and source code?',
    'faq.six.a': 'Original code uses GPLv3 and is available on GitHub and in the downloads. Maps, community data and third-party components retain their own rights and licenses, including CC BY-NC 4.0 for community maps and data.',
    'faq.licenses': 'View licenses and credits →',
    'support.title': 'Enjoying the company?',
    'support.description': 'If my work helped you and you would like to give something back, you can support me here. No pressure: using the app, sending feedback and sharing it with friends already helps a lot.',
    'support.creator': 'Support the creator', 'support.recipient': 'Personal creator support · Mercado Pago',
    'support.community.eyebrow': 'SUPPORT THE DEAF COMMUNITY TOO',
    'support.community.description': 'You can also contribute directly to Brazilian organizations that support deaf people.',
    'support.community.note': 'Donate through the organizations’ official channels. Recipients differ from personal creator support.',
    'footer.creator': 'Contact:', 'footer.source': 'Source code', 'footer.terms': 'Terms of use', 'footer.feedback': 'Feedback',
    'footer.note': 'An independent project with no official affiliation with AION 2 or NCSOFT. Game trademarks and images belong to their respective owners. Sources and credits are included with the app.',
    'legal.back': '← Back to the app', 'legal.title': 'Terms of use',
    'legal.intro': 'The complete terms included in the installer. Original code uses GPLv3; third-party materials retain their respective rights and licenses.',
    'legal.license': 'Read the complete GPLv3 license →',
  };
  const es = {
    'download.release': "Notas en GitHub Releases",
    'download.previous': "Versión anterior · beta.16",
    'download.stable': "Versión estable · v0.8.0",
    "live.feature.title": "Live Sync Beta — Estrategias compartidas en tiempo real",
    "live.feature.intro": "Comparte pines, anillos de vuelo y dibujos tácticos de Lower Reshanta con tu grupo durante el asedio.",
    "live.feature.host": "Hospeda en tu cuenta de Cloudflare",
    "live.feature.hostBody": "El caller crea una sesión en su cuenta, usa las herramientas rápidas para marcar el mapa y decide cuándo publicar.",
    "live.feature.join": "Únete con una invitación",
    "live.feature.joinBody": "Los jugadores se unen sin cuenta de Cloudflare y reciben automáticamente cada revisión publicada.",
    "live.feature.map": "Consulta el plan en el mapa del juego",
    "live.feature.mapBody": "Las marcas aparecen en el overlay de Reshanta. Tus datos personales y ajustes locales permanecen en tu equipo.",
    "live.feature.guide": "Abrir la guía de Live Sync",
    "live.feature.feedback": "Reportar un problema",
    "live.feature.limit": "La prueba con 2.000 clientes se hizo en un emulador local. La capacidad de una sesión real aún está por medir.",
    "skip": "Saltar al contenido",
    "navigation": "Navegación principal",
    "language": "Idioma",
    "page.title": "Azphelumbra — tu próximo descubrimiento",
    "legal.page.title": "Términos de uso — Azphelumbra",
    "nav.explore": "Explorar",
    "nav.sonar": "Sonar",
    "nav.download": "Descargas",
    "hero.title": "Descubre<br>tu próxima<br><em>aventura.</em>",
    "hero.description": "Mapas, rutas de farmeo, cubos, mascotas, eventos y combate en un solo lugar. Aether se encarga del mapa mientras tú juegas.",
    "hero.tour": "Conocer la aplicación",
    "hero.platform": "Windows 10/11 · 64 bits · PT-BR / EN-US / ES-419",
    "hero.free": "Gratis y de código abierto",
    "hero.license": "Código GPLv3",
    "hero.cube": "Tu próxima pista está cerca.",
    "hero.map": "Tu cuaderno de exploración",
    "hero.guardian": "PEQUEÑO GUARDIÁN. GRANDES DESCUBRIMIENTOS.",
    "mascot.alt": "Aether, un pequeño vampiro inspirado en los asmodianos, con un mapa y alas oscuras",
    "ribbon.maps": "Mapas reales",
    "ribbon.overlay": "Superposición externa",
    "ribbon.sonar": "Accesibilidad auditiva",
    "ribbon.local": "Tus registros, en tu equipo",
    "explore.eyebrow": "MENOS ALT+TAB. MÁS EXPLORACIÓN.",
    "explore.title": "Un mapa que te acompaña<br><em>a donde vayas.</em>",
    "explore.description": "Elige tus capas, registra tus visitas y sigue lo que te interesa mientras exploras.",
    "showcase.label": "Explora las pantallas de la aplicación",
    "tab.atlas": "Atlas",
    "tab.overlay": "Superposición",
    "tab.events": "Eventos",
    "showcase.actual": "PANTALLA REAL DE LA APLICACIÓN",
    "screen.atlas": "Atlas con el mapa de Altgard",
    "screen.overlay": "Ajustes de superposición con capas compartidas entre el atlas, el minimapa y el mapa grande",
    "screen.events": "Agenda de eventos de Azphelumbra con el perfil de Sudamérica",
    "screen.sonar": "Pantalla del Sonar de cubos con controles para elegir la aplicación y la sensibilidad",
    "showcase.atlas.title": "Tu atlas, con las capas que elijas",
    "showcase.atlas.description": "Ve hierbas y cubos juntos, filtra los recursos y marca los lugares que ya visitaste.",
    "showcase.overlay.title": "Un filtro para todos tus mapas",
    "showcase.overlay.description": "Las capas siguen la región que el minimapa o el mapa grande reconocen. Tus filtros siguen activos cuando viajas.",
    "showcase.events.title": "Ten a mano el horario de los eventos",
    "showcase.events.description": "Elige el evento del panel flotante. Contrae el panel para seguir el próximo horario o expándelo para ver todo el día.",
    "tab.routes": "Rutas",
    "screen.routes": "Vista previa de una ruta de farmeo con paradas y controles del recorrido",
    "showcase.routes.title": "Elige qué buscar y arma tu ruta",
    "showcase.routes.description": "Crea circuitos o rutas de ida, ajusta los tramos y sigue las paradas en el minimapa con Trazado o Guía. Verifica los tramos sugeridos en el juego.",
    "tab.routine": "Rutina",
    "screen.routine": "Vista general de personajes y saldos de Energía de Odyle",
    "showcase.routine.title": "Consulta el saldo de cada personaje",
    "showcase.routine.description": "Ve los saldos de Odyle que llegan del juego y elige Pulso compacto o Barra para seguir al personaje actual. Cada registro muestra si la lectura es actual o guardada.",
    "tab.pets": "Mascotas",
    "screen.pets": "Colección de mascotas con retratos originales y controles de seguimiento",
    "showcase.pets.title": "Sigue el progreso de tu colección",
    "showcase.pets.description": "Elige una mascota y sigue las almas que recolectes. Abre sus detalles en el juego para leer el Insight y confirmar el total. Los mapas muestran ubicaciones de referencia para farmear.",
    "tab.combat": "Combate",
    "screen.combat": "Módulo de combate con daño registrado, DPS y participación de cada integrante del grupo",
    "showcase.combat.title": "Revisa el daño que hizo tu grupo",
    "showcase.combat.description": "La medición espera al juego y el panel aparece en las instancias reconocidas. Al salir de la instancia, el panel se oculta y la medición continúa. Puedes ocultarlo desde el menú rápido. Los resultados quedan en el historial.",
    "download.beta": "La beta.17 reúne marcadores y dibujos en el Editor táctico y agrega herramientas rápidas a Live Sync.",
    "download.siege": "Configurar Siege Command",
    "showcase.sonar.title": "Una alerta visual para el sonido del cubo",
    "showcase.sonar.description": "Activa el Sonar para recibir un aviso visual cuando reconozca el sonido de un Cubo Oculto.",
    "explore.source": "Imágenes de mapas reales y ubicaciones de la comunidad con fuentes documentadas. Confirma en el juego si el recurso está disponible en los puntos marcados.",
    "sonar.eyebrow": "ACCESIBILIDAD AUDITIVA",
    "sonar.title": "Una pista que<br>puedes <em>ver.</em>",
    "sonar.description": "El Sonar reconoce el sonido característico del Cubo Oculto y te avisa para que busques en los alrededores.",
    "sonar.point1": "Selecciona la aplicación del juego y activa el Sonar cuando quieras.",
    "sonar.point2": "El audio se analiza en tu equipo, sin usar el micrófono ni grabar o enviar el sonido.",
    "sonar.point3": "El Sonar recuerda tu elección y espera al juego cuando vuelves a abrir la aplicación.",
    "sonar.note": "Creado como recurso de accesibilidad para personas sordas o con pérdida auditiva. Cuando recibas un aviso, busca por la zona para confirmar que el cubo está ahí.",
    "sonar.visual": "UNA SEÑAL SONORA. UN AVISO VISUAL.",
    "start.eyebrow": "DE LA DESCARGA A LA AVENTURA",
    "start.title": "Empieza en tres pasos",
    "start.one.title": "Instala y elige el idioma",
    "start.one.text": "Descarga el instalador, elige tu idioma y lee los términos. Azphelumbra funciona sin instalar Python.",
    "start.two.title": "Prepara tu mapa",
    "start.two.text": "Elige las capas del atlas. La misma selección se aplica al minimapa y al mapa grande.",
    "start.three.title": "Entra al juego",
    "start.three.text": "Activa la superposición, selecciona el terreno del minimapa una vez y elige qué evento seguir.",
    "download.eyebrow": "TU PEQUEÑO GUARDIÁN ESTÁ LISTO",
    "download.title": "Nos vemos en Atreia.",
    "download.description": "Elige cómo quieres usar Azphelumbra. Ambas ediciones ofrecen las mismas funciones e incluyen el código fuente.",
    "download.installer": "Descargar instalador",
    "download.recommended": "Recomendado",
    "download.installer.detail": "Accesos directos, idioma inicial, desinstalador y asistente oficial de Npcap para Combate y Mascotas.",
    "download.portable": "Descargar edición portátil",
    "download.portable.detail": "Extrae la carpeta completa y abre la aplicación.",
    "download.terms": "Leer los términos de uso",
    "download.checksums": "Verificar archivos · SHA-256",
    "faq.eyebrow": "PREGUNTAS FRECUENTES",
    "faq.title": "Antes de jugar",
    "faq.one.q": "¿La aplicación modifica el juego?",
    "faq.one.a": "Los marcadores y avisos aparecen en ventanas externas superpuestas al juego. Azphelumbra analiza la imagen de la pantalla y recibe el audio a través de Windows. Funciona sin inyectar código en las DLL, modificar archivos o leer la memoria de AION 2. Combate lee pasivamente la conexión del juego mediante Npcap. Consulta las condiciones en los términos de uso.",
    "faq.two.q": "¿Funciona en el minimapa y el mapa grande?",
    "faq.two.a": "Sí, con el minimapa rectangular orientado con el norte fijo. Selecciona solo el terreno del minimapa y deja fuera la barra de título. La superposición cambia al mapa grande al presionar M y vuelve al minimapa cuando lo cierras.",
    "faq.three.q": "¿La agenda es para Sudamérica?",
    "faq.three.a": "Hay perfiles de agenda para Sudamérica con fuentes documentadas y horarios en la zona horaria que elijas. Los mapas y las posibles ubicaciones vienen de bases comunitarias. Puedes consultar sus fuentes en la aplicación y confirmar cada ubicación en el juego.",
    "faq.four.q": "¿Puedo usar Azphelumbra con el juego cerrado?",
    "faq.four.a": "El atlas, las visitas y la agenda local funcionan sin conexión. Para usar la superposición y el Sonar, abre el juego y activa esas funciones. Tus preferencias y registros se guardan en tu equipo.",
    "faq.five.q": "¿Cómo cambio el idioma después de instalar?",
    "faq.five.a": "Abre Configuración → Idioma de la aplicación. Puedes alternar al instante entre portugués de Brasil, inglés de Estados Unidos y español latinoamericano. Tus filtros, visitas, región y zona horaria se conservan.",
    "faq.six.q": "¿Dónde están las licencias y el código?",
    "faq.six.a": "El código propio usa GPLv3 y está disponible en GitHub y en las descargas. Los mapas, los datos comunitarios y los componentes de terceros conservan sus derechos y licencias. Los mapas y datos comunitarios incluyen material con licencia CC BY-NC 4.0.",
    "faq.licenses": "Consultar licencias y créditos →",
    "support.title": "¿Te está gustando Azphelumbra?",
    "support.description": "Si mi trabajo te sirvió y quieres apoyarme, puedes hacerlo aquí. Usar la aplicación, enviarme comentarios o compartirla con tus amigos ya me ayuda muchísimo.",
    "support.creator": "Apoyar al creador",
    "support.recipient": "Apoyo personal al creador · Mercado Pago",
    "support.community.eyebrow": "APOYA TAMBIÉN A LA COMUNIDAD SORDA",
    "support.community.description": "Puedes contribuir directamente a organizaciones brasileñas que apoyan a las personas sordas.",
    "support.community.note": "Usa los canales oficiales para que tu donación llegue directamente a la organización que elijas.",
    "footer.creator": "Contacto:",
    "footer.source": "Código fuente",
    "footer.terms": "Términos de uso",
    "footer.feedback": "Comentarios",
    "footer.note": "Proyecto independiente sin afiliación oficial con AION 2 ni con NCSOFT. Las marcas e imágenes del juego pertenecen a sus respectivos titulares. La aplicación incluye las fuentes y los créditos.",
    "legal.back": "← Volver a la aplicación",
    "legal.title": "Términos de uso",
    "legal.intro": "Estos son los términos completos que se incluyen en el instalador. El código propio usa GPLv3. Los materiales de terceros conservan sus derechos y licencias.",
    "legal.license": "Leer el texto completo de la GPLv3 →"
  };
  Object.assign(pt, window.StrigoiGuide?.ui.pt_BR || {'nav.guide':'Guia de uso','start.guide':'Abrir guia interativo'});
  Object.assign(en, window.StrigoiGuide?.ui.en_US || {'nav.guide':'User guide','start.guide':'Open interactive guide'});
  Object.assign(es, window.StrigoiGuide?.ui['es-419'] || {'nav.guide':'Guía de uso','start.guide':'Abrir guía interactiva'});
  const translations = { pt_BR: pt, en_US: en, 'es-419': es };
  const liveGuides = {
    pt_BR: ['Live Sync — Guia de configuração do Azphelumbra', '← Guia do Azphelumbra'],
    en_US: ['Live Sync — Azphelumbra setup guide', '← Azphelumbra guide'],
    'es-419': ['Live Sync — Guía de configuración de Azphelumbra', '← Guía de Azphelumbra'],
  };
  const languageTags = { pt_BR: 'pt-BR', en_US: 'en-US', 'es-419': 'es-419' };
  const supports = locale => Object.hasOwn(translations, locale);
  const htmlKeys = new Set(['hero.title', 'explore.title', 'sonar.title', 'guide.title']);
  const tabs = [...document.querySelectorAll('[data-tab]')];
  let selectedTab = 'atlas';
  let language = 'pt_BR';
  const readPreference = () => { try { return localStorage.getItem('strigoi-site-language'); } catch { return null; } };
  function updateShowcase() {
    const image = document.getElementById('app-screenshot');
    if (!image) return;
    const t = translations[language];
    image.src = `assets/app-${selectedTab}-${language}.webp`;
    image.alt = t[`screen.${selectedTab}`];
    image.dataset.i18nAlt = `screen.${selectedTab}`;
    for (const part of ['title', 'description']) {
      const el = document.getElementById(`showcase-${part}`);
      el.dataset.i18n = `showcase.${selectedTab}.${part}`;
      el.textContent = t[el.dataset.i18n];
    }
    document.getElementById('showcase-number').textContent = `0${tabs.findIndex(tab => tab.dataset.tab === selectedTab) + 1} / ${String(tabs.length).padStart(2, '0')}`;
    document.getElementById('showcase-icon').src = `assets/icons/${selectedTab}.svg`;
    document.getElementById('showcase-panel').setAttribute('aria-labelledby', `tab-${selectedTab}`);
    for (const tab of tabs) {
      const selected = tab.dataset.tab === selectedTab;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
  }
  function setLanguage(next) {
    if (!supports(next)) return;
    language = next;
    const t = translations[next];
    document.documentElement.lang = languageTags[next];
    document.documentElement.dataset.locale = next;
    document.querySelectorAll('time[data-release-date]').forEach(date => {
      date.textContent = new Intl.DateTimeFormat(languageTags[next], {
        dateStyle: 'medium', timeZone: 'UTC',
      }).format(new Date(date.dateTime + 'T00:00:00Z'));
    });
    const liveGuide = document.body.dataset.page === 'live-sync';
    document.title = liveGuide ? liveGuides[next][0] : t[document.body.dataset.page === 'terms' ? 'legal.page.title' : document.body.dataset.page === 'guide' ? 'guide.page.title' : 'page.title'];
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const text = el.dataset.i18n === 'live.back' ? liveGuides[next][1] : t[el.dataset.i18n];
      if (text === undefined) return;
      if (htmlKeys.has(el.dataset.i18n)) el.innerHTML = text;
      else el.textContent = text;
    });
    document.querySelectorAll('[data-i18n-alt]').forEach(el => { if (t[el.dataset.i18nAlt]) el.alt = t[el.dataset.i18nAlt]; });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => { if (t[el.dataset.i18nAria]) el.setAttribute('aria-label', t[el.dataset.i18nAria]); });
    document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === next)));
    document.querySelectorAll('[data-legal-language]').forEach(article => { article.hidden = article.dataset.legalLanguage !== next; });
    document.querySelectorAll('[data-alert-image]').forEach(image => {
      image.width = 350;
      image.height = next === 'pt_BR' ? 76 : 61;
      image.src = `assets/sonar-alert-${next}.webp`;
    });
    updateShowcase();
    document.dispatchEvent(new CustomEvent('strigoi:language', {detail: {language: next}}));
    document.querySelectorAll('a[href]').forEach(link => {
      const href = link.getAttribute('href');
      if (!/^(?:index|guide|terms|live-sync)\.html(?:[?#]|$)/.test(href)) return;
      const url = new URL(link.href);
      url.searchParams.set('lang', next);
      link.setAttribute('href', href.split(/[?#]/, 1)[0] + url.search + url.hash);
    });
    try { localStorage.setItem('strigoi-site-language', next); } catch { /* Reading the page never requires local storage. */ }
  }
  for (const button of document.querySelectorAll('[data-language]')) {
    button.addEventListener('click', () => {
      const next = button.dataset.language;
      const url = new URL(location.href);
      url.searchParams.set('lang', next);
      history.replaceState(history.state, '', url);
      setLanguage(next);
    });
  }
  for (const tab of tabs) {
    tab.addEventListener('click', () => { selectedTab = tab.dataset.tab; updateShowcase(); });
    tab.addEventListener('keydown', event => {
      const index = tabs.indexOf(tab);
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectedTab = tabs[next].dataset.tab; updateShowcase(); tabs[next].focus();
    });
  }
  const requestedLanguage = () => new URLSearchParams(location.search).get('lang');
  window.addEventListener('popstate', () => {
    const next = requestedLanguage();
    if (supports(next) && next !== language) setLanguage(next);
  });
  const requested = requestedLanguage();
  const preference = readPreference();
  const browserLanguage = navigator.language.toLowerCase().split('-')[0];
  const automatic = browserLanguage === 'es' ? 'es-419' : browserLanguage === 'pt' ? 'pt_BR' : 'en_US';
  setLanguage(supports(requested) ? requested : supports(preference) ? preference : automatic);
})();
