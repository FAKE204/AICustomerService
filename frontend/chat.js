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
  const contentNode = typingElement.querySelector(".message-content");
  const streamRenderer = createMarkdownStreamRenderer(contentNode);
  let answer = "";
  let finalPayload = null;
  let streamError = null;

  try {
    const response = await fetch("/api/v1/conversation", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: text,
        history,
        stream: true,
        system_prompt: systemPromptInput.value.trim() || null,
      }),
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    await consumeEventStream(response, ({ event, data }) => {
      if (!data) {
        return;
      }

      const payload = JSON.parse(data);
      if (event === "delta") {
        answer += payload.content || "";
        streamRenderer.update(answer);
        return;
      }

      if (event === "done") {
        finalPayload = payload;
        answer = payload.answer || answer;
        streamRenderer.finish(answer);
        typingElement.classList.remove("typing");
        history = Array.isArray(payload.messages)
          ? payload.messages.filter((message) => message.role !== "system")
          : history;
        setStatus("空闲", "idle");
        return;
      }

      if (event === "error") {
        streamError = new Error(payload.message || "流式输出失败");
      }
    });

    if (streamError) {
      throw streamError;
    }

    if (!finalPayload) {
      streamRenderer.finish(answer);
      typingElement.classList.remove("typing");
      setStatus("空闲", "idle");
    }
  } catch (error) {
    typingElement.classList.remove("typing");
    contentNode.classList.remove("markdown");
    contentNode.textContent = `请求失败：${error.message}`;
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
  // 用户输入按纯文本展示（避免 XSS）；AI 回复支持 Markdown 渲染
  if (role === "assistant") {
    contentText.classList.add("markdown");
    contentText.innerHTML = renderMarkdown(content);
  } else {
    contentText.textContent = content;
  }

  wrapper.appendChild(roleText);
  wrapper.appendChild(contentText);
  messageList.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function renderMarkdown(text) {
  if (typeof marked === "undefined") {
    // 库未加载时退化为纯文本，保证可用
    const node = document.createElement("div");
    node.textContent = text;
    return node.innerHTML;
  }
  marked.setOptions({ gfm: true, breaks: true });
  const raw = marked.parse(text || "");
  return typeof DOMPurify === "undefined" ? raw : DOMPurify.sanitize(raw);
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

function createMarkdownStreamRenderer(node) {
  let latestText = "";
  let frameId = null;

  const flush = () => {
    frameId = null;
    node.classList.add("markdown");
    node.innerHTML = renderMarkdown(latestText);
    scrollToBottom();
  };

  return {
    update(text) {
      latestText = text;
      if (frameId !== null) {
        return;
      }
      frameId = window.requestAnimationFrame(flush);
    },
    finish(text) {
      latestText = text;
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
        frameId = null;
      }
      flush();
    },
  };
}

async function consumeEventStream(response, onEvent) {
  if (!response.body) {
    throw new Error("当前浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const rawEvent = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      const parsedEvent = parseSseEvent(rawEvent);
      if (parsedEvent) {
        onEvent(parsedEvent);
      }

      boundaryIndex = buffer.indexOf("\n\n");
    }
  }

  buffer += decoder.decode();
  const tailEvent = parseSseEvent(buffer);
  if (tailEvent) {
    onEvent(tailEvent);
  }
}

function parseSseEvent(rawEvent) {
  if (!rawEvent.trim()) {
    return null;
  }

  let event = "message";
  const dataLines = [];

  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  return {
    event,
    data: dataLines.join("\n"),
  };
}

async function readErrorMessage(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const data = await response.json();
    return data.detail || data.message || "接口调用失败";
  }

  const text = await response.text();
  return text || "接口调用失败";
}
