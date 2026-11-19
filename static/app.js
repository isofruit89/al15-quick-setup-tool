function $(id) {
  return document.getElementById(id);
}

function showView(name) {
  ['homeView', 'creatorView', 'deployView', 'profileView', 'packagerView'].forEach(id => $(id)?.classList.add('hidden'));
  if (name === 'home') $('homeView')?.classList.remove('hidden');
  if (name === 'create') $('creatorView')?.classList.remove('hidden');
  if (name === 'deploy') $('deployView')?.classList.remove('hidden');
  if (name === 'profiles') $('profileView')?.classList.remove('hidden');
  if (name === 'packager') $('packagerView')?.classList.remove('hidden');
  window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
}


function setStatus(id, text, cls = '') {
  const el = $(id);
  if (!el) return;
  el.dataset.src = String(text ?? '');
  delete el.dataset.key;
  el.textContent = trText(text);
  el.className = 'status-box ' + cls;
}
// Übersetzt einen bereits angezeigten Text in die aktuelle Sprache (für den Sprachwechsel).
function retranslate(text) {
  const s = String(text ?? '');
  for (const k of Object.keys(I18N.de)) if (I18N.de[k] === s || I18N.en[k] === s) return t(k);
  if (TEXT_EN[s] !== undefined) return trText(s);
  const de = Object.keys(TEXT_EN).find(k => TEXT_EN[k] === s);
  if (de !== undefined) return LANG === 'en' ? s : de;
  return trText(s);
}
function retranslateStatusBoxes() {
  document.querySelectorAll('.status-box').forEach(el => {
    if (el.dataset.key) el.textContent = t(el.dataset.key);
    else if (el.dataset.src !== undefined) el.textContent = retranslate(el.dataset.src);
  });
}

