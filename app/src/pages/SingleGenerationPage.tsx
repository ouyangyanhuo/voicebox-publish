import { useCallback, useEffect, useRef, useState } from 'react';
import { Mic, Square, Upload, User } from 'lucide-react';
import { AudioWaveformPlayer } from '../components/AudioWaveformPlayer';
import { BottomAudioPlayer } from '../components/BottomAudioPlayer';
import { EmotionVectorEditor } from '../components/EmotionVectorEditor';
import { PageHeader } from '../components/PageHeader';
import { Panel } from '../components/Panel';
import { Select } from '../components/Select';
import { apiGet, apiPost, apiUpload, apiUrl } from '../shared/api';
import { useI18n } from '../shared/i18n';
import type {
  EmotionVector,
  GenerationStatus,
  GenerationStatusResponse,
  PresetVoice,
  UploadedGenerationAudio,
} from '../shared/types';

type AudioSource = 'preset' | 'upload' | 'record';

const ACCEPTED_FORMATS = ['audio/wav', 'audio/mpeg', 'audio/flac', 'audio/ogg', 'audio/x-wav'];

export function SingleGenerationPage() {
  const { t } = useI18n();
  const [vector, setVector] = useState<EmotionVector>([0, 0, 0, 0, 0, 0, 0, 0]);
  const [audioSource, setAudioSource] = useState<AudioSource>('preset');
  const [presetVoices, setPresetVoices] = useState<PresetVoice[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState('');
  const [text, setText] = useState('');
  const [emoAlpha, setEmoAlpha] = useState(1);
  const [useRandom, setUseRandom] = useState(false);

  // Upload state
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioFileName, setAudioFileName] = useState<string | null>(null);
  const [uploadedAudioId, setUploadedAudioId] = useState<string | null>(null);
  const [recordedAudioId, setRecordedAudioId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const [generationMessage, setGenerationMessage] = useState<string | null>(null);
  const [resultAudioUrl, setResultAudioUrl] = useState<string | null>(null);

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const revokeUrl = useCallback(() => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  const setAudioFromBlob = useCallback(
    (blob: Blob, fileName: string, uploaded?: UploadedGenerationAudio) => {
      revokeUrl();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setAudioFileName(fileName);
      if (audioSource === 'record') {
        setRecordedAudioId(uploaded?.id ?? null);
        setUploadedAudioId(null);
      } else {
        setUploadedAudioId(uploaded?.id ?? null);
        setRecordedAudioId(null);
      }
    },
    [audioSource, revokeUrl],
  );

  const handleFile = useCallback(
    async (file: File) => {
      if (!ACCEPTED_FORMATS.includes(file.type) && !file.name.match(/\.(wav|mp3|flac|ogg)$/i)) {
        return;
      }
      try {
        const uploaded = await apiUpload<UploadedGenerationAudio>('/generation-audio', file, file.name);
        setAudioFromBlob(file, file.name, uploaded);
      } catch (error) {
        setGenerationStatus('failed');
        setGenerationMessage(error instanceof Error ? error.message : t('generationFailed'));
      }
    },
    [setAudioFromBlob, t],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleRemoveAudio = useCallback(() => {
    revokeUrl();
    setAudioUrl(null);
    setAudioFileName(null);
    setUploadedAudioId(null);
    setRecordedAudioId(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [revokeUrl]);

  // Recording
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const ts = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        const name = `recording_${ts.getFullYear()}${pad(ts.getMonth() + 1)}${pad(ts.getDate())}_${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}.webm`;
        apiUpload<UploadedGenerationAudio>('/generation-audio', blob, name)
          .then((uploaded) => setAudioFromBlob(blob, name, uploaded))
          .catch((error) => {
            setGenerationStatus('failed');
            setGenerationMessage(error instanceof Error ? error.message : t('generationFailed'));
          });
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      // Microphone permission denied or unavailable
    }
  }, [setAudioFromBlob, t]);

  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }, []);

  const switchSource = useCallback(
    (source: AudioSource) => {
      if (isRecording) stopRecording();
      if (source !== 'upload' && source !== 'record') {
        handleRemoveAudio();
      }
      setAudioSource(source);
    },
    [isRecording, stopRecording, handleRemoveAudio],
  );

  useEffect(() => {
    apiGet<{ items: PresetVoice[] }>('/preset-voices')
      .then((data) => {
        setPresetVoices(data.items);
        setSelectedPresetId((current) => current || data.items[0]?.id || '');
      })
      .catch(() => setPresetVoices([]));
  }, []);

  useEffect(() => {
    if (!generationId || generationStatus === 'completed' || generationStatus === 'failed') return;
    const timer = window.setInterval(() => {
      apiGet<GenerationStatusResponse>(`/generate/${generationId}`)
        .then((data) => {
          setGenerationStatus(data.status);
          if (data.error) setGenerationMessage(data.error);
          if (data.status === 'running') setGenerationMessage(t('generationRunning'));
          if (data.status === 'completed' && data.audio_url) {
            setGenerationMessage(t('generationCompleted'));
            setResultAudioUrl(apiUrl(data.audio_url));
          }
          if (data.status === 'failed') {
            setGenerationMessage(data.error || t('generationFailed'));
          }
        })
        .catch((error) => {
          setGenerationStatus('failed');
          setGenerationMessage(error instanceof Error ? error.message : t('generationFailed'));
        });
    }, 1500);
    return () => window.clearInterval(timer);
  }, [generationId, generationStatus, t]);

  const submitGeneration = useCallback(async () => {
    if (!text.trim()) return;
    if (audioSource === 'preset' && !selectedPresetId) {
      setGenerationStatus('failed');
      setGenerationMessage(t('noReferenceAudio'));
      return;
    }
    if (audioSource === 'upload' && !uploadedAudioId) {
      setGenerationStatus('failed');
      setGenerationMessage(t('noReferenceAudio'));
      return;
    }
    if (audioSource === 'record' && !recordedAudioId) {
      setGenerationStatus('failed');
      setGenerationMessage(t('noReferenceAudio'));
      return;
    }
    setResultAudioUrl(null);
    setGenerationStatus('queued');
    setGenerationMessage(t('generationQueued'));
    try {
      const response = await apiPost<{ id: string; status: GenerationStatus; message: string }>('/generate', {
        text,
        language: 'zh',
        audio_source: audioSource,
        preset_voice_id: audioSource === 'preset' ? selectedPresetId : null,
        uploaded_audio_id: audioSource === 'upload' ? uploadedAudioId : null,
        recorded_audio_id: audioSource === 'record' ? recordedAudioId : null,
        emo_alpha: emoAlpha,
        emo_vector: vector,
        use_random: useRandom,
        interval_silence: 200,
        max_text_tokens_per_segment: 120,
      });
      setGenerationId(response.id);
      setGenerationStatus(response.status);
      setGenerationMessage(response.message);
    } catch (error) {
      setGenerationStatus('failed');
      setGenerationMessage(error instanceof Error ? error.message : t('generationFailed'));
    }
  }, [audioSource, emoAlpha, recordedAudioId, selectedPresetId, t, text, uploadedAudioId, useRandom, vector]);

  return (
    <>
      <PageHeader title={t('singleTitle')} subtitle={t('singleSubtitle')} />
      <div className="workspace two-column">
        <Panel title={t('singleTitle')}>
          {/* Audio source selector */}
          <label className="field">
            <span>{t('audioSource')}</span>
            <div className="segmented segmented-3">
              <button
                className={audioSource === 'preset' ? 'selected' : ''}
                onClick={() => switchSource('preset')}
              >
                <User size={14} />
                {t('audioSourcePreset')}
              </button>
              <button
                className={audioSource === 'upload' ? 'selected' : ''}
                onClick={() => switchSource('upload')}
              >
                <Upload size={14} />
                {t('audioSourceUpload')}
              </button>
              <button
                className={audioSource === 'record' ? 'selected' : ''}
                onClick={() => switchSource('record')}
              >
                <Mic size={14} />
                {t('audioSourceRecord')}
              </button>
            </div>
          </label>

          {/* Preset role selector */}
          {audioSource === 'preset' && (
            <label className="field">
              <span>{t('role')}</span>
              <Select
                value={selectedPresetId}
                onChange={setSelectedPresetId}
                options={
                  presetVoices.length === 0
                    ? [{ value: '', label: t('emptyState') }]
                    : presetVoices.map((voice) => ({ value: voice.id, label: voice.name }))
                }
              />
            </label>
          )}

          {/* Upload zone */}
          {audioSource === 'upload' && !audioUrl && (
            <div
              className={`upload-zone${isDragging ? ' drag-over' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
            >
              <Upload size={28} />
              <span className="upload-zone-hint">{t('uploadHint')}</span>
              <span className="upload-zone-formats">{t('uploadFormats')}</span>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileInput}
                hidden
              />
            </div>
          )}

          {/* Record zone */}
          {audioSource === 'record' && !audioUrl && (
            <div className="record-zone">
              <button
                className={`record-button${isRecording ? ' recording' : ''}`}
                onClick={isRecording ? stopRecording : startRecording}
              >
                {isRecording ? <Square size={20} /> : <Mic size={24} />}
              </button>
              <span className="record-label">
                {isRecording ? t('recording') : t('recordStart')}
              </span>
            </div>
          )}

          {/* Audio waveform player (shown after upload or recording) */}
          {audioUrl && (
            <div className="field">
              <AudioWaveformPlayer
                audioUrl={audioUrl}
                fileName={audioFileName}
                onRemove={handleRemoveAudio}
              />
            </div>
          )}

          <label className="field">
            <span>{t('text')}</span>
            <textarea rows={8} placeholder={t('textPlaceholder')} value={text} onChange={(event) => setText(event.target.value)} />
          </label>
          <button className="primary-button" onClick={submitGeneration} disabled={generationStatus === 'queued' || generationStatus === 'running'}>
            {t('generate')}
          </button>
        </Panel>

        <Panel title={t('emotionControl')}>
          <div className="emotion-panel-body">
            <label className="field">
              <span>{t('emotionAlpha')}</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={emoAlpha}
                onChange={(event) => setEmoAlpha(Number(event.target.value))}
              />
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={useRandom} onChange={(event) => setUseRandom(event.target.checked)} />
              <span>{t('randomEmotion')}</span>
            </label>
            <EmotionVectorEditor value={vector} onChange={setVector} />
          </div>
        </Panel>
      </div>
      {generationMessage && (
        <div className={`toast toast-${generationStatus ?? 'queued'}`} role="status">
          <strong>
            {generationStatus === 'failed'
              ? t('generationFailed')
              : generationStatus === 'completed'
                ? t('generationCompleted')
                : generationStatus === 'running'
                  ? t('generationRunning')
                  : t('generationQueued')}
          </strong>
          <span>{generationMessage}</span>
        </div>
      )}
      {resultAudioUrl && (
        <BottomAudioPlayer
          audioUrl={resultAudioUrl}
          title="generated.wav"
          onClose={() => setResultAudioUrl(null)}
        />
      )}
    </>
  );
}
