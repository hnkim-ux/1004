// 상태를 읽어 DOM을 그린다. 상태를 바꾸지 않는다.
(function (TD) {
  const $ = (id) => document.getElementById(id);

  const SVG_ATTRS = 'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  const ICONS = {
    star: (filled) =>
      `<svg ${SVG_ATTRS}><path fill="${filled ? 'currentColor' : 'none'}" d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>`,
    edit: `<svg ${SVG_ATTRS}><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>`,
    trash: `<svg ${SVG_ATTRS}><path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/></svg>`,
  };

  const EMPTY = {
    active: '남은 임무가 없어요. 임무 완수!',
    done: '아직 완수한 임무가 없어요',
  };

  // 해당 날짜에 할일이 하나도 없을 때의 안내
  function emptyDayText(date, today) {
    if (date === today) return '임무 대기 중… 오늘 할 일을 알려 주세요!';
    if (date > today) return '미래의 임무를 미리 등록해 두세요';
    return '이 날은 기록된 임무가 없어요';
  }

  function button(className, label, html, pressed) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = `icon-btn ${className}`;
    btn.setAttribute('aria-label', label);
    if (pressed !== undefined) btn.setAttribute('aria-pressed', String(pressed));
    btn.innerHTML = html;
    return btn;
  }

  function renderItem(todo, editing, readOnly) {
    const li = document.createElement('li');
    li.className = 'todo-item';
    li.classList.toggle('done', todo.done);
    li.classList.toggle('important', todo.important);
    li.dataset.id = todo.id;

    const check = document.createElement('input');
    check.type = 'checkbox';
    check.className = 'todo-check';
    check.checked = todo.done;
    check.setAttribute('aria-label', `"${todo.text}" 완료`);

    const star = button('star', '중요 표시', ICONS.star(todo.important), todo.important);
    star.disabled = readOnly;

    let body;
    if (editing) {
      body = document.createElement('input');
      body.type = 'text';
      body.className = 'todo-edit';
      body.value = todo.text;
      body.maxLength = TD.store.MAX_LENGTH;
      body.setAttribute('aria-label', '할일 수정');
    } else {
      body = document.createElement('span');
      body.className = 'todo-text';
      body.textContent = todo.text;
      if (!readOnly) body.title = '더블클릭하여 수정';
    }

    li.append(check, star, body);
    if (!readOnly) {
      li.append(
        button('edit', `"${todo.text}" 수정`, ICONS.edit),
        button('delete', `"${todo.text}" 삭제`, ICONS.trash)
      );
    }
    return li;
  }

  function render(ui) {
    const store = TD.store;
    const stats = store.getStats();
    const filter = store.getFilter();
    const visible = store.getVisible();
    const today = TD.date.today();
    const viewDate = store.getViewDate();
    const isToday = viewDate === today;
    const readOnly = store.isReadOnly();
    const rel = TD.date.relative(viewDate);

    $('view-date-text').textContent = TD.date.format(viewDate);
    $('view-date-badge').textContent = rel;
    $('view-date-badge').hidden = !rel;
    $('go-today').hidden = isToday;

    const pct = stats.total ? Math.round((stats.done / stats.total) * 100) : 0;
    $('progress-fill').style.width = `${pct}%`;
    $('progress-bar').setAttribute('aria-valuenow', String(pct));
    $('progress-text').textContent = `${stats.done} / ${stats.total} 임무 완료`;
    $('celebrate').hidden = !(stats.total > 0 && stats.remaining === 0);
    $('celebrate').textContent = isToday
      ? '🛸 오늘의 임무를 모두 완수했어요!'
      : '🛸 이 날의 임무를 모두 완수했어요!';
    document.body.dataset.mood = stats.total > 0 && stats.remaining === 0 ? 'happy' : 'idle';

    $('storage-notice').hidden = store.isPersistent();
    $('readonly-notice').hidden = !readOnly;
    $('todo-form').hidden = readOnly;
    $('todo-input').placeholder = rel && !isToday
      ? `${rel}의 임무를 입력하세요...`
      : '오늘의 임무를 입력하세요...';

    const carry = isToday ? store.getCarryOver() : [];
    $('carry-banner').hidden = carry.length === 0;
    $('carry-text').textContent = `지난날 못 끝낸 임무 ${carry.length}개를 오늘로 가져올까요?`;

    document.querySelectorAll('.filter').forEach((btn) => {
      btn.setAttribute('aria-pressed', String(btn.dataset.filter === filter));
    });

    // replaceChildren은 구형 모바일 브라우저(Safari 14 미만 등)에 없어서 사용하지 않는다
    const list = $('todo-list');
    list.textContent = '';
    visible.forEach((t) => {
      list.appendChild(renderItem(t, !readOnly && t.id === ui.editingId, readOnly));
    });

    const empty = $('empty-state');
    empty.hidden = visible.length > 0;
    $('empty-text').textContent = stats.total === 0 ? emptyDayText(viewDate, today) : EMPTY[filter];

    $('footer').hidden = stats.total === 0;
    $('remaining').textContent = readOnly
      ? `못 끝낸 임무 ${stats.remaining}개`
      : `남은 임무 ${stats.remaining}개`;
    $('clear-done').hidden = readOnly;
    $('clear-done').disabled = stats.done === 0;
  }

  TD.render = render;
})(window.TD = window.TD || {});
