import { Pause, Play, RotateCcw, Volume2, VolumeX, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${rest.toString().padStart(2, '0')}`;
}

export function BottomAudioPlayer({
  audioUrl,
  title,
  onClose,
}: {
  audioUrl: string;
  title: string;
  onClose: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.85);

  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
  }, [audioUrl]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = volume;
  }, [volume]);

  const togglePlayback = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      void audio.play();
    }
  }, [isPlaying]);

  const restart = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    setCurrentTime(0);
  }, []);

  const seek = useCallback((value: number) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;
    audio.currentTime = value;
    setCurrentTime(value);
  }, [duration]);

  return (
    <div className="bottom-audio-player" role="region" aria-label="Generated audio player">
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="auto"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
      />

      <div className="bottom-audio-meta">
        <strong>{title}</strong>
        <span>{formatTime(currentTime)} / {formatTime(duration)}</span>
      </div>

      <button className="bottom-audio-icon" onClick={togglePlayback} title={isPlaying ? 'Pause' : 'Play'}>
        {isPlaying ? <Pause size={17} /> : <Play size={17} />}
      </button>
      <button className="bottom-audio-icon secondary" onClick={restart} title="Restart">
        <RotateCcw size={15} />
      </button>

      <input
        className="bottom-audio-seek"
        type="range"
        min={0}
        max={duration || 0}
        step={0.01}
        value={Math.min(currentTime, duration || 0)}
        onChange={(event) => seek(Number(event.currentTarget.value))}
      />

      <div className="bottom-audio-volume">
        {volume === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={volume}
          onChange={(event) => setVolume(Number(event.currentTarget.value))}
        />
      </div>

      <button className="bottom-audio-icon secondary" onClick={onClose} title="Close">
        <X size={16} />
      </button>
    </div>
  );
}
