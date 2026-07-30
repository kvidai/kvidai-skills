#!/usr/bin/env node
/**
 * kvidai-ai — kvid.ai APIM 생성 엔드포인트 래퍼 (기존 kvidai CLI 미포함분).
 *
 * 인증: api-key 헤더 (KVIDAI_API_KEY). 생성 엔드포인트는 credit pool 식별을 위해
 *       body 에 product_code | product_id | email 중 하나 필요 → KVIDAI_USER_EMAIL 사용.
 * base: KVIDAI_BASE_URL (기본 https://api.kvid.ai). Local(api.hometip.net/...clone) 미사용.
 *
 * 커버: voice(TTS) · stt(speech-to-text) · talk(talk-v2v 립싱크) · edit(ai-edit)
 *   (image / video t2v 는 `kvidai` CLI 가 이미 제공 → 여기서 제외)
 *
 * Usage:
 *   node kvidai-ai-client.mjs voice --text "..." [--voice-id X] [--model-id X] [--lang ko] [--speed 1.0] [--out a.mp3]
 *   node kvidai-ai-client.mjs voices            # 사용 가능한 voice 목록
 *   node kvidai-ai-client.mjs models            # 사용 가능한 TTS 모델 목록
 */

import fs from 'node:fs';

const API_KEY = process.env.KVIDAI_API_KEY;
const BASE_URL = process.env.KVIDAI_BASE_URL || 'https://api.kvid.ai';
const EMAIL = process.env.KVIDAI_USER_EMAIL; // credit pool 식별자 (email 경로)

if (!API_KEY) {
  console.error('KVIDAI_API_KEY 환경변수가 필요합니다.');
  process.exit(1);
}

const log = (...a) => console.error('[kvidai-ai]', ...a);

function headers() {
  return { 'api-key': API_KEY, 'Content-Type': 'application/json' };
}

async function req(method, path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json;
  try { json = text ? JSON.parse(text) : null; } catch { json = text; }
  if (!res.ok) {
    console.error(`${method} ${path} → ${res.status}`);
    if (json) console.error(JSON.stringify(json, null, 2));
    process.exit(1);
  }
  return json;
}

// --flag value 파서
function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
      out[key] = val;
    }
  }
  return out;
}

function creditId(body = {}) {
  if (process.env.KVIDAI_PRODUCT_CODE) return { ...body, product_code: process.env.KVIDAI_PRODUCT_CODE };
  if (process.env.KVIDAI_PRODUCT_ID) return { ...body, product_id: process.env.KVIDAI_PRODUCT_ID };
  if (EMAIL) return { ...body, email: EMAIL };
  console.error('credit 식별자 필요: KVIDAI_USER_EMAIL 또는 KVIDAI_PRODUCT_CODE/ID 설정');
  process.exit(1);
}

async function download(url, outPath) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download ${res.status}: ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(outPath, buf);
}

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

// ── voice (TTS) ────────────────────────────────────────────────────────────
// submit → poll(voice status) → result. result_url(mp3) + duration_seconds + alignment.

async function voice(args) {
  if (!args.text) { console.error('voice: --text 필요'); process.exit(1); }
  const body = creditId({
    text: String(args.text),
    voice_id: args['voice-id'] || 'pNInz6obpgDQGcFmaJgB',
    model_id: args['model-id'] || 'eleven_multilingual_v2',
    ...(args.lang ? { language_code: String(args.lang) } : {}),
    output_format: args.format || 'mp3_44100_128',
    ...(args.speed ? { voice_settings: { speed: Number(args.speed) } } : {}),
  });

  const submit = await req('POST', '/ai/generation/voice/text-to-speech/generate-async', body);
  const jobId = submit?.data?.job_id ?? submit?.job_id;
  if (!jobId) { console.error('job_id 없음:', JSON.stringify(submit)); process.exit(1); }
  log(`voice job ${jobId} — polling...`);

  const start = Date.now();
  while (true) {
    const st = await req('GET', `/ai/generation/voice/status?jobId=${encodeURIComponent(jobId)}`);
    const status = String(st?.data?.status ?? st?.status ?? '');
    log(`  [${Math.round((Date.now() - start) / 1000)}s] ${status}${st?.data?.progress != null ? ` ${st.data.progress}%` : ''}`);
    if (/completed/i.test(status)) break;
    if (/failed|error/i.test(status)) { console.error('voice 실패:', JSON.stringify(st)); process.exit(1); }
    if (Date.now() - start > 5 * 60 * 1000) { console.error('voice timeout'); process.exit(1); }
    await sleep(3000);
  }

  const result = await req('GET', `/ai/generation/voice/result?jobId=${encodeURIComponent(jobId)}`);
  const d = result?.data ?? result;
  if (args.out && d.result_url) {
    await download(d.result_url, String(args.out));
    log(`saved ${args.out} (${d.duration_seconds}s)`);
  }
  // stdout = 결과 JSON (result_url, duration_seconds, alignment, out)
  console.log(JSON.stringify({ result_url: d.result_url, duration_seconds: d.duration_seconds, alignment: d.alignment, out: args.out || null }, null, 2));
}

