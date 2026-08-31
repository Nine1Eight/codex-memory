import sqlite3
import json
import time

DB_FILE = "ecosystem.db"
MIN_STAKE = 5.0
BASE_EMISSION = 1000.0
EMISSION_DECAY = 0.01

def connect():
    return sqlite3.connect(DB_FILE)

def init_ledger():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS genomes (
        hash TEXT PRIMARY KEY,
        species TEXT,
        stake REAL,
        reputation REAL,
        lineage TEXT,
        failure_debt REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL,
        from_hash TEXT,
        to_hash TEXT,
        amount REAL,
        reason TEXT
    )
    """)

    conn.commit()
    conn.close()

def register_genome(hash_id, species):
    conn = connect()
    c = conn.cursor()

    c.execute("SELECT hash FROM genomes WHERE hash=?", (hash_id,))
    if not c.fetchone():
        c.execute("""
        INSERT INTO genomes VALUES (?, ?, ?, ?, ?, ?)
        """, (hash_id, species, 10.0, 1.0, json.dumps([]), 0.0))

    conn.commit()
    conn.close()

def get_stake(hash_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT stake FROM genomes WHERE hash=?", (hash_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def update_stake(hash_id, delta):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE genomes SET stake = stake + ? WHERE hash=?", (delta, hash_id))
    conn.commit()
    conn.close()

def transfer(from_hash, to_hash, amount, reason):
    conn = connect()
    c = conn.cursor()

    c.execute("UPDATE genomes SET stake = stake - ? WHERE hash=?", (amount, from_hash))
    c.execute("UPDATE genomes SET stake = stake + ? WHERE hash=?", (amount, to_hash))

    c.execute("""
    INSERT INTO transactions (ts, from_hash, to_hash, amount, reason)
    VALUES (?, ?, ?, ?, ?)
    """, (time.time(), from_hash, to_hash, amount, reason))

    conn.commit()
    conn.close()

def purge_bankrupt():
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM genomes WHERE stake < ?", (MIN_STAKE,))
    conn.commit()
    conn.close()

def emission_for_generation(gen):
    return BASE_EMISSION / (1 + gen * EMISSION_DECAY)
