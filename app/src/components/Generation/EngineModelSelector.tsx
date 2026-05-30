import type { UseFormReturn } from 'react-hook-form';
import { Badge } from '@/components/ui/badge';
import type { VoiceProfileResponse } from '@/lib/api/types';
import type { GenerationFormValues } from '@/lib/hooks/useGenerationForm';

export function applyEngineSelection(form: UseFormReturn<GenerationFormValues>) {
  form.setValue('engine', 'indextts2');
}

interface EngineModelSelectorProps {
  form: UseFormReturn<GenerationFormValues>;
  compact?: boolean;
  selectedProfile?: VoiceProfileResponse | null;
}

export function EngineModelSelector({ compact }: EngineModelSelectorProps) {
  return (
    <Badge variant="outline" className={compact ? 'h-8 rounded-full px-3 text-xs' : undefined}>
      IndexTTS2
    </Badge>
  );
}

export function getEngineDescription(): string {
  return 'IndexTTS2 voice cloning with emotion controls';
}

export function isProfileCompatibleWithEngine(
  profile: VoiceProfileResponse,
  engine: string,
): boolean {
  const voiceType = profile.voice_type || 'cloned';
  return voiceType === 'cloned' && engine === 'indextts2';
}
