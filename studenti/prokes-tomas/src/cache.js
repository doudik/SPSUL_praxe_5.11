import fs from 'node:fs';
import crypto from 'node:crypto';

function cacheKey(model, prompt, input) {
  return crypto.createHash('sha256').update(model + '|' + prompt + '|' + input).digest('hex');
}

export function cacheGet(model, prompt, input) {
  const file = `cache/${cacheKey(model, prompt, input)}.json`;
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf-8')) : null;
}

export function cacheSet(model, prompt, input, data) {
  fs.mkdirSync('cache', { recursive: true });
  fs.writeFileSync(`cache/${cacheKey(model, prompt, input)}.json`, JSON.stringify(data));
}