function splitCsv(text) {
  return String(text || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
}

function safeName(s) {
  return String(s || '').trim();
}

function showDialog() {
  const d = $('previewDialog');
  if (d && !d.open) d.showModal();
}

function closeDialog() {
  const d = $('previewDialog');
  if (d && d.open) d.close();
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}
async function readJsonResponse(response) {
  const text = await response.text();
  const contentType = String(response.headers.get('content-type') || '').toLowerCase();
  if (!contentType.includes('application/json')) {
    const compact = text.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    throw new Error(`${t('serverNoJson')} HTTP ${response.status}${compact ? ': ' + compact.slice(0, 300) : ''}`);
  }
  try {
    return JSON.parse(text);
  } catch (_) {
    throw new Error(`${t('serverInvalidJson')} HTTP ${response.status}`);
  }
}



const I18N = {
  de: {
    langButton: 'EN', createTitle: 'Parametersatz erstellen', createSub: 'Offline-Konfiguration des AL15 und Parametersatz speichern', deployHome: 'Parametersatz übertragen', deploySub: 'Mit Gerät verbinden, Profil auswählen, Quick Edit, Dry-Run und Konfiguration übernehmen.', profileManagerHome:'Profilverwaltung', profileManagerSub:'Profile laden, bearbeiten, kopieren oder löschen.', homeButton:'🏠 Startseite',
    back: '← Startseite', newSet: 'Neuer Parametersatz', newSetInfo: 'Tragen Sie die Werte abweichend von den Default-Einstellungen ein.', fwHint: 'Hinweis: Kompatibel ab Firmware 1.7', preview: 'Technische Vorschau', save: 'Parametersatz speichern', profileName: 'Profilname',
    deviceTags: 'Device Tags', appHint: 'Application Tag Hinweis: Hostname für OPC UA Server', network: 'Network', system: 'Systemeinstellungen', connections: 'Connections', noAction: 'Keine Aktion', start: 'Start', stop: 'Stop', on: 'Ein', off: 'Aus',
    mqttClient:'MQTT Client', mqttCmd:'MQTT Command Channel', checkCerts:'Zertifikate prüfen', clearCerts:'Zertifikate löschen', noCerts:'Keine Zertifikate eingefügt.',
    certHelpClient:'Fügen Sie ein einzelnes PEM-Zertifikat oder eine komplette Zertifikatskette ein. Das Tool erkennt alle <code>BEGIN/END CERTIFICATE</code>-Blöcke automatisch und sendet diese in der vom Gerät erwarteten Syntax: <code>newvalue: ["CERT1,\\nCERT2"]</code>.',
    certHelpCmd:'Sie können ein einzelnes PEM-Zertifikat oder eine komplette Zertifikatskette für den MQTT Command Channel einfügen. Echte Zeilenumbrüche und aus JSON kopierte <code>\\n</code>-Sequenzen werden unterstützt. Mehrere Zertifikate werden automatisch im Geräteformat <code>newvalue: ["CERT1,\\nCERT2"]</code> übertragen.',
    ready:'Bereit. Werte eingeben und Parametersatz speichern.', deployTitle:'Parametersatz übertragen', deployHelp:'Für eine lokale Verbindung und Inbetriebnahme des AL15 schließen Sie den AL15 bitte direkt an Ihren PC/PG an. Bitte stellen Sie den verwendeten Netzwerkadapter auf DHCP. Das Gerät ist unter https://ifm-AL1590-Seriennummer.local erreichbar. Die 12-stellige Seriennummer finden Sie seitlich auf dem Gerät.<br><br>Beispiel SN 000261900178 --&gt; https://ifm-AL1590-000261900178.local<br><br>Alternativ kann das Gerät in eine bestehende IT-Infrastruktur integriert werden und erhält eine DHCP Adresse von einem DHCP-Server. Ihr PC/PG muss Zugang zu dem verwendeten Netzwerk haben. Der Zugriff kann ebenfalls per &quot;https://ifm-AL1590-000261900178.local&quot; erfolgen.',
    reload:'Profile neu laden', precheck:'Vorprüfung', dryRun:'Dry Run', apply:'Konfiguration übernehmen', liveHint:'Hinweis: Es kann bis zu 60s dauern. Während der Übertragung wird jeder Request live angezeigt.', connectionStatus:'Verbindungsstatus', username:'Benutzer', password:'Passwort', newPassword:'Neues Passwort', confirmNewPassword:'Neues Passwort bestätigen', profile:'Profil', quickEditTitle:'Quick Edit für dieses Gerät', mode:'Modus', ipAddress:'IP-Adresse', subnetMask:'Subnetzmaske', dnsServer:'DNS-Server', readyPackager:'Bereit.', noPrecheck:'Noch keine Vorprüfung durchgeführt.', feedback:'Feedback', close:'Schließen', selectProfile:'-- Profil wählen --',
    section:'Bereich', label:'Label', path:'Pfad', status:'Status', value:'Wert', profileManagerTitle:'Profilverwaltung', profileManagerInfo:'Profile laden, bearbeiten, kopieren oder löschen.', savedProfiles:'Gespeicherte Profile', profileManagerHint:'Bearbeiten lädt das Profil in den Editor. Speichern überschreibt bei gleichem Namen das Profil.', readyShort:'Bereit.', edit:'Bearbeiten', copy:'Kopieren', delete:'Löschen', noProfiles:'Keine Profile vorhanden.', profileLoadFailed:'Profil konnte nicht geladen werden.', copyFailed:'Kopieren fehlgeschlagen.', deleteFailed:'Löschen fehlgeschlagen.', anonRequiresNone:'OPC UA Anonymous benötigt Security Profile "None". "None" wurde automatisch aktiviert.', anonDisabledNone:'Anonymous wurde deaktiviert, weil Security Profile "None" deaktiviert wurde.', noRequests:'Keine Requests erzeugt.', noOutput:'Noch keine Ausgabe vorhanden.', ioddTitle:'IODD-Integration', ioddHint:'IODD-Dateien werden im Parametersatz gespeichert und beim Übertragen in den AL15 geladen.', ioddHelp:'ZIP bis 10 MB, Mehrfachauswahl möglich.', ioddEmpty:'Keine IODD-Dateien ausgewählt.', ioddInvalid:'Bitte nur ZIP auswählen.', ioddTooLarge:'IODD-Datei ist größer als 10 MB.', remove:'Entfernen', flowTitle:'Node-RED Flow-Import', flowHint:'Node-RED Flow-Dateien werden im Parametersatz gespeichert und beim Übertragen in Node-RED geladen.', flowHelp:'JSON-Flows bis 5 MB. Mehrere Dateien werden zusammengeführt. Der Import ersetzt die aktive Flow-Konfiguration.', flowEmpty:'Keine Node-RED Flow-Dateien ausgewählt.', flowInvalid:'Bitte nur gültige Node-RED JSON-Flow-Dateien auswählen.', flowTooLarge:'Die Node-RED Flow-Datei ist größer als 5 MB.', flowDuplicateId:'Doppelte Node-ID:', packagerHome:'Node-RED Paletten Packager', packagerSub:'Offlinefähige TGZ-Pakete einschließlich Runtime-Abhängigkeiten erzeugen.', packagerInfo:'Erzeugt eine vollständig offlinefähige TGZ-Datei mit Runtime-Abhängigkeiten.', internetRequired:'Aktive Internetverbindung erforderlich', exactPackageName:'Genauer Name der Palette', exactVersion:'Genaue Version', createTgz:'TGZ-Datei erstellen', createdPalettes:'Erstellte Paletten im Arbeitsverzeichnis', paletteTitle:'Node-RED Paletten', paletteHint:'TGZ-Dateien werden im Parametersatz gespeichert und vor dem Node-RED Flow auf dem Gerät installiert.', paletteHelp:'TGZ, Mehrfachauswahl möglich. Die Reihenfolge der Auswahl wird bei der Installation verwendet.', paletteEmpty:'Keine Node-RED Paletten ausgewählt.', paletteInvalid:'Bitte nur TGZ-Dateien auswählen.', packagerInputRequired:'Bitte den genauen Namen der Palette und die genaue Version eingeben.', packagerCreating:'TGZ-Datei wird erstellt. Runtime-Abhängigkeiten werden heruntergeladen...', packagerCreated:'TGZ-Datei erfolgreich erstellt', packagerCreateFailed:'TGZ-Datei konnte nicht erstellt werden.', packagerListFailed:'Arbeitsverzeichnis konnte nicht gelesen werden.', packagerNoFiles:'Noch keine TGZ-Dateien erzeugt.', download:'Herunterladen', serverNoJson:'Der Server hat keine JSON-Antwort geliefert. Bitte das Quick-Setup-Tool mit der aktualisierten app.py neu starten.', serverInvalidJson:'Die Serverantwort ist kein gültiges JSON.', packagerStepInit:'npm-Projekt wird initialisiert...', packagerStepDownload:'Palette und Runtime-Abhängigkeiten werden heruntergeladen...', packagerStepRuntimeTest:'Runtime-Auflösung wird geprüft und automatisch repariert...', packagerStepDependencies:'Runtime-Abhängigkeiten werden ermittelt und eingebettet...', packagerStepArchiveTest:'Direktes TGZ wird entpackt und erneut geprüft...', packagerStepPack:'Offline-Paket wird erstellt...', packagerStepSave:'TGZ-Datei und Manifest werden im Arbeitsverzeichnis gespeichert...', packagerStepPrebuiltFind:'Mitgelieferte Palette wird gesucht...', packagerStepPrebuiltVerify:'Artefakt und Manifest werden geprüft...', packagerStepPrebuiltSha:'SHA-256 wird validiert...', packagerStepPrebuiltPublish:'Freigegebenes AL15-Artefakt wird bereitgestellt...', packagerStrategy:'Buildstrategie', packagerDependenciesFound:'Eingebettete Runtime-Abhängigkeiten', packagerFileSize:'Dateigröße', packagerStreamEnded:'Die Statusübertragung wurde unerwartet beendet.', packagerInputRequired:'Bitte den genauen Namen der Palette und die genaue Version eingeben.', packagerCreating:'TGZ-Datei wird erstellt. Runtime-Abhängigkeiten werden heruntergeladen...', packagerCreated:'TGZ-Datei erfolgreich erstellt', packagerCreateFailed:'TGZ-Datei konnte nicht erstellt werden.', packagerListFailed:'Arbeitsverzeichnis konnte nicht gelesen werden.', packagerNoFiles:'Noch keine TGZ-Dateien erzeugt.', download:'Herunterladen', quickEditHint:'Diese Werte überschreiben nur die Übertragung, nicht das gespeicherte Profil. Es dient lediglich zur schnellen Anpassung und Vervielfältigung auf mehrere AL159x. Bitte ändern Sie keine Werte, wenn das gespeicherte Profil direkt übertragen werden soll.'
  },
  en: {
    langButton: 'DE', createTitle: 'Create parameter set', createSub: 'Offline configuration of the AL15 and save the parameter set', deployHome: 'Transfer parameter set', deploySub: 'Connect to device, select profile, quick edit, dry run and apply configuration.', profileManagerHome:'Profile management', profileManagerSub:'Load, edit, copy or delete profiles.', homeButton:'🏠 Home',
    back: '← Home', newSet: 'New parameter set', newSetInfo: 'Enter values that differ from the default settings.', fwHint: 'Note: Compatible from firmware 1.7', preview: 'Technical preview', save: 'Save parameter set', profileName: 'Profile name',
    deviceTags: 'Device Tags', appHint: 'Application Tag note: Hostname for OPC UA Server', network: 'Network', system: 'System Settings', connections: 'Connections', noAction: 'No action', start: 'Start', stop: 'Stop', on: 'On', off: 'Off',
    mqttClient:'MQTT Client', mqttCmd:'MQTT Command Channel', checkCerts:'Validate certificates', clearCerts:'Clear certificates', noCerts:'No certificates inserted.',
    certHelpClient:'Paste a single PEM certificate or a complete certificate chain. The tool automatically detects all <code>BEGIN/END CERTIFICATE</code> blocks and sends them in the syntax expected by the device: <code>newvalue: ["CERT1,\\nCERT2"]</code>.',
    certHelpCmd:'Paste a single PEM certificate or a complete certificate chain for the MQTT Command Channel. Real line breaks and copied JSON <code>\\n</code> sequences are supported. Multiple certificates are automatically transferred in the device format <code>newvalue: ["CERT1,\\nCERT2"]</code>.',
    ready:'Ready. Enter values and save the parameter set.', deployTitle:'Transfer parameter set', deployHelp:'For local connection and commissioning of the AL15, connect the AL15 directly to the PC/PG. Set the used network adapter to DHCP. The device is available at https://ifm-AL1590-serialnumber.local. The 12-digit serial number is printed on the side of the device.<br><br>Example SN 000261900178 --&gt; https://ifm-AL1590-000261900178.local<br><br>Alternatively, the device can be integrated into an existing IT infrastructure and receives a DHCP address from a DHCP server. The PC/PG must have access to the used network. Access is also possible via &quot;https://ifm-AL1590-000261900178.local&quot;.',
    reload:'Reload profiles', precheck:'Pre-check', dryRun:'Dry run', apply:'Apply configuration', liveHint:'Note: This can take up to 60 seconds. Each request is displayed live during transfer.', connectionStatus:'Connection status', username:'Username', password:'Password', newPassword:'New password', confirmNewPassword:'Confirm new password', profile:'Profile', quickEditTitle:'Quick Edit for this device', mode:'Mode', ipAddress:'IP address', subnetMask:'Subnet mask', dnsServer:'DNS server', readyPackager:'Ready.', noPrecheck:'No pre-check performed yet.', feedback:'Feedback', close:'Close', selectProfile:'-- Select profile --',
    section:'Section', label:'Label', path:'Path', status:'Status', value:'Value', profileManagerTitle:'Profile management', profileManagerInfo:'Load, edit, copy or delete profiles.', savedProfiles:'Saved profiles', profileManagerHint:'Edit loads the profile into the editor. Saving with the same name overwrites the profile.', readyShort:'Ready.', edit:'Edit', copy:'Copy', delete:'Delete', noProfiles:'No profiles available.', profileLoadFailed:'Profile could not be loaded.', copyFailed:'Copy failed.', deleteFailed:'Delete failed.', anonRequiresNone:'OPC UA Anonymous requires security profile "None". "None" was enabled automatically.', anonDisabledNone:'Anonymous was disabled because security profile "None" was disabled.', noRequests:'No requests generated.', noOutput:'No output available yet.', ioddTitle:'IODD integration', ioddHint:'IODD files are stored in the parameter set and uploaded to the AL15 during transfer.', ioddHelp:'ZIP up to 10 MB, multiple selection supported.', ioddEmpty:'No IODD files selected.', ioddInvalid:'Select ZIP only.', ioddTooLarge:'IODD file exceeds 10 MB.', remove:'Remove', flowTitle:'Node-RED flow import', flowHint:'Node-RED flow files are stored in the parameter set and loaded into Node-RED during transfer.', flowHelp:'JSON flows up to 5 MB. Multiple files are merged. The import replaces the active flow configuration.', flowEmpty:'No Node-RED flow files selected.', flowInvalid:'Select valid Node-RED JSON flow files only.', flowTooLarge:'The Node-RED flow file exceeds 5 MB.', flowDuplicateId:'Duplicate node id:', packagerHome:'Node-RED Palette Packager', packagerSub:'Create offline-capable TGZ packages including runtime dependencies.', packagerInfo:'Creates a fully offline-capable TGZ file including runtime dependencies.', internetRequired:'Active internet connection required', exactPackageName:'Exact palette name', exactVersion:'Exact version', createTgz:'Create TGZ file', createdPalettes:'Created palettes in the working directory', paletteTitle:'Node-RED Palettes', paletteHint:'TGZ files are stored in the parameter set and installed on the device before the Node-RED flow.', paletteHelp:'TGZ, multiple selection supported. Installation follows the selection order.', paletteEmpty:'No Node-RED palettes selected.', paletteInvalid:'Select TGZ files only.', packagerInputRequired:'Enter the exact palette name and exact version.', packagerCreating:'Creating TGZ file and downloading runtime dependencies...', packagerCreated:'TGZ file created successfully', packagerCreateFailed:'TGZ file could not be created.', packagerListFailed:'The working directory could not be read.', packagerNoFiles:'No TGZ files have been created yet.', download:'Download', serverNoJson:'The server did not return JSON. Restart the Quick-Setup Tool with the updated app.py.', serverInvalidJson:'The server response is not valid JSON.', packagerStepInit:'Initializing npm project...', packagerStepDownload:'Downloading palette and runtime dependencies...', packagerStepRuntimeTest:'Testing and automatically repairing runtime resolution...', packagerStepDependencies:'Detecting and embedding runtime dependencies...', packagerStepArchiveTest:'Extracting and validating the direct TGZ archive...', packagerStepPack:'Creating offline package...', packagerStepSave:'Saving TGZ file and manifest to the working directory...', packagerStepPrebuiltFind:'Searching bundled palette...', packagerStepPrebuiltVerify:'Validating artifact and manifest...', packagerStepPrebuiltSha:'Validating SHA-256...', packagerStepPrebuiltPublish:'Publishing released AL15 artifact...', packagerStrategy:'Build strategy', packagerDependenciesFound:'Embedded runtime dependencies', packagerFileSize:'File size', packagerStreamEnded:'The status stream ended unexpectedly.', packagerInputRequired:'Enter the exact palette name and exact version.', packagerCreating:'Creating TGZ file and downloading runtime dependencies...', packagerCreated:'TGZ file created successfully', packagerCreateFailed:'TGZ file could not be created.', packagerListFailed:'The working directory could not be read.', packagerNoFiles:'No TGZ files have been created yet.', download:'Download', quickEditHint:'These values override only the transfer, not the stored profile. This feature is intended for quick adjustments and replication to multiple AL159x devices. Do not modify any values if the stored profile is to be transferred unchanged.'
  }
};
Object.assign(I18N.de, {opcuaCertHint:'Zertifikat als DER/PEM, Private Key als PKCS#12 (.pfx, ohne Passwort). Wurde der OPC UA Server noch nie gestartet, startet und stoppt das Tool ihn vor dem Upload einmal automatisch.', opcuaCertFile:'Zertifikat', opcuaKeyFile:'Private Key', opcuaCertMissing:'nicht ausgewählt', opcuaCertTooLarge:'Zertifikats-/Schlüsseldatei ist größer als 64 KB.', opcuaCertFileLabel:'Zertifikat (.der / .pem / .crt)', opcuaKeyFileLabel:'Private Key (.pfx / .p12, ohne Passwort)', selectFile:'Datei auswählen'});
Object.assign(I18N.en, {opcuaCertHint:'Certificate as DER/PEM, private key as PKCS#12 (.pfx, no password). If the OPC UA server has never been started, the tool starts and stops it once automatically before the upload.', opcuaCertFile:'Certificate', opcuaKeyFile:'Private key', opcuaCertMissing:'not selected', opcuaCertTooLarge:'Certificate/key file exceeds 64 KB.', opcuaCertFileLabel:'Certificate (.der / .pem / .crt)', opcuaKeyFileLabel:'Private key (.pfx / .p12, no password)', selectFile:'Select file'});
Object.assign(I18N.de, {profileOverwriteConfirm:'Das Profil "{name}" existiert bereits. Überschreiben?', copyCancelled:'Kopieren abgebrochen.', profileNameAdjusted:'Name angepasst: {name}.', serviceAction:'Dienst', appTagHostnameWarn:'Der Application Tag wird als Hostname des OPC UA Servers verwendet. Erlaubt sind nur A–Z, a–z, 0–9 und Bindestrich (max. 63 Zeichen, nicht am Anfang oder Ende). Umlaute, Leerzeichen und Sonderzeichen können OPC-UA-Clients stören.'});
Object.assign(I18N.en, {profileOverwriteConfirm:'Profile "{name}" already exists. Overwrite?', copyCancelled:'Copy cancelled.', profileNameAdjusted:'Name adjusted: {name}.', serviceAction:'Service', appTagHostnameWarn:'The application tag is used as host name of the OPC UA server. Only A–Z, a–z, 0–9 and hyphen are allowed (max. 63 characters, not at the start or end). Umlauts, spaces and special characters may disturb OPC UA clients.'});
Object.assign(I18N.de, {excludeSecrets:'Passwörter und Private Key nicht im Profil speichern', excludeSecretsHint:'Profile werden unverschlüsselt im Ordner „profiles“ abgelegt. Ist die Option aktiv, werden das MQTT-Command-Channel-Passwort und das OPC-UA-Zertifikat mit Private Key nicht gespeichert und nicht übertragen.', secretMqttPassword:'MQTTCC-Passwort', secretOpcuaKey:'OPC-UA-Zertifikat mit Private Key', secretsRemoved:'Nicht gespeichert: {items}.', secretsStored:'Hinweis: {items} unverschlüsselt im Profil gespeichert.'});
Object.assign(I18N.en, {excludeSecrets:'Do not store passwords and private key in the profile', excludeSecretsHint:'Profiles are stored unencrypted in the "profiles" folder. If enabled, the MQTT command channel password and the OPC UA certificate with private key are neither stored nor transferred.', secretMqttPassword:'MQTTCC password', secretOpcuaKey:'OPC UA certificate with private key', secretsRemoved:'Not stored: {items}.', secretsStored:'Note: {items} stored unencrypted in the profile.'});
Object.assign(I18N.de, {configure:'Konfigurieren', currentValue:'Ist', targetValue:'Soll', planned:'Geplant', dryRunReading:'Dry Run wird erstellt, Ist-Werte werden vom Gerät gelesen...'});
Object.assign(I18N.en, {configure:'Configure', currentValue:'Current', targetValue:'Target', planned:'Planned', dryRunReading:'Creating dry run, reading current values from the device...'});
Object.assign(I18N.de, {precheckRunning:'Vorprüfung läuft...', precheckFailed:'Vorprüfung fehlgeschlagen.', precheckRequired:'Bitte zuerst eine erfolgreiche Vorprüfung durchführen.', precheckInvalidated:'Host oder Zugangsdaten geändert. Bitte Vorprüfung erneut durchführen.', errorStatus:'Fehler'});
Object.assign(I18N.en, {precheckRunning:'Pre-check running...', precheckFailed:'Pre-check failed.', precheckRequired:'Please run a successful pre-check first.', precheckInvalidated:'Host or credentials changed. Please run the pre-check again.', errorStatus:'Error'});
Object.assign(I18N.de, {selectFiles:'Dateien auswählen',noFileSelected:'Keine Datei ausgewählt',selectedFiles:'Dateien ausgewählt',portsTitle:'Portkonfiguration',portsHint:'Pin 4 für Ports 1–8 und Pin 2 für B-Ports 1–4 konfigurieren.',portLabel:'Port',pin4Label:'Pin 4',pin2Label:'Pin 2',pin4Disable:'0 = Deaktiviert',pin4DI:'1 = Digitaler Eingang',pin4DO:'2 = Digitaler Ausgang',pin4IOLink:'3 = IO-Link (Standard)',pin2Off:'0 = Aus (IO-Link Typ-A-Versorgung, Standard)',pin2On:'1 = Ein (IO-Link Typ-B-Versorgung)',pin2DO:'2 = Digitaler Ausgang'});
Object.assign(I18N.en, {selectFiles:'Select files',noFileSelected:'No file selected',selectedFiles:'files selected',portsTitle:'Port configuration',portsHint:'Configure Pin 4 for ports 1–8 and Pin 2 for B-ports 1–4.',portLabel:'Port',pin4Label:'Pin 4',pin2Label:'Pin 2',pin4Disable:'0 = Disabled',pin4DI:'1 = Digital input',pin4DO:'2 = Digital output',pin4IOLink:'3 = IO-Link (default)',pin2Off:'0 = Off (IO-Link Type A supply, default)',pin2On:'1 = On (IO-Link Type B supply)',pin2DO:'2 = Digital output'});

let IODD_FILES = [];
function bytesLabel(n){ if(n<1024)return `${n} B`; if(n<1048576)return `${(n/1024).toFixed(1)} KB`; return `${(n/1048576).toFixed(1)} MB`; }
function ensureIoddUi(){
  if($('iodd_files'))return;
  const cards=Array.from(document.querySelectorAll('#creatorView .card'));
  const networkCard=cards.find(c=>c.querySelector('.section-header h2')?.textContent.trim()==='Network');
  if(!networkCard)return;
  const section=document.createElement('section'); section.className='card compact-card'; section.id='ioddSection';
  section.innerHTML=`<div class="section-header"><h2>${t('ioddTitle')}</h2><span class="hint">${t('ioddHint')}</span></div><div class="iodd-drop"><input id="iodd_files" type="file" accept=".zip" multiple><div class="minor-hint">${t('ioddHelp')}</div></div><div id="ioddList" class="iodd-list"></div>`;
  networkCard.after(section); $('iodd_files').addEventListener('change',handleIoddFiles); renderIoddList();
}
function fileToBase64(file){return new Promise((ok,fail)=>{const r=new FileReader();r.onload=()=>ok(String(r.result).split(',')[1]||'');r.onerror=fail;r.readAsDataURL(file);});}
async function handleIoddFiles(e){for(const file of Array.from(e.target.files||[])){const n=file.name.toLowerCase();if(!n.endsWith('.zip')){setStatus('createStatus',t('ioddInvalid'),'error');continue;}if(file.size>10485760){setStatus('createStatus',t('ioddTooLarge'),'error');continue;}IODD_FILES=IODD_FILES.filter(x=>x.name!==file.name);IODD_FILES.push({name:file.name,size:file.size,type:file.type||'application/octet-stream',content_base64:await fileToBase64(file)});}e.target.value='';renderIoddList();}
function renderIoddList(){updateFileSelectionLabels();const w=$('ioddList');if(!w)return;if(!IODD_FILES.length){w.innerHTML=`<div class="muted">${t('ioddEmpty')}</div>`;return;}w.innerHTML='';IODD_FILES.forEach((f,i)=>{const r=document.createElement('div');r.className='iodd-row';r.innerHTML=`<div><strong>${escapeHtml(f.name)}</strong><span>${bytesLabel(f.size||0)}</span></div><button type="button" class="danger" data-i="${i}">${t('remove')}</button>`;w.appendChild(r);});w.querySelectorAll('[data-i]').forEach(x=>x.onclick=()=>{IODD_FILES.splice(Number(x.dataset.i),1);renderIoddList();});}

let FLOW_FILES = [];
function flowNodes(value){
  if(Array.isArray(value)) return value;
  if(value && Array.isArray(value.flows)) return value.flows;
  throw new Error(t('flowInvalid'));
}
function ensureFlowUi(){
  if($('flow_files')) return;
  const anchor=$('ioddSection'); if(!anchor) return;
  const section=document.createElement('section'); section.className='card compact-card'; section.id='flowSection';
  section.innerHTML=`<div class="section-header"><h2>${t('flowTitle')}</h2><span class="hint">${t('flowHint')}</span></div><div class="flow-drop"><input id="flow_files" type="file" accept=".json,application/json" multiple><div class="minor-hint">${t('flowHelp')}</div></div><div id="flowList" class="flow-list"></div>`;
  anchor.after(section); $('flow_files').addEventListener('change',handleFlowFiles); renderFlowList();
}
async function handleFlowFiles(event){
  try{
    for(const file of Array.from(event.target.files||[])){
      if(!file.name.toLowerCase().endsWith('.json')) throw new Error(t('flowInvalid'));
      if(file.size>5*1024*1024) throw new Error(t('flowTooLarge'));
      let content; try{content=JSON.parse(await file.text());}catch(_){throw new Error(`${t('flowInvalid')} ${file.name}`);}
      flowNodes(content);
      const candidate=FLOW_FILES.filter(x=>x.name!==file.name).concat([{name:file.name,size:file.size,type:file.type||'application/json',content_json:content}]);
      const ids=new Set();
      for(const entry of candidate){for(const node of flowNodes(entry.content_json)){if(node?.id&&ids.has(node.id))throw new Error(`${t('flowDuplicateId')} ${node.id}`);if(node?.id)ids.add(node.id);}}
      FLOW_FILES=candidate;
    }
    renderFlowList();
  }catch(error){setStatus('createStatus',String(error.message||error),'error');}
  event.target.value='';
}
function renderFlowList(){
  updateFileSelectionLabels();
  const wrap=$('flowList'); if(!wrap)return;
  if(!FLOW_FILES.length){wrap.innerHTML=`<div class="muted">${t('flowEmpty')}</div>`;return;}
  wrap.innerHTML=''; FLOW_FILES.forEach((file,index)=>{const row=document.createElement('div');row.className='flow-row';const size=file.size||new Blob([JSON.stringify(file.content_json)]).size;row.innerHTML=`<div><strong>${escapeHtml(file.name)}</strong><span>${bytesLabel(size)} · ${flowNodes(file.content_json).length} nodes</span></div><button type="button" class="danger" data-flow-remove="${index}">${t('remove')}</button>`;wrap.appendChild(row);});
  wrap.querySelectorAll('[data-flow-remove]').forEach(button=>button.onclick=()=>{FLOW_FILES.splice(Number(button.dataset.flowRemove),1);renderFlowList();});
}
  let PALETTE_FILES = [];

  function ensurePaletteUi() {
    if ($('palette_files')) return;
    const flowSection = $('flowSection');
    if (!flowSection) return;
    const section = document.createElement('section');
    section.className = 'card compact-card';
    section.id = 'paletteSection';
    section.innerHTML = `<div class="section-header"><h2>${t('paletteTitle')}</h2><span class="hint">${t('paletteHint')}</span></div><div class="palette-drop"><input id="palette_files" type="file" accept=".tgz,application/gzip,application/x-compressed" multiple><div class="minor-hint">${t('paletteHelp')}</div></div><div id="paletteList" class="palette-list"></div>`;
    flowSection.after(section);
    $('palette_files').addEventListener('change', handlePaletteFiles);
    renderPaletteList();
  }

  async function handlePaletteFiles(event) {
    for (const file of Array.from(event.target.files || [])) {
      if (!file.name.toLowerCase().endsWith('.tgz')) {
        setStatus('createStatus', t('paletteInvalid'), 'error');
        continue;
      }
      PALETTE_FILES = PALETTE_FILES.filter(x => x.name !== file.name);
      PALETTE_FILES.push({
        name: file.name,
        size: file.size,
        type: file.type || 'application/x-compressed',
        content_base64: await fileToBase64(file)
      });
    }
    event.target.value = '';
    renderPaletteList();
  }

  function renderPaletteList() {
    updateFileSelectionLabels();
    const wrap = $('paletteList');
    if (!wrap) return;
    if (!PALETTE_FILES.length) {
      wrap.innerHTML = `<div class="muted">${t('paletteEmpty')}</div>`;
      return;
    }
    wrap.innerHTML = '';
    PALETTE_FILES.forEach((file, index) => {
      const row = document.createElement('div');
      row.className = 'palette-row';
      row.innerHTML = `<div><strong>${escapeHtml(file.name)}</strong><span>${bytesLabel(file.size || 0)}</span></div><button type="button" class="danger" data-palette-remove="${index}">${t('remove')}</button>`;
      wrap.appendChild(row);
    });
    wrap.querySelectorAll('[data-palette-remove]').forEach(button => {
      button.onclick = () => {
        PALETTE_FILES.splice(Number(button.dataset.paletteRemove), 1);
        renderPaletteList();
      };
    });
  }

  async function refreshPalettePackages() {
    const wrap = $('palettePackageFiles');
    if (!wrap) return;
    try {
      const response = await fetch('/palette-packager/files?lang=' + encodeURIComponent(LANG));
      const data = await readJsonResponse(response);
      if (!response.ok || !data.ok) throw new Error(data.error || t('packagerListFailed'));
      wrap.innerHTML = '';
      if (!(data.files || []).length) {
        wrap.innerHTML = `<div class="muted">${t('packagerNoFiles')}</div>`;
        return;
      }
      (data.files || []).forEach(file => {
        const row = document.createElement('div');
        row.className = 'palette-row';
        row.innerHTML = `<div><strong>${escapeHtml(file.name)}</strong><span>${bytesLabel(file.size || 0)}</span></div><a class="download-link" href="/palette-packager/download/${encodeURIComponent(file.name)}">${t('download')}</a>`;
        wrap.appendChild(row);
      });
    } catch (error) {
      wrap.innerHTML = `<div class="muted">${escapeHtml(String(error.message || error))}</div>`;
    }
  }

  let PALETTE_PROGRESS_TOTAL = 7;

  function resetPaletteProgress() {
    $('paletteProgressWrap')?.classList.remove('hidden');
    if ($('paletteProgress')) $('paletteProgress').value = 0;
    if ($('paletteProgressLabel')) $('paletteProgressLabel').textContent = `0/${PALETTE_PROGRESS_TOTAL}`;
    if ($('paletteProgressPercent')) $('paletteProgressPercent').textContent = '0%';
    if ($('paletteLiveLog')) $('paletteLiveLog').textContent = '';
  }

  function appendPaletteLog(text) {
    const log = $('paletteLiveLog');
    if (!log || !text) return;
    log.textContent += `${text}\n`;
    log.scrollTop = log.scrollHeight;
  }

  function updatePaletteStep(message) {
    const step = Number(message.step || 0);
    const total = Number(message.total || 7);
    PALETTE_PROGRESS_TOTAL = total;
    if ($('paletteProgress')) { $('paletteProgress').max = total; $('paletteProgress').value = step; }
    if ($('paletteProgressLabel')) $('paletteProgressLabel').textContent = `${step}/${total}`;
    if ($('paletteProgressPercent')) $('paletteProgressPercent').textContent = `${Math.round(step / total * 100)}%`;
    const text = t(message.key || 'packagerCreating');
    setStatus('palettePackagerStatus', `[${step}/${total}] ${text}`);
    appendPaletteLog(`[${step}/${total}] ${text}`);
  }

  async function createPalettePackage() {
    const packageName = String($('palettePackageName')?.value || '').trim();
    const version = String($('palettePackageVersion')?.value || '').trim();
    if (!packageName || !version) {
      setStatus('palettePackagerStatus', t('packagerInputRequired'), 'error');
      return;
    }
    const button = $('createPalettePackageBtn');
    if (button) button.disabled = true;
    resetPaletteProgress();
    setStatus('palettePackagerStatus', t('packagerCreating'));
    try {
      const response = await fetch('/palette-packager/create-stream?lang=' + encodeURIComponent(LANG), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-UI-Lang': LANG },
        body: JSON.stringify({ package: packageName, version, lang: LANG })
      });
      if (!response.ok || !response.body) throw new Error(`${t('packagerCreateFailed')} HTTP ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let completed = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          const message = JSON.parse(line);
          if (message.type === 'step') updatePaletteStep(message);
          else if (message.type === 'log') appendPaletteLog(message.message);
          else if (message.type === 'info' && message.key === 'packagerDependenciesFound') {
            appendPaletteLog(`${t('packagerDependenciesFound')}: ${message.value}`);
          } else if (message.type === 'done') {
            completed = true;
            if (!message.ok) throw new Error(message.error || t('packagerCreateFailed'));
            const size = bytesLabel(message.size || 0);
            setStatus('palettePackagerStatus', `${t('packagerCreated')}: ${message.filename}`, 'ok');
            appendPaletteLog(`${t('packagerCreated')}: ${message.filename}`);
            appendPaletteLog(`${t('packagerFileSize')}: ${size}`);
            appendPaletteLog(`${t('packagerDependenciesFound')}: ${message.dependencies ?? 0}`);
            if ($('paletteProgress')) $('paletteProgress').value = PALETTE_PROGRESS_TOTAL;
              if ($('paletteProgressLabel')) $('paletteProgressLabel').textContent = `${PALETTE_PROGRESS_TOTAL}/${PALETTE_PROGRESS_TOTAL}`;
            if ($('paletteProgressPercent')) $('paletteProgressPercent').textContent = '100%';
            await refreshPalettePackages();
          }
        }
      }
      if (!completed) throw new Error(t('packagerStreamEnded'));
    } catch (error) {
      setStatus('palettePackagerStatus', String(error.message || error), 'error');
      appendPaletteLog(`${t('errorStatus')}: ${String(error.message || error)}`);
    } finally {
      if (button) button.disabled = false;
    }
  }

function enhanceFileInput(inputId, labelId) {
  const input=$(inputId); if(!input) return;
  input.classList.add('native-file-input');
  let wrap=input.parentElement?.querySelector('.localized-file-picker');
  if(!wrap){wrap=document.createElement('div');wrap.className='localized-file-picker';wrap.innerHTML=`<button type="button" class="file-select-btn"></button><span id="${labelId}" class="file-selection-label"></span>`;input.after(wrap);wrap.querySelector('button').addEventListener('click',()=>input.click());}
  wrap.querySelector('button').textContent=t('selectFiles');
}
function updateFileSelectionLabels(){const entries=[['ioddFileSelection',IODD_FILES.length],['flowFileSelection',FLOW_FILES.length],['paletteFileSelection',PALETTE_FILES.length]];for(const [id,count] of entries){const el=$(id);if(el)el.textContent=count?`${count} ${t('selectedFiles')}`:t('noFileSelected');}}
function enhanceAllFileInputs(){enhanceFileInput('iodd_files','ioddFileSelection');enhanceFileInput('flow_files','flowFileSelection');enhanceFileInput('palette_files','paletteFileSelection');updateFileSelectionLabels();}
function ensurePortConfigurationUi(){if($('portConfigurationSection'))return;const anchor=$('paletteSection');if(!anchor)return;const section=document.createElement('section');section.className='card compact-card';section.id='portConfigurationSection';section.innerHTML=`<div class="section-header"><h2></h2><span class="hint"></span></div><div id="portConfigurationGrid" class="port-config-grid"></div>`;anchor.after(section);renderPortConfiguration();}
function portSelect(id,options,value){return `<select id="${id}"><option value="" class="opt-noaction"${String(value??'')===''?' selected':''}>${t('noAction')}</option>${options.map(([v,k])=>`<option value="${v}"${String(value)===String(v)?' selected':''}>${t(k)}</option>`).join('')}</select>`;}
function renderPortConfiguration(){const wrap=$('portConfigurationGrid');if(!wrap)return;const values={};for(let p=1;p<=8;p++)values[p]={pin4:$(`port_${p}_pin4`)?.value??'',pin2:$(`port_${p}_pin2`)?.value??''};wrap.innerHTML='';for(let p=1;p<=8;p++){const card=document.createElement('div');card.className='subcard port-config-card';const pin4=portSelect(`port_${p}_pin4`,[['0','pin4Disable'],['1','pin4DI'],['2','pin4DO'],['3','pin4IOLink']],values[p].pin4);const pin2=p<=4?`<div class="field-block"><label>${t('pin2Label')}</label>${portSelect(`port_${p}_pin2`,[['0','pin2Off'],['1','pin2On'],['2','pin2DO']],values[p].pin2)}</div>`:'';card.innerHTML=`<h3>${t('portLabel')} ${p}</h3><div class="field-block"><label>${t('pin4Label')}</label>${pin4}</div>${pin2}`;wrap.appendChild(card);}document.querySelector('#portConfigurationSection h2').textContent=t('portsTitle');document.querySelector('#portConfigurationSection .hint').textContent=t('portsHint');}
function loadPortConfiguration(profile){const ports=profile?.port_configuration?.ports||[];for(let p=1;p<=8;p++){const item=ports.find(x=>Number(x.port)===p)||{};setSelectParam(`port_${p}_pin4`,item.pin4);if(p<=4)setSelectParam(`port_${p}_pin2`,item.pin2);}}
function collectPortConfiguration(){return{ports:Array.from({length:8},(_,i)=>{const p=i+1,item={port:p,pin4:getSelectParam(`port_${p}_pin4`)};if(p<=4)item.pin2=getSelectParam(`port_${p}_pin2`);return item;})};}
let LANG = localStorage.getItem('al15_lang') || 'de';
const TEXT_EN = {
  'Bereit. Werte eingeben und Parametersatz speichern.':'Ready. Enter values and save the parameter set.', 'Parametersatz wird gespeichert...':'Saving parameter set...', 'Speichern fehlgeschlagen.':'Saving failed.', 'Technische Vorschau wird erstellt...':'Creating technical preview...', 'Vorschau fehlgeschlagen.':'Preview failed.', 'Vorprüfung läuft...':'Pre-check running...', 'Vorprüfung erfolgreich.':'Pre-check successful.', 'Vorprüfung fehlgeschlagen.':'Pre-check failed.', 'Dry Run wird erstellt...':'Creating dry run...', 'Dry Run erfolgreich erstellt.':'Dry run created successfully.', 'Dry Run fehlgeschlagen':'Dry run failed', 'Konfiguration wird übertragen... Live-Feedback aktiv.':'Applying configuration... Live feedback active.', 'Konfiguration abgeschlossen.':'Configuration completed.', 'Konfiguration fehlgeschlagen.':'Configuration failed.', 'Bitte Profil wählen':'Please select a profile', 'Fehler':'Error', 'Vorprüfung':'Pre-check', 'Profil':'Profile', 'Passwort ändern':'Change password', 'MQTT Zertifikate erfolgreich geprüft.':'MQTT certificates validated successfully.', 'MQTT Zertifikate sind ungültig.':'MQTT certificates are invalid.', 'MQTT Zertifikate gelöscht.':'MQTT certificates cleared.', 'MQTT Command Channel Zertifikate erfolgreich geprüft.':'MQTT Command Channel certificates validated successfully.', 'MQTT Command Channel Zertifikate sind ungültig.':'MQTT Command Channel certificates are invalid.', 'MQTT Command Channel Zertifikate gelöscht.':'MQTT Command Channel certificates cleared.', 'MQTT Trusted Server Certificates sind nicht im gültigen PEM-Format.':'MQTT Trusted Server Certificates are not in valid PEM format.'
};
const LABEL_EN = {'OPC UA Start (nach Settings)':'OPC UA Start (after settings)','OPC UA Zertifikat':'OPC UA certificate','Credentials ein':'Enable credentials','Credentials aus':'Disable credentials','MQTTCC Passwort':'MQTTCC password','Passwort ändern':'Change password','Vorprüfung':'Pre-check'};
function t(k){ return (I18N[LANG] && I18N[LANG][k]) || I18N.de[k] || k; }
function trText(v){ let s = String(v ?? ''); if (LANG !== 'en') return s; if (TEXT_EN[s]) return TEXT_EN[s]; Object.entries(LABEL_EN).forEach(([de,en]) => { s = s.replaceAll(de,en); }); return s; }
function isSuccessCode(code, adr = '') {
  const c = String(code ?? '');
  if (c === '200') return true;
  if (c === '230' && String(adr ?? '') === '/connections/httpserver0/httpserver/allowed_services/setdata') return true;
  return false;
}
function setLang(lang){ LANG = lang; localStorage.setItem('al15_lang', LANG); applyTranslations(); }
function setNodeText(sel, txt){ const el = document.querySelector(sel); if(el) el.textContent = txt; }
function setNodeHtml(sel, val){ const el = document.querySelector(sel); if(el) el.innerHTML = val; }
const LAST_HOST_KEY = 'al15_last_host';
function rememberHost(host) { try { if (host) localStorage.setItem(LAST_HOST_KEY, host); } catch (_) {} }
function restoreHost() {
  const el = $('deployIp');
  if (!el || el.value) return;
  try { const last = localStorage.getItem(LAST_HOST_KEY); if (last) el.value = last; } catch (_) {}
}
// Hostname-Regeln (RFC 1123): nur A-Z, a-z, 0-9 und '-', max. 63 Zeichen, nicht mit '-' beginnen/enden.
function appTagHostnameOk(value) { const v = String(value || ''); return !v || (/^[A-Za-z0-9-]{1,63}$/.test(v) && !v.startsWith('-') && !v.endsWith('-')); }
function ensureAppTagWarnings() {
  for (const id of ['application_tag', 'qe_application_tag']) {
    const input = $(id);
    if (!input) continue;
    let warn = $(id + '_warn');
    if (!warn) {
      warn = document.createElement('div'); warn.id = id + '_warn'; warn.className = 'field-warning hidden';
      input.after(warn);
      input.addEventListener('input', () => updateAppTagWarning(id));
    }
    updateAppTagWarning(id);
  }
}
function updateAppTagWarning(id) {
  const input = $(id), warn = $(id + '_warn');
  if (!input || !warn) return;
  const ok = appTagHostnameOk(input.value);
  warn.textContent = ok ? '' : t('appTagHostnameWarn');
  warn.classList.toggle('hidden', ok);
}
// Überschrift über den Start/Stop-Schaltern der Dienste
function ensureActionLabels() {
  document.querySelectorAll('.segmented[data-target$="_action"]').forEach(group => {
    let label = group.previousElementSibling;
    if (!label || !label.classList.contains('seg-label')) {
      label = document.createElement('label'); label.className = 'seg-label';
      group.before(label);
    }
    label.textContent = t('serviceAction');
  });
}
function applyTranslations(){
  ensureIoddUi();
  ensureFlowUi();
  ensurePaletteUi();
  ensurePortConfigurationUi();
  document.documentElement.lang = LANG;
  const lb = $('langToggleBtn'); if(lb) lb.textContent = t('langButton');
  const hb = $('topHomeBtn'); if(hb) hb.textContent = t('homeButton');
  setNodeText('#openCreateBtn .mode-title', t('createTitle')); setNodeText('#openCreateBtn .mode-subtitle', t('createSub'));
  setNodeText('#openDeployBtn .mode-title', t('deployHome')); setNodeText('#openDeployBtn .mode-subtitle', t('deploySub'));
  setNodeText('#packagerTitle', t('packagerHome'));
  setNodeText('#packagerInfo', t('packagerInfo'));
  setNodeText('#packagerInternet', t('internetRequired'));
  setNodeText('#packageNameLabel', t('exactPackageName'));
  setNodeText('#packageVersionLabel', t('exactVersion'));
  setNodeText('#createPalettePackageBtn', t('createTgz'));
  setNodeText('#packageFilesTitle', t('createdPalettes'));
  const packageFilesWrap=$('palettePackageFiles'); if(packageFilesWrap && packageFilesWrap.querySelector('.muted')) packageFilesWrap.querySelector('.muted').textContent=t('packagerNoFiles');
  setNodeText('#openPalettePackagerBtn .mode-title', t('packagerHome')); setNodeText('#openPalettePackagerBtn .mode-subtitle', t('packagerSub'));
    setNodeText('#openProfileManagerBtn .mode-title', t('profileManagerHome')); setNodeText('#openProfileManagerBtn .mode-subtitle', t('profileManagerSub'));
  document.querySelectorAll('.back-btn').forEach(e => e.textContent = t('back'));
  setNodeText('#creatorView .hero h2', t('newSet')); setNodeText('#creatorView .hero p:not(.minor-hint)', t('newSetInfo')); setNodeText('#creatorView .hero .minor-hint', t('fwHint'));
  setNodeText('#previewBtn', t('preview')); setNodeText('#saveBtn', t('save')); setNodeText('#saveBtnBottom', t('save'));
  const pl = document.querySelector('.meta-grid .label'); if(pl) pl.textContent = t('profileName');
  // Überschriften über feste IDs setzen (die Position verschiebt sich durch dynamisch eingefügte Abschnitte).
  setNodeText('#sec_device_tags .section-header h2', t('deviceTags')); setNodeText('#sec_network .section-header h2', t('network'));
  setNodeText('#systemTitle', t('system')); setNodeText('#connectionsTitle', t('connections'));
  setNodeText('#creatorView .section-header .hint', t('appHint'));
  document.querySelectorAll('.seg-btn').forEach(btn => { const v=btn.getAttribute('data-value'); if(v==='none') btn.textContent=t('noAction'); if(v==='start') btn.textContent=t('start'); if(v==='stop') btn.textContent=t('stop'); if(v==='true') btn.textContent=t('on'); if(v==='false') btn.textContent=t('off'); });
  document.querySelectorAll('#creatorView h3').forEach(h => { if(h.textContent.trim()==='MQTT Client') h.textContent=t('mqttClient'); if(h.textContent.trim()==='MQTT Command Channel') h.textContent=t('mqttCmd'); });
  setNodeText('#opcuaCertHint', t('opcuaCertHint'));
  const helps = document.querySelectorAll('.cert-help'); if(helps[0]) helps[0].innerHTML = t('certHelpClient'); if(helps[1]) helps[1].innerHTML = t('certHelpCmd');
  setNodeText('#mqttCertValidateBtn', t('checkCerts')); setNodeText('#mqttCertClearBtn', t('clearCerts')); setNodeText('#mqttCmdCertValidateBtn', t('checkCerts')); setNodeText('#mqttCmdCertClearBtn', t('clearCerts'));
  if(!$('mqtt_certs')?.value) setNodeText('#mqttCertStatus', t('noCerts')); if(!$('mqttcmd_certs')?.value) setNodeText('#mqttCmdCertStatus', t('noCerts'));
  retranslateStatusBoxes();
  setNodeText('#deployView h2', t('deployTitle')); setNodeHtml('#deployView .deploy-help', t('deployHelp'));
    const deployLabels=[['deployUsername','username'],['deployPassword','password'],['deployNewPassword','newPassword'],['deployConfirmNewPassword','confirmNewPassword'],['deployProfiles','profile'],['qe_network_mode','mode'],['qe_network_address','ipAddress'],['qe_network_subnetmask','subnetMask'],['qe_network_dns','dnsServer']];
    deployLabels.forEach(([inputId,key])=>{const el=$(inputId);const label=el?.closest('.field-row, .field-block')?.querySelector('.label, label');if(label)label.textContent=t(key);});
    setNodeText('#deployQuickEdit > h3',t('quickEditTitle'));
    if($('palettePackagerStatus')&&['Bereit.','Ready.'].includes($('palettePackagerStatus').textContent.trim()))$('palettePackagerStatus').textContent=t('readyPackager'); setNodeText('#quickEditHint', t('quickEditHint')); setNodeText('#deployReloadProfilesBtn', t('reload')); setNodeText('#deployConnectBtn', t('precheck')); setNodeText('#deployDryRunBtn', t('dryRun')); setNodeText('#deployApplyBtn', t('apply')); setNodeText('#deployView .minor-hint', t('liveHint')); setNodeText('#deployView section:nth-of-type(2) h2', t('connectionStatus')); setNodeText('#deployView section:nth-of-type(3) h2', t('feedback'));
  if($('deployConnectionStatus') && ($('deployConnectionStatus').textContent.includes('Vorprüfung') || $('deployConnectionStatus').textContent.includes('pre-check'))) $('deployConnectionStatus').textContent = t('noPrecheck');
  const opt = document.querySelector('#deployProfiles option[value=""]'); if(opt) opt.textContent = t('selectProfile'); setNodeText('#previewDialog h3', t('preview')); setNodeText('#closePreviewBtn', t('close'));
  setNodeText('#profileView .hero h2', t('profileManagerTitle'));
  setNodeText('#profileView .hero p', t('profileManagerInfo'));
  setNodeText('#profileManagerReloadBtn', t('reload'));
  setNodeText('#profileView .section-header h2', t('savedProfiles'));
  setNodeText('#profileView .section-header .hint', t('profileManagerHint'));
  if ($('profileManagerStatus') && ($('profileManagerStatus').textContent === 'Bereit.' || $('profileManagerStatus').textContent === 'Ready.')) $('profileManagerStatus').textContent = t('readyShort');
  setNodeText("#ioddSection .section-header h2",t("ioddTitle")); setNodeText("#ioddSection .section-header .hint",t("ioddHint")); setNodeText("#ioddSection .minor-hint",t("ioddHelp")); renderIoddList();
  setNodeText("#flowSection .section-header h2",t("flowTitle")); setNodeText("#flowSection .section-header .hint",t("flowHint")); setNodeText("#flowSection .minor-hint",t("flowHelp")); renderFlowList();
  setNodeText("#paletteSection .section-header h2", t("paletteTitle"));
  setNodeText("#paletteSection .section-header .hint", t("paletteHint"));
  setNodeText("#paletteSection .minor-hint", t("paletteHelp"));
  renderPaletteList();
  enhanceAllFileInputs();
  renderPortConfiguration();
  ensureClassToggles();
  ensureNoActionToggles();
  translateNoActionControls();
  setNodeText('#opcuaCertFileLabel', t('opcuaCertFileLabel')); setNodeText('#opcuaKeyFileLabel', t('opcuaKeyFileLabel'));
  enhanceFileInput('opcua_cert_file', 'opcuaCertFileSelection'); enhanceFileInput('opcua_key_file', 'opcuaKeyFileSelection');
  document.querySelectorAll('#opcua_cert_panel .file-select-btn').forEach(b => b.textContent = t('selectFile'));
  document.querySelectorAll('#opcua_cert_panel .file-selection-label').forEach(l => l.textContent = '');
  renderOpcuaCert();
  ensureActionLabels(); ensureAppTagWarnings();
  setNodeText('#excludeSecretsLabel', t('excludeSecrets')); setNodeText('#excludeSecretsHint', t('excludeSecretsHint'));
  refreshProfileManager?.();
}
function initSegmented() {
  document.querySelectorAll('.segmented').forEach(group => {
    const target = group.getAttribute('data-target');
    group.querySelectorAll('.seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const h = $(target);
        if (h) h.value = btn.getAttribute('data-value') || 'none';
      });
    });
  });
}

function setSegmentValue(targetId, value) {
  const hidden = $(targetId);
  if (hidden) hidden.value = value;
  document.querySelectorAll(`.segmented[data-target="${targetId}"] .seg-btn`).forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-value') === value);
  });
}

// ---------------------------------------------------------------------------
// "Keine Aktion" (Profilschema v2)
//  - Klasse: Schalter "Konfigurieren | Keine Aktion" je Abschnitt -> section.apply
//  - Parameter: Checkbox "Keine Aktion" bei Textfeldern, Option "Keine Aktion" bei Auswahllisten
//    -> Wert null im Profil. Tippen in ein Feld hebt "Keine Aktion" automatisch auf.
// ---------------------------------------------------------------------------
const CLASS_SECTIONS = {
  device_tags: 'sec_device_tags', network: 'sec_network', port_configuration: 'portConfigurationSection',
  system_ntp: 'sub_ntp', system_nodered: 'sub_nodered', system_security: 'sub_security',
  connections_http: 'sub_http', connections_opcua: 'sub_opcua', connections_mqtt_client: 'sub_mqtt_client',
  connections_mqtt_command_channel: 'sub_mqttcc', iodd: 'ioddSection', node_red_flows: 'flowSection', node_red_palettes: 'paletteSection'
};
const CLASS_APPLY = Object.fromEntries(Object.keys(CLASS_SECTIONS).map(k => [k, true]));
const NOACTION_GROUPS = ['opcua_profiles', 'opcua_cert_panel'];
const NOACTION_PARAMS = ['application_tag', 'function_tag', 'location_tag', 'ntp_servers', 'opcua_port', 'opcua_profiles', 'opcua_cert_panel',
  'mqtt_clientid', 'mqtt_certs', 'mqttcmd_brokerip', 'mqttcmd_brokerport', 'mqttcmd_cmdtopic', 'mqttcmd_replytopic',
  'mqttcmd_clientid', 'mqttcmd_user', 'mqttcmd_password', 'mqttcmd_certs'];

function ensureClassToggles() {
  Object.entries(CLASS_SECTIONS).forEach(([section, id]) => {
    const box = $(id);
    if (!box || box.querySelector(':scope > .class-toggle, :scope > .section-header > .class-toggle')) return;
    const toggle = document.createElement('div');
    toggle.className = 'class-toggle';
    toggle.dataset.section = section;
    toggle.innerHTML = `<button type="button" class="seg-btn" data-apply="true"></button><button type="button" class="seg-btn" data-apply="false"></button>`;
    toggle.addEventListener('click', e => {
      const btn = e.target.closest('button[data-apply]');
      if (btn) setClassApply(section, btn.dataset.apply === 'true');
    });
    const header = box.querySelector(':scope > .section-header');
    if (header) header.appendChild(toggle);
    else {
      const h3 = box.querySelector(':scope > h3');
      if (h3) h3.after(toggle); else box.prepend(toggle);
    }
    setClassApply(section, CLASS_APPLY[section]);
  });
  translateNoActionControls();
}
function setClassApply(section, apply) {
  CLASS_APPLY[section] = apply !== false;
  const box = $(CLASS_SECTIONS[section]);
  if (!box) return;
  box.classList.toggle('section-skipped', !CLASS_APPLY[section]);
  box.querySelectorAll('.class-toggle button[data-apply]').forEach(b => b.classList.toggle('active', (b.dataset.apply === 'true') === CLASS_APPLY[section]));
}
function getClassApply(section) { return CLASS_APPLY[section] !== false; }

function noActionBox(id) { return document.querySelector(`input.noaction[data-for="${id}"]`); }
function isNoAction(id) { return !!noActionBox(id)?.checked; }
function setNoAction(id, on) {
  const box = noActionBox(id);
  if (box) box.checked = !!on;
  const holder = NOACTION_GROUPS.includes(id) ? $(id) : $(id)?.closest('.field-block');
  holder?.classList.toggle('param-noaction', !!on);
}
function ensureNoActionToggles() {
  NOACTION_PARAMS.forEach(id => {
    const field = $(id);
    if (!field || noActionBox(id)) return;
    const holder = NOACTION_GROUPS.includes(id) ? field : field.closest('.field-block');
    if (!holder) return;
    const label = document.createElement('label');
    label.className = 'noaction-toggle';
    label.innerHTML = `<input type="checkbox" class="noaction" data-for="${id}"><span></span>`;
    if (NOACTION_GROUPS.includes(id)) holder.before(label); else holder.appendChild(label);
    label.querySelector('input').addEventListener('change', e => setNoAction(id, e.target.checked));
    // Eingabe im Feld bedeutet: Parameter soll geschrieben werden.
    const clear = () => { if (isNoAction(id)) setNoAction(id, false); };
    field.addEventListener('input', clear);
    field.addEventListener('change', e => { if (!e.target.classList.contains('noaction')) clear(); });
    setNoAction(id, true);
  });
  translateNoActionControls();
}
function translateNoActionControls() {
  document.querySelectorAll('.class-toggle button[data-apply="true"]').forEach(b => b.textContent = t('configure'));
  document.querySelectorAll('.class-toggle button[data-apply="false"]').forEach(b => b.textContent = t('noAction'));
  document.querySelectorAll('.noaction-toggle span').forEach(s => s.textContent = t('noAction'));
  document.querySelectorAll('option.opt-noaction').forEach(o => o.textContent = t('noAction'));
  document.querySelectorAll('option.opt-on').forEach(o => o.textContent = t('on'));
  document.querySelectorAll('option.opt-off').forEach(o => o.textContent = t('off'));
}
// Textparameter: null = Keine Aktion
function setTextParam(id, value, format = v => String(v)) {
  const el = $(id);
  if (!el) return;
  const none = value === null || value === undefined;
  el.value = none ? '' : format(value);
  setNoAction(id, none);
}
function getTextParam(id, parse = v => v) {
  if (isNoAction(id)) return null;
  return parse($(id)?.value ?? '');
}
// Auswahlparameter: Option '' = Keine Aktion
function setSelectParam(id, value) {
  const el = $(id);
  if (el) el.value = value === null || value === undefined ? '' : String(value);
}
function getSelectParam(id, parse = v => Number(v)) {
  const v = $(id)?.value ?? '';
  return v === '' ? null : parse(v);
}
const numberOrNull = v => (String(v).trim() === '' ? null : Number(v));
const csvOrNull = v => { const list = splitCsv(v); return list.length ? list : null; };
const certsOrNull = v => (String(v).trim() === '' ? null : parsePemCertificates(v));
// OPC-UA-Zertifikat: Zertifikat (DER/PEM) + Private Key (PKCS#12) als eingebettete Dateien im Profil
let OPCUA_CERT = { certificate: null, private_key: null };
async function handleOpcuaCertFile(event, slot) {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  if (file.size > 65536) { setStatus('createStatus', t('opcuaCertTooLarge'), 'error'); return; }
  OPCUA_CERT[slot] = { name: file.name, size: file.size, content_base64: await fileToBase64(file) };
  setNoAction('opcua_cert_panel', false);
  renderOpcuaCert();
}
function renderOpcuaCert() {
  const wrap = $('opcuaCertList');
  if (!wrap) return;
  const rows = [['certificate', t('opcuaCertFile')], ['private_key', t('opcuaKeyFile')]];
  wrap.innerHTML = rows.map(([slot, label]) => {
    const f = OPCUA_CERT[slot];
    return `<div class="iodd-row"><div><strong>${escapeHtml(label)}: ${f ? escapeHtml(f.name) : '—'}</strong><span>${f ? bytesLabel(f.size || 0) : t('opcuaCertMissing')}</span></div>${f ? `<button type="button" class="danger" data-cert-remove="${slot}">${t('remove')}</button>` : ''}</div>`;
  }).join('');
  wrap.querySelectorAll('[data-cert-remove]').forEach(b => b.onclick = () => { OPCUA_CERT[b.dataset.certRemove] = null; renderOpcuaCert(); });
}
function loadOpcuaCert(cert) {
  OPCUA_CERT = { certificate: cert?.certificate ? { ...cert.certificate } : null, private_key: cert?.private_key ? { ...cert.private_key } : null };
  setNoAction('opcua_cert_panel', !cert);
  renderOpcuaCert();
}
function collectOpcuaCert() {
  if (isNoAction('opcua_cert_panel')) return null;
  if (!OPCUA_CERT.certificate && !OPCUA_CERT.private_key) return null;
  const strip = f => f ? { name: f.name, size: f.size, content_base64: f.content_base64 } : null;
  return { certificate: strip(OPCUA_CERT.certificate), private_key: strip(OPCUA_CERT.private_key) };
}

function updateNetworkFields() {
  const noMode = ($('network_mode')?.value ?? '') === '';
  ['network_address', 'network_subnetmask', 'network_gateway', 'network_dns'].forEach(id => $(id)?.closest('.field-block')?.classList.toggle('param-noaction', noMode));
}

function getPemCertificateMatches(text) {
  const value = String(text || '').trim();
  if (!value) return [];
  const regex = /-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g;
  const matches = value.match(regex);
  return matches ? matches.map(s => s.trim()) : [];
}

function parsePemCertificates(text) {
  const value = String(text || '').trim();
  if (!value) return [];
  // Wichtig: nicht mehr in einzelne Array-Elemente splitten.
  // Das Backend baut daraus das Geräteformat: newvalue: ["CERT1,\nCERT2"]
  return value;
}

function updateMqttCertStatus(showOkMessage = false) {
  const status = $('mqttCertStatus');
  const textarea = $('mqtt_certs');
  if (!status || !textarea) return true;
  if (isNoAction('mqtt_certs')) { status.classList.remove('ok', 'error'); status.textContent = t('noAction'); return true; }
  const value = String(textarea.value || '').trim();
  const matches = getPemCertificateMatches(value);
  status.classList.remove('ok', 'error');
  if (!value) {
    status.textContent = t('noCerts');
    return true;
  }
  if (matches.length === 0) {
    status.textContent = LANG === 'en' ? 'Invalid: No complete PEM certificate block found.' : 'Ungültig: Kein vollständiger PEM-Zertifikatsblock gefunden.';
    status.classList.add('error');
    return false;
  }
  status.textContent = matches.length === 1
    ? (LANG === 'en' ? '1 certificate detected. Note: Many brokers/devices require the complete certificate chain here.' : '1 Zertifikat erkannt. Hinweis: Für viele Broker/Geräte muss hier die komplette Zertifikatskette eingefügt werden.')
    : (LANG === 'en' ? `${matches.length} certificates detected. Will be sent as a certificate chain.` : `${matches.length} Zertifikate erkannt. Werden als Zertifikatskette gesendet.`);
  if (showOkMessage) status.classList.add('ok');
  return true;
}

function updateMqttCmdCertStatus(showOkMessage = false) {
  const status = $('mqttCmdCertStatus');
  const textarea = $('mqttcmd_certs');
  if (!status || !textarea) return true;
  if (isNoAction('mqttcmd_certs')) { status.classList.remove('ok', 'error'); status.textContent = t('noAction'); return true; }
  const value = String(textarea.value || '').trim();
  const matches = getPemCertificateMatches(value);
  status.classList.remove('ok', 'error');
  if (!value) {
    status.textContent = t('noCerts');
    return true;
  }
  if (matches.length === 0) {
    status.textContent = LANG === 'en' ? 'Invalid: No complete PEM certificate block found.' : 'Ungültig: Kein vollständiger PEM-Zertifikatsblock gefunden.';
    status.classList.add('error');
    return false;
  }
  status.textContent = matches.length === 1
    ? (LANG === 'en' ? '1 certificate detected. Note: Many brokers/devices require the complete certificate chain here.' : '1 Zertifikat erkannt. Hinweis: Für viele Broker/Geräte muss hier die komplette Zertifikatskette eingefügt werden.')
    : (LANG === 'en' ? `${matches.length} certificates detected. Will be sent as a certificate chain.` : `${matches.length} Zertifikate erkannt. Werden als Zertifikatskette gesendet.`);
  if (showOkMessage) status.classList.add('ok');
  return true;
}

function loadDefaults() {
  const p = window.DEFAULT_PROFILE || {};
  ensureClassToggles();
  ensureNoActionToggles();
  Object.keys(CLASS_SECTIONS).forEach(section => setClassApply(section, p[section]?.apply !== false));

  IODD_FILES=JSON.parse(JSON.stringify(p.iodd?.files||[])); renderIoddList();
  FLOW_FILES=JSON.parse(JSON.stringify(p.node_red_flows?.files||[])); renderFlowList();
  PALETTE_FILES=JSON.parse(JSON.stringify(p.node_red_palettes?.files||[])); renderPaletteList();
  loadPortConfiguration(p);

  if ($('profile_name')) $('profile_name').value = p.name || '';

  const tags = p.device_tags || {};
  setTextParam('application_tag', tags.application_tag);
  setTextParam('function_tag', tags.function_tag);
  setTextParam('location_tag', tags.location_tag);

  const net = p.network || {};
  setSelectParam('network_mode', net.mode || null);
  if ($('network_address')) $('network_address').value = net.address || '';
  if ($('network_subnetmask')) $('network_subnetmask').value = net.subnetmask || '';
  if ($('network_gateway')) $('network_gateway').value = net.gateway || '';
  if ($('network_dns')) $('network_dns').value = (net.dns_servers || []).join(', ');
  updateNetworkFields();

  setTextParam('ntp_servers', p.system_ntp?.servers?.length ? p.system_ntp.servers : null, v => v.join(', '));
  setSegmentValue('ntp_action', p.system_ntp?.action || 'none');
  setSegmentValue('nodered_action', p.system_nodered?.action || 'none');
  const cred = p.system_security?.credentials_enabled;
  setSegmentValue('credentials_enabled', cred === null || cred === undefined ? 'none' : String(!!cred));
  setSegmentValue('http_action', p.connections_http?.action || 'none');

  const opc = p.connections_opcua || {};
  setTextParam('opcua_port', opc.port);
  setSelectParam('opcua_anonymous', opc.enable_anonymous === null || opc.enable_anonymous === undefined ? null : String(!!opc.enable_anonymous));
  const profiles = opc.security_profiles;
  const enabled = n => !!(profiles || []).find(x => x.name === n && x.enabled === true);
  if ($('prof_basic256')) $('prof_basic256').checked = enabled('Basic256Sha256');
  if ($('prof_aes128')) $('prof_aes128').checked = enabled('Aes128Sha256RsaOaep');
  if ($('prof_aes256')) $('prof_aes256').checked = enabled('Aes256Sha256RsaPss');
  if ($('prof_none')) $('prof_none').checked = enabled('None');
  setNoAction('opcua_profiles', !Array.isArray(profiles));
  loadOpcuaCert(opc.certificate);
  setSegmentValue('opcua_action', opc.action || 'none');

  const mq = p.connections_mqtt_client || {};
  setSelectParam('mqtt_qos', mq.qos);
  setTextParam('mqtt_clientid', mq.clientid);
  setSelectParam('mqtt_validate', mq.validate_server_certificate);
  setSegmentValue('mqtt_action', mq.action || 'none');
  setTextParam('mqtt_certs', mq.trustedservercertificates, v => Array.isArray(v) ? v.join('\n') : String(v));
  updateMqttCertStatus(false);

  const cc = p.connections_mqtt_command_channel || {};
  setTextParam('mqttcmd_brokerip', cc.brokerip);
  setTextParam('mqttcmd_brokerport', cc.brokerport);
  setSelectParam('mqttcmd_qos', cc.qos);
  setTextParam('mqttcmd_cmdtopic', cc.cmdtopic);
  setTextParam('mqttcmd_replytopic', cc.defaultreplytopic);
  setTextParam('mqttcmd_clientid', cc.clientid);
  setSelectParam('mqttcmd_secure', cc.secure);
  setSelectParam('mqttcmd_validate', cc.validate_server_certificate);
  setTextParam('mqttcmd_certs', cc.trustedservercertificates, v => Array.isArray(v) ? v.join('\n') : String(v));
  updateMqttCmdCertStatus(false);
  setTextParam('mqttcmd_user', cc.user);
  setTextParam('mqttcmd_password', cc.password);
  setSegmentValue('mqttcmd_action', cc.action || 'none');
}

function collectProfile() {
  const cred = $('credentials_enabled')?.value || 'none';
  return {
    schema_version: 2,
    name: safeName($('profile_name')?.value) || 'quick_setup_profile',

    device_tags: {
      apply: getClassApply('device_tags'),
      application_tag: getTextParam('application_tag'),
      function_tag: getTextParam('function_tag'),
      location_tag: getTextParam('location_tag')
    },

    port_configuration: { apply: getClassApply('port_configuration'), ...collectPortConfiguration() },

    system_ntp: {
      apply: getClassApply('system_ntp'),
      servers: getTextParam('ntp_servers', csvOrNull),
      action: $('ntp_action')?.value || 'none'
    },

    system_nodered: { apply: getClassApply('system_nodered'), action: $('nodered_action')?.value || 'none' },

    system_security: { apply: getClassApply('system_security'), credentials_enabled: cred === 'none' ? null : cred === 'true' },

    connections_http: { apply: getClassApply('connections_http'), action: $('http_action')?.value || 'none' },

    connections_opcua: {
      apply: getClassApply('connections_opcua'),
      port: getTextParam('opcua_port', numberOrNull),
      enable_anonymous: getSelectParam('opcua_anonymous', v => v === 'true'),
      security_profiles: isNoAction('opcua_profiles') ? null : [
        { name: 'Basic256Sha256', enabled: !!$('prof_basic256')?.checked },
        { name: 'Aes128Sha256RsaOaep', enabled: !!$('prof_aes128')?.checked },
        { name: 'Aes256Sha256RsaPss', enabled: !!$('prof_aes256')?.checked },
        { name: 'None', enabled: !!$('prof_none')?.checked }
      ],
      certificate: collectOpcuaCert(),
      action: $('opcua_action')?.value || 'none'
    },

    connections_mqtt_client: {
      apply: getClassApply('connections_mqtt_client'),
      qos: getSelectParam('mqtt_qos'),
      clientid: getTextParam('mqtt_clientid'),
      validate_server_certificate: getSelectParam('mqtt_validate'),
      trustedservercertificates: getTextParam('mqtt_certs', certsOrNull),
      action: $('mqtt_action')?.value || 'none'
    },

    connections_mqtt_command_channel: {
      apply: getClassApply('connections_mqtt_command_channel'),
      brokerip: getTextParam('mqttcmd_brokerip'),
      brokerport: getTextParam('mqttcmd_brokerport', numberOrNull),
      qos: getSelectParam('mqttcmd_qos'),
      cmdtopic: getTextParam('mqttcmd_cmdtopic'),
      defaultreplytopic: getTextParam('mqttcmd_replytopic'),
      clientid: getTextParam('mqttcmd_clientid'),
      secure: getSelectParam('mqttcmd_secure'),
      validate_server_certificate: getSelectParam('mqttcmd_validate'),
      trustedservercertificates: getTextParam('mqttcmd_certs', certsOrNull),
      user: getTextParam('mqttcmd_user'),
      password: getTextParam('mqttcmd_password'),
      action: $('mqttcmd_action')?.value || 'none'
    },

    iodd: { apply: getClassApply('iodd'), files: JSON.parse(JSON.stringify(IODD_FILES)) },
    node_red_flows: { apply: getClassApply('node_red_flows'), files: JSON.parse(JSON.stringify(FLOW_FILES)) },
    node_red_palettes: { apply: getClassApply('node_red_palettes'), files: JSON.parse(JSON.stringify(PALETTE_FILES)) },
    network: {
      apply: getClassApply('network'),
      mode: getSelectParam('network_mode', v => v),
      address: $('network_address')?.value || '',
      subnetmask: $('network_subnetmask')?.value || '',
      gateway: $('network_gateway')?.value || '',
      dns_servers: splitCsv($('network_dns')?.value)
    }
  };
}

// Entfernt Passwort und Private Key aus dem Profil (Option) und meldet, was gespeichert bleibt.
function stripSecrets(profile, exclude) {
  const removed = [], kept = [];
  const cc = profile.connections_mqtt_command_channel || {};
  const ua = profile.connections_opcua || {};
  if (cc.password) { if (exclude) { cc.password = null; removed.push(t('secretMqttPassword')); } else kept.push(t('secretMqttPassword')); }
  if (ua.certificate?.private_key) { if (exclude) { ua.certificate = null; removed.push(t('secretOpcuaKey')); } else kept.push(t('secretOpcuaKey')); }
  return { removed, kept };
}
async function saveProfile() {
  validateOpcUaUi(true);
  if (!updateMqttCertStatus(true) || !updateMqttCmdCertStatus(true)) {
    setStatus('createStatus', 'MQTT Trusted Server Certificates sind nicht im gültigen PEM-Format.', 'error');
    return;
  }
  const profile = collectProfile();
  const secrets = stripSecrets(profile, !!$('exclude_secrets')?.checked);
  setStatus('createStatus', 'Parametersatz wird gespeichert...');

  try {
    const res = await fetch('/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...profile, lang: LANG })
    });

    const data = await res.json();
    if (!data.ok) {
      setStatus('createStatus', data.error || 'Speichern fehlgeschlagen.', 'error');
      return;
    }

    const note = secrets.removed.length ? ' ' + t('secretsRemoved').replace('{items}', secrets.removed.join(', '))
      : secrets.kept.length ? ' ' + t('secretsStored').replace('{items}', secrets.kept.join(', ')) : '';
    const adjusted = (profile.name || '').trim() && data.name !== (profile.name || '').trim() ? ' ' + t('profileNameAdjusted').replace('{name}', data.name) : '';
    const saved = (LANG === 'en' ? `Parameter set saved: ${data.name} (${data.requests_count} request(s) generated).` : `Parametersatz gespeichert: ${data.name} (${data.requests_count} Request(s) generiert).`) + adjusted;
    if ($('profile_name')) $('profile_name').value = data.name;
    setStatus('createStatus', saved + note, secrets.kept.length ? 'warning' : 'ok');
    await refreshProfiles();
  } catch (e) {
    setStatus('createStatus', String(e), 'error');
  }
}

async function previewProfile() {
  validateOpcUaUi(true);
  if (!updateMqttCertStatus(true) || !updateMqttCmdCertStatus(true)) {
    setStatus('createStatus', 'MQTT Trusted Server Certificates sind nicht im gültigen PEM-Format.', 'error');
    return;
  }
  const profile = collectProfile();
  setStatus('createStatus', 'Technische Vorschau wird erstellt...');

  try {
    const res = await fetch('/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...profile, lang: LANG })
    });

    const data = await res.json();
    if (!data.ok) {
      setStatus('createStatus', data.error || 'Vorschau fehlgeschlagen.', 'error');
      return;
    }

    renderPreview(data.requests || []);
    setStatus('createStatus', `Vorschau erstellt: ${data.requests.length} Request(s).`, 'ok');
    showDialog();
  } catch (e) {
    setStatus('createStatus', String(e), 'error');
  }
}

function renderPreview(rows) {
  const wrap = $('previewWrap');
  if (!wrap) return;

  if (!rows || rows.length === 0) {
    wrap.innerHTML = `<div class="muted">${t('noRequests')}</div>`;
    return;
  }

  let html = `<table class="data-table"><thead><tr><th>#</th><th>${t('section')}</th><th>${t('label')}</th><th>ADR</th><th>Data</th><th>Auth</th></tr></thead><tbody>`;

  rows.forEach((r, i) => {
    html += `<tr>
      <td>${i + 1}</td>
      <td>${escapeHtml(trText(r.section || ''))}</td>
      <td>${escapeHtml(trText(r.label || ''))}</td>
      <td>${escapeHtml(r.adr || '')}</td>
      <td><pre>${Object.prototype.hasOwnProperty.call(r, 'data') ? escapeHtml(JSON.stringify(r.data, null, 2)) : ''}</pre></td>
      <td>${escapeHtml(r.auth_mode || '')}</td>
    </tr>`;
  });

  html += '</tbody></table>';
  wrap.innerHTML = html;
}


let LAST_DEPLOY_PROFILE = null;
function cloneProfile(profile) { return JSON.parse(JSON.stringify(profile || {})); }
function populateDeployQuickEdit(profile) {
  LAST_DEPLOY_PROFILE = cloneProfile(profile);
  $('deployQuickEdit')?.classList.remove('hidden');
  const p = profile || {};
  // Klassen mit "Keine Aktion" erscheinen leer; Quick Edit aktiviert sie nur, wenn hier etwas eingetragen wird.
  const tags = p.device_tags?.apply === false ? {} : (p.device_tags || {});
  const net = p.network?.apply === false ? {} : (p.network || {});
  if ($('qe_application_tag')) $('qe_application_tag').value = tags.application_tag ?? '';
  if ($('qe_function_tag')) $('qe_function_tag').value = tags.function_tag ?? '';
  if ($('qe_location_tag')) $('qe_location_tag').value = tags.location_tag ?? '';
  if ($('qe_network_mode')) $('qe_network_mode').value = net.mode || '';
  if ($('qe_network_address')) $('qe_network_address').value = net.address || '';
  if ($('qe_network_subnetmask')) $('qe_network_subnetmask').value = net.subnetmask || '';
  if ($('qe_network_gateway')) $('qe_network_gateway').value = net.gateway || '';
  if ($('qe_network_dns')) $('qe_network_dns').value = (net.dns_servers || []).join(', ');
}
function applyQuickEditToProfile(profile) {
  // Leeres Feld im Quick Edit = Keine Aktion für diesen Parameter.
  const edited = cloneProfile(profile);
  const val = id => { const v = $(id)?.value ?? ''; return v === '' ? null : v; };
  const tags = { application_tag: val('qe_application_tag'), function_tag: val('qe_function_tag'), location_tag: val('qe_location_tag') };
  edited.device_tags = { ...(edited.device_tags || {}), ...tags, apply: Object.values(tags).some(v => v !== null) };
  const mode = val('qe_network_mode');
  edited.network = {
    ...(edited.network || {}), apply: mode !== null, mode,
    address: $('qe_network_address')?.value || '',
    subnetmask: $('qe_network_subnetmask')?.value || '',
    gateway: $('qe_network_gateway')?.value || '',
    dns_servers: splitCsv($('qe_network_dns')?.value || '')
  };
  return edited;
}
async function refreshDeployQuickEditFromSelection() {
  const profile = await loadSelectedProfile();
  if (!profile) { LAST_DEPLOY_PROFILE = null; $('deployQuickEdit')?.classList.add('hidden'); return; }
  populateDeployQuickEdit(profile);
}
function validateOpcUaUi(showStatus = false) {
  const anon = $('opcua_anonymous');
  const none = $('prof_none');
  if (!anon || !none) return true;
  // Nur prüfbar, wenn die Security Profiles mitgeschrieben werden (sonst: Gerätezustand, ab Phase 3).
  if (anon.value === 'true' && !isNoAction('opcua_profiles') && !none.checked) {
    none.checked = true;
    if (showStatus) setStatus('createStatus', t('anonRequiresNone'), 'ok');
  }
  return true;
}

async function refreshProfiles() {
  const sel = $('deployProfiles');
  if (!sel) return;

  const res = await fetch('/profiles?lang=' + encodeURIComponent(LANG));
  const data = await res.json();

  sel.innerHTML = `<option value="">${t('selectProfile')}</option>`;
  (data.profiles || []).forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });
}

