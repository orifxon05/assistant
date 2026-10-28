const path = require('path');
try { require('dotenv').config({ path: path.join(__dirname, '..', '.env') }); } catch (e) {}
try { require('dotenv').config(); } catch (e) {}
const express = require('express');
const crypto = require('crypto');
const { randomUUID } = require('crypto');
const { query, initDb } = require('./db');


const app = express();
app.use(express.json({ limit: '5mb' }));
app.use(express.static(path.join(__dirname, 'public')));

function validateTelegramInitData(initData) {
  const botToken = process.env.TELEGRAM_BOT_TOKEN || process.env.BOT_TOKEN;
  if (!botToken || !initData) return null;
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  const authDate = Number(params.get('auth_date') || 0);
  if (!hash || !authDate) return null;
  // Reject old initData (older than 24 hours) and future timestamps.
  const now = Math.floor(Date.now() / 1000);
  if (authDate > now + 60 || now - authDate > 86400) return null;
  params.delete('hash');
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');
  const secretKey = crypto.createHmac('sha256', 'WebAppData').update(botToken).digest();
  const calculated = crypto.createHmac('sha256', secretKey).update(dataCheckString).digest('hex');
  const a = Buffer.from(calculated, 'hex');
  const b = Buffer.from(hash, 'hex');
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    const user = JSON.parse(params.get('user') || '{}');
    if (!user.id) return null;
    return {
      id: String(user.id),
      first_name: String(user.first_name || ''),
      username: String(user.username || '')
    };
  } catch { return null; }
}

const DEFAULT_ACCESS_KEY = (process.env.TOYONA_ACCESS_KEY || 'orifxon').toLowerCase().trim();
const ADMIN_ID = String(process.env.ADMIN_ID || '7813512925').trim();

async function auth(req, res, next) {
  try {
    let user = null;

    if (process.env.DEV_AUTH === 'true' && process.env.NODE_ENV !== 'production') {
      user = {
        id: ADMIN_ID,
        first_name: 'Orifxon',
        username: 'orifxon05'
      };
    } else {
      // 1. Check Telegram WebApp initData
      const initData = req.get('X-Telegram-Init-Data');
      if (initData) {
        user = validateTelegramInitData(initData);
      }

      // 2. Check Web link access key / token / PIN (for opening via direct link in any browser/phone)
      if (!user) {
        const key = String(
          req.get('X-Toyona-Key') ||
          req.get('X-Toyona-Auth') ||
          req.query.key ||
          req.query.token ||
          req.body?.authKey ||
          ''
        ).toLowerCase().trim();

        if (key && (key === DEFAULT_ACCESS_KEY || key === ADMIN_ID || key === '7813' || key === 'orifxon')) {
          user = {
            id: ADMIN_ID,
            first_name: 'Orifxon',
            username: 'orifxon05'
          };
        }
      }

      if (!user) {
        return res.status(401).json({
          error: 'Kirish uchun ruxsat berilmadi.',
          auth_required: true,
          message: 'Mini App’ni Telegram orqali oching yoki kirish kalitini (parol) kiriting.'
        });
      }
    }

    req.user = user;
    await query(
      `INSERT INTO app_users(telegram_id, first_name, username) VALUES($1,$2,$3)
       ON CONFLICT(telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name, username=EXCLUDED.username`,
      [req.user.id, req.user.first_name, req.user.username]
    );
    await query(`INSERT INTO settings(telegram_id) VALUES($1) ON CONFLICT(telegram_id) DO NOTHING`, [req.user.id]);
    next();
  } catch (e) {
    console.error('[TOYONA AUTH XATO]:', e);
    res.status(500).json({ error: 'Baza bilan ulanishda xatolik: ' + (e.message || String(e)) });
  }
}
app.use('/api', auth);

process.on('uncaughtException', (err) => {
  console.error('[TOYONA UNCAUGHT EXCEPTION]:', err.message || err);
});
process.on('unhandledRejection', (reason) => {
  console.error('[TOYONA UNHANDLED REJECTION]:', reason);
});

