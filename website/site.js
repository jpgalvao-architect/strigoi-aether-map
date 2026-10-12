// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const pt = {};
  document.querySelectorAll('[data-i18n]').forEach(el => { pt[el.dataset.i18n] ??= el.innerHTML; });
  document.querySelectorAll('[data-i18n-alt]').forEach(el => { pt[el.dataset.i18nAlt] ??= el.alt; });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { pt[el.dataset.i18nAria] ??= el.getAttribute('aria-label'); });
  Object.assign(pt, {
    'page.title': 'Strigoi Aether Map — sua próxima descoberta',
    'legal.page.title': 'Termos de uso — Strigoi Aether Map',
    'screen.overlay': 'Configuração do overlay com as mesmas camadas para Atlas, minimapa e mapa grande',
    'screen.events': 'Agenda de eventos do Strigoi com perfil da América do Sul',
    'screen.sonar': 'Tela do Sonar de cubos com seleção do aplicativo e sensibilidade',
    'showcase.overlay.title': 'Um filtro. Todos os mapas.',
    'showcase.overlay.description': 'Sua escolha de camadas acompanha o minimapa e o mapa grande. Abra M e o overlay muda com você.',
    'showcase.events.title': 'Um olho na aventura. Outro no relógio.',
    'showcase.events.description': 'Escolha o evento do painel flutuante. Recolha para acompanhar o próximo horário ou expanda para ver o dia.',
    'tab.combat': 'Combate',
    'screen.combat': 'Módulo Combate com dano observado, DPS e participação do grupo',
    'showcase.combat.title': 'Seu grupo. Seu dano observado.',
    'showcase.combat.description': 'A medição começa automaticamente e aguarda o jogo. Controle a visibilidade do placar no menu rápido; ocultá-lo mantém a leitura. A próxima instância reconhecida abre um novo placar e preserva o histórico.',
    'download.beta': 'Novo menu rápido para Sonar, mapas, combate e eventos. O combate começa automaticamente ao abrir o app e aguarda o jogo. A leitura é experimental; os resultados podem ser parciais.',
    'showcase.sonar.title': 'O som vira uma pista na tela.',
    'showcase.sonar.description': 'Selecione o áudio do jogo, escolha a sensibilidade e ative o Sonar. Você controla quando ele começa e termina.',
  });
  const en = {
    'skip': 'Skip to content', 'navigation': 'Main navigation', 'language': 'Language',
    'page.title': 'Strigoi Aether Map — your next discovery', 'legal.page.title': 'Terms of use — Strigoi Aether Map',
    'nav.explore': 'Explore', 'nav.sonar': 'Sonar', 'nav.download': 'Downloads',
    'hero.title': 'Your next<br>discovery<br><em>starts here.</em>',
    'hero.description': 'Maps, gatherables, cubes, events and combat in one place. Aether minds the map. You live the adventure.',
    'hero.tour': 'Meet the app', 'hero.platform': 'Windows 10/11 · 64-bit · PT-BR / EN-US',
    'hero.free': 'Free, with open-source code', 'hero.license': 'GPLv3 code',
    'hero.cube': 'Your next clue is nearby.', 'hero.map': 'Your exploration journal',
    'hero.guardian': 'LITTLE GUARDIAN. GREAT DISCOVERIES.',
    'mascot.alt': 'Aether, a small Asmodian-inspired vampire with a map and dark wings',
    'ribbon.maps': 'Real maps', 'ribbon.overlay': 'External overlay', 'ribbon.sonar': 'Hearing accessibility', 'ribbon.local': 'Your records, on your PC',
    'explore.eyebrow': 'LESS ALT-TAB. MORE EXPLORATION.',
    'explore.title': 'A map that follows<br>your journey.',
    'explore.description': 'Choose your layers, record your visits and let Strigoi track what matters to you.',
    'showcase.label': 'Explore the app screens', 'tab.atlas': 'Atlas', 'tab.overlay': 'Overlay', 'tab.events': 'Events',
    'showcase.actual': 'ACTUAL APP SCREEN',
    'screen.atlas': 'App atlas displaying the real Altgard map',
    'screen.overlay': 'Overlay settings with shared layers for the atlas, minimap and full map',
    'screen.events': 'Strigoi event schedule with a South America profile',
    'screen.sonar': 'Cube Sonar screen with application and sensitivity selection',
    'showcase.atlas.title': 'Your atlas. Your layers.',
    'showcase.atlas.description': 'See herbs and cubes together, filter resources and mark the places you have visited.',
    'showcase.overlay.title': 'One filter. Every map.',
    'showcase.overlay.description': 'Your chosen layers follow the minimap and full map. Press M and the overlay switches with you.',
    'showcase.events.title': 'Adventure in sight. Time on your side.',
    'showcase.events.description': 'Choose the floating panel event. Collapse it to track the next occurrence or expand it to see the day.',
    'tab.combat': 'Combat',
    'screen.combat': 'Combat module with observed damage, DPS and group share',
    'showcase.combat.title': 'Your group. Your observed damage.',
    'showcase.combat.description': 'Capture starts automatically and waits for the game. Show or hide the meter through quick controls; hiding it keeps capture running. A recognized new instance opens a fresh meter and preserves your history.',
    'download.beta': 'New quick controls for Sonar, maps, combat and events. Combat starts automatically when the app opens and waits for the game. Capture is experimental; results may be partial.',
    'showcase.sonar.title': 'Sound becomes a clue on screen.',
    'showcase.sonar.description': 'Select the game audio, choose sensitivity and enable Sonar. You control when it starts and stops.',
    'explore.source': 'Real map images and community locations with documented sources. Markers indicate possible locations, not guaranteed spawns.',
    'sonar.eyebrow': 'HEARING ACCESSIBILITY',
    'sonar.title': 'A clue you<br>can <em>see.</em>',
    'sonar.description': 'The cube sound can go unnoticed. Sonar looks for signs of that sound in the game audio and turns the cue into an on-screen alert.',
    'sonar.point1': 'Select the game application and enable it when you want.',
    'sonar.point2': 'No microphone, recording or audio uploads.',
    'sonar.point3': 'Sonar starts off each time the app opens.',
    'sonar.note': 'Developed as an accessibility feature for deaf and hard-of-hearing people. The alert is a clue: it does not confirm a cube or reveal its exact location.',
    'sonar.visual': 'A SOUND CUE. A VISUAL ALERT.',
    'start.eyebrow': 'FROM DOWNLOAD TO ADVENTURE', 'start.title': 'Ready in a few steps.',
    'start.one.title': 'Install and choose your language', 'start.one.text': 'Download the installer, read the terms and choose Portuguese or English. No Python installation needed.',
    'start.two.title': 'Build your map', 'start.two.text': 'Choose your atlas layers. The same selection appears on the minimap and full map.',
    'start.three.title': 'Join the adventure', 'start.three.text': 'Enable the overlay, select the minimap terrain once and choose the event to track.',
    'download.eyebrow': 'YOUR LITTLE GUARDIAN IS READY', 'download.title': 'See you in Altgard.',
    'download.description': 'Choose how to use Strigoi. Both versions offer the same features and include source code.',
    'download.installer': 'Download installer', 'download.recommended': 'Recommended',
    'download.installer.detail': 'Shortcuts, initial language, uninstaller and official Npcap setup for combat.',
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
    'faq.five.a': 'Open Settings → App language. Switching between Brazilian Portuguese and US English is immediate. It does not change your filters, visits, region or time zone.',
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
  const translations = { pt_BR: pt, en_US: en };
  const htmlKeys = new Set(['hero.title', 'explore.title', 'sonar.title']);
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
    if (!translations[next]) return;
    language = next;
    const t = translations[next];
    document.documentElement.lang = next === 'en_US' ? 'en-US' : 'pt-BR';
    document.title = t[document.body.dataset.page === 'terms' ? 'legal.page.title' : 'page.title'];
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const text = t[el.dataset.i18n];
      if (text === undefined) return;
      if (htmlKeys.has(el.dataset.i18n)) el.innerHTML = text;
      else el.textContent = text;
    });
    document.querySelectorAll('[data-i18n-alt]').forEach(el => { if (t[el.dataset.i18nAlt]) el.alt = t[el.dataset.i18nAlt]; });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => { if (t[el.dataset.i18nAria]) el.setAttribute('aria-label', t[el.dataset.i18nAria]); });
    document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === next)));
    document.querySelectorAll('[data-legal-language]').forEach(article => { article.hidden = article.dataset.legalLanguage !== next; });
    document.querySelectorAll('[data-alert-image]').forEach(image => { image.src = `assets/sonar-alert-${next}.webp`; });
    updateShowcase();
    try { localStorage.setItem('strigoi-site-language', next); } catch { /* Reading the page never requires local storage. */ }
  }
  for (const button of document.querySelectorAll('[data-language]')) button.addEventListener('click', () => setLanguage(button.dataset.language));
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
  const preference = readPreference();
  setLanguage(translations[preference] ? preference : (navigator.language.toLowerCase().startsWith('pt') ? 'pt_BR' : 'en_US'));
})();
