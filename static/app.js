(() => {
  'use strict';
  const TOKEN_KEY = 'univers_guest_token';
  const form = document.getElementById('chat-form');
  const input = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  const messages = document.getElementById('messages');
  const suggestions = document.getElementById('suggestions');
  const connectionLabel = document.getElementById('connection-label');
  const connectionStatus = document.getElementById('connection-status');

  let token = null;
  let sending = false;
  let sessionReady = false;

  function randomHex(size) {
    const bytes = new Uint8Array(size);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function setConnection(state, label) {
    connectionLabel.textContent = label;
    connectionStatus.classList.toggle('connecting', state === 'connecting');
    connectionStatus.classList.toggle('offline', state === 'offline');
  }

  async function request(path, options = {}) {
    const response = await fetch(path, options);
    let data = {};
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) {
      const error = new Error(data.detail || 'Ошибка запроса');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function createGuestSession() {
    setConnection('connecting', 'Готовим гостевой вход…');
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const username = 'guest_' + randomHex(8);
      const password = randomHex(24);
      try {
        await request('/auth/register', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({username, password, role: 'student'})
        });
      } catch (error) {
        if (error.status === 400 && attempt < 3) continue;
        throw error;
      }
      const result = await request('/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password})
      });
      token = result.access_token;
      localStorage.setItem(TOKEN_KEY, token);
      sessionReady = true;
      return token;
    }
    throw new Error('Не удалось создать гостевой вход.');
  }

  async function ensureSession(forceNew = false) {
    if (forceNew) localStorage.removeItem(TOKEN_KEY);
    if (!forceNew) {
      const saved = localStorage.getItem(TOKEN_KEY);
      if (saved) {
        try {
          await request('/auth/me', {headers: {Authorization: 'Bearer ' + saved}});
          token = saved;
          sessionReady = true;
          return token;
        } catch (_) {
          localStorage.removeItem(TOKEN_KEY);
        }
      }
    }
    return createGuestSession();
  }

  function scrollDown() { messages.scrollTop = messages.scrollHeight; }

  function addMessage(role, text, isError = false) {
    const row = document.createElement('article');
    row.className = 'message ' + role + (isError ? ' error' : '');
    const avatar = document.createElement('span');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'Я' : 'U';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = (role === 'user' ? 'ТЫ' : 'ПОМОЩНИК') + ' · ' +
      new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    body.append(meta, bubble);
    row.append(avatar, body);
    messages.append(row);
    scrollDown();
  }

  function showTyping() {
    const row = document.createElement('article');
    row.className = 'message assistant';
    row.id = 'typing-indicator';
    const avatar = document.createElement('span');
    avatar.className = 'message-avatar';
    avatar.textContent = 'U';
    const body = document.createElement('div');
    body.className = 'message-body';
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = 'ПОМОЩНИК · ПЕЧАТАЕТ';
    const bubble = document.createElement('div');
    bubble.className = 'bubble typing';
    bubble.setAttribute('aria-label', 'Помощник готовит ответ');
    for (let i = 0; i < 3; i += 1) bubble.append(document.createElement('i'));
    body.append(meta, bubble);
    row.append(avatar, body);
    messages.append(row);
    scrollDown();
  }

  function hideTyping() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
  }

  function updateComposer() {
    sendButton.disabled = sending || !input.value.trim();
  }

  async function sendMessage(value) {
    const message = (value !== undefined ? value : input.value).trim();
    if (!message || sending) return;
    sending = true;
    input.value = '';
    input.style.height = 'auto';
    updateComposer();
    addMessage('user', message);
    suggestions.hidden = true;
    showTyping();

    try {
      if (!sessionReady || !token) await ensureSession();
      let result;
      try {
        result = await request('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token},
          body: JSON.stringify({message})
        });
      } catch (error) {
        if (error.status !== 401) throw error;
        await ensureSession(true);
        result = await request('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token},
          body: JSON.stringify({message})
        });
      }
      hideTyping();
      addMessage('assistant', result.response || 'Не получилось подготовить ответ. Попробуй переформулировать вопрос.');
      setConnection('online', 'Готов помочь');
    } catch (error) {
      hideTyping();
      const messageText = error.status === 503
        ? 'На сервере не настроен ключ OpenRouter. Администратору нужно добавить LLM_KEY в Render → Environment Variables.'
        : error.status === 502
          ? 'Сервис ИИ временно недоступен. Попробуй ещё раз позже.'
          : error.status === 404
            ? 'Сервер не нашёл нужный адрес API. Проверь версию приложения.'
            : 'Не удаётся связаться с помощником. Проверь соединение и попробуй ещё раз.';
      addMessage('assistant', messageText, true);
      setConnection('offline', 'Нет соединения');
    } finally {
      sending = false;
      updateComposer();
      input.focus();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    sendMessage();
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 105) + 'px';
    updateComposer();
  });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });
  suggestions.addEventListener('click', event => {
    const button = event.target.closest('[data-prompt]');
    if (button) sendMessage(button.dataset.prompt);
  });

  updateComposer();
  setConnection('connecting', 'Подключаемся…');
  ensureSession()
    .then(() => setConnection('online', 'Готов помочь'))
    .catch(() => {
      setConnection('offline', 'Нет соединения');
      addMessage('assistant', 'Не получилось подключиться к серверу. Обнови страницу позже.', true);
    });
})();