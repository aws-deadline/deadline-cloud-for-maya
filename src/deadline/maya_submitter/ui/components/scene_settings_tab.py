# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os

from qtpy.QtCore import QSize, Qt  # type: ignore
from qtpy.QtWidgets import (  # type: ignore
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
from deadline.client.ui import block_signals

from ...render_layers import LayerSelection

"""
UI widgets for the Scene Settings tab.
"""


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

        self.developer_options = (
            os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )

        # Save the two lists of selectable cameras
        self.all_layer_selectable_cameras = initial_settings.all_layer_selectable_cameras
        self.current_layer_selectable_cameras = initial_settings.current_layer_selectable_cameras

        self._build_ui(initial_settings)
        self._configure_settings(initial_settings)

    def _build_ui(self, settings):
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
        lyt.addWidget(QLabel("Render Layers"), 2, 0)
        lyt.addWidget(self.layers_box, 2, 1)
        self.layers_box.currentIndexChanged.connect(self._fill_cameras_box)

        self.cameras_box = QComboBox(self)
        lyt.addWidget(QLabel("Cameras"), 3, 0)
        lyt.addWidget(self.cameras_box, 3, 1)

        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        lyt.addWidget(self.frame_override_chck, 4, 0)
        lyt.addWidget(self.frame_override_txt, 4, 1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, 5, 0)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 10, 0)

        self._fill_cameras_box(0)

    def _fill_cameras_box(self, _):
        with block_signals(self.cameras_box):
            # Determine the list of selectable cameras
            if self.layers_box.currentData() == LayerSelection.ALL:
                selectable_cameras = self.all_layer_selectable_cameras
            else:
                selectable_cameras = self.current_layer_selectable_cameras

            # Save the current camera and reset the camera box list
            saved_camera_name = self.cameras_box.currentData()
            self.cameras_box.clear()
            for camera_name in selectable_cameras:
                self.cameras_box.addItem(camera_name, camera_name)

            # Re-select the camera if possible
            index = self.cameras_box.findData(saved_camera_name)
            if index >= 0:
                self.cameras_box.setCurrentIndex(index)

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

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

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

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(Qt.CheckState(state) == Qt.Checked)
