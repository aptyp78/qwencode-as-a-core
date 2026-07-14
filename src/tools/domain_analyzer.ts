/**
 * Domain Analyzer — custom tool для AI Canvas
 *
 * Определяет домен документа через Activity Theory (SMD-методология).
 * Домен emergent — не predefined.
 */

export const domainAnalyzer = {
  name: 'domain_analyzer',
  description: 'Определяет домен документа через Activity Theory',
  parameters: {
    type: 'object',
    properties: {
      universal_representation: {
        type: 'object',
        description: 'Universal Representation из pdf_normalizer'
      }
    },
    required: ['universal_representation']
  }
};