// Ergebnis der letzten erfolgreichen Vorprüfung. Die Übertragung ist nur damit freigegeben;
// jede Änderung an Host oder Zugangsdaten setzt die Freigabe zurück.
let PRECHECK = null;
const PRECHECK_INPUTS = ['deployIp', 'deployUsername', 'deployPassword', 'deployNewPassword', 'deployConfirmNewPassword'];
function deployCredentials() {
  return {
    ip: $('deployIp')?.value?.trim() || '',
    username: $('deployUsername')?.value?.trim() || '',
    password: $('deployPassword')?.value || '',
    new_password: $('deployNewPassword')?.value || '',
    confirm_new_password: $('deployConfirmNewPassword')?.value || ''
  };
}
function updateApplyButton() {
  if ($('deployApplyBtn')) $('deployApplyBtn').disabled = !PRECHECK;
}
function invalidatePrecheck() {
  if (!PRECHECK) return;
  PRECHECK = null;
  updateApplyButton();
  setStatus('deployConnectionStatus', t('precheckInvalidated'), 'warning');
}
function precheckRowsForTable(precheck) {
  return (precheck?.checks || []).map(c => ({ path: c.path, value: c.value, code: c.code, status: c.status }));
}

async function deployConnect() {
  PRECHECK = null;
  updateApplyButton();
  setStatus('deployConnectionStatus', t('precheckRunning'));
  const creds = deployCredentials();
  try {
    const res = await fetch('/deploy/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: LANG, ...creds })
    });
    const data = await readJsonResponse(res);
    const rows = precheckRowsForTable(data.precheck);
    const message = data.message || data.error || t('precheckFailed');
    if (data.ok) {
      rememberHost(creds.ip);
      PRECHECK = { ...creds, mode: data.mode, serial: data.precheck?.identity?.serial || '', hostname: data.precheck?.identity?.hostname || '' };
      const hasWarning = (data.precheck?.warnings || []).length > 0;
      setStatus('deployConnectionStatus', message, hasWarning ? 'warning' : 'ok');
    } else {
      setStatus('deployConnectionStatus', message, 'error');
    }
    renderDeployTable(rows.length ? rows : [{ path: t('precheck'), value: message, code: res.status, status: data.ok ? 'OK' : t('errorStatus') }]);
  } catch (e) {
    setStatus('deployConnectionStatus', String(e), 'error');
    renderDeployTable([{ path: t('precheck'), value: String(e), code: 500, status: t('errorStatus') }]);
  } finally {
    updateApplyButton();
  }
}

