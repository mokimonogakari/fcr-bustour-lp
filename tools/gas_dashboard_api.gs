/**
 * ダッシュボード用 集計API（スプレッドシート内蔵のGASプロジェクト）
 *
 * 集計シートの項目をそのままJSONで返す。項目を増やしたら KEYS に足すだけでよい。
 * SpreadsheetApp.getActive() のみを使い、追加の権限を必要としない
 * （メール送信やトリガーは通知用の別プロジェクトに分けている）。
 */

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
  '最大想定人数（確定＋保留）': 'max_total',
  'チケット必要枚数（保留含む最大）': 'tickets_max'
};

function doGet() {
  const sheet = SpreadsheetApp.getActive().getSheetByName('集計');
  const out = {};
  sheet.getRange('A2:B30').getValues().forEach(function (row) {
    const key = KEYS[String(row[0]).trim()];
    if (key) out[key] = Number(row[1]) || 0;
  });
  out.updated_at = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm');
  return ContentService.createTextOutput(JSON.stringify(out))
    .setMimeType(ContentService.MimeType.JSON);
}
