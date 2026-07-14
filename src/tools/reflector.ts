/**
 * Reflector — custom tool для AI Canvas
 *
 * Оценивает качество результата через confidence-gated escalation.
 * Если confidence < tau → повторный проход с уточнением.
 */

export const reflector = {
  name: 'reflector',
  description: 'Оценивает качество и принимает решение о повторном проходе',
  parameters: {
    type: 'object',
    properties: {
      result: {
        type: 'object',
        description: 'Результат анализа'
      },
      threshold: {
        type: 'number',
        description: 'Порог confidence (tau)',
        default: 0.8
      }
    },
    required: ['result']
  }
};
