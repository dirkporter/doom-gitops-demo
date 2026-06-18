from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)
DB_HOST = os.getenv("DB_HOST", "doom-db-service")
DB_NAME = os.getenv("DB_NAME", "doom_stats")
DB_USER = os.getenv("DB_USER", "doom_admin")
DB_PASS = os.getenv("DB_PASSWORD", "doom_password")


def get_db_connection():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)


@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route('/level-complete', methods=['POST'])
def level_complete():
    data = request.get_json(force=True, silent=True) or {}
    player_id = data.get('player_id', 'anonymous')
    level = data.get('level')
    seconds = data.get('time_seconds')
    if not level or seconds is None:
        return jsonify({"status": "error", "message": "Missing level or time_seconds"}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO level_times (player_id, level_name, completion_time_seconds) VALUES (%s, %s, %s)',
        (player_id, level, seconds)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "player_id": player_id}), 200


@app.route('/scores', methods=['GET'])
def scores():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT player_id, level_name, completion_time_seconds, recorded_at '
                'FROM level_times ORDER BY recorded_at DESC LIMIT 50')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"player_id": r[0], "level": r[1], "time_seconds": r[2], "recorded_at": str(r[3])}
        for r in rows
    ]), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
