"""
<name>CSV File import</name>
<description>Import comma separated file</description>

"""
import os
import csv
from StringIO import StringIO

import Orange

from OWWidget import *
import OWGUI

from OWDataTable import ExampleTableModel

NAME = "CSV File Import"
DESCRIPTION = "Import CSV files"
ICON = "icons/CSV.svg"

OUTPUTS = [
    {"name": "Data",
     "type": Orange.data.Table,
     "doc": "Loaded data table"}
]

PRIORITY = 15
CATEGORY = "Data"
KEYWORDS = ["data", "csv", "file", "load", "read"]

MakeStatus = Orange.feature.Descriptor.MakeStatus


# Hints used when the sniff_csv cannot determine the dialect.
DEFAULT_HINTS = {
    "delimiter": ",",
    "quotechar": "'",
    "doublequote": False,
    "quoting": csv.QUOTE_MINIMAL,
    "escapechar": "\\",
    "skipinitialspace": True,
    "has_header": True,
    "has_orange_header": False,
    "DK": "?",
}


class standard_icons(object):
    def __init__(self, qwidget=None, style=None):
        self.qwidget = qwidget
        if qwidget is None:
            self.style = QApplication.instance().style()
        else:
            self.style = qwidget.style()

    @property
    def dir_open_icon(self):
        return self.style.standardIcon(QStyle.SP_DirOpenIcon)

    @property
    def reload_icon(self):
        return self.style.standardIcon(QStyle.SP_BrowserReload)


