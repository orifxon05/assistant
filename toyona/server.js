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

function hashPassword(password, salt = crypto.randomBytes(16).toString('hex')) {
  const hash = crypto.pbkdf2Sync(password, salt, 1000, 64, 'sha512').toString('hex');
  return `${salt}:${hash}`;
}

function verifyPassword(password, stored) {
  if (!stored || !stored.includes(':')) return false;
  const [salt, hash] = stored.split(':');
  const testHash = crypto.pbkdf2Sync(password, salt, 1000, 64, 'sha512').toString('hex');
  return testHash === hash;
}

async function auth(req, res, next) {
  // Public routes that do not require authentication
  if (
    req.path === '/health' ||
    req.path === '/auth/login' ||
    req.path === '/auth/register' ||
    req.path === '/auth/logout'
  ) {
    return next();
  }

  try {
    let user = null;

    if (process.env.DEV_AUTH === 'true' && process.env.NODE_ENV !== 'production') {
      user = {
        id: ADMIN_ID,
        first_name: 'Orifxon',
        username: 'orifxon05',
        login: 'orifxon',
        access_key: 'orifxon'
      };
    } else {
      // 1. Session token from X-Toyona-Token or Authorization Bearer header
      const token = (
        req.get('X-Toyona-Token') ||
        (req.get('Authorization') || '').replace(/^Bearer\s+/i, '') ||
        req.query.token ||
        ''
      ).trim();

      if (token) {
        const sessUser = await query(
          'SELECT telegram_id, first_name, username, login, access_key FROM app_users WHERE session_token=$1',
          [token]
        );
        if (sessUser.rowCount) {
          const u = sessUser.rows[0];
          user = {
            id: String(u.telegram_id),
            first_name: u.first_name || '',
            username: u.username || '',
            login: u.login || '',
            access_key: u.access_key || ''
          };
        }
      }

      // 2. Check Telegram WebApp initData (from Telegram Mini App)
      if (!user) {
        const initData = req.get('X-Telegram-Init-Data') || req.query.initData || req.query.tgWebAppInitData;
        if (initData) {
          user = validateTelegramInitData(initData);
        }
      }

      // 3. Fallback direct access key (for direct links or backwards compatibility)
      if (!user) {
        const rawKey = String(
          req.get('X-Toyona-Key') ||
          req.get('X-Toyona-Auth') ||
          req.query.key ||
          req.body?.authKey ||
          ''
        ).trim();

        if (rawKey) {
          const lowerKey = rawKey.toLowerCase();
          // Master key for Orifxon
          if (lowerKey === DEFAULT_ACCESS_KEY || lowerKey === ADMIN_ID || lowerKey === '7813' || lowerKey === 'orifxon') {
            user = {
              id: ADMIN_ID,
              first_name: 'Orifxon',
              username: 'orifxon05',
              login: 'orifxon',
              access_key: 'orifxon'
            };
          } else {
            // Find user by their personal access_key or login
            const dbUser = await query(
              'SELECT telegram_id, first_name, username, login, access_key FROM app_users WHERE access_key=$1 OR LOWER(access_key)=$2 OR LOWER(login)=$2 LIMIT 1',
              [rawKey, lowerKey]
            );
            if (dbUser.rowCount) {
              const u = dbUser.rows[0];
              user = {
                id: String(u.telegram_id),
                first_name: u.first_name || '',
                username: u.username || '',
                login: u.login || '',
                access_key: u.access_key || rawKey
              };
            }
          }
        }
      }

      if (!user) {
        return res.status(401).json({
          error: 'Tizimga kirish talab etiladi.',
          auth_required: true,
          message: 'Davom etish uchun login va parolingizni kiriting.'
        });
      }
    }

    req.user = user;

    // Check or create access_key for this user
    const existing = await query('SELECT telegram_id, access_key, login, password_hash FROM app_users WHERE telegram_id=$1', [req.user.id]);
    let userKey = existing.rows[0]?.access_key;
    if (!existing.rowCount) {
      userKey = (req.user.id === ADMIN_ID) ? 'orifxon' : ('toy_' + crypto.randomBytes(4).toString('hex'));
      const defaultLogin = (req.user.id === ADMIN_ID) ? 'orifxon' : (req.user.username || userKey);
      await query(
        `INSERT INTO app_users(telegram_id, first_name, username, login, access_key) VALUES($1,$2,$3,$4,$5)
         ON CONFLICT(telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name, username=EXCLUDED.username`,
        [req.user.id, req.user.first_name, req.user.username, defaultLogin, userKey]
      );
    } else if (!userKey) {
      userKey = (req.user.id === ADMIN_ID) ? 'orifxon' : ('toy_' + crypto.randomBytes(4).toString('hex'));
      await query('UPDATE app_users SET access_key=$1 WHERE telegram_id=$2', [userKey, req.user.id]);
    }

    // Ensure Orifxon has login='orifxon' and default password if empty
    if (req.user.id === ADMIN_ID && (!existing.rows[0]?.login || !existing.rows[0]?.password_hash)) {
      const defaultHash = hashPassword('orifxon');
      await query(
        `UPDATE app_users SET login='orifxon', password_hash=COALESCE(password_hash, $1), access_key='orifxon' WHERE telegram_id=$2`,
        [defaultHash, ADMIN_ID]
      );
    }

    req.user.access_key = userKey;
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

app.post('/api/auth/register', asyncHandler(async (req, res) => {
  const name = String(req.body.name || '').trim();
  const login = String(req.body.login || '').toLowerCase().trim();
  const password = String(req.body.password || '');
  const tgUsername = String(req.body.tgUsername || '').replace(/^@/, '').trim();

  if (!name || name.length < 2 || name.length > 50) {
    return res.status(400).json({ error: 'Ism 2–50 ta belgidan iborat bo‘lishi kerak.' });
  }
  if (!login || login.length < 3 || login.length > 32 || !/^[a-zA-Z0-9_.-]+$/.test(login)) {
    return res.status(400).json({ error: 'Login 3–32 ta belgi (harf, raqam) bo‘lishi kerak.' });
  }
  if (!password || password.length < 4) {
    return res.status(400).json({ error: 'Parol kamida 4 ta belgidan iborat bo‘lishi kerak.' });
  }

  const check = await query('SELECT telegram_id FROM app_users WHERE LOWER(login)=$1', [login]);
  if (check.rowCount) {
    return res.status(400).json({ error: 'Bu login band. Boshqa login tanlang.' });
  }

  const newId = Date.now() * 1000 + Math.floor(Math.random() * 1000);
  const pwdHash = hashPassword(password);
  const sessionToken = crypto.randomBytes(32).toString('hex');
  const accessKey = 'toy_' + crypto.randomBytes(4).toString('hex');

  await query(
    `INSERT INTO app_users(telegram_id, first_name, username, login, password_hash, session_token, access_key)
     VALUES($1, $2, $3, $4, $5, $6, $7)`,
    [newId, name, tgUsername, login, pwdHash, sessionToken, accessKey]
  );

  await query(`INSERT INTO settings(telegram_id) VALUES($1) ON CONFLICT(telegram_id) DO NOTHING`, [newId]);

  res.json({
    ok: true,
    token: sessionToken,
    user: {
      id: String(newId),
      first_name: name,
      username: tgUsername,
      login: login,
      access_key: accessKey
    }
  });
}));

app.post('/api/auth/login', asyncHandler(async (req, res) => {
  const login = String(req.body.login || '').toLowerCase().trim();
  const password = String(req.body.password || '');

  if (!login || !password) {
    return res.status(400).json({ error: 'Login va parolni kiriting.' });
  }

  // Check Orifxon master login
  if (login === 'orifxon' || login === '7813' || login === '7813512925') {
    const orifRow = await query('SELECT * FROM app_users WHERE telegram_id=$1', [ADMIN_ID]);
    let orifUser = orifRow.rows[0];
    if (!orifUser || !orifUser.password_hash) {
      const defaultHash = hashPassword('orifxon');
      await query(
        `INSERT INTO app_users(telegram_id, first_name, username, login, password_hash, access_key)
         VALUES($1, 'Orifxon', 'orifxon05', 'orifxon', $2, 'orifxon')
         ON CONFLICT(telegram_id) DO UPDATE SET login='orifxon', password_hash=COALESCE(app_users.password_hash, $2), access_key='orifxon'`,
        [ADMIN_ID, defaultHash]
      );
      const refetch = await query('SELECT * FROM app_users WHERE telegram_id=$1', [ADMIN_ID]);
      orifUser = refetch.rows[0];
    }

    const isValid = verifyPassword(password, orifUser.password_hash) || (password === 'orifxon');
    if (!isValid) {
      return res.status(400).json({ error: 'Login yoki parol noto‘g‘ri.' });
    }

    const sessionToken = crypto.randomBytes(32).toString('hex');
    await query('UPDATE app_users SET session_token=$1 WHERE telegram_id=$2', [sessionToken, ADMIN_ID]);

    return res.json({
      ok: true,
      token: sessionToken,
      user: {
        id: String(ADMIN_ID),
        first_name: orifUser.first_name || 'Orifxon',
        username: orifUser.username || 'orifxon05',
        login: 'orifxon',
        access_key: orifUser.access_key || 'orifxon'
      }
    });
  }

  // Regular user login
  const userRes = await query(
    'SELECT telegram_id, first_name, username, login, password_hash, access_key FROM app_users WHERE LOWER(login)=$1 OR LOWER(username)=$1 LIMIT 1',
    [login]
  );

  if (!userRes.rowCount) {
    return res.status(400).json({ error: 'Login yoki parol noto‘g‘ri.' });
  }

  const u = userRes.rows[0];
  if (!verifyPassword(password, u.password_hash)) {
    return res.status(400).json({ error: 'Login yoki parol noto‘g‘ri.' });
  }

  const sessionToken = crypto.randomBytes(32).toString('hex');
  await query('UPDATE app_users SET session_token=$1 WHERE telegram_id=$2', [sessionToken, u.telegram_id]);

  res.json({
    ok: true,
    token: sessionToken,
    user: {
      id: String(u.telegram_id),
      first_name: u.first_name,
      username: u.username,
      login: u.login,
      access_key: u.access_key
    }
  });
}));

app.post('/api/auth/logout', asyncHandler(async (req, res) => {
  const token = (
    req.get('X-Toyona-Token') ||
    (req.get('Authorization') || '').replace(/^Bearer\s+/i, '') ||
    req.body?.token ||
    ''
  ).trim();
  if (token) {
    await query('UPDATE app_users SET session_token=NULL WHERE session_token=$1', [token]);
  }
  res.json({ ok: true });
}));

app.post('/api/auth/change-password', asyncHandler(async (req, res) => {
  const oldPwd = String(req.body.oldPassword || '');
  const newPwd = String(req.body.newPassword || '');
  if (!newPwd || newPwd.length < 4) {
    return res.status(400).json({ error: 'Yangi parol kamida 4 ta belgidan iborat bo‘lishi kerak.' });
  }
  const userRes = await query('SELECT password_hash FROM app_users WHERE telegram_id=$1', [req.user.id]);
  const stored = userRes.rows[0]?.password_hash;
  if (stored && !verifyPassword(oldPwd, stored) && !(req.user.id === ADMIN_ID && oldPwd === 'orifxon')) {
    return res.status(400).json({ error: 'Eski parol noto‘g‘ri kiritildi.' });
  }
  const newHash = hashPassword(newPwd);
  await query('UPDATE app_users SET password_hash=$1 WHERE telegram_id=$2', [newHash, req.user.id]);
  res.json({ ok: true, message: 'Parol muvaffaqiyatli o‘zgartirildi.' });
}));

app.get('/api/bootstrap', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const [settings, friends, weddings, gifts] = await Promise.all([
    query('SELECT current_price, current_dollar_rate FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1 ORDER BY name COLLATE "C"', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1 ORDER BY wedding_date DESC NULLS LAST, created_at DESC', [owner]),
    query('SELECT * FROM gifts WHERE telegram_id=$1', [owner])
  ]);
  res.json({
    user: req.user,
    currentPrice: Number(settings.rows[0]?.current_price || 150000),
    currentDollarRate: Number(settings.rows[0]?.current_dollar_rate || 12800),
    friends: friends.rows,
    weddings: weddings.rows.map(w => ({
      ...w,
      meat_price: Number(w.meat_price),
      dollar_rate: Number(w.dollar_rate || 12800),
      calc_type: w.calc_type || 'both',
      min_kg: Number(w.min_kg)
    })),
    gifts: gifts.rows.map(g => ({
      ...g,
      amount: Number(g.amount),
      meat_price: Number(g.meat_price),
      dollar_rate: Number(g.dollar_rate || 12800)
    }))
  });
}));

app.put('/api/settings', asyncHandler(async (req, res) => {
  const price = req.body.currentPrice !== undefined ? Number(req.body.currentPrice) : null;
  const dollarRate = req.body.currentDollarRate !== undefined ? Number(req.body.currentDollarRate) : null;

  if (price !== null && (!Number.isSafeInteger(price) || price < 1)) {
    return res.status(400).json({ error: 'Go‘sht narxi musbat butun son bo‘lishi kerak.' });
  }
  if (dollarRate !== null && (!Number.isSafeInteger(dollarRate) || dollarRate < 1)) {
    return res.status(400).json({ error: 'Dollar kursi musbat butun son bo‘lishi kerak.' });
  }

  if (price !== null && dollarRate !== null) {
    await query('UPDATE settings SET current_price=$1, current_dollar_rate=$2, updated_at=NOW() WHERE telegram_id=$3', [price, dollarRate, req.user.id]);
  } else if (price !== null) {
    await query('UPDATE settings SET current_price=$1, updated_at=NOW() WHERE telegram_id=$2', [price, req.user.id]);
  } else if (dollarRate !== null) {
    await query('UPDATE settings SET current_dollar_rate=$1, updated_at=NOW() WHERE telegram_id=$2', [dollarRate, req.user.id]);
  }
  res.json({ ok: true });
}));

app.put('/api/user/key', asyncHandler(async (req, res) => {
  const newKey = String(req.body.key || '').trim();
  if (!newKey || newKey.length < 3 || newKey.length > 32 || !/^[a-zA-Z0-9_-]+$/.test(newKey)) {
    return res.status(400).json({ error: 'Kalit so‘z 3–32 ta harf, raqam yoki chiziqcha (_) dan iborat bo‘lishi kerak.' });
  }
  const conflict = await query('SELECT telegram_id FROM app_users WHERE LOWER(access_key)=$1 AND telegram_id!=$2', [newKey.toLowerCase(), req.user.id]);
  if (conflict.rowCount) {
    return res.status(400).json({ error: 'Ushbu kalit so‘z band. Boshqa kalit tanlang.' });
  }
  await query('UPDATE app_users SET access_key=$1 WHERE telegram_id=$2', [newKey, req.user.id]);
  req.user.access_key = newKey;
  res.json({ ok: true, access_key: newKey });
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
  const price = Number(req.body.meatPrice || 150000);
  const dollarRate = Number(req.body.dollarRate || 12800);
  const calcType = ['both', 'meat', 'dollar'].includes(req.body.calcType) ? req.body.calcType : 'both';
  const minKg = Number(req.body.minKg ?? 2);
  const note = String(req.body.note || '').trim().slice(0, 500);
  if (!name || name.length > 100 || !Number.isSafeInteger(price) || price < 1 || !Number.isSafeInteger(dollarRate) || dollarRate < 1 || !Number.isFinite(minKg) || minKg < 0 || minKg > 100) {
    return res.status(400).json({ error: 'To‘y nomi, narx, dollar kursi yoki minimum qiymatini tekshiring.' });
  }
  if (friendId) {
    const f = await query('SELECT id FROM friends WHERE id=$1 AND telegram_id=$2', [friendId, req.user.id]);
    if (!f.rowCount) return res.status(400).json({ error: 'Tanlangan oshna topilmadi.' });
  }
  const id = randomUUID();
  await query(
    'INSERT INTO weddings(id,telegram_id,friend_id,name,wedding_date,meat_price,dollar_rate,calc_type,min_kg,note) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)',
    [id, req.user.id, friendId, name, date, price, dollarRate, calcType, minKg, note]
  );
  res.status(201).json({ id });
}));

app.put('/api/weddings/:id', asyncHandler(async (req, res) => {
  const rawFriend = req.body.friendId;
  const friendId = (rawFriend && typeof rawFriend === 'string' && rawFriend.trim().length > 10) ? rawFriend.trim() : null;
  const name = String(req.body.name || '').trim();
  const rawDate = req.body.date ? String(req.body.date).trim() : null;
  const date = (rawDate && rawDate !== 'null' && rawDate !== 'undefined') ? rawDate : null;
  const price = Number(req.body.meatPrice || 150000);
  const dollarRate = Number(req.body.dollarRate || 12800);
  const calcType = ['both', 'meat', 'dollar'].includes(req.body.calcType) ? req.body.calcType : 'both';
  const minKg = Number(req.body.minKg ?? 2);
  const note = String(req.body.note || '').trim().slice(0, 500);
  if (!name || name.length > 100 || !Number.isSafeInteger(price) || price < 1 || !Number.isSafeInteger(dollarRate) || dollarRate < 1 || !Number.isFinite(minKg) || minKg < 0 || minKg > 100) {
    return res.status(400).json({ error: 'Maydonlarni tekshiring.' });
  }
  const result = await query(
    `UPDATE weddings SET name=$1,wedding_date=$2,meat_price=$3,dollar_rate=$4,calc_type=$5,min_kg=$6,friend_id=$7,note=$8
     WHERE id=$9 AND telegram_id=$10 RETURNING id`,
    [name, date, price, dollarRate, calcType, minKg, friendId, note, req.params.id, req.user.id]
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
  const wedding = await query('SELECT meat_price, dollar_rate FROM weddings WHERE id=$1 AND telegram_id=$2', [weddingId, req.user.id]);
  const friend = await query('SELECT id FROM friends WHERE id=$1 AND telegram_id=$2', [friendId, req.user.id]);
  if (!wedding.rowCount || !friend.rowCount) return res.status(400).json({ error: 'To‘y yoki oshna topilmadi.' });
  if (amount === 0) {
    await query('DELETE FROM gifts WHERE wedding_id=$1 AND friend_id=$2 AND telegram_id=$3', [weddingId, friendId, req.user.id]);
    return res.json({ ok: true, deleted: true });
  }
  const id = randomUUID();
  const wMeatPrice = Number(wedding.rows[0].meat_price || 150000);
  const wDollarRate = Number(wedding.rows[0].dollar_rate || 12800);
  await query(
    `INSERT INTO gifts(id,telegram_id,wedding_id,friend_id,amount,meat_price,dollar_rate,note)
     VALUES($1,$2,$3,$4,$5,$6,$7,$8)
     ON CONFLICT(wedding_id,friend_id) DO UPDATE SET amount=EXCLUDED.amount,meat_price=EXCLUDED.meat_price,dollar_rate=EXCLUDED.dollar_rate,note=EXCLUDED.note,updated_at=NOW()
     WHERE gifts.telegram_id=EXCLUDED.telegram_id`,
    [id, req.user.id, weddingId, friendId, amount, wMeatPrice, wDollarRate, note]
  );
  res.json({ ok: true });
}));

app.get(['/api/backup', '/api/backup.json'], asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const [settings, friends, weddings, gifts] = await Promise.all([
    query('SELECT * FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM gifts WHERE telegram_id=$1', [owner])
  ]);
  const dateStr = new Date().toISOString().slice(0, 10);
  const data = {
    version: '2.0',
    app: 'toyona',
    telegram_id: owner,
    exported_at: new Date().toISOString(),
    settings: settings.rows[0] || null,
    friends: friends.rows,
    weddings: weddings.rows,
    gifts: gifts.rows
  };
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="toyona_backup_${dateStr}.json"`);
  res.send(JSON.stringify(data, null, 2));
}));

app.post('/api/restore', asyncHandler(async (req, res) => {
  const owner = req.user.id;
  const { settings, friends, weddings, gifts } = req.body || {};
  let restoredFriends = 0;
  let restoredWeddings = 0;
  let restoredGifts = 0;

  if (settings) {
    const cp = Number(settings.current_price || 150000);
    const cd = Number(settings.current_dollar_rate || 12800);
    await query(
      `INSERT INTO settings(telegram_id, current_price, current_dollar_rate, updated_at) VALUES($1,$2,$3,NOW())
       ON CONFLICT(telegram_id) DO UPDATE SET current_price=EXCLUDED.current_price, current_dollar_rate=EXCLUDED.current_dollar_rate, updated_at=NOW()`,
      [owner, cp, cd]
    );
  }

  if (Array.isArray(friends)) {
    for (const f of friends) {
      if (f.id && f.name) {
        await query(
          `INSERT INTO friends(id, telegram_id, name) VALUES($1,$2,$3)
           ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name`,
          [f.id, owner, String(f.name).trim()]
        );
        restoredFriends++;
      }
    }
  }

  if (Array.isArray(weddings)) {
    for (const w of weddings) {
      if (w.id && w.name) {
        const friendId = (w.friend_id && String(w.friend_id).length > 10) ? String(w.friend_id) : null;
        const wDate = (w.wedding_date && w.wedding_date !== 'null' && w.wedding_date !== 'undefined') ? String(w.wedding_date).slice(0, 10) : null;
        const price = Number(w.meat_price || 150000);
        const dollarRate = Number(w.dollar_rate || 12800);
        const calcType = ['both', 'meat', 'dollar'].includes(w.calc_type) ? w.calc_type : 'both';
        const minKg = Number(w.min_kg ?? 2);
        const note = String(w.note || '').trim().slice(0, 500);

        await query(
          `INSERT INTO weddings(id, telegram_id, friend_id, name, wedding_date, meat_price, dollar_rate, calc_type, min_kg, note)
           VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
           ON CONFLICT(id) DO UPDATE SET
             name=EXCLUDED.name,
             wedding_date=EXCLUDED.wedding_date,
             meat_price=EXCLUDED.meat_price,
             dollar_rate=EXCLUDED.dollar_rate,
             calc_type=EXCLUDED.calc_type,
             min_kg=EXCLUDED.min_kg,
             friend_id=EXCLUDED.friend_id,
             note=EXCLUDED.note`,
          [w.id, owner, friendId, String(w.name).trim(), wDate, price, dollarRate, calcType, minKg, note]
        );
        restoredWeddings++;
      }
    }
  }

  if (Array.isArray(gifts)) {
    for (const g of gifts) {
      if (g.wedding_id && g.friend_id && g.amount !== undefined) {
        const amount = Number(g.amount);
        const meatP = Number(g.meat_price || 150000);
        const dollR = Number(g.dollar_rate || 12800);
        const gNote = String(g.note || '').trim().slice(0, 500);
        await query(
          `INSERT INTO gifts(id, telegram_id, wedding_id, friend_id, amount, meat_price, dollar_rate, note)
           VALUES($1,$2,$3,$4,$5,$6,$7,$8)
           ON CONFLICT(wedding_id, friend_id) DO UPDATE SET
             amount=EXCLUDED.amount,
             meat_price=EXCLUDED.meat_price,
             dollar_rate=EXCLUDED.dollar_rate,
             note=EXCLUDED.note,
             updated_at=NOW()
           WHERE gifts.telegram_id=EXCLUDED.telegram_id`,
          [g.id || randomUUID(), owner, g.wedding_id, g.friend_id, amount, meatP, dollR, gNote]
        );
        restoredGifts++;
      }
    }
  }

  res.json({
    ok: true,
    message: `Baza muvaffaqiyatli tiklandi: ${restoredFriends} ta oshna, ${restoredWeddings} ta to‘y, ${restoredGifts} ta to‘yona yozuvi tiklandi.`
  });
}));

function buildToyonaReport(settings, friends, weddings, gifts) {
  const currentPrice = Number(settings.rows[0]?.current_price || 150000);
  const currentDollarRate = Number(settings.rows[0]?.current_dollar_rate || 12800);
  const moneyFmt = n => Math.round(Number(n) || 0).toLocaleString('uz-UZ').replace(/,/g, ' ') + ' so‘m';
  const kgFmt = n => (Math.round((Number(n) || 0) * 10) / 10).toLocaleString('uz-UZ') + ' kg';
  const dollarFmt = n => '$ ' + (Math.round((Number(n) || 0) * 10) / 10).toLocaleString('uz-UZ');
  const dateFmt = d => d ? new Date(String(d).slice(0, 10) + 'T12:00:00').toLocaleDateString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '-';

  let totalSum = 0;
  let totalKg = 0;
  let totalDollars = 0;
  let totalTodayMeatVal = 0;
  let totalTodayDollarVal = 0;

  const rowsData = gifts.rows.map((r, idx) => {
    const amount = Number(r.amount || 0);
    const meatPriceAtGift = Number(r.gift_price || r.wedding_price || currentPrice);
    const dollarRateAtGift = Number(r.gift_dollar_rate || r.wedding_dollar_rate || currentDollarRate);
    const kg = meatPriceAtGift > 0 ? (amount / meatPriceAtGift) : 0;
    const dollars = dollarRateAtGift > 0 ? (amount / dollarRateAtGift) : 0;
    const todayMeatVal = Math.round(kg * currentPrice);
    const todayDollarVal = Math.round(dollars * currentDollarRate);

    totalSum += amount;
    totalKg += kg;
    totalDollars += dollars;
    totalTodayMeatVal += todayMeatVal;
    totalTodayDollarVal += todayDollarVal;

    return {
      num: idx + 1,
      friend: r.friend || 'Noma‘lum',
      wedding: r.wedding ? (r.wedding + ' to‘yi') : '-',
      date: dateFmt(r.wedding_date),
      amount,
      amountFmt: moneyFmt(amount),
      kg,
      kgFmt: kgFmt(kg),
      dollars,
      dollarFmt: dollarFmt(dollars),
      todayMeatVal,
      todayMeatValFmt: moneyFmt(todayMeatVal),
      todayDollarVal,
      todayDollarValFmt: moneyFmt(todayDollarVal),
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
      kg: 0,
      dollars: 0
    };
  }
  for (const g of gifts.rows) {
    if (weddingMap[g.wedding_id]) {
      const a = Number(g.amount || 0);
      const p = Number(g.gift_price || g.wedding_price || currentPrice);
      const d = Number(g.gift_dollar_rate || g.wedding_dollar_rate || currentDollarRate);
      const k = p > 0 ? (a / p) : 0;
      const dl = d > 0 ? (a / d) : 0;
      weddingMap[g.wedding_id].count++;
      weddingMap[g.wedding_id].sum += a;
      weddingMap[g.wedding_id].kg += k;
      weddingMap[g.wedding_id].dollars += dl;
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
      <td style="text-align:right;">${r.dollarFmt}</td>
      <td style="text-align:right;">${r.todayMeatValFmt}</td>
      <td style="text-align:right;">${r.todayDollarValFmt}</td>
      <td>${r.note}</td>
    </tr>
  `).join('') : `<tr><td colspan="10" style="text-align:center;color:#888;padding:15px;">To‘yona yozuvlari kiritilmagan</td></tr>`;

  const weddingRowsHtml = weddingSummary.length ? weddingSummary.map((w, idx) => `
    <tr>
      <td style="text-align:center;">${idx + 1}</td>
      <td><b>${w.name}</b></td>
      <td style="text-align:center;">${w.date}</td>
      <td style="text-align:center;">${w.count} kishi</td>
      <td style="text-align:right;">${moneyFmt(w.sum)}</td>
      <td style="text-align:right;">${kgFmt(w.kg)}</td>
      <td style="text-align:right;">${dollarFmt(w.dollars)}</td>
    </tr>
  `).join('') : `<tr><td colspan="7" style="text-align:center;color:#888;padding:15px;">To‘ylar mavjud emas</td></tr>`;

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
  <p style="margin:0 0 16px;color:#556;font-size:10pt;">Tayyorlangan sana: <b>${todayDateStr}</b> | Bugungi 1 kg go‘sht: <b>${moneyFmt(currentPrice)}</b> | Bugungi 1 $ kursi: <b>${moneyFmt(currentDollarRate)}</b></p>

  <table>
    <tr><th colspan="2" class="head-sec">📊 1. UMUMIY KO‘RSATKICHLAR</th></tr>
    <tr><td class="summary-lbl">Jami yig‘ilgan to‘yona summasi:</td><td class="summary-val">${moneyFmt(totalSum)}</td></tr>
    <tr><td class="summary-lbl">Jami go‘sht ekvivalenti:</td><td class="summary-val">${kgFmt(totalKg)} (Bugungi qiymati: ${moneyFmt(totalTodayMeatVal)})</td></tr>
    <tr><td class="summary-lbl">Jami dollar ekvivalenti:</td><td class="summary-val">${dollarFmt(totalDollars)} (Bugungi kursda: ${moneyFmt(totalTodayDollarVal)})</td></tr>
    <tr><td class="summary-lbl">Bugungi 1 kg go‘sht narxi:</td><td>${moneyFmt(currentPrice)}</td></tr>
    <tr><td class="summary-lbl">Bugungi 1 $ dollari kursi:</td><td>${moneyFmt(currentDollarRate)}</td></tr>
    <tr><td class="summary-lbl">Jami to‘ylar soni:</td><td>${weddings.rows.length} ta</td></tr>
    <tr><td class="summary-lbl">Jami oshnalar soni:</td><td>${friends.rows.length} ta</td></tr>
    <tr><td class="summary-lbl">Kiritilgan to‘yona yozuvlari:</td><td>${gifts.rows.length} ta</td></tr>
  </table>

  <table>
    <tr><th colspan="10" class="head-sec">📋 2. BARCHA TO‘YONALARNING BATAFSIL RO‘YXATI</th></tr>
    <tr>
      <th style="width:40px;text-align:center;">№</th>
      <th style="text-align:left;">Oshna (Do‘st ismi)</th>
      <th style="text-align:left;">Qaysi to‘y</th>
      <th style="text-align:center;">To‘y sanasi</th>
      <th style="text-align:right;">Berilgan to‘yona</th>
      <th style="text-align:right;">Go‘sht (kg)</th>
      <th style="text-align:right;">Dollar ($)</th>
      <th style="text-align:right;">Bugun (Go‘sht)</th>
      <th style="text-align:right;">Bugun (Dollar)</th>
      <th style="text-align:left;">Izoh</th>
    </tr>
    ${giftRowsHtml}
    <tr class="total-row">
      <td colspan="4" style="text-align:right;">JAMI:</td>
      <td style="text-align:right;">${moneyFmt(totalSum)}</td>
      <td style="text-align:right;">${kgFmt(totalKg)}</td>
      <td style="text-align:right;">${dollarFmt(totalDollars)}</td>
      <td style="text-align:right;">${moneyFmt(totalTodayMeatVal)}</td>
      <td style="text-align:right;">${moneyFmt(totalTodayDollarVal)}</td>
      <td></td>
    </tr>
  </table>

  <table>
    <tr><th colspan="7" class="head-sec">🎉 3. TO‘YLAR BO‘YICHA JAMLANMA</th></tr>
    <tr>
      <th style="width:40px;text-align:center;">№</th>
      <th style="text-align:left;">To‘y nomi</th>
      <th style="text-align:center;">Sanasi</th>
      <th style="text-align:center;">To‘yona berganlar</th>
      <th style="text-align:right;">Jami summa</th>
      <th style="text-align:right;">Go‘sht ekv.</th>
      <th style="text-align:right;">Dollar ekv.</th>
    </tr>
    ${weddingRowsHtml}
  </table>
</body>
</html>`;

  const cell = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const csvLines = [
    ['№', 'Oshna (Do‘st ismi)', 'Qaysi to‘y', 'To‘y sanasi', 'Berilgan to‘yona (so‘m)', 'Go‘sht (kg)', 'Dollar ($)', 'Bugungi narxda (Go‘sht)', 'Bugungi kursda (Dollar)', 'Izoh'],
    ...rowsData.map(r => [
      r.num,
      r.friend,
      r.wedding,
      r.date,
      r.amountFmt,
      r.kgFmt,
      r.dollarFmt,
      r.todayMeatValFmt,
      r.todayDollarValFmt,
      r.note
    ]),
    ['JAMI', '', '', '', moneyFmt(totalSum), kgFmt(totalKg), dollarFmt(totalDollars), moneyFmt(totalTodayMeatVal), moneyFmt(totalTodayDollarVal), '']
  ];
  const csvContent = '\uFEFF' + csvLines.map(row => row.map(cell).join(';')).join('\r\n');

  const caption = (
    "📊 <b>To‘yona Hisoboti (Excel)</b>\n\n" +
    `💰 <b>Jami to‘yona:</b> ${moneyFmt(totalSum)}\n` +
    `🥩 <b>Go‘sht ekvivalenti:</b> ${kgFmt(totalKg)} (Bugun: ${moneyFmt(totalTodayMeatVal)})\n` +
    `💵 <b>Dollar ekvivalenti:</b> ${dollarFmt(totalDollars)} (Bugun: ${moneyFmt(totalTodayDollarVal)})\n` +
    `🎉 <b>To‘ylar:</b> ${weddings.rows.length} ta | 👥 <b>Oshnalar:</b> ${friends.rows.length} ta\n` +
    `📝 <b>Kiritilgan yozuvlar:</b> ${gifts.rows.length} ta\n` +
    `🍖 <b>1 kg go‘sht:</b> ${moneyFmt(currentPrice)} | 💲 <b>1 $ kursi:</b> ${moneyFmt(currentDollarRate)}\n\n` +
    "📁 <i>Quyidagi Excel faylini ochsangiz, barcha to‘yona va oshnalar Go‘sht va Dollar hisob-kitoblari bilan toza jadvalda ko‘rinadi!</i>"
  );

  return { excelHtml, csvContent, caption, totalSum, totalKg, totalDollars, totalTodayMeatVal, totalTodayDollarVal };
}

async function fetchReportData(owner) {
  return await Promise.all([
    query('SELECT current_price, current_dollar_rate FROM settings WHERE telegram_id=$1', [owner]),
    query('SELECT * FROM friends WHERE telegram_id=$1 ORDER BY name COLLATE "C"', [owner]),
    query('SELECT * FROM weddings WHERE telegram_id=$1 ORDER BY wedding_date DESC NULLS LAST, created_at DESC', [owner]),
    query(`
      SELECT w.name AS wedding, w.wedding_date, w.meat_price AS wedding_price, w.dollar_rate AS wedding_dollar_rate,
             f.name AS friend, g.wedding_id, g.amount, g.meat_price AS gift_price, g.dollar_rate AS gift_dollar_rate, g.note
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
  const dateStr = new Date().toISOString().slice(0, 10);
  res.setHeader('Content-Type', 'application/vnd.ms-excel; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="toyona_hisoboti_${dateStr}.xls"`);
  res.send(excelHtml);
}));

app.get('/api/export.csv', asyncHandler(async (req, res) => {
  const [settings, friends, weddings, gifts] = await fetchReportData(req.user.id);
  const { csvContent } = buildToyonaReport(settings, friends, weddings, gifts);
  const dateStr = new Date().toISOString().slice(0, 10);
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="toyona_hisoboti_${dateStr}.csv"`);
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


