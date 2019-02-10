# coding=utf-8
##########################################################
#  pyFatturaPA                                           #
#--------------------------------------------------------#
#   Quick generation of FatturaPA eInvoice XML files !   #
#--------------------------------------------------------#
#    Copyright (C) 2019 Walter Arrighetti, PhD, CISSP    #
#    All Rights Reserved.                                #
#    coding by: Walter Arrighetti                        #
#               <walter.arrighetti@agid.gov.it>          #
#  < https://github.com/walter-arrighetti/pyFatturaPA >  #
#                                                        #
##########################################################
import datetime
import os.path
import json
import sys
import re

__VERSION = "0.1"
CONF_FILE = "pyFatturaPA.conf"


def check_config():
	try:	os.path.exists(CONF_FILE)
	except:	return create_config()
	return True

def enter_org_data():
	print('\n')
	answer = input("P.IVA individuale? [S]ì/[N]o ")
	if answer and answer.lower()[0]=='n':	orgname = input("Ragione sociale:  ")
	else:	orgname = tuple([input("Nome:  "), input("Cognome:  ")])
	VATit = input("Partita IVA:  ")
	CF = None
	while CF==None:
		CF = input("Codice Fiscale (se applicabile):  ")
		if CF=="":	break
		elif not (CFre1.match(CF) or CFre1.match(CF)):	CF = None
	email = None
	while email==None:
		email = input("Indirizzo email (obbligatoriamente PEC se in Italia):  ")
		if email=="" or emailre.match(email):	break
		else:	email = None
	if email:
		Id = "0000000"
		print("Indirizzo PEC specificato: identificativo unico impostato a '0000000'.")
	else:
		Id = None
		while not Id:	Id = input("Identificativo Unico (se applicabile):  ")
	if not CF:	CF = None
	if not Id:	Id = None
	addr = {	'country':"", 'zip':"", 'addr':None, 'prov':None, 'muni':None	}
	while len(addr['country'])!=2:
		addr['country'] = input("Sigla a 2 caratteri della nazione (premi [Invio] per Italia):  ").upper()
		if not addr['country']:	addr['country'] = "IT"
	if addr['country']=="IT":
		while not (len(addr['zip'])==5 and addr['zip'].isnumeric()):
			addr['zip'] = input("CAP (5 cifre):  ").upper()
		while not addr['muni']:
			comune = input("Comune (nome completo):  ")
			for prov in PROVINCES.keys():
				if comune.upper() in [m.upper() for m in PROVINCES[prov]]:
					print("Comune identificato nella sua provincia: %s"%prov)
					addr['prov'], addr['muni'] = prov, comune.upper()
					break
	else:
		print("\nATTENZIONE!: Questa versione di supporta solo fatture da/per enti con sede in Italia.")
		sys.exit(-1)
	while not addr['addr']:
		addr['addr'] = input("Indirizzo (via/piazza/..., numero civico):  ")
	RF = _enum_selection(RegimeFiscale_t, "regime fiscale", 'RF01')
	return {	'name':orgname, 'VAT#':('IT',VATit), 'CF':CF, 'Id':Id, 'addr':addr, 'email':email, 'RegimeFiscale':RF	}


def parse_config():
	clients = json.load(open(CONF_FILE,"r"))
	#except:	return False, False
	if "USER" not in clients.keys():	return False, False
	USER = clients["USER"]
	del clients["USER"]
	for org in clients.keys():
		if type(org)!=type("") or len(org)!=3 or not org.isalnum():	return False, False
	return (USER, clients)


def pretty_dict_print(dictname, D):
	return json.dumps({dictname:D}, indent='\t')


def add_company():
	if not os.path.exists(CONF_FILE):
		print("ERROR!: Il file di configurazione di pyFatturaPA (%s) non è stato trovato. L'utente va prima inizializzato."%CONF_FILE)
		sys.exit(-2)
	USER, clients = parse_config()
	if not USER:	return False
	orgname = ""
	while len(orgname)!=3 or not orgname.isalnum() or orgname in clients.keys():
		orgname = input("Sigla di 3 caratteri alfanumerici per la nuova organizzazione:  ").upper()
	new_client = enter_org_data()
	clients[orgname] = new_client
	return create_config(USER, clients)


