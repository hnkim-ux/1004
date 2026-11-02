// 상태 관리 + localStorage 입출력. 상태 변경은 이 모듈의 함수로만 한다.
(function (TD) {
  const KEYS = {
    todos: 'todolist:v1:todos',
    lastOpened: 'todolist:v1:lastOpenedDate',
    filter: 'todolist:v1:filter',
  };
  const FILTERS = ['all', 'active', 'done'];
  const MAX_LENGTH = 200;

  let todos = [];
  let filter = 'all';
  let lastOpened = null; // 이월 배너를 마지막으로 처리한 날짜
  let viewDate = null; // 화면에 보고 있는 날짜. 저장하지 않고 항상 오늘로 시작
  let persistent = true;
  const listeners = new Set();

  function storageAvailable() {
    try {
      const key = 'todolist:v1:__test';
      localStorage.setItem(key, '1');
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      return false;
    }
  }

  function read(key) {
    if (!persistent) return null;
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function write(key, value) {
    if (!persistent) return;
    try {
      localStorage.setItem(key, value);
    } catch (e) {
      persistent = false;
    }
  }

  function normalize(t) {
    const todo = {
      id: t.id,
      text: String(t.text).slice(0, MAX_LENGTH),
      done: !!t.done,
      important: !!t.important,
      date: t.date,
      createdAt: Number(t.createdAt) || Date.now(),
      order: Number(t.order) || 0,
    };
    if (todo.done && t.completedAt) todo.completedAt = Number(t.completedAt);
    return todo;
  }

  function isValid(t) {
    return t && typeof t.id === 'string' && typeof t.text === 'string' &&
      /^\d{4}-\d{2}-\d{2}$/.test(t.date);
  }

  function load() {
    todos = [];
    const raw = read(KEYS.todos);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) throw new Error('todos is not an array');
        todos = parsed.filter(isValid).map(normalize);
      } catch (e) {
        // 손상된 원본은 백업해 두고 빈 목록으로 시작
        write(KEYS.todos + ':backup', raw);
      }
    }
    const savedFilter = read(KEYS.filter);
    filter = FILTERS.includes(savedFilter) ? savedFilter : 'all';
    lastOpened = read(KEYS.lastOpened);
  }

  function save() {
    write(KEYS.todos, JSON.stringify(todos));
  }

  function emit() {
    listeners.forEach((fn) => fn());
  }

  function commit() {
    save();
    emit();
  }

  function newId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return Date.now().toString(36) + Math.random().toString(36).slice(2);
  }

  function cleanText(text) {
    return String(text).trim().slice(0, MAX_LENGTH);
  }

  function nextOrder(date) {
    return todos
      .filter((t) => t.date === date)
      .reduce((max, t) => Math.max(max, t.order), 0) + 1;
  }

  function find(id) {
    return todos.find((t) => t.id === id);
  }

  // 지난 날짜는 완료 체크만 가능. 그 외 변경은 오늘과 미래 날짜만 할 수 있다.
  function isEditableDate(date) {
    return date >= TD.date.today();
  }

  function findEditable(id) {
    const t = find(id);
    return t && isEditableDate(t.date) ? t : null;
  }

  // 중요 항목 우선, 그다음 order. 완료 여부로는 재정렬하지 않는다.
  function compare(a, b) {
    if (a.important !== b.important) return a.important ? -1 : 1;
    return a.order - b.order;
  }

  function add(text) {
    const clean = cleanText(text);
    if (!clean || !isEditableDate(viewDate)) return null;
    const todo = {
      id: newId(),
      text: clean,
      done: false,
      important: false,
      date: viewDate,
      createdAt: Date.now(),
      order: nextOrder(viewDate),
    };
    todos.push(todo);
    commit();
    return todo;
  }

  function toggle(id) {
    const t = find(id);
    if (!t) return;
    t.done = !t.done;
    if (t.done) t.completedAt = Date.now();
    else delete t.completedAt;
    commit();
  }

  function toggleImportant(id) {
    const t = findEditable(id);
    if (!t) return;
    t.important = !t.important;
    commit();
  }

  function update(id, text) {
    const t = findEditable(id);
    const clean = cleanText(text);
    if (!t || !clean) return false;
    t.text = clean;
    commit();
    return true;
  }

  function remove(id) {
    const index = todos.findIndex((t) => t.id === id);
    if (index < 0 || !isEditableDate(todos[index].date)) return null;
    const [removed] = todos.splice(index, 1);
    commit();
    return removed;
  }

  // 실행 취소용: 삭제했던 항목을 원래 date/order 그대로 되돌린다.
  function restore(items) {
    items.forEach((item) => {
      if (!find(item.id)) todos.push(item);
    });
    commit();
  }

  function clearDone() {
    if (!isEditableDate(viewDate)) return [];
    const removed = todos.filter((t) => t.date === viewDate && t.done);
    todos = todos.filter((t) => !(t.date === viewDate && t.done));
    commit();
    return removed;
  }

  function getDayList() {
    return todos.filter((t) => t.date === viewDate).sort(compare);
  }

  function getVisible() {
    const list = getDayList();
    if (filter === 'active') return list.filter((t) => !t.done);
    if (filter === 'done') return list.filter((t) => t.done);
    return list;
  }

  function getStats() {
    const list = getDayList();
    const done = list.filter((t) => t.done).length;
    return { total: list.length, done, remaining: list.length - done };
  }

  // 오늘 아직 배너를 처리하지 않았다면, 지난 날짜의 미완료 항목
  function getCarryOver() {
    const today = TD.date.today();
    if (lastOpened === today) return [];
    return todos.filter((t) => t.date < today && !t.done);
  }

  function markOpened(date) {
    lastOpened = date;
    write(KEYS.lastOpened, date);
  }

  // 미완료 항목을 오늘로 "이동"한다.
  function carryOver() {
    const today = TD.date.today();
    const items = getCarryOver().sort((a, b) => a.date.localeCompare(b.date) || compare(a, b));
    let order = nextOrder(today);
    items.forEach((t) => {
      t.date = today;
      t.order = order++;
    });
    markOpened(today);
    commit();
  }

  function dismissCarryOver() {
    markOpened(TD.date.today());
    emit();
  }

  function setFilter(next) {
    if (!FILTERS.includes(next) || next === filter) return;
    filter = next;
    write(KEYS.filter, next);
    emit();
  }

  function setViewDate(date) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date === viewDate) return;
    viewDate = date;
    emit();
  }

  function shiftViewDate(n) {
    setViewDate(TD.date.addDays(viewDate, n));
  }

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function init() {
    persistent = storageAvailable();
    viewDate = TD.date.today();
    load();
    if (persistent) {
      // 다른 탭에서 바뀐 내용을 반영
      window.addEventListener('storage', (e) => {
        if (e.key === null || e.key.startsWith('todolist:v1:')) {
          load();
          emit();
        }
      });
    }
  }

  TD.store = {
    MAX_LENGTH,
    init,
    subscribe,
    add,
    toggle,
    toggleImportant,
    update,
    remove,
    restore,
    clearDone,
    carryOver,
    dismissCarryOver,
    setFilter,
    setViewDate,
    shiftViewDate,
    getViewDate: () => viewDate,
    isReadOnly: () => !isEditableDate(viewDate),
    getFilter: () => filter,
    getVisible,
    getStats,
    getCarryOver,
    isPersistent: () => persistent,
  };
})(window.TD = window.TD || {});
