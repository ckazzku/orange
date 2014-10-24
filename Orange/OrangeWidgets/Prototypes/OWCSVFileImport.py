"""
<name>CSV File import</name>
<description>Import comma separated file</description>

"""
import os
import csv
import unicodedata
from StringIO import StringIO

from PyQt4.QtCore import pyqtSignal as Signal
import Orange

from OWWidget import *
import OWGUI

from OWDataTable import ExampleTableModel

NAME = "File Import"
DESCRIPTION = "Import files"
ICON = "icons/File.svg"

OUTPUTS = [
    {"name": "Data",
     "type": Orange.data.Table,
     "doc": "Loaded data table"}
]

PRIORITY = 15
CATEGORY = "Data"
KEYWORDS = ["data", "import", "file", "load", "read"]

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


class Dialect(csv.Dialect):
    def __init__(self, delimiter, quotechar, escapechar, doublequote,
                 skipinitialspace, quoting=csv.QUOTE_MINIMAL):
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.doublequote = doublequote
        self.skipinitialspace = skipinitialspace
        self.quoting = quoting
        self.lineterminator = "\r\n"

        csv.Dialect.__init__(self)


class CSVOptionsWidget(QWidget):
    _PresetDelimiters = [
        ("Comma", ","),
        ("Tab", "\t"),
        ("Semicolon", ";"),
        ("Space", " "),
    ]

    format_changed = Signal()

    def __init__(self, parent=None, **kwargs):
        self._delimiter_idx = 0
        self._delimiter_custom = "|"
        self._delimiter = ","
        self._quotechar = "'"
        self._escapechar = "\\"
        self._doublequote = True
        self._skipinitialspace = False

        self._hasheader = False

        super(QWidget, self).__init__(parent, **kwargs)

        layout = QVBoxLayout()
        # Dialect options

        form = QFormLayout()
        self.delimiters_cb = QComboBox()
        self.delimiters_cb.addItems(
            [name for name, _ in self._PresetDelimiters]
        )
        self.delimiters_cb.insertSeparator(self.delimiters_cb.count())
        self.delimiters_cb.addItem("Other")

        self.delimiters_cb.setCurrentIndex(self._delimiter_idx)
        self.delimiters_cb.activated.connect(self._on_delimiter_idx_changed)

        validator = QRegExpValidator(QRegExp("."))
        self.delimiteredit = QLineEdit(
            enabled=False
        )
        self.delimiteredit.setValidator(validator)
        self.delimiteredit.textChanged.connect(self._on_delimiter_changed)

        delimlayout = QHBoxLayout()
        delimlayout.setContentsMargins(0, 0, 0, 0)
        delimlayout.addWidget(self.delimiters_cb)
        delimlayout.addWidget(self.delimiteredit)

        self.quoteedit = QLineEdit(self._quotechar)
        self.quoteedit.setValidator(validator)
        self.quoteedit.textChanged.connect(self._on_quotechar_changed)

        self.escapeedit = QLineEdit(self._escapechar)
        self.escapeedit.setValidator(validator)

        self.skipinitialspace_cb = QCheckBox(
            checked=self._skipinitialspace
        )

        form.addRow("Cell delimiters", delimlayout)
        form.addRow("Quote", self.quoteedit)
        form.addRow("Escape character", self.escapeedit)
        form.addRow("Skip initial white space", QCheckBox())

        form.addRow(QFrame(self, frameShape=QFrame.HLine))
        # File format option
        form.addRow("Missing values", QLineEdit())
        layout.addLayout(form)

#         form.addRow("", QCheckBox("Has header"))
#         form.addRow("", QCheckBox("Skip empty lines"))
#         form.addRow("", QCheckBox("Has header"))
#         form.addRow("", QCheckBox("Has orange type defs"))

        layout.addWidget(QCheckBox("Has header"))
        layout.addWidget(QCheckBox("Skip empty lines"))
        layout.addWidget(QCheckBox("Has header"))
        layout.addWidget(QCheckBox("Has orange type definitions"))

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

    def dialect(self):
        """
        Return the current state as a Dialect instance.
        """
        if self._delimiter_idx >= len(self._PresetDelimiters):
            delimiter = self._delimiter_custom
        else:
            _, delimiter = self._PresetDelimiters[self._delimiter_idx]

        return Dialect(delimiter, self._quotechar, self._escapechar,
                       self._doublequote, self._skipinitialspace)

    def setDialect(self, dialect):
        """
        Set the current state to match dialect instance.
        """
        delimiter = dialect.delimiter
        try:
            index = [d for _, d in self._PresetDelimiters].index(delimiter)
        except ValueError:
            index = -1

        self.delimter_cb.setCurrentIndex(index)

        if index == -1:
            self.custom_delimiter_te.setText(delimiter)

        self.quoteedit.setText(dialect.quotechar)
        self.escapeedit.setText(dialect.escapechar)
        self.skipinitialspace_cb.setChecked(dialect.skipinitialspace)

    def has_header(self):
        return self._hasheader_cb.isChecked()

    def _on_delimiter_idx_changed(self, index):
        self.delimiteredit.setEnabled(index >= len(self._PresetDelimiters))
        self._delimiter_idx = index
        self.format_changed.emit()

    def _on_delimiter_changed(self, delimiter):
        self._delimiter_custom = delimiter
        self.format_changed.emit()

    def _on_quotechar_changed(self, quotechar):
        self._quotechar = quotechar
        self.format_changed.emit()

    def _on_escapechar_changed(self, escapechar):
        self._escapechar = escapechar
        self.format_changed.emit()

    def _on_skipspace_changed(self, skipinitialspace):
        self._skipinitialspace = skipinitialspace
        self.format_changed.emit()


