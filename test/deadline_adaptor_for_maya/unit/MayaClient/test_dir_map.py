# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from deadline.maya_adaptor.MayaClient.dir_map import DirectoryMapping, DirectoryMappingDict


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


class TestDirectoryMapping:
    def test_mappings_is_mapping_dict(self):
        """
        Test that the mappings is a directory mapping dict
        """
        assert isinstance(DirectoryMapping.mappings, DirectoryMappingDict)
