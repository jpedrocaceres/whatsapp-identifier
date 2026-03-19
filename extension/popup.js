document.addEventListener('DOMContentLoaded', () => {
  const usernameInput  = document.getElementById('username');
  const toggleActive   = document.getElementById('toggleActive');
  const saveBtn        = document.getElementById('saveBtn');
  const status         = document.getElementById('status');
  const previewText    = document.getElementById('previewText');
  const charCount      = document.getElementById('charCount');
  const toggleSubtitle = document.getElementById('toggleSubtitle');
  const chatBubbleWrap = document.getElementById('chatBubbleWrap');
  const headerStatus   = document.getElementById('headerStatus');
  const statusDot      = document.getElementById('statusDot');

  // Privacy elements
  const togglePrivacy    = document.getElementById('togglePrivacy');
  const privacySubtitle  = document.getElementById('privacySubtitle');
  const blurIntensity    = document.getElementById('blurIntensity');
  const blurValue        = document.getElementById('blurValue');

  // Carregar configurações salvas
  chrome.storage.sync.get([
    'waIdentifierName', 'waIdentifierActive',
    'waPrivacyEnabled', 'waBlurIntensity'
  ], (result) => {
    if (result.waIdentifierName) {
      usernameInput.value = result.waIdentifierName;
    }
    if (result.waIdentifierActive !== undefined) {
      toggleActive.checked = result.waIdentifierActive;
    }
    // Privacy
    togglePrivacy.checked = result.waPrivacyEnabled || false;
    blurIntensity.value   = result.waBlurIntensity  || 8;
    blurValue.textContent = blurIntensity.value + 'px';

    updatePreview();
    updateCharCount();
    updatePrivacyUI();
    updateHeaderBadge();
  });

  usernameInput.addEventListener('input', () => {
    updatePreview();
    updateCharCount();
  });

  toggleActive.addEventListener('change', () => {
    updatePreview();
    updateHeaderBadge();
  });

  // Privacy listeners
  togglePrivacy.addEventListener('change', updatePrivacyUI);
  blurIntensity.addEventListener('input', () => {
    blurValue.textContent = blurIntensity.value + 'px';
  });

  function updateHeaderBadge() {
    const on = toggleActive.checked;
    headerStatus.textContent = on ? 'Ativo' : 'Inativo';
    statusDot.style.background = on ? '#4ADE80' : '#8696A0';
  }

  function updatePrivacyUI() {
    const on = togglePrivacy.checked;
    privacySubtitle.textContent = on ? 'Ativo' : 'Inativo';
    privacySubtitle.className   = 'toggle-subtitle' + (on ? '' : ' inactive');
  }

  function updateCharCount() {
    const len = usernameInput.value.length;
    charCount.textContent = `${len}/30`;
    charCount.classList.toggle('warn', len > 24);
  }

  function sanitize(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function updatePreview() {
    const name   = usernameInput.value.trim() || 'Nome';
    const active = toggleActive.checked;

    if (active) {
      previewText.innerHTML = `<strong>${sanitize(name)}:</strong> <br>Sua mensagem aqui...`;
      previewText.style.opacity = '1';
      toggleSubtitle.textContent = 'Ativo';
      toggleSubtitle.className = 'toggle-subtitle';
      chatBubbleWrap.classList.remove('inactive');
    } else {
      previewText.textContent = 'Sua mensagem aqui...';
      previewText.style.opacity = '0.6';
      toggleSubtitle.textContent = 'Inativo';
      toggleSubtitle.className = 'toggle-subtitle inactive';
      chatBubbleWrap.classList.add('inactive');
    }
  }

  // Salvar configurações
  saveBtn.addEventListener('click', () => {
    const name = usernameInput.value.trim();

    if (!name) {
      showStatus('Digite um nome!', true);
      usernameInput.focus();
      return;
    }

    const privacyEnabled = togglePrivacy.checked;
    const blur           = parseInt(blurIntensity.value);

    chrome.storage.sync.set({
      waIdentifierName:   name,
      waIdentifierActive: toggleActive.checked,
      waPrivacyEnabled:   privacyEnabled,
      waBlurIntensity:    blur,
    }, () => {
      showStatus('Configuração salva com sucesso');

      chrome.tabs.query({ url: 'https://web.whatsapp.com/*' }, (tabs) => {
        tabs.forEach((tab) => {
          chrome.tabs.sendMessage(tab.id, {
            type:   'CONFIG_UPDATED',
            name:   name,
            active: toggleActive.checked,
          }).catch(() => {});
          chrome.tabs.sendMessage(tab.id, {
            type:          'PRIVACY_UPDATED',
            enabled:       privacyEnabled,
            blurIntensity: blur,
          }).catch(() => {});
        });
      });
    });
  });

  // Enter para salvar
  usernameInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') saveBtn.click();
  });

  function showStatus(message, isError = false) {
    status.textContent = message;
    status.className   = `status ${isError ? 'error' : ''}`;
    setTimeout(() => {
      status.className = 'status hidden';
    }, 2500);
  }
});