async function loadSelectedProfile() {
  const name = $('deployProfiles')?.value;
  if (!name) return null;

  const res = await fetch(`/profiles/load/${encodeURIComponent(name)}?lang=${encodeURIComponent(LANG)}`);
  const data = await res.json();
  return data.ok ? data.config : null;
}

async function deployDryRun() {
  let profile = await loadSelectedProfile();
  if (!profile) {
    renderDeployTable([{ path: 'Profil', value: 'Bitte Profil wählen', code: '', status: 'Fehler' }]);
    return;
  }
  profile = applyQuickEditToProfile(profile);

  setStatus('deployConnectionStatus', t('dryRunReading'));
  try {
    const res = await fetch('/config/dry-run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // readback: Ist-Werte vom Gerät lesen (nur lesend), sofern erreichbar und angemeldet.
      body: JSON.stringify({ lang: LANG, config: profile, readback: true, ...deployCredentials() })
    });
    const data = await readJsonResponse(res);
    if (!data.ok) {
      setStatus('deployConnectionStatus', data.error || 'Dry Run fehlgeschlagen', 'error');
      return;
    }
    setStatus('deployConnectionStatus', data.info || 'Dry Run erfolgreich erstellt.', data.readback ? 'ok' : 'warning');
    renderDryRunTable(data.preview || []);
  } catch (e) {
    setStatus('deployConnectionStatus', String(e), 'error');
  }
}

