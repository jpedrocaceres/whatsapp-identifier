/**
 * WhatsApp Identifier - Content Script (v7)
 *
 * Adiciona prefixo *Nome:* antes de cada mensagem enviada no WhatsApp Web.
 * Usa paste event para contornar o React que restaura o DOM ao editar diretamente.
 */

(function () {
  'use strict';

  let config = { name: '', active: false };
  let isProcessing = false;

  // ─── Privacy Blur ──────────────────────────────────────────────────────────
  let privacyConfig = {
    enabled: false,
    blurIntensity: 8,
  };

  function buildBlurCSS(blur) {
    return `
/* WhatsApp Identifier - Privacy Blur */

/* === LISTA DE CONVERSAS (sidebar) === */
._ak8k span[title] {
    filter: blur(${blur}px) !important;
    transition: filter 0.2s ease !important;
}
/* Hover na conversa inteira revela o preview */
._ak8l:hover ._ak8k span[title] {
    filter: blur(0px) !important;
}

/* === MENSAGENS NO CHAT === */
.message-in .copyable-text,
.message-out .copyable-text {
    filter: blur(${blur}px) !important;
    transition: filter 0.2s ease !important;
}
/* Hover no balão da mensagem revela o texto */
.message-in:hover .copyable-text,
.message-out:hover .copyable-text {
    filter: blur(0px) !important;
}

/* === MÍDIA (imagens, vídeos) === */
.message-in img, .message-out img,
.message-in video, .message-out video {
    filter: blur(${blur}px) !important;
    transition: filter 0.2s ease !important;
}
.message-in:hover img, .message-out:hover img,
.message-in:hover video, .message-out:hover video {
    filter: blur(0px) !important;
}`;
  }

  function injectBlurCSS() {
    let style = document.getElementById('wa-privacy-blur');
    if (style) style.remove();
    style = document.createElement('style');
    style.id = 'wa-privacy-blur';
    style.textContent = buildBlurCSS(privacyConfig.blurIntensity);
    document.head.appendChild(style);
  }

  function removeBlurCSS() {
    const style = document.getElementById('wa-privacy-blur');
    if (style) style.remove();
  }

  function updateBlurState() {
    if (privacyConfig.enabled) {
      injectBlurCSS();
    } else {
      removeBlurCSS();
    }
  }

  function loadPrivacyConfig() {
    chrome.storage.sync.get([
      'waPrivacyEnabled', 'waBlurIntensity'
    ], (result) => {
      privacyConfig.enabled       = result.waPrivacyEnabled || false;
      privacyConfig.blurIntensity = result.waBlurIntensity  || 8;
      updateBlurState();
    });
  }

  // ─── Helpers de prefixo ───────────────────────────────────────────────────
  function buildPrefix() {
    return '*' + config.name + ':* ';
  }

  function hasPrefix(text) {
    return text.startsWith(buildPrefix());
  }

  // ─── Config ───────────────────────────────────────────────────────────────
  function loadConfig() {
    chrome.storage.sync.get(['waIdentifierName', 'waIdentifierActive'], (result) => {
      config.name   = result.waIdentifierName   || '';
      config.active = result.waIdentifierActive !== undefined ? result.waIdentifierActive : false;
    });
  }

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'CONFIG_UPDATED') {
      config.name   = msg.name;
      config.active = msg.active;
    }
    if (msg.type === 'PRIVACY_UPDATED') {
      privacyConfig.enabled       = msg.enabled;
      privacyConfig.blurIntensity = msg.blurIntensity;
      updateBlurState();
    }
  });

  chrome.storage.onChanged.addListener((changes) => {
    if (changes.waIdentifierName)   config.name   = changes.waIdentifierName.newValue;
    if (changes.waIdentifierActive) config.active = changes.waIdentifierActive.newValue;
    if (changes.waPrivacyEnabled !== undefined)  { privacyConfig.enabled       = changes.waPrivacyEnabled.newValue;  updateBlurState(); }
    if (changes.waBlurIntensity !== undefined)   { privacyConfig.blurIntensity = changes.waBlurIntensity.newValue;   updateBlurState(); }
  });

  // ─── DOM helpers ──────────────────────────────────────────────────────────
  function getInput() {
    // Seletores ordenados do mais específico ao mais genérico
    return (
      document.querySelector('div[contenteditable="true"][data-tab="10"]') ||
      document.querySelector('div[contenteditable="true"][data-tab="1"]')  ||
      document.querySelector('footer div[contenteditable="true"]')         ||
      document.querySelector('div[contenteditable="true"][role="textbox"]')
    );
  }

  function getFullText(inputEl) {
    const paragraphs = inputEl.querySelectorAll('p');
    if (paragraphs.length > 0) {
      return Array.from(paragraphs)
        .map(p => p.textContent || '')
        .join('\n')
        .trim();
    }
    return (inputEl.innerText || inputEl.textContent || '').trim();
  }

  function selectAll(inputEl) {
    inputEl.focus();
    const sel   = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(inputEl);
    sel.removeAllRanges();
    sel.addRange(range);
  }

  function pasteText(text, inputEl) {
    const dt = new DataTransfer();
    dt.setData('text/plain', text);
    inputEl.dispatchEvent(new ClipboardEvent('paste', {
      clipboardData: dt,
      bubbles:       true,
      cancelable:    true,
    }));
  }

  function clickSend() {
    const selectors = [
      'span[data-icon="send"]',
      '[data-testid="send"]',
      'button[aria-label="Enviar"]',
      'button[aria-label="Send"]',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        (el.closest('button') || el).click();
        return true;
      }
    }
    return false;
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ─── Lógica principal ─────────────────────────────────────────────────────
  // Fluxo: selectAll → delete (limpa campo) → paste (insere prefixo+texto)
  // IMPORTANTE: não chamar focus() entre delete e paste — isso desfaz a seleção
  // e faz o paste colar no final em vez de substituir, duplicando a mensagem.
  async function processMessage(inputEl) {
    try {
      const originalText = getFullText(inputEl);
      if (!originalText) return;

      const prefix  = buildPrefix();
      const newText = prefix + '\n' + originalText;

      // Step 1: Selecionar tudo e deletar
      selectAll(inputEl);
      await sleep(15);
      document.execCommand('delete', false, null);
      await sleep(30);

      // Step 2: Colar texto novo (sem refazer focus — field já está focado)
      pasteText(newText, inputEl);
      await sleep(60);

      // Step 3: Verificar e enviar
      const afterText = getFullText(inputEl);
      if (afterText.includes(prefix)) {
        clickSend();
        console.log('[WA Identifier] ✓ Enviado com prefixo');
        return;
      }

      // Retry com delays maiores
      console.log('[WA Identifier] Retry...');
      selectAll(inputEl);
      await sleep(20);
      document.execCommand('delete', false, null);
      await sleep(50);
      pasteText(newText, inputEl);
      await sleep(100);

      const retryText = getFullText(inputEl);
      if (retryText.includes(prefix)) {
        clickSend();
        console.log('[WA Identifier] ✓ Enviado (retry)');
      } else {
        // Falha: restaura texto original sem enviar
        console.warn('[WA Identifier] Falha ao inserir prefixo. Restaurando texto original.');
        selectAll(inputEl);
        await sleep(20);
        document.execCommand('delete', false, null);
        await sleep(30);
        pasteText(originalText, inputEl);
      }
    } catch (err) {
      console.error('[WA Identifier] Erro:', err);
    } finally {
      setTimeout(() => { isProcessing = false; }, 300);
    }
  }

  // ─── Verificação pré-envio ────────────────────────────────────────────────
  function shouldIntercept(inputEl) {
    if (!config.active || !config.name) return false;
    const text = getFullText(inputEl);
    return text && !hasPrefix(text);
  }

  // ─── Event Listeners ──────────────────────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if (isProcessing) return;
    if (e.key !== 'Enter' || e.shiftKey) return;

    const inputEl = getInput();
    if (!inputEl) return;
    if (inputEl !== document.activeElement && !inputEl.contains(document.activeElement)) return;

    if (!shouldIntercept(inputEl)) return;

    e.preventDefault();
    e.stopImmediatePropagation();

    isProcessing = true;
    processMessage(inputEl);
  }, true);

  document.addEventListener('click', (e) => {
    if (isProcessing) return;

    const sendTarget = e.target.closest(
      'span[data-icon="send"], [data-testid="send"], button[aria-label="Enviar"], button[aria-label="Send"]'
    );
    if (!sendTarget) return;

    const inputEl = getInput();
    if (!inputEl) return;

    if (!shouldIntercept(inputEl)) return;

    e.preventDefault();
    e.stopImmediatePropagation();

    isProcessing = true;
    processMessage(inputEl);
  }, true);

  // ─── Init ─────────────────────────────────────────────────────────────────
  loadConfig();
  loadPrivacyConfig();
  console.log('[WA Identifier v8] Carregada!');

})();