def create_config(user=None, clients={}):
	conf = open(CONF_FILE,"w")
	if not user:
		print("Inizializzazione del database: inserimento dati dell'UTENTE.")
		user = enter_org_data()
		answ = None
		while not answ:
			answ = input("L'utente (in qualità di cedente/prestatore) è soggetto a ritenuta? [S]ì/No ")
			if (not answ) or answ[0].lower()=="s":
				user['ritenuta'], aliquota, causale = {'aliquota':None, 'causale':None}
				if type(user['name'])==type(""):	user['ritenuta']['tipo'] = 'RT02'
				else:	user['ritenuta']['tipo'] = 'RT01'
				while not user['ritenuta']['aliquota'] or user['ritenuta']['aliquota']<0. or user['ritenuta']['aliquota']>100.:
					user['ritenuta']['aliquota'] = eval(input("Inserire % aliquota della ritenuta (e.g. \"22.0\"):  "))
				while not user['ritenuta']['causale'] or user['ritenuta']['causale'] not in Causale_Pagamento_t:
					user['ritenuta']['causale'] = input("Inserire sigla della causale di pagamento ('A...Z' ovvero 'L|M|O|V1':  ").upper()
			elif answ and answ[0].lower()=="n":	user['ritenuta'] = None
			else: answ = None;	continue
	while not answ:
		answ = input("Si è iscritti ad una cassa previdenziale? [S]ì/No ")
		if (not answ) or answ[0].lower()=="s":
			user['cassa'] = {
				'tipo':_enum_selection(TipoCassa_t, "cassa di appartenenza", 'TP22'),
				'aliquota':eval(input("Indicare l'aliquota contributo cassa:  ")),
				'IVA':22.00
			}
		elif answ and answ[0].lower()=="n":	user['cassa'] = None
		else: answ = None;	continue
	clients["USER"] = user
	for client in clients.keys():
		conf.write(pretty_dict_print(client,clients[client]))
	conf.close()
	return True

