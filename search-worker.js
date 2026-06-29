/**
 * Cloudflare Worker — proxy CORS pour Serper Google Search API
 *
 * Déploiement :
 *   1. Cloudflare Dashboard → Workers & Pages → Create Worker
 *   2. Coller ce code, cliquer Deploy
 *   3. Copier l'URL du Worker (ex. anara-search.moncompte.workers.dev)
 *   4. Dans meetup-pipeline.html, remplacer SERPER_URL par cette URL
 *
 * Chaque utilisateur fournit sa propre clé Serper via le header X-API-KEY.
 * Ce Worker ne stocke aucun secret.
 */

const SERPER_URL = 'https://google.serper.dev/search';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-API-KEY',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: CORS_HEADERS });
    }

    const apiKey = request.headers.get('X-API-KEY');
    if (!apiKey) return json({ error: 'Missing X-API-KEY header' }, 401);

    const body = await request.text();

    let resp;
    try {
      resp = await fetch(SERPER_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-KEY':    apiKey,
        },
        body,
      });
    } catch (err) {
      return json({ error: `Network error: ${err.message}` }, 502);
    }

    const result = await resp.text();
    return new Response(result, {
      status: resp.status,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  },
};

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
