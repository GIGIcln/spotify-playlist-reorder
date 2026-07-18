# Skill per questo repo

Guida di riferimento: quali skill installare per lavorare su questo tool con il coding agent, e come scaricarle su Mac e su Windows.

## 0. Prerequisito: Node.js (serve per il comando `npx`)

- **Mac**: `brew install node` (oppure installer da https://nodejs.org)
- **Windows**: installer da https://nodejs.org oppure `winget install OpenJS.NodeJS` (PowerShell)

## 1. Nessuna skill di progetto specifica necessaria

Questo repo è un CLI Python "normale" (spotipy + pytest + GitHub Actions già configurata): non esiste una skill di stack dedicata che valga la pena committare qui. Bastano le skill di base sotto — in particolare `tdd` e `setup-pre-commit`, utili perché il repo ha già test e CI ma **manca un pre-commit config**.

## 2. Skill di base consigliate (personali, da installare su ogni macchina)

Vanno nella cartella skill globale (fuori da qualsiasi progetto), quindi da installare una volta su ogni macchina con il flag `-g`:

```
npx skills add obra/superpowers -g
npx skills add mattpocock/skills -g
```

| Sistema | Dove finiscono |
|---|---|
| Mac | `~/.claude/skills/` |
| Windows | `%USERPROFILE%\.claude\skills\` (es. `C:\Users\<tuo-utente>\.claude\skills\`) |

Se dopo l'installazione il CLI non le vede, controlla quella cartella: alcune versioni le mettono invece in `~/.agents/skills/` e vanno spostate a mano.

Per questo repo userai soprattutto: `test-driven-development`, `systematic-debugging` (da `superpowers`) e `tdd`, `setup-pre-commit`, `diagnosing-bugs` (da `mattpocock/skills`).
