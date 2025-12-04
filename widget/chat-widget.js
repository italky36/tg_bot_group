/**
 * SupportHub Chat Widget
 * A lightweight chat widget for website support
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        wsUrl: window.SUPPORTHUB_WS_URL || 'ws://localhost:8000/ws/widget',
        primaryColor: window.SUPPORTHUB_COLOR || '#007bff',
        position: window.SUPPORTHUB_POSITION || 'bottom-right',
        greeting: window.SUPPORTHUB_GREETING || 'Здравствуйте! Чем можем помочь?',
    };

    class ChatWidget {
        constructor() {
            this.visitorId = this.getOrCreateVisitorId();
            this.ws = null;
            this.isOpen = false;
            this.messages = [];
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;

            this.init();
        }

        getOrCreateVisitorId() {
            let visitorId = localStorage.getItem('supporthub_visitor_id');
            if (!visitorId) {
                visitorId = this.generateId();
                localStorage.setItem('supporthub_visitor_id', visitorId);
            }
            return visitorId;
        }

        generateId() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        init() {
            this.injectStyles();
            this.createWidget();
            this.attachEventListeners();
            this.connectWebSocket();
        }

        injectStyles() {
            const style = document.createElement('style');
            style.textContent = `
                .supporthub-widget {
                    position: fixed;
                    ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                    bottom: 20px;
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .supporthub-button {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background-color: ${CONFIG.primaryColor};
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: transform 0.3s, box-shadow 0.3s;
                }

                .supporthub-button:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
                }

                .supporthub-button.has-unread {
                    animation: pulse 2s infinite;
                }

                @keyframes pulse {
                    0%, 100% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
                    50% { box-shadow: 0 4px 20px ${CONFIG.primaryColor}; }
                }

                .supporthub-button svg {
                    width: 28px;
                    height: 28px;
                    fill: white;
                }

                .supporthub-badge {
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background-color: #ff4444;
                    color: white;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                }

                .supporthub-window {
                    position: fixed;
                    ${CONFIG.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                    bottom: 90px;
                    width: 380px;
                    height: 600px;
                    max-height: calc(100vh - 120px);
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                    display: none;
                    flex-direction: column;
                    overflow: hidden;
                    animation: slideUp 0.3s ease-out;
                }

                @keyframes slideUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                .supporthub-window.open {
                    display: flex;
                }

                .supporthub-header {
                    background-color: ${CONFIG.primaryColor};
                    color: white;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }

                .supporthub-header h3 {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                }

                .supporthub-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    padding: 0;
                    width: 30px;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .supporthub-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    background: #f8f9fa;
                }

                .supporthub-message {
                    margin-bottom: 16px;
                    display: flex;
                    flex-direction: column;
                }

                .supporthub-message.user {
                    align-items: flex-end;
                }

                .supporthub-message.operator {
                    align-items: flex-start;
                }

                .supporthub-message-bubble {
                    max-width: 70%;
                    padding: 12px 16px;
                    border-radius: 18px;
                    word-wrap: break-word;
                }

                .supporthub-message.user .supporthub-message-bubble {
                    background-color: ${CONFIG.primaryColor};
                    color: white;
                }

                .supporthub-message.operator .supporthub-message-bubble {
                    background-color: white;
                    color: #333;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                }

                .supporthub-message-meta {
                    font-size: 11px;
                    color: #999;
                    margin-top: 4px;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }

                .supporthub-message-status {
                    font-size: 14px;
                }

                .supporthub-input-area {
                    padding: 16px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    display: flex;
                    gap: 8px;
                }

                .supporthub-input {
                    flex: 1;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
                    padding: 10px 16px;
                    font-size: 14px;
                    outline: none;
                    resize: none;
                    font-family: inherit;
                    max-height: 100px;
                }

                .supporthub-input:focus {
                    border-color: ${CONFIG.primaryColor};
                }

                .supporthub-send {
                    background-color: ${CONFIG.primaryColor};
                    border: none;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: opacity 0.2s;
                }

                .supporthub-send:hover:not(:disabled) {
                    opacity: 0.9;
                }

                .supporthub-send:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .supporthub-send svg {
                    width: 20px;
                    height: 20px;
                    fill: white;
                }

                .supporthub-typing {
                    padding: 8px 16px;
                    color: #666;
                    font-size: 13px;
                    font-style: italic;
                }

                @media (max-width: 480px) {
                    .supporthub-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 120px);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        createWidget() {
            const widget = document.createElement('div');
            widget.className = 'supporthub-widget';
            widget.innerHTML = `
                <button class="supporthub-button" id="supporthub-toggle">
                    <svg viewBox="0 0 24 24">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                    </svg>
                    <span class="supporthub-badge" id="supporthub-badge" style="display: none;">0</span>
                </button>

                <div class="supporthub-window" id="supporthub-window">
                    <div class="supporthub-header">
                        <h3>Чат поддержки</h3>
                        <button class="supporthub-close" id="supporthub-close">&times;</button>
                    </div>
                    <div class="supporthub-messages" id="supporthub-messages"></div>
                    <div class="supporthub-typing" id="supporthub-typing" style="display: none;">
                        Оператор печатает...
                    </div>
                    <div class="supporthub-input-area">
                        <textarea
                            class="supporthub-input"
                            id="supporthub-input"
                            placeholder="Введите сообщение..."
                            rows="1"
                        ></textarea>
                        <button class="supporthub-send" id="supporthub-send">
                            <svg viewBox="0 0 24 24">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(widget);
        }

        attachEventListeners() {
            document.getElementById('supporthub-toggle').addEventListener('click', () => {
                this.toggleChat();
            });

            document.getElementById('supporthub-close').addEventListener('click', () => {
                this.closeChat();
            });

            const input = document.getElementById('supporthub-input');
            const sendBtn = document.getElementById('supporthub-send');

            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            input.addEventListener('input', () => {
                this.autoResize(input);
            });

            sendBtn.addEventListener('click', () => {
                this.sendMessage();
            });
        }

        autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        }

        toggleChat() {
            if (this.isOpen) {
                this.closeChat();
            } else {
                this.openChat();
            }
        }

        openChat() {
            const window = document.getElementById('supporthub-window');
            window.classList.add('open');
            this.isOpen = true;
            this.clearUnreadBadge();
            this.scrollToBottom();

            // Focus input
            setTimeout(() => {
                document.getElementById('supporthub-input').focus();
            }, 300);
        }

        closeChat() {
            const window = document.getElementById('supporthub-window');
            window.classList.remove('open');
            this.isOpen = false;
        }

        connectWebSocket() {
            try {
                this.ws = new WebSocket(`${CONFIG.wsUrl}/${this.visitorId}`);

                this.ws.onopen = () => {
                    console.log('SupportHub: Connected');
                    this.reconnectAttempts = 0;
                };

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };

                this.ws.onerror = (error) => {
                    console.error('SupportHub: WebSocket error', error);
                };

                this.ws.onclose = () => {
                    console.log('SupportHub: Disconnected');
                    this.attemptReconnect();
                };
            } catch (error) {
                console.error('SupportHub: Failed to connect', error);
                this.attemptReconnect();
            }
        }

        attemptReconnect() {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`SupportHub: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connectWebSocket(), delay);
            }
        }

        handleWebSocketMessage(data) {
            switch (data.type) {
                case 'connected':
                    console.log('SupportHub: Session established');
                    break;

                case 'history':
                    this.loadHistory(data.messages);
                    break;

                case 'message':
                    this.addMessage(data);
                    if (!this.isOpen) {
                        this.incrementUnreadBadge();
                    }
                    break;

                case 'message_sent':
                    // Message confirmation
                    break;

                case 'typing':
                    this.showTypingIndicator();
                    break;

                case 'stop_typing':
                    this.hideTypingIndicator();
                    break;

                case 'closed':
                    this.showSystemMessage('Диалог завершен');
                    break;

                case 'pong':
                    // Keep-alive response
                    break;

                case 'error':
                    console.error('SupportHub error:', data.error);
                    break;
            }
        }

        loadHistory(messages) {
            messages.forEach(msg => {
                this.addMessage({
                    text: msg.text,
                    is_from_user: msg.is_from_user,
                    created_at: msg.created_at,
                    is_delivered: msg.is_delivered,
                    is_read: msg.is_read,
                }, false);
            });
            this.scrollToBottom();
        }

        sendMessage() {
            const input = document.getElementById('supporthub-input');
            const text = input.value.trim();

            if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
                return;
            }

            // Send to server
            this.ws.send(JSON.stringify({
                type: 'message',
                text: text,
                page_url: window.location.href,
                user_agent: navigator.userAgent,
            }));

            // Add to UI immediately
            this.addMessage({
                text: text,
                is_from_user: true,
                created_at: new Date().toISOString(),
                is_delivered: false,
            });

            input.value = '';
            this.autoResize(input);
        }

        addMessage(data, scroll = true) {
            const messagesContainer = document.getElementById('supporthub-messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `supporthub-message ${data.is_from_user ? 'user' : 'operator'}`;

            const bubble = document.createElement('div');
            bubble.className = 'supporthub-message-bubble';
            bubble.textContent = data.text;

            const meta = document.createElement('div');
            meta.className = 'supporthub-message-meta';

            const time = new Date(data.created_at).toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
            meta.textContent = time;

            if (data.is_from_user) {
                const status = document.createElement('span');
                status.className = 'supporthub-message-status';
                status.textContent = data.is_read ? '✓✓' : data.is_delivered ? '✓' : '○';
                meta.appendChild(status);
            }

            messageDiv.appendChild(bubble);
            messageDiv.appendChild(meta);
            messagesContainer.appendChild(messageDiv);

            if (scroll) {
                this.scrollToBottom();
            }
        }

        showSystemMessage(text) {
            const messagesContainer = document.getElementById('supporthub-messages');
            const messageDiv = document.createElement('div');
            messageDiv.style.cssText = 'text-align: center; color: #999; font-size: 13px; margin: 16px 0;';
            messageDiv.textContent = text;
            messagesContainer.appendChild(messageDiv);
            this.scrollToBottom();
        }

        showTypingIndicator() {
            document.getElementById('supporthub-typing').style.display = 'block';
        }

        hideTypingIndicator() {
            document.getElementById('supporthub-typing').style.display = 'none';
        }

        scrollToBottom() {
            const messages = document.getElementById('supporthub-messages');
            messages.scrollTop = messages.scrollHeight;
        }

        incrementUnreadBadge() {
            const badge = document.getElementById('supporthub-badge');
            const button = document.getElementById('supporthub-toggle');
            const count = parseInt(badge.textContent) || 0;
            badge.textContent = count + 1;
            badge.style.display = 'flex';
            button.classList.add('has-unread');
        }

        clearUnreadBadge() {
            const badge = document.getElementById('supporthub-badge');
            const button = document.getElementById('supporthub-toggle');
            badge.textContent = '0';
            badge.style.display = 'none';
            button.classList.remove('has-unread');
        }
    }

    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new ChatWidget();
        });
    } else {
        new ChatWidget();
    }
})();