function formatValue(v) {
  if (v === undefined) return '';
  if (v === null) return '—';
  return typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v);
}
function statusRowClass(status) {
  return ({ 'OK': 'row-ok', 'Fehler': 'row-error', 'Error': 'row-error', 'Warnung': 'row-warning', 'Warning': 'row-warning',
            'Unverändert': 'row-skipped', 'Unchanged': 'row-skipped', 'Ändern': 'row-change', 'Change': 'row-change',
            'Schreiben (ohne Vergleich)': 'row-change', 'Write (no comparison)': 'row-change' })[String(status || '')] || '';
}
function renderDryRunTable(rows) {
  const wrap = $('deployOutputTableWrap');
  if (!wrap) return;
  if (!rows.length) { wrap.innerHTML = `<div class="muted">${t('noRequests')}</div>`; return; }
  let html = `<table class="data-table"><thead><tr><th>#</th><th>${t('status')}</th><th>${t('path')}</th><th>${t('currentValue')}</th><th>${t('targetValue')}</th></tr></thead><tbody>`;
  rows.forEach((r, i) => {
    const target = r.target !== undefined ? r.target : r.data;
    html += `<tr class="${statusRowClass(r.status)}">
      <td>${i + 1}</td>
      <td>${escapeHtml(r.status || t('planned'))}${r.reason ? `<div class="muted small">${escapeHtml(r.reason)}</div>` : ''}</td>
      <td>${escapeHtml(trText((r.label || r.section) + ' → ' + r.adr))}</td>
      <td><pre>${escapeHtml(r.current !== undefined ? formatValue(r.current) : '')}</pre></td>
      <td><pre>${escapeHtml(formatValue(target))}</pre></td>
    </tr>`;
  });
  wrap.innerHTML = html + '</tbody></table>';
}