const asyncHandler = fn => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(err => {
    console.error(`[API XATO ${req.method} ${req.originalUrl}]:`, err.message || err);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message || 'Serverda xatolik yuz berdi.' });
    }
  });
};

const own = (table, id, owner) => query(`SELECT * FROM ${table} WHERE id=$1 AND telegram_id=$2`, [id, owner]);

app.get('/api/bootstrap', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const [settings, friends, weddings, gifts] = await Promise.all([
    query('SELECT current_price FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1 ORDER BY name COLLATE "C"', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1 ORDER BY wedding_date DESC NULLS LAST, created_at DESC', [owner]),
    query('SELECT * FROM gifts WHERE telegram_id=$1', [owner])
  ]);
  res.json({
    user: req.user,
    currentPrice: Number(settings.rows[0]?.current_price || 150000),
    friends: friends.rows,
    weddings: weddings.rows.map(w => ({...w, meat_price: Number(w.meat_price), min_kg: Number(w.min_kg)})),
    gifts: gifts.rows.map(g => ({...g, amount: Number(g.amount), meat_price: Number(g.meat_price)}))
  });
}));

app.put('/api/settings', asyncHandler(async (req, res) => {
  const price = Number(req.body.currentPrice);
  if (!Number.isSafeInteger(price) || price < 1) return res.status(400).json({ error: 'Narx musbat butun son bo‘lishi kerak.' });
  await query('UPDATE settings SET current_price=$1, updated_at=NOW() WHERE telegram_id=$2', [price, req.user.id]);
  res.json({ ok: true });
}));

app.post('/api/friends', asyncHandler(async (req, res) => {
  const name = String(req.body.name || '').trim();
  if (!name || name.length > 100) return res.status(400).json({ error: 'Ism 1–100 belgi bo‘lishi kerak.' });
  const id = randomUUID();
  await query('INSERT INTO friends(id, telegram_id, name) VALUES($1,$2,$3)', [id, req.user.id, name]);
  res.status(201).json({ id, name });
}));

app.put('/api/friends/:id', asyncHandler(async (req, res) => {
  const name = String(req.body.name || '').trim();
  if (!name || name.length > 100) return res.status(400).json({ error: 'Ism 1–100 belgi bo‘lishi kerak.' });
  const result = await query('UPDATE friends SET name=$1 WHERE id=$2 AND telegram_id=$3 RETURNING *', [name, req.params.id, req.user.id]);
  if (!result.rowCount) return res.status(404).json({ error: 'Oshna topilmadi.' });
  res.json(result.rows[0]);
}));

app.delete('/api/friends/:id', asyncHandler(async (req, res) => {
  const result = await query('DELETE FROM friends WHERE id=$1 AND telegram_id=$2 RETURNING id', [req.params.id, req.user.id]);
  if (!result.rowCount) return res.status(404).json({ error: 'Oshna topilmadi.' });
  res.json({ ok: true });
}));

app.post('/api/weddings', asyncHandler(async (req, res) => {
  const rawFriend = req.body.friendId;
  const friendId = (rawFriend && typeof rawFriend === 'string' && rawFriend.trim().length > 10) ? rawFriend.trim() : null;
  const name = String(req.body.name || '').trim();
  const rawDate = req.body.date ? String(req.body.date).trim() : null;
  const date = (rawDate && rawDate !== 'null' && rawDate !== 'undefined') ? rawDate : null;
  const price = Number(req.body.meatPrice);
  const minKg = Number(req.body.minKg ?? 2);
  const note = String(req.body.note || '').trim().slice(0, 500);
  if (!name || name.length > 100 || !Number.isSafeInteger(price) || price < 1 || !Number.isFinite(minKg) || minKg < 0 || minKg > 100) {
    return res.status(400).json({ error: 'To‘y nomi, narx yoki minimum qiymatini tekshiring.' });
  }
  if (friendId) {
    const f = await query('SELECT id FROM friends WHERE id=$1 AND telegram_id=$2', [friendId, req.user.id]);
    if (!f.rowCount) return res.status(400).json({ error: 'Tanlangan oshna topilmadi.' });
  }
  const id = randomUUID();
  await query(
    'INSERT INTO weddings(id,telegram_id,friend_id,name,wedding_date,meat_price,min_kg,note) VALUES($1,$2,$3,$4,$5,$6,$7,$8)',
    [id, req.user.id, friendId, name, date, price, minKg, note]
  );
  res.status(201).json({ id });
}));

