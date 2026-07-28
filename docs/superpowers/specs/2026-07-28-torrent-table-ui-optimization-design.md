# Specifica Tecnica: Ottimizzazione Interfaccia Tabella Torrent e Icone Pulsanti

* **Data**: 2026-07-28
* **Stato**: In Revisione
* **Autore**: Antigravity & Michele

---

## 1. Obiettivo & Contesto

Attualmente, nella pagina di monitoraggio dei torrent (`/torrents`), la tabella contenente l'elenco dei torrent aggiunti o in elaborazione può subire fenomeni di overflow orizzontale, uscendo dallo schermo. Questo è dovuto principalmente alla presenza di testi molto lunghi (come i titoli originali dei torrent e i codici info_hash completi) e all'ingombro dei pulsanti di azione ("Riprova", "Modifica", "File", "Elimina") che contengono etichette testuali estese.

### Obiettivo principale:
Rendere l'interfaccia utente della tabella più compatta, leggibile e responsive tramite:
1. Integrazione globale di **FontAwesome 6 Free** per sostituire il testo dei pulsanti di azione all'interno della tabella con icone intuitive dotate di tooltip.
2. Contenimento e troncamento controllato (tramite ellissi `...`) dei titoli e dei codici hash.
3. Introduzione di uno scorrimento orizzontale come fallback elastico solo per la tabella tramite contenitore responsive.

---

## 2. Modifiche ai File di Progetto

### 2.1 Integrazione FontAwesome in `base.html`
File: [base.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/base.html)
Inserimento del link alla CDN di FontAwesome 6 Free nella sezione `<head>`:

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

### 2.2 Aggiornamento di `torrents.html`
File: [torrents.html](file:///Users/michele/PycharmProjects/stremio-catalog-provider/templates/torrents.html)

* Avvolgimento della tabella `.torrent-table` in un tag `div` con classe `table-responsive`.
* Assegnazione delle classi CSS alle intestazioni (`<th>`) e alle celle (`<td>`):
  * **Titolo**: classe `.col-title`
  * **Hash**: classe `.col-hash`
  * **Azioni**: classe `.col-actions`
* Sostituzione del testo dei pulsanti con le icone FontAwesome e aggiunta di `title` per l'accessibilità:
  * Pulsante "Riprova" -> `title="Riprova"` con `<i class="fa-solid fa-rotate-right"></i>`
  * Pulsante "Modifica" (torrent) -> `title="Modifica"` con `<i class="fa-solid fa-pen-to-square"></i>`
  * Pulsante "File" -> `title="Mostra File"` con `<i class="fa-solid fa-folder-open"></i>`
  * Pulsante "Elimina" -> `title="Elimina"` con `<i class="fa-solid fa-trash-can"></i>`
* Sostituzione del pulsante "Modifica" generato via JS nella lista dei mapping dei file:
  * Pulsante "Modifica" (file mapping) -> `title="Modifica Mapping"` con `<i class="fa-solid fa-pen-to-square"></i>`
* Il pulsante **"Aggiungi"** della card superiore per l'inserimento dei magnet generici **rimarrà testuale** per preservare la chiarezza dell'azione principale.

### 2.3 Aggiornamento degli Stili in `style.css`
File: [style.css](file:///Users/michele/PycharmProjects/stremio-catalog-provider/static/css/style.css)

Aggiunta e aggiornamento delle definizioni CSS per la tabella dei torrent:

```css
/* Contenitore responsive per consentire lo scorrimento orizzontale in extremis */
.table-responsive {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-top: 15px;
}

/* Riduzione di padding e font-size per ottimizzare lo spazio */
.torrent-table th, .torrent-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
    vertical-align: middle;
}

.torrent-table th {
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 13px;
}

.torrent-table td {
    font-size: 14px;
}

/* Troncamento dei testi lunghi con ellissi (...) */
.col-title {
    max-width: 280px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.col-hash {
    max-width: 160px;
}

.col-hash code {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
    background: rgba(255, 255, 255, 0.05);
    padding: 4px 8px;
    border-radius: 6px;
}

/* Previene il wrapping dei pulsanti di azione */
.col-actions {
    width: 1%;
    white-space: nowrap;
}

.col-actions .btn {
    padding: 8px 12px; /* Pulsanti leggermente più compatti in tabella */
}
```

---

## 3. Strategia di Test & Validazione

1. **Test di Visualizzazione**:
   * Caricare la pagina `/torrents` e verificare che nessuna parte della tabella provochi la comparsa di scrollbars generali sul body.
   * Ridurre manualmente le dimensioni della finestra del browser per simulare dispositivi tablet e mobili, accertandosi che la tabella si contragga correttamente e che l'overflow rimanga limitato al solo contenitore `.table-responsive`.
2. **Test di Usabilità**:
   * Passare il mouse sopra le icone di azione per verificare che compaiano i corretti tooltip (`title`).
3. **Test di Funzionalità**:
   * Cliccare su ciascuno dei pulsanti iconici per verificare che il comportamento javascript o il redirect (Modifica, Riprova, Elimina, Espansione File) continui a funzionare esattamente come prima.
