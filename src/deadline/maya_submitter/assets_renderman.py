import errno
import os

from deadline.client.job_bundle.submission import AssetReferences

OPTION_TAG = 'Option'
DISPLAY_TAG = 'Display'
LIGHTMAP_TAG = '"string lightColorMap"'
FILE_TAG = '"string filename"'


class RibFileProcessor:
    _awaiting_display_file = False
    _awaiting_filename = False
    _line_number = 0
    _output_filename = ""
    _output_path = ""
    _asset_references = None

    def process_display(self, parts) -> str:
        if len(parts) == 0:
            # Filename could be on the following line.
            self._awaiting_display_file = True
            return ""

        # Filename will be surrounded by quotes, remove them.
        _output_path = parts[0][1:-1]

        self._output_filename = os.path.basename(_output_path)
        self._output_path = os.path.dirname(_output_path)

        self._asset_references.output_directories.add(self._output_path)
        return ' '.join(parts)

    def get_following_filename(self, search_start_index, line) -> str:
        offset = search_start_index
        # Look for first ".
        while offset < len(line) and line[offset] != '"':
            offset += 1

        if offset >= len(line):  # Line is split - need to search on next line.
            return ""

        # Find the end of the filename.
        length = line.find('"', offset+1)
        if length < 0:
            raise ValueError('Line break detected inside string at line {}.'.format(self._line_number))

        filepath = line[offset+1:length]
        self._awaiting_filename = False

        return filepath

    def process_other_line(self, line) -> str:
        offset = 0

        if not self._awaiting_filename:
            offset = line.find(FILE_TAG)
            if offset >= 0:
                offset += len(FILE_TAG)

            if offset < 0:
                offset = line.find(LIGHTMAP_TAG)
                if offset >= 0:
                    offset += len(LIGHTMAP_TAG)

            if offset < 0:
                return line

        # We have found a filename tag, start looking for the filename which may be on a subsequent line.
        self._awaiting_filename = True
        try:
            filename = self.get_following_filename(offset, line)
        except ValueError:
            raise

        if not self._awaiting_filename and len(filename) > 0:
            if os.path.exists(filename):
                self._asset_references.input_filenames.add(filename)

        return line

    def process_line(self, line) -> str:
        parts = line.split(" ")
        if len(parts) == 0:
            return ""

        try:
            if self._awaiting_display_file:
                self._awaiting_display_file = False
                return self.process_display(parts)

            tag = parts[0]

            if tag == DISPLAY_TAG:
                return tag + " " + self.process_display(parts[1:])
            else:
                return self.process_other_line(line)
        except ValueError:
            raise

    def read(self, in_filename, asset_references) -> AssetReferences:
        self._asset_references = asset_references

        if not os.path.exists(in_filename):
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), in_filename)

        self._asset_references.input_filenames.add(in_filename)
        try:
            input_file = open(in_filename, "r")

            self._line_number = 1

            for input_line in input_file:
                self.process_line(input_line)
                self._line_number += 1
        except ValueError as e:
            print(str(e))
            return asset_references

        return asset_references

    @property
    def output_file(self) -> str:
        return self._output_filename

    @property
    def output_path(self) -> str:
        return self._output_path

