import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react';

export interface ToastMessage {
  id: number;
  title: string;
  detail: string;
  tone: 'info' | 'success' | 'warning';
}

interface ToastStackProps {
  messages: ToastMessage[];
  onDismiss: (id: number) => void;
}

export function ToastStack({ messages, onDismiss }: ToastStackProps) {
  return (
    <div className="toast-stack">
      {messages.map((message) => (
        <div className={`toast ${message.tone}`} key={message.id}>
          {message.tone === 'success' ? <CheckCircle2 size={17} /> : message.tone === 'warning' ? <TriangleAlert size={17} /> : <Info size={17} />}
          <div>
            <strong>{message.title}</strong>
            <span>{message.detail}</span>
          </div>
          <button type="button" onClick={() => onDismiss(message.id)} title="Dismiss notification">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
