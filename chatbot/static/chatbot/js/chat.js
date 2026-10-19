(() => {
  const messagesEl    = document.getElementById('messages');
  const form          = document.getElementById('chatForm');
  const input         = document.getElementById('input');
  const sendBtn       = document.getElementById('sendBtn');
  const resetBtn      = document.getElementById('resetBtn');
  const suggestionsEl = document.getElementById('suggestions');
  const csrf          = window.CSRF_TOKEN;

  let suggestTimer     = null;
  let activeIndex      = -1;
  let currentSuggestions = [];

  // ── Helpers ─────────────────────────────────────────────
  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function el(html) {
    const d = document.createElement('div');
    d.innerHTML = html.trim();
    return d.firstElementChild;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;',
      '"': '&quot;', "'": '&#39;'
    })[c]);
  }

  function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return escapeHtml(text);
    return (
      escapeHtml(text.slice(0, idx)) +
      '<span class="match">' + escapeHtml(text.slice(idx, idx + query.length)) + '</span>' +
      escapeHtml(text.slice(idx + query.length))
    );
  }

  // ── Messages ────────────────────────────────────────────
  function addUserMessage(text) {
    const node = el(`<div class="msg user"><div class="bubble"></div></div>`);
    node.querySelector('.bubble').textContent = text;
    messagesEl.appendChild(node);
    scrollBottom();
  }

  function addTyping() {
    const node = el(`
      <div class="msg bot">
        <div class="bubble">
          <div class="typing"><span></span><span></span><span></span></div>
        </div>
      </div>
    `);
    messagesEl.appendChild(node);
    scrollBottom();
    return node;
  }

  function addBotMessage(data) {
    const wrapper = document.createElement('div');
    wrapper.className = 'msg bot';
    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (data.category) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = data.category;
      bubble.appendChild(badge);
      bubble.appendChild(document.createElement('br'));
    }

    const text = document.createElement('div');
    text.textContent = data.answer;
    bubble.appendChild(text);

    if (data.confidence && data.confidence > 0) {
      const meta = document.createElement('div');
      meta.style.cssText = 'font-size:11px;color:#64748b;margin-top:6px;';
      meta.textContent = `Match confidence: ${Math.round(data.confidence * 100)}%`;
      bubble.appendChild(meta);
    }

    if (data.faq_id) {
      const fb = document.createElement('div');
      fb.className = 'feedback';
      fb.innerHTML = `<span>Was this helpful?</span>
        <button data-v="1">👍 Yes</button>
        <button data-v="0">👎 No</button>`;
      fb.addEventListener('click', e => {
        const btn = e.target.closest('button');
        if (!btn) return;
        fetch('/chat/api/feedback/', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
          body: JSON.stringify({faq_id: data.faq_id, helpful: btn.dataset.v === '1'})
        }).then(() => {
          fb.querySelectorAll('button').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          fb.querySelector('span').textContent = 'Thanks for the feedback!';
        });
      });
      bubble.appendChild(fb);
    }

    wrapper.appendChild(bubble);
    messagesEl.appendChild(wrapper);

    if (data.suggestions?.length) {
      const chips = document.createElement('div');
      chips.className = 'chips';
      data.suggestions.forEach(s => {
        if (!s.question) return;
        const b = document.createElement('button');
        b.className = 'chip';
        b.textContent = s.question;
        b.addEventListener('click', () => {
          if (s.id) {
            fetch(`/chat/api/faq/${s.id}/`)
              .then(r => r.json())
              .then(f => {
                addUserMessage(s.question);
                addBotMessage({
                  answer: f.answer, faq_id: f.id,
                  category: f.category, confidence: 1.0, suggestions: []
                });
              });
          } else {
            sendMessage(s.question);
          }
        });
        chips.appendChild(b);
      });
      messagesEl.appendChild(chips);
    }

    scrollBottom();
  }

  // ── Autocomplete ────────────────────────────────────────
  function hideSuggestions() {
    suggestionsEl.hidden = true;
    suggestionsEl.innerHTML = '';
    activeIndex = -1;
    currentSuggestions = [];
  }

  function renderSuggestions(items, query) {
    if (!items.length) return hideSuggestions();

    currentSuggestions = items;
    activeIndex = -1;

    suggestionsEl.innerHTML = items.map((s, i) => `
      <div class="suggestion-item" data-index="${i}" data-id="${s.id}">
        <span class="suggestion-icon">🔍</span>
        <span class="suggestion-text">${highlightMatch(s.question, query)}</span>
        ${s.category ? `<span class="suggestion-cat">${escapeHtml(s.category)}</span>` : ''}
      </div>
    `).join('');

    suggestionsEl.hidden = false;
  }

  function fetchSuggestions(query) {
    fetch(`/chat/api/suggest/?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
      .then(data => renderSuggestions(data.suggestions || [], query))
      .catch(() => hideSuggestions());
  }

  function setActiveSuggestion(idx) {
    const items = suggestionsEl.querySelectorAll('.suggestion-item');
    items.forEach(it => it.classList.remove('active'));
    if (idx >= 0 && idx < items.length) {
      items[idx].classList.add('active');
      items[idx].scrollIntoView({block: 'nearest'});
      activeIndex = idx;
    } else {
      activeIndex = -1;
    }
  }

  function pickSuggestion(idx) {
    const s = currentSuggestions[idx];
    if (!s) return;
    hideSuggestions();
    input.value = '';
    addUserMessage(s.question);
    loadAndShowFaq(s.id);
  }

  function loadAndShowFaq(faqId) {
    const typing = addTyping();
    fetch(`/chat/api/faq/${faqId}/`)
      .then(r => r.json())
      .then(f => {
        typing.remove();
        addBotMessage({
          answer: f.answer, faq_id: f.id,
          category: f.category, confidence: 1.0, suggestions: []
        });
      })
      .catch(() => {
        typing.remove();
        addBotMessage({answer: '⚠️ Could not load FAQ.', suggestions: []});
      });
  }

  // ── Send ────────────────────────────────────────────────
  async function sendMessage(text) {
    if (!text || !text.trim()) return;
    hideSuggestions();
    addUserMessage(text);
    input.value = '';
    sendBtn.disabled = true;

    const typing = addTyping();

    try {
      const res = await fetch('/chat/api/ask/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify({message: text})
      });
      const data = await res.json();
      typing.remove();

      if (data.error) {
        addBotMessage({answer: '⚠️ ' + data.error, suggestions: []});
      } else {
        addBotMessage(data);
      }
    } catch (err) {
      typing.remove();
      addBotMessage({answer: '⚠️ Network error. Please try again.', suggestions: []});
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // ── Input listeners ─────────────────────────────────────
  input.addEventListener('input', () => {
    const q = input.value.trim();
    clearTimeout(suggestTimer);

    if (q.length < 2) return hideSuggestions();

    suggestTimer = setTimeout(() => fetchSuggestions(q), 120);
  });

  input.addEventListener('keydown', e => {
    const open = !suggestionsEl.hidden;

    if (e.key === 'ArrowDown' && open) {
      e.preventDefault();
      setActiveSuggestion(Math.min(activeIndex + 1, currentSuggestions.length - 1));
    } else if (e.key === 'ArrowUp' && open) {
      e.preventDefault();
      setActiveSuggestion(Math.max(activeIndex - 1, -1));
    } else if (e.key === 'Enter' && open && activeIndex >= 0) {
      e.preventDefault();
      pickSuggestion(activeIndex);
    } else if (e.key === 'Escape' && open) {
      hideSuggestions();
    }
  });

  suggestionsEl.addEventListener('click', e => {
    const item = e.target.closest('.suggestion-item');
    if (!item) return;
    pickSuggestion(parseInt(item.dataset.index, 10));
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('.composer-wrap')) hideSuggestions();
  });

  // ── Form + chips ────────────────────────────────────────
  form.addEventListener('submit', e => {
    e.preventDefault();
    sendMessage(input.value);
  });

  document.addEventListener('click', e => {
    const chip = e.target.closest('#initialChips .chip');
    if (chip) {
      const faqId = chip.dataset.faq;
      const question = chip.textContent;
      document.getElementById('initialChips')?.remove();
      addUserMessage(question);
      loadAndShowFaq(faqId);
    }
  });

  resetBtn.addEventListener('click', async () => {
    await fetch('/chat/api/reset/', {
      method: 'POST',
      headers: {'X-CSRFToken': csrf}
    });
    messagesEl.innerHTML = '';
    hideSuggestions();
    addBotMessage({
      answer: "Conversation reset. What would you like to know?",
      suggestions: []
    });
  });

  scrollBottom();
})();