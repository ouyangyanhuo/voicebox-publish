import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { useToast } from '@/components/ui/use-toast';
import { apiClient } from '@/lib/api/client';
import type { EffectConfig } from '@/lib/api/types';
import { LANGUAGE_CODES, type LanguageCode } from '@/lib/constants/languages';
import { useGeneration } from '@/lib/hooks/useGeneration';
import { useModelDownloadToast } from '@/lib/hooks/useModelDownloadToast';
import { useGenerationSettings } from '@/lib/hooks/useSettings';
import { useGenerationStore } from '@/stores/generationStore';

const generationSchema = z.object({
  text: z.string().min(1, '').max(50000),
  language: z.enum(LANGUAGE_CODES as [LanguageCode, ...LanguageCode[]]),
  seed: z.number().int().optional(),
  modelSize: z.enum(['1.7B', '0.6B', '1B', '3B']).optional(),
  instruct: z.string().max(500).optional(),
  engine: z.enum(['indextts2']).optional(),
  emoAudioPrompt: z.string().max(1000).optional(),
  emoAlpha: z.number().min(0).max(1).optional(),
  emoVector: z.array(z.number().min(0).max(1.4)).length(8).optional(),
  useEmoText: z.boolean().optional(),
  emoText: z.string().max(1000).optional(),
  useRandom: z.boolean().optional(),
  intervalSilence: z.number().int().min(0).max(5000).optional(),
  maxTextTokensPerSegment: z.number().int().min(20).max(500).optional(),
  topP: z.number().min(0).max(1).optional(),
  topK: z.number().int().min(1).max(200).optional(),
  temperature: z.number().min(0).max(2).optional(),
  lengthPenalty: z.number().min(-10).max(10).optional(),
  numBeams: z.number().int().min(1).max(10).optional(),
  repetitionPenalty: z.number().min(0).max(30).optional(),
  maxMelTokens: z.number().int().min(100).max(10000).optional(),
  personality: z.boolean().optional(),
});

export type GenerationFormValues = z.infer<typeof generationSchema>;

interface UseGenerationFormOptions {
  onSuccess?: (generationId: string) => void;
  defaultValues?: Partial<GenerationFormValues>;
  getEffectsChain?: () => EffectConfig[] | undefined;
}

export function useGenerationForm(options: UseGenerationFormOptions = {}) {
  const { toast } = useToast();
  const generation = useGeneration();
  const addPendingGeneration = useGenerationStore((state) => state.addPendingGeneration);
  const { settings: genSettings } = useGenerationSettings();
  const maxChunkChars = genSettings?.max_chunk_chars ?? 800;
  const crossfadeMs = genSettings?.crossfade_ms ?? 50;
  const normalizeAudio = genSettings?.normalize_audio ?? true;
  const [downloadingModelName, setDownloadingModelName] = useState<string | null>(null);
  const [downloadingDisplayName, setDownloadingDisplayName] = useState<string | null>(null);

  useModelDownloadToast({
    modelName: downloadingModelName || '',
    displayName: downloadingDisplayName || '',
    enabled: !!downloadingModelName,
  });

  const form = useForm<GenerationFormValues>({
    resolver: zodResolver(generationSchema),
    defaultValues: {
      text: '',
      language: 'en',
      seed: undefined,
      modelSize: undefined,
      instruct: '',
      engine: 'indextts2',
      emoAlpha: 1,
      emoVector: [0, 0, 0, 0, 0, 0, 0, 0],
      useEmoText: false,
      useRandom: false,
      intervalSilence: 200,
      maxTextTokensPerSegment: 120,
      topP: 0.8,
      topK: 30,
      temperature: 0.8,
      numBeams: 3,
      repetitionPenalty: 10,
      maxMelTokens: 1500,
      personality: false,
      ...options.defaultValues,
    },
  });

  async function handleSubmit(
    data: GenerationFormValues,
    selectedProfileId: string | null,
  ): Promise<void> {
    if (!selectedProfileId) {
      toast({
        title: 'No profile selected',
        description: 'Please select a voice profile from the cards above.',
        variant: 'destructive',
      });
      return;
    }

    try {
      const engine = 'indextts2' as const;
      const modelName = 'indextts2';
      const displayName = 'IndexTTS2';

      // Check if model needs downloading
      try {
        const modelStatus = await apiClient.getModelStatus();
        const model = modelStatus.models.find((m) => m.model_name === modelName);

        if (model && !model.downloaded) {
          setDownloadingModelName(modelName);
          setDownloadingDisplayName(displayName);
        }
      } catch (error) {
        console.error('Failed to check model status:', error);
      }

      const effectsChain = options.getEffectsChain?.();
      // This now returns immediately with status="generating"
      const result = await generation.mutateAsync({
        profile_id: selectedProfileId,
        text: data.text,
        language: data.language,
        seed: data.seed,
        model_size: undefined,
        engine,
        instruct: undefined,
        emo_audio_prompt: data.emoAudioPrompt || undefined,
        emo_alpha: data.emoAlpha,
        emo_vector: data.emoVector,
        use_emo_text: data.useEmoText || undefined,
        emo_text: data.emoText || undefined,
        use_random: data.useRandom || undefined,
        interval_silence: data.intervalSilence,
        max_text_tokens_per_segment: data.maxTextTokensPerSegment,
        top_p: data.topP,
        top_k: data.topK,
        temperature: data.temperature,
        length_penalty: data.lengthPenalty,
        num_beams: data.numBeams,
        repetition_penalty: data.repetitionPenalty,
        max_mel_tokens: data.maxMelTokens,
        personality: data.personality || undefined,
        max_chunk_chars: maxChunkChars,
        crossfade_ms: crossfadeMs,
        normalize: normalizeAudio,
        effects_chain: effectsChain?.length ? effectsChain : undefined,
      });

      // Track this generation for SSE status updates
      addPendingGeneration(result.id);

      // Reset form immediately — user can start typing again
      form.reset({
        text: '',
        language: data.language,
        seed: undefined,
        modelSize: undefined,
        instruct: '',
        engine,
        emoAudioPrompt: data.emoAudioPrompt,
        emoAlpha: data.emoAlpha,
        emoVector: data.emoVector,
        useEmoText: data.useEmoText,
        emoText: data.emoText,
        useRandom: data.useRandom,
        intervalSilence: data.intervalSilence,
        maxTextTokensPerSegment: data.maxTextTokensPerSegment,
        topP: data.topP,
        topK: data.topK,
        temperature: data.temperature,
        lengthPenalty: data.lengthPenalty,
        numBeams: data.numBeams,
        repetitionPenalty: data.repetitionPenalty,
        maxMelTokens: data.maxMelTokens,
        personality: data.personality,
      });
      options.onSuccess?.(result.id);
    } catch (error) {
      toast({
        title: 'Generation failed',
        description: error instanceof Error ? error.message : 'Failed to generate audio',
        variant: 'destructive',
      });
    } finally {
      setDownloadingModelName(null);
      setDownloadingDisplayName(null);
    }
  }

  return {
    form,
    handleSubmit,
    isPending: generation.isPending,
  };
}