def FatturaPA_assemble(user, client, data):
	#####	FATTURA ELETTRONICA HEADER
	F = [
		'<?xml version="1.0" encoding="UTF-8" ?>',
		'<p:FatturaElettronica versione="%s" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd">'%data['FormatoTrasmissione'],
		'\t<FatturaElettronicaHeader>',
		'\t\t<DatiTrasmissione>',
		'\t\t\t<IdTrasmittente>',
		'\t\t\t\t<IdPaese>%s</IdPaese>'%user['VAT#'][0],
		'\t\t\t\t<IdCodice>%s</IdCodice>'%user['CF'],
		'\t\t\t</IdTrasmittente>',
		'\t\t\t<ProgressivoInvio>%s</ProgressivoInvio>'%data['ProgressivoInvio'],
		'\t\t\t<FormatoTrasmissione>%s</FormatoTrasmissione>'%data['FormatoTrasmissione'],
		'\t\t\t<CodiceDestinatario>%s</CodiceDestinatario>'%client['Id']
	]
	if ('email' in user.keys()) and client['Id']=="0000000":	F.append('\t\t\t<PECDestinatario>%s</PECDestinatario>'%client['email'])
	F.extend([
		'\t\t</DatiTrasmissione>',
		'\t\t<CedentePrestatore>',
		'\t\t\t<DatiAnagrafici>',
		'\t\t\t\t<IdFiscaleIVA>',
		'\t\t\t\t\t<IdPaese>%s</IdPaese>'%user['VAT#'][0],
		'\t\t\t\t\t<IdCodice>%s</IdCodice>'%user['VAT#'][1],
		'\t\t\t\t</IdFiscaleIVA>'])
	if 'CF' in user.keys():	F.append('\t\t\t\t<CodiceFiscale>%s</CodiceFiscale>'%user['CF'])
	F.append('\t\t\t\t<Anagrafica>')
	if type(user['name'])==type(""):	F.append('\t\t\t\t\t<Denominazione>%s</Denominazione>'%user['name'])
	else:	F.extend(['\t\t\t\t\t<Nome>%s</Nome>'%user['name'][0],'\t\t\t\t\t<Cognome>%s</Cognome>'%user['name'][1]])
	F.extend([
		'\t\t\t\t</Anagrafica>',
		'\t\t\t\t<RegimeFiscale>%s</RegimeFiscale>'%user['RegimeFiscale'],
		'\t\t\t</DatiAnagrafici>',
		'\t\t\t<Sede>',
		'\t\t\t\t<Indirizzo>%s</Indirizzo>'%user['addr']['addr'],
		'\t\t\t\t<CAP>%s</CAP>'%user['addr']['zip'],
		'\t\t\t\t<Comune>%s</Comune>'%user['addr']['muni'],
		'\t\t\t\t<Provincia>%2c</Provincia>'%user['addr']['prov'],
		'\t\t\t\t<Nazione>%s</Nazione>'%user['addr']['country'],
		'\t\t\t</Sede>',
		'\t\t</CedentePrestatore>',
		'\t\t<CessionarioCommittente>',
		'\t\t\t<DatiAnagrafici>'])
	if 'VAT#' in client.keys():	F.extend([
		'\t\t\t\t<IdFiscaleIVA>',
		'\t\t\t\t\t<IdPaese>%s</IdPaese>'%client['VAT#'][0],
		'\t\t\t\t\t<IdCodice>%s</IdCodice>'%client['VAT#'][1],
		'\t\t\t\t</IdFiscaleIVA>'])
	if 'CF' in client.keys():	F.append('\t\t\t\t<CodiceFiscale>%s</CodiceFiscale>'%client['CF'])
	F.append('\t\t\t\t<Anagrafica>')
	if type(client['name'])==type(""):	F.append('\t\t\t\t\t<Denominazione>%s</Denominazione>'%client['name'])
	else:	F.extend(['\t\t\t\t\t<Nome>%s</Nome>'%client['name'][0],'\t\t\t\t\t<Cognome>%s</Cognome>'%client['name'][1]])
	F.extend([
		'\t\t\t\t</Anagrafica>',
		'\t\t\t\t<RegimeFiscale>%s</RegimeFiscale>'%client['RegimeFiscale'],
		'\t\t\t</DatiAnagrafici>',
		'\t\t\t<Sede>',
		'\t\t\t\t<Indirizzo>%s</Indirizzo>'%client['addr']['addr'],
		'\t\t\t\t<CAP>%s</CAP>'%client['addr']['zip'],
		'\t\t\t\t<Comune>%s</Comune>'%client['addr']['muni'],
		'\t\t\t\t<Provincia>%2c</Provincia>'%client['addr']['prov'],
		'\t\t\t\t<Nazione>%s</Nazione>'%client['addr']['country'],
		'\t\t\t</Sede>',
		'\t\t</CessionarioCommittente>',
		'\t</FatturaElettronicaHeader>'])
	#####	FATTURA ELETTRONICA BODY
	F.extend([
		'\t<FatturaElettronicaBody>',
		'\t\t<DatiGenerali>',
		'\t\t\t<DatiGeneraliDocumento>',
		'\t\t\t\t<TipoDocumento>%s</TipoDocumento>'%data['TipoDocumento'],
		'\t\t\t\t<Divisa>%s</Divisa>'%data['Divisa'],
		'\t\t\t\t<Data>%s</Data>'%data['Data'],
		'\t\t\t\t<Numero>%s</Numero>'%data['ProgressivoInvio']])
	if 'ritenuta' in user.keys() and 'ritenuta' in data.keys():
		F.extend([
			'\t\t\t\t<DatiRitenuta>',
			'\t\t\t\t\t<TipoRitenuta>%s</TipoRitenuta>'%user['ritenuta']['tipo'],
			'\t\t\t\t\t<ImportoRitenuta>%.02f</ImportoRitenuta>'%data['ritenuta']['importo'],
			'\t\t\t\t\t<AliquotaRitenuta>%.02f</AliquotaRitenuta>'%user['ritenuta']['aliquota'],
			'\t\t\t\t\t<CausalePagamento>%s</CausalePagamento>'%user['ritenuta']['causale'],
			'\t\t\t\t</DatiRitenuta>'])
	if 'cassa' in user.keys() and 'cassa' in data.keys():
		F.extend([
			'\t\t\t\t<DatiCassaPrevidenziale>',
			'\t\t\t\t\t<TipoCassa>%s</TipoCassa>'%user['cassa']['tipo'],
			'\t\t\t\t\t<AlCassa>%.02f</AlCassa>'%user['cassa']['aliquota'],
			'\t\t\t\t\t<ImportoContributoCassa>%.02f</ImportoContributoCassa>'%data['cassa']['total'],
			'\t\t\t\t\t<AliquotaIVA>%.02f</AliquotaIVA>'%user['cassa']['aliquota'],
			'\t\t\t\t\t<ImponibileCassa>%.02f</ImponibileCassa>'%data['cassa']['imponibile'],
			'\t\t\t\t</DatiCassaPrevidenziale>'])
	if 'causale' in data.keys():
		for k in range(0,len(data['causale']),200):
			F.append('\t\t\t\t<Causale>%s</Causale>'%data['causale'][200*k:200*(k+1)])
	F.append('\t\t\t</DatiGeneraliDocumento>')
	if 'ref' in data.keys():
		if 'Id' in data['ref'].keys():
			F.append('\t\t\t<DatiOrdineAcquisto>')
			if '##' in data['ref'].keys():
				for l in sorted(data['ref']['##']):
					F.append('\t\t\t\t<RiferimentoNumeroLinea>%d</RiferimentoNumeroLinea>'%l)
			F.append('\t\t\t\t<IdDocumento>%s</IdDocumento>'%data['ref']['Id']),
			F.append('\t\t\t<DatiOrdineAcquisto>')
		for reftype in ['Contratto','Convenzione','Ricezione','FattureCollegate']:
			if reftype in data['ref'].keys():
				F.append('\t\t\t\t<Dati%s>%s</Dati%s>'%(reftype,data['ref'][reftype],reftype))
	F.expand([
		'\t\t</DatiGenerali>',
		'\t\t<DatiBeniServizi>',
		'\t\t\t<DettaglioLinee>'])
	lines = sorted([data['#'][l]['linea'] for l in data['#'].keys()])
	for l in lines:
		line = data['#'][l];
		F.append('\t\t\t\t<DettaglioLinea>')
		F.append('\t\t\t\t\t<NumeroLinea>%d</NumeroLinea>'%l)
		if 'descr' in line.keys():	F.append('\t\t\t\t\t<Descrizione>%s</Descrizione>'%line['period']['descr'][:1000])
		if 'period' in line.keys():	F.expand([
			'\t\t\t\t\t<DataInizioPeriodo>%s</DataInzioPeriodo>'%line['period'][0].strftime("%Y-%m-%d"),
			'\t\t\t\t\t<DataFinePeriodo>%s</DataFinePeriodo>'%line['period'][1].strftime("%Y-%m-%d")])
		F.append('\t\t\t\t\t<PrezzoUnitario>%.02f</PrezzoUnitario>'%line['price'])
		if 'Qty' in line.keys():
			F.append('\t\t\t\t\t<Quantita>%.02f</Quantita>'%line['Qty'])
			if 'unit' in line.keys():	F.append('\t\t\t\t\t<UnitaMisura>%s</UnitaMisura>'%line['unit'])
		F.append('\t\t\t\t\t<PrezzoTotale>%s</PrezzoTotlae>'%line['total'])
		if 'ritenuta' in user.keys():
			F.expand([
				'\t\t\t\t\t<AliquotaIVA>%.02f</AliquotaIVA>'%user['ritenuta']['aliquota'],
				'\t\t\t\t\t<Ritenuta>%s</Ritenuta>'%'SI'])
		F.append('\t\t\t\t</DettaglioLinea>')
	F.expand([
		'\t\t\t</DettaglioLinee>',
		'\t\t\t<DatiRiepilogo>',
		'\t\t\t\t<AliquotaIVA>%.02f</AliquotaIVA>'%data['total']['IVA'],
		'\t\t\t\t<ImponibileImporto>%.02f</ImponibileImporto>'%data['total']['imponibile'],
		'\t\t\t\t<Imposta>%.02f</Imposta>'%data['total']['imposta'],
		'\t\t\t\t<EsigibilitaIVA>%s</EsigibilitaIVA>'%data['EsigibilitaIVA'],
		'\t\t\t</DatiRiepilogo>',
		'\t\t</DatiBeniServizi>'])
	if 'pagamento' in data.keys():
		F.expand([
			'\t\t<DatiPagamento>',
			'\t\t\t<CondizioniPagamento>%s</CondizioniPagamento>'%data['pagamento']['Condizioni'],
			'\t\t\t<DettaglioPagamento>',
			'\t\t\t\t<ModalitaPagamento>%s</ModalitaPagamento>'%data['pagamento']['mod']])
		if 'exp' in data['pagamento'].keys():
				'\t\t\t\t<DataScadenzaPagamento>%s</DataScadenzaPagamento>'%data['pagamento']['expt'].strftime("%Y-%m-%d"),
		F.expand([
			'\t\t\t</DettaglioPagamento>',
			'\t\t</DatiPagamento>'])
	F.expand([
		'\t</FatturaElettronicaBody>',
		'</p:FatturaElettronica>'])
	for l in F:	print(l)



