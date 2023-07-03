import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";
const difficultyColourSpectrum = d3.scaleLinear()
  .domain([0.1, 1.25, 2, 2.5, 3.3, 4.2, 4.9, 5.8, 6.7, 7.7, 9])
  .clamp(true)
  .range(['#4290FB', '#4FC0FF', '#4FFFD5', '#7CFF4F', '#F6F05C', '#FF8068', '#FF4E6F', '#C645B8', '#6563DE', '#18158E', '#000000'])
  .interpolate(d3.interpolateRgb.gamma(2.2));


export function getDiffColor(starRating) {
	if (starRating < 0.1) return "#AAAAAA";
	if (starRating >= 9) return "#000000";
	return difficultyColourSpectrum(starRating);
}

function disableScroll() {
    const body = document.getElementsByTagName("body")[0];
    body.style.height = "100vh";
    body.style.overflow = "hidden";
}

function enableScroll() {
    const body = document.getElementsByTagName("body")[0];
    body.style.removeProperty("height");
    body.style.removeProperty("overflow");
}

function createPopupButton(buttonInfo) {
    const button = document.createElement("button");
    button.innerHTML = buttonInfo.text;
    button.style.backgroundColor = buttonInfo.color;
    button.style.width = buttonInfo.width+"px";
    button.classList.add("popup-button");
    button.classList.add("button-transition");
    button.addEventListener("mouseenter", (event) => {
        button.style.width = buttonInfo.width+20+"px";
        button.style.height = "75px";
        button.style.fontSize = "35px";
        button.style.boxShadow = "0 0 30px 5px "+buttonInfo.color;
    });
    button.addEventListener("mouseleave", (event) => {
        button.style.width = buttonInfo.width+"px";
        button.style.height = "60px";
        button.style.fontSize = "30px";
        button.style.boxShadow = "none";
    });
    button.onclick = buttonInfo.callback;
    return button;
}

export function initiatePopup(title, buttons) {
    disableScroll();
    const popupBackground = document.getElementById("popup-background");
    popupBackground.removeAttribute("hidden")
    popupBackground.style.opacity = 0.5;
    const popup = document.getElementById("popup");
    popup.removeAttribute("hidden");
    const popupTitle = document.getElementById("popup-title");
    popupTitle.innerHTML = title;
    for (const buttonInfo of buttons) {
        const button = createPopupButton(buttonInfo);
        popup.appendChild(button);
    }
}

export function closePopup() {
    const popupBackground = document.getElementById("popup-background");
    popupBackground.style.opacity = 0;
    popupBackground.hidden = true;
    const popup = document.getElementById("popup");
    popup.hidden = true;
    const buttons = document.getElementsByClassName("popup-button");
    while (buttons.length > 0) {
        buttons[0].remove();
    }
    enableScroll();
}
