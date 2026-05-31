import type { EmotionVector } from '../shared/types';

const labels = ['Happy', 'Angry', 'Sad', 'Afraid', 'Disgust', 'Melancholy', 'Surprise', 'Calm'];

export function EmotionVectorEditor({
  value,
  onChange,
}: {
  value: EmotionVector;
  onChange: (value: EmotionVector) => void;
}) {
  return (
    <div className="emotion-grid">
      {labels.map((label, index) => (
        <label key={label} className="range-row">
          <span>{label}</span>
          <input
            type="range"
            min="0"
            max="1.2"
            step="0.05"
            value={value[index]}
            onChange={(event) => {
              const next = [...value] as EmotionVector;
              next[index] = Number(event.target.value);
              onChange(next);
            }}
          />
          <strong>{value[index].toFixed(2)}</strong>
        </label>
      ))}
    </div>
  );
}
