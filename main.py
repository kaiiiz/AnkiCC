from anki.collection import DeckId
from anki import decks_pb2
from aqt.forms.main import QtWidgets  # type: ignore
from aqt.main import AnkiQt
from aqt.operations import QueryOp
from aqt.utils import showCritical, showInfo
from aqt.qt import (
    QListWidget,
    QComboBox,
    QLabel,
    QHBoxLayout,
    QDialog,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QAction,
    Qt,
    qconnect,
)
from typing import Sequence, TypedDict
from .opencc_python.opencc.opencc import OpenCC

import json


def get_mw() -> AnkiQt:
    from aqt import mw

    if mw is None:
        raise Exception("Error: main window is uninitialized")
    return mw


mw = get_mw()

OPENCC_PROFILE = [
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
]


class IgnoredFldsData(TypedDict):
    ntid: int
    name: str


class AnkiCCDialog(QDialog):
    def __init__(self, deck_names_and_ids: Sequence[decks_pb2.DeckNameId]) -> None:
        super().__init__()

        # deck
        deck_label = QLabel("Choose deck:")
        self.deck_dropdown = QComboBox()
        for d in deck_names_and_ids:
            self.deck_dropdown.addItem(d.name, d.id)
        self.deck_dropdown.currentIndexChanged.connect(
            lambda: self.on_deck_dropbox_changed()
        )

        deck_hbox = QHBoxLayout()
        deck_hbox.addWidget(deck_label)
        deck_hbox.addWidget(self.deck_dropdown)

        # OpenCC profile
        cc_label = QLabel("Choose OpenCC profile:")
        self.cc_dropdown = QComboBox()
        self.cc_dropdown.addItems(OPENCC_PROFILE)

        cc_hbox = QHBoxLayout()
        cc_hbox.addWidget(cc_label)
        cc_hbox.addWidget(self.cc_dropdown)

        # Ignored fields
        ignored_flds_label = QLabel("Ignored fields:")
        self.ignored_flds = QListWidget()
        self.ignored_flds.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.update_ignored_fields()

        ignored_flds_hbox = QHBoxLayout()
        ignored_flds_hbox.addWidget(ignored_flds_label)
        ignored_flds_hbox.addWidget(self.ignored_flds)

        # Convert btn
        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(lambda: self.convert())

        # layout
        vbox_main = QVBoxLayout()
        vbox_main.addLayout(deck_hbox)
        vbox_main.addLayout(cc_hbox)
        vbox_main.addLayout(ignored_flds_hbox)
        vbox_main.addWidget(convert_btn)

        self.setLayout(vbox_main)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

    def update_ignored_fields(self):
        if mw.col is None:
            raise Exception("Error: collection is uninitialized")

        deck_id = self.deck_dropdown.currentData()
        cids = mw.col.decks.cids(deck_id)
        note_types = {}
        for cid in cids:
            card = mw.col.get_card(cid)
            note = card.note()
            note_type = note.note_type()
            if note_type is None:
                continue

            ntid = note_type["id"]
            if ntid not in note_types:
                note_types[ntid] = note_type

        self.ignored_flds.clear()
        for ntid, nt in note_types.items():
            for fld in nt["flds"]:
                item = QListWidgetItem(f"{nt['name']} - {fld['name']}")
                ignored_fld_data: IgnoredFldsData = {"ntid": ntid, "name": fld["name"]}
                item.setData(Qt.ItemDataRole.UserRole, ignored_fld_data)
                self.ignored_flds.addItem(item)

    def on_deck_dropbox_changed(self):
        self.update_ignored_fields()

    def convert(self):
        def on_convert_success(convert_ret: tuple[int, int]) -> None:
            num_cards = convert_ret[0]
            num_nt = convert_ret[1]
            showInfo(f"Convert {num_cards} cards and {num_nt} note type successfully")

        deck_id = self.deck_dropdown.currentData()
        cc_profile = self.cc_dropdown.currentText()
        ignored_flds = self.ignored_flds.selectedItems()
        op = QueryOp(
            parent=self,
            op=lambda _: self.convert_deck(deck_id, cc_profile, ignored_flds),
            success=on_convert_success,
        )
        op.with_progress().run_in_background()

    def convert_deck(
        self, deck_id: DeckId, cc_profile: str, ignored_flds: list[QListWidgetItem]
    ) -> tuple[int, int]:
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

        # build ignored fields table
        ignored_flds = self.ignored_flds.selectedItems()
        ignored_flds_tbl: dict[int, list[str]] = {}
        for fld in ignored_flds:
            fld_data: IgnoredFldsData = fld.data(Qt.ItemDataRole.UserRole)
            ntid = fld_data["ntid"]
            name = fld_data["name"]
            if ntid not in ignored_flds_tbl:
                ignored_flds_tbl[ntid] = []
            ignored_flds_tbl[ntid].append(name)

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

            note.set_tags_from_str(cc.convert(note.string_tags()))

            for k, v in note.items():
                if (ntid not in ignored_flds_tbl) or (k not in ignored_flds_tbl[ntid]):
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

    deck_names_and_ids = mw.col.decks.all_names_and_ids()
    dialog = AnkiCCDialog(deck_names_and_ids)
    dialog.exec()


action = QAction("AnkiCC", mw)
qconnect(action.triggered, main)
mw.form.menuTools.addAction(action)
