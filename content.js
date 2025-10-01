function addPolishButton() {
    const answerTitle = document.querySelector('h2.red');

    if (!answerTitle) {
        console.log("답변 제목(h2.red)을 찾을 수 없습니다.");
        return;
    }

    if (document.getElementById('polishTextBtn')) return;

    const button = document.createElement('button');
    button.innerText = "📝 문장 다듬기";
    button.id = "polishTextBtn";

    button.style.marginLeft = "10px";
    button.style.padding = "8px 16px";
    button.style.backgroundColor = "#4CAF50";
    button.style.color = "white";
    button.style.border = "none";
    button.style.cursor = "pointer";
    button.style.borderRadius = "8px";
    button.style.fontSize = "14px";
    button.style.display = "inline-flex";
    button.style.alignItems = "center";
    button.style.gap = "6px";
    button.style.transition = "background-color 0.3s, transform 0.1s";

    button.addEventListener("mouseover", function () {
        button.style.backgroundColor = "#45A049";
    });
    button.addEventListener("mouseout", function () {
        button.style.backgroundColor = "#4CAF50";
    });
    button.addEventListener("mousedown", function () {
        button.style.transform = "scale(0.96)";
    });
    button.addEventListener("mouseup", function () {
        button.style.transform = "scale(1)";
    });
    button.addEventListener("mouseleave", function () {
        button.style.transform = "scale(1)";
    });

    answerTitle.insertAdjacentElement('afterend', button);

    // ✅ 버튼 클릭 시 background.js로 메시지 전송
    button.addEventListener('click', () => {
        chrome.runtime.sendMessage({ action: "openPolishPopup" });
    });
}

window.addEventListener('load', () => {
    setTimeout(addPolishButton, 1000);
});
