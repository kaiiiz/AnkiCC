# import the main window object (mw) from aqt
from PyQt6 import QtWidgets
from aqt import mw
from aqt.forms.main import QtCore

# import the "show info" tool from utils.py
from aqt.utils import showInfo

from aqt.qt import qconnect

# import all of the Qt GUI library
from aqt.qt import *

from .opencc_python.opencc.opencc import OpenCC

import json
import typing
from typing import Sequence

from anki import decks_pb2

DeckNameId = decks_pb2.DeckNameId


class Menu(QDialog):
    def __init__(self, deckNamesAndIds: Sequence[DeckNameId]) -> None:
        super().__init__()

        deck_label = QLabel("Choose deck:")
        self.deck_dropdown = QComboBox()
        for d in deckNamesAndIds:
            self.deck_dropdown.addItem(d.name, d.id)

        deck_hbox = QHBoxLayout()
        deck_hbox.addWidget(deck_label)
        deck_hbox.addWidget(self.deck_dropdown)

        cc_label = QLabel("Choose cc profile:")
        self.cc_dropdown = QComboBox()
        for cc in [
            "hk2s",
            "s2hk",
            "s2t",
            "s2tw",
            "s2twp",
            "t2hk",
            "t2s",
            "t2tw",
            "tw2s",
            "tw2sp",
        ]:
            self.cc_dropdown.addItem(cc)

        cc_hbox = QHBoxLayout()
        cc_hbox.addWidget(cc_label)
        cc_hbox.addWidget(self.cc_dropdown)

        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(lambda: self.convert())

        vbox_main = QVBoxLayout()
        vbox_main.addLayout(deck_hbox)
        vbox_main.addLayout(cc_hbox)
        vbox_main.addWidget(convert_btn)

        self.setLayout(vbox_main)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

    def convert(self):
        deck_name = self.deck_dropdown.currentText()
        deck_id = self.deck_dropdown.currentData()
        cc_name = self.cc_dropdown.currentText()
        showInfo(f"Hello {deck_name} {deck_id} {cc_name}")


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

    deckNamesAndIds = mw.col.decks.all_names_and_ids()

    widget = Menu(deckNamesAndIds)
    widget.exec()

    # cc = OpenCC("s2t")
    # did = mw.col.decks.get_current_id()
    # deck = mw.col.decks.get(did)
    # if deck is None:
    #     return
    # deck["name"] = cc.convert(deck["name"])
    # mw.col.decks.save(deck)
    # ids = mw.col.decks.cids(did)
    # for id in ids:
    #     card = mw.col.get_card(id)
    #     note = card.note()
    #     note_type = note.note_type()
    #     if note_type is None:
    #         return
    #
    #     for k, v in note_type.items():
    #         if isinstance(v, str):
    #             note_type[k] = cc.convert(v)
    #         elif isinstance(v, dict) or isinstance(v, list):
    #             note_type[k] = json.loads(cc.convert(json.dumps(v, ensure_ascii=False)))
    #             showInfo(f"{note_type[k]}")
    #
    #     mw.col.models.save(note_type)
    #
    #     # showInfo(f"notetype: {note_type.keys()}")
    #     showInfo(f"notetype: {note.note_type()}")
    #     #
    #     # for k, v in note.items():
    #     #     # converted_k = cc.convert(k)
    #     #     converted_v = cc.convert(v)
    #     #     note[k] = converted_v
    #     #
    #     # mw.col.update_note(note)
    #     # # showInfo(f"card: {dir(card)}")
    #     # showInfo(f"card: {note.keys()}")
    #     # showInfo(f"card: {note.values()}")
    #     #
    #     break
    # # showInfo("Card counttt: %d" % (len(ids)))
    # # show a message box
    # # showInfo("Card count: %d" % cardCount)


# create a new menu item, "test"
action = QAction("test", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, testFunction)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
