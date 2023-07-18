# import the main window object (mw) from aqt
from PyQt6 import QtWidgets
from anki.collection import DeckId
from aqt import mw
from aqt.forms.main import QtCore

# import the "show info" tool from utils.py
from aqt.utils import showCritical, showInfo

from aqt.qt import qconnect

# import all of the Qt GUI library
from aqt.qt import (
    QComboBox,
    QLabel,
    QHBoxLayout,
    QDialog,
    QPushButton,
    QVBoxLayout,
    QAction,
)

from .opencc_python.opencc.opencc import OpenCC

import json
from typing import Sequence

from anki import decks_pb2

DeckNameId = decks_pb2.DeckNameId


class CCDialog(QDialog):
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
        deck_id = self.deck_dropdown.currentData()
        cc_profile = self.cc_dropdown.currentText()
        self.convert_deck(deck_id, cc_profile)

    def convert_deck(self, deck_id: DeckId, cc_profile: str):
        if mw is None or mw.col is None:
            showCritical("Error: main window is uninitialized")
            return

        cc = OpenCC(cc_profile)
        deck = mw.col.decks.get(deck_id)
        if deck is None:
            showCritical("Error: deck not found")
            return

        # convert deck data
        deck["name"] = cc.convert(deck["name"])
        mw.col.decks.save(deck)

        # convert card and gather note type
        cids = mw.col.decks.cids(deck_id)
        num_cards = len(cids)
        note_types = {}
        for cid in cids:
            card = mw.col.get_card(cid)
            note = card.note()
            note_type = note.note_type()
            if note_type is None:
                continue

            ntid = note_type["id"]
            note_types[ntid] = note_type

            for k, v in note.items():
                note[k] = cc.convert(v)

            mw.col.update_note(note)

        # convert note type
        num_nt = len(note_types)
        for _, note_type in note_types.items():
            for k, v in note_type.items():
                if isinstance(v, str):
                    note_type[k] = cc.convert(v)
                elif isinstance(v, dict) or isinstance(v, list):
                    note_type[k] = json.loads(
                        cc.convert(json.dumps(v, ensure_ascii=False))
                    )
            mw.col.models.save(note_type)

        showInfo(f"Convert {num_cards} cards and {num_nt} note type successfully")


def main() -> None:
    if mw is None or mw.col is None:
        showCritical("Error: main window is uninitialized")
        return

    deckNamesAndIds = mw.col.decks.all_names_and_ids()
    dialog = CCDialog(deckNamesAndIds)
    dialog.exec()


# create a new menu item, "test"
action = QAction("AnkiCC", mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, main)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
