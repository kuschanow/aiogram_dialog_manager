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
- **Typed filters** — `DialogFilter`, `ButtonFilter`, `MenuFilter`, `DialogAccessFilter` for precise handler routing

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
| `edit_reply_markup(record, menu_proto)` | Edit inline keyboard only |
| `edit_live_location(record, proto)` | Update live location |
| `delete_message(record)` | Delete a single message |
| `delete_all_messages(only_current_branch)` | Bulk delete |
| `append_user_message(message)` | Manually track an incoming user message |
| `append_bot_message(record)` | Manually add a bot message record to the dialog tree |
| `rollback(index)` | Roll dialog state back to position `index` in the history |
| `switch_node(node_id)` | Jump to any node in the dialog tree |
| `data` | Current dialog data dict (read/write) |
| `temp` | Per-request scratch dict (not persisted) |

### `DialogManager`

| Method | Description |
|--------|-------------|
| `create_dialog(proto, user_id, chat_id, bot, context, ttl)` | Create a new dialog instance |
| `set_active_dialog(operator)` | Mark a dialog as active for its user+chat |
| `get_active_dialog(user_id, chat_id, bot)` | Fetch the active dialog for a user+chat |
| `get_dialog(dialog_id, bot)` | Fetch any dialog by ID |
| `save(operator, ttl)` | Persist dialog state and refresh button index |
| `delete(operator)` | Delete a dialog and all its button index entries |
| `save_standalone_menu(instance, ttl)` | Register a menu instance in storage and index its buttons |
| `delete_standalone_menu(menu)` | Delete a standalone menu by instance or ID and remove its button index entries |
| `cleanup_orphaned()` | Delete dialogs with no active pointer and standalone menus with no live buttons; returns count |
| `set_active_dialog(operator)` | Mark a dialog as active for its user+chat |
| `set_user_message_filter(dialog, filter_fn)` | Register a per-dialog-type message filter |
| `set_dead_button_handler(handler)` | Register a callback for button presses that resolve to nothing |
| `setup(dp)` | Register middleware on all supported event types |

### Active dialog

Each user+chat pair has at most one **active dialog** — the dialog injected into `Message` handlers via middleware. Set it explicitly after creation:

```python
op = await manager.create_dialog(proto, user_id, chat_id, bot)
await manager.set_active_dialog(op)
```

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
    async def get_config(self) -> DialogConfig:
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
    DialogFilter,       # match by dialog prototype or name and/or data
    ButtonFilter,       # match by button prototype or name and/or data
    MenuFilter,         # match by menu prototype or name and/or data
    DialogAccessFilter, # pass only if event.from_user.id == dialog.user_id
)

# Examples
DialogFilter(my_dialog_proto)                 # by prototype instance
DialogFilter("my_dialog", step="confirm")     # name + data field
ButtonFilter(my_button_proto)                 # by prototype instance
ButtonFilter("greet_button", color="red")     # by name + data field
MenuFilter(my_menu_proto)                     # by prototype instance
MenuFilter("main_menu")                       # by name
DialogAccessFilter()                          # ownership check
```

### What the middleware injects

#### On `Message`

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Active dialog for this user+chat, or `None` |
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
└── storage/                    # BaseStorage, MemoryStorage, RedisStorage
```

## License

MIT