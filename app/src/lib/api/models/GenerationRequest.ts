/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for voice generation.
 */
export type GenerationRequest = {
  profile_id: string;
  text: string;
  language?: string;
  seed?: number | null;
  model_size?: string | null;
  instruct?: string | null;
  engine?: 'indextts2' | null;
  emo_audio_prompt?: string | null;
  emo_alpha?: number | null;
  emo_vector?: Array<number> | null;
  use_emo_text?: boolean;
  emo_text?: string | null;
  use_random?: boolean;
  interval_silence?: number | null;
  max_text_tokens_per_segment?: number | null;
  top_p?: number | null;
  top_k?: number | null;
  temperature?: number | null;
  length_penalty?: number | null;
  num_beams?: number | null;
  repetition_penalty?: number | null;
  max_mel_tokens?: number | null;
};
