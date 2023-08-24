# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
UI widgets for the Scene Settings tab.
"""
from PySide2.QtCore import QSize, Qt  # type: ignore
from PySide2.QtWidgets import (  # type: ignore
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from ...cameras import CameraSelection
from ...render_layers import LayerSelection


class FileSearchLineEdit(QWidget):
    """
    Widget used to contain a line edit and a button which opens a file search box.
    """

    def __init__(self, file_format=None, directory_only=False, parent=None):
        super().__init__(parent=parent)

        if directory_only and file_format is not None:
            raise ValueError("")

        self.file_format = file_format
        self.directory_only = directory_only

        lyt = QHBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setMargin(0)

        self.edit = QLineEdit(self)
        self.btn = QPushButton("...", parent=self)
        self.btn.setMaximumSize(QSize(100, 40))
        self.btn.clicked.connect(self.get_file)

        lyt.addWidget(self.edit)
        lyt.addWidget(self.btn)

    def get_file(self):
        """
        Open a file picker to allow users to choose a file.
        """
        if self.directory_only:
            new_txt = QFileDialog.getExistingDirectory(
                self,
                "Open Directory",
                self.edit.text(),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
            )
        else:
            new_txt = QFileDialog.getOpenFileName(self, "Select File", self.edit.text())

        if new_txt:
            self.edit.setText(new_txt)

    def setText(self, txt: str) -> None:  # pylint: disable=invalid-name
        """
        Sets the text of the internal line edit
        """
        self.edit.setText(txt)

    def text(self) -> str:
        """
        Retrieves the text from the internal line edit.
        """
        return self.edit.text()


class SceneSettingsWidget(QWidget):
    """
    Widget containing all top level scene settings.
    """

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)

        self._build_ui()
        self._configure_settings(initial_settings)

    def _build_ui(self):
        lyt = QGridLayout(self)
        self.proj_path_txt = FileSearchLineEdit(directory_only=True, parent=self)
        lyt.addWidget(QLabel("Project Path"), 0, 0)
        lyt.addWidget(self.proj_path_txt, 0, 1)

        self.op_path_txt = FileSearchLineEdit(directory_only=True)
        lyt.addWidget(QLabel("Output Path"), 1, 0)
        lyt.addWidget(self.op_path_txt, 1, 1)

        self.layers_box = QComboBox(self)
        layer_items = [
            (LayerSelection.ALL, "All Renderable Layers"),
            (LayerSelection.CURRENT, "Current Layer"),
        ]
        for layer_value, text in layer_items:
            self.layers_box.addItem(text, layer_value)
        # self.layers_box.addItems(layer_selection_display.values())
        lyt.addWidget(QLabel("Render Layers"), 2, 0)
        lyt.addWidget(self.layers_box, 2, 1)

        self.cameras_box = QComboBox(self)
        camera_items = [
            (CameraSelection.SEPARATE, "Separate Steps"),
            (CameraSelection.COMBINED, "Same Step"),
        ]
        for cam_value, text in camera_items:
            self.cameras_box.addItem(text, cam_value)
        lyt.addWidget(QLabel("Cameras"), 3, 0)
        lyt.addWidget(self.cameras_box, 3, 1)

        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        lyt.addWidget(self.frame_override_chck, 4, 0)
        lyt.addWidget(self.frame_override_txt, 4, 1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 10, 0)

        # TODO: Re-enable when these options are available in the back end.
        self.proj_path_txt.setEnabled(False)
        self.op_path_txt.setEnabled(False)
        self.cameras_box.setEnabled(False)

    def _configure_settings(self, settings):
        self.proj_path_txt.setText(settings.project_path)
        self.op_path_txt.setText(settings.output_path)
        self.frame_override_chck.setChecked(settings.override_frame_range)
        self.frame_override_txt.setEnabled(settings.override_frame_range)
        self.frame_override_txt.setText(settings.frame_list)

        index = self.layers_box.findData(settings.render_layer_selection)
        if index >= 0:
            self.layers_box.setCurrentIndex(index)

        index = self.cameras_box.findData(settings.camera_selection)
        if index >= 0:
            self.cameras_box.setCurrentIndex(index)

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """

        settings.project_path = self.proj_path_txt.text()
        settings.output_path = self.op_path_txt.text()

        settings.override_frame_range = self.frame_override_chck.isChecked()
        settings.frame_list = self.frame_override_txt.text()

        settings.render_layer_selection = self.layers_box.currentData()
        settings.camera_selection = self.cameras_box.currentData()

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(state == Qt.Checked)
