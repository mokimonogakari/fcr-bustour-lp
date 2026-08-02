#!/usr/bin/env python3
"""集計スプレッドシートから人数を読み、dashboard/data.json を更新してpushする。

cron (15分毎) 実行前提。値に変化がなければ commit しない。
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
END_DATE = date(2026, 8, 29)  # ツアー当日いっぱいで更新終了


def remove_own_cron():
    """crontab から自分のエントリを削除する。"""
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
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/集計!A2:B6',
        headers={'Authorization': f'Bearer {creds.token}'},
        params={'valueRenderOption': 'UNFORMATTED_VALUE'}, timeout=30)
    r.raise_for_status()
    rows = {row[0]: int(row[1]) for row in r.json().get('values', []) if len(row) > 1}

    new = {
        'groups': rows.get('申込組数', 0),
        'adults': rows.get('大人 合計人数', 0),
        'kids': rows.get('高校生以下 合計人数', 0),
        'total': rows.get('合計人数', 0),
        'revenue': rows.get('参加費見込み（円）', 0),
    }

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
