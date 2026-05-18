# aiogram Dialog Manager

A library for building structured, stateful dialog flows in [aiogram 3](https://docs.aiogram.dev/) Telegram bots.

## Features

- **Prototype-based design** — define reusable message, menu, and button blueprints via abstract classes
- **Stateful dialogs** — each dialog instance maintains a conversation history as a branching tree with data snapshots
- **Automatic middleware** — `DialogManager` injects the active dialog, button, menu, and message directly into your handlers
- **13 message types** — text, photo, document, video, audio, animation, voice, sticker, video note, location, contact, poll, and media group
- **Pluggable storage** — `MemoryStorage` (in-process) and `RedisStorage` out of the box; custom backends via `BaseStorage`
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


class GreetButton(ButtonPrototype, name="greet_button"):
    async def get_state(self, dialog, context) -> str:
        return "👋 Say hello"


class MainMenu(MenuPrototype, name="main_menu"):
    _greet = GreetButton()

    async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
        return [[await self._greet.get_instance(dialog, context)]]


class WelcomeMessage(TextMessagePrototype, name="welcome"):
    _menu = MainMenu()

    async def get_text_content(self, dialog, context) -> TextContent:
        name = dialog.data.get("user_name", "stranger")
        return TextContent(text=f"Hello, {name}! Choose an action:")

    async def get_menu(self, dialog, context):
        return await self._menu.get_instance(dialog, context)


class MyDialog(DialogPrototype, name="my_dialog"):
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
manager.setup(dp)          # registers middleware on message and callback_query
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

Each prototype class registers itself by name at definition time using the `name=` keyword argument:

```python
class MyButton(ButtonPrototype, name="my_button"):
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

### Dialog Tree

Each message is stored as a node in a branching tree. Every node snapshots the dialog data before and after processing, enabling rollback and branching. Use `dialog.dialog.build_tree()` to inspect the full history.

Whether messages are saved automatically is controlled by `DialogConfig`, which you override in `DialogPrototype.get_config()`:

```python
from aiogram_dialog_manager.instance import DialogConfig

class MyDialog(DialogPrototype, name="my_dialog"):
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

#### On `CallbackQuery` (button press)

| Key | Type | Description |
|-----|------|-------------|
| `dialog` | `DialogOperator \| None` | Dialog that owns the button, or `None` if not found in the active branch |
| `button` | `ButtonInstance \| None` | The pressed button |
| `message` | `BotMessageRecord \| None` | The bot message that contained the button |
| `menu` | `AnyMenuInstance \| None` | The menu that contained the button |
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