# pyFatturaPA
Tool for quick, command-line generation of simple e-Invoice compatible with the Italian-standard, [FatturaPA](https://www.fatturapa.gov.it).

This is a typical, lazy sunday afternoon exercise, aimed at self-generating e-invoices to private companies as an individual freelance consultant.
It is a rudimetary command-line generator of XML e-invoices to be later electronically signed or sealed. It generates a JSON database of clients (with VAT# and full invoicing information). More and more complex invoicing scenarios will be added in future releases.
Due to the validity of such e-invoicing standard being limited to Italian finance, the README continues in Italian.

### Descrizione
Questo tool viene inizialmente impiegato per costituire un database in JSON contenente un elenco essenziale di committenti (ove sono registrate le loro informazioni fiscali quali P.IVA, indirizzo PEC, C.F., ecc.). Il database, chiamato `pyFatturaPA.json`, deve trovarsi nella medesima cartella del tool, così come si consiglia di eseguirlo da tale cartella.

Sempre mediante lo stesso (cfr. sezione **Sintassi**), si possono generare singole fatture elettroniche in formato XML che rispettano lo standard [*FatturaPA* 1.2.1](https://www.fatturapa.gov.it/export/fatturazione/it/normativa/f-2.htm). La sintassi del nome del file generato è `IT`_partitaIVA_`_`_IdProg_`.xml`, cioè combinando il numero di P.IVA emettente e l'identificativo univoco di quella fattura elettronica specifica.

Tali fatture elettroniche sono pronte per essere *firmate* (da parte del cedente/prestatore) ovvero *sigillate elettronicamente* (da parte dell'[Agenzia delle Entrate](https://www.agenziaentrate.gov.it)), per poi essere inviate al [*Sistema di Interscambio* dell'Agenzia delle Entrate](https://ivaservizi.agenziaentrate.gov.it/portale/) stessa e, da li, in conservazione sostitutiva.

### Sintassi
```
pyFatturaPA   consulenza | emetti | committente | inizializza
```
Il tool effettua quattro possibili operazioni:

 `inizializza` inizializza il database JSON (`pyFatturaPA.json`) creandone uno vuoto e inserendovi *una tantum* le sole informazioni del cedente/prestatore, dalle quali viene anche determinato se è soggetto a vati tipi di casse o ritenute.
 
 `committente` permette di aggiungere al database JSON dei fornitori/committenti un'ulteriore voce, che sarà poi indicizzata mediante codice a 3 cifre alfanumeriche. Non è attualmente possibile rimuovere un cessionario/committente.
 
 `emetti` genera una singola fattura con opzioni piuttosto generiche; sono infatti supportate diverse tipologie di fattura/ritenuta/nota, esigibilità, aliquota, condizioni e modalità di pagamento, nonché causali, quantità e unità di misura per voci multiple.
 
 `consulenza` è una versione specializzata del precedente; crea ancor più rapidamente una singola fattura, relativa ad una prestazione senza alcuna cessazione/trasferimento di beni (e.g. una o più voci di consulenza) da parte di un professionista soggetto ad IVA (22%), alla cassa INPS (4%) e a ritenuta d'acconto (-20%). Dopo aver selezionato il committente, è possibile generarla inserendo solo 4 valori.

*test* **test** `basepath` _basepath_
