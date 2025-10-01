// popup.js (로딩 스피너 포함, /polish-text 단일 호출 버전)

document.addEventListener('DOMContentLoaded', () => {
  const inputTextArea = document.getElementById('inputText');
  const polishBtn = document.getElementById('polishBtn');
  const resultDiv = document.getElementById('result');

  const BASE_URL = 'https://texthelper.onrender.com';

  // 1) 스피너 CSS 주입 (한 번만)
  (function ensureLoaderStyles() {
    if (document.getElementById('loader-style')) return;
    const style = document.createElement('style');
    style.id = 'loader-style';
    style.textContent = `
      .loading { display:flex; align-items:center; gap:10px; color:#666; font-size:12px; padding:6px 0; }
      .loading .spinner { width:16px; height:16px; border:2px solid #ddd; border-top-color:#4CAF50; border-radius:50%; animation:spin .8s linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
      .muted { font-size:12px; color:#666; }
      textarea[readonly] { width: 100%; box-sizing: border-box; }
    `;
    document.head.appendChild(style);
  })();

  // 2) 로딩/출력 UI 유틸
  function showLoading(message = '모델이 문장을 다듬는 중입니다...') {
    resultDiv.innerHTML = `
      <div class="loading">
        <div class="spinner"></div>
        <div>${message}</div>
      </div>
    `;
  }

  function showResult(text) {
    resultDiv.innerHTML = `
      <h3>📝 다듬어진 문장</h3>
      <textarea rows="10" cols="50" readonly>${text}</textarea>
      <p class="muted">※ 텍스트를 드래그하여 복사할 수 있습니다.</p>
    `;
  }

  function showError(message = '❌ 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.') {
    resultDiv.innerHTML = `<p style="color:red;">${message}</p>`;
  }

  // 3) API 호출
  async function polish(text) {
    const res = await fetch(`${BASE_URL}/polish-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.polished_text) throw new Error(data.error || 'EMPTY_RESPONSE');
    return data.polished_text;
  }

  // 4) 클릭 핸들러
  polishBtn.addEventListener('click', async () => {
    const inputText = inputTextArea.value.trim();
    if (!inputText) {
      resultDiv.innerHTML = `<p style="color:red;">⚠️ 텍스트를 입력해 주세요.</p>`;
      return;
    }

    polishBtn.disabled = true;
    polishBtn.innerText = '⏳ 다듬는 중...';

    showLoading(); // ✅ 로딩 스피너 표시

    try {
      const text = await polish(inputText);
      showResult(text);  // ✅ 완료 시 결과 표시
    } catch (err) {
      console.error(err);
      showError();
    } finally {
      polishBtn.disabled = false;
      polishBtn.innerText = '다듬기';
    }
  });
});