app.put('/api/weddings/:id', asyncHandler(async (req, res) => {
  const rawFriend = req.body.friendId;
  const friendId = (rawFriend && typeof rawFriend === 'string' && rawFriend.trim().length > 10) ? rawFriend.trim() : null;
  const name = String(req.body.name || '').trim();
  const rawDate = req.body.date ? String(req.body.date).trim() : null;
  const date = (rawDate && rawDate !== 'null' && rawDate !== 'undefined') ? rawDate : null;
  const price = Number(req.body.meatPrice);
  const minKg = Number(req.body.minKg);
  const note = String(req.body.note || '').trim().slice(0, 500);
  if (!name || name.length > 100 || !Number.isSafeInteger(price) || price < 1 || !Number.isFinite(minKg) || minKg < 0 || minKg > 100) return res.status(400).json({ error: 'Maydonlarni tekshiring.' });
  const result = await query(
    `UPDATE weddings SET name=$1,wedding_date=$2,meat_price=$3,min_kg=$4,friend_id=$5,note=$6
     WHERE id=$7 AND telegram_id=$8 RETURNING id`,
    [name,date,price,minKg,friendId, note, req.params.id, req.user.id]
  );
  if (!result.rowCount) return res.status(404).json({ error: 'To‘y topilmadi.' });
  res.json({ ok: true });
}));

app.delete('/api/weddings/:id', asyncHandler(async (req, res) => {
  const result = await query('DELETE FROM weddings WHERE id=$1 AND telegram_id=$2 RETURNING id', [req.params.id, req.user.id]);
  if (!result.rowCount) return res.status(404).json({ error: 'To‘y topilmadi.' });
  res.json({ ok: true });
}));


app.put('/api/gifts', asyncHandler(async (req, res) => {
  const weddingId = String(req.body.weddingId || '').trim();
  const friendId = String(req.body.friendId || '').trim();
  const amount = Number(req.body.amount);
  const note = String(req.body.note || '').trim().slice(0, 500);
  if (!weddingId || !friendId || weddingId.length < 10 || friendId.length < 10) {
    return res.status(400).json({ error: 'To‘y yoki oshna ma’lumotlari to‘liq emas.' });
  }
  if (!Number.isSafeInteger(amount) || amount < 0) return res.status(400).json({ error: 'Summa 0 yoki musbat butun son bo‘lishi kerak.' });
  const wedding = await query('SELECT meat_price FROM weddings WHERE id=$1 AND telegram_id=$2', [weddingId, req.user.id]);
  const friend = await query('SELECT id FROM friends WHERE id=$1 AND telegram_id=$2', [friendId, req.user.id]);
  if (!wedding.rowCount || !friend.rowCount) return res.status(400).json({ error: 'To‘y yoki oshna topilmadi.' });
  if (amount === 0) {
    await query('DELETE FROM gifts WHERE wedding_id=$1 AND friend_id=$2 AND telegram_id=$3', [weddingId, friendId, req.user.id]);
    return res.json({ ok: true, deleted: true });
  }
  const id = randomUUID();
  await query(
    `INSERT INTO gifts(id,telegram_id,wedding_id,friend_id,amount,meat_price,note)
     VALUES($1,$2,$3,$4,$5,$6,$7)
     ON CONFLICT(wedding_id,friend_id) DO UPDATE SET amount=EXCLUDED.amount,note=EXCLUDED.note,updated_at=NOW()
     WHERE gifts.telegram_id=EXCLUDED.telegram_id`,
    [id, req.user.id, weddingId, friendId, amount, Number(wedding.rows[0].meat_price), note]
  );
  res.json({ ok: true });
}));

