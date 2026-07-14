import { describe, it, expect } from 'vitest';
import { pdfNormalizer } from '../src/tools/pdf_normalizer';
import { domainAnalyzer } from '../src/tools/domain_analyzer';
import { reflector } from '../src/tools/reflector';

describe('Custom Tools', () => {
  it('pdf_normalizer имеет корректную схему', () => {
    expect(pdfNormalizer.name).toBe('pdf_normalizer');
    expect(pdfNormalizer.parameters.required).toContain('file_path');
  });

  it('domain_analyzer имеет корректную схему', () => {
    expect(domainAnalyzer.name).toBe('domain_analyzer');
    expect(domainAnalyzer.parameters.required).toContain('universal_representation');
  });

  it('reflector имеет корректную схему', () => {
    expect(reflector.name).toBe('reflector');
    expect(reflector.parameters.required).toContain('result');
  });
});
