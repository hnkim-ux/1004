// 진입점: 이벤트를 store 함수 호출로 연결하고 다시 그린다.
(function (TD) {
  const store = TD.store;
  const $ = (id) => document.getElementById(id);

  const ui = { editingId: null };
  const TOAST_MS = 5000;
  let toastTimer = null;
  let undoItems = null;
  let currentDay = null;

  function rerender() {
    TD.render(ui);
    if (ui.editingId) {
      const input = document.querySelector('.todo-edit');
      if (input && document.activeElement !== input) {
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
      }
    }
  }

  function itemId(el) {
    const li = el.closest('.todo-item');
    return li ? li.dataset.id : null;
  }

  function focusItemButton(id, selector) {
    const btn = document.querySelector(`.todo-item[data-id="${id}"] ${selector}`);
    if (btn) btn.focus();
  }

  // ---- 토스트 / 실행 취소 ----
  function showToast(text, items) {
    undoItems = items;
    $('toast-text').textContent = text;
    $('toast').hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, TOAST_MS);
  }

  function hideToast() {
    clearTimeout(toastTimer);
    undoItems = null;
    $('toast').hidden = true;
  }

  function deleteWithUndo(id) {
    const removed = store.remove(id);
    if (!removed) return;
    showToast('임무를 삭제했어요', [removed]);
    $('todo-input').focus();
  }

  // ---- 인라인 수정 ----
  function startEdit(id) {
    if (store.isReadOnly()) return;
    ui.editingId = id;
    rerender();
  }

  function finishEdit(save) {
    const id = ui.editingId;
    if (!id) return;
    const input = document.querySelector('.todo-edit');
    const value = input ? input.value.trim() : '';
    // confirm 중 blur가 다시 들어와도 무시되도록 먼저 해제
    ui.editingId = null;

    if (save && !value) {
      if (confirm('내용이 비어 있어요. 이 할일을 삭제할까요?')) {
        deleteWithUndo(id);
        return;
      }
    } else if (save) {
      store.update(id, value);
    }
    rerender();
    focusItemButton(id, '.edit');
  }

  // ---- 날짜 변경 감지 (자정을 넘겨 열어둔 경우) ----
  function checkDayChange() {
    const day = TD.date.today();
    if (day !== currentDay) {
      // 어제의 "오늘"을 보고 있었다면 새 오늘로 따라간다
      const wasViewingToday = store.getViewDate() === currentDay;
      currentDay = day;
      if (wasViewingToday) store.setViewDate(day);
      rerender();
    }
  }

  function bindEvents() {
    $('todo-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const input = $('todo-input');
      if (store.add(input.value)) {
        input.value = '';
        if (store.getFilter() === 'done') store.setFilter('all');
      }
      input.focus();
    });

    const list = $('todo-list');

    list.addEventListener('change', (e) => {
      if (e.target.classList.contains('todo-check')) {
        const id = itemId(e.target);
        store.toggle(id);
        focusItemButton(id, '.todo-check');
      }
    });

    list.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;
      const id = itemId(btn);
      if (btn.classList.contains('star')) {
        store.toggleImportant(id);
        focusItemButton(id, '.star');
      } else if (btn.classList.contains('edit')) {
        startEdit(id);
      } else if (btn.classList.contains('delete')) {
        deleteWithUndo(id);
      }
    });

    list.addEventListener('dblclick', (e) => {
      if (e.target.classList.contains('todo-text')) startEdit(itemId(e.target));
    });

    list.addEventListener('keydown', (e) => {
      if (!e.target.classList.contains('todo-edit') || e.isComposing) return;
      if (e.key === 'Enter') {
        e.preventDefault();
        finishEdit(true);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        finishEdit(false);
      }
    });

    list.addEventListener('focusout', (e) => {
      if (e.target.classList.contains('todo-edit')) finishEdit(true);
    });

    $('filters').addEventListener('click', (e) => {
      const btn = e.target.closest('.filter');
      if (btn) store.setFilter(btn.dataset.filter);
    });

    $('clear-done').addEventListener('click', () => {
      const { done } = store.getStats();
      if (done && confirm(`완료한 할일 ${done}개를 지울까요?`)) store.clearDone();
    });

    $('prev-day').addEventListener('click', () => store.shiftViewDate(-1));
    $('next-day').addEventListener('click', () => store.shiftViewDate(1));
    $('go-today').addEventListener('click', () => {
      store.setViewDate(TD.date.today());
      $('next-day').focus();
    });

    $('carry-accept').addEventListener('click', () => store.carryOver());
    $('carry-dismiss').addEventListener('click', () => store.dismissCarryOver());

    $('toast-undo').addEventListener('click', () => {
      if (undoItems) store.restore(undoItems);
      hideToast();
    });

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) checkDayChange();
    });
    window.addEventListener('focus', checkDayChange);
    setInterval(checkDayChange, 60 * 1000);
  }

  store.init();
  store.subscribe(rerender);
  bindEvents();
  currentDay = TD.date.today();
  rerender();
  $('js-fallback').hidden = true;
})(window.TD = window.TD || {});