app.get('/api/backup', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const [settings, friends, weddings, gifts] = await Promise.all([
    query('SELECT * FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM gifts WHERE telegram_id=$1', [owner])
  ]);
  res.json({
    telegram_id: owner,
    exported_at: new Date().toISOString(),
    settings: settings.rows[0] || null,
    friends: friends.rows,
    weddings: weddings.rows,
    gifts: gifts.rows
  });
}));

app.post('/api/restore', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const { settings, friends, weddings, gifts } = req.body || {};
  if (settings && settings.current_price) {
    await query(
      `INSERT INTO settings(telegram_id, current_price, updated_at) VALUES($1,$2,NOW())
       ON CONFLICT(telegram_id) DO UPDATE SET current_price=EXCLUDED.current_price, updated_at=NOW()`,
      [owner, Number(settings.current_price)]
    );
  }
  if (Array.isArray(friends)) {
    for (const f of friends) {
      if (f.id && f.name) {
        await query(
          `INSERT INTO friends(id, telegram_id, name) VALUES($1,$2,$3)
           ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name`,
          [f.id, owner, f.name]
        );
      }
    }
  }
  if (Array.isArray(weddings)) {
    for (const w of weddings) {
      if (w.id && w.name) {
        await query(
          `INSERT INTO weddings(id, telegram_id, friend_id, name, wedding_date, meat_price, min_kg, note)
           VALUES($1,$2,$3,$4,$5,$6,$7,$8)
           ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name, wedding_date=EXCLUDED.wedding_date, meat_price=EXCLUDED.meat_price, min_kg=EXCLUDED.min_kg, friend_id=EXCLUDED.friend_id, note=EXCLUDED.note`,
          [w.id, owner, w.friend_id || null, w.name, w.wedding_date || null, Number(w.meat_price), Number(w.min_kg || 2), w.note || '']
        );
      }
    }
  }
  if (Array.isArray(gifts)) {
    for (const g of gifts) {
      if (g.wedding_id && g.friend_id && g.amount) {
        await query(
          `INSERT INTO gifts(id, telegram_id, wedding_id, friend_id, amount, meat_price, note)
           VALUES($1,$2,$3,$4,$5,$6,$7)
           ON CONFLICT(wedding_id, friend_id) DO UPDATE SET amount=EXCLUDED.amount, meat_price=EXCLUDED.meat_price, note=EXCLUDED.note`,
          [g.id || randomUUID(), owner, g.wedding_id, g.friend_id, Number(g.amount), Number(g.meat_price), g.note || '']
        );
      }
    }
  }
  res.json({ ok: true, message: 'Baza muvaffaqiyatli tiklandi.' });
}));

