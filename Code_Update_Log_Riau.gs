const DB_SHEET = 'DATABASE_BERITA';
const LOG_SHEET = 'UPDATE_LOG';

function jsonOutput(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getDbSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(DB_SHEET);
  if (!sh) {
    sh = ss.insertSheet(DB_SHEET);
    sh.appendRow([
      'Tanggal','Judul','Link','Sumber','Ringkasan',
      'Sektor PDRB','Sentimen','Kabupaten/Kota','Perusahaan','Collected At'
    ]);
  }
  return sh;
}

function getLogSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(LOG_SHEET);
  if (!sh) {
    sh = ss.insertSheet(LOG_SHEET);
    sh.appendRow([
      'Timestamp','Status','Received','Inserted','Duplicate','Message'
    ]);
  }
  return sh;
}

function doGet(e) {
  try {
    const sheetName = (e && e.parameter && e.parameter.sheet)
      ? e.parameter.sheet : DB_SHEET;

    const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
    if (!sh) return jsonOutput({ok:false,error:'Sheet tidak ditemukan: '+sheetName});

    return jsonOutput({
      ok:true,
      sheet:sheetName,
      data:sh.getDataRange().getValues()
    });
  } catch (err) {
    return jsonOutput({ok:false,error:String(err)});
  }
}

function doPost(e) {
  const lock = LockService.getScriptLock();

  try {
    lock.waitLock(30000);

    const body = e && e.postData && e.postData.contents
      ? e.postData.contents : '';

    if (!body) return jsonOutput({ok:false,error:'POST body kosong'});

    let payload;
    try {
      payload = JSON.parse(body);
    } catch (err) {
      return jsonOutput({ok:false,error:'Body bukan JSON valid',detail:String(err)});
    }

    const incoming = Array.isArray(payload)
      ? payload
      : (Array.isArray(payload.data) ? payload.data : []);

    if (incoming.length === 0) {
      return jsonOutput({
        ok:true,received:0,inserted:0,duplicate:0,
        message:'Tidak ada data'
      });
    }

    const sh = getDbSheet();
    const lastRow = sh.getLastRow();
    const lastCol = sh.getLastColumn();

    const existingLinks = new Set();
    const existingTitles = new Set();

    if (lastRow >= 2) {
      sh.getRange(2,1,lastRow-1,lastCol).getValues().forEach(row => {
        const title = normalizeTitle(row[1]);
        const link = String(row[2] || '').trim();
        if (title) existingTitles.add(title);
        if (link) existingLinks.add(link);
      });
    }

    const rows = [];
    let duplicate = 0;

    incoming.forEach(item => {
      const title = String(item['Judul'] || '').trim();
      const link = String(item['Link'] || '').trim();
      if (!title && !link) return;

      const titleKey = normalizeTitle(title);

      if ((link && existingLinks.has(link)) ||
          (titleKey && existingTitles.has(titleKey))) {
        duplicate++;
        return;
      }

      if (link) existingLinks.add(link);
      if (titleKey) existingTitles.add(titleKey);

      rows.push([
        item['Tanggal'] || '',
        title,
        link,
        item['Sumber'] || '',
        item['Ringkasan'] || '',
        item['Sektor PDRB'] || '',
        item['Sentimen'] || '',
        item['Kabupaten/Kota'] || '',
        item['Perusahaan'] || '',
        item['Collected At'] || new Date()
      ]);
    });

    if (rows.length > 0) {
      sh.getRange(sh.getLastRow()+1,1,rows.length,rows[0].length)
        .setValues(rows);
    }

    getLogSheet().appendRow([
      new Date(),'SUCCESS',incoming.length,rows.length,duplicate,
      rows.length > 0 ? 'Update database berhasil' : 'Tidak ada berita baru'
    ]);

    return jsonOutput({
      ok:true,
      received:incoming.length,
      inserted:rows.length,
      duplicate:duplicate,
      message:rows.length > 0 ? 'Data berhasil ditambahkan' : 'Tidak ada data baru'
    });

  } catch (err) {
    try {
      getLogSheet().appendRow([new Date(),'ERROR',0,0,0,String(err)]);
    } catch (ignore) {}

    return jsonOutput({ok:false,error:String(err)});
  } finally {
    try { lock.releaseLock(); } catch (ignore) {}
  }
}

function normalizeTitle(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/https?:\/\/\S+/g,'')
    .replace(/[^\p{L}\p{N}\s]/gu,' ')
    .replace(/\s+/g,' ')
    .trim();
}

function setupSheets() {
  getDbSheet();
  getLogSheet();
  return 'DATABASE_BERITA dan UPDATE_LOG siap.';
}
