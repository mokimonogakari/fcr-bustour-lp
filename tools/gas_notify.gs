/**
 * 申し込み通知（ダッシュボードAPIとは別のGASプロジェクト）
 *
 * フォーム送信の瞬間にメールを送る。定期実行（cron）は使わない。
 * メール送信・トリガー設置の権限が必要なため、集計APIとは別プロジェクトにして
 * ダッシュボードの動作に影響しないようにしている。
 *
 * 使い方: setupNotification() を一度だけ実行する（権限の承認画面が出る）。
 * トリガー方式のためウェブアプリのデプロイは不要。
 */

const FORM_ID = '1wpX3j14Y8DdBYRB1A-Xu5VoZR7kQv7Uxlj99ZEPP_0k';
const SPREADSHEET_ID = '1ocIIxTurXOLTGyXQOhvq4fZ8g5ewqOnUuUHT_xWPPt4';
const NOTIFY_EMAIL = 'y.oki.20017.441@gmail.com';

/** 初回だけ実行: フォーム送信トリガーを設置する（重複は自動削除） */
function setupNotification() {
  ScriptApp.getProjectTriggers()
    .filter(function (t) { return t.getHandlerFunction() === 'onFormSubmitNotify'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onFormSubmitNotify')
    .forForm(FormApp.openById(FORM_ID))
    .onFormSubmit()
    .create();
  MailApp.sendEmail(NOTIFY_EMAIL, '【バスツアー】通知の設定が完了しました',
    '申し込みフォームの通知設定が完了しました。\n' +
    '以降、新しい回答が届くたびにこのアドレスへ通知します。');
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
