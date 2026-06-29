# Free Sourcing Tools — Meetup Pipeline

Outil de sourcing **100 % côté client** (un seul fichier HTML, aucun backend) qui transforme
les participants d'un groupe Meetup en une liste de prospects LinkedIn scorés.

Construit à l'origine pour le cabinet **Anara**. Ce dépôt est une **passation** : tout est
fonctionnel tel quel, mais le design (charte Anara) est destiné à être **remplacé** pour une
intégration sur un autre site, en particulier **Astro**.

---

## 1. Ce que fait l'outil

Pipeline en 4 phases, exécuté entièrement dans le navigateur :

```
[Scraper Meetup]  →  Phase 1        →  Phase 2          →  Phase 3            →  Phase 4
 bookmarklet /       Import CSV +       Recherche Google     Scoring IA            Export XLSX
 extension Chrome     filtrage          (Serper, site:        (Gemini Flash :       (2 fichiers :
 → CSV participants                     linkedin.com/in)      pertinence du         best_profiles +
                                        top 10 / membre       profil vs membre)     all_scores)
```

1. **Scraper Meetup** (intégré dans la page) — récupère, via l'API GraphQL interne de Meetup
   (`/gql2`), tous les participants des événements passés d'un groupe. Livré sous deux formes :
   un **bookmarklet** et un **générateur d'extension Chrome** (ZIP téléchargeable). Sortie : un CSV.
2. **Phase 1 — Import & filtrage** : on charge le CSV, on filtre (ex. nombre d'événements
   suivis, no-shows) et on prévisualise.
3. **Phase 2 — Recherche** : pour chaque membre, requête `site:linkedin.com/in "Nom" <mot-clé>`
   via l'API **Serper** (Google Search). Récupère le top 10 des résultats LinkedIn.
