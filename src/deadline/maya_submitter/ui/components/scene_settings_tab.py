# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os

from qtpy.QtCore import QSize, Qt, QRegularExpression  # type: ignore
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
from qtpy.QtGui import QRegularExpressionValidator  # type: ignore
from deadline.client.ui import block_signals

from ...render_layers import LayerSelection

"""
UI widgets for the Scene Settings tab.
"""


# Job type identifiers. Kept in sync with the values written to settings.job_type
# and consumed by the adaptor's init_data schema.
JOB_TYPE_RENDER = "render"
JOB_TYPE_PYTHON_SCRIPT = "python_script"

_JOB_TYPE_ITEMS = [
    (JOB_TYPE_RENDER, "Render"),
    (JOB_TYPE_PYTHON_SCRIPT, "Python Script"),
]


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
            # file_format is a Qt filter string like "Python Scripts (*.py);;All Files (*)"
            if self.file_format:
                new_txt, _ = QFileDialog.getOpenFileName(
                    self, "Select File", self.edit.text(), self.file_format
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

        # Track all widgets that should only be visible in render mode so we can
        # toggle them when the user switches job type.
        self._render_only_rows: list[tuple[QWidget, QWidget]] = []
        self._python_only_rows: list[tuple[QWidget, QWidget]] = []

        self._build_ui(initial_settings)
        self._configure_settings(initial_settings)
        # Apply visibility based on the configured job type.
        self._on_job_type_changed()

    def _build_ui(self, settings):
        lyt = QGridLayout(self)

        # --- Job Type selector (always visible) ---
        self.job_type_box = QComboBox(self)
        for value, text in _JOB_TYPE_ITEMS:
            self.job_type_box.addItem(text, value)
        lyt.addWidget(QLabel("Job Type"), 0, 0)
        lyt.addWidget(self.job_type_box, 0, 1)
        self.job_type_box.currentIndexChanged.connect(self._on_job_type_changed)

        # --- Always-visible fields ---
        self.proj_path_txt = FileSearchLineEdit(directory_only=True, parent=self)
        lyt.addWidget(QLabel("Project Path"), 1, 0)
        lyt.addWidget(self.proj_path_txt, 1, 1)

        self.op_path_txt = FileSearchLineEdit(directory_only=True)
        lyt.addWidget(QLabel("Output Path"), 2, 0)
        lyt.addWidget(self.op_path_txt, 2, 1)

        # --- Render-only fields ---
        self.layers_label = QLabel("Render Layers")
        self.layers_box = QComboBox(self)
        layer_items = [
            (LayerSelection.ALL, "All Renderable Layers"),
            (LayerSelection.CURRENT, "Current Layer"),
        ]
        for layer_value, text in layer_items:
            self.layers_box.addItem(text, layer_value)
        lyt.addWidget(self.layers_label, 3, 0)
        lyt.addWidget(self.layers_box, 3, 1)
        self.layers_box.currentIndexChanged.connect(self._fill_cameras_box)
        self._render_only_rows.append((self.layers_label, self.layers_box))

        self.cameras_label = QLabel("Cameras")
        self.cameras_box = QComboBox(self)
        lyt.addWidget(self.cameras_label, 4, 0)
        lyt.addWidget(self.cameras_box, 4, 1)
        self._render_only_rows.append((self.cameras_label, self.cameras_box))

        # --- Frame range (visible in both modes; meaning differs) ---
        self.frame_override_chck = QCheckBox("Override Frame Range", self)
        self.frame_override_txt = QLineEdit(self)
        # Only allow numbers, colons, dashes, commas, and whitespace for frame ranges
        frame_pattern = QRegularExpression(r"^[0-9:\-,\s]*$")
        self.frame_override_txt.setValidator(QRegularExpressionValidator(frame_pattern))
        lyt.addWidget(self.frame_override_chck, 5, 0)
        lyt.addWidget(self.frame_override_txt, 5, 1)
        self.frame_override_chck.stateChanged.connect(self.activate_frame_override_changed)

        # --- Python-script-only fields ---
        self.python_script_label = QLabel("Python Script")
        self.python_script_txt = FileSearchLineEdit(
            file_format="Python Scripts (*.py);;All Files (*)", parent=self
        )
        lyt.addWidget(self.python_script_label, 6, 0)
        lyt.addWidget(self.python_script_txt, 6, 1)
        self._python_only_rows.append((self.python_script_label, self.python_script_txt))

        self.script_args_label = QLabel("Script Args")
        self.script_args_txt = QLineEdit(self)
        self.script_args_txt.setToolTip(
            "Optional argument string passed to the script via the "
            "DEADLINE_SCRIPT_ARGS environment variable."
        )
        lyt.addWidget(self.script_args_label, 7, 0)
        lyt.addWidget(self.script_args_txt, 7, 1)
        self._python_only_rows.append((self.script_args_label, self.script_args_txt))

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, 8, 0)

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

    def _on_job_type_changed(self, *args):
        """Toggle visibility of render-only / python-script-only widgets."""
        is_python = self.job_type_box.currentData() == JOB_TYPE_PYTHON_SCRIPT
        for label, widget in self._render_only_rows:
            label.setVisible(not is_python)
            widget.setVisible(not is_python)
        for label, widget in self._python_only_rows:
            label.setVisible(is_python)
            widget.setVisible(is_python)

    def _configure_settings(self, settings):
        # Job type
        index = self.job_type_box.findData(getattr(settings, "job_type", JOB_TYPE_RENDER))
        if index >= 0:
            self.job_type_box.setCurrentIndex(index)

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

        # Python script fields
        self.python_script_txt.setText(getattr(settings, "python_script_path", ""))
        self.script_args_txt.setText(getattr(settings, "script_args", ""))

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """

        settings.job_type = self.job_type_box.currentData()

        settings.project_path = self.proj_path_txt.text()
        settings.output_path = self.op_path_txt.text()

        settings.override_frame_range = self.frame_override_chck.isChecked()
        settings.frame_list = self.frame_override_txt.text()

        settings.render_layer_selection = self.layers_box.currentData()
        settings.camera_selection = self.cameras_box.currentData()

        settings.python_script_path = self.python_script_txt.text()
        settings.script_args = self.script_args_txt.text()

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False

    def activate_frame_override_changed(self, state):
        """
        Set the activated/deactivated status of the Frame override text box
        """
        self.frame_override_txt.setEnabled(Qt.CheckState(state) == Qt.Checked)
