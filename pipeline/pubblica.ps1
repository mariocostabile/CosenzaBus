# Build dei dati CORe e pubblicazione su Pages. Uso (PowerShell 7, dalla cartella del repo): pwsh -File pipeline/pubblica.ps1
# Va lanciato da un IP italiano: CORe blocca le porte 8083/8801 ai datacenter USA (runner GitHub).
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
Set-Location (Split-Path $PSScriptRoot)

python -m unittest discover -s pipeline/tests
python pipeline/build.py site/data  # esce con 1 se la validazione fallisce: niente pubblicazione
if ((Get-Content site/data/.cambiata) -ne "1") { Write-Host "Dati invariati: niente da pubblicare."; exit 0 }
Remove-Item site/data/.cambiata
'<!doctype html><meta charset="utf-8"><title>CosenzaBus</title><p>Dati: <a href="data/index.json">data/index.json</a></p>' | Set-Content -Encoding utf8 site/index.html

# un solo commit, sovrascritto ogni volta: la storia del branch `dati` non cresce
$origin = git remote get-url origin
Push-Location site
try {
    if (Test-Path .git) { Remove-Item -Recurse -Force .git }
    git init -q -b dati
    git add -A
    git commit -q -m "dati $(Get-Date -Format s)"
    git push -q -f $origin dati
} finally { Pop-Location }
gh workflow run pages.yml --ref main
Write-Host "Pubblicazione avviata: gh run list --workflow pages.yml"
