import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react';

interface ComposerProps {
  disabled: boolean;
  onSend: (message: string) => void;
}

export default function Composer({ disabled, onSend }: ComposerProps) {
  const [value, setValue] = useState('');
  const textarea = useRef<HTMLTextAreaElement>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const message = value.trim();
    if (!message || disabled) return;
    onSend(message);
    setValue('');
    if (textarea.current) textarea.current.style.height = 'auto';
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <footer className="composer-wrap">
      <form className="composer-box" onSubmit={submit}>
        <textarea
          ref={textarea}
          rows={1}
          maxLength={1000}
          value={value}
          onChange={event => {
            setValue(event.target.value);
            event.target.style.height = 'auto';
            event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your trip…"
          aria-label="Message tripPartner"
          disabled={disabled}
        />
        <button type="submit" className="send-button" aria-label="Send message" disabled={disabled || !value.trim()}>↑</button>
      </form>
      <div className="composer-note"><span>✦</span> Thoughtful suggestions, grounded in local knowledge <span className="note-right">Sample trip · Not a live booking</span></div>
    </footer>
  );
}
