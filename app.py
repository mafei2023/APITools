import sqlite3
import time
import json
import base64
import re
import regex
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

DB_PATH = 'data.db'


# ─── Database ───────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT DEFAULT '',
            model TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            api_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            UNIQUE(group_id, api_key)
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            ok INTEGER NOT NULL,
            latency INTEGER,
            error TEXT,
            protocol TEXT,
            model TEXT,
            tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS removed_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            group_name TEXT,
            error TEXT,
            removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS add_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            group_id INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()


# ─── Helpers ─────────────────────────────────────────────────

def _normalize_key(raw):
    """Strip whitespace, decode Base64 if applicable."""
    k = raw.strip()
    if not k:
        return None
    if len(k) >= 4 and len(k) % 4 == 0 and re.match(r'^[A-Za-z0-9+/]+=*$', k):
        try:
            decoded = base64.b64decode(k).decode('utf-8')
            # 剔除中文字符
            decoded = regex.sub(r'\p{Han}+', '', decoded)
            if all(32 <= ord(c) <= 126 for c in decoded) and len(decoded) > 3:
                return decoded
        except Exception:
            pass
    return k


# ─── Page ───────────────────────────────────────────────────

@app.route('/')
def index():
    return send_file('index.html')


# ─── Groups ─────────────────────────────────────────────────

@app.route('/api/groups', methods=['GET'])
def get_groups():
    conn = get_db()
    groups = conn.execute('SELECT * FROM groups ORDER BY id').fetchall()
    result = []
    for g in groups:
        keys = conn.execute(
            'SELECT id, api_key FROM keys WHERE group_id = ? ORDER BY id', (g['id'],)
        ).fetchall()
        result.append({
            'id': g['id'],
            'name': g['name'],
            'protocol': g['protocol'] or '',
            'model': g['model'] or '',
            'keys': [{'id': k['id'], 'api_key': k['api_key']} for k in keys]
        })
    conn.close()
    return jsonify(result)


@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '请输入分组名称'}), 400
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO groups (name, protocol, model) VALUES (?, ?, ?)',
        (name, data.get('protocol', ''), data.get('model', ''))
    )
    conn.commit()
    group_id = cur.lastrowid
    conn.close()
    return jsonify({'id': group_id, 'name': name})


