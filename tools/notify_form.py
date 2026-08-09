#!/usr/bin/env python3
"""フォームの新規回答を検知して NOTIFY_EMAIL へメール通知する。

cron (5分毎) 実行前提。通知済みの回答行数を state ファイルに記録し、
増えた分だけ Gmail API でメールする。初回実行時は既存回答を通知せずに
state を初期化し、設定完了のテストメールを送る。
END_DATE を過ぎたら自分の cron エントリを削除して終了。
実行: /home/claude/google-tools/.venv/bin/python3 notify_form.py
"""
import base64
import json
import subprocess
import sys
from datetime import date, datetime, timezone, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SPREADSHEET_ID = '1ocIIxTurXOLTGyXQOhvq4fZ8g5ewqOnUuUHT_xWPPt4'
NOTIFY_EMAIL = 'y.oki.20017.441@gmail.com'
FORM_EDIT_URL = 'https://docs.google.com/forms/d/1wpX3j14Y8DdBYRB1A-Xu5VoZR7kQv7Uxlj99ZEPP_0k/edit#responses'
STATE = Path('/home/claude/.form_notify_state.json')
JST = timezone(timedelta(hours=9))
END_DATE = date(2026, 8, 30)  # ツアー翌日で通知終了


def remove_own_cron():
    cur = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=True).stdout
    kept = [l for l in cur.splitlines() if 'notify_form.py' not in l]
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


def send_mail(creds, subject, body):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['To'] = NOTIFY_EMAIL
    msg['Subject'] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    r = requests.post(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        headers={'Authorization': f'Bearer {creds.token}'},
        json={'raw': raw}, timeout=30)
    r.raise_for_status()


def fetch_rows(creds):
    headers = {'Authorization': f'Bearer {creds.token}'}
    meta = requests.get(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}',
        headers=headers, params={'fields': 'sheets.properties.title'}, timeout=30)
    meta.raise_for_status()
    titles = [s['properties']['title'] for s in meta.json()['sheets']]
    sheet = next((t for t in titles if t.startswith('フォームの回答')), titles[0])
    r = requests.get(
        f'https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/'
        + quote(f'{sheet}!A1:Z10000', safe='!:'),
        headers=headers, timeout=30)
    r.raise_for_status()
    values = r.json().get('values', [])
    return (values[0], values[1:]) if values else ([], [])


def main():
    now = datetime.now(JST)
    if now.date() > END_DATE:
        remove_own_cron()
        print(f'{END_DATE} を過ぎたため cron エントリを削除して終了')
        return
    creds = get_creds()
    header, data = fetch_rows(creds)

    if not STATE.exists():
        STATE.write_text(json.dumps({'notified': len(data)}))
        send_mail(creds, '【バスツアー】回答通知の設定が完了しました',
                  f'フォーム回答の通知設定が完了しました。\n'
                  f'以降、新しい回答があるたびにこのアドレスへ通知します。\n'
                  f'（現在の回答数: {len(data)}件）\n\n回答一覧: {FORM_EDIT_URL}')
        print(f'state初期化（既存{len(data)}件）・テストメール送信')
        return

    notified = json.loads(STATE.read_text()).get('notified', 0)
    new_rows = data[notified:]
    if not new_rows:
        print('no change')
        return

    for row in new_rows:
        lines = [f'{h}：{v}' for h, v in zip(header, row + [''] * (len(header) - len(row))) if v]
        send_mail(creds, '【バスツアー】新しい申し込みがありました',
                  '申し込みフォームに新しい回答がありました。\n\n'
                  + '\n'.join(lines)
                  + f'\n\n回答一覧: {FORM_EDIT_URL}')
    STATE.write_text(json.dumps({'notified': len(data)}))
    print(f'{len(new_rows)}件通知（累計{len(data)}件） {now.strftime("%H:%M")}')


if __name__ == '__main__':
    sys.exit(main())