def cb_append_file_list(combobox, paths):
    model = combobox.model()
    count = model.rowCount()
    cb_insert_file_list(combobox, count, paths)


def cb_insert_file_list(combobox, index, paths):
    model = combobox.model()
    iconprovider = QFileIconProvider()

    for i, path in enumerate(paths):
        basename = os.path.basename(path)
        item = QStandardItem(basename)
        item.setToolTip(path)
        item.setIcon(iconprovider.icon(QFileInfo(path)))
        model.insertRow(index + i, item)


class FileNameContextHandler(ContextHandler):
    def match(self, context, imperfect, filename):
        return 2 if os.path.samefile(context.filename, filename) else 0


FILEFORMATS = (
    "Tab-delimited files (*.tab)\n"
    "Tab-delimited simplified (*.txt)\n"
    "Basket files (*.basket)\n"
    "C4.5 files (*.data)\n"
    "Comma-separated values (*.csv)\n"
    "Tab-separated values (*.tsv)\n"
    "Weka (*.arff)\n"
    "All files(*.*)"
)

# Loaders
from collections import namedtuple

OrangeTab = namedtuple("OrangeTab", ["DK", "DC"])
OrangeTxt = namedtuple("OrangeTxt", ["DK", "DC"])
C45 = namedtuple("C45", ["DK", "DC"])
Basket = namedtuple("Basket", ["DK", "DC"])
CSV = namedtuple("CSV", ["NA", "dialect", "has_header"])
TSV = namedtuple("TSV", ["NA", "dialect", "has_header"])
Arff = namedtuple("Arff", [])


