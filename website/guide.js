// SPDX-License-Identifier: GPL-3.0-only
(() => {
  'use strict';
  const content = window.StrigoiGuide;
  if (!content || document.body.dataset.page !== 'guide') return;
  const topics = content.topics;
  const $ = id => document.getElementById(id);
  const storageKey = 'strigoi-guide-v1';
  const keys = new Set(topics.flatMap(topic => topic.steps.map((_, index) => `${topic.id}:${index}`)));
  const total = keys.size;
  let language = document.documentElement.lang === 'en-US' ? 'en_US' : 'pt_BR';
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(storageKey)) || {}; } catch { /* Optional local progress. */ }
  if (typeof saved !== 'object' || Array.isArray(saved)) saved = {};
  const completed = new Set((Array.isArray(saved.completed) ? saved.completed : []).filter(key => keys.has(key)));
  let edition = saved.edition === 'portable' ? 'portable' : 'installer';
  let topicIndex = Math.max(0, topics.findIndex(topic => topic.id === saved.topic));
  let stepIndex = Number.isInteger(saved.step) ? Math.max(0, Math.min(saved.step, topics[topicIndex].steps.length - 1)) : 0;
  const text = value => value[language];
  const t = (key, values = {}) => Object.entries(values).reduce((copy, [name, value]) => copy.replace(`{${name}}`, value), content.ui[language][key]);
  function route() {
    const match = location.hash.match(/^#([a-z]+)(?:\/(\d+))?$/);
    if (!match) return null;
    const index = topics.findIndex(topic => topic.id === match[1]);
    if (index < 0) return null;
    return [index, Math.max(0, Math.min(Number(match[2] || 1) - 1, topics[index].steps.length - 1))];
  }
  const initial = route();
  if (initial) [topicIndex, stepIndex] = initial;
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify({topic: topics[topicIndex].id, step: stepIndex, edition, completed: [...completed]})); } catch { /* Usable when storage is blocked. */ }
  }
  function navigate(index, step, focus = true, updateUrl = true) {
    topicIndex = index; stepIndex = step;
    if (updateUrl) history.pushState(null, '', `#${topics[index].id}/${step + 1}`);
    render();
    if (focus) {
      $('guide-step-title').focus({preventScroll: true});
      $('guide-counter').scrollIntoView({block: 'start', behavior: 'auto'});
    }
  }
  function node(tag, value, className) {
    const el = document.createElement(tag);
    if (value !== undefined) el.textContent = value;
    if (className) el.className = className;
    return el;
  }
  function render() {
    const topic = topics[topicIndex];
    const step = topic.steps[stepIndex];
    const currentKey = `${topic.id}:${stepIndex}`;
    const nav = $('guide-topics'); nav.replaceChildren();
    topics.forEach((item, index) => {
      const button = node('button'); button.type = 'button'; button.dataset.topic = item.id;
      button.setAttribute('aria-current', String(index === topicIndex));
      const image = node('img'); image.src = `assets/icons/${item.icon}.svg`; image.alt = ''; image.width = 20; image.height = 20;
      const count = item.steps.filter((_, number) => completed.has(`${item.id}:${number}`)).length;
      button.append(image, node('span', text(item.title)), node('small', `${count}/${item.steps.length}`));
      button.addEventListener('click', () => navigate(index, 0)); nav.append(button);
    });
    $('guide-topic-title').textContent = text(topic.title);
    $('guide-description').textContent = text(topic.description);
    $('guide-counter').textContent = t('guide.step', {current: stepIndex + 1, total: topic.steps.length});
    const steps = $('guide-steps'); steps.replaceChildren();
    topic.steps.forEach((item, index) => {
      const li = node('li'); const button = node('button'); button.type = 'button'; button.dataset.step = index;
      button.setAttribute('aria-current', index === stepIndex ? 'step' : 'false');
      button.append(node('span', completed.has(`${topic.id}:${index}`) ? '✓' : String(index + 1)), node('span', text(item.title)));
      button.addEventListener('click', () => navigate(topicIndex, index)); li.append(button); steps.append(li);
    });
    $('guide-where').textContent = text(step.where);
    $('guide-step-title').textContent = text(step.title);
    $('guide-body').textContent = text(step[edition] || step.body);
    $('guide-tip').textContent = text(step.tip);
    $('guide-complete').checked = completed.has(currentKey);
    $('guide-edition').hidden = topic.id !== 'install';
    document.querySelectorAll('[name="edition"]').forEach(radio => { radio.checked = radio.value === edition; });
    const action = $('guide-action'); action.hidden = !step.action;
    if (step.action) {
      action.href = step.action.href; action.textContent = text(step.action.label);
      if (step.action.href.startsWith('https:')) { action.target = '_blank'; action.rel = 'noopener noreferrer'; }
      else { action.removeAttribute('target'); action.removeAttribute('rel'); }
    }
    const image = $('guide-image');
    image.src = topic.image === 'quick-menu' ? `assets/quick-menu-${language}.webp` : `assets/app-${topic.image}-${language}.webp`;
    image.alt = t('guide.imageAlt', {topic: text(topic.title)});
    image.width = topic.image === 'quick-menu' ? 288 : 1380; image.height = topic.image === 'quick-menu' ? 322 : 900;
    $('guide-zoom').classList.toggle('compact-screen', topic.image === 'quick-menu');
    $('guide-dialog-image').src = image.src; $('guide-dialog-image').alt = image.alt;
    $('guide-previous').disabled = stepIndex === 0;
    const nextTopic = stepIndex === topic.steps.length - 1;
    $('guide-next').disabled = nextTopic && topicIndex === topics.length - 1;
    const nextKey = $('guide-next').disabled ? 'guide.last' : nextTopic ? 'guide.nextTopic' : 'guide.next';
    $('guide-next').dataset.i18n = nextKey; $('guide-next').textContent = t(nextKey);
    $('guide-progress').max = total; $('guide-progress').value = completed.size;
    $('guide-progress-text').textContent = t('guide.completed', {done: completed.size, total});
    $('guide-announcement').textContent = completed.size === total ? t('guide.ready') : '';
    const help = $('guide-help'); help.replaceChildren();
    topic.help.forEach(item => { const details = node('details'); details.append(node('summary', text(item.question)), node('p', text(item.answer))); help.append(details); });
    $('guide-layout').hidden = false;
    save();
  }
  $('guide-complete').addEventListener('change', event => {
    const key = `${topics[topicIndex].id}:${stepIndex}`;
    if (event.target.checked) completed.add(key); else completed.delete(key);
    render();
  });
  $('guide-previous').addEventListener('click', () => { if (stepIndex > 0) navigate(topicIndex, stepIndex - 1); });
  $('guide-next').addEventListener('click', () => {
    if (stepIndex < topics[topicIndex].steps.length - 1) navigate(topicIndex, stepIndex + 1);
    else if (topicIndex < topics.length - 1) navigate(topicIndex + 1, 0);
  });
  document.querySelectorAll('[name="edition"]').forEach(radio => radio.addEventListener('change', () => { edition = radio.value; render(); }));
  $('guide-reset').addEventListener('click', () => { completed.clear(); edition = 'installer'; navigate(0, 0); });
  document.addEventListener('strigoi:language', event => { language = event.detail.language; render(); });
  const updateRoute = () => { const next = route(); if (next) navigate(...next, false, false); };
  window.addEventListener('hashchange', updateRoute);
  window.addEventListener('popstate', updateRoute);
  const dialog = $('guide-dialog');
  $('guide-zoom').addEventListener('click', () => dialog.showModal());
  $('guide-dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  render();
})();