4. **Phase 3 — Scoring IA** : **Gemini Flash** note la correspondance entre chaque résultat
   LinkedIn et le membre Meetup (contexte de l'événement inclus).
5. **Phase 4 — Export** : deux fichiers XLSX générés simultanément —
   `best_profiles_AAAA-MM-JJ.xlsx` (1 ligne / membre, le meilleur match) et
   `all_scores_AAAA-MM-JJ.xlsx` (jusqu'à 10 lignes / membre, colonne `is_best`).

Détails d'implémentation clés :
- **Accordéon verrouillé** : chaque phase se déverrouille (`unlockPhase(id)`) à la fin de la
  précédente. Pas d'`onclick` inline sur les en-têtes — délégation via `querySelectorAll('.phase-header')`.
- **Bilingue FR/EN** : un toggle change la langue de recherche (`fr.linkedin.com/in` vs
  `linkedin.com/in`) et les libellés (`applyTranslations()`). Langue stockée en localStorage.

---

## 2. Fichiers du dépôt

| Fichier | Rôle | À garder ? |
|---|---|---|
| `meetup-pipeline.html` | **L'outil complet** (UI + logique + scraper embarqué). C'est LE livrable. | ✅ cœur du projet |
| `search-worker.js` | Worker Cloudflare — proxy CORS **optionnel** pour Serper. | ⚠️ seulement si CORS bloque (voir §5) |
| `wrangler.toml` | Config de déploiement du worker Cloudflare. | ⚠️ idem |
| `proxy-local.py` | Proxy CORS local (Python, sans dépendance) pour tester en dev. | ⚠️ dev uniquement |
| `meetup1-scraper.html` | Ancienne page autonome du scraper (design bleu générique). **Redondant** : le scraper est déjà embarqué dans `meetup-pipeline.html`. | 🗑️ legacy, ignorable |

---

## 3. Clés API nécessaires (fournies par l'utilisateur)

Aucune clé n'est en dur dans le code. Chaque utilisateur saisit les siennes dans la barre du
haut ; elles sont stockées en **localStorage** (jamais envoyées ailleurs que vers l'API concernée).

| Service | À quoi ça sert | Où l'obtenir | Quota gratuit |
|---|---|---|---|
| **Serper** | Recherche Google (Phase 2) | https://serper.dev | ~2 500 requêtes offertes |
| **Google Gemini** | Scoring des profils (Phase 3) | https://aistudio.google.com/apikey | 15 req/min (free tier) |

Clés localStorage utilisées : `serper_key`, `gemini_key`, `search_lang`.

> ⚠️ Le scraper Meetup **n'utilise aucune clé** : il s'appuie sur la session Meetup connectée
> de l'utilisateur (cookies, `credentials: 'include'`). Il doit donc être exécuté depuis un
> onglet où l'utilisateur est loggué sur meetup.com.

---

## 4. Constantes de configuration (dans `meetup-pipeline.html`)

| Constante | Ligne (≈) | Valeur par défaut | Note |
|---|---|---|---|
| `SERPER_URL` | ~816 | `https://google.serper.dev/search` | Appel **direct** à Serper. Remplacer par l'URL du worker si CORS pose problème. |
| `GEMINI_URL` | ~1085 | `…/models/gemini-2.5-flash:generateContent` | Modèle Gemini utilisé. |
| `GEMINI_DELAY` | ~1086 | `4200` (ms) | Délai entre appels Gemini pour respecter 15 req/min. |

> Les numéros de ligne sont indicatifs (« ≈ ») — cherche les noms de constantes, c'est plus fiable.

---

## 5. CORS — quand le worker / proxy sont nécessaires

Par défaut, l'outil appelle **Serper directement** depuis le navigateur. Serper autorise
généralement le CORS, donc **dans la plupart des cas tu n'as besoin ni du worker ni du proxy**.

Si tu rencontres une erreur CORS sur Serper :

- **En prod** : déploie `search-worker.js` sur Cloudflare Workers (gratuit), puis remplace
  `SERPER_URL` dans le HTML par l'URL du worker. Le worker ne stocke aucun secret : il relaie
  la clé fournie par chaque utilisateur via l'en-tête `X-API-KEY`.
  ```
  npx wrangler deploy        # nécessite un compte Cloudflare + wrangler.toml
  ```
- **En local (dev)** : lance le proxy Python et pointe `SERPER_URL` dessus.
  ```
  python proxy-local.py      # écoute sur http://localhost:8787
  ```
  Puis dans le HTML : `const SERPER_URL = 'http://localhost:8787';`

Gemini, lui, est appelé directement (pas de souci CORS connu).

---

## 6. Le design à remplacer (pour intégration Astro)

Tout le design vit dans **un seul bloc `<style>`** de `meetup-pipeline.html`, lignes **≈13 à 293**.
Il est entièrement piloté par des **tokens CSS** (variables) regroupés dans `:root` (lignes ≈14-33) :

```css
:root {
  --cream:  #f1ebde;  --ink: #131310;   --mustard: #c89438;  --brick: #a8392a;  /* couleurs Anara */
  --display: "Bricolage Grotesque", …;  --serif: "EB Garamond", …;  --mono: "JetBrains Mono", …;  /* polices */
}
```

Les polices sont importées via Google Fonts (ligne ≈9, balise `<link>`).

### Stratégie de re-skin recommandée

La logique (le `<script>`, lignes ≈435-1388) est **totalement indépendante du design**. Pour
réintégrer sur un autre site :

1. **Option simple (rester en HTML/tokens)** : ne change que les valeurs dans `:root` + l'import
   de polices. Tu gardes la même structure, look instantanément différent.
2. **Option Astro (recommandée pour ton cas)** :
   - Crée une page `meetup-pipeline.astro`.
   - Copie le **markup** (le `<body>`, lignes ≈297-433) dans le template Astro.
   - Mets ta **propre CSS / ton design system** à la place du bloc `<style>` Anara — garde les
     **noms de classes** (`.phase`, `.phase-header`, `.api-bar`, `.btn`, etc.) OU renomme-les
     partout (CSS + markup), au choix.
   - Copie le `<script>` tel quel dans un bloc `<script>` Astro (ou un `.js` importé). **Ne le
     mets pas en `type="module"` sans vérifier** : il utilise des fonctions globales appelées
     depuis le markup (`unlockPhase`, `setSearchLang`, etc.).
   - Garde les 3 `<script src>` CDN (PapaParse, SheetJS/xlsx, JSZip) — ou installe-les en npm
     et adapte les imports.
   - Attention : le générateur d'extension Chrome embarque un mini-CSS inline (lignes ≈1349+) et
     une icône base64 — c'est indépendant du design de la page, à laisser tel quel.

> ⚠️ Pièges connus (vécus sur le projet Anara) :
> - Les en-têtes de phase utilisent la **délégation d'événements**, pas d'`onclick` inline.
>   Si tu refactores le markup, garde la classe `.phase-header` ou adapte le sélecteur.
> - Certaines couleurs sont référencées **en dur dans le JS** (ex. `var(--brick)`,
>   `var(--mustard)` injectés via `style.background`). Si tu renommes les tokens, fais un
>   rechercher/remplacer dans le `<script>` aussi.

---

## 7. Dépendances externes (CDN)

Chargées via `<script src>` dans le `<head>` :

- [PapaParse 5.4.1](https://www.papaparse.com/) — parsing CSV
- [SheetJS / xlsx 0.18.5](https://sheetjs.com/) — génération XLSX
- [JSZip 3.10.1](https://stuk.github.io/jszip/) — génération du ZIP de l'extension Chrome

Aucune autre dépendance. Pas de build, pas de serveur : ouvrir le HTML dans un navigateur suffit.

---

## 8. Démarrage rapide (pour tester en l'état)

1. Ouvre `meetup-pipeline.html` dans Chrome.
2. Saisis tes clés Serper + Gemini dans la barre du haut.
3. Section scraper : glisse le bookmarklet dans tes favoris (ou installe l'extension générée),
   va sur la page d'un groupe Meetup (connecté), lance-le → tu obtiens un CSV.
4. Phase 1 : importe ce CSV, filtre, valide.
5. Phase 2 : lance la recherche LinkedIn (Serper).
6. Phase 3 : lance le scoring (Gemini).
7. Phase 4 : exporte les deux XLSX.

---

## Licence / usage

Outil interne de sourcing. Respecter les CGU de Meetup, LinkedIn, Serper et Google,
ainsi que le RGPD pour le traitement des données personnelles des participants.