// ── voices / models 목록 ─────────────────────────────────────────────────────
async function voices() { console.log(JSON.stringify(await req('GET', '/ai/generation/voice/voices'), null, 2)); }
async function models() { console.log(JSON.stringify(await req('GET', '/ai/generation/voice/models'), null, 2)); }

// ── stt (speech-to-text) — 동기. --url(CDN) 또는 --file(업로드) ────────────────
async function stt(args) {
  const model = args['model-id'] || 'scribe_v1';
  const gran = args.granularity || 'word';
  let json;
  if (args.file) {
    // multipart 업로드 (Content-Type 는 fetch 가 boundary 포함해 자동 설정 — 수동 지정 금지)
    const { basename } = await import('node:path');
    const fd = new FormData();
    fd.append('file', new Blob([fs.readFileSync(String(args.file))]), basename(String(args.file)));
    fd.append('model_id', model);
    fd.append('timestamps_granularity', gran);
    if (args.lang) fd.append('language_code', String(args.lang));
    if (args.diarize != null) fd.append('diarize', String(args.diarize));
    const res = await fetch(`${BASE_URL}/ai/speech-to-text`, { method: 'POST', headers: { 'api-key': API_KEY }, body: fd });
    const t = await res.text();
    if (!res.ok) { console.error(`stt ${res.status}: ${t}`); process.exit(1); }
    json = JSON.parse(t);
  } else if (args.url) {
    // JSON (CDN URL). api.kvid.ai 는 api-key 로 owner/email 주입 → body email 불필요.
    json = await req('POST', '/ai/speech-to-text', {
      cloud_storage_url: String(args.url), model_id: model, timestamps_granularity: gran,
      ...(args.lang ? { language_code: String(args.lang) } : {}),
    });
  } else {
    console.error('stt: --url <cdnUrl> 또는 --file <path> 필요'); process.exit(1);
  }
  console.log(JSON.stringify(json, null, 2));
}

// ── edit (ai-edit) — SSE. summary | silence-cut | shorts ───────────────────────
async function edit(sub, args) {
  if (!['summary', 'silence-cut', 'shorts'].includes(sub)) { console.error('edit: summary|silence-cut|shorts'); process.exit(1); }
  if (!args.url) { console.error('edit: --url <mediaUrl> 필요'); process.exit(1); }
  const body = { mediaUrl: String(args.url) };
  if (sub === 'summary') {
    if (args.instruction) body.instruction = String(args.instruction);
    if (args.mode) body.mode = String(args.mode);
  } else if (sub === 'silence-cut') {
    for (const k of ['mode', 'thresholdDb', 'minDuration', 'keepSilence']) {
      if (args[k] != null && args[k] !== true) body[k] = isNaN(Number(args[k])) ? args[k] : Number(args[k]);
    }
  }
  const res = await fetch(`${BASE_URL}/ai-edit/${sub}`, {
    method: 'POST', headers: headers(), body: JSON.stringify(body), signal: AbortSignal.timeout(20 * 60 * 1000),
  });
  if (!(res.headers.get('content-type') || '').includes('event-stream')) {
    console.error('rejected:', JSON.stringify(await res.json())); process.exit(1);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let event = '', done = null;
  while (true) {
    const { done: fin, value } = await reader.read();
    if (fin) break;
    for (const line of dec.decode(value, { stream: true }).split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7).trim();
      else if (line.startsWith('data: ') && event) {
        try {
          const p = JSON.parse(line.slice(6));
          if (event === 'error') { console.error('error:', JSON.stringify(p)); process.exit(1); }
          if (event === 'done') done = p.data ?? p;
          else log(event);
        } catch { /* non-JSON */ }
      }
    }
  }
  if (sub === 'silence-cut' && args.out && done?.outputUrl) { await download(done.outputUrl, String(args.out)); log(`saved ${args.out}`); }
  console.log(JSON.stringify(done, null, 2));
}

// ── CLI ──────────────────────────────────────────────────────────────────────
const [cmd, ...rest] = process.argv.slice(2);
switch (cmd) {
  case 'voice': await voice(parseArgs(rest)); break;
  case 'voices': await voices(); break;
  case 'models': await models(); break;
  case 'stt': await stt(parseArgs(rest)); break;
  case 'edit': await edit(rest[0], parseArgs(rest.slice(1))); break; // edit <summary|silence-cut|shorts> --url ...
  default:
    console.error('usage: kvidai-ai-client.mjs <cmd> [--flags]');
    console.error('  voice  --text "..." [--voice-id X --lang ko --speed 1.1 --out a.mp3]');
    console.error('  stt    --url <cdnUrl> | --file <path> [--lang ko]');
    console.error('  edit   summary --url <mediaUrl> --instruction "..." [--mode overview]');
    console.error('  edit   silence-cut --url <mediaUrl> [--out out.mp4]');
    console.error('  edit   shorts --url <mediaUrl>');
    console.error('  voices | models');
    console.error('  (talk-v2v 는 서비스 미제공 — 제외)');
    process.exit(1);
}
