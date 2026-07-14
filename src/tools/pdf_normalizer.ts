/**
 * PDF Normalizer — custom tool для AI Canvas
 *
 * Извлекает примитивы из PDF (текст, изображения, векторы)
 * и формирует Universal Representation.
 */

// TODO: Реализация через qwen-code tool interface
// TODO: Интеграция с PyMuPDF или Qwen3-VL

export const pdfNormalizer = {
  name: 'pdf_normalizer',
  description: 'Извлекает примитивы из PDF в Universal Representation',
  parameters: {
    type: 'object',
    properties: {
      file_path: {
        type: 'string',
        description: 'Путь к PDF-файлу'
      }
    },
    required: ['file_path']
  }
};
