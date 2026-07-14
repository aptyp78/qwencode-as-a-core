/**
 * QwenCode as a Core — точка входа
 *
 * Эксперимент: использование @qwen-code/sdk
 * как встраиваемого agent loop для AI Canvas.
 *
 * SDK запускает qwen-code как subprocess и общается через stdin/stdout.
 * Custom tools регистрируются через SDK MCP servers.
 */

import { query, type SDKMessage, type QueryOptions } from '@qwen-code/sdk';

console.log('QwenCode as a Core — эксперимент запущен');
console.log('Версия: 0.1.0');
console.log('Цель: проверить встраиваемость @qwen-code/sdk');

/**
 * Пример 1: Простой запрос к qwen-code через SDK
 */
async function simpleQuery() {
  console.log('\n=== Пример 1: Простой запрос ===');

  const options: QueryOptions = {
    cwd: process.cwd(),
    model: 'qwen3-coder-next',
    permissionMode: 'yolo', // Автоодобрение всех инструментов
    maxSessionTurns: 5,
  };

  const messages = await query({
    prompt: 'Какая сегодня дата?',
    options,
  });

  for await (const message of messages) {
    if (message.type === 'assistant') {
      console.log('Ответ:', message.message.content);
    } else if (message.type === 'result') {
      console.log('Результат:', message.subtype, message.is_error ? 'ошибка' : 'успех');
    }
  }
}

/**
 * Пример 2: Запрос с custom system prompt
 */
async function queryWithSystemPrompt() {
  console.log('\n=== Пример 2: Custom system prompt ===');

  const options: QueryOptions = {
    cwd: process.cwd(),
    model: 'qwen3-coder-next',
    permissionMode: 'yolo',
    systemPrompt: 'Ты — эксперт по анализу документов AI Canvas. Отвечай кратко и по делу.',
  };

  const messages = await query({
    prompt: 'Что такое Universal Representation?',
    options,
  });

  for await (const message of messages) {
    if (message.type === 'assistant') {
      const text = message.message.content
        .filter((block): block is { type: 'text'; text: string } => block.type === 'text')
        .map((block) => block.text)
        .join('');
      console.log('Ответ:', text);
    }
  }
}

/**
 * Пример 3: Запрос с custom permission handler
 */
async function queryWithCustomPermissions() {
  console.log('\n=== Пример 3: Custom permissions ===');

  const options: QueryOptions = {
    cwd: process.cwd(),
    model: 'qwen3-coder-next',
    permissionMode: 'default',
    canUseTool: async (toolName, input, { signal }) => {
      console.log(`[Permission] Tool: ${toolName}, Input:`, input);

      // Автоодобрение read-only инструментов
      if (toolName === 'read_file' || toolName === 'list_directory') {
        return { behavior: 'allow', updatedInput: input };
      }

      // Запрос подтверждения для остальных
      return { behavior: 'deny', message: 'Tool requires manual approval' };
    },
  };

  const messages = await query({
    prompt: 'Покажи содержимое текущей директории',
    options,
  });

  for await (const message of messages) {
    if (message.type === 'assistant') {
      const text = message.message.content
        .filter((block): block is { type: 'text'; text: string } => block.type === 'text')
        .map((block) => block.text)
        .join('');
      console.log('Ответ:', text);
    }
  }
}

/**
 * Главная функция
 */
async function main() {
  try {
    await simpleQuery();
    // await queryWithSystemPrompt();
    // await queryWithCustomPermissions();
  } catch (error) {
    console.error('Ошибка:', error);
    process.exit(1);
  }
}

main();