async function deployApply() {
  let profile = await loadSelectedProfile();
  if (!profile) {
    renderDeployTable([{ path: 'Profil', value: 'Bitte Profil wählen', code: '', status: 'Fehler' }]);
    return;
  }
  if (!PRECHECK) {
    setStatus('deployConnectionStatus', t('precheckRequired'), 'error');
    updateApplyButton();
    return;
  }
  profile = applyQuickEditToProfile(profile);
  if ($('deployApplyBtn')) $('deployApplyBtn').disabled = true;
  initDeployLiveTable();
  setStatus('deployConnectionStatus', 'Konfiguration wird übertragen... Live-Feedback aktiv.');
  const creds = deployCredentials();
  let passwordChanged = false;
  try {
    const res = await fetch('/config/apply_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lang: LANG,
        ...creds,
        expected_serial: PRECHECK.serial || '',
        config: profile
      })
    });
    if (!res.ok || !res.body) {
      const text = await res.text();
      setStatus('deployConnectionStatus', text || 'Konfiguration fehlgeschlagen.', 'error');
      appendDeployRow({ path: 'Apply', value: text, code: res.status, status: 'Fehler' });
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalOk = true;
    let finalWarning = false;
    let finalMessage = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        let msg;
        try { msg = JSON.parse(line); }
        catch (e) {
          appendDeployRow({ path: 'Stream Parser', value: line, code: 500, status: 'Fehler' });
          finalOk = false;
          continue;
        }
        if (msg.type === 'status') {
          setStatus('deployConnectionStatus', msg.message || 'Konfiguration läuft...');
        } else if (msg.type === 'step_start') {
          setStatus('deployConnectionStatus', msg.message || msg.path || 'Request läuft...');
        } else if (msg.type === 'row') {
          appendDeployRow(msg);
          if (!msg.warning && !isSuccessCode(msg.code, msg.request_adr)) finalOk = false;
          if (msg.request_adr === '/security/password/setdata' && String(msg.code) === '200') passwordChanged = true;
        } else if (msg.type === 'done') {
          finalOk = !!msg.ok;
          finalWarning = !!msg.warning;
          finalMessage = msg.message || msg.error || 'Konfiguration abgeschlossen.';
        }
      }
    }
    if (buffer.trim()) {
      try {
        const msg = JSON.parse(buffer);
        if (msg.type === 'row') appendDeployRow(msg);
        if (msg.type === 'done') {
          finalOk = !!msg.ok;
          finalWarning = !!msg.warning;
          finalMessage = msg.message || msg.error || 'Konfiguration abgeschlossen.';
        }
      } catch (e) {
        appendDeployRow({ path: 'Stream Parser', value: buffer, code: 500, status: 'Fehler' });
        finalOk = false;
      }
    }
    setStatus('deployConnectionStatus', finalMessage || 'Konfiguration abgeschlossen.', finalOk ? (finalWarning ? 'warning' : 'ok') : 'error');
  } catch (e) {
    setStatus('deployConnectionStatus', String(e), 'error');
    appendDeployRow({ path: 'Apply', value: String(e), code: 500, status: 'Fehler' });
  } finally {
    // Nach einem Passwortwechsel gilt ab sofort das neue Passwort.
    if (passwordChanged && creds.new_password) {
      if ($('deployPassword')) $('deployPassword').value = creds.new_password;
      if ($('deployNewPassword')) $('deployNewPassword').value = '';
      if ($('deployConfirmNewPassword')) $('deployConfirmNewPassword').value = '';
    }
    // Der Gerätezustand hat sich geändert (Passwort, ggf. Netzwerk): neue Vorprüfung erforderlich.
    PRECHECK = null;
    updateApplyButton();
  }
}