function buildToyonaReport(settings, friends, weddings, gifts) {
  const currentPrice = Number(settings.rows[0]?.current_price || 150000);
  const moneyFmt = n => Math.round(Number(n) || 0).toLocaleString('uz-UZ').replace(/,/g, ' ') + ' so‘m';
  const kgFmt = n => (Math.round((Number(n) || 0) * 10) / 10).toLocaleString('uz-UZ') + ' kg';
  const dateFmt = d => d ? new Date(String(d).slice(0, 10) + 'T12:00:00').toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '-';

  let totalSum = 0;
  let totalKg = 0;
  let totalTodayValue = 0;

  const rowsData = gifts.rows.map((r, idx) => {
    const amount = Number(r.amount || 0);
    const meatPriceAtGift = Number(r.gift_price || r.wedding_price || currentPrice);
    const kg = meatPriceAtGift > 0 ? (amount / meatPriceAtGift) : 0;
    const todayVal = Math.round(kg * currentPrice);

    totalSum += amount;
    totalKg += kg;
    totalTodayValue += todayVal;

    return {
      num: idx + 1,
      friend: r.friend || 'Noma‘lum',
      wedding: r.wedding ? (r.wedding + ' to‘yi') : '-',
      date: dateFmt(r.wedding_date),
      amount,
      amountFmt: moneyFmt(amount),
      kg,
      kgFmt: kgFmt(kg),
      todayVal,
      todayValFmt: moneyFmt(todayVal),
      note: r.note || '-'
    };
  });

  const weddingMap = {};
  for (const w of weddings.rows) {
    weddingMap[w.id] = {
      name: w.name ? (w.name + ' to‘yi') : '-',
      date: dateFmt(w.wedding_date),
      count: 0,
      sum: 0,
      kg: 0
    };
  }
  for (const g of gifts.rows) {
    if (weddingMap[g.wedding_id]) {
      const a = Number(g.amount || 0);
      const p = Number(g.gift_price || g.wedding_price || currentPrice);
      const k = p > 0 ? (a / p) : 0;
      weddingMap[g.wedding_id].count++;
      weddingMap[g.wedding_id].sum += a;
      weddingMap[g.wedding_id].kg += k;
    }
  }
  const weddingSummary = Object.values(weddingMap).sort((a, b) => b.sum - a.sum);

  const todayDateStr = new Date().toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric' });
  const giftRowsHtml = rowsData.length ? rowsData.map(r => `
    <tr>
      <td style="text-align:center;">${r.num}</td>
      <td><b>${r.friend}</b></td>
      <td>${r.wedding}</td>
      <td style="text-align:center;">${r.date}</td>
      <td style="text-align:right;">${r.amountFmt}</td>
      <td style="text-align:right;">${r.kgFmt}</td>
      <td style="text-align:right;">${r.todayValFmt}</td>
      <td>${r.note}</td>
    </tr>
  `).join('') : `<tr><td colspan="8" style="text-align:center;color:#888;padding:15px;">To‘yona yozuvlari kiritilmagan</td></tr>`;

  const weddingRowsHtml = weddingSummary.length ? weddingSummary.map((w, idx) => `
    <tr>
      <td style="text-align:center;">${idx + 1}</td>
      <td><b>${w.name}</b></td>
      <td style="text-align:center;">${w.date}</td>
      <td style="text-align:center;">${w.count} kishi</td>
      <td style="text-align:right;">${moneyFmt(w.sum)}</td>
      <td style="text-align:right;">${kgFmt(w.kg)}</td>
    </tr>
  `).join('') : `<tr><td colspan="6" style="text-align:center;color:#888;padding:15px;">To‘ylar mavjud emas</td></tr>`;

  const excelHtml = `\uFEFF<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<!--[if gte mso 9]>
<xml>
 <x:ExcelWorkbook>
  <x:ExcelWorksheets>
   <x:ExcelWorksheet>
    <x:Name>Toyona hisoboti</x:Name>
    <x:WorksheetOptions>
     <x:DisplayGridlines/>
    </x:WorksheetOptions>
   </x:ExcelWorksheet>
  </x:ExcelWorksheets>
 </x:ExcelWorkbook>
</xml>
<![endif]-->
<style>
  body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1e2924; }
  table { border-collapse: collapse; margin-bottom: 22px; width: 100%; }
  th { background-color: #0d785b; color: #ffffff; font-weight: bold; border: 1px solid #084c39; padding: 8px 10px; font-size: 11pt; }
  td { border: 1px solid #d3ded8; padding: 7px 10px; font-size: 10.5pt; }
  .head-sec { background-color: #164e3f; color: #ffffff; font-size: 12pt; font-weight: bold; padding: 7px 10px; }
  .total-row { background-color: #e5f4ed; font-weight: bold; color: #084c39; }
  .summary-lbl { background-color: #f6faf8; font-weight: 600; width: 280px; }
  .summary-val { font-weight: bold; color: #0d785b; }
</style>
</head>
<body>
  <h2 style="color:#0d785b;margin:0 0 4px;font-size:16pt;">💒 TO‘YONA HISOBOTI</h2>
  <p style="margin:0 0 16px;color:#556;font-size:10pt;">Tayyorlangan sana: <b>${todayDateStr}</b> | Bugungi 1 kg go‘sht narxi: <b>${moneyFmt(currentPrice)}</b></p>

  <table>
    <tr><th colspan="2" class="head-sec">📊 1. UMUMIY KO‘RSATKICHLAR</th></tr>
    <tr><td class="summary-lbl">Jami yig‘ilgan to‘yona summasi:</td><td class="summary-val">${moneyFmt(totalSum)}</td></tr>
    <tr><td class="summary-lbl">Jami go‘sht ekvivalenti:</td><td class="summary-val">${kgFmt(totalKg)}</td></tr>
    <tr><td class="summary-lbl">Bugungi narxdagi umumiy qiymati:</td><td class="summary-val">${moneyFmt(totalTodayValue)}</td></tr>
    <tr><td class="summary-lbl">Jami to‘ylar soni:</td><td>${weddings.rows.length} ta</td></tr>
    <tr><td class="summary-lbl">Jami oshnalar soni:</td><td>${friends.rows.length} ta</td></tr>
    <tr><td class="summary-lbl">Kiritilgan to‘yona yozuvlari:</td><td>${gifts.rows.length} ta</td></tr>
  </table>

  <table>
    <tr><th colspan="8" class="head-sec">📋 2. BARCHA TO‘YONALARNING BATAFSIL RO‘YXATI</th></tr>
    <tr>
      <th style="width:45px;text-align:center;">№</th>
      <th style="text-align:left;">Oshna (Do‘st ismi)</th>
      <th style="text-align:left;">Qaysi to‘y</th>
      <th style="text-align:center;">To‘y sanasi</th>
      <th style="text-align:right;">Berilgan to‘yona</th>
      <th style="text-align:right;">Go‘sht miqdori</th>
      <th style="text-align:right;">Bugungi qiymati</th>
      <th style="text-align:left;">Izoh</th>
    </tr>
    ${giftRowsHtml}
    <tr class="total-row">
      <td colspan="4" style="text-align:right;">JAMI:</td>
      <td style="text-align:right;">${moneyFmt(totalSum)}</td>
      <td style="text-align:right;">${kgFmt(totalKg)}</td>
      <td style="text-align:right;">${moneyFmt(totalTodayValue)}</td>
      <td></td>
    </tr>
  </table>

  <table>
    <tr><th colspan="6" class="head-sec">🎉 3. TO‘YLAR BO‘YICHA JAMLANMA</th></tr>
    <tr>
      <th style="width:45px;text-align:center;">№</th>
      <th style="text-align:left;">To‘y nomi</th>
      <th style="text-align:center;">Sanasi</th>
      <th style="text-align:center;">To‘yona berganlar</th>
      <th style="text-align:right;">Jami summa</th>
      <th style="text-align:right;">Jami go‘sht ekv.</th>
    </tr>
    ${weddingRowsHtml}
  </table>
</body>
</html>`;

  const cell = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const csvLines = [
    ['№', 'Oshna (Do‘st ismi)', 'Qaysi to‘y', 'To‘y sanasi', 'Berilgan to‘yona (so‘m)', 'Go‘sht miqdori (kg)', 'Bugungi qiymati (so‘m)', 'Izoh'],
    ...rowsData.map(r => [
      r.num,
      r.friend,
      r.wedding,
      r.date,
      r.amountFmt,
      r.kgFmt,
      r.todayValFmt,
      r.note
    ]),
    ['JAMI', '', '', '', moneyFmt(totalSum), kgFmt(totalKg), moneyFmt(totalTodayValue), '']
  ];
  const csvContent = '\uFEFF' + csvLines.map(row => row.map(cell).join(';')).join('\r\n');

  const caption = (
    "📊 <b>To‘yona Hisoboti (Excel)</b>\n\n" +
    `💰 <b>Jami to‘yona:</b> ${moneyFmt(totalSum)}\n` +
    `🥩 <b>Go‘sht ekvivalenti:</b> ${kgFmt(totalKg)}\n` +
    `💵 <b>Bugungi qiymati:</b> ${moneyFmt(totalTodayValue)}\n` +
    `🎉 <b>To‘ylar:</b> ${weddings.rows.length} ta | 👥 <b>Oshnalar:</b> ${friends.rows.length} ta\n` +
    `📝 <b>Kiritilgan yozuvlar:</b> ${gifts.rows.length} ta\n` +
    `🍖 <b>Bugungi 1 kg narxi:</b> ${moneyFmt(currentPrice)}\n\n` +
    "📁 <i>Quyidagi Excel faylini ochsangiz, barcha to‘yona va oshnalar toza, tushunarli jadvalda ko‘rinadi!</i>"
  );

  return { excelHtml, csvContent, caption, totalSum, totalKg, totalTodayValue };
}