class OWCSVFileImport(OWWidget):
    settingsList = ["selected_file", "recent_files", "hints",
                    "show_advenced", "create_new_on"]
    contextHandlers = {"": FileNameContextHandler()}

    DELIMITERS = [
        ("Tab", "\t"),
        ("Comma", ","),
        ("Semicolon", ";"),
        ("Space", " "),
        ("Others", None)
    ]

    def __init__(self, parent=None, signalManager=None,
                 title="CSV File Import"):
        OWWidget.__init__(self, parent, signalManager, title,
                          wantMainArea=False)
        # Settings CSV
        self.delimiter = ","
        self.other_delimiter = None
        self.quote = '"'
        self.missing = ""

        self.skipinitialspace = True
        self.has_header = True
        self.has_orange_header = True

        #: Current selected file name
        self.selected_file = None
        #: List of recent opened files.
        self.recent_files = []
        #: Hints for the recent files
        self.hints = {}

        self.loadSettings()

        self.recent_files = filter(os.path.exists, self.recent_files)

        self.hints = dict([item for item in self.hints.items()
                           if item[0] in self.recent_files])
        self._loaders = {}

        layout = QHBoxLayout()
        OWGUI.widgetBox(self.controlArea, "File", orientation=layout)

        icons = standard_icons(self)

        self.recent_combo = QComboBox(
            self, objectName="recent_combo",
            toolTip="Recent files.",
            activated=self.activate_recent
        )
        cb_append_file_list(self.recent_combo, self.recent_files)

        self.recent_combo.insertSeparator(self.recent_combo.count())
        self.recent_combo.addItem("Browse documentation data sets...")

        self.browse_button = QPushButton(
            unicodedata.lookup("HORIZONTAL ELLIPSIS"),
            icon=icons.dir_open_icon, toolTip="Browse filesystem",
            clicked=self.browse
        )

        self.reload_button = QPushButton(
            "Reload", icon=icons.reload_icon,
            toolTip="Reload the selected file", clicked=self.reload
        )

        layout.addWidget(self.recent_combo, 2)
        layout.addWidget(self.browse_button)
        layout.addWidget(self.reload_button)

        ###########
        # Info text
        ###########
        box = OWGUI.widgetBox(self.controlArea, "Info")
        self.infoa = OWGUI.widgetLabel(box, "No data loaded.")
        self.infob = OWGUI.widgetLabel(box, " ")
        self.warnings = OWGUI.widgetLabel(box, " ")

        # Set word wrap so long warnings won't expand the widget
        self.warnings.setWordWrap(True)
        self.warnings.setSizePolicy(QSizePolicy.Ignored,
                                    QSizePolicy.MinimumExpanding)

        singlecharvalidator = QRegExpValidator(QRegExp("."))

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
        self.delimiter_edit.setValidator(singlecharvalidator)

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
        self.quote_edit.setValidator(singlecharvalidator)

        form.addRow("Quote", self.quote_edit)

        self.missing_edit = QLineEdit(
            text=self.missing,
            editingFinished=self.missing_changed,
            toolTip="Missing value flags (separated by a comma)."
        )

        form.addRow("Missing values", self.missing_edit)

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

        OWGUI.button(self.controlArea, self, "Send", callback=self.send_data,
                     default=True)

        self.resize(450, 500)
        if self.recent_files:
            QTimer.singleShot(
                0, lambda: self.set_selected_file(self.recent_files[0])
            )

    def activate_recent(self, index):
        """
        Load file from the recent list.
        """
        if 0 <= index < len(self.recent_files):
            recent = self.recent_files[index]
            self.set_selected_file(recent)
        elif index == len(self.recent_files) + 1:
            self.browse(Orange.utils.environ.dataset_install_dir)
            if self.recent_combo.currentIndex() == index:
                self.recent_combo.setCurrentIndex(
                    min(0, len(self.recent_files) - 1)
                )
        else:
            assert False

    @pyqtSlot()
    def browse(self, startdir=None):
        """
        Open a file dialog and select a user specified file.
        """
        if startdir is None:
            if self.selected_file:
                startdir = os.path.dirname(self.selected_file)
            else:
                startdir = unicode(
                    QDesktopServices.storageLocation(
                        QDesktopServices.DocumentsLocation)
                )
        path, filter_idx = QFileDialog.getOpenFileNameAndFilter(
            self, "Open Data File", startdir, FILEFORMATS
        )

        if path:
            self.set_selected_file(path, loader_hint=filter_idx)
            return QDialog.Accepted
        else:
            return QDialog.Rejected

    @pyqtSlot()
    def reload(self):
        """
        Reload the current selected file.
        """
        if self.selected_file:
            self.set_selected_file(self.selected_file)

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

    def set_selected_file(self, filename, loader=None):
        index_to_remove = None
        if filename in self.recent_files:
            index_to_remove = self.recent_files.index(filename)
        elif self.recent_combo.count() > 20:
            # Always keep 20 latest files in the list.
            index_to_remove = self.recent_combo.count() - 1
        cb_insert_file_list(self.recent_combo, 0, [filename])
        self.recent_combo.setCurrentIndex(0)
        self.recent_files.insert(0, filename)

        if index_to_remove is not None:
            self.recent_combo.removeItem(index_to_remove + 1)
            self.recent_files.pop(index_to_remove + 1)

        self.warning(1)
#         self.closeContext("")
#         self.openContext("", filename)

        if loader is None:
            loader = self.loader_for_path(filename)

        self.set_loader(loader)