def _enum_selection(enumtype, enumname=None, default=None):
	if not enumname:	question = "Indicare la selezione numerica sopra elencata"
	else:	question = "Prego selezionare %s"%enumname
	keys = sorted(list(enumtype.keys()))
	if default and default in keys:	question += " (default: %s)"%default
	question += ":  "
	for n in range(len(keys)):	print(("  %%0%dd"%len(str(len(keys))))%n + ":\t%s"%enumtype[keys[n]])
	answ = None
	if default and default in keys:
		while True:
			answ = input(question)
			if not answ:	return default
			elif answ.isnumeric() and 1<=eval(answ)<=len(keys):	break
			else:	answ = None
	else:
		while not (answ.isnumeric() and 1<=eval(answ)<=len(keys)):	answ = input(question)
	return keys[eval(answ)-1]

def issue_invoice():
	user, clients = parse_config()
	data = {}
	if not user:
		print(" * ERRORE!: Database senza dati personali, ovvero il file \"%s\" deve trovarsi nella stessa cartella di \"%s\"."%(CONF_FILE,sys.argv[0]))
		sys.exit(-3)
	if not clients:
		print(" * ERRORE!: Database dei clienti vuoto. Deve essere inserito almeno un cliente tramite l'argomento 'fornitore'.")
		sys.exit(-4)
	org = input("Inserire la sigla identificativa (3 caratteri) del cliente nel database:  ").upper()
	if org not in clients.keys():
		print(" * ERRORE!: Cliente '%s' non trovato nel database."%org)
		sys.exit(-5)
	client = clients[org];	del clients
	data['FormatoTrasmissione'] = _enum_selection(FormatoTrasmissione_t, "tipologia di fattura", 'FPR12')
	data['TipoDocumento'] = _enum_selection(Documento_t, "tipologia di documento", 'TD01')
	data['ProgressivoInvio'] = input("Inserire il numero identificativo (progressivo) della fattura:  ")
	#if data['TipoDocumento'] in ['TD01', ]
	data['Divisa'] = ""
	while not (data['Divisa'] and len(data['Divisa'])==3):
		data['Divisa'] = input("Inserire la divisa (3 caratteri, default: EUR):  ")
		if not data['Divisa']:	data['Divisa'] = "EUR"
	data['Data'] = None
	while not Date.isinstance(datetime.date):
		datetmp = input("Data fatturazione nel formato GG-MM-AAAA (per oggi premere [Invio]):  ")
		if not datetmp:	data['Data'] = datetime.date.today()
		else:
			try:	data['Data'] = datetime.strptime(datetmp,"%d-%m-%Y").today()
			except:	pass
	answ = None
	#####################
	data['causale'] = input("Causale dell'intera fattura (obbligatoria, max. 400 caratteri):  ")
	answ = input("Se applicabile, indicare numero d'Ordine richiesto dal cessionario/committente, ovvero premere [Invio]:  ")
	if answ:	data['ref'] = { 'Id':answ	}
	#answer = input("Il vettore della fattura è il cliente [S]ì/[N]o ")
	#if answer and answer.lower()[0]=='n':
	#	print("Inserire informazioni fiscali sul Vettore")
	#	vector = enter_org_data()
	#else:	vector = client
	data['EsigibilitaIVA'] = _enum_selection(EsigibilitaIVA_t, "esigibilità dell'IVA", 'I')
	data['total'] = {
		'aliquota':eval(input("Aliquota IVA (indicare \"0\" se non applcabile):  ")),
		'imponibile':0.
		}
	answ = None
	while True:
		answ = input("Si vuole specificare condizioni di pagamento? Sì/[N]o ")
		if not answ or answ[0].lower()=='n':	break
		data['pagamento'] = {	'Condizioni':_enum_selection(CondizioniPagamento_t, "condizioni di pagamento", 'TP02')	}
		if data['pagamento']['Condizioni'] == 'TP01':
			exp = None
			while not exp.isinstance(datetime.date):
				try:	exp = datetime.strptime(input("Indicare la scadenza della rata (formato GG-MM-AAA):  "),"%d-%m-%Y")
				except:	pass
		data['pagamento']['mod']:_enum_selection(ModalitaPagamento_t, "modalità di pagamento", 'MP05')	
	data['Scadenza'] = None
	while not data['Scadenza'].isinstance(datetime.date):
		datetmp = input("Scadenza di pagamento della fattura nel formato GG-MM-AAAA (per 30gg premere [Invio]):  ")
		if not datetmp:	data['Scadenza'] = datetime.date.today() + datetime.timedelta(days=30)
		else:
			try:	data['Scadenza'] = datetime.strptime(datetmp,"%d-%m-%Y")
			except:	pass
	data['#'], l, = [], 1
	while True:
		print("\nVOCE #%d DELLA FATTURA."%l)
		price = eval(input("Prezzo unitario della voce #%d:  "%l))
		if not price:	l -= 1;	break
		qty, vat = None
		while not qty:
			qty = input("Quantità della voce #%d  [default: 1]:  "%l)
			if qty.isnumeric():
				qty = eval(qty)
				if qty <= 0:	qty = None
			elif not qty:	qty = 0
			else:	qty = None
		if qty and qty.isnumeric():
			total = price * qty
			unit = input("Unità di misura della voce #%d (premere [Invio] per nessuna):  "%l)
		else:	total, unit = price, None
		data['total']['imponibile'] += total
		#	while not vat:
		#		vat = input("Alitquota della voce #%d  [%%, default: %d]:  "%int(DEF_VAT))
		#		if vat.isnumeric():
		#			vat = eval(vat)
		#			if vat <= 0:	vat = None
		#		elif not vat:	vat = DEF_VAT
		#		else:	vat = None
		descr = input("Descrizione della voce #%d:  "%l)[:1000]
		line = {'linea':l,	'price':price, 'total':total, 'descr':descr	}
		if qty:
			line['Qty'] = qty
			if unit:	line['unit'] = unit
		data['#'].append( line )
		del price, vat, qty, total, descr
		l += 1
	if not data['#']:
		print(" * ERROR!: Non sono state inserite voci nella fattura (è necessaria almeno una voce).")
		sys.exit(-6)
	subtotale = data['total']['imponibile']
	if 'cassa' in user.keys():	###	CASSA
		data['total']['imposta'] = data['cassa']['importo'] = subtotale * user['cassa']['aliquota']
	else:	data['total']['imposta'] = data['cassa']['importo'] = 0
	subtotale += data['cassa']['importo']
	if 'ritenuta' in user.keys():
		data['total']['ritenuta'] = data['ritenuta']['importo'] = -1 * subtotale * user['ritenuta']['aliquota']
	else:	data['total']['ritenuta'] = data['ritenuta']['importo'] = 0
	subtotale += data['ritenuta']['importo']
	data['total']['TOTALE'] = max(0,subtotale)
	if 'pagamento' in data.keys():
		data['pagamento']['importo'] = data['total']['TOTALE']
	return FatturaPA_assemble(user, client, data)

