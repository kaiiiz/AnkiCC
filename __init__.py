# import the main window object (mw) from aqt
from aqt import mw

# import the "show info" tool from utils.py
from aqt.utils import showInfo

from aqt.qt import qconnect

# import all of the Qt GUI library
from aqt.qt import *

from .opencc_python.opencc.opencc import OpenCC

import json


def testFunction() -> None:
    if mw is None:
        return
    # get the number of cards in the current collection, which is stored in
    # the main window
    # cardCount = mw.col.cardCount()
    if mw.col is None:
        return
    if mw.col.db is None:
        return

    # mw.col.decks.all_names_and_ids

    cc = OpenCC("s2t")
    did = mw.col.decks.get_current_id()
    deck = mw.col.decks.get(did)
    if deck is None:
        return
    deck["name"] = cc.convert(deck["name"])
    mw.col.decks.save(deck)
    ids = mw.col.decks.cids(did)
    for id in ids:
        card = mw.col.get_card(id)
        note = card.note()
        note_type = note.note_type()
        if note_type is None:
            return

        for k, v in note_type.items():
            if isinstance(v, str):
                note_type[k] = cc.convert(v)
            elif isinstance(v, dict) or isinstance(v, list):
                note_type[k] = json.loads(cc.convert(json.dumps(v, ensure_ascii=False)))
                showInfo(f"{note_type[k]}")

        mw.col.models.save(note_type)

        # showInfo(f"notetype: {note_type.keys()}")
        showInfo(f"notetype: {note.note_type()}")
        #
        # for k, v in note.items():
        #     # converted_k = cc.convert(k)
        #     converted_v = cc.convert(v)
        #     note[k] = converted_v
        #
        # mw.col.update_note(note)
        # # showInfo(f"card: {dir(card)}")
        # showInfo(f"card: {note.keys()}")
        # showInfo(f"card: {note.values()}")
        #
        break
    # showInfo("Card counttt: %d" % (len(ids)))
    # show a message box
    # showInfo("Card count: %d" % cardCount)


# create a new menu item, "test"
action = QAction("test", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, testFunction)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
