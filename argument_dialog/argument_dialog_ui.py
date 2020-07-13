import inspect
import os
import re
import sys

from Qt import QtCore, QtWidgets, QtGui


class ArgumentWidget(QtWidgets.QWidget):
    value_modified = QtCore.Signal()

    def __init__(self, name, default_value, is_required=False, parent=None):
        super(ArgumentWidget, self).__init__(parent)
        self.name = name
        self.default_value = default_value
        self.was_modified = False
        self.is_required = is_required

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.argument_context_menu)

        arg_widgets = self.build_widget()
        if not isinstance(arg_widgets, (list, tuple)):
            arg_widgets = (arg_widgets,)

        for arg_widget in arg_widgets:
            arg_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            arg_widget.customContextMenuRequested.connect(self.argument_context_menu)

        self.default_style = "background-color:rgb(120, 120, 120); color:white;"
        self.setStyleSheet(self.default_style)

        if is_required:
            self.mark_as_required()  # has no real Default value, needs input from user.

        self.setLayout(self.main_layout)

    def argument_context_menu(self, position):
        menu = QtWidgets.QMenu(self)
        menu.addAction("Reset Value", self.set_value_to_default)
        menu.exec_(self.mapToGlobal(position))

    def build_widget(self):
        return ()

    def get_argument_value(self):
        return

    def set_value(self, val):
        pass

    def mark_as_required(self, has_value=False):
        if has_value:
            self.setStyleSheet(self.default_style)
        else:
            self.setStyleSheet("background-color:rgb(250, 200, 100); color:black;")  # orange-ish tone

    def mark_as_modified(self):
        self.was_modified = True
        self.value_modified.emit()
        self.setStyleSheet("background-color:rgb(100, 150, 100); color:white;")  # green-ish tone

    def set_value_to_default(self):
        self.set_value(self.default_value)
        self.was_modified = False
        self.value_modified.emit()
        self.mark_as_required(has_value=not self.is_required)  # reset background-color


class BoolCheckBoxWidget(ArgumentWidget):
    def build_widget(self):
        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setChecked(self.default_value)
        self.main_layout.addWidget(self.check_box)
        self.check_box.stateChanged.connect(self.mark_as_modified)
        return self.check_box

    def set_value(self, val):
        self.check_box.setChecked(val)

    def get_argument_value(self):
        return self.check_box.isChecked()


class DoubleSpinBoxWidget(ArgumentWidget):
    def build_widget(self):
        self.spin_box = self.create_spin_widget()
        self.spin_box.setMinimum(-999999999)
        self.spin_box.setMaximum(999999999)
        self.spin_box.setValue(self.default_value)
        self.main_layout.addWidget(self.spin_box)
        self.spin_box.valueChanged.connect(self.mark_as_modified)
        return self.spin_box

    def create_spin_widget(self):  # integer spin overloads this
        spin = QtWidgets.QDoubleSpinBox()
        spin.setDecimals(4)
        return spin

    def set_value(self, val):
        self.spin_box.setValue(val)

    def get_argument_value(self):
        return self.spin_box.value()


class IntegerSpinBoxWidget(DoubleSpinBoxWidget):
    def create_spin_widget(self):
        return QtWidgets.QSpinBox()


class StringTextEditWidget(ArgumentWidget):
    """
    TextEdit is a real pain for widget height. Currently not in use.
    TODO: Maybe swap out the LineEdit for this class when attempting to enter new line, or pasting multi-line strings.
    """

    def build_widget(self):
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setText(self.default_value)
        self.main_layout.addWidget(self.text_edit)
        self.text_edit.textChanged.connect(self.mark_as_modified)
        self.text_edit.setMinimumHeight(0)
        return self.text_edit

    def set_value(self, val):
        self.text_edit.setText(val)

    def get_argument_value(self):
        return self.text_edit.toPlainText()


"""
    def sizeHint(self):
        doc_size = self.text_edit.document().size()
        self.text_edit.setMinimumHeight(doc_size.height())
        return doc_size.toSize()

    def resizeEvent(self, *args):
        super(StringTextEditWidget, self).resizeEvent(*args)
        self.updateGeometry()
"""


class StringLineEditWidget(ArgumentWidget):
    def build_widget(self):
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setText(self.default_value)
        self.main_layout.addWidget(self.line_edit)
        self.line_edit.textEdited.connect(self.mark_as_modified)
        return self.line_edit

    def set_value(self, val):
        self.line_edit.setText(val)

    def get_argument_value(self):
        return self.line_edit.text()

    def mark_as_required(self, *args, **kwargs):
        super(StringLineEditWidget, self).mark_as_required(*args, **kwargs)
        self.line_edit.setPlaceholderText("REQUIRED")


