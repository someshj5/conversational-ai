
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

function Message({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      <div className="message-avatar">
        {isUser ? "Y" : "F"}
      </div>

      <div className="message-content">
        <div className="message-author">
          {isUser ? "You" : "Forge"}
        </div>

        <div className="message-bubble">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}


function parseSSEBlock(block) {
  let event = "message";
  const dataLines = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (!dataLines.length) return null;

  try {
    return {
      event,
      data: JSON.parse(dataLines.join("\n")),
    };
  } catch {
    throw new Error("Forge returned an invalid SSE event.");
  }
}


function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);
  const submittingRef = useRef(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);



  async function handleSubmit(event) {
    event.preventDefault();

    if (submittingRef.current) return;

    const question = input.trim();
    if (!question) return;

    submittingRef.current = true;

    const assistantId = crypto.randomUUID();

    const updatedMessages = [
      ...messages,
      {
        role: "user",
        content: question,
      },
      {
        id: assistantId,
        role: "assistant",
        content: "",
      },
    ];

    setMessages(updatedMessages);
    setInput("");
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/chat/stream/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({
          messages: updatedMessages
            .filter((message) => message.role !== "assistant" || message.content)
            .map(({ role, content }) => ({ role, content })),
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `HTTP ${response.status}: ${errorText.slice(0, 300)}`
        );
      }

      if (!response.body) {
        throw new Error("Streaming response body is unavailable.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = "";
      let streamCompleted = false;

      function appendToken(content) {
        setMessages((previous) =>
          previous.map((message) =>
            message.id === assistantId
              ? { ...message, content: message.content + content }
              : message
          )
        );
      }

      function handleEvent(block) {
        const parsed = parseSSEBlock(block);
        if (!parsed) return;

        switch (parsed.event) {
          case "token":
            appendToken(parsed.data.content || "");
            break;

          case "done":
            streamCompleted = true;
            break;

          case "error":
            throw new Error(
              parsed.data.message || "Forge streaming failed."
            );

          default:
            break;
        }
      }

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          buffer += decoder.decode();
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Normalize CRLF and CR line endings.
        buffer = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          handleEvent(block);

          if (streamCompleted) break;
        }

        if (streamCompleted) {
          await reader.cancel();
          break;
        }
      }

      // Process any final event left in the buffer.
      if (!streamCompleted && buffer.trim()) {
        handleEvent(buffer);
      }

      if (!streamCompleted) {
        throw new Error("Forge stream ended without a completion event.");
      }

    } catch (err) {
      console.error("Forge streaming error:", err);
      setError(err.message || "Unable to stream response.");
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }



  function handleNewChat() {
    if (loading) return;

    setMessages([]);
    setInput("");
    setError("");
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">F</div>
          <span>Forge</span>
        </div>

        <button
          className="new-chat-button"
          onClick={handleNewChat}
          disabled={loading}
        >
          + New chat
        </button>

        <div className="sidebar-description">
          Repository intelligence
        </div>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Local development
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>Repository Assistant</h1>
            <p>Ask questions about your codebase</p>
          </div>

          <div className="model-label">
            Deep Agents
          </div>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">F</div>

              <h2>Understand your codebase.</h2>

              <p>
                Ask Forge where a feature lives, how a function
                works, or how different modules interact.
              </p>

              <div className="suggestions">
                {[
                  "Where is create_agent implemented?",
                  "Explain the repository architecture.",
                  "Where are API endpoints defined?",
                  "How does authentication work?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <Message
                  key={index}
                  message={message}
                />
              ))}

              {loading && (
                <div className="loading-indicator">
                  <span />
                  <span />
                  <span />
                  <p>Forge is responding...</p>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        <footer className="composer-container">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <form
            className="composer"
            onSubmit={handleSubmit}
          >
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" &&
                  !event.shiftKey
                ) {
                  event.preventDefault();
                  handleSubmit(event);
                }
              }}
              placeholder="Ask anything about your repository..."
              rows={2}
              disabled={loading}
            />

            <button
              type="submit"
              disabled={!input.trim() || loading}
            >
              {loading ? "..." : "↑"}
            </button>
          </form>

          <p className="composer-note">
            Forge answers using repository context. It does not modify your code.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
