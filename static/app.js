const messagesEl = document.getElementById("messages");
const quickEl = document.getElementById("quickReplies");
const form = document.getElementById("form");
const input = document.getElementById("input");

function getSessionId() {
  let id = localStorage.getItem("glina_session_id");
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    localStorage.setItem("glina_session_id", id);
  }
  return id;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function scrollDown() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = "msg msg--" + role;
  el.textContent = text;
  messagesEl.appendChild(el);
  scrollDown();
}

function addDraft(draft) {
  const el = document.createElement("div");
  el.className = "draft";

  const rows = [
    ["Услуга", draft.service],
    ["Задача", draft.problem_text],
    ["Контакт", draft.contact],
    ["Что известно", draft.summary],
    ["Чего не хватает", draft.missing],
  ]
    .map(
      ([label, value]) =>
        '<div class="draft__row"><span class="draft__label">' +
        escapeHtml(label) +
        "</span><span>" +
        escapeHtml(value || "—") +
        "</span></div>"
    )
    .join("");

  el.innerHTML =
    '<div class="draft__title">Черновик заявки</div>' +
    '<div class="draft__body">' +
    rows +
    "</div>" +
    '<div class="draft__actions">' +
    '<button class="draft__action draft__action--primary" data-act="confirm">Отправить заявку</button>' +
    '<button class="draft__action" data-act="edit">Изменить</button>' +
    '<button class="draft__action" data-act="cancel">Отмена</button>' +
    "</div>";

  el.querySelector('[data-act="confirm"]').addEventListener("click", () => sendCommand("__confirm_lead__"));
  el.querySelector('[data-act="edit"]').addEventListener("click", () => sendCommand("__edit_lead__"));
  el.querySelector('[data-act="cancel"]').addEventListener("click", () => sendCommand("__cancel_lead__"));

  messagesEl.appendChild(el);
  scrollDown();
  el.scrollIntoView({ block: "end", behavior: "auto" });
}

function setQuickReplies(items) {
  quickEl.innerHTML = "";
  items.forEach((label) => {
    const button = document.createElement("button");
    button.className = "quick";
    button.textContent = label;
    button.addEventListener("click", () => send(label));
    quickEl.appendChild(button);
  });
}

async function send(text, silent = false) {
  if (text !== "" && !silent) addMessage("user", text);
  setQuickReplies([]);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: getSessionId(), text }),
    });
    const data = await res.json();

    if (data.reply) addMessage("bot", data.reply);
    if (data.draft) addDraft(data.draft);
    if (data.quick_replies && data.quick_replies.length) setQuickReplies(data.quick_replies);
  } catch (err) {
    addMessage("bot", "Не удалось связаться с сервером. Проверьте, что приложение запущено.");
  }
}

function sendCommand(command) {
  send(command, true);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.value = "";
  send(value);
});

send("");
