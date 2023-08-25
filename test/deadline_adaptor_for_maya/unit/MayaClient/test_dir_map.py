# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import Mock, patch

import pymel.core as _pmc
import pytest

from deadline_adaptor_for_maya.MayaClient.pymel_additions import (
    DirectoryMapping,
    DirectoryMappingDict,
)


class TestDirectoryMappingDict:
    def test_constructor(self):
        """
        No errors raised when constructing the Mapping Dict
        """
        # Given
        DirectoryMappingDict()

    def test_repr(self):
        """Test that the repr is as expected"""
        dict_obj = DirectoryMappingDict()
        assert str(dict_obj) == "DirectoryMappingDict"

    @patch.object(_pmc, "dirmap")
    def test_get_items_with_values(self, mock_dirmap: Mock):
        """
        Test that get_item successfully returns the correct value
        """
        # Given
        # dirmap returns a flattened list of pairs.
        mock_dirmap.return_value = "dest"

        dict_obj = DirectoryMappingDict()

        # When
        assert dict_obj["source"] == "dest"

        # Then
        mock_dirmap.assert_called_once_with(getMappedDirectory="source")

    @patch.object(_pmc, "dirmap")
    def test_get_items_with_non_existant_key(self, mock_dirmap: Mock):
        """Test that __get_items__ raises an error if the key does not exist"""
        # Given
        mock_dirmap.return_value = None
        dict_obj = DirectoryMappingDict()

        # When
        with pytest.raises(KeyError):
            _ = dict_obj["unknown"]

        # Then
        mock_dirmap.assert_called_once_with(getMappedDirectory="unknown")

    @patch.object(_pmc, "dirmap")
    def test_get_with_values(self, mock_dirmap: Mock):
        """
        Test that get_item successfully returns the correct value
        """
        # Given
        # dirmap returns a flattened list of pairs.
        mock_dirmap.return_value = "dest"

        dict_obj = DirectoryMappingDict()

        # When
        assert dict_obj.get("source") == "dest"

        # Then
        mock_dirmap.assert_called_once_with(getMappedDirectory="source")

    @patch.object(_pmc, "dirmap")
    def test_get_with_non_existant_key(self, mock_dirmap: Mock):
        """
        Test that .get returns None if the key does not exist
        """
        # Given
        mock_dirmap.return_value = None
        dict_obj = DirectoryMappingDict()

        # When
        assert dict_obj.get("unknown") is None

        # Then
        mock_dirmap.assert_called_once_with(getMappedDirectory="unknown")

    @patch.object(_pmc, "dirmap")
    def test_get_with_non_existant_key_with_default(self, mock_dirmap: Mock):
        """
        Test that get works with default arguments when specified
        """
        # Given
        mock_dirmap.return_value = None
        dict_obj = DirectoryMappingDict()

        # When
        assert dict_obj.get("unknown", default="default") == "default"

        # Then
        mock_dirmap.assert_called_once_with(getMappedDirectory="unknown")

    @patch.object(_pmc, "dirmap")
    def test_set_item(self, mock_dirmap: Mock):
        """
        Test that set item calls dirmap with the correct args
        """
        # Given
        dict_obj = DirectoryMappingDict()

        # When
        dict_obj["key"] = "value"

        # Then
        mock_dirmap.assert_called_once_with(mapDirectory=("key", "value"))

    @patch.object(_pmc, "dirmap")
    def test_del_item(self, mock_dirmap: Mock):
        """
        Test that dirmap is called with unmapDirectiroy
        """
        # Given
        dict_obj = DirectoryMappingDict()

        # When
        del dict_obj["key"]

        # Then
        mock_dirmap.assert_called_once_with(unmapDirectory="key")

    @patch.object(_pmc, "dirmap")
    def test_in_no_value(self, mock_dirmap: Mock):
        """
        Test that in fails if getMappedDirectory returns None
        """
        # WHEN
        mock_dirmap.return_value = None
        dict_obj = DirectoryMappingDict()

        # THEN
        assert "key" not in dict_obj
        mock_dirmap.assert_called_once_with(getMappedDirectory="key")

    @patch.object(_pmc, "dirmap")
    def test_in_with_value(self, mock_dirmap: Mock):
        """
        Test that in succeeds if dirmap returns a value
        """

        # When
        mock_dirmap.return_value = "value"
        dict_obj = DirectoryMappingDict()

        # Then
        assert "key" in dict_obj
        mock_dirmap.assert_called_once_with(getMappedDirectory="key")

    @pytest.mark.parametrize("mappings", [["source", "dest", "orig", "swapped"], []])
    @patch.object(_pmc, "dirmap")
    def test_keys(self, mock_dirmap: Mock, mappings: list):
        """
        Test that keys returns the expected list of keys
        """
        # Given
        mock_dirmap.return_value = mappings
        dict_obj = DirectoryMappingDict()

        # When
        keys = dict_obj.keys()

        # Then
        assert keys == mappings[::2]
        mock_dirmap.assert_called_once_with(getAllMappings=True)

    @pytest.mark.parametrize("mappings", [["source", "dest", "orig", "swapped"], []])
    @patch.object(_pmc, "dirmap")
    def test_values(self, mock_dirmap: Mock, mappings: list):
        """Test that values return the expected values"""
        # Given
        mock_dirmap.return_value = mappings
        dict_obj = DirectoryMappingDict()

        # When
        vals = dict_obj.values()

        # Then
        assert vals == mappings[1::2]
        mock_dirmap.assert_called_once_with(getAllMappings=True)

    @pytest.mark.parametrize("mappings", [["source", "dest", "orig", "swapped"], []])
    @patch.object(_pmc, "dirmap")
    def test_items(self, mock_dirmap: Mock, mappings: list):
        """
        Test that items return the correct tuples.
        """
        # Given
        mock_dirmap.return_value = mappings
        dict_obj = DirectoryMappingDict()

        # When
        items = dict_obj.items()

        assert len(items) == len(mappings) / 2
        assert all(len(item) == 2 for item in items)

    @pytest.mark.parametrize("mappings", [["source", "dest", "orig", "swapped"], []])
    @patch.object(_pmc, "dirmap")
    def test_iter(self, mock_dirmap: Mock, mappings: list):
        """
        Test that the dict can be iterated over properly.
        """
        # Given
        mock_dirmap.return_value = mappings
        dict_obj = DirectoryMappingDict()

        assert [x for x in dict_obj] == mappings[::2]


