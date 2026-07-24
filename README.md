# aiogram Dialog Manager

A library for building structured, stateful dialog flows in [aiogram 3](https://docs.aiogram.dev/) Telegram bots.

## Features

- **Prototype-based design** — define reusable message, menu, and button blueprints via abstract classes
- **Stateful dialogs** — each dialog instance maintains a conversation history as a branching tree with data snapshots
- **Automatic middleware** — `DialogManager` injects the active dialog, button, menu, and message directly into your handlers
- **13 message types** — text, photo, document, video, audio, animation, voice, sticker, video note, location, contact, poll, and media group
- **Standalone keyboards** — create inline keyboards independent of any dialog and attach them to arbitrary messages
- **Pluggable storage** — `MemoryStorage` (in-process) and `RedisStorage` out of the box; custom backends via `BaseStorage`
- **TTL support** — automatic expiry of dialogs and standalone menus in storage
- **Typed filters** — `DialogFilter`, `ButtonFilter`, `MenuFilter`, `MessageFilter`, `DialogAccessFilter` for precise handler routing
- **Declarative dialog specs** — describe windows, texts and menus as a JSON-serializable model or via the Python builder instead of writing prototype classes; see [Declarative dialog specs](#declarative-dialog-specs)

## Installation

```bash
pip install aiogram_dialog_manager
```

## Quick Start

### 1 — Define prototypes

```python
from aiogram_dialog_manager.prototype import DialogPrototype, ButtonPrototype, MenuPrototype
from aiogram_dialog_manager.prototype.message import TextMessagePrototype
from aiogram_dialog_manager.prototype.base import TextContent
from aiogram_dialog_manager.instance import ButtonInstance


class GreetButton(ButtonPrototype, type_name="greet_button"):
    async def get_state(self, dialog, context) -> str:
        return "👋 Say hello"


class MainMenu(MenuPrototype, type_name="main_menu"):
    _greet = GreetButton()

    async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
        return [[await self._greet.get_instance(dialog, context)]]


class WelcomeMessage(TextMessagePrototype, type_name="welcome"):
    _menu = MainMenu()

    async def get_text_content(self, dialog, context) -> TextContent:
        name = dialog.data.get("user_name", "stranger")
        return TextContent(text=f"Hello, {name}! Choose an action:")

    async def get_menu(self, dialog, context):
        return await self._menu.get_instance(dialog, context)


class MyDialog(DialogPrototype, type_name="my_dialog"):
    welcome = WelcomeMessage()
```

### 2 — Set up `DialogManager`

```python
from aiogram import Bot, Dispatcher
from aiogram_dialog_manager import DialogManager
from aiogram_dialog_manager.storage import MemoryStorage

bot = Bot(token="YOUR_TOKEN")
dp = Dispatcher()

storage = MemoryStorage()
manager = DialogManager(storage)
manager.setup(dp)          # registers middleware on all supported event types
```

### 3 — Start a dialog in a handler

```python
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog_manager import DialogManager
from aiogram_dialog_manager.instance import MessageTarget

dialog_proto = MyDialog()

@dp.message(Command("start"))
async def start(message: Message, dialog_manager: DialogManager):
    op = await dialog_manager.create_dialog(
        dialog_proto,
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        bot=message.bot,
        context={"user_name": message.from_user.first_name},
    )
    await dialog_manager.set_active_dialog(op)
    target = MessageTarget.from_message(message)
    await op.send_message(dialog_proto.welcome, target)
```

> `DialogManager` auto-saves the dialog after every handler call, so you do not need to call `save()` manually inside handlers.

### 4 — React to button clicks

```python
from aiogram.types import CallbackQuery
from aiogram_dialog_manager import DialogOperator, ButtonFilter
from aiogram_dialog_manager.instance import ButtonInstance, MessageTarget

greet_btn = GreetButton()

@dp.callback_query(ButtonFilter(greet_btn))
async def on_greet(
    callback: CallbackQuery,
    dialog: DialogOperator,
    button: ButtonInstance,
):
    await callback.answer()
    target = MessageTarget(chat_id=callback.message.chat.id)
    await dialog.send_message(
        dialog_proto.welcome,
        target,
        context={"user_name": "World"},
    )
```

---

## Core Concepts

### Prototypes vs Instances

| Prototype | Instance |
|-----------|----------|
| Stateless blueprint — subclass and override | Live object created at runtime |
| `ButtonPrototype` → `ButtonInstance` | Created via `prototype.get_instance(dialog, context)` |
| `MenuPrototype` → `MenuInstance` | Created via `prototype.get_instance(dialog, context)` |
| `DialogPrototype` → `DialogInstance` | Created via `DialogManager.create_dialog()` |
| `TextMessagePrototype` → `BotMessageInstance` | Created by `DialogOperator` internally |

Each prototype class registers itself by name at definition time using the `type_name=` keyword argument:

```python
class MyButton(ButtonPrototype, type_name="my_button"):
    ...
```

Names must be unique within each prototype base class — reusing a name raises `ValueError` at import time.

### `DialogOperator`

The object injected into handlers as `dialog`. Provides:

| Method | Description |
|--------|-------------|
| `send_message(proto, target)` | Send a text message |
| `send_photo / send_video / ...` | Send media (13 types total) |
| `reply_to_message(proto, reply_to)` | Send a reply |
| `edit_message(record, proto)` | Edit text or caption |
| `edit_message_media(record, proto)` | Edit media file |
| `edit_reply_markup(record, menu_proto)` | Replace inline keyboard with a new one |
| `delete_reply_markup(record)` | Remove the inline keyboard from a message |
| `edit_live_location(record, proto)` | Update live location |
| `delete_message(record, delete_node, delete_messages, preserve_data)` | Delete a Telegram message; optionally also remove its dialog node and descendant messages |
| `delete_all_messages(only_current_branch, delete_nodes, preserve_data)` | Bulk-delete Telegram messages; optionally also remove dialog nodes |
| `delete_node(node_id, delete_messages, preserve_data)` | Remove a dialog node and all its descendants; optionally delete their Telegram messages |
| `append_user_message(message)` | Manually track an incoming user message |
| `append_bot_message(record)` | Manually add a bot message record to the dialog tree |
| `rollback(index, delete_nodes, delete_messages, preserve_data)` | Roll dialog state back to position `index`; optionally delete rolled-back nodes and their Telegram messages |
| `switch_node(node_id)` | Jump to any node in the dialog tree |
| `data` | Current dialog data dict (read/write) |
| `temp` | Per-request scratch dict (not persisted) |

### `DialogManager`

| Method | Description |
|--------|-------------|
| `create_dialog(proto, user_id, chat_id, bot, context, ttl)` | Create a new dialog instance |
| `set_active_dialog(dialog, user_id, chat_id)` | Mark a dialog as active for its user+chat |
| `get_active_dialog(user_id, chat_id, bot)` | Fetch the active dialog for a user+chat |
| `get_dialog(dialog_id, bot)` | Fetch any dialog by ID |
| `save(operator, ttl)` | Persist dialog state and refresh button index |
| `delete(operator)` | Delete a dialog and all its button index entries |
| `save_standalone_menu(instance, ttl)` | Register a menu instance in storage and index its buttons |
| `delete_standalone_menu(menu)` | Delete a standalone menu by instance or ID and remove its button index entries |
| `cleanup_orphaned()` | Delete dialogs with no active pointer and standalone menus with no live buttons; returns count |
| `set_user_message_filter(dialog, filter_fn)` | Register a per-dialog-type message filter |
| `set_dead_button_handler(handler)` | Register a callback for button presses that resolve to nothing |
| `setup(dp)` | Register middleware on all supported event types |

### Active dialog

Each user+chat pair has at most one **active dialog** — the dialog injected into `Message` handlers via middleware. Set it explicitly after creation:

```python
op = await manager.create_dialog(proto, user_id, chat_id, bot)
await manager.set_active_dialog(op)
```

You can also set the active dialog by raw values if you already know the IDs and do not need to load the full operator:

```python
await manager.set_active_dialog(dialog_id, user_id=user_id, chat_id=chat_id)
```

`user_id` and `chat_id` are required when passing a string dialog ID.

Creating a new dialog does not automatically replace the active one. Call `set_active_dialog` whenever you want to switch.

### Deleting a dialog

```python
await manager.delete(dialog)
```

Removes the dialog, its `active:*` pointer (if it was active), and all button index entries. Safe to call from inside a handler.

### Standalone keyboards

Keyboards that exist independently of any dialog — useful for persistent menus, welcome screens, or any message not part of a dialog flow.

```python
menu_proto = MainMenu()

# create instance yourself, then register it in storage
instance = await menu_proto.get_instance(None, context)
await manager.save_standalone_menu(instance)

markup = instance.get_markup()
await bot.send_message(chat_id, "Choose:", reply_markup=markup)

# update keyboard — create a fresh instance and register it
await manager.delete_standalone_menu(instance)  # or delete_standalone_menu(instance.id)
new_instance = await menu_proto.get_instance(None, new_context)
await manager.save_standalone_menu(new_instance)
await bot.edit_message_reply_markup(chat_id, message_id, reply_markup=new_instance.get_markup())
```

When a standalone button is pressed, the middleware injects `button` and `menu` but `dialog` is `None`.

### Dead button handler

Called when a user presses a button whose dialog or standalone menu no longer exists (expired TTL, deleted, etc.):

```python
from aiogram_dialog_manager import DeadButtonHandler

async def on_dead_button(callback: CallbackQuery):
    await callback.answer("This button is no longer active.", show_alert=True)

manager.set_dead_button_handler(on_dead_button)
```

### Dialog Tree

Each message is stored as a node in a branching tree. Every node snapshots the dialog data before and after processing, enabling rollback and branching. Use `dialog.dialog.build_tree()` to inspect the full history.

Whether messages are saved automatically is controlled by `DialogConfig`, which you override in `DialogPrototype.get_config()`:

```python
from aiogram_dialog_manager.instance import DialogConfig

class MyDialog(DialogPrototype, type_name="my_dialog"):
    async def get_config(self, context) -> DialogConfig:
        return DialogConfig(
            save_bot_message_nodes=True,    # default — send_* auto-appends to tree
            save_user_message_nodes=False,  # default — user messages not auto-appended
        )
```

When auto-saving is off, use `append_user_message` / `append_bot_message` to add messages manually.

**Per-dialog user message filter**

When `save_user_message_nodes=True`, you can additionally filter which messages get saved by registering a `UserMessageFilter` on the manager:

```python
from aiogram_dialog_manager import UserMessageFilter

my_dialog = MyDialog()

# accepts a prototype instance or a plain string type name
manager.set_user_message_filter(
    my_dialog,
    lambda msg: not (msg.text and msg.text.startswith("/")),
)
```

The filter receives the `Message` object and returns `True` to save or `False` to skip. One filter per dialog type; if no filter is registered for a type, all messages are saved.

**Reply-based dialog lookup**

By default the `Message` middleware resolves the dialog only for the dialog owner (via the active dialog pointer). You can optionally enable reply-based lookup so that any user who replies to a message belonging to a dialog receives that dialog in `data["dialog"]`.

Enable it via three flags in `DialogConfig`:

| Flag | Default | Description |
|------|---------|-------------|
| `allow_reply_lookup` | `False` | Master switch — enables reply-based lookup |
| `index_bot_messages` | `False` | Index bot messages so replies to them resolve the dialog |
| `index_user_messages` | `False` | Index user messages so replies to them resolve the dialog |

```python
class MyDialog(DialogPrototype, type_name="my_dialog"):
    async def get_config(self, context) -> DialogConfig:
        return DialogConfig(
            allow_reply_lookup=True,
            index_bot_messages=True,   # reply to any bot message → this dialog
            index_user_messages=False, # user messages not indexed
        )
```

Indexes are built automatically on every `save()` call and cleaned up automatically on `delete()`.

When `operator is None` (the sender has no active dialog) but the incoming message is a reply, the middleware looks up `reply_to_message.message_id` in the index. If found, the owning dialog is returned as `data["dialog"]`. If the sender already has an active dialog, that takes priority and the reply index is not consulted.

**Saving messages from non-owner users**

When reply lookup is enabled you may also want to record the replies of non-owner users as nodes in the dialog tree. Set `save_foreign_user_messages=True` — it works only in combination with `save_user_message_nodes=True`:

```python
class MyDialog(DialogPrototype, type_name="my_dialog"):
    async def get_config(self, context) -> DialogConfig:
        return DialogConfig(
            save_user_message_nodes=True,
            allow_reply_lookup=True,
            index_bot_messages=True,
            save_foreign_user_messages=True,  # save replies from any user
        )
```

Without this flag only the dialog owner's messages are appended to the tree even when another user's reply resolves the dialog.

### Node deletion

Dialog nodes can be removed from the tree independently of Telegram messages, or together with them. All deletion methods accept an optional `delete_messages` flag that controls whether the corresponding Telegram messages are deleted via the Bot API.

**Delete a single node and its entire subtree:**

```python
# Remove from dialog tree only (Telegram messages are kept)
await op.delete_node(node_id)

# Remove from dialog tree AND delete Telegram messages
await op.delete_node(node_id, delete_messages=True)
```

When a node is deleted, all its descendants are deleted too. If the current node is inside the deleted subtree, `current_id` is moved to the parent of the deleted subtree root.

**Delete a Telegram message and optionally its node:**

```python
# Delete only the Telegram message (default behaviour, unchanged)
await op.delete_message(record)

# Delete the Telegram message and remove the node from the tree
await op.delete_message(record, delete_node=True)

# Delete the Telegram message, remove the node, and also delete descendant messages
await op.delete_message(record, delete_node=True, delete_messages=True)
```

**Bulk delete with node cleanup:**

```python
# Delete all messages and clear the entire dialog tree
await op.delete_all_messages(delete_nodes=True)

# Delete messages on the current branch only and remove those nodes
await op.delete_all_messages(only_current_branch=True, delete_nodes=True)
```

When `only_current_branch=True`, nodes on the current path are removed. Any sibling branches that branch off from the deleted path are re-parented to the virtual root and preserved.

**Rollback with node deletion:**

```python
# Standard rollback — nodes are kept in the tree (history is preserved)
await op.rollback(1)

# Rollback and discard the rolled-back nodes from the tree
await op.rollback(1, delete_nodes=True)

# Rollback, discard nodes, and delete their Telegram messages
await op.rollback(1, delete_nodes=True, delete_messages=True)
```

**Preserving dialog data during deletion**

By default, all deletion and rollback operations restore `dialog.data` to the snapshot that was active before the deleted/rolled-back nodes were created. Pass `preserve_data=True` to keep the current value of `dialog.data` unchanged:

```python
# Rollback cursor position but keep current data
await op.rollback(1, preserve_data=True)

# Remove a node without restoring an older data snapshot
await op.delete_node(node_id, preserve_data=True)

# Bulk delete with node cleanup, keeping current data
await op.delete_all_messages(delete_nodes=True, preserve_data=True)
await op.delete_message(record, delete_node=True, preserve_data=True)
```

This is useful when you have already updated `dialog.data` with information that should survive the structural cleanup (e.g. clearing old message nodes after a multi-step form while keeping the collected form values).

### Storage

```python
from aiogram_dialog_manager.storage import MemoryStorage, RedisStorage
from redis.asyncio import Redis

# In-process (development / single instance)
storage = MemoryStorage()

# Redis (production / multi-instance)
redis = Redis.from_url("redis://localhost")
storage = RedisStorage(redis)
```

Custom backend: subclass `aiogram_dialog_manager.storage.BaseStorage` and implement all abstract methods.

**TTL**

Configure default TTL (in seconds) for dialogs and standalone menus:

```python
manager = DialogManager(
    storage,
    dialog_ttl=86400,           # dialogs expire after 24 h of inactivity
    standalone_menu_ttl=604800, # standalone menus expire after 7 days
)
```

TTL is refreshed on every `save()` call for dialogs (and for the `active:*` pointer if the dialog is active). Override per call:

```python
# this dialog has a shorter TTL
op = await manager.create_dialog(proto, user_id, chat_id, bot, ttl=3600)

# this standalone menu never expires
instance = await proto.get_instance(None, context)
await manager.save_standalone_menu(instance, ttl=None)
```

**Cleanup**

Remove stale records that were never explicitly deleted:

```python
deleted = await manager.cleanup_orphaned()
# dialogs with no active pointer → deleted
# standalone menus with no live button entries → deleted
```

Run periodically (e.g. via a scheduled task or cron).

### Filters

All filters work with objects resolved by the middleware.

```python
from aiogram_dialog_manager import (
    DialogFilter,        # match by dialog prototype or name and/or data
    ButtonFilter,        # match by button prototype or name and/or data
    MenuFilter,          # match by menu prototype or name and/or data
    MessageFilter,       # match CallbackQuery by the bot message that contained the button
    EditedMessageFilter, # pass only if the edited message was tracked in the dialog
    DialogAccessFilter,  # pass only if event.from_user.id == dialog.user_id
)

# Examples
DialogFilter(my_dialog_proto)                 # by prototype instance
DialogFilter("my_dialog", step="confirm")     # name + data field
ButtonFilter(my_button_proto)                 # by prototype instance
ButtonFilter("greet_button", color="red")     # by name + data field
MenuFilter(my_menu_proto)                     # by prototype instance
MenuFilter("main_menu")                       # by name
MessageFilter(my_message_proto)               # by prototype instance
MessageFilter(my_message_proto, step="input") # prototype + data field
EditedMessageFilter()                         # any tracked user message was edited
EditedMessageFilter(step="input")             # edited message has matching data
DialogAccessFilter()                          # ownership check
```

### What the middleware injects

#### On `Message`

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Active dialog for this user+chat, or dialog resolved via reply (if `allow_reply_lookup` is enabled), or `None` |
| `dialog_manager` | `DialogManager` | The manager instance |

#### On `EditedMessage`

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Active dialog for this user+chat, or `None` |
| `message_record` | `UserMessageRecord \| None` | The saved record matching the edited message, or `None` if not tracked |
| `dialog_manager` | `DialogManager` | The manager instance |

#### On `CallbackQuery` (button press)

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Dialog that owns the button, or `None` for standalone / not found |
| `button` | `ButtonInstance \| None` | The pressed button |
| `message_record` | `BotMessageRecord \| None` | The bot message that contained the button (dialog buttons only) |
| `menu` | `AnyMenuInstance \| None` | The menu that contained the button |
| `dialog_manager` | `DialogManager` | The manager instance |

#### On `MyChatMember` / `ChatMember`

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Active dialog for the user who triggered the update, or `None` |
| `dialog_manager` | `DialogManager` | The manager instance |

#### On `PollAnswer`

Resolved via the poll index built automatically when a dialog sends a poll via `send_poll`. If the poll was not sent through the dialog framework, `dialog` and `message_record` are `None`.

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Dialog that sent the poll, or `None` |
| `message_record` | `BotMessageRecord \| None` | The bot message record for the poll, or `None` |
| `dialog_manager` | `DialogManager` | The manager instance |

#### On `MessageReaction`

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Active dialog for the reacting user, or `None` (also `None` for anonymous reactions) |
| `message_record` | `AnyMessageRecord \| None` | The dialog message record that was reacted to, or `None` if not tracked |
| `dialog_manager` | `DialogManager` | The manager instance |

### Message Types

All message prototypes live in `aiogram_dialog_manager.prototype.message`:

| Class | Bot API method |
|-------|---------------|
| `TextMessagePrototype` | `sendMessage` |
| `PhotoMessagePrototype` | `sendPhoto` |
| `DocumentMessagePrototype` | `sendDocument` |
| `VideoMessagePrototype` | `sendVideo` |
| `AudioMessagePrototype` | `sendAudio` |
| `AnimationMessagePrototype` | `sendAnimation` |
| `VoiceMessagePrototype` | `sendVoice` |
| `StickerMessagePrototype` | `sendSticker` |
| `VideoNoteMessagePrototype` | `sendVideoNote` |
| `LocationMessagePrototype` | `sendLocation` |
| `ContactMessagePrototype` | `sendContact` |
| `PollMessagePrototype` | `sendPoll` |
| `MediaGroupMessagePrototype` | `sendMediaGroup` |

Media types (`Photo`, `Document`, `Video`, `Audio`, `Animation`) also implement `get_input_media()` for use with `edit_message_media`.

### Menu Types

| Class | Telegram keyboard |
|-------|------------------|
| `MenuInstance` | Inline or Reply keyboard (controlled by `keyboard_type`) |
| `ForceReplyMenuInstance` | `ForceReply` |
| `RemoveKeyboardMenuInstance` | `ReplyKeyboardRemove` |

---

## Declarative dialog specs

An alternative to writing prototype classes: describe a whole dialog — windows, texts, menus, buttons — as data. The model is **fully serializable** (store it in a DB or file, load it at runtime) and compiles into regular prototypes, so the entire existing runtime (instances, storage, history, filters, `send_*`) works unchanged.

The spec covers **layout only**. Behavior stays in ordinary aiogram handlers with filters: a handler shrinks to "update `dialog.data` → re-render the window", while all message/menu assembly lives on the model.

### Quick example

```python
from aiogram_dialog_manager.spec import compile_dialog
from aiogram_dialog_manager.spec import builder as b

spec = b.dialog(
    "settings",
    windows={
        "main": b.window(
            b.text("Hello, ", b.data_.name | "stranger", "!"),
            menu=b.menu(
                b.row(b.button("save", b.t("save_btn"))),
                # one button per player, each carrying its own payload
                b.foreach(b.data_.players, b.row(
                    b.button("player", b.item_.name, data={"player_id": b.item_.id}),
                )),
                b.if_(b.data_.is_admin, b.row(b.button("admin", "Admin panel"))),
            ),
        ),
    },
)

dialog_model = compile_dialog(spec, register=True)
```

The compiled model exposes **typed handles** — a typo fails at startup, not at runtime:

```python
@dp.callback_query(ButtonFilter(dialog_model.windows.main.buttons.player))
async def on_player(callback, dialog: DialogOperator, button: ButtonInstance):
    player_id = button.data["player_id"]   # payload evaluated per button at render time
    ...
    await dialog.send_message(dialog_model.windows.main.message, target)
```

Prototypes get deterministic names in the shared registries — `settings:main` (message), `settings:main:menu`, `settings:main:save` (buttons) — so string-based filters (`ButtonFilter("settings:main:save")`) and storage round-trips keep working across restarts. Re-compiling and re-registering the same dialog **replaces** the spec entries (hot-reload, loading from a DB); colliding with a Python prototype class still raises.

### Canonical JSON form

The builder is a thin layer: everything compiles to a JSON-compatible dict (`spec.to_dict()` / `DialogSpec.from_dict(...)`), with `version` at the root:

```jsonc
{
  "version": 1,
  "name": "settings",
  "windows": {
    "main": {
      "content": {"type": "text", "text": ["Hello, ", {"type": "path", "path": "data.name"}]},
      "menu": {"rows": [[{"type": "button", "name": "save", "text": "Save"}]]}
    }
  }
}
```

### Expressions

Any leaf field (button text, url, caption, payload values, `chunk` size, …) accepts a literal **or** an expression node. Expressions are JSON trees; the builder writes them with plain Python operators:

```python
b.data_.page > 0                    # {"type": "op", "op": ">", "args": [{"type": "path", ...}, 0]}
b.data_.name | "anonymous"          # or with Python semantics (returns operand)
b.fn("len", b.data_.players)        # function call from the open registry
b.provider("top_players", limit=5)  # escape hatch: named Python provider (may hit DB/network)
b.t("welcome_text")                 # translatable string (see i18n below)
b.format_(b.t("greeting"), name=b.data_.name)  # fill {name} in a (translated) template
```

- Namespaces are explicit: `data.*` (persistent `dialog.data`), `ctx.*` (render context), `item`/`index` inside `foreach`.
- A missing path evaluates to `null`; type errors and division by zero raise (a silent `null` would hide script bugs).
- Starter functions: `len, str, int, float, bool, round, abs, min, max, sum, join, split, upper, lower, strip, format, default, range, sorted, keys, values` — register your own pure functions in a `FunctionRegistry`.

### Structural constructs

| Construct | Purpose |
|-----------|---------|
| `foreach` | multiply a node over a list (`item`/`index` in scope); parameterizes button payloads |
| `if` / `else` | conditional inclusion of a button, row, text fragment or menu part |
| `chunk` | lay out a flat button list into rows of N |
| `slice` | list slice with expression bounds; with `foreach` covers pagination |
| `def` / `ref` | named reusable fragments inside the model (a shared "Back" button, common footer) |
| `provider` | named Python provider from the registry — the only door to external data |
| `t` | translatable string |
| `format` | fill `{name}`/`{0}` placeholders of a template (usually a `t` node) via `str.format` |
| `use_button` / `use_menu` / `use_message` | plug an existing registered Python prototype into the spec (see below) |

Rows that render empty are dropped; a menu whose rows are all empty produces no keyboard at all.

**Pagination widget** — a builder-level macro that expands into `slice` + `foreach` + a nav row (the serialized model contains only core primitives):

```python
menu = b.menu(*b.paginator(
    "pl",
    over=b.data_.players,
    page=b.data_.page,
    item=b.button("player", b.item_.name, data={"pid": b.item_.id}),
    page_size=5, per_row=1,
))
# nav buttons are named pl_prev / pl_next and carry {"page": <target>} in payload
```

### Reusing Python prototypes: `use`

Existing registered prototypes plug into spec dialogs by `type_name` — the standard way to share cancel/skip buttons (and their handlers) across spec and Python dialogs:

```python
b.window(
    b.text("Step 1: enter a name"),
    menu=b.menu(
        b.row(b.use_button("cancel_btn")),                 # existing ButtonPrototype
        b.row(b.use_button("skip_btn", context={"step": 1})),
    ),
)

b.window(b.text("…"), menu=b.use_menu("shared_menu"))       # existing MenuPrototype
b.window(b.use_message("error_msg"))                        # existing message prototype
```

- The used prototype **keeps its own `type_name`** — existing `ButtonFilter`/handler wiring works without changes.
- `context` values are expressions merged over the render context, so `foreach` can parameterize a used button per item.
- **Escape hatch — catching a fresh inline button with a short-name filter.** An inline `b.button` is namespaced `{dialog}:{window}:{name}`, so a bare-name `ButtonFilter("save")` won't catch it (this is why handler-backed buttons normally go through `use_button`). Pass `b.button("save", "Save", type_name="save")` to declare a fresh button inline *and* have it caught by an existing short-name handler — the deliberate opt-out of the namespacing.
- All three (`use_button`/`use_menu`/`use_message`) resolve **lazily at render time** through the dialog's resolver (see below): the target may be registered after the spec is compiled, and a compiled dialog resolves nothing until used — so it caches and re-runs cheaply.
- A `use_message` window declares neither `menu` nor `data`: the target prototype controls both (compilation fails otherwise).

### Swapping resolution and interpreters

Two extension seams on `compile_dialog`, both symmetric across the primitives:

**`resolver=`** — how every `use` reference (`button`/`menu`/`message`) resolves a registered prototype by name, at render time. Subclass `SpecResolver` to gate access, scope a registry, or log; the default is a plain registry lookup. This is the single choke point for access control over untrusted scripts:

```python
from aiogram_dialog_manager.spec import SpecResolver

class AccessResolver(SpecResolver):
    def __init__(self, author, rights):
        self._author, self._rights = author, rights

    def resolve(self, base_cls, name, scope):
        if not self._rights.may_use(self._author, base_cls, name):
            raise AccessDenied(name)          # author fixed per script; acting user via scope
        return super().resolve(base_cls, name, scope)

compile_dialog(spec, resolver=AccessResolver(author, rights))   # compile once, resolve per render
```

**`prototypes=`** — a `SpecPrototypeFactory` builds the four spec interpreters (dialog / message / menu / button). Override a hook to swap the interpreter of a primitive across the whole dialog:

```python
from aiogram_dialog_manager.spec import SpecPrototypeFactory

class MyFactory(SpecPrototypeFactory):
    def create_button(self, name, spec, runtime, window_name):
        return LoggingButtonPrototype(name, spec, runtime, window_name)

compile_dialog(spec, prototypes=MyFactory())
```

### Window data and the "window name is the state" pattern

A window can carry default message data (values are expressions); the render context is merged on top:

```python
spec = b.dialog(
    "wizard",
    window_name_key="state",     # every window stamps its own name into message data under this key
    windows={
        "enter_name": b.window(b.text("Name?"), data={"attempts": 0}),
        "enter_age":  b.window(b.text("Age?")),
    },
)
```

Message data assembles in three layers, later ones winning: `{window_name_key: window_name}` → window `data` → render context. In wizard-style dialogs this removes the boilerplate of passing `{"state": ...}` through every `send_message` — `MessageFilter`/`EditedMessageFilter` route on the stamped window name directly.

The **dialog itself** carries the same, symmetric with windows: `b.dialog(..., data={...}, config={...})`. `data` seeds the initial `dialog.data` (render context merged on top); `config` evaluates into `DialogConfig` (its keys are validated against the config schema at build time). Both are expression maps, interpreted by the dialog prototype's `get_data`/`get_config`.

### Standalone messages and legacy names

Some messages are not their own dialog — they are rendered by `edit_message` *into* another dialog (e.g. a repost/topic card). `compile_message(...)` compiles one such message directly, without wrapping it in a throwaway one-window dialog:

```python
from aiogram_dialog_manager.spec import compile_message

topic = compile_message(
    b.text("Card: ", b.data_.title, send_params={"parse_mode": "HTML"}),
    name="game:topic",                                   # the message's exact type_name
    menu=b.menu(b.row(b.button("open", "Open", type_name="open_card"))),
    register=True,                                        # register message/menu/buttons under those names
)
```

- The message prototype's `type_name` is exactly `name` — **author-controlled**. Its menu/button names derive from it (`{name}:menu`, `{name}:open`). `content`/`menu`/`data`/`defs` mirror a window; the rest of the keyword arguments mirror `compile_dialog` (`functions`/`providers`/`translator`/`prototypes`/`resolver`/`register`).
- **Preserving a legacy name.** Inside a dialog, a window's message name is `{dialog}:{window}` by default. To keep an old prototype's exact `type_name` — so an in-flight persisted non-dialog message still resolves by its old name across a deploy — set `b.window(..., message_name="legacy_topic")` (DSL: `window w (message_name="legacy_topic") { … }`). Not allowed together with `use_message` (the target owns its name).

### Localization

`b.t("msgid")` marks a translatable string. Pass a `translator(msgid, locale) -> str` hook to `compile_dialog`; the locale comes from the render context (`ctx.locale`). Without a translator the msgid is returned as is — no translation library is bundled, only the hook.

```python
compile_dialog(spec, translator=my_gettext_hook)
```

`b.t(...)` returns the msgid verbatim; to fill placeholders in a translated template wrap it in `format`: `b.format_(b.t("greeting"), name=b.data_.name)` fills `{name}` (and positional `{0}`) via `str.format` after the msgid is translated. Fragment lists (`b.text(b.t("hi"), " ", b.data_.name)`) and DSL string holes (`"{data.name}"`) cover the concatenation case; `format` covers the single-template case.

**Extracting msgids for gettext.** `pybabel` does not pick up `b.t(...)` calls by default — add `-k t` on the command line (keywords cannot be set per-section in a mapping file: the `python` extractor ignores a `keywords` option there):

```bash
pybabel extract -F mapping.cfg -k t -o messages.pot src/
```

For **serialized models** (JSON files, DB dumps) the keyword mechanism cannot see `{"type": "t"}` nodes, so the library ships a Babel extractor (entry point `aiogram_dialog_spec`). Wire it up in the mapping file:

```ini
[python: **.py]

[aiogram_dialog_spec: dialogs/**.json]
```

For models stored elsewhere (a DB), `iter_translation_keys` yields every msgid of a model or its dict form:

```python
from aiogram_dialog_manager.spec import iter_translation_keys

for msgid in iter_translation_keys(spec):   # DialogSpec or its to_dict() form
    ...
```

### Textual DSL

For dialogs authored as plain text — stored in a `.dlg` file, a text field, or a DB column — a compact syntax compiles into the exact same `DialogSpec`. It needs no extra runtime dependency (the lexer/parser are pre-generated and shipped):

```python
from aiogram_dialog_manager.spec.text import parse_dialog_text
from aiogram_dialog_manager.spec import compile_dialog

spec = parse_dialog_text(open("create_game.dlg").read())   # -> DialogSpec
compiled = compile_dialog(spec, register=True)             # compiles like any other spec
```

Braces `{}` mark nested structure (not indentation — robust to reflowed text/DB storage). Comments: `// line` and `/* block */`.

```
dialog create_game (window_name_key="state", data=(step=0), config=(allow_reply_lookup=true)) {
  defs {
    back: button back (text=t("btn_back"))
    footer: row [ ref back, button help (text="?") ]
  }

  window title_prompt (data=(attempts=0)) {
    text: "Hello, {data.name}!"
    menu (keyboard_type="inline") {
      row [ button save (text=t("save"), data=(id=item.id)), button("cancel_btn") ]
      foreach player, i in data.players {
        row [ button pick (text="{player.name} #{i}", data=(pid=player.0)) ]
      }
      if data.page > 0 {
        row [ button prev (text="«", data=(p=data.page - 1)) ]
      } else {
        ref footer
      }
      chunk 2 { foreach x in data.items { button b (text=x.name) } }
    }
  }

  window album {
    media_group {
      foreach ph in data.photos { photo ph.file_id caption: "{ph.title}" has_spoiler: true }
    }
  }
}
```

**One shape for the five declarations.** `dialog`, `window`, `menu`, `message`, `button` all read `<keyword> <name>? (config)? { children }`:

- `( config )` — a flat, order-free map of parameters (`key = expr`).
- `{ children }` — nested nodes (content, menu, rows, …). A **leaf** has no children and no braces, so a button is all config: `button back (text=…, data=(…), inline=(…), common=(…), type_name=…)` — `type_name` opts a fresh inline button out of `{dialog}:{window}:{name}` namespacing so a short-name `ButtonFilter` catches it.
- The name is **optional** — omit it and a deterministic `#N` marker name is synthesized. Name anything you reference from the DSL or wire from Python (`ButtonFilter`, window `state`).
- `dialog`/`window` carry `data=(…)` (default data, expressions); `dialog` also takes `config=(…)` (validated `DialogConfig` fields) and `window_name_key=…`. A `window` can pin its message's `type_name` with `message_name="…"` (preserve a legacy name).

`row`, `foreach`, `if`, `chunk`, `slice`, `ref` and media items are **not** declarations and keep their own syntax (`row [ … ]`, `foreach x in …`).

**Content.** A window's content is either inline fields (sugar for an anonymous message) or an explicit `message { … }` / `message("proto")` — never both. Fields: `text:` · `photo:` (+ `caption`, `has_spoiler`, `show_caption_above_media`) · `document:` (+ `caption`, `disable_content_type_detection`); or `media_group { … }` with positional items `photo <expr> [caption: …] [has_spoiler: …]` (`photo`/`video`/`document`/`audio`), spliced by `foreach`/`if`.

**Send parameters.** How a message is *sent* — `parse_mode`, `link_preview_options`, `disable_notification`, `protect_content`, … — lives in `send_params=(…)`, an order-free map of expressions surfaced through the prototype's `get_send_params` (validated against `SendParams` at render time). For inline content it goes on the window: `window w (send_params=(parse_mode="HTML")) { text: "<b>hi</b>" }`; for an explicit block it goes on the message: `message (send_params=(disable_notification=true)) { text: … }`. In the builder it is a keyword on each content helper: `b.text("<b>hi</b>", send_params={"parse_mode": "HTML"})`. Because the values are expressions, formatting can be dynamic and travels with a serialized/runtime-authored dialog — no Python send-site required.

**Menu, rows, structural.** `menu (keyboard_type="reply", reply_parameters=(…)) { <rows/structural> }` (or `menu("shared")`); `row [ <buttons/refs/structural> ]` (comma-separated); `if <expr> { … } else { … }`; `foreach <alias>[, <index>] in <expr> { … }` (`item`/`index` stay bound; aliases let a nested `foreach` reach the outer element); `chunk <expr> { … }`.

**Expressions & strings.** Operators `< > <= >= == != + - * / % and or not in "not in"`, unary `-`/`not`, grouping `( … )`, standard precedence. Paths `data.x` / `item.0`, calls `join(data.tags, ", ")`, list `[ … ]`, inline map `( k=v, … )`. Registry forms: `t("msgid")`, `provider("name", k=v)`, `ref name` / `ref("name")`, `slice(over, start, stop)`, and prototype refs `button("name")` / `menu("name")` / `message("name")`.

- **Quotes = a string literal; a bare name = a reference.** `"…"`/`'…'` are equivalent; `{ expr }` interpolates inside a string, `{{`/`}}` are literal braces (use the other quote style inside a hole).
- Reuse mirrors the builder: `X("name")` references the **same** registered prototype; `defs { name: <fragment> }` + `ref name` expands a **fresh** fragment at each site.

**Which node kinds the DSL exposes.** The grammar covers every built-in node kind:

| Category | DSL syntax | Node |
|----------|-----------|------|
| paths | `data.x`, `item.0`, bare names | `path` |
| operators | `a + b`, `x and y`, `not z`, … | `op` |
| function call | `join(data.tags, ", ")` | `call` |
| translation | `t("msgid")` | `t` |
| format | `node("format", template=t("g"), kwargs=(name=data.name))` | `format` |
| provider | `provider("name", k=v)` | `provider` |
| fresh reuse | `ref name` / `ref("name")` | `ref` |
| slice | `slice(over, start, stop)` | `slice` |
| list / map | `[ … ]` / `( k=v, … )` | list / dict value |
| structure | `row [ … ]`, `if/else`, `foreach`, `chunk` | `row`/`if`/`foreach`/`chunk` |
| content | `text:` / `photo:` / `document:` / `media_group { … }` | content specs, `media_item` |
| declarations | `dialog`/`window`/`menu`/`message`/`button` | the five prototype nodes |
| shared reuse | `button("n")` / `menu("n")` / `message("n")` | `use_button`/`use_menu`/`use_message` |
| object w/ `type` key | `escape(k=v, …)` | `escape` |
| any node by name | `node("type_name", k=v, …)` | any registered node |

**The generic escape hatch.** `node("type_name", field=expr, …)` builds *any* registered node kind by name — the way to reach node kinds without dedicated sugar from the text DSL: your **own custom node kinds**, or `literal` for fully-opaque data (`node("literal", value=…)`). It is deliberately verbose (positional `type` first, then `key=value` fields); use the sugared forms above for the common kinds. So nothing is truly out of reach from the DSL — only some kinds need the verbose form.

**Current limits.** Names passed to `button(...)`/`menu(...)`/`message(...)`/`ref(...)`/`t(...)` must be **string literals** (a non-literal argument raises a clear error); general calls take positional args only (`provider` and `send_params=(…)` are the exceptions that take `k=v`).

### Extensibility

Four open registries: message/menu/button prototypes (existing), expression **functions**, **providers**, and **node kinds**.

**Reach for functions/providers first.** If you only need a new computation or a new data source, register a pure function (callable as `fn("name", …)` in the builder and `name(...)` in the DSL) or a provider (`provider("name", …)`). Both work across the builder, JSON, and the text DSL — no new node type required. Write a **custom node** only when you need a new *shape* of expression or structure.

#### How a node is built

The canonical form of a dialog is a JSON dict. The rule is simple: **any dict with a `"type"` key becomes a node; everything else is a literal.** A node is just a pydantic model. Anatomy:

> **Gotcha — a literal dict that contains `"type"`.** The rule is applied recursively, so a payload like `{"type": "premium"}` is taken for a node and fails with `UnknownNodeTypeError` (or, worse, is misread if the string collides with a real node kind). Wrap such data in the `literal` escape-hatch node: `{"type": "literal", "value": {"type": "premium"}}`, or `b.lit({"type": "premium"})` in the builder. Its `value` is returned **verbatim at every depth** — the whole subtree becomes opaque literal data with nothing evaluated inside it (no paths, no nested nodes), so wrap only the minimal part that needs it, not an expression you still want evaluated.
>
> If the container has a `"type"` key **but some values must still be evaluated**, reach for the shallow `escape` node instead — `{"type": "escape", "entries": {"type": "premium", "count": {"type": "path", "path": "data.n"}}}`, or `b.escape({"type": "premium", "count": b.data_.n})`. It escapes **only this one level**: the container is kept as data (the `"type"` key survives), while each value is evaluated normally. `literal` = freeze the whole subtree; `escape` = keep the container, evaluate the values.

```python
from typing import Literal
from aiogram_dialog_manager.spec import EvaluableNode, Value, evaluate_value, node_registry

@node_registry.register                       # 4. register — the `type` default is the key
class CoalesceNode(EvaluableNode):            # 1. EvaluableNode = usable in any expression
    """First non-null option (like SQL COALESCE)."""

    type: Literal["coalesce"] = "coalesce"    # 2. discriminator + registry key (unique string)
    options: list[Value]                      # 3. `Value` fields accept a literal OR a nested node

    async def evaluate(self, scope) -> object:            # called wherever a value is needed
        for option in self.options:
            value = await evaluate_value(option, scope)   # resolve literal-or-node uniformly
            if value is not None:
                return value
        return None
```

The four things to know:

1. **Base class.** `EvaluableNode` has `async evaluate(scope)` and can appear anywhere a value is accepted (button text, payload, `if` condition, …). `SpecNode` is a plain *data* node with no `evaluate` — used for structural declarations (window content kinds subclass it and build a prototype instead).
2. **`type`.** A `Literal["..."]` with a default. That default is both the JSON discriminator and the registry key; it must be unique. `extra="forbid"` — unknown JSON keys are rejected.
3. **Fields.** Annotate a field as **`Value`** if it may hold an expression (a literal *or* a nested node — nested dicts/lists are resolved automatically). Use a plain type (`str`, `int`, `Literal[...]`) for fields that must be static config. Never read a `Value` field directly in `evaluate` — always `await evaluate_value(field, scope)`, since it might be a node.
4. **`evaluate(self, scope)`.** Returns a plain Python value. The `scope` gives you everything: `scope.resolve_path("data.x")` / `scope.context` / `scope.dialog` for data, `scope.runtime` for services (`functions`, `providers`, `translator`, `resolver`), and `scope.child(item=…)` to bind locals for sub-evaluation (how `foreach` exposes `item`/`index`).

Because a node is a pydantic model, it round-trips to/from JSON for free.

**Using a custom node.** In the builder/JSON, drop the dict anywhere a value is accepted or pass the node instance directly. From the **text DSL**, build it with the generic `node("type_name", field=expr, …)` constructor (see [Textual DSL](#textual-dsl)) — so a custom kind is reachable there too, just without dedicated syntax.

```python
# JSON / dict form
{"type": "coalesce", "options": [{"type": "path", "path": "data.nickname"},
                                 {"type": "path", "path": "data.name"},
                                 "anonymous"]}

# builder form — a node instance is a value like any other
b.button("greet", CoalesceNode(options=[b.data_.nickname, b.data_.name, "anonymous"]))
```

**List semantics (for structural nodes).** In a list context — menu rows, text fragments, media items — an `evaluate` may return `OMIT` to drop itself (how `if` without `else` disappears) or `Spliced([...])` to inline several items (how `foreach`/`chunk` expand). Return a normal value for the common one-node-one-value case.

All standard nodes — `path`, `op`, `t`, `foreach`, … — are implemented through this exact mechanism, so your own kinds are first-class. Mixing is free: within one dialog some windows can come from a spec and others from Python prototype classes — both live in the same registries.

Window content types shipped in the first iteration: `text`, `photo`, `document`, `media_group`. The compact textual DSL that compiles into the same model is documented above under [Textual DSL](#textual-dsl).

---

## Project Layout

```
src/aiogram_dialog_manager/
├── __init__.py                 # DialogManager, DialogOperator, filters, storage
├── dialog_manager.py           # DialogManager + middleware
├── dialog_operator.py          # DialogOperator
├── filter/                     # DialogFilter, ButtonFilter, MenuFilter, DialogAccessFilter
├── instance/                   # Runtime objects (ButtonInstance, MenuInstance, …)
├── prototype/                  # Abstract base classes to subclass
│   ├── button.py
│   ├── dialog.py
│   ├── menu.py
│   └── message/                # 13 message prototype classes
├── spec/                       # Declarative dialog specs
│   ├── model.py                # DialogSpec / WindowSpec / MenuSpec (JSON-serializable core)
│   ├── nodes.py                # expression & structural nodes (path, op, if, foreach, …)
│   ├── content.py              # window content kinds (content-kind extension seam)
│   ├── prototypes.py           # the four spec interpreters + SpecPrototypeFactory
│   ├── scope.py                # EvalScope, SpecRuntime, SpecResolver
│   ├── use.py                  # use_button / use_menu / use_message (lazy, via resolver)
│   ├── compile.py              # compile_dialog, typed handles, registration
│   ├── babel.py                # gettext extraction from serialized models
│   ├── builder.py              # Python builder + widgets (paginator)
│   └── text/                   # textual DSL: parse_dialog_text + generated lexer/parser
└── storage/                    # BaseStorage, MemoryStorage, RedisStorage
```

## License

MIT