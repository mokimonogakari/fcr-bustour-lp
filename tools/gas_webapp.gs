/**
 * バスツアー用 GAS（ダッシュボードAPI ＋ 申し込み通知）
 *
 * 既存のウェブアプリのGASプロジェクトにこの内容を貼り付けて使う。
 *   1. doGet          … ダッシュボードが読む集計JSONを返す（アクセス時のみ実行）
 *   2. onFormSubmit   … フォーム送信の瞬間に通知メールを送る（定期実行なし）
 *
 * 初回だけ setupNotification() を実行してトリガーを設置する。
 * コードを更新したら「デプロイ > デプロイを管理 > 編集 > バージョン: 新しいバージョン」
 * で再デプロイする（URLは変わらない）。
 */

const SPREADSHEET_ID = '1ocIIxTurXOLTGyXQOhvq4fZ8g5ewqOnUuUHT_xWPPt4';
const FORM_ID = '1wpX3j14Y8DdBYRB1A-Xu5VoZR7kQv7Uxlj99ZEPP_0k';
const NOTIFY_EMAIL = 'y.oki.20017.441@gmail.com';
const SUM_SHEET = '集計';

// 集計シートの項目名 -> ダッシュボードが使うキー
const KEYS = {
  '申込組数': 'groups',
  '大人 合計人数': 'adults',
  '高校生以下 合計人数': 'kids',
  '合計人数': 'total',
  '参加費見込み（円）': 'revenue',
  '内訳未確認人数': 'unknown',
  'チケット必要枚数': 'tickets',
  '保留（確認中）組数': 'pending_groups',
  '保留（確認中）人数': 'pending_people',
  '最大想定人数（確定＋保留）': 'max_total'
};

/** ダッシュボードからのアクセス時に集計値を返す */
function doGet() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(SUM_SHEET);
  const rows = sheet.getRange('A2:B30').getValues();
  const out = {};
  rows.forEach(function (row) {
    const key = KEYS[String(row[0]).trim()];
    if (key) out[key] = Number(row[1]) || 0;
  });
  out.updated_at = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm');
  return ContentService.createTextOutput(JSON.stringify(out))
    .setMimeType(ContentService.MimeType.JSON);
}

/** 初回だけ実行: フォーム送信トリガーを設置する（重複は自動削除） */
function setupNotification() {
  ScriptApp.getProjectTriggers()
    .filter(function (t) { return t.getHandlerFunction() === 'onFormSubmitNotify'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onFormSubmitNotify')
    .forForm(FormApp.openById(FORM_ID))
    .onFormSubmit()
    .create();
  Logger.log('通知トリガーを設置しました');
}

/** フォーム送信時に呼ばれる（定期実行ではなくイベント発火） */
function onFormSubmitNotify(e) {
  const lines = e.response.getItemResponses().map(function (r) {
    const answer = r.getResponse();
    return r.getItem().getTitle() + '：' + (Array.isArray(answer) ? answer.join('、') : answer);
  });
  const submitted = Utilities.formatDate(
    e.response.getTimestamp(), 'Asia/Tokyo', 'yyyy/MM/dd HH:mm');
  MailApp.sendEmail(
    NOTIFY_EMAIL,
    '【バスツアー】新しい申し込みがありました',
    '申し込みフォームに新しい回答がありました。\n\n' +
    '送信日時：' + submitted + '\n' +
    lines.join('\n') +
    '\n\n申込一覧: https://docs.google.com/spreadsheets/d/' + SPREADSHEET_ID + '/edit');
}