function initDeployLiveTable() {
  const wrap = $('deployOutputTableWrap');
  if (!wrap) return;
  wrap.innerHTML = `<table class="data-table"><thead><tr><th>#</th><th>Code</th><th>${t('status')}</th><th>${t('path')}</th><th>${t('value')}</th></tr></thead><tbody></tbody></table>`;
}

function appendDeployRow(row) {
  const wrap = $('deployOutputTableWrap');
  if (!wrap) return;
  if (!wrap.querySelector('tbody')) initDeployLiveTable();
  const tbody = wrap.querySelector('tbody');
  const tr = document.createElement('tr');
  const status = String(row.status || '');
  const cls = statusRowClass(status);
  if (cls) tr.classList.add(cls);
  let valueText;
  if (row.decision) {
    // Zurückgelesener Ist-Wert -> Soll-Wert
    valueText = `${t('currentValue')}: ${formatValue(row.current)}\n${t('targetValue')}: ${formatValue(row.target)}`;
  } else {
    const value = row.request_data ?? row.value ?? '';
    valueText = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value ?? '');
  }
  if (row.reason) valueText += `\n(${row.reason})`;
  tr.innerHTML = `
    <td>${escapeHtml(String(row.index ?? ''))}</td>
    <td>${escapeHtml(String(row.code ?? ''))}</td>
    <td>${escapeHtml(trText(status))}</td>
    <td>${escapeHtml(trText(row.path || ''))}</td>
    <td><pre>${escapeHtml(valueText)}</pre></td>
  `;
  tbody.appendChild(tr);
  wrap.scrollTop = wrap.scrollHeight;
}

