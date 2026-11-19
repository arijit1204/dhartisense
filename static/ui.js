/* Shared interface helpers: confirmations (toasts), button feedback, one-card-at-a-time pager, language and units. Loaded before app.js. */

// ---- Confirmations ----

function toast(message, kind = "ok") {
  let box = document.getElementById("toasts");
  if (!box) {
    box = document.createElement("div");
    box.id = "toasts";
    box.setAttribute("aria-live", "polite");
    document.body.appendChild(box);
  }
  const item = document.createElement("div");
  item.className = `toast ${kind}`;
  item.innerHTML = `<span class="toast-mark">${kind === "ok" ? "✓" : kind === "error" ? "!" : "i"}</span><span></span>`;
  item.lastChild.textContent = message;
  box.appendChild(item);
  while (box.children.length > 3) box.firstChild.remove();
  setTimeout(() => { item.classList.add("leaving"); setTimeout(() => item.remove(), 300); }, kind === "error" ? 5200 : 3200);
}

// Shows "Saved ✓" on a button for a moment, so a click visibly did something.
function flashButton(button, text = "Saved ✓", ms = 1800) {
  if (!button) return;
  const label = button.dataset.label || button.innerHTML;
  button.dataset.label = label;
  button.classList.add("done");
  button.innerHTML = text;
  clearTimeout(button._flash);
  button._flash = setTimeout(() => { button.classList.remove("done"); button.innerHTML = label; delete button.dataset.label; if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } }); }, ms);
}

// ---- One card at a time, with left and right arrows ----

function makePager(box, items, noun = "item") {
  let index = 0;
  const draw = () => {
    const item = items[index];
    box.innerHTML = `<div class="pager" tabindex="0" aria-label="${noun} ${index + 1} of ${items.length}">
      <div class="pager-bar"><button type="button" class="pager-btn" data-dir="-1" aria-label="Previous ${noun}" ${index === 0 ? "disabled" : ""}><i data-lucide="chevron-left"></i></button>
        <div class="pager-title"><strong>${item.title}</strong><span>${index + 1} of ${items.length}</span></div>
        <button type="button" class="pager-btn" data-dir="1" aria-label="Next ${noun}" ${index === items.length - 1 ? "disabled" : ""}><i data-lucide="chevron-right"></i></button></div>
      <div class="pager-dots">${items.map((_, i) => `<button type="button" class="pager-dot${i === index ? " on" : ""}" data-i="${i}" aria-label="Show ${noun} ${i + 1}"></button>`).join("")}</div>
      <div class="pager-body">${item.html}</div></div>`;
    box.querySelectorAll(".pager-btn").forEach((b) => b.addEventListener("click", () => go(index + Number(b.dataset.dir))));
    box.querySelectorAll(".pager-dot").forEach((b) => b.addEventListener("click", () => go(Number(b.dataset.i))));
    if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  };
  const go = (to) => {
    if (to < 0 || to >= items.length || to === index) return;
    index = to;
    draw();
    box.querySelector(".pager")?.focus({ preventScroll: true });
  };
  // swipe left or right on the card to move between crops (touch screens)
  let touchStart = null;
  box.addEventListener("touchstart", (event) => { touchStart = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null; }, { passive: true });
  box.addEventListener("touchend", (event) => {
    if (!touchStart) return;
    const dx = event.changedTouches[0].clientX - touchStart.x;
    const dy = event.changedTouches[0].clientY - touchStart.y;
    touchStart = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) go(index + (dx < 0 ? 1 : -1));
  }, { passive: true });
  box._pagerKey = (event) => { // arrows work while the cards are focused or the pointer is over them
    if (!box.isConnected || !box.offsetParent || /INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName)) return;
    const shown = [...document.querySelectorAll(".pager")].filter((el) => el.offsetParent);
    if (!(box.matches(":hover") || box.contains(document.activeElement) || shown.length === 1)) return; // with two sets of cards on a page, the arrows follow the pointer
    if (event.key === "ArrowRight") { event.preventDefault(); go(index + 1); }
    if (event.key === "ArrowLeft") { event.preventDefault(); go(index - 1); }
  };
  document.addEventListener("keydown", (event) => box._pagerKey?.(event));
  draw();
}

