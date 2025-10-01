document.addEventListener('DOMContentLoaded', () => {
  const inputTextArea = document.getElementById('inputText');
  const polishBtn = document.getElementById('polishBtn');
  const resultDiv = document.getElementById('result');

  polishBtn.addEventListener('click', async () => {
    const inputText = inputTextArea.value.trim();
    if (!inputText) {
      resultDiv.innerHTML = `<p style="color:red;">⚠️ 텍스트를 입력해 주세요.</p>`;
      return;
    }

    polishBtn.disabled = true;
    polishBtn.innerText = "⏳ 다듬는 중...";

    try {
      const response = await fetch('https://texthelper.onrender.com/polish-text', { // ✅ 포트 8502 추가 완료
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: inputText }),
      });

      const data = await response.json();

      if (data.polished_text) {
        resultDiv.innerHTML = `
          <h3>📝 다듬어진 문장</h3>
          <textarea rows="10" cols="50" readonly>${data.polished_text}</textarea>
          <p style="font-size: 12px; color: #666;">※ 텍스트를 드래그하여 복사할 수 있습니다.</p>
        `;
      } else {
        resultDiv.innerHTML = `<p style="color:red;">❌ 문장 다듬기 실패: ${data.error || "알 수 없는 오류"}</p>`;
      }
    } catch (error) {
      resultDiv.innerHTML = `<p style="color:red;">❌ 서버 통신 오류 발생</p>`;
      console.error("서버 통신 오류", error);
    } finally {
      polishBtn.disabled = false;
      polishBtn.innerText = "다듬기";
    }
  });
});