function renderDeployTable(rows) {
  const wrap = $('deployOutputTableWrap');
  if (!wrap) return;

  if (!rows || rows.length === 0) {
    wrap.innerHTML = `<div class="muted">${t('noOutput')}</div>`;
    return;
  }

  let html = `<table class="data-table"><thead><tr><th>Code</th><th>${t('status')}</th><th>${t('path')}</th><th>${t('value')}</th></tr></thead><tbody>`;

  const rowClass = s => ({ 'OK': 'row-ok', 'Fehler': 'row-error', 'Error': 'row-error', 'Warnung': 'row-warning', 'Warning': 'row-warning' })[String(s || '')] || '';
  rows.forEach(r => {
    html += `<tr class="${rowClass(r.status)}">
      <td>${escapeHtml(String(r.code ?? ''))}</td>
      <td>${escapeHtml(trText(r.status || ''))}</td>
      <td>${escapeHtml(trText(r.path || ''))}</td>
      <td>${escapeHtml(typeof r.value === 'object' ? JSON.stringify(r.value) : String(r.value ?? ''))}</td>
    </tr>`;
  });

  html += '</tbody></table>';
  wrap.innerHTML = html;
}


async function refreshProfileManager() {
  const wrap = $('profileManagerList');
  if (!wrap) return;
  try {
    const res = await fetch('/profiles?lang=' + encodeURIComponent(LANG));
    const data = await res.json();
    const profiles = data.profiles || [];
    if (profiles.length === 0) {
      wrap.innerHTML = `<div class="muted">${t('noProfiles')}</div>`;
      return;
    }
    wrap.innerHTML = '';
    profiles.forEach(name => {
      const row = document.createElement('div');
      row.className = 'profile-manager-row';
      row.innerHTML = `<div class="profile-manager-name">${escapeHtml(name)}</div><div class="profile-manager-actions"><button type="button" class="ghost" data-action="edit" data-name="${escapeHtml(name)}">${t('edit')}</button><button type="button" class="ghost" data-action="copy" data-name="${escapeHtml(name)}">${t('copy')}</button><button type="button" class="danger" data-action="delete" data-name="${escapeHtml(name)}">${t('delete')}</button></div>`;
      wrap.appendChild(row);
    });
  } catch (e) { setStatus('profileManagerStatus', String(e), 'error'); }
}
async function editManagedProfile(name) {
  const res = await fetch(`/profiles/load/${encodeURIComponent(name)}?lang=${encodeURIComponent(LANG)}`);
  const data = await res.json();
  if (!data.ok) { setStatus('profileManagerStatus', data.error || t('profileLoadFailed'), 'error'); return; }
  window.DEFAULT_PROFILE = data.config;
  loadDefaults();
  validateOpcUaUi(false);
  showView('create');
  setStatus('createStatus', LANG === 'en' ? `Profile loaded for editing: ${name}` : `Profil zum Bearbeiten geladen: ${name}`, 'ok');
}
async function copyManagedProfile(name) {
  const newName = prompt(LANG === 'en' ? 'New profile name:' : 'Neuer Profilname:', `${name}_copy`);
  if (!newName) return;
  const copyRequest = overwrite => fetch(`/profiles/copy/${encodeURIComponent(name)}?lang=${encodeURIComponent(LANG)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lang: LANG, new_name: newName, overwrite }) }).then(r => r.json());
  let data = await copyRequest(false);
  if (!data.ok && data.exists) {
    if (!confirm(t('profileOverwriteConfirm').replace('{name}', data.name))) { setStatus('profileManagerStatus', t('copyCancelled')); return; }
    data = await copyRequest(true);
  }
  if (!data.ok) { setStatus('profileManagerStatus', data.error || t('copyFailed'), 'error'); return; }
  await refreshProfileManager(); await refreshProfiles();
  await editManagedProfile(data.name);
  if ($('profile_name')) $('profile_name').value = data.name;
  setStatus('createStatus', LANG === 'en' ? `Profile copy opened for editing: ${data.name}` : `Profilkopie zum Bearbeiten geöffnet: ${data.name}`, 'ok');
}
async function deleteManagedProfile(name) {
  if (!confirm(LANG === 'en' ? `Delete profile "${name}"?` : `Profil "${name}" löschen?`)) return;
  const res = await fetch(`/profiles/delete/${encodeURIComponent(name)}?lang=${encodeURIComponent(LANG)}`, { method: 'DELETE' });
  const data = await res.json();
  if (!data.ok) { setStatus('profileManagerStatus', data.error || t('deleteFailed'), 'error'); return; }
  setStatus('profileManagerStatus', LANG === 'en' ? `Profile deleted: ${name}` : `Profil gelöscht: ${name}`, 'ok');
  await refreshProfileManager(); await refreshProfiles();
}
function handleProfileManagerClick(event) {
  const btn = event.target.closest('button[data-action]');
  if (!btn) return;
  const action = btn.getAttribute('data-action');
  const name = btn.getAttribute('data-name');
  if (action === 'edit') editManagedProfile(name);
  if (action === 'copy') copyManagedProfile(name);
  if (action === 'delete') deleteManagedProfile(name);
}

document.addEventListener('DOMContentLoaded', () => {
  try { initSegmented(); } catch (e) { console.error('initSegmented Fehler:', e); }
  applyTranslations();
  restoreHost();
  $('langToggleBtn')?.addEventListener('click', () => setLang(LANG === 'de' ? 'en' : 'de'));

  // Navigation
  $('topHomeBtn')?.addEventListener('click', () => showView('home'));
  $('openCreateBtn')?.addEventListener('click', () => showView('create'));
  $('openDeployBtn')?.addEventListener('click', async () => {
    showView('deploy');
    await refreshProfiles();
  });
  $('openPalettePackagerBtn')?.addEventListener('click', async () => { showView('packager'); await refreshPalettePackages(); });
    $('openProfileManagerBtn')?.addEventListener('click', async () => {
    showView('profiles');
    await refreshProfileManager();
  });
  $('backHome1')?.addEventListener('click', () => showView('home'));
  $('backHome2')?.addEventListener('click', () => showView('home'));
  $('backHome3')?.addEventListener('click', () => showView('home'));
    $('backHome4')?.addEventListener('click', () => showView('home'));
    $('createPalettePackageBtn')?.addEventListener('click', createPalettePackage);

  // Create
  $('saveBtn')?.addEventListener('click', saveProfile);
  $('saveBtnBottom')?.addEventListener('click', saveProfile);
  $('previewBtn')?.addEventListener('click', previewProfile);
  $('closePreviewBtn')?.addEventListener('click', closeDialog);
  $('mqtt_certs')?.addEventListener('input', () => updateMqttCertStatus(false));
  $('mqttCertValidateBtn')?.addEventListener('click', () => {
    const ok = updateMqttCertStatus(true);
    setStatus('createStatus', ok ? 'MQTT Zertifikate erfolgreich geprüft.' : 'MQTT Zertifikate sind ungültig.', ok ? 'ok' : 'error');
  });
  $('mqttCertClearBtn')?.addEventListener('click', () => {
    if ($('mqtt_certs')) $('mqtt_certs').value = '';
    updateMqttCertStatus(false);
    setStatus('createStatus', 'MQTT Zertifikate gelöscht.');
  });
  $('opcua_anonymous')?.addEventListener('change', () => validateOpcUaUi(true));
  $('network_mode')?.addEventListener('change', updateNetworkFields);
  $('opcua_cert_file')?.addEventListener('change', e => handleOpcuaCertFile(e, 'certificate'));
  $('opcua_key_file')?.addEventListener('change', e => handleOpcuaCertFile(e, 'private_key'));
  $('prof_none')?.addEventListener('change', () => {
    if (!$('prof_none')?.checked && $('opcua_anonymous')?.value === 'true') {
      $('opcua_anonymous').value = 'false';
      setStatus('createStatus', t('anonDisabledNone'), 'ok');
    }
  });
  $('mqttcmd_certs')?.addEventListener('input', () => updateMqttCmdCertStatus(false));
  $('mqttCmdCertValidateBtn')?.addEventListener('click', () => {
    const ok = updateMqttCmdCertStatus(true);
    setStatus('createStatus', ok ? 'MQTT Command Channel Zertifikate erfolgreich geprüft.' : 'MQTT Command Channel Zertifikate sind ungültig.', ok ? 'ok' : 'error');
  });
  $('mqttCmdCertClearBtn')?.addEventListener('click', () => {
    if ($('mqttcmd_certs')) $('mqttcmd_certs').value = '';
    updateMqttCmdCertStatus(false);
    setStatus('createStatus', 'MQTT Command Channel Zertifikate gelöscht.');
  });


  // Deploy
  $('deployReloadProfilesBtn')?.addEventListener('click', refreshProfiles);
  $('deployProfiles')?.addEventListener('change', refreshDeployQuickEditFromSelection);
  $('profileManagerReloadBtn')?.addEventListener('click', refreshProfileManager);
  $('profileManagerList')?.addEventListener('click', handleProfileManagerClick);
  $('deployConnectBtn')?.addEventListener('click', deployConnect);
  $('deployDryRunBtn')?.addEventListener('click', deployDryRun);
  $('deployApplyBtn')?.addEventListener('click', deployApply);
  PRECHECK_INPUTS.forEach(id => $(id)?.addEventListener('input', invalidatePrecheck));

  updateApplyButton();

  try { loadDefaults(); } catch (e) { console.error('loadDefaults Fehler:', e); }

  showView('home');
});