// ---- Language and units (kept on this device) ----

const LANG_KEY = "dhartisense-language";
const UNITS_KEY = "dhartisense-units";

function storedSetting(key, fallback) {
  try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
}
const currentLanguage = () => storedSetting(LANG_KEY, "English");
const useImperial = () => storedSetting(UNITS_KEY, "metric") === "imperial";
const tempText = (celsius) => (celsius == null ? "—" : useImperial() ? `${Math.round(celsius * 1.8 + 32)}°F` : `${Math.round(celsius)}°C`);

// Interface words translated for the main navigation, page titles and key buttons. Anything not listed stays in English.
// shortcut: these translations were written without a native-speaker review; have a Hindi/Marathi/Bengali/Tamil speaker check them before launch.
const I18N = {
  Hindi: { "Crop health": "फसल स्वास्थ्य", "Overview": "अवलोकन", "My fields": "मेरे खेत", "Crop plan": "फसल योजना", "Plant health": "पौधों का स्वास्थ्य", "Water & nutrients": "पानी और पोषक तत्व", "Ask Dhartisense": "Dhartisense से पूछें", "Reports": "रिपोर्ट", "Settings": "सेटिंग्स", "Add a field": "खेत जोड़ें", "Your fields": "आपके खेत", "Weather": "मौसम", "Field area": "खेत का क्षेत्रफल", "Next irrigation": "अगली सिंचाई", "Save field profile": "खेत की जानकारी सहेजें", "Find best crops": "सबसे अच्छी फसलें खोजें", "Make irrigation schedule": "सिंचाई कार्यक्रम बनाएँ", "Make fertiliser plan": "खाद योजना बनाएँ", "Print or save as PDF": "प्रिंट करें या PDF सहेजें", "Preferred language": "पसंदीदा भाषा", "Units": "इकाइयाँ", "Account": "खाता", "Sign out": "साइन आउट",
    "Make today’s field decision with confidence.": "आज खेत का फैसला भरोसे के साथ लें।", "Build your field profile.": "अपने खेत की जानकारी बनाएँ।", "Choose with the field in mind.": "खेत को ध्यान में रखकर चुनें।", "Look closer, early.": "करीब से और जल्दी देखें।", "Plan from what you can observe.": "जो आप देख सकते हैं उसके आधार पर योजना बनाएँ।", "Keep your field story together.": "अपने खेत की कहानी एक जगह रखें।" },
  Marathi: { "Crop health": "पीक आरोग्य", "Overview": "आढावा", "My fields": "माझी शेते", "Crop plan": "पीक योजना", "Plant health": "वनस्पती आरोग्य", "Water & nutrients": "पाणी आणि पोषक द्रव्ये", "Ask Dhartisense": "Dhartisense ला विचारा", "Reports": "अहवाल", "Settings": "सेटिंग्ज", "Add a field": "शेत जोडा", "Your fields": "तुमची शेते", "Weather": "हवामान", "Field area": "शेताचे क्षेत्रफळ", "Next irrigation": "पुढील पाणी देणे", "Save field profile": "शेताची माहिती जतन करा", "Find best crops": "सर्वोत्तम पिके शोधा", "Make irrigation schedule": "सिंचन वेळापत्रक बनवा", "Make fertiliser plan": "खत योजना बनवा", "Print or save as PDF": "प्रिंट करा किंवा PDF जतन करा", "Preferred language": "आवडती भाषा", "Units": "एकके", "Account": "खाते", "Sign out": "साइन आउट",
    "Make today’s field decision with confidence.": "आजचा शेतीचा निर्णय आत्मविश्वासाने घ्या.", "Build your field profile.": "तुमच्या शेताची माहिती तयार करा.", "Choose with the field in mind.": "शेताचा विचार करून निवडा.", "Look closer, early.": "लवकर आणि जवळून पाहा.", "Plan from what you can observe.": "तुम्ही जे पाहता त्यावरून नियोजन करा.", "Keep your field story together.": "तुमच्या शेताची कहाणी एकत्र ठेवा." },
  Bengali: { "Crop health": "ফসলের স্বাস্থ্য", "Overview": "ওভারভিউ", "My fields": "আমার জমি", "Crop plan": "ফসল পরিকল্পনা", "Plant health": "গাছের স্বাস্থ্য", "Water & nutrients": "জল ও পুষ্টি", "Ask Dhartisense": "Dhartisense-কে জিজ্ঞাসা করুন", "Reports": "রিপোর্ট", "Settings": "সেটিংস", "Add a field": "জমি যোগ করুন", "Your fields": "আপনার জমি", "Weather": "আবহাওয়া", "Field area": "জমির পরিমাণ", "Next irrigation": "পরবর্তী সেচ", "Save field profile": "জমির তথ্য সংরক্ষণ করুন", "Find best crops": "সেরা ফসল খুঁজুন", "Make irrigation schedule": "সেচের সময়সূচি তৈরি করুন", "Make fertiliser plan": "সারের পরিকল্পনা তৈরি করুন", "Print or save as PDF": "প্রিন্ট বা PDF সংরক্ষণ করুন", "Preferred language": "পছন্দের ভাষা", "Units": "একক", "Account": "অ্যাকাউন্ট", "Sign out": "সাইন আউট",
    "Make today’s field decision with confidence.": "আজকের জমির সিদ্ধান্ত আত্মবিশ্বাসের সাথে নিন।", "Build your field profile.": "আপনার জমির তথ্য তৈরি করুন।", "Choose with the field in mind.": "জমির কথা মাথায় রেখে বেছে নিন।", "Look closer, early.": "কাছ থেকে, আগেভাগে দেখুন।", "Plan from what you can observe.": "আপনি যা দেখেন তার ভিত্তিতে পরিকল্পনা করুন।", "Keep your field story together.": "আপনার জমির গল্প একসাথে রাখুন।" },
  Tamil: { "Crop health": "பயிர் ஆரோக்கியம்", "Overview": "கண்ணோட்டம்", "My fields": "என் வயல்கள்", "Crop plan": "பயிர் திட்டம்", "Plant health": "தாவர ஆரோக்கியம்", "Water & nutrients": "நீர் & ஊட்டச்சத்து", "Ask Dhartisense": "Dhartisense-இடம் கேளுங்கள்", "Reports": "அறிக்கைகள்", "Settings": "அமைப்புகள்", "Add a field": "வயலைச் சேர்", "Your fields": "உங்கள் வயல்கள்", "Weather": "வானிலை", "Field area": "வயல் பரப்பு", "Next irrigation": "அடுத்த நீர்ப்பாசனம்", "Save field profile": "வயல் விவரத்தைச் சேமி", "Find best crops": "சிறந்த பயிர்களைக் கண்டுபிடி", "Make irrigation schedule": "நீர்ப்பாசன அட்டவணை உருவாக்கு", "Make fertiliser plan": "உர திட்டம் உருவாக்கு", "Print or save as PDF": "அச்சிடு அல்லது PDF சேமி", "Preferred language": "விருப்ப மொழி", "Units": "அலகுகள்", "Account": "கணக்கு", "Sign out": "வெளியேறு",
    "Make today’s field decision with confidence.": "இன்றைய வயல் முடிவை நம்பிக்கையுடன் எடுங்கள்.", "Build your field profile.": "உங்கள் வயல் விவரத்தை உருவாக்குங்கள்.", "Choose with the field in mind.": "வயலை மனதில் கொண்டு தேர்ந்தெடுங்கள்.", "Look closer, early.": "முன்கூட்டியே, உற்றுப் பாருங்கள்.", "Plan from what you can observe.": "நீங்கள் கவனிப்பதன் அடிப்படையில் திட்டமிடுங்கள்.", "Keep your field story together.": "உங்கள் வயல் கதையை ஒன்றாக வைத்திருங்கள்." },
};

function applyLanguage() {
  const table = I18N[currentLanguage()] || {};
  document.documentElement.lang = { Hindi: "hi", Marathi: "mr", Bengali: "bn", Tamil: "ta" }[currentLanguage()] || "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = table[el.dataset.i18n] || el.dataset.i18n; });
}
