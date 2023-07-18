from anki.collection import DeckId
from anki import decks_pb2
from aqt.main import AnkiQt
from aqt.operations import QueryOp
from aqt.utils import showCritical, showInfo
from aqt.qt import qconnect
from aqt.qt import (
    QComboBox,
    QLabel,
    QHBoxLayout,
    QDialog,
    QPushButton,
    QVBoxLayout,
    QAction,
)
from typing import Sequence
from .opencc_python.opencc.opencc import OpenCC

import json


def get_mw() -> AnkiQt:
    from aqt import mw

    if mw is None:
        raise Exception("Error: main window is uninitialized")
    return mw


mw = get_mw()


class AnkiCCDialog(QDialog):
    def __init__(self, deckNamesAndIds: Sequence[decks_pb2.DeckNameId]) -> None:
        super().__init__()

        deck_label = QLabel("Choose deck:")
        self.deck_dropdown = QComboBox()
        for d in deckNamesAndIds:
            self.deck_dropdown.addItem(d.name, d.id)

        deck_hbox = QHBoxLayout()
        deck_hbox.addWidget(deck_label)
        deck_hbox.addWidget(self.deck_dropdown)

        cc_label = QLabel("Choose OpenCC profile:")
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
        def on_convert_success(convert_ret: tuple[int, int]) -> None:
            num_cards = convert_ret[0]
            num_nt = convert_ret[1]
            showInfo(f"Convert {num_cards} cards and {num_nt} note type successfully")

        deck_id = self.deck_dropdown.currentData()
        cc_profile = self.cc_dropdown.currentText()
        op = QueryOp(
            parent=self,
            op=lambda _: self.convert_deck(deck_id, cc_profile),
            success=on_convert_success,
        )
        op.with_progress().run_in_background()

    def convert_deck(self, deck_id: DeckId, cc_profile: str) -> tuple[int, int]:
        def update_progess(label: str, val: int, num_cards: int):
            mw.progress.update(
                label=f"{label} ({val}/{num_cards})",
                value=val,
                max=num_cards,
            )

        if mw.col is None:
            raise Exception("Error: collection is uninitialized")

        cc = OpenCC(cc_profile)
        deck = mw.col.decks.get(deck_id)
        if deck is None:
            raise Exception("Error: deck not found")

        # convert deck data
        deck["name"] = cc.convert(deck["name"])
        mw.col.decks.save(deck)

        # convert card and gather note type
        cids = mw.col.decks.cids(deck_id)
        num_cards = len(cids)
        note_types = {}
        for idx, cid in enumerate(cids):
            card = mw.col.get_card(cid)
            note = card.note()
            note_type = note.note_type()
            if note_type is None:
                continue

            ntid = note_type["id"]
            if ntid not in note_types:
                note_types[ntid] = note_type

            for k, v in note.items():
                note[k] = cc.convert(v)

            mw.col.update_note(note)
            mw.taskman.run_on_main(
                lambda: update_progess("Convert cards", idx, num_cards)
            )

        # convert note type
        num_nt = len(note_types)
        for idx, (_, note_type) in enumerate(note_types.items()):
            for k, v in note_type.items():
                if isinstance(v, str):
                    note_type[k] = cc.convert(v)
                elif isinstance(v, dict) or isinstance(v, list):
                    note_type[k] = json.loads(
                        cc.convert(json.dumps(v, ensure_ascii=False))
                    )
            mw.col.models.save(note_type)
            mw.taskman.run_on_main(
                lambda: update_progess("Convert note type", idx, num_nt)
            )

        return num_cards, num_nt


def main() -> None:
    if mw.col is None:
        showCritical("Error: collection is uninitialized")
        return

    deckNamesAndIds = mw.col.decks.all_names_and_ids()
    dialog = AnkiCCDialog(deckNamesAndIds)
    dialog.exec()


action = QAction("AnkiCC", mw)
qconnect(action.triggered, main)
mw.form.menuTools.addAction(action)
