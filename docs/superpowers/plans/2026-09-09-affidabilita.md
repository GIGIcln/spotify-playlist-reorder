# Affidabilità del riordino

Ambito approvato: protezione da modifiche concorrenti, backup robusti, esiti delle automazioni. Conservare CLI e criteri attuali.

1. Test iniziali: 118 passano nell'ambiente spotify-env; pytest installato come dipendenza di sviluppo.
2. Lettura coerente: leggere snapshot prima/dopo tutte le pagine; rifiutare letture cambiate. Confrontare snapshot prima di ogni spostamento e verificare contenuto finale, includendo elementi esclusi e date di aggiunta. Non ripetere scritture su errori 5xx dall'esito incerto; consentire retry 429.
3. Backup v2: salvare identità di tutti gli elementi e ordine filtrato con scrittura atomica e nomi univoci. Validare JSON prima dell'auth; mantenere backup legacy per sole playlist senza elementi esclusi. Rifiutare differenze nel contenuto.
4. Automazioni: restituire esiti espliciti, proseguire il batch dopo un errore per playlist e terminare con codice 1 se almeno una fallisce. Non avviare login manuale con --no-browser.
5. Verifica: test prima delle modifiche per conflitti, risposte ambigue, backup incompleto/corrotto, batch parzialmente fallito; poi suite completa e verifica diff. Nessuna chiamata alle playlist reali.

Limite: Spotify non offre una transazione su più spostamenti. Un errore può lasciare un ordine parziale; fermarsi e segnalarlo, senza rollback automatico. I controlli aumentano le letture API.