#         if filename in self.hints:
#             hints = self.hints[filename]
#         else:
#             try:
#                 hints = sniff_csv(filename)
#             except csv.Error, ex:
#                 self.warning(1, str(ex))
#                 hints = dict(DEFAULT_HINTS)
# 
#         if not hints:
#             hints = dict(DEFAULT_HINTS)
# 
#         self.hints[filename] = hints
# 
#         delimiter = hints["delimiter"]
# 
#         # Update the widget state (GUI) from the saved hints for the file
#         preset = [d[1] for d in self.DELIMITERS[:-1]]
#         if delimiter not in preset:
#             self.delimiter = None
#             self.other_delimiter = delimiter
#             index = len(self.DELIMITERS) - 1
#             button = self.delimiter_button_group.button(index)
#             button.setChecked(True)
#             self.delimiter_edit.setText(self.other_delimiter)
#             self.delimiter_edit.setEnabled(True)
#         else:
#             self.delimiter = delimiter
#             index = preset.index(delimiter)
#             button = self.delimiter_button_group.button(index)
#             button.setChecked(True)
#             self.delimiter_edit.setEnabled(False)
# 
#         self.quote = hints["quotechar"]
#         self.quote_edit.setText(self.quote)
# 
#         self.missing = hints["DK"] or ""
#         self.missing_edit.setText(self.missing)
# 
#         self.has_header = hints["has_header"]
#         self.has_header_check.setChecked(self.has_header)
# 
#         self.has_orange_header = hints["has_orange_header"]
#         self.has_orange_header_check.setChecked(self.has_orange_header)
# 
# #         self.skipinitialspace = hints["skipinitialspace"]
# #         self.skipinitialspace_check.setChecked(self.skipinitialspace)
# 
#         self.selected_file = filename
#         self.selected_file_head = []
#         with open(self.selected_file, "rU") as f:
#             for i, line in zip(range(30), f):
#                 self.selected_file_head.append(line)
# 
#         self.update_preview()

    def loader_for_path(self, path):
        if path in self._loaders:
            return self._loaders[path]
        else:
            return loader_for_path(path)

    def set_loader(self, loader):
        if self.selected_file:
            self._loaders[self.selected_file] = loader

        self._loader = loader
        if isinstance(loader, OrangeTab):
            self.addvancedstack.setCurrentWidget(self.taboptions)
        elif isinstance(loader, OrangeTxt):
            self.advancedstack.setCurrentWidget(self.taboptions)
        elif isinstance(loader, Basket):
            pass
        elif isinstance(loader, (CSV, TSV)):
            self.advancedstack.setCurrentWidget(self.csvoptions)
        elif isinstance(loader, C45):
            pass
        elif isinstance(loader, Arff):
            pass
        else:
            assert False

    def update_preview(self):
        self.error(0)
        if self.selected_file:
            head = StringIO("".join(self.selected_file_head))
            hints = self.hints[self.selected_file]

            # Save hints for the selected file
            hints["quotechar"] = self.quote
            hints["escapechar"] = "\\"
            hints["delimiter"] = self.delimiter or self.other_delimiter
            hints["has_header"] = self.has_header
            hints["has_orange_header"] = self.has_orange_header
            hints["DK"] = self.missing or None
            try:
                data = Orange.data.io.load_csv(head, delimiter=self.delimiter,
                                   quotechar=self.quote,
                                   has_header=self.has_header,
                                   has_types=self.has_orange_header,
                                   has_annotations=self.has_orange_header,
                                   skipinitialspace=True,
                                   DK=self.missing or None,
                                   create_new_on=MakeStatus.OK)
            except csv.Error, err:
                self.error(0, "csv error {0!s}".format(err))
                data = None
            except Exception, ex:
                self.error(0, "Cannot parse (%s)" % ex)
                data = None

            if data is not None:
                model = ExampleTableModel(data, None, self)
            else:
                model = None
            self.preview_view.setModel(model)

    def send_data(self):
        self.error(0)
        data = None
        if self.selected_file:
            try:
                data = Orange.data.io.load_csv(self.selected_file,
                                   delimiter=self.delimiter,
                                   quotechar=self.quote,
                                   has_header=self.has_header,
                                   has_annotations=self.has_orange_header,
                                   skipinitialspace=True,
                                   DK=self.missing or None,
                                   create_new_on=MakeStatus.OK
                                   )
            except Exception, ex:
                self.error(0, "An error occurred while "
                              "loading the file:\n\t%r" % ex
                              )
                data = None
        self.send("Data", data)

    def settingsFromWidgetCallback(self, handler, context):
        context.filename = self.selected_file or ""
        context.symbolDC, context.symbolDK = self.symbolDC, self.symbolDK

    def settingsToWidgetCallback(self, handler, context):
        self.symbolDC, self.symbolDK = context.symbolDC, context.symbolDK


def sniff_csv(file):
    snifer = csv.Sniffer()
    if isinstance(file, basestring):
        file = open(file, "rU")

    sample = file.read(5 * 2 ** 20)  # max 1MB sample
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


def _call(f, *args, **kwargs):
    return f(*args, **kwargs)

# Make any KernelWarning raise an error if called through the '_call' function
# defined above.
warnings.filterwarnings(
    "error", ".*", Orange.core.KernelWarning,
    __name__, _call.func_code.co_firstlineno + 1
)


def load_tab(filename, createNewOn=2, na_values=set(["?", "~", "NA"])):
    argdict = {"createNewOn": createNewOn}
    data = None
    try:
        return _call(Orange.data.Table, filename, **argdict)
    except Exception as ex:
        if "is being loaded as" in str(ex):
            try:
                data = Orange.data.Table(filename, **argdict)
            except Exception:
                pass

        if data is None:
            exc_type, exc_value = type(ex), ex.args
            return (exc_type, exc_value, str(ex))




if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    w = OWCSVFileImport()
    w.show()
    w.raise_()
    app.exec_()
    w.saveSettings()
