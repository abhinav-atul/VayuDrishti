import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { sendChatMessage } from "../api";

/**
 * ChatPanel — LLM-powered air quality advisory chatbot.
 * Uses the selected map point's AQI data as context.
 */
export default function ChatPanel({ selectedPoint, onClose }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm VayuDrishti's air quality advisor. Click anywhere on the map and ask me about air quality at that location. I can answer in English, Hindi, Kannada, or Tamil.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setSending(true);

    try {
      const res = await sendChatMessage(
        userMsg,
        selectedPoint?.lat || null,
        selectedPoint?.lng || null,
        "en"
      );
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't connect to the advisory service. Please try again.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel" id="chat-panel">
      <div className="chat-panel__header">
        <span className="chat-panel__title">🌬️ Air Quality Advisor</span>
        <button className="chat-panel__close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`chat-message chat-message--${msg.role === "user" ? "user" : "assistant"}`}
          >
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ))}
        {sending && (
          <div className="chat-message chat-message--assistant">
            <em>Thinking...</em>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <input
          className="chat-input__field"
          type="text"
          placeholder={
            selectedPoint
              ? "Ask about air quality at the selected point..."
              : "Click a point on the map first..."
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={sending}
          id="chat-input-field"
        />
        <button
          className="chat-input__send"
          onClick={handleSend}
          disabled={sending || !input.trim()}
          id="chat-send-btn"
        >
          Send
        </button>
      </div>
    </div>
  );
}