async function fetchReportData(owner) {
  return await Promise.all([
    query('SELECT current_price FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1 ORDER BY name COLLATE "C"', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1 ORDER BY wedding_date DESC NULLS LAST, created_at DESC', [owner]),
    query(`
      SELECT w.name AS wedding, w.wedding_date, w.meat_price AS wedding_price,
             f.name AS friend, g.wedding_id, g.amount, g.meat_price AS gift_price, g.note
      FROM gifts g
      JOIN weddings w ON w.id=g.wedding_id
      JOIN friends f ON f.id=g.friend_id
      WHERE g.telegram_id=$1
      ORDER BY w.wedding_date DESC NULLS LAST, w.name, f.name
    `, [owner])
  ]);
}

app.get('/api/export.xls', asyncHandler(async (req, res) => {
  const [settings, friends, weddings, gifts] = await fetchReportData(req.user.id);
  const { excelHtml } = buildToyonaReport(settings, friends, weddings, gifts);
  res.setHeader('Content-Type', 'application/vnd.ms-excel; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="toyona_hisoboti.xls"');
  res.send(excelHtml);
}));

app.get('/api/export.csv', asyncHandler(async (req, res) => {
  const [settings, friends, weddings, gifts] = await fetchReportData(req.user.id);
  const { csvContent } = buildToyonaReport(settings, friends, weddings, gifts);
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="toyona_hisoboti.csv"');
  res.send(csvContent);
}));

app.post('/api/send-telegram-report', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const botToken = process.env.TELEGRAM_BOT_TOKEN || process.env.BOT_TOKEN || '8703043493:AAFIFYQa4SpjW4Nz8OYdVwnVBIqkjJbz7eo';
  if (!botToken) {
    return res.status(400).json({ error: 'Telegram Bot Token sozlanmagan.' });
  }

  const [settings, friends, weddings, gifts] = await fetchReportData(owner);
  const { excelHtml, caption } = buildToyonaReport(settings, friends, weddings, gifts);

  const targetChatId = owner || process.env.ADMIN_ID || '7813512925';
  const nowStr = new Date().toISOString().slice(0, 10);
  const filename = `toyona_hisoboti_${nowStr}.xls`;

  try {
    const formData = new FormData();
    formData.append('chat_id', targetChatId);
    const fileBlob = new Blob([Buffer.from(excelHtml, 'utf-8')], { type: 'application/vnd.ms-excel' });
    formData.append('document', fileBlob, filename);
    formData.append('caption', caption);
    formData.append('parse_mode', 'HTML');

    const tgRes = await fetch(`https://api.telegram.org/bot${botToken}/sendDocument`, {
      method: 'POST',
      body: formData
    });
    const tgJson = await tgRes.json();

    if (!tgRes.ok || !tgJson.ok) {
      console.warn('[TOYONA TG DOC WARNING]:', tgJson);
      await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: targetChatId,
          text: caption,
          parse_mode: 'HTML'
        })
      });
    }

    return res.json({ ok: true, message: 'Excel hisoboti Telegram botingizga yuborildi!' });
  } catch (err) {
    console.error('[TOYONA SEND TG REPORT ERROR]:', err);
    return res.status(500).json({ error: 'Telegramga yuborishda xatolik: ' + err.message });
  }
}));

app.get('/health', (_req, res) => res.json({ ok: true }));

const port = Number(process.env.TOYONA_PORT || process.env.PORT || 3000);
if (!process.env.VERCEL && !process.env.NOW_REGION) {
  app.listen(port, '0.0.0.0', () => {
    console.log(`[TOYONA] Express server ${port}-portda faol (http://0.0.0.0:${port})`);
    initDb().then(() => console.log('[TOYONA] Baza jadvallari tekshirildi va tayyor.'))
      .catch(err => console.error('[TOYONA DB XATO]:', err.message));
  });
} else {
  initDb().catch(err => console.error('[TOYONA DB INIT ERROR]:', err.message));
}

module.exports = app;


