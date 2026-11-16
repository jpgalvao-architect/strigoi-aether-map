# SPDX-License-Identifier: GPL-3.0-only
$ErrorActionPreference = 'Stop'
$site = Join-Path (Split-Path -Parent $PSScriptRoot) 'website'
$articles = foreach ($edition in @(
    @{ Locale = 'pt_BR'; Lang = 'pt-BR'; File = 'live-sync.md' },
    @{ Locale = 'en_US'; Lang = 'en-US'; File = 'live-sync.en-US.md' },
    @{ Locale = 'es-419'; Lang = 'es-419'; File = 'live-sync.es-419.md' }
)) {
    $html = (ConvertFrom-Markdown -LiteralPath (Join-Path $site $edition.File)).Html.TrimEnd()
    $html = $html.Replace(' id="', (' id="' + $edition.Locale + '-'))
    $hidden = if ($edition.Locale -ne 'pt_BR') { ' hidden' } else { '' }
    '<article class="legal-document live-guide" lang="{0}" data-legal-language="{1}"{2}>{3}</article>' -f $edition.Lang,$edition.Locale,$hidden,$html
}
$page = @'
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0b0e18">
  <meta name="description" content="Configure o Live Sync no Azphelumbra, hospede sessões na sua conta Cloudflare e compartilhe a estratégia de Lower Reshanta.">
  <link rel="canonical" href="https://jpgalvao-architect.github.io/strigoi-aether-map/live-sync.html">
  <link rel="icon" href="assets/favicon.ico">
  <link rel="stylesheet" href="styles.css?v=es419">
  <script src="site.js?v=live-sync" defer></script>
  <title>Live Sync — Guia de configuração do Azphelumbra</title>
  <style>
    .live-guide h1 { margin: 0 0 22px; }
    .live-guide h3 { font-size: 16px; margin-top: 22px; }
    .live-guide p, .live-guide li { font-size: 14px; line-height: 1.7; }
    .live-guide ol, .live-guide ul { padding-left: 24px; }
    .live-guide li + li { margin-top: .6em; }
    .live-guide a { color: var(--aqua); text-decoration: underline; }
    .live-guide code { overflow-wrap: anywhere; }
    .live-guide img { display: block; max-width: 100%; height: auto; margin-block: 18px; border-radius: 8px; }
  </style>
</head>
<body data-page="live-sync">
  <a class="skip-link" href="#main" data-i18n="skip">Ir para o conteúdo</a>
  <header class="site-header"><div class="container nav-row">
    <a class="brand" href="index.html"><img src="assets/azphelumbra-emblem.webp" width="48" height="48" alt=""><span>AZPHELUMBRA<small>AION 2 COMPANION</small></span></a>
    <div class="nav-actions"><div class="languages" aria-label="Idioma" data-i18n-aria="language">
      <button type="button" data-language="pt_BR" lang="pt-BR" aria-label="Português (Brasil)" aria-pressed="true">PT</button>
      <button type="button" data-language="en_US" lang="en-US" aria-label="English (United States)" aria-pressed="false">EN</button>
      <button type="button" data-language="es-419" lang="es-419" aria-label="Español (Latinoamérica)" aria-pressed="false">ES</button>
    </div></div>
  </div></header>
  <main id="main" class="container legal-main">
    <a class="legal-back" href="guide.html" data-i18n="live.back">← Guia do Azphelumbra</a>
__ARTICLE__
  </main>
</body>
</html>
'@
Set-Content -LiteralPath (Join-Path $site 'live-sync.html') -Value $page.Replace('__ARTICLE__', ($articles -join [Environment]::NewLine)) -Encoding utf8NoBOM
