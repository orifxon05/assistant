const { Pool } = require('pg');

const DEFAULT_NEON_DB_URL = 'postgresql://neondb_owner:npg_RNsvIktC3pF2@ep-curly-math-b5sqz5zy-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require';
let rawConn = (process.env.TOYONA_DATABASE_URL || process.env.DATABASE_URL || '').trim();
if (!rawConn) {
  rawConn = DEFAULT_NEON_DB_URL;
}
// Strip channel_binding if present to prevent node-postgres SASL mismatches
if (rawConn.includes('channel_binding=')) {
  rawConn = rawConn.replace(/[?&]channel_binding=[^&]+/, '');
  if (!rawConn.includes('?') && rawConn.includes('&')) {
    rawConn = rawConn.replace('&', '?');
  }
}

const isSsl = process.env.DATABASE_SSL === 'true' || 
              (rawConn && (rawConn.includes('neon.tech') || rawConn.includes('sslmode=require')));

const pool = new Pool({
  connectionString: rawConn,
  ssl: isSsl ? { rejectUnauthorized: false } : false,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
  allowExitOnIdle: false
});

// Neon serverless idle socket error handler to prevent crashing process
pool.on('error', (err) => {
  console.warn('[TOYONA POOL NON-FATAL ERROR]:', err.message);
});

async function query(text, params, retries = 2) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await pool.query(text, params);
    } catch (err) {
      if (attempt < retries) {
        console.warn(`[TOYONA DB RETRY] ${err.message}. Qayta ulanmoqda (${attempt}/${retries})...`);
        await new Promise(r => setTimeout(r, 400));
      } else {
        throw err;
      }
    }
  }
}

async function initDb() {
  await query(`
    CREATE TABLE IF NOT EXISTS app_users (
      telegram_id BIGINT PRIMARY KEY,
      first_name TEXT NOT NULL DEFAULT '',
      username TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS settings (
      telegram_id BIGINT PRIMARY KEY REFERENCES app_users(telegram_id) ON DELETE CASCADE,
      current_price BIGINT NOT NULL DEFAULT 150000 CHECK (current_price > 0),
      current_dollar_rate BIGINT NOT NULL DEFAULT 12800 CHECK (current_dollar_rate > 0),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS friends (
      id UUID PRIMARY KEY,
      telegram_id BIGINT NOT NULL REFERENCES app_users(telegram_id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS friends_owner_idx ON friends(telegram_id);

    CREATE TABLE IF NOT EXISTS weddings (
      id UUID PRIMARY KEY,
      telegram_id BIGINT NOT NULL REFERENCES app_users(telegram_id) ON DELETE CASCADE,
      friend_id UUID REFERENCES friends(id) ON DELETE SET NULL,
      name TEXT NOT NULL,
      wedding_date DATE,
      meat_price BIGINT NOT NULL CHECK (meat_price > 0),
      dollar_rate BIGINT NOT NULL DEFAULT 12800 CHECK (dollar_rate > 0),
      calc_type TEXT NOT NULL DEFAULT 'both',
      min_kg NUMERIC(8,2) NOT NULL DEFAULT 2 CHECK (min_kg >= 0),
      note TEXT NOT NULL DEFAULT '',
      archived BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS weddings_owner_idx ON weddings(telegram_id, wedding_date DESC);

    CREATE TABLE IF NOT EXISTS gifts (
      id UUID PRIMARY KEY,
      telegram_id BIGINT NOT NULL REFERENCES app_users(telegram_id) ON DELETE CASCADE,
      wedding_id UUID NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
      friend_id UUID NOT NULL REFERENCES friends(id) ON DELETE CASCADE,
      amount BIGINT NOT NULL CHECK (amount > 0),
      meat_price BIGINT NOT NULL CHECK (meat_price > 0),
      dollar_rate BIGINT NOT NULL DEFAULT 12800 CHECK (dollar_rate > 0),
      note TEXT NOT NULL DEFAULT '',
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE (wedding_id, friend_id)
    );
    CREATE INDEX IF NOT EXISTS gifts_owner_idx ON gifts(telegram_id);

    ALTER TABLE settings ADD COLUMN IF NOT EXISTS current_dollar_rate BIGINT NOT NULL DEFAULT 12800;
    ALTER TABLE weddings ADD COLUMN IF NOT EXISTS dollar_rate BIGINT NOT NULL DEFAULT 12800;
    ALTER TABLE weddings ADD COLUMN IF NOT EXISTS calc_type TEXT NOT NULL DEFAULT 'both';
    ALTER TABLE gifts ADD COLUMN IF NOT EXISTS dollar_rate BIGINT NOT NULL DEFAULT 12800;
  `);
}

module.exports = { pool, query, initDb };
