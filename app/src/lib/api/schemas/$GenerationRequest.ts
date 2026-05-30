/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export const $GenerationRequest = {
  description: `Request model for voice generation.`,
  properties: {
    profile_id: {
      type: 'string',
      isRequired: true,
    },
    text: {
      type: 'string',
      isRequired: true,
      maxLength: 50000,
      minLength: 1,
    },
    language: {
      type: 'string',
      pattern: '^(zh|en)$',
    },
    seed: {
      type: 'any-of',
      contains: [
        {
          type: 'number',
        },
        {
          type: 'null',
        },
      ],
    },
    model_size: {
      type: 'any-of',
      contains: [
        {
          type: 'string',
          pattern: '^(1\\.7B|0\\.6B|1B|3B)$',
        },
        {
          type: 'null',
        },
      ],
    },
    engine: {
      type: 'string',
      pattern: '^indextts2$',
    },
    emo_audio_prompt: {
      type: 'string',
      maxLength: 1000,
    },
    emo_alpha: {
      type: 'number',
      maximum: 1,
      minimum: 0,
    },
    emo_vector: {
      type: 'array',
      contains: { type: 'number' },
      maxItems: 8,
      minItems: 8,
    },
    use_emo_text: {
      type: 'boolean',
    },
    emo_text: {
      type: 'string',
      maxLength: 1000,
    },
    use_random: {
      type: 'boolean',
    },
    interval_silence: {
      type: 'number',
      maximum: 5000,
      minimum: 0,
    },
    max_text_tokens_per_segment: {
      type: 'number',
      maximum: 500,
      minimum: 20,
    },
  },
} as const;
