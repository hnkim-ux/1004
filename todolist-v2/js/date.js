// 로컬 시간 기준 날짜 유틸. toISOString()은 UTC라서 사용하지 않는다.
(function (TD) {
  const DAYS = ['일', '월', '화', '수', '목', '금', '토'];

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  // Date → "YYYY-MM-DD"
  function toKey(d) {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  function today() {
    return toKey(new Date());
  }

  // "YYYY-MM-DD" → "2026년 11월 2일 (월)"
  function format(key) {
    const d = fromKey(key);
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${DAYS[d.getDay()]})`;
  }

  function fromKey(key) {
    const [y, m, d] = key.split('-').map(Number);
    return new Date(y, m - 1, d);
  }

  // "YYYY-MM-DD"에서 n일 이동
  function addDays(key, n) {
    const d = fromKey(key);
    d.setDate(d.getDate() + n);
    return toKey(d);
  }

  // 오늘 기준 상대 이름: "오늘" / "내일" / "어제" / ''
  function relative(key) {
    const t = today();
    if (key === t) return '오늘';
    if (key === addDays(t, 1)) return '내일';
    if (key === addDays(t, -1)) return '어제';
    return '';
  }

  TD.date = { toKey, today, format, addDays, relative };
})(window.TD = window.TD || {});
