const messageList = document.getElementById("messageList");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");
const statusText = document.getElementById("statusText");
const sessionIdText = document.getElementById("sessionId");
const systemPromptInput = document.getElementById("systemPrompt");

let history = [];
let isSending = false;
let sessionId = createSessionId();

sessionIdText.textContent = sessionId;
appendMessage("assistant", "您好，我是 AI 助手，请输入您想咨询的问题。");

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSending) {
    return;
  }

  const text = messageInput.value.trim();
  if (!text) {
    return;
  }

  appendMessage("user", text);
  messageInput.value = "";
  autoResize(messageInput);

  await sendMessage(text);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

messageInput.addEventListener("input", () => autoResize(messageInput));

clearBtn.addEventListener("click", () => {
  history = [];
  sessionId = createSessionId();
  sessionIdText.textContent = sessionId;
  messageList.innerHTML = "";
  appendMessage("assistant", "会话已清空，可以开始新的对话。");
  setStatus("空闲", "idle");
});

async function sendMessage(text) {
  isSending = true;
  sendBtn.disabled = true;
  clearBtn.disabled = true;
  setStatus("AI 回复中...", "loading");

  const typingElement = appendMessage("assistant", "", true);

  try {
    const response = await fetch("/api/v1/conversation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        history,
        system_prompt: systemPromptInput.value.trim() || null,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "接口调用失败");
    }

    await typewriter(typingElement, data.answer || "");
    history = Array.isArray(data.messages)
      ? data.messages.filter((message) => message.role !== "system")
      : history;
    setStatus("空闲", "idle");
  } catch (error) {
    typingElement.classList.remove("typing");
    typingElement.querySelector(".message-content").textContent =
      `请求失败：${error.message}`;
    setStatus("请求失败", "error");
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    clearBtn.disabled = false;
    messageInput.focus();
    scrollToBottom();
  }
}

function appendMessage(role, content, typing = false) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;
  if (typing) {
    wrapper.classList.add("typing");
  }

  const roleText = document.createElement("span");
  roleText.className = "message-role";
  roleText.textContent = role === "user" ? "用户" : role === "assistant" ? "AI" : "系统";

  const contentText = document.createElement("div");
  contentText.className = "message-content";
  contentText.textContent = content;

  wrapper.appendChild(roleText);
  wrapper.appendChild(contentText);
  messageList.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

async function typewriter(element, text) {
  const contentNode = element.querySelector(".message-content");
  contentNode.textContent = "";

  for (const char of text) {
    contentNode.textContent += char;
    scrollToBottom();
    await sleep(char === "\n" ? 10 : 22);
  }

  element.classList.remove("typing");
}

function setStatus(text, type) {
  statusText.textContent = text;
  statusText.className = `status ${type}`;
}

function createSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function scrollToBottom() {
  messageList.scrollTop = messageList.scrollHeight;
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${textarea.scrollHeight}px`;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
