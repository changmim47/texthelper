document.addEventListener('DOMContentLoaded', () => {
  const inputTextArea = document.getElementById('inputText');
  const polishBtn = document.getElementById('polishBtn');
  const resultDiv = document.getElementById('result');

  const BASE_URL = 'https://texthelper.onrender.com';

  async function streamPolish(text) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000); // 30s 타임아웃

    // 출력 영역 먼저 구성
    resultDiv.innerHTML = `
      <h3>📝 다듬어진 문장</h3>
      <textarea id="out" rows="10" cols="50" readonly></textarea>
      <p id="info" style="font-size:12px;color:#666;">※ 생성 중입니다. (스트리밍)</p>
    `;
    const out = document.getElementById('out');
    const info = document.getElementById('info');

    try {
      const res = await fetch(`${BASE_URL}/polish-text-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        signal: controller.signal,
        cache: 'no-store',
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let acc = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        out.value = acc;
        out.scrollTop = out.scrollHeight;
      }

      // ✅ 최종 flush (부분 유니코드 잔여 바이트 처리)
      acc += decoder.decode();
      out.value = acc;

      clearTimeout(timeout);

      // ✅ 스트림에 서버 오류 텍스트가 섞여온 경우 폴백 유도
      if (acc.includes('[SERVER ERROR]') || acc.includes('[ERROR]')) {
        throw new Error(acc);
      }

      // 안내 문구 전환
      if (info) info.textContent = '※ 텍스트를 드래그하여 복사할 수 있습니다.';
      return acc.trim();
    } catch (err) {
      clearTimeout(timeout);
      throw err;
    }
  }

  async function polishOnce(path, text) {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.polished_text) throw new Error(data.error || '알 수 없는 오류');
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

    try {
      // 1) 스트리밍 우선
      const streamed = await streamPolish(inputText);
      if (streamed) return;

      // 만약 streamed가 비어있다면 폴백
      throw new Error('빈 응답');
    } catch (_) {
      // 2) 폴백: Responses 비스트리밍
      try {
        const text = await polishOnce('/polish-text-resp', inputText);
        resultDiv.innerHTML = `
          <h3>📝 다듬어진 문장</h3>
          <textarea rows="10" cols="50" readonly>${text}</textarea>
          <p style="font-size: 12px; color: #666;">※ 텍스트를 드래그하여 복사할 수 있습니다.</p>
        `;
      } catch (e2) {
        // 3) 최종 폴백: 기존 Chat Completions 엔드포인트
        try {
          const text = await polishOnce('/polish-text', inputText);
          resultDiv.innerHTML = `
            <h3>📝 다듬어진 문장</h3>
            <textarea rows="10" cols="50" readonly>${text}</textarea>
            <p style="font-size: 12px; color: #666;">※ 텍스트를 드래그하여 복사할 수 있습니다.</p>
          `;
        } catch (e3) {
          console.error(e3);
          resultDiv.innerHTML = `<p style="color:red;">❌ 서버 통신 오류: ${e3.message || '알 수 없는 오류'}</p>`;
        }
      }
    } finally {
      polishBtn.disabled = false;
      polishBtn.innerText = '다듬기';
    }
  });
});
