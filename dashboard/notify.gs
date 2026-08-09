// フォーム回答のメール通知
// 使い方: ダッシュボード用GASプロジェクトにこのファイルを追加し、
// setupNotification() を一度実行する（権限承認あり）。
// 以降、フォームに回答があるたびに NOTIFY_EMAIL へ回答内容がメールされる。

const NOTIFY_EMAIL = 'y.oki.20017.441@gmail.com';
const FORM_ID = '1wpX3j14Y8DdBYRB1A-Xu5VoZR7kQv7Uxlj99ZEPP_0k';

// 一度だけ実行: フォーム送信トリガーを設置する（重複は自動削除）
function setupNotification() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'onFormSubmitNotify')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('onFormSubmitNotify')
    .forForm(FormApp.openById(FORM_ID))
    .onFormSubmit()
    .create();
  Logger.log('通知トリガーを設置しました');
}

function onFormSubmitNotify(e) {
  const lines = e.response.getItemResponses().map(r => {
    const answer = r.getResponse();
    const text = Array.isArray(answer) ? answer.join('、') : answer;
    return r.getItem().getTitle() + '：' + text;
  });
  const body =
    'バスツアーの申し込みフォームに新しい回答がありました。\n\n' +
    lines.join('\n') +
    '\n\n回答一覧: https://docs.google.com/forms/d/' + FORM_ID + '/edit#responses';
  MailApp.sendEmail(NOTIFY_EMAIL, '【バスツアー】新しい申し込みがありました', body);
}