class StringFilePathWidget(StringLineEditWidget):
    def build_widget(self):
        parent_widget = super(StringFilePathWidget, self).build_widget()
        browse_file_button = QtWidgets.QPushButton()
        browse_file_button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogOpenButton")))
        browse_file_button.clicked.connect(self.browse_file_path)
        self.main_layout.addWidget(browse_file_button)
        return parent_widget, browse_file_button

    def browse_file_path(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Browse File")
        if file_path:
            self.set_value(file_path)
            self.mark_as_modified()


class ArgumentDialog(QtWidgets.QDialog):
    def __init__(self, func, argument_widgets=None, empty_default_type=str, parent=None):
        super(ArgumentDialog, self).__init__(parent)
        self.setWindowTitle("Argument Dialog")
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "icons", "argument_dialog_icon.png")))

        stylesheet_path = os.path.join(os.path.dirname(__file__), "stylesheets", "darkblue.stylesheet")
        if os.path.exists(stylesheet_path):
            with open(stylesheet_path, "r") as fh:
                self.setStyleSheet(fh.read())

        self.func = func
        self.empty_default_type = empty_default_type
        self.input_arg_widget_dict = argument_widgets if argument_widgets else {}
        self.generated_arg_widgets = []

        self.main_layout = QtWidgets.QVBoxLayout()

        top_text_L = QtWidgets.QLabel("Arguments for function: {}".format(self.func.__name__))
        self.main_layout.addWidget(top_text_L)

        self.argument_TW = QtWidgets.QTreeWidget()
        self.argument_TW.setColumnCount(2)
        self.argument_TW.setHeaderLabels(("Argument", "Value"))
        self.argument_TW.setColumnWidth(0, 200)

        self.generate_argument_widgets()

        # argument_scroll_area.setWidget(scroll_widget)
        self.main_layout.addWidget(self.argument_TW)

        self.func_preview_text_TE = QtWidgets.QTextEdit()
        self.func_preview_text_TE.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.func_preview_text_TE.setWordWrapMode(QtGui.QTextOption.NoWrap)
        self.func_preview_text_TE.setReadOnly(True)
        self.main_layout.addWidget(self.func_preview_text_TE)

        self.run_BTN = QtWidgets.QPushButton("Run")
        self.run_BTN.setMinimumHeight(40)
        self.run_BTN.clicked.connect(self.run_func)
        self.main_layout.addWidget(self.run_BTN)

        self.main_layout.setStretch(1, 25)  # give the TreeWidget some extra height
        self.main_layout.setStretch(2, 10)

        self.setLayout(self.main_layout)
        self.resize(700, 500)
        self.preview_func_call()

    def generate_argument_widgets(self):
        type_widgets = {
            'bool': BoolCheckBoxWidget,
            'str': StringLineEditWidget,
            'int': IntegerSpinBoxWidget,
            'float': DoubleSpinBoxWidget,
            'path': StringFilePathWidget,
        }

        # ------------------------------------------------------------------------
        # get doc string as tooltip for the widget
        param_tool_tips = {}
        param_doc_string_types = {}
        type_regex_pattern = re.compile('<(.*)>', re.IGNORECASE)

        func_doc_string = inspect.getdoc(self.func)  # god I love python sometimes
        if func_doc_string:
            for doc_line in func_doc_string.splitlines():
                try:
                    if ":param " not in doc_line:  # this is not very safe
                        continue
                    param_doc_split = doc_line.lstrip(":param ").split(":")  # neither ís this, split arg name / arg doc
                    if len(param_doc_split) == 1:
                        continue
                    if not param_doc_split[1]:  # if doc string is blank, don't add it to dict
                        continue

                    param_tool_tips[param_doc_split[0]] = param_doc_split[1]

                    # Extract type from doc string if possible
                    type_doc_part = param_doc_split[1]
                    type_regex_search_result = type_regex_pattern.search(type_doc_part)
                    if type_regex_search_result:
                        param_doc_string_types[param_doc_split[0]] = type_regex_search_result.group(1)

                except Exception as e:
                    print(e)

        # ----------------------------------------------------------
        # iterate through function arguments
        sig = inspect.signature(self.func)
        for param in sig.parameters.values():  # type: inspect.Parameter

            tree_widget_item = QtWidgets.QTreeWidgetItem()
            tree_widget_item.setText(0, param.name)
            self.argument_TW.addTopLevelItem(tree_widget_item)

            arg_layout = QtWidgets.QHBoxLayout()
            arg_layout.setContentsMargins(0, 0, 0, 0)

            arg_label = QtWidgets.QLabel("{}: ".format(param.name))
            arg_label.setMinimumWidth(40)
            arg_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
            arg_layout.addWidget(arg_label)

            # ------------------------------------------------------------------------
            default_value = param.default
            has_default_value = default_value != inspect.Parameter.empty
            if not has_default_value:
                default_value = self.empty_default_type() if self.empty_default_type else None

            param_type = type(default_value)
            arg_widget_cls = self.input_arg_widget_dict.get(param.name)  # QT Class can be specified in main() arguments

            if arg_widget_cls is None:
                doc_string_type = param_doc_string_types.get(param.name)
                if doc_string_type:  # Try to find matching QT Widget from doc string type
                    arg_widget_cls = type_widgets.get(doc_string_type)

            if arg_widget_cls is None:
                # Try to find matching QT Widget from value type()
                arg_widget_cls = type_widgets.get(param_type.__name__)

            # ------------------------------------------------------------------------
            if arg_widget_cls:
                # Create QT Widget instance for this value type
                arg_widget_instance = arg_widget_cls(param.name, default_value,
                                                     is_required=not has_default_value)  # type:ArgumentWidget
                arg_widget_instance.value_modified.connect(self.preview_func_call)
                # arg_layout.addWidget(arg_widget_instance)
                self.argument_TW.setItemWidget(tree_widget_item, 1, arg_widget_instance)

                param_tool_tip = param_tool_tips.get(param.name, "parameter un-documented")
                arg_widget_instance.setToolTip(param_tool_tip)

                self.generated_arg_widgets.append(arg_widget_instance)
            else:
                no_widget_label = QtWidgets.QLabel("No Widget Found for argument: {}".format(param_type.__name__))
                self.argument_TW.setItemWidget(tree_widget_item, 1, no_widget_label)

    def get_modified_values(self):
        args = []
        kwargs = {}
        for widget in self.generated_arg_widgets:  # type: ArgumentWidget
            if not widget.was_modified:  # leave defaults as is
                continue

            if widget.is_required:
                args.append(widget.get_argument_value())
            else:
                kwargs[widget.name] = widget.get_argument_value()

        return args, kwargs

    def preview_func_call(self):
        args, kwargs = self.get_modified_values()
        func_string = "{}(".format(self.func.__name__)
        empty_spaces = " " * len(func_string)

        arg_length = len(args)
        kwarg_length = len(kwargs)

        for i, arg_val in enumerate(args):
            if isinstance(arg_val, str):
                func_string += "'{}'".format(arg_val)
            else:
                func_string += "{}".format(arg_val)

            if arg_length > 1 and i != arg_length - 1 or kwarg_length:
                func_string += ",\n{}".format(empty_spaces)

        for i, kwarg_key in enumerate(kwargs.keys()):
            kwarg_val = kwargs[kwarg_key]

            if isinstance(kwarg_val, str):
                func_string += "{}='{}'".format(kwarg_key, kwarg_val)
            else:
                func_string += "{}={}".format(kwarg_key, kwarg_val)

            if kwarg_length > 1 and i != kwarg_length - 1:
                func_string += ",\n{}".format(empty_spaces)

        if arg_length + kwarg_length > 1:
            func_string += "\n{})".format(empty_spaces)
        else:
            func_string += ")"
        self.func_preview_text_TE.setText(func_string)

    def run_func(self):
        args, kwargs = self.get_modified_values()
        self.func(*args, **kwargs)


def test_function(file_name, file_path="",
                  transforms=False, shapes=False, attributes=False, connections=False,
                  user_attributes=False, keyable_attributes=False, locked_attributes=False,
                  skip_attrs=None, test_float=1.0, test_int=2,
                  kwarg1=True, testing_very_loooooooooooong_argument_name="Testing"):
    """

    Doc strings in this format will be read and added as tooltips to the widgets

    :param file_name: example doc string used in tooltip
    :param file_path: type can also be defined like this <path> if it wants special widgets
    :param transforms:
    :param shapes:
    :param attributes:
    :param connections:
    :param user_attributes:
    :param keyable_attributes:
    :param locked_attributes:
    :param skip_attrs:
    :param test_float:
    :param test_int:
    :param kwarg1:
    :param testing_very_loooooooooooong_argument_name:
    """
    print(file_name)
    print(file_path)


def main(func, argument_widgets=None, empty_default_type=str):
    arg_dialog = ArgumentDialog(func, argument_widgets=argument_widgets, empty_default_type=empty_default_type)
    arg_dialog.show()
    return arg_dialog


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    dialog = main(test_function)
    sys.exit(app.exec_())