@app.route('/api/groups/<int:gid>', methods=['PUT'])
def update_group(gid):
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '请输入分组名称'}), 400
    conn = get_db()
    group = conn.execute('SELECT id FROM groups WHERE id=?', (gid,)).fetchone()
    if not group:
        conn.close()
        return jsonify({'error': '分组不存在'}), 404
    conn.execute(
        'UPDATE groups SET name=?, protocol=?, model=? WHERE id=?',
        (name, data.get('protocol', ''), data.get('model', ''), gid)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/groups/<int:gid>', methods=['DELETE'])
def delete_group(gid):
    conn = get_db()
    group = conn.execute('SELECT id, name FROM groups WHERE id=?', (gid,)).fetchone()
    if not group:
        conn.close()
        return jsonify({'error': '分组不存在'}), 404
    keys = conn.execute('SELECT api_key FROM keys WHERE group_id=?', (gid,)).fetchall()
    for k in keys:
        conn.execute(
            'INSERT INTO removed_keys (api_key, group_name, error) VALUES (?, ?, ?)',
            (k['api_key'], group['name'], '删除分组')
        )
    conn.execute('DELETE FROM groups WHERE id=?', (gid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── Keys ───────────────────────────────────────────────────

@app.route('/api/groups/<int:gid>/keys', methods=['POST'])
def add_keys(gid):
    data = request.json
    raw_keys = data.get('keys', [])
    if not raw_keys:
        return jsonify({'error': '没有有效的密钥'}), 400

    conn = get_db()
    group = conn.execute('SELECT * FROM groups WHERE id=?', (gid,)).fetchone()
    if not group:
        conn.close()
        return jsonify({'error': '分组不存在'}), 404

    protocol = group['protocol'] or ''
    model = group['model'] or ''

    existing = {r['api_key'] for r in conn.execute(
        'SELECT api_key FROM keys WHERE group_id=?', (gid,)
    ).fetchall()}

    # Normalize and deduplicate
    new_keys = []
    skipped = 0
    for raw in raw_keys:
        k = _normalize_key(raw)
        if not k:
            continue
        if k in existing:
            skipped += 1
            continue
        new_keys.append(k)
        existing.add(k)

    if not new_keys:
        conn.close()
        return jsonify({'added': 0, 'skipped': skipped, 'failed': 0, 'failed_keys': []})

    # If no protocol configured, add without testing
    if not protocol:
        added = 0
        for k in new_keys:
            try:
                conn.execute('INSERT INTO keys (group_id, api_key) VALUES (?, ?)', (gid, k))
                conn.execute('INSERT INTO add_events (api_key, group_id) VALUES (?, ?)', (k, gid))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
        conn.close()
        return jsonify({'added': added, 'skipped': skipped, 'failed': 0, 'failed_keys': []})

    # Test keys concurrently, only add those that pass
    test_map = {}
    with ThreadPoolExecutor(max_workers=min(len(new_keys), 20)) as executor:
        future_to_key = {executor.submit(_do_test, protocol, k, model): k for k in new_keys}
        for future in as_completed(future_to_key):
            k = future_to_key[future]
            test_map[k] = future.result()

    added = 0
    failed = 0
    failed_keys = []
    for k in new_keys:
        res = test_map[k]
        if res['ok']:
            try:
                conn.execute('INSERT INTO keys (group_id, api_key) VALUES (?, ?)', (gid, k))
                conn.execute('INSERT INTO add_events (api_key, group_id) VALUES (?, ?)', (k, gid))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
        else:
            failed += 1
            failed_keys.append({'api_key': k, 'error': res['error']})
        # Save test result regardless
        conn.execute(
            'INSERT INTO test_results (api_key, ok, latency, error, protocol, model) VALUES (?,?,?,?,?,?)',
            (k, int(res['ok']), res['latency'], res['error'], protocol, model)
        )

    conn.commit()
    conn.close()
    return jsonify({'added': added, 'skipped': skipped, 'failed': failed, 'failed_keys': failed_keys})


@app.route('/api/keys/<int:kid>', methods=['DELETE'])
def delete_key(kid):
    conn = get_db()
    row = conn.execute(
        'SELECT k.api_key, g.name AS group_name FROM keys k JOIN groups g ON g.id = k.group_id WHERE k.id=?',
        (kid,)
    ).fetchone()
    if row:
        conn.execute(
            'INSERT INTO removed_keys (api_key, group_name, error) VALUES (?, ?, ?)',
            (row['api_key'], row['group_name'], '手动删除')
        )
    conn.execute('DELETE FROM keys WHERE id=?', (kid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/groups/<int:gid>/keys', methods=['DELETE'])
def clear_keys(gid):
    conn = get_db()
    rows = conn.execute(
        'SELECT k.api_key, g.name AS group_name FROM keys k JOIN groups g ON g.id = k.group_id WHERE k.group_id=?',
        (gid,)
    ).fetchall()
    for r in rows:
        conn.execute(
            'INSERT INTO removed_keys (api_key, group_name, error) VALUES (?, ?, ?)',
            (r['api_key'], r['group_name'], '清空分组')
        )
    conn.execute('DELETE FROM keys WHERE group_id=?', (gid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── Aggregate (all keys virtual group) ─────────────────────

@app.route('/api/all-keys', methods=['GET'])
def get_all_keys():
    """List every key across all groups, with their group info."""
    conn = get_db()
    rows = conn.execute('''
        SELECT k.id, k.api_key, k.group_id, g.name AS group_name,
               g.protocol AS protocol, g.model AS model
        FROM keys k JOIN groups g ON g.id = k.group_id
        ORDER BY g.id, k.id
    ''').fetchall()
    conn.close()
    return jsonify([{
        'id': r['id'], 'api_key': r['api_key'],
        'group_id': r['group_id'], 'group_name': r['group_name'],
        'protocol': r['protocol'] or '', 'model': r['model'] or ''
    } for r in rows])


@app.route('/api/test-all-keys', methods=['POST'])
def test_all_keys_global():
    """Test every key across all groups using its own group's protocol/model."""
    conn = get_db()
    rows = conn.execute('''
        SELECT k.api_key, g.protocol, g.model, g.id AS group_id, g.name AS group_name
        FROM keys k JOIN groups g ON g.id = k.group_id
        ORDER BY g.id, k.id
    ''').fetchall()
    conn.close()

    # Separate keys that need testing vs those with missing protocol
    skipped = []
    to_test = []
    for r in rows:
        protocol = r['protocol'] or ''
        if not protocol:
            skipped.append({
                'api_key': r['api_key'], 'group_id': r['group_id'], 'group_name': r['group_name'],
                'ok': False, 'latency': 0, 'error': '该分组未配置接口协议'
            })
        else:
            to_test.append(r)

    # Concurrent testing
    test_results_map = {}
    with ThreadPoolExecutor(max_workers=min(len(to_test), 20)) as executor:
        future_to_key = {
            executor.submit(_do_test, r['protocol'], r['api_key'], r['model'] or ''): r
            for r in to_test
        }
        for future in as_completed(future_to_key):
            r = future_to_key[future]
            res = future.result()
            test_results_map[r['api_key']] = res

    # Build results and pending writes in original order
    results = list(skipped)
    pending_writes = []
    for r in to_test:
        res = test_results_map[r['api_key']]
        pending_writes.append(
            (r['api_key'], int(res['ok']), res['latency'], res['error'], r['protocol'], r['model'] or '')
        )
        results.append({
            'api_key': r['api_key'], 'group_id': r['group_id'], 'group_name': r['group_name'],
            **res
        })

    conn = get_db()
    conn.executemany(
        'INSERT INTO test_results (api_key, ok, latency, error, protocol, model) VALUES (?,?,?,?,?,?)',
        pending_writes
    )
    conn.commit()
    conn.close()
    return jsonify(results)


@app.route('/api/remove-failed', methods=['POST'])
def remove_failed_keys():
    """Remove every key whose latest test_result is failed; log them in removed_keys."""
    conn = get_db()
    rows = conn.execute('''
        SELECT k.id AS key_id, k.api_key, g.name AS group_name, t.error
        FROM keys k
        JOIN groups g ON g.id = k.group_id
        JOIN (
            SELECT api_key, MAX(id) AS max_id FROM test_results GROUP BY api_key
        ) latest ON latest.api_key = k.api_key
        JOIN test_results t ON t.id = latest.max_id
        WHERE t.ok = 0
    ''').fetchall()

    removed = 0
    for r in rows:
        conn.execute(
            'INSERT INTO removed_keys (api_key, group_name, error) VALUES (?, ?, ?)',
            (r['api_key'], r['group_name'], r['error'])
        )
        conn.execute('DELETE FROM keys WHERE id=?', (r['key_id'],))
        removed += 1
    conn.commit()
    conn.close()
    return jsonify({'removed': removed})


# ─── Stats ──────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    total_added = conn.execute('SELECT COUNT(*) AS c FROM add_events').fetchone()['c']
    total_removed = conn.execute('SELECT COUNT(*) AS c FROM removed_keys').fetchone()['c']
    current_total = conn.execute('SELECT COUNT(*) AS c FROM keys').fetchone()['c']

    per_group = conn.execute('''
        SELECT g.id, g.name, COUNT(k.id) AS count
        FROM groups g LEFT JOIN keys k ON k.group_id = g.id
        GROUP BY g.id ORDER BY g.id
    ''').fetchall()

    latest_status = conn.execute('''
        SELECT t.ok, COUNT(*) AS c FROM test_results t
        JOIN (
            SELECT api_key, MAX(id) AS max_id FROM test_results GROUP BY api_key
        ) latest ON latest.max_id = t.id
        JOIN keys k ON k.api_key = t.api_key
        GROUP BY t.ok
    ''').fetchall()
    ok_count = 0
    fail_count = 0
    for r in latest_status:
        if r['ok']:
            ok_count = r['c']
        else:
            fail_count = r['c']

    conn.close()
    return jsonify({
        'total_added': total_added,
        'total_removed': total_removed,
        'current_total': current_total,
        'ok_count': ok_count,
        'fail_count': fail_count,
        'untested_count': max(0, current_total - ok_count - fail_count),
        'per_group': [{'id': r['id'], 'name': r['name'], 'count': r['count']} for r in per_group],
    })


# ─── Test ───────────────────────────────────────────────────

def _normalize_base_url(url):
    """Ensure base_url ends with /v1; if user already provided it, leave as-is."""
    u = (url or '').strip().rstrip('/')
    if not u:
        return u
    if re.search(r'/v\d+$', u):
        return u
    return u + '/v1'


def _do_test(protocol, api_key, model):
    """Send a test request via the OpenAI SDK, return result dict."""
    model = model or 'gpt-3.5-turbo'
    base_url = _normalize_base_url(protocol)
    start = time.time()
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
        client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': '你好'}],
            max_completion_tokens=10,
        )
        latency = int((time.time() - start) * 1000)
        return {'ok': True, 'latency': latency, 'error': None}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        msg = getattr(e, 'message', None) or str(e)
        return {'ok': False, 'latency': latency, 'error': msg}


@app.route('/api/test', methods=['POST'])
def test_single():
    data = request.json
    protocol = data.get('protocol', '')
    api_key = data.get('key', '')
    model = data.get('model', '')
    if not protocol:
        return jsonify({'error': '请先填写接口协议地址'}), 400
    if not api_key:
        return jsonify({'error': '密钥不能为空'}), 400

    result = _do_test(protocol, api_key, model)

    conn = get_db()
    conn.execute(
        'INSERT INTO test_results (api_key, ok, latency, error, protocol, model) VALUES (?,?,?,?,?,?)',
        (api_key, int(result['ok']), result['latency'], result['error'], protocol, model)
    )
    conn.commit()
    conn.close()

    return jsonify(result)


@app.route('/api/test-all', methods=['POST'])
def test_all():
    data = request.json
    group_id = data.get('group_id')
    if not group_id:
        return jsonify({'error': '缺少 group_id'}), 400

    conn = get_db()
    group = conn.execute('SELECT * FROM groups WHERE id=?', (group_id,)).fetchone()
    if not group:
        conn.close()
        return jsonify({'error': '分组不存在'}), 404

    protocol = group['protocol']
    model = group['model'] or ''
    if not protocol:
        conn.close()
        return jsonify({'error': '请先填写接口协议地址'}), 400

    keys = conn.execute('SELECT api_key FROM keys WHERE group_id=?', (group_id,)).fetchall()
    conn.close()

    results = []
    pending_writes = []

    def _test_one(row):
        api_key = row['api_key']
        r = _do_test(protocol, api_key, model)
        return api_key, r

    with ThreadPoolExecutor(max_workers=min(len(keys), 20)) as executor:
        future_to_key = {executor.submit(_test_one, row): row for row in keys}
        result_map = {}
        for future in as_completed(future_to_key):
            api_key, r = future.result()
            result_map[api_key] = r

    for row in keys:
        api_key = row['api_key']
        r = result_map[api_key]
        pending_writes.append(
            (api_key, int(r['ok']), r['latency'], r['error'], protocol, model)
        )
        results.append({'api_key': api_key, **r})

    conn = get_db()
    conn.executemany(
        'INSERT INTO test_results (api_key, ok, latency, error, protocol, model) VALUES (?,?,?,?,?,?)',
        pending_writes
    )
    conn.commit()
    conn.close()

    return jsonify(results)


@app.route('/api/test-results', methods=['GET'])
def get_test_results():
    conn = get_db()
    rows = conn.execute(
        'SELECT api_key, ok, latency, error, tested_at FROM test_results '
        'WHERE id IN (SELECT MAX(id) FROM test_results GROUP BY api_key) '
        'ORDER BY tested_at DESC'
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r['api_key']] = {
            'ok': bool(r['ok']),
            'latency': r['latency'],
            'error': r['error'],
            'tested_at': r['tested_at']
        }
    return jsonify(result)


# ─── Health ─────────────────────────────────────────────────

@app.route('/api/ping')
def ping():
    return 'pong'


# ─── Start ──────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print('API Key Manager started')
    print('   http://localhost:5000')
    app.run(host='127.0.0.1', port=5000, debug=True)