class OWCSVFileImport(OWWidget):
    settingsList = ["recent_files", "hints"]

    DELIMITERS = [("Tab", "\t"),
                  ("Comma", ","),
                  ("Semicolon", ";"),
                  ("Space", " "),
                  ("Others", None),
                  ]

    def __init__(self, parent=None, signalManager=None,
                 title="CSV File Import"):
        OWWidget.__init__(self, parent, signalManager, title,
                          wantMainArea=False)

        self.inputs = []
        self.outputs = [("Data", Orange.data.Table)]

        # Settings
        self.delimiter = ","
        self.other_delimiter = None
        self.quote = '"'
        self.missing = ""

        self.skipinitialspace = True
        self.has_header = True
        self.has_orange_header = True

        # List of recent opened files.
        self.recent_files = []

        # Hints for the recent files
        self.hints = {}

        self.loadSettings()

        self.recent_files = filter(os.path.exists, self.recent_files)
        self.hints = dict([item for item in self.hints.items() \
                           if item[0] in self.recent_files])

        layout = QHBoxLayout()
        OWGUI.widgetBox(self.controlArea, "File", orientation=layout)

        icons = standard_icons(self)

        self.recent_combo = QComboBox(
            self, objectName="recent_combo",
            toolTip="Recent files.",
            activated=self.on_select_recent
        )
        self.recent_combo.addItems([os.path.basename(p) \
                                    for p in self.recent_files])

        self.browse_button = QPushButton("...", icon=icons.dir_open_icon,
                                         toolTip="Browse filesystem",
                                         clicked=self.on_open_dialog)

        self.reload_button = QPushButton("Reload", icon=icons.reload_icon,
                                         toolTip="Reload the selected file",
                                         clicked=self.on_reload_file)

        layout.addWidget(self.recent_combo, 2)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.reload_button)

        ###########
        # Info text
        ###########
        box = OWGUI.widgetBox(self.controlArea, "Info")
        self.infolabel = OWGUI.widgetLabel(box, "")
        self.infolabel.setWordWrap(True)

        stack = QStackedWidget()
        self.controlArea.layout().addWiddet(stack)

        #################
        # Cell separators
        #################

        import_options = QWidget()
        grid = QGridLayout()
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)
        import_options.setLayout(grid)

        self.controlArea.layout().addWidget(import_options)

        box = OWGUI.widgetBox(self.controlArea, "Cell Separator",
                              addToLayout=False)
        import_options.layout().addWidget(box, 0, 0)
        button_group = QButtonGroup(box)
        button_group.buttonPressed[int].connect(self.delimiter_changed)

        for i, (name, char) in  enumerate(self.DELIMITERS[:-1]):
            button = QRadioButton(
                name, box, toolTip="Use %r as cell separator" % char
            )
            button_group.addButton(button, i)
            box.layout().addWidget(button)

        button = QRadioButton("Other", box, toolTip="Use a custom character")

        button_group.addButton(button, i + 1)
        box.layout().addWidget(button)

        self.delimiter_button_group = button_group

        self.delimiter_edit = QLineEdit(
            objectName="delimiter_edit",
            text=self.other_delimiter or self.delimiter,
            editingFinished=self.delimiter_changed,
            toolTip="Cell delimiter character."
        )

        ibox = OWGUI.indentedBox(box)
        ibox.layout().addWidget(self.delimiter_edit)

        preset = [d[1] for d in self.DELIMITERS[:-1]]
        if self.delimiter in preset:
            index = preset.index(self.delimiter)
            b = button_group.button(index)
            b.setChecked(True)
            self.delimiter_edit.setEnabled(False)
        else:
            b = button_group.button(len(self.DELIMITERS) - 1)
            b.setChecked(True)
            self.delimiter_edit.setEnabled(True)

        ###############
        # Other options
        ###############
        form = QFormLayout()
        box = OWGUI.widgetBox(self.controlArea, "Other Options",
                              orientation=form, addToLayout=False)

        self.quote_edit = QLineEdit(
            text=self.quote,
            editingFinished=self.quote_changed,
            toolTip="Text quote character."
        )

        form.addRow("Quote", self.quote_edit)

        self.missing_edit = QLineEdit(
            text=self.missing,
            editingFinished=self.missing_changed,
            toolTip="Missing value flags (separated by a comma)."
        )

        form.addRow("Missing values", self.missing_edit)

        self.skipinitialspace_check = QCheckBox(
            checked=self.skipinitialspace,
            text="Skip initial whitespace",
            toolTip="Skip any whitespace at the beginning of each cell.",
            clicked=self.skipinitialspace_changed
        )

        form.addRow(self.skipinitialspace_check)

        self.has_header_check = QCheckBox(
            checked=self.has_header,
            text="Header line",
            toolTip="Use the first line as a header",
            clicked=self.has_header_changed
        )

        form.addRow(self.has_header_check)

        self.has_orange_header_check = QCheckBox(
            checked=self.has_orange_header,
            text="Has orange variable type definitions",
            toolTip="Use second and third line as a orange style"
                    "'.tab' format feature definitions.",
            clicked=self.has_orange_header_changed
        )

        form.addRow(self.has_orange_header_check)
        import_options.layout().addWidget(box, 0, 1)

        box = OWGUI.widgetBox(self.controlArea, "Preview")
        self.preview_view = QTableView()
        box.layout().addWidget(self.preview_view)

        OWGUI.button(self.controlArea, self, "Send", callback=self.send_data)

        self.selected_file = None
        self.data = None

        self.resize(450, 500)
        if self.recent_files:
            QTimer.singleShot(1,
                    lambda: self.set_selected_file(self.recent_files[0])
                    )

    def on_select_recent(self, recent):
        if isinstance(recent, int):
            recent = self.recent_files[recent]

        self.set_selected_file(recent)

    def on_open_dialog(self):
        last = os.path.expanduser("~/Documents")
        path = QFileDialog.getOpenFileName(self, "Open File", last)
        path = unicode(path)
        if path:
            self.set_selected_file(path)

    def on_reload_file(self):
        if self.recent_files:
            self.set_selected_file(self.recent_files[0])

    def delimiter_changed(self, index=-1):
        self.delimiter = self.DELIMITERS[index][1]
        self.delimiter_edit.setEnabled(self.delimiter is None)
        if self.delimiter is None:
            self.other_delimiter = str(self.delimiter_edit.text())
        self.update_preview()

    def quote_changed(self):
        if self.quote_edit.text():
            self.quote = str(self.quote_edit.text())
            self.update_preview()

    def missing_changed(self):
        self.missing = str(self.missing_edit.text())
        self.update_preview()

    def has_header_changed(self):
        self.has_header = self.has_header_check.isChecked()
        self.update_preview()

    def has_orange_header_changed(self):
        self.has_orange_header = self.has_orange_header_check.isChecked()
        self.update_preview()

    def skipinitialspace_changed(self):
        self.skipinitialspace = self.skipinitialspace_check.isChecked()
        self.update_preview()

    def set_selected_file(self, filename):
        basedir, name = os.path.split(filename)
        index_to_remove = None
        if filename in self.recent_files:
            index_to_remove = self.recent_files.index(filename)
        elif self.recent_combo.count() > 20:
            # Always keep 20 latest files in the list.
            index_to_remove = self.recent_combo.count() - 1
        self.recent_combo.insertItem(0, name)
        self.recent_combo.setCurrentIndex(0)
        self.recent_files.insert(0, filename)

        if index_to_remove is not None:
            self.recent_combo.removeItem(index_to_remove + 1)
            self.recent_files.pop(index_to_remove + 1)

        self.warning(1)
        if filename in self.hints:
            hints = self.hints[filename]
        else:
            try:
                hints = sniff_csv(filename)
            except csv.Error, ex:
                self.warning(1, str(ex))
                hints = dict(DEFAULT_HINTS)

        if not hints:
            hints = dict(DEFAULT_HINTS)

        self.hints[filename] = hints

        delimiter = hints["delimiter"]

        # Update the widget state (GUI) from the saved hints for the file
        preset = [d[1] for d in self.DELIMITERS[:-1]]
        if delimiter not in preset:
            self.delimiter = None
            self.other_delimiter = delimiter
            index = len(self.DELIMITERS) - 1
            button = self.delimiter_button_group.button(index)
            button.setChecked(True)
            self.delimiter_edit.setText(self.other_delimiter)
            self.delimiter_edit.setEnabled(True)
        else:
            self.delimiter = delimiter
            index = preset.index(delimiter)
            button = self.delimiter_button_group.button(index)
            button.setChecked(True)
            self.delimiter_edit.setEnabled(False)

        self.quote = hints["quotechar"]
        self.quote_edit.setText(self.quote)

        self.missing = hints["DK"] or ""
        self.missing_edit.setText(self.missing)

        self.has_header = hints["has_header"]
        self.has_header_check.setChecked(self.has_header)

        self.has_orange_header = hints["has_orange_header"]
        self.has_orange_header_check.setChecked(self.has_orange_header)

        self.skipinitialspace = hints["skipinitialspace"]
        self.skipinitialspace_check.setChecked(self.skipinitialspace)

        self.selected_file = filename
        self.selected_file_head = []
        with open(self.selected_file, "rU") as f:
            for i, line in zip(range(30), f):
                self.selected_file_head.append(line)

        self.update_preview()

    def update_preview(self):
        self.error(0)
        if self.selected_file:
            head = StringIO("".join(self.selected_file_head))
            hints = self.hints[self.selected_file]

            # Save hints for the selected file
            hints["quotechar"] = self.quote
            hints["delimiter"] = self.delimiter or self.other_delimiter
            hints["has_header"] = self.has_header
            hints["has_orange_header"] = self.has_orange_header
            hints["skipinitialspace"] = self.skipinitialspace
            hints["DK"] = self.missing or None
            try:
                data = Orange.data.io.load_csv(head, delimiter=self.delimiter,
                                   quotechar=self.quote,
                                   has_header=self.has_header,
                                   has_types=self.has_orange_header,
                                   has_annotations=self.has_orange_header,
                                   skipinitialspace=self.skipinitialspace,
                                   DK=self.missing or None,
                                   create_new_on=MakeStatus.OK)
            except Exception, ex:
                self.error(0, "Cannot parse (%r)" % ex)
                data = None

            if data is not None:
                model = ExampleTableModel(data, None, self)
            else:
                model = None
            self.preview_view.setModel(model)

    def send_data(self):
        self.error(0)
        if self.selected_file:
            try:
                data = Orange.data.io.load_csv(self.selected_file,
                                   delimiter=self.delimiter,
                                   quotechar=self.quote,
                                   has_header=self.has_header,
                                   has_annotations=self.has_orange_header,
                                   skipinitialspace=self.skipinitialspace,
                                   DK=self.missing or None,
                                   create_new_on=MakeStatus.OK
                                   )
            except Exception, ex:
                self.error(0, "An error occurred while "
                              "loading the file:\n\t%r" % ex
                              )
                data = None
            self.data = data
        self.send("Data", self.data)


def sniff_csv(file):
    snifer = csv.Sniffer()
    if isinstance(file, basestring):
        file = open(file, "rU")

    sample = file.read(2 ** 20)  # max 1MB sample
    dialect = snifer.sniff(sample)
    has_header = snifer.has_header(sample)

    return {"delimiter": dialect.delimiter,
            "doublequote": dialect.doublequote,
            "escapechar": dialect.escapechar,
            "quotechar": dialect.quotechar,
            "quoting": dialect.quoting,
            "skipinitialspace": dialect.skipinitialspace,
            "has_header": has_header,
            "has_orange_header": False,
            "skipinitialspace": True,
            "DK": None,
            }

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = OWCSVFileImport()
    w.show()
    w.raise_()
    app.exec_()
    w.saveSettings()
