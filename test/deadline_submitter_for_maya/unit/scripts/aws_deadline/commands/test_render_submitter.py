# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import json

from deadline_submitter_for_maya.scripts.aws_deadline.commands.renderSubmitter import (
    RenderSubmitterCmd,
)


class TestRenderSubmitterCmd:
    def test_cmd_creator(self) -> None:
        """Tests that the cmdCreater creates a RenderSubmitterCmd class"""
        # WHEN
        cmd = RenderSubmitterCmd.cmdCreator()

        # THEN
        assert isinstance(cmd, RenderSubmitterCmd)

    mock_output_response = {
        "status": "SUCCESS",
        "result": json.dumps(
            {
                "RenderManagers": {
                    "RenderManager": {
                        "farm": {
                            "allowed_values": ["farm1:abc123", "farm2:def456", "farm3:ghi789"]
                        },
                        "queues_farm1": {
                            "allowed_values": [
                                "farm1q1:jkl123",
                                "farm1q2:mno456",
                                "farm1q3:pqr789",
                            ],
                        },
                        "submission_status": {
                            "allowed_values": ["status1", "status2", "status3"],
                        },
                        "retries": {"default": 1},
                    }
                }
            }
        ),
    }
