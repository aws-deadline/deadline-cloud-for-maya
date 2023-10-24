# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
UI widgets for the Scene Settings tab.
"""
import os
from PySide2.QtCore import QSize, Qt  # type: ignore
from PySide2.QtWidgets import (  # type: ignore
    QCheckBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)


class SceneSettingsWidget(QWidget):
    """
    Widget containing all top level scene settings.
    """
    info_line = None

    def __init__(self, initial_settings, parent=None):
        super().__init__(parent=parent)

        self.developer_options = (
                os.environ.get("DEADLINE_ENABLE_DEVELOPER_OPTIONS", "").upper() == "TRUE"
        )

        self._build_ui()
        self._configure_settings(initial_settings)

    def _build_ui(self):
        lyt = QGridLayout(self)
        self.rib_file_path_txt = QListWidget(self)
        lyt.addWidget(QLabel("Rib Files"), 0, 0)
        lyt.addWidget(self.rib_file_path_txt, 0, 1)

        self.continue_on_error_checkbox = QCheckBox(self)
        lyt.addWidget(QLabel("ContinueOnError"), 1, 0)
        lyt.addWidget(self.continue_on_error_checkbox, 1, 1)

        if self.developer_options:
            self.include_adaptor_wheels = QCheckBox(
                "Developer Option: Include Adaptor Wheels", self
            )
            lyt.addWidget(self.include_adaptor_wheels, 5, 0)

        lyt.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 10, 0)

        self.rib_file_path_txt.setEnabled(False)

    def _configure_settings(self, settings):
        self.rib_file_path_txt.addItems(settings.rib_file_paths.split(', '))
        self.continue_on_error_checkbox.setChecked(settings.continue_on_error == "true")

        if self.developer_options:
            self.include_adaptor_wheels.setChecked(settings.include_adaptor_wheels)

    def update_settings(self, settings):
        """
        Update a scene settings object with the latest values.
        """
        rib_list = [self.rib_file_path_txt.item(x).text() for x in range(self.rib_file_path_txt.count())]
        settings.rib_file_paths = ', '.join(rib_list)
        if self.continue_on_error_checkbox.isChecked():
            settings.continue_on_error = "true"
        else:
            settings.continue_on_error = "false"

        if self.developer_options:
            settings.include_adaptor_wheels = self.include_adaptor_wheels.isChecked()
        else:
            settings.include_adaptor_wheels = False



