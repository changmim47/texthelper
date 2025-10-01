document.addEventListener('DOMContentLoaded', () => {
  const inputTextArea = document.getElementById('inputText');
  const polishBtn = document.getElementById('polishBtn');
  const resultDiv = document.getElementById('result');

  const BASE_URL = 'https://texthelper.onrender.com';

  async function polish(text) {
    const res = await fetch(`${BASE_URL}/polish-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      cache: 'no-store',
    });
    if (!res.ok) throw new Error('SERVER_ERROR');
    const data = await res.json();
    if (!data.polished_text) throw new Error('EMPTY');
    return data.polished_text;
  }

  polishBtn.addEventListener('click', async () => {
    const inputText = inputTextArea.value.trim();
    if (!inputText) {
      resultDiv.innerHTML = `<p style="color:red;">⚠️ 텍스트를 입력해 주세요.</p>`;
      return;
    }

    polishBtn.disabled = true;
    polishBtn.innerText = '⏳ 다듬는 중...';

    // 미리 출력 영역 구성
    resultDiv.innerHTML = `
      <h3>📝 다듬어진 문장</h3>
      <textarea id="out" rows="10" cols="50" readonly></textarea>
      <p style="font-size:12px;color:#666;">※ 처리 중입니다.</p>
    `;
    const out = document.getElementById('out');

    try {
      const text = await polish(inputText);
      out.value = text;
      out.scrollTop = out.scrollHeight;
      resultDiv.querySelector('p').textContent = '※ 텍스트를 드래그하여 복사할 수 있습니다.';
    } catch (err) {
      console.error(err);
      resultDiv.innerHTML = `<p style="color:red;">❌ 처리에 실패했습니다. 잠시 후 다시 시도해 주세요.</p>`;
    } finally {
      polishBtn.disabled = false;
      polishBtn.innerText = '다듬기';
    }
  });
});
