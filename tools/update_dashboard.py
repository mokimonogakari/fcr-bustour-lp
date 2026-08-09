#!/usr/bin/env python3
"""集計シートを読み、dashboard/data.json を更新してpushする。

GASウェブアプリが返すのは基本5項目のみのため、保留人数・チケット枚数などの
拡張項目をこのファイル経由でダッシュボードへ渡す。氏名や連絡先は書き出さない
（公開リポジトリのため集計値のみ）。
cron (10分毎) 実行前提。値に変化がなければ commit しない。
実行: /home/claude/google-tools/.venv/bin/python3 update_dashboard.py
"""
import json
import subprocess
import sys
from datetime import date, datetime, timezone, timedelta

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

REPO = '/home/claude/work/fcr-bustour'
DATA = f'{REPO}/dashboard/data.json'
SPREADSHEET_ID = '1ocIIxTurXOLTGyXQOhvq4fZ8g5ewqOnUuUHT_xWPPt4'
JST = timezone(timedelta(hours=9))
END_DATE = date(2026, 8, 30)  # ツアー翌日で更新終了

# 集計シートの項目名 -> data.json のキー
KEYS = {
    '申込組数': 'groups',
    '大人 合計人数': 'adults',
    '高校生以下 合計人数': 'kids',
    '合計人数': 'total',
    '参加費見込み（円）': 'revenue',
    '内訳未確認人数': 'unknown',
    'チケット必要枚数': 'tickets',
    '保留（確認中）組数': 'pending_groups',
    '保留（確認中）人数': 'pending_people',
    '最大想定人数（確定＋保留）': 'max_total',
}


def remove_own_cron():
    cur = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True).stdout
    kept = [l for l in cur.splitlines() if 'update_dashboard.py' not in l]
    subprocess.run(['crontab', '-'], input='\n'.join(kept) + '\n', text=True, check=True)


def get_creds():
    tok = json.load(open('/home/claude/token_gmail.json'))
    cred_data = json.load(open('/home/claude/credentials.json'))
    key = 'installed' if 'installed' in cred_data else 'web'
    creds = Credentials(
        token=tok['access_token'], refresh_token=tok['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=cred_data[key]['client_id'],
        client_secret=cred_data[key]['client_secret'])
    creds.refresh(Request())
    return creds


def main():
    if datetime.now(JST).date() > END_DATE:
        remove_own_cron()
        print(f'{END_DATE} を過ぎたため cron エントリを削除して終了')
        return
    # 先にpullしておく（書き換え後にpullするとrebaseが失敗する）
    subprocess.run(['git', '-C', REPO, 'pull', '-q', '--rebase', '--autostash',
                    'origin', 'main'], check=True)
    creds = get_creds()
    r = requests.get(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/集計!A2:B20',
        headers={'Authorization': f'Bearer {creds.token}'},
        params={'valueRenderOption': 'UNFORMATTED_VALUE'}, timeout=30)
    r.raise_for_status()
    rows = {row[0]: row[1] for row in r.json().get('values', []) if len(row) > 1}

    new = {}
    for label, key in KEYS.items():
        try:
            new[key] = int(rows.get(label, 0))
        except (TypeError, ValueError):
            new[key] = 0

    try:
        old = {k: v for k, v in json.load(open(DATA)).items() if k != 'updated_at'}
    except Exception:
        old = None
    if old == new:
        print('no change')
        return

    new['updated_at'] = datetime.now(JST).strftime('%Y-%m-%d %H:%M')
    with open(DATA, 'w') as f:
        json.dump(new, f, ensure_ascii=False, indent=1)

    for cmd in [
        ['git', '-C', REPO, 'add', 'dashboard/data.json'],
        ['git', '-C', REPO, 'commit', '-q', '-m', 'ダッシュボード集計データ更新'],
        ['git', '-C', REPO, 'push', '-q', 'origin', 'main'],
    ]:
        subprocess.run(cmd, check=True)
    print('updated:', new)


if __name__ == '__main__':
    sys.exit(main())