CFre1, CFre2, EORIre = re.compile(r"[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]"), re.compile(r"[A-Z0-9]{11,16}"), re.compile(r"[a-zA-Z0-9]{13,17}")
emailre = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-._]+@[a-zA-Z0-9][a-zA-Z0-9-._]+")
IBANre, BICre = re.compile(r"[a-zA-Z]{2}[0-9]{2}[a-zA-Z0-9]{11,30}"), re.compile(r"[A-Z]{6}[A-Z2-9][A-NP-Z0-9]([A-Z0-9]{3}){0,1}")

REGIONS, PROVINCES = {
	'Abruzzo'              :{'AQ':"L'Aquila", 'CH':"Chieti", 'PE':"Pescara", 'TE':"Teramo"},
	'Basilicata'           :{'MT':"Matera", 'PZ':"Potenza"},
	'Calabria'             :{'CZ':"Catanzaro", 'CS':"Cosenza", 'KR':"Crotone", 'RC':"Reggio-Calabria", 'VV':"Vibo-Valentia"},
	'Campania'             :{'AV':"Avellino", 'BN':"Benevento", 'CE':"Caserta", 'NA':"Napoli", 'SA':"Salerno"},
	'Emilia Romagna'       :{'BO':"Bologna", 'FE':"Ferrara", 'FC':"Forlì-Cesena", 'MO':"Modena", 'PR':"Parma", 'PC':"Piacenza", 'RA':"Ravenna", 'RE':"Reggio-Emilia", 'RN':"Rimini"},
	'Friuli Venezia Giulia':{'GO':"Gorizia", 'PN':"Pordenone", 'TS':"Trieste", 'UD':"Udine"},
	'Lazio'                :{'FR':"Frosinone", 'LT':"Latina", 'RI':"Rieti", 'RM':"Roma", 'VT':"Viterbo"},
	'Liguria'              :{'GE':"Genova", 'IM':"Imperia", 'SP':"La Spezia", 'SV':"Savona"},
	'Lombardia'            :{'BG':"Bergamo", 'BS':"Brescia", 'CO':"Como", 'CR':"Cremona", 'LC':"Lecco", 'LO':"Lodi", 'MN':"Mantova", 'MI':"Milano", 'MB':"Monza-Brianza", 'PV':"Pavia", 'SO':"Sondrio", 'VA':"Varese"},
	'Marche'               :{'AN':"Ancona", 'AP':"Ascoli-Piceno", 'FM':"Fermo", 'MC':"Macerata", 'PU':"Pesaro-Urbino"},
	'Molise'               :{'CB':"Campobasso", 'IS':"Isernia"},
	'Piemonte'             :{'AL':"Alessandria", 'AT':"Asti", 'BI':"Biella", 'CN':"Cuneo", 'NO':"Novara", 'TO':"Torino", 'VB':"Verbania", 'VC':"Vercelli"},
	'Puglia'               :{'BA':"Bari", 'BT':"Barletta-Andria-Trani", 'BR':"Brindisi", 'FG':"Foggia", 'LE':"Lecce", 'TA':"Taranto"},
	'Sardegna'             :{'CA':"Cagliari", 'CI':"Carbonia-Iglesias", 'NU':"Nuoro", 'OG':"Ogliastra", 'OT':"Olbia Tempio", 'OR':"Oristano", 'SS':"Sassari", 'VS':"Medio Campidano"},
	'Sicilia'              :{'AG':"Agrigento", 'CL':"Caltanissetta", 'CT':"Catania", 'EN':"Enna", 'ME':"Messina", 'PA':"Palermo", 'RG':"Ragusa", 'SR':"Siracusa", 'TP':"Trapani"},
	'Toscana'              :{'AR':"Arezzo", 'FI':"Firenze", 'GR':"Grosseto", 'LI':"Livorno", 'LU':"Lucca", 'MS':"Massa-Carrara", 'PI':"Pisa", 'PT':"Prato", 'SI':"Siena"},
	'Trentino Alto Adige'  :{'BZ':"Bolzano", 'TN':"Trento"},
	'Umbria'               :{'PG':"Perugia", 'TR':"Terni"},
	'Valle d\'Aosta'       :{'AO':"Aosta"},
	'Veneto'               :{'BL':"Belluno", 'PD':"Padova", 'RO':"Rovigo", 'TV':"Treviso", 'VE':"Venezia", 'VR':"Verona", 'VI':"Vicenza"}
}, []
FormatoTrasmissione_t = { 'FPA12':"verso PA", 'FPR12':"verso privati"	}
CausalePagamento_t = frozenset(['A','B','C','D','E','F','G','H','I','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','L1','M1','O1','V1'])
TipoSconto_t = { 'sconto':"SC", 'maggiorazione':"MG"	}
Art73_t = frozenset(["SI"])	# documento emesso secondo modalità e temini stabiliti con DM ai sensi art. 74 DPR 633/72
TipoCassa_t = {
	'TC01':"Cassa nazionale previdenza e assistenza avvocati e procuratori legali",
	'TC02':"Cassa previdenza dottori commercialisti",
	'TC03':"Cassa previdenza e assistenza geometri",
	'TC04':"Cassa nazionale previdenza e assistenza ingegneri e architetti liberi professionisti",
	'TC05':"Cassa nazionale del notariato",
	'TC06':"Cassa nazionale previdenza e assistenza ragionieri e periti commerciali",
	'TC07':"Ente nazionale assistenza agenti e rappresentanti di commercio (ENASARCO)",
	'TC08':"Ente nazionale previdenza e assistenza consulenti del lavoro (ENPACL)",
	'TC09':"Ente nazionale previdenza e assistenza medici (ENPAM)",
	'TC10':"Ente nazionale previdenza e assistenza farmacisti (ENPAF)",
	'TC11':"Ente nazionale previdenza e assistenza veterinari (ENPAV)",
	'TC12':"Ente nazionale previdenza e assistenza impiegati dell'agricoltura (ENPAIA)",
	'TC13':"Fondo previdenza impiegati imprese di spedizione e agenzie marittime",
	'TC14':"Istituto nazionale previdenza giornalisti italiani (INPGI)",
	'TC15':"Opera nazionale assistenza orfani sanitari italiani (ONAOSI)",
	'TC16':"Cassa autonoma assistenza integrativa giornalisti italiani (CASAGIT)",
	'TC17':"Ente previdenza periti industriali e periti industriali laureati (EPPI)",
	'TC18':"Ente previdenza e assistenza pluricategoriale (EPAP)",
	'TC19':"Ente nazionale previdenza e assistenza biologi (ENPAB)",
	'TC20':"Ente nazionale previdenza e assistenza professione infermieristica (ENPAPI)",
	'TC21':"Ente nazionale previdenza e assistenza psicologi (ENPAP)",
	'TC22':"INPS"
}
Documento_t = {	'TD01':"Fattura", 'TD02':"Acconto/anticipo su fattura", 'TD03':"Acconto/anticipo su parcella", 'TD04':"Nota di credito", 'TD05':"Nota di debito", 'TD06':"Parcella"	}
Ritenuta_t1 = {	'RT01':"Ritenuta di acconto persone fisiche", 'RT02':"Ritenuta di acconto persone giuridiche"	}
Ritenuta_t2 = {	'SI':"Cessione/prestazione soggetta a ritenuta"	}
SoggettoEmittente_t = {	'CC':"Cessionario / committente", 'TZ':"Terzo"	}
RegimeFiscale_t = {
	'RF01':"Regime ordinario",
	'RF02':"Regime dei contribuenti minimi (art. 1,c.96-117, L. 244/2007)",
	#'RF03':"Nuove iniziative produttive (art.13 L.388/0)",
	'RF04':"Agricoltura e attività connesse e pesca (artt.34 e 34-bis, D.P.R. 633/1972)",
	'RF05':"Vendita sali e tabacchi (art. 74, c.1, D.P.R. 633/1972)",
	'RF06':"Commercio dei fiammiferi (art. 74, c.1, D.P.R. 633/1972)",
	'RF07':"Editoria (art. 74, c.1, D.P.R. 633/1972)",
	'RF08':"Gestione di servizi di telefonia pubblica (art. 74, c.1, D.P.R. 633/1972)",
	'RF09':"Rivendita di documenti di trasporto pubblico e di sosta (art. 74, c.1, D.P.R. 633/1972)",
	'RF10':"Intrattenimenti, giochi e altre attività di cui alla tariffa allegata al D.P.R. 640/72 (art. 74, c.6, D.P.R. 633/1972)",
	'RF11':"Agenzie di viaggi e turismo (art. 74-ter, D.P.R. 633/1972)",
	'RF12':"Agriturismo (art. 5, c.2, L. 413/1991)",
	'RF13':"Vendite a domicilio (art. 25-bis, c.6, D.P.R. 600/1973)",
	'RF14':"Rivendita di beni usati, di oggetti	d’arte, d’antiquariato o da collezione (art.36, D.L. 41/1995)",
	'RF15':"Agenzie di vendite all’asta di oggetti d’arte, antiquariato o da collezione (art. 40-bis, D.L. 41/1995)",
	'RF16':"IVA per cassa P.A. (art. 6, c.5, D.P.R. 633/1972)",
	'RF17':"IVA per cassa (art. 32-bis, D.L. 83/2012)",
	'RF19':"Regime forfettario",
	'RF18':"Altro"
}
CondizioniPagamento_t = {	'TP01':"pagamento a rate", 'TP02':"pagamento completo", 'TP03':"anticipo"	}
ModalitaPagamento_t = {
	'MP01':"contanti", 'MP02':"assegno circolare", 'MP04':"contanti presso Tesoreria", 'MP05':"bonifico", 'MP06':"vaglia cambiario", 'MP07':"bollettino bancario",
	'MP08':"carta di pagamento", 'MP09':"RID", 'MP10':"RID utenze", 'MP11':"RID veloce", 'MP12':"RIBA", 'MP13':"MAV", 'MP14':"quietanza erario",
	'MP15':"giroconto su conti di contabilità speciale", 'MP16':"domiciliazione bancaria", 'MP17':"domiciliazione postale", 'MP18':"bollettino di c/c postale", 
	'MP19':"SEPA Direct Debit", 'MP20':"SEPA Direct Debit CORE", 'MP21':"SEPA Direct Debit B2B", 'MP22':"Trattenuta su somme già riscosse", 
}
EsigibilitaIVA_t = {	'D':"esibilità differita", 'I':"esigibilità immediata", 'S':"scissione dei pagamenti"	}
Natura_t = {
	'N1':"Escluse ex. art.15", 'N2':"Non soggette", 'N3':"Non Imponibili", 'N4':"Esenti", 'N5':"Regime del margine", 'N6':"Inversione contabile (reverse charge)",
	'N7':"IVA assolta in altro stato UE (vendite a distanza ex art.40 commi 3 e 4 e art.41 comma 1 lett.b, DL 331/93; prestazione di servizi di telecomunicazioni, teleradiodiffusione ed elettronici ex art.7-sexies lett. f,g, DPR 633/72 e art.74-sexies, DPR 633/72)"
}
SocioUnico_t = {	'SU':"socio unico", 'SM':"più soci"	}
StatoLiquidazione_t = {	'LS':"in liquidazione", 'LN':"non in liquidazione"	}
TipoCessionePrestazione_t = {	'SC':"Sconto", 'PR':"Premio", 'AB':"Abbuono", 'AC':"Spesa accessoria"	}

def main():
	def print_args():
		print("%s %s - Genera rapidamente fatture elettroniche semplici in XML nel formato FatturaPA."%(sys.argv[0].upper(),__VERSION))
		print("Copytight (C) 2019 Walter Arrighetti  <walter.arrighetti@agid.gov.it>\n")
		print(" Utilizzo:  %s  emetti | fornitore | inizializza"%sys.argv[0].lower())
		print("\t\temetti       Genera FatturaPA verso fornitore esistente")
		print("\t\tfornitore    Aggiunge un fornitore (italiano) al database")
		print("\t\tinizializza  Inizializza un nuovo database con i tuoi dati")
		print('\n')
		sys.exit(9)
	[PROVINCES.extend(list(prov.keys())) for prov in REGIONS.values()]
	if len(sys.argv) != 2:	print_args()
	elif sys.argv[1].lower()=="emetti":	issue_invoice()
	elif sys.argv[1].lower()=="fornitore":	add_company()
	elif sys.argv[1].lower()=="inizializza":	create_config()
	else:	print_args()
	sys.exit(0)


if __name__ == "__main__":	main()