# Эскиз текстового DSL описания диалогов (фаза 2, без реализации)

Статус: **эскиз для проверки выразимости ядра фазы 1.** Синтаксис не
реализован и может меняться до начала фазы 2; семантика каждой конструкции
уже зафиксирована ядром (см. `dialog_spec_design.md`), эскиз лишь показывает,
что вся она записывается компактным текстом и компилируется в JSON-модель
без расширения ядра.

## 1. Общая форма

Блочная структура с отступами (как YAML, но со своими строковыми
выражениями). Один файл — один диалог.

```
dialog settings

window main:
  text: "Привет, {data.name or 'аноним'}!"
  menu:
    row: [ @save, @notify_toggle ]
    row: [ ref back ]

window notify:
  text: t(notify_text)
  menu:
    row: [ ref back ]
```

## 2. Выражения

Строковые выражения (`data.page > 0`, `len(data.players)`) — часть
текстового DSL: парсер компилирует их в дерево узлов ядра (`op`, `path`,
`call`, ...). Скобки и приоритеты — забота парсера; в дереве структура
задаёт всё сама.

- интерполяция в строках: `"Страница {data.page + 1} из {ceil}"`;
- операторы ядра: `< > <= >= == != + - * / % and or not in not in`;
- литералы: числа, строки, `true/false/null`;
- вызовы функций реестра: `join(data.tags, ", ")`;
- провайдеры: `provider(top_players, limit=10)`;
- переводы: `t(welcome_text)`.

## 3. Кнопки

Объявление кнопки — имя, текст и payload:

```
button save "Сохранить"
button player "{item.name}" (player_id=item.id)
button site "Сайт" url="https://example.com/{data.slug}"
```

`@имя` — ссылка на кнопку, объявленную в этом же окне; `ref имя` — на
фрагмент из `defs`.

## 4. Структурные конструкции

```
menu:
  # условное включение
  if data.is_admin:
    row: [ @admin_panel ]
  else:
    row: [ @request_access ]

  # размножение по списку + раскладка по 2 в ряд
  chunk 2:
    foreach data.players:
      button player "{item.name}" (player_id=item.id)

  # пагинация: slice + foreach + навигационный ряд
  foreach slice(data.players, data.page * 5, (data.page + 1) * 5):
    row: [ button player "{item.name}" (player_id=item.id) ]
  row:
    - if data.page > 0: button pl_prev "«" (page=data.page - 1)
    - if (data.page + 1) * 5 < len(data.players): button pl_next "»" (page=data.page + 1)
```

## 5. Переиспользуемые фрагменты

```
defs:
  back: button back "Назад"
  footer:
    row: [ ref back, button help "Помощь" ]

window any:
  menu:
    ...
    ref footer
```

## 6. Контент окна

```
window photo_example:
  photo: data.cover_file_id
  caption: "Альбом {data.title}"
  spoiler: data.hide_cover

window album:
  media_group:
    foreach data.photos:
      photo item.file_id caption "{item.title}"
```

## 7. Импорт Python-прототипов

Существующие Python-прототипы подключаются lookup'ом по `type_name`
в существующих реестрах (смешивание бесплатно, § 9.1 дизайна):

```
window legacy:
  use message my_python_message_prototype
```

## 8. Проверка выразимости — вывод

Каждая конструкция эскиза 1:1 отображается в примитивы ядра фазы 1
(`path/op/call/t/provider/ref/if/foreach/chunk/slice/row/button/media_item`
и типы контента `text/photo/document/media_group`). Расширений ядра для
текстового DSL не потребовалось — цель эскиза достигнута.

Открытые вопросы фазы 2 (не блокируют ядро):

- точная грамматика интерполяции строк и экранирование `{}`;
- синтаксис объявления `keyboard_type: reply` и reply-параметров;
- диагностика ошибок парсера (позиции, подсказки);
- синтаксис импорта Python-прототипов (`use ...`) и его валидация.
