interface WelcomePanelProps {
  onPrompt: (message: string) => void;
  onRainSimulation: () => void;
}

const prompts = [
  { number: '01', title: 'Find a dinner spot', detail: 'Quiet, local, and nearby', message: 'Suggest a quiet dinner place near Sohra with vegetarian options.' },
  { number: '02', title: 'Plan my three days', detail: 'Made around what I enjoy', message: 'Plan a three-day Meghalaya itinerary around Sohra. I enjoy caves, waterfalls, local culture, and quiet nature.' },
];

export default function WelcomePanel({ onPrompt, onRainSimulation }: WelcomePanelProps) {
  return (
    <div className="welcome-block">
      <div className="welcome-icon">✳</div>
      <p className="eyebrow">A LITTLE HELP, RIGHT ON TIME</p>
      <h2>Your journey has<br /><em>just begun.</em></h2>
      <p className="welcome-copy">I know where you're staying and what you love. Ask me anything about your time in Meghalaya.</p>
      <div className="suggestions">
        {prompts.map(prompt => (
          <button className="suggestion" key={prompt.number} onClick={() => onPrompt(prompt.message)}>
            <span>{prompt.number}</span><span>{prompt.title}<small>{prompt.detail}</small></span><b>↗</b>
          </button>
        ))}
        <button className="suggestion" onClick={onRainSimulation}>
          <span>03</span><span>Rain changed tomorrow<small>Try the itinerary approval flow</small></span><b>↗</b>
        </button>
      </div>
    </div>
  );
}