class TestDirectoryMapping:
    def test_mappings_is_mapping_dict(self):
        """
        Test that the mappings is a directory mapping dict
        """
        assert isinstance(DirectoryMapping.mappings, DirectoryMappingDict)

    @patch.object(_pmc, "dirmap")
    def test_get_activated(self, mock_dirmap: Mock):
        """
        Test that get_activated queries dirmaps activated flag
        """
        # GIVEN
        mock_dirmap.return_value = True

        # WHEN
        assert DirectoryMapping.get_activated() is True

        # THEN
        mock_dirmap.assert_called_once_with(query=True, enable=True)

    @pytest.mark.parametrize("value", [True, False])
    @patch.object(_pmc, "dirmap")
    def test_set_activated(self, mock_dirmap: Mock, value: bool):
        """
        Test that set_activated modifies the enable flag on dirmap
        """
        # WHEN
        DirectoryMapping.set_activated(value)

        # THEN
        mock_dirmap.assert_called_once_with(enable=value)

    @patch.object(_pmc, "dirmap")
    def test_convert(self, mock_dirmap: Mock):
        """
        Test that convert correctly passes through the call to dirmap
        """
        # WHEN
        DirectoryMapping.convert("/test")

        # THEN
        mock_dirmap.assert_called_once_with(convertDirectory="/test")
