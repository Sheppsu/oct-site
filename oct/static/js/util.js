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

export function activateBackground(zIndex = null) {
    const popupBackground = document.getElementById("popup-background");
    if (zIndex !== null) {
        popupBackground.style.zIndex = zIndex;
    }
    popupBackground.removeAttribute("hidden")
    popupBackground.style.opacity = 0.5;
}

export function disableBackground() {
    const popupBackground = document.getElementById("popup-background");
    popupBackground.style.opacity = 0;
    popupBackground.hidden = true;
    popupBackground.style.zIndex = 10;
}

export function initiatePopup(title, buttons) {
    disableScroll();
    activateBackground();
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
    disableBackground();
    const popup = document.getElementById("popup");
    popup.hidden = true;
    const buttons = document.getElementsByClassName("popup-button");
    while (buttons.length > 0) {
        buttons[0].remove();
    }
    enableScroll();
}

export function initCopyableElements() {
    document.querySelectorAll("[copyable]").forEach((elm) => {
        elm.style.cursor = "pointer";
        elm.addEventListener("click", (evt) => {
            var text = elm.innerHTML;
            if (text.endsWith("✔")) {
                text = text.substring(0, text.length-2);
            } else {
                elm.innerHTML += " ✔";
                setTimeout(() => {
                    if (elm.innerHTML.endsWith("✔")) {
                        elm.innerHTML = elm.innerHTML.substring(0, elm.innerHTML.length-2);
                    }
                }, 5000);
            }
            navigator.clipboard.writeText(text);
        });
    });
}

export function initDropdowns() {
    document.querySelectorAll(".dropdown").forEach((elm) => {
        const container = elm.querySelector(".dropdown-container");
        elm.addEventListener("click", (evt) => {
            if (container.hasAttribute("hidden")) {
                return container.removeAttribute("hidden");
            }
            container.setAttribute("hidden", null);
        });
    });
}

export function createDropdownItem(dropdown, text) {
    const dropdownLabel = dropdown.querySelector(".dropdown-label");
    const dropdownContainer = dropdown.querySelector(".dropdown-container");

    const dropdownItem = document.createElement("div");
    dropdownItem.classList.add("dropdown-item");
    const label = document.createElement("p");
    label.classList.add("dropdown-item-label");
    label.innerHTML = text;

    dropdownItem.appendChild(label);
    dropdownContainer.appendChild(dropdownItem);
    dropdownItem.addEventListener("click", (evt) => {
        dropdownLabel.innerHTML = label.innerHTML;
    });
    
    return dropdownItem;
}

export function clearChildren(elm) {
    while (elm.children.length > 0) {
        elm.children.item(0).remove();
    }
}
