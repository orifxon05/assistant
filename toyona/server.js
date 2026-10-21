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

async function auth(req, res, next) {
  try {
    if (process.env.DEV_AUTH === 'true' && process.env.NODE_ENV !== 'production') {
      req.user = {
        id: String(process.env.DEV_TELEGRAM_ID || process.env.ADMIN_ID || '123456789'),
        first_name: 'Sinov',
        username: 'local_test'
      };
    } else {
      const user = validateTelegramInitData(req.get('X-Telegram-Init-Data'));
      if (!user) return res.status(401).json({ error: 'Telegram sessiyasi tekshirilmadi. Mini App’ni Telegram ichidan oching.' });
      req.user = user;
    }
    await query(
      `INSERT INTO app_users(telegram_id, first_name, username) VALUES($1,$2,$3)
       ON CONFLICT(telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name, username=EXCLUDED.username`,
      [req.user.id, req.user.first_name, req.user.username]
    );
    await query(`INSERT INTO settings(telegram_id) VALUES($1) ON CONFLICT(telegram_id) DO NOTHING`, [req.user.id]);
    next();
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'Serverda vaqtinchalik xatolik.' });
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

app.get('/api/export.csv', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const rows = await query(`
    SELECT w.name AS wedding, w.wedding_date, w.meat_price AS wedding_price,
           f.name AS friend, g.amount, g.meat_price AS gift_price, g.note
    FROM gifts g
    JOIN weddings w ON w.id=g.wedding_id
    JOIN friends f ON f.id=g.friend_id
    WHERE g.telegram_id=$1
    ORDER BY w.wedding_date DESC NULLS LAST, w.name, f.name
  `, [owner]);
  const cell = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const csv = '\uFEFF' + [
    ['To‘y', 'Sana', 'To‘y paytidagi kg narxi', 'Oshna', 'Summa (so‘m)', 'Yozuvdagi kg narxi', 'Izoh'],
    ...rows.rows.map(r => [r.wedding, r.wedding_date ? String(r.wedding_date).slice(0,10) : '', r.wedding_price, r.friend, r.amount, r.gift_price, r.note])
  ].map(row => row.map(cell).join(';')).join('\r\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', 'attachment; filename="toyona-hisoboti.csv"');
  res.send(csv);
}));

app.get('/health', (_req, res) => res.json({ ok: true }));

const port = Number(process.env.TOYONA_PORT || process.env.PORT || 3000);
app.listen(port, '0.0.0.0', () => {
  console.log(`[TOYONA] Express server ${port}-portda faol (http://0.0.0.0:${port})`);
  initDb().then(() => console.log('[TOYONA] Baza jadvallari tekshirildi va tayyor.'))
    .catch(err => console.error('[TOYONA DB XATO]:', err.message));
});